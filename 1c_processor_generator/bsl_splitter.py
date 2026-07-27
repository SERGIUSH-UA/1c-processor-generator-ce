"""
BSL Splitter для генератора зовнішніх обробок 1C

Розділяє монолітний BSL файл з процедурами на окремі файли.
Дозволяє LLM генерувати один великий файл, який автоматично розділяється на модулі.

Приклад:
    # LLM генерує handlers.bsl з усіма процедурами
    splitter = BSLSplitter(Path("handlers.bsl"))

    # Автоматичне розділення на окремі файли
    files = splitter.split_to_directory(Path("handlers/"))
    # Результат: handlers/ПриОткрытии.bsl, handlers/Команда1.bsl, ...
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from .constants import ENCODING_UTF8_BOM


class BSLSplitter:
    """Клас для розділення монолітного BSL файлу на окремі процедури"""

    # Regex паттерни для парсингу BSL коду

    # Пошук процедур та функцій з опціональною директивою
    # Групи: (директива?, тип процедури/функції, назва, параметри, тіло, закриваючий тег)
    PROCEDURE_PATTERN = re.compile(
        r'(?:^|\n)'  # Початок рядка або новий рядок
        r'((?:&[^\n]+\n)+)?'  # Група 1: Опціональні директиви (може бути кілька)
        r'\s*'  # Можливі пробіли
        r'(Процедура|Функция|Procedure|Function|Асинх|Async)'  # Група 2: Тип
        r'\s+'  # Пробіли
        r'(\w+)'  # Група 3: Назва процедури/функції
        r'\s*\('  # Відкриваюча дужка
        r'([^)]*)'  # Група 4: Параметри (все до закриваючої дужки)
        r'\)'  # Закриваюча дужка
        r'(.*?)'  # Група 5: Тіло процедури (non-greedy)
        r'(КонецПроцедуры|КонецФункции|EndProcedure|EndFunction)',  # Група 6: Закриваючий тег
        re.DOTALL | re.MULTILINE | re.IGNORECASE
    )

    # Пошук коментарів перед процедурою
    COMMENTS_BEFORE_PROCEDURE = re.compile(
        r'((?:^|\n)(?://[^\n]*\n)+)',  # Група коментарів
        re.MULTILINE
    )

    # Пошук регіону Документация (v2.14.0+)
    DOCUMENTATION_REGION_PATTERN = re.compile(
        r'#Область\s+Документация\s*\n(.*?)\n#КонецОбласти',
        re.DOTALL | re.IGNORECASE
    )

    # Пошук регіону МодульОбъекта (v2.66.0+)
    # Код з цього регіону потрапляє в ObjectModule.bsl замість FormModule
    # Підтримує: МодульОбъекта, МодульОб'єкта, ObjectModule
    # ВАЖЛИВО: (?:^|\n) гарантує що ми знаходимо регіон на початку рядка, а не в коментарі
    OBJECT_MODULE_REGION_PATTERN = re.compile(
        r"(?:^|\n)#(?:Область|Region)\s+(?:Модуль(?:Объекта|Об['\u0027]?єкта)|ObjectModule)\s*\n(.*?)\n#(?:КонецОбласти|EndRegion)",
        re.DOTALL | re.IGNORECASE
    )

    # Пошук модульних змінних (v2.73.0+)
    # Підтримує: Перем Var1, Var2 Экспорт; // коментар
    # З опціональними директивами: &НаКлиенте\nПерем Var;
    # ВАЖЛИВО: Витягуємо ТІЛЬКИ змінні ДО першої процедури/функції (module-level)
    MODULE_VARIABLE_PATTERN = re.compile(
        r'((?:^[ \t]*//[^\n]*\n)*'          # Група 1: Попередні коментарі (опціонально)
        r'(?:^[ \t]*&[^\n]+\n)?'            # Директива (опціонально)
        r'^[ \t]*(?:Перем|Var)\s+'          # Ключове слово Перем/Var
        r'[^;]+;'                            # Імена змінних до крапки з комою
        r'(?:[ \t]*//[^\n]*)?)',            # Inline коментар (опціонально)
        re.MULTILINE | re.IGNORECASE
    )

    def __init__(self, bsl_file_path: Path):
        """
        Ініціалізація BSL Splitter

        Args:
            bsl_file_path: Шлях до монолітного BSL файлу
        """
        self.bsl_file_path = Path(bsl_file_path)

        if not self.bsl_file_path.exists():
            raise FileNotFoundError(f"BSL файл не знайдено: {self.bsl_file_path}")

        # Завантажуємо вміст файлу
        self.content = self._load_file()

        # Чи був витягнутий регіон #Область МодульОбъекта (v2.78.0+)
        self.object_module_extracted = False

    def _load_file(self) -> str:
        """
        Завантажує вміст BSL файлу

        Returns:
            Вміст файлу як рядок
        """
        try:
            # Спробуємо UTF-8 з BOM
            return self.bsl_file_path.read_text(encoding=ENCODING_UTF8_BOM)
        except UnicodeDecodeError:
            # Якщо не вийшло, спробуємо без BOM
            try:
                return self.bsl_file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                # Останній варіант - Windows-1251 (для старих файлів)
                return self.bsl_file_path.read_text(encoding="windows-1251")

    def extract_documentation_region(self) -> Optional[str]:
        """
        Витягує регіон #Область Документация з BSL файлу (v2.14.0+)

        Регіон витягується ПЕРЕД парсингом процедур і видаляється з self.content
        щоб не заважати пошуку процедур.

        Returns:
            Текст документації (без маркерів #Область/#КонецОбласти) або None

        Example:
            # У handlers.bsl:
            #Область Документация
            // Опис модуля
            // Приклад коду
            #КонецОбласті

            # Результат:
            "// Опис модуля\\n// Приклад коду"
        """
        match = self.DOCUMENTATION_REGION_PATTERN.search(self.content)

        if not match:
            return None

        # Витягуємо вміст регіону (група 1)
        documentation = match.group(1).strip()

        # Видаляємо регіон з content щоб не заважав парсингу процедур
        self.content = self.content[:match.start()] + self.content[match.end():]

        print(f"  ✓ Витягнуто регіон Документация ({len(documentation)} символів)")

        return documentation

    def extract_object_module_region(self) -> Optional[str]:
        """
        Витягує регіон #Область МодульОбъекта з BSL файлу (v2.66.0+)

        Код з цього регіону буде додано в ObjectModule.bsl замість FormModule.
        Підтримує назви: МодульОбъекта, МодульОб'єкта, ObjectModule

        Регіон витягується ПЕРЕД парсингом процедур і видаляється з self.content
        щоб не заважати пошуку процедур.

        Returns:
            Текст модуля об'єкта (без маркерів #Область/#КонецОбласти) або None

        Example:
            # У handlers.bsl:
            #Область МодульОбъекта

            Функция СведенияОВнешнейОбработке() Экспорт
                // ...
            КонецФункции

            #КонецОбласти

            &НаКлиенте
            Процедура Команда1(Команда)
                // Це йде в FormModule
            КонецПроцедуры
        """
        match = self.OBJECT_MODULE_REGION_PATTERN.search(self.content)

        if not match:
            return None

        # Витягуємо вміст регіону (група 1)
        object_module_code = match.group(1).strip()

        # Видаляємо регіон з content щоб не заважав парсингу процедур
        self.content = self.content[:match.start()] + self.content[match.end():]
        self.object_module_extracted = True

        print(f"  ✓ Витягнуто регіон МодульОбъекта ({len(object_module_code)} символів)")

        return object_module_code

    def extract_module_variables(self) -> Optional[str]:
        """
        Витягує модульні змінні з BSL файлу (v2.73.0+)

        Модульні змінні - це декларації `Перем` на рівні модуля (до процедур/функцій).
        Вони відрізняються від локальних змінних всередині процедур.

        Підтримує:
        - Прості декларації: Перем Var1;
        - Множинні змінні: Перем Var1, Var2, Var3;
        - З директивами: &НаКлиенте\\nПерем Var;
        - З Экспорт: Перем Var Экспорт;
        - З коментарями: Перем Var; // коментар
        - Multiline: Перем Var1,\\n\\tVar2;

        Регіон витягується ПЕРЕД парсингом процедур і видаляється з self.content.

        Returns:
            Текст всіх модульних змінних або None

        Example:
            # У handlers.bsl:
            &НаКлиенте
            Перем Направление, Змейка;

            &НаКлиенте
            Процедура НачатьИгру(Команда)
                // ...
            КонецПроцедуры

            # Результат:
            "&НаКлиенте\\nПерем Направление, Змейка;"
        """
        # 1. Знайти позицію першої процедури/функції
        first_proc_match = self.PROCEDURE_PATTERN.search(self.content)

        if first_proc_match:
            # Беремо текст ДО першої процедури (module-level preamble)
            preamble = self.content[:first_proc_match.start()]
        else:
            # Немає процедур - весь контент є preamble (рідкісний випадок)
            preamble = self.content

        # 2. Знайти всі декларації Перем в preamble
        var_matches = list(self.MODULE_VARIABLE_PATTERN.finditer(preamble))

        if not var_matches:
            return None

        # 3. Збираємо всі знайдені декларації
        var_declarations = []
        for match in var_matches:
            var_decl = match.group(1).strip()
            if var_decl:
                var_declarations.append(var_decl)

        if not var_declarations:
            return None

        # 4. Видаляємо знайдені декларації з preamble
        # (щоб не заважали парсингу процедур)
        modified_preamble = preamble
        for match in reversed(var_matches):  # reversed щоб індекси не зсувались
            modified_preamble = modified_preamble[:match.start()] + modified_preamble[match.end():]

        # 5. Оновлюємо content з видаленими змінними
        if first_proc_match:
            self.content = modified_preamble + self.content[first_proc_match.start():]
        else:
            self.content = modified_preamble

        # 6. Формуємо результат
        module_vars = '\n'.join(var_declarations)

        var_count = len(var_declarations)
        print(f"  ✓ Витягнуто {var_count} модульн{'у' if var_count == 1 else 'их'} змінн{'у' if var_count == 1 else 'их'}")

        return module_vars

    def extract_procedures(self) -> Dict[str, str]:
        """
        Витягує процедури як словник {назва: код}

        Returns:
            Словник, де ключ - назва процедури, значення - повний код процедури

        Example:
            {
                "ПриОткрытии": "&НаКлиенте\\nПроцедура ПриОткрытии(Отказ)\\n...\\nКонецПроцедуры",
                "Команда1": "&НаКлиенте\\nПроцедура Команда1(Команда)\\n...\\nКонецПроцедуры"
            }
        """
        procedures = {}

        # Шукаємо всі процедури в файлі
        for match in self.PROCEDURE_PATTERN.finditer(self.content):
            directive = match.group(1)  # &НаКлиенте або None
            proc_type = match.group(2)  # Процедура або Функция
            proc_name = match.group(3)  # Назва
            params = match.group(4)     # Параметри
            body = match.group(5)       # Тіло
            end_tag = match.group(6)    # КонецПроцедуры або КонецФункции

            # Збираємо повний код процедури
            full_code = self._assemble_procedure(
                directive=directive,
                proc_type=proc_type,
                proc_name=proc_name,
                params=params,
                body=body,
                end_tag=end_tag
            )

            procedures[proc_name] = full_code

            print(f"  ✓ Витягнуто процедуру: {proc_name}")

        # Порожній результат нормальний, якщо весь код лежить у регіоні
        # МодульОбъекта (напр. BSP print_form) - тоді це не привід попереджати
        if not procedures and not self.object_module_extracted:
            print(f"⚠️  Не знайдено процедур у файлі {self.bsl_file_path}")

        return procedures

    def _assemble_procedure(
        self,
        directive: Optional[str],
        proc_type: str,
        proc_name: str,
        params: str,
        body: str,
        end_tag: str
    ) -> str:
        """
        Збирає повний код процедури з окремих частин

        Args:
            directive: Директива компіляції (&НаКлиенте, &НаСервере)
            proc_type: Тип (Процедура, Функция)
            proc_name: Назва процедури
            params: Параметри
            body: Тіло процедури
            end_tag: Закриваючий тег (КонецПроцедуры, КонецФункции)

        Returns:
            Повний код процедури
        """
        parts = []

        # Директива (якщо є)
        if directive:
            parts.append(directive.strip())

        # Заголовок процедури
        parts.append(f"{proc_type} {proc_name}({params})")

        # Тіло процедури
        parts.append(body)

        # Закриваючий тег
        parts.append(end_tag)

        return "\n".join(parts)

    def split_to_directory(self, output_dir: Path) -> Dict[str, Path]:
        """
        Розділяє файл на окремі файли в директорії

        Args:
            output_dir: Директорія для збереження окремих BSL файлів

        Returns:
            Словник {назва_процедури: шлях_до_файлу}

        Example:
            {
                "ПриОткрытии": Path("handlers/ПриОткрытии.bsl"),
                "Команда1": Path("handlers/Команда1.bsl")
            }
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        procedures = self.extract_procedures()
        file_paths = {}

        print(f"\n📂 Збереження {len(procedures)} процедур у {output_dir}...")

        for proc_name, proc_code in procedures.items():
            file_path = output_dir / f"{proc_name}.bsl"

            # Зберігаємо з UTF-8 BOM (стандарт для BSL файлів)
            file_path.write_text(proc_code, encoding=ENCODING_UTF8_BOM)

            file_paths[proc_name] = file_path
            print(f"  ✓ {file_path.name}")

        return file_paths

    @staticmethod
    def validate_bsl_file(bsl_file: Path) -> Tuple[bool, str]:
        """
        Валідує BSL файл перед розділенням

        Args:
            bsl_file: Шлях до BSL файлу

        Returns:
            Кортеж (валідний?, повідомлення про помилку)

        Example:
            is_valid, error = BSLSplitter.validate_bsl_file(Path("handlers.bsl"))
            if not is_valid:
                print(f"Помилка: {error}")
        """
        if not bsl_file.exists():
            return False, f"Файл не знайдено: {bsl_file}"

        if not bsl_file.is_file():
            return False, f"Шлях не є файлом: {bsl_file}"

        if bsl_file.suffix.lower() not in [".bsl", ".txt"]:
            return False, f"Невірне розширення файлу: {bsl_file.suffix} (очікується .bsl)"

        # Перевіряємо, чи файл не порожній
        try:
            content = bsl_file.read_text(encoding=ENCODING_UTF8_BOM)
            if not content.strip():
                return False, f"Файл порожній: {bsl_file}"
        except Exception as e:
            return False, f"Помилка читання файлу: {e}"

        return True, ""


def split_bsl_file(bsl_file: Path, output_dir: Path) -> Optional[Dict[str, Path]]:
    """
    Утилітна функція для швидкого розділення BSL файлу

    Args:
        bsl_file: Шлях до монолітного BSL файлу
        output_dir: Директорія для збереження окремих файлів

    Returns:
        Словник {назва_процедури: шлях_до_файлу} або None у разі помилки

    Example:
        files = split_bsl_file(
            Path("handlers.bsl"),
            Path("handlers/")
        )
    """
    try:
        # Валідація
        is_valid, error = BSLSplitter.validate_bsl_file(bsl_file)
        if not is_valid:
            print(f"❌ {error}")
            return None

        # Розділення
        splitter = BSLSplitter(bsl_file)
        return splitter.split_to_directory(output_dir)

    except Exception as e:
        print(f"❌ Помилка розділення BSL файлу: {e}")
        import traceback
        traceback.print_exc()
        return None
