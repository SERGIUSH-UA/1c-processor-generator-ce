"""
BSL Handler Injection для генератора зовнішніх обробок 1C

Цей модуль відповідає за:
1. Завантаження BSL коду з окремих файлів
2. Обгортання BSL коду в процедурні сигнатури
3. Інжектування BSL коду в Processor об'єкт
"""

import re
from pathlib import Path
from typing import Dict, Optional, Tuple

# v2.53.0+: Critical constants from PRO module (.pyd)
from .pro.generation_context import get_generation_context

# Get constants from generation context
_gen_ctx = get_generation_context()
FORM_EVENT_SIGNATURES = _gen_ctx["form_event_signatures"]
ELEMENT_EVENT_SIGNATURES = _gen_ctx["element_event_signatures"]
EVENT_HANDLER_TEMPLATE = _gen_ctx["event_handler_template"]
SERVER_CALL_TEMPLATE = _gen_ctx["server_call_template"]
SERVER_PROCEDURE_TEMPLATE = _gen_ctx["server_procedure_template"]
LONG_OPERATION_CLIENT_BUTTON_TEMPLATE = _gen_ctx["long_operation_client_button_template"]
LONG_OPERATION_SERVER_START_TEMPLATE = _gen_ctx["long_operation_server_start_template"]
LONG_OPERATION_CLIENT_COMPLETION_TEMPLATE = _gen_ctx["long_operation_client_completion_template"]


class BSLInjector:
    """Клас для завантаження та інжектування BSL handlers"""

    @staticmethod
    def has_bsl_signature(code: str) -> bool:
        """
        Перевіряє чи BSL код вже має сигнатуру процедури/функції

        Args:
            code: BSL код для перевірки

        Returns:
            True якщо код має сигнатуру, False якщо потрібно обгорнути
        """
        stripped = code.strip()
        return (
            stripped.startswith("&") or
            stripped.startswith("Процедура") or
            stripped.startswith("Функция") or
            stripped.startswith("Procedure") or
            stripped.startswith("Function") or
            stripped.startswith("Асинх") or  # Async для нових версій 1C
            stripped.startswith("Async")
        )

    def __init__(
        self,
        handlers_dir: Optional[Path] = None,
        handlers_file: Optional[Path] = None,
        normalize_escapes: bool = False,
    ):
        """
        Args:
            handlers_dir: Шлях до директорії з окремими BSL файлами (старий підхід)
            handlers_file: Шлях до монолітного BSL файлу з усіма процедурами (новий підхід)
            normalize_escapes: Нормалізувати escape-послідовності в BSL (v2.72.0+)
        """
        self.handlers_dir = None
        self._loaded_handlers: Dict[str, str] = {}
        self._helper_procedures_cache: Dict[str, str] = {}  # Кеш для хелперів
        self._form_handlers_cache: Dict[str, Dict[str, str]] = {}  # Кеш per-form handlers (v2.69.0+)
        self._documentation_from_handlers: Optional[str] = None  # Документація з регіону #Область Документация (v2.14.0+)
        self._object_module_from_handlers: Optional[str] = None  # Код для ObjectModule з регіону #Область МодульОбъекта (v2.66.0+)
        self._module_variables_from_handlers: Optional[str] = None  # Модульні змінні Перем (v2.73.0+)
        self._normalize_escapes = normalize_escapes  # v2.72.0+

        # Новий підхід: один файл з усіма процедурами
        if handlers_file:
            self.load_handlers_from_single_file(handlers_file)
        # Старий підхід: окремі файли в директорії
        elif handlers_dir:
            self.handlers_dir = Path(handlers_dir)

    def _normalize_bsl_escape_sequences(self, code: str) -> str:
        """
        Нормалізує escape-послідовності в BSL коді (v2.72.0+).

        LLM часто генерують запити з буквальними \\n замість реальних переносів:
        "ВЫБРАТЬ\\n    |   Поле" → "ВЫБРАТЬ
            |   Поле"

        Нормалізує тільки \\n перед | (формат запитів 1С) для безпеки.

        Args:
            code: BSL код

        Returns:
            Нормалізований код
        """
        # Патерн: literal backslash + n перед опціональними пробілами та |
        # Це специфічно для форматування запитів 1С
        pattern = re.escape('\\') + r'n(\s*' + re.escape('|') + r')'
        normalized = re.sub(pattern, '\n\\1', code)

        if normalized != code:
            # Рахуємо кількість замін для логування
            count = code.count('\\n') - normalized.count('\\n')
            if count > 0:
                print(f"  🔄 Нормалізовано {count} escape-послідовностей в запитах")

        return normalized

    def load_handlers_from_single_file(self, bsl_file: Path) -> None:
        """
        Завантажує BSL handlers з монолітного файлу

        Використовує BSLSplitter для автоматичного розділення файлу
        на окремі процедури, які зберігаються в кеші _loaded_handlers.

        Args:
            bsl_file: Шлях до монолітного BSL файлу з усіма процедурами

        Example:
            injector = BSLInjector(handlers_file=Path("handlers.bsl"))
            # Автоматично завантажує всі процедури з файлу
        """
        from .bsl_splitter import BSLSplitter

        bsl_file = Path(bsl_file)

        if not bsl_file.exists():
            print(f"❌ BSL файл не знайдено: {bsl_file}")
            return

        print(f"📦 Завантаження BSL handlers з монолітного файлу {bsl_file.name}...")

        try:
            # Використовуємо BSLSplitter для витягування процедур та документації
            splitter = BSLSplitter(bsl_file)

            # Витягуємо регіон Документация ПЕРЕД парсингом процедур (v2.14.0+)
            documentation = splitter.extract_documentation_region()
            if documentation:
                self._documentation_from_handlers = documentation

            # Витягуємо регіон МодульОбъекта ПЕРЕД парсингом процедур (v2.66.0+)
            object_module_code = splitter.extract_object_module_region()
            if object_module_code:
                self._object_module_from_handlers = object_module_code

            # Витягуємо модульні змінні ПЕРЕД парсингом процедур (v2.73.0+)
            module_variables = splitter.extract_module_variables()
            if module_variables:
                self._module_variables_from_handlers = module_variables

            # Витягуємо процедури
            procedures = splitter.extract_procedures()

            # Нормалізуємо escape-послідовності якщо увімкнено (v2.72.0+)
            if self._normalize_escapes:
                procedures = {
                    name: self._normalize_bsl_escape_sequences(code)
                    for name, code in procedures.items()
                }
            else:
                # Детекція проблеми та підказка (v2.72.0+)
                # Pattern: literal backslash + n + optional spaces + |
                escape_pattern = re.escape('\\') + r'n\s*' + re.escape('|')
                handlers_with_escapes = [
                    name for name, code in procedures.items()
                    if re.search(escape_pattern, code)
                ]
                if handlers_with_escapes:
                    print(f"⚠️  Виявлено literal \\n в {len(handlers_with_escapes)} handler(s): {', '.join(handlers_with_escapes[:3])}{'...' if len(handlers_with_escapes) > 3 else ''}")
                    print(f"   💡 Використайте --normalize-bsl-escapes для автоматичного виправлення")

            # Зберігаємо в кеш
            self._loaded_handlers = procedures

            print(f"✅ Завантажено {len(procedures)} процедур з {bsl_file.name}")

        except Exception as e:
            print(f"❌ Помилка завантаження BSL файлу: {e}")
            import traceback
            traceback.print_exc()

    def load_form_handlers_file(self, form_name: str, handlers_file: Path) -> Dict[str, str]:
        """
        Завантажує handlers з монолітного BSL файлу для конкретної форми (v2.69.0+)

        Args:
            form_name: Ім'я форми для кешування
            handlers_file: Шлях до BSL файлу з handlers для цієї форми

        Returns:
            Словник {назва_процедури: код}
        """
        from .bsl_splitter import BSLSplitter

        # Перевіряємо кеш
        if form_name in self._form_handlers_cache:
            return self._form_handlers_cache[form_name]

        handlers_file = Path(handlers_file)
        if not handlers_file.exists():
            print(f"❌ BSL файл для форми '{form_name}' не знайдено: {handlers_file}")
            return {}

        try:
            splitter = BSLSplitter(handlers_file)
            procedures = splitter.extract_procedures()

            # Нормалізуємо escape-послідовності якщо увімкнено (v2.72.0+)
            if self._normalize_escapes:
                procedures = {
                    name: self._normalize_bsl_escape_sequences(code)
                    for name, code in procedures.items()
                }
            else:
                # Детекція проблеми та підказка
                escape_pattern = re.escape('\\') + r'n\s*' + re.escape('|')
                handlers_with_escapes = [
                    name for name, code in procedures.items()
                    if re.search(escape_pattern, code)
                ]
                if handlers_with_escapes:
                    print(f"  ⚠️  Виявлено literal \\n в {len(handlers_with_escapes)} handler(s) форми '{form_name}'")
                    print(f"     💡 Використайте --normalize-bsl-escapes")

            self._form_handlers_cache[form_name] = procedures
            print(f"  📦 Завантажено {len(procedures)} handlers з {handlers_file.name} для форми '{form_name}'")
            return procedures
        except Exception as e:
            print(f"❌ Помилка завантаження handlers для форми '{form_name}': {e}")
            return {}

    def load_handler(
        self,
        handler_name: str,
        handlers_dir: Optional[Path] = None,
        form_handlers: Optional[Dict[str, str]] = None,
    ) -> Optional[str]:
        """
        Завантажує BSL код з файлу або кешу

        Пріоритет пошуку (v2.69.0+):
        1. Per-form handlers (form_handlers) - якщо форма має свій handlers_file
        2. Глобальний кеш (_loaded_handlers) - з глобального handlers_file
        3. Директорія (handlers_dir) - окремі файли

        Args:
            handler_name: Ім'я обробника (без розширення)
            handlers_dir: Опціональна директорія для завантаження (для per-form handlers)
            form_handlers: Опціональний словник handlers для конкретної форми (v2.69.0+)

        Returns:
            BSL код або None якщо не знайдено
        """
        # 1. Перевіряємо per-form handlers (пріоритет)
        if form_handlers and handler_name in form_handlers:
            return form_handlers[handler_name]

        # 2. Перевіряємо глобальний кеш (для handlers_file підходу)
        if handler_name in self._loaded_handlers:
            return self._loaded_handlers[handler_name]

        # Визначаємо директорію: per-form або глобальна
        search_dir = Path(handlers_dir) if handlers_dir else self.handlers_dir

        # Якщо в кеші немає і немає директорії - нічого не знайдено
        if not search_dir:
            return None

        # Шукаємо окремий файл
        handler_file = search_dir / f"{handler_name}.bsl"

        if not handler_file.exists():
            print(f"⚠️  BSL файл не знайдено: {handler_file}")
            return None

        try:
            # Читаємо з UTF-8 BOM (стандарт для BSL файлів)
            code = handler_file.read_text(encoding="utf-8-sig").strip()
            self._loaded_handlers[handler_name] = code
            return code
        except Exception as e:
            import traceback
            print(f"❌ Помилка читання {handler_file}: {e}")
            traceback.print_exc()
            return None

    def wrap_handler_code(
        self,
        code: str,
        handler_name: str,
        event_signature: dict,
    ) -> str:
        """
        Обгортає BSL код у процедурну сигнатуру

        Args:
            code: Тіло BSL процедури
            handler_name: Ім'я обробника
            event_signature: Сигнатура події з constants.py

        Returns:
            Повний BSL код з сигнатурою
        """
        # Якщо код вже має сигнатуру (Процедура, Функция, &), повертаємо як є
        if self.has_bsl_signature(code):
            return code

        # Інакше обгортаємо в шаблон
        return EVENT_HANDLER_TEMPLATE.format(
            directive=event_signature["directive"],
            handler_name=handler_name,
            params=event_signature["params"],
            body=self._indent_code(code),
        )

    def wrap_server_call_handler(
        self,
        client_code: str,
        server_code: str,
        client_handler: str,
        server_handler: str,
        params: str,
    ) -> str:
        """
        Обгортає клієнт-серверну пару обробників

        Args:
            client_code: Клієнтський BSL код
            server_code: Серверний BSL код
            client_handler: Ім'я клієнтського обробника
            server_handler: Ім'я серверного обробника
            params: Параметри клієнтської процедури

        Returns:
            Обидва обробники з сигнатурами
        """
        # Якщо є власний клієнтський код, використовуємо його
        if client_code:
            # Перевіряємо чи код вже має сигнатуру
            if self.has_bsl_signature(client_code):
                client_proc = client_code
            else:
                client_proc = EVENT_HANDLER_TEMPLATE.format(
                    directive="НаКлиенте",
                    handler_name=client_handler,
                    params=params,
                    body=self._indent_code(client_code),
                )
        else:
            # Інакше генеруємо виклик серверної процедури
            client_proc = SERVER_CALL_TEMPLATE.format(
                client_handler=client_handler,
                params=params,
                server_handler=server_handler,
            )

        # Серверна процедура
        if server_code:
            # Якщо серверний код вже має сигнатуру, використовуємо як є
            if self.has_bsl_signature(server_code):
                server_proc = server_code
            else:
                # Інакше обгортаємо в шаблон
                server_body = self._indent_code(server_code)
                server_proc = SERVER_PROCEDURE_TEMPLATE.format(
                    server_handler=server_handler
                ).replace(
                    "// Вставить содержимое обработчика.",
                    server_body
                )
        else:
            # Якщо немає серверного коду, генеруємо заглушку
            server_proc = SERVER_PROCEDURE_TEMPLATE.format(
                server_handler=server_handler
            )

        return f"{client_proc}\n\n{server_proc}"

    def wrap_command_handler(
        self,
        code: str,
        handler_name: str,
        is_client: bool = True,
    ) -> str:
        """
        Обгортає обробник команди

        Args:
            code: Тіло BSL процедури
            handler_name: Ім'я обробника
            is_client: Чи це клієнтська процедура

        Returns:
            Повний BSL код
        """
        # Якщо код вже має сигнатуру, повертаємо як є
        if self.has_bsl_signature(code):
            return code

        directive = "НаКлиенте" if is_client else "НаСервере"
        return EVENT_HANDLER_TEMPLATE.format(
            directive=directive,
            handler_name=handler_name,
            params="Команда",
            body=self._indent_code(code),
        )

    def _extract_and_store_helpers(
        self,
        code: str,
        handler_name: str,
        form,
    ) -> str:
        """
        Універсальний метод для витягування хелперів з коду та збереження в form.helper_procedures

        Args:
            code: BSL код
            handler_name: Ім'я обробника
            form: Form об'єкт

        Returns:
            Основний код без хелперів
        """
        main_code, helpers = self._extract_main_and_helpers(code, handler_name)
        if helpers:
            form.helper_procedures.update(helpers)
        return main_code

    def _load_server_handler(
        self,
        handler_name: str,
        suffix: str,
        handlers_dir: Optional[Path],
        used_handlers: set,
        form_handlers: Optional[Dict[str, str]] = None,
    ) -> Optional[str]:
        """
        Універсальний метод для завантаження серверного обробника

        Args:
            handler_name: Базова назва обробника
            suffix: Суфікс для серверного обробника (напр. "НаСервере")
            handlers_dir: Директорія з handlers
            used_handlers: Множина використаних handlers
            form_handlers: Опціональний словник handlers для форми (v2.69.0+)

        Returns:
            BSL код серверного обробника або None
        """
        server_handler = f"{handler_name}{suffix}"
        server_code = self.load_handler(server_handler, handlers_dir, form_handlers)
        if server_code:
            used_handlers.add(server_handler)
        return server_code

    def _wrap_with_signature(
        self,
        code: str,
        handler_name: str,
        directive: str,
        params: str = "",
    ) -> str:
        """
        Універсальний метод для обгортання коду в сигнатуру процедури

        Якщо код вже має сигнатуру - повертає як є,
        інакше обгортає в EVENT_HANDLER_TEMPLATE

        Args:
            code: BSL код
            handler_name: Ім'я обробника
            directive: Директива (&НаСервере, &НаКлиенте)
            params: Параметри процедури

        Returns:
            Код з сигнатурою
        """
        if self.has_bsl_signature(code):
            return code

        return EVENT_HANDLER_TEMPLATE.format(
            directive=directive,
            handler_name=handler_name,
            params=params,
            body=self._indent_code(code),
        )

    def inject_form_handlers(
        self,
        form,
        handlers_dir: Optional[Path] = None,
        form_handlers: Optional[Dict[str, str]] = None,
    ) -> set:
        """
        Інжектує BSL код для однієї форми (Form об'єкт)

        Args:
            form: Form об'єкт з processor.forms
            handlers_dir: Опціональна директорія з handlers для цієї форми
            form_handlers: Опціональний словник handlers для цієї форми (v2.69.0+)

        Returns:
            Множина використаних handler names (для відстеження)
        """
        used_handlers = set()

        # 1. Інжектуємо обробники подій форми
        for event_name, handler_name in list(form.events.items()):
            # Завантажуємо BSL код з per-form handlers або директорії
            code = self.load_handler(handler_name, handlers_dir, form_handlers)

            if code:
                used_handlers.add(handler_name)

                # Зберігаємо код в form.events_bsl для генерації
                if not hasattr(form, "events_bsl"):
                    form.events_bsl = {}

                event_sig = FORM_EVENT_SIGNATURES.get(event_name)
                if not event_sig:
                    print(f"⚠️  Невідома подія форми: {event_name}")
                    continue

                # Перевіряємо чи потрібен серверний виклик
                if "server_call" in event_sig:
                    server_handler = event_sig["server_call"]
                    server_code = self.load_handler(server_handler, handlers_dir, form_handlers)
                    if server_code:
                        used_handlers.add(server_handler)

                    # Витягуємо хелпери з клієнтського та серверного коду
                    main_client_code = self._extract_and_store_helpers(code, handler_name, form)
                    main_server_code = self._extract_and_store_helpers(server_code, server_handler, form) if server_code else ""

                    wrapped = self.wrap_server_call_handler(
                        client_code=main_client_code,
                        server_code=main_server_code,
                        client_handler=handler_name,
                        server_handler=server_handler,
                        params=event_sig["params"],
                    )
                else:
                    # Витягуємо хелпери
                    main_code = self._extract_and_store_helpers(code, handler_name, form)
                    wrapped = self.wrap_handler_code(main_code, handler_name, event_sig)

                form.events_bsl[handler_name] = wrapped

        # 2. Інжектуємо обробники команд форми
        for cmd in form.commands:
            # Завантажуємо основний обробник
            code = self.load_handler(cmd.action, handlers_dir, form_handlers)

            if code:
                used_handlers.add(cmd.action)

                # Витягуємо основну частину та хелпери
                main_code = self._extract_and_store_helpers(code, cmd.action, form)

                # Обгортаємо тільки основну частину
                wrapped = self.wrap_command_handler(main_code, cmd.action, is_client=True)

                # Зберігаємо в команді
                cmd.bsl_code = wrapped

                # Перевіряємо чи є серверна частина (суфікс НаСервере)
                server_code = self._load_server_handler(cmd.action, "НаСервере", handlers_dir, used_handlers, form_handlers)

                if server_code:
                    # Витягуємо основну частину та хелпери з серверної частини
                    main_server_code = self._extract_and_store_helpers(server_code, f"{cmd.action}НаСервере", form)

                    # Обгортаємо серверну процедуру
                    server_wrapped = self._wrap_with_signature(main_server_code, f"{cmd.action}НаСервере", "НаСервере", "")

                    # Додаємо серверний обробник
                    cmd.bsl_code = f"{cmd.bsl_code}\n\n{server_wrapped}"

        # 3. Інжектуємо обробники подій елементів форми
        for elem in form.elements:
            if not elem.event_handlers:
                continue

            for event_name, handler_name in elem.event_handlers.items():
                code = self.load_handler(handler_name, handlers_dir, form_handlers)

                if code:
                    used_handlers.add(handler_name)

                    event_sig = ELEMENT_EVENT_SIGNATURES.get(event_name)
                    if not event_sig:
                        print(f"⚠️  Невідома подія елемента: {event_name}")
                        continue

                    # Перевіряємо чи потрібен серверний виклик
                    if "server_call_suffix" in event_sig:
                        server_handler = f"{handler_name}{event_sig['server_call_suffix']}"
                        server_code = self._load_server_handler(handler_name, event_sig['server_call_suffix'], handlers_dir, used_handlers, form_handlers)

                        # Витягуємо хелпери з клієнтського та серверного коду
                        main_client_code = self._extract_and_store_helpers(code, handler_name, form)
                        main_server_code = self._extract_and_store_helpers(server_code, server_handler, form) if server_code else ""

                        # Використовуємо wrap_server_call_handler для правильної обгортки
                        wrapped = self.wrap_server_call_handler(
                            client_code=main_client_code,
                            server_code=main_server_code,
                            client_handler=handler_name,
                            server_handler=server_handler,
                            params=event_sig["params"],
                        )
                    else:
                        # Витягуємо хелпери
                        main_code = self._extract_and_store_helpers(code, handler_name, form)
                        wrapped = self.wrap_handler_code(main_code, handler_name, event_sig)

                    # Зберігаємо в елементі
                    if not hasattr(elem, "bsl_code"):
                        elem.bsl_code = {}
                    elem.bsl_code[event_name] = wrapped

        # Об'єднуємо документацію з файлу та регіону (v2.14.0+)
        documentation_parts = []
        if form.documentation:  # З файлу (завантажено в yaml_parser)
            documentation_parts.append(form.documentation)
        if self._documentation_from_handlers:  # З регіону в handlers.bsl
            documentation_parts.append(self._documentation_from_handlers)

        if documentation_parts:
            form.documentation = '\n\n'.join(documentation_parts)
            print(f"📚 Об'єднано документацію для форми {form.name} ({len(form.documentation)} символів)")

        # Передаємо модульні змінні у форму (v2.73.0+)
        if self._module_variables_from_handlers:
            form.module_variables = self._module_variables_from_handlers

        return used_handlers

    def inject_forms_handlers(self, processor) -> set:
        """
        Інжектує BSL код для всіх форм з processor.forms

        Args:
            processor: Processor об'єкт з списком forms

        Returns:
            Множина використаних handler names
        """
        # Пропускаємо якщо немає форм
        if not processor.forms:
            return set()

        # Перевіряємо чи є хоча б у однієї форми власний handlers_dir або handlers_file (v2.69.0+)
        has_any_handlers = (self.handlers_dir or self._loaded_handlers or
                           any(form.handlers_dir or form.handlers_file for form in processor.forms))

        if not has_any_handlers:
            # Немає жодних джерел для handlers
            return set()

        total_used_handlers = set()
        forms_with_own_handlers = []  # Форми з власним handlers_file

        for form in processor.forms:
            # Визначаємо handlers_dir для цієї форми
            form_handlers_dir = None
            if form.handlers_dir:
                # Per-form handlers directory
                form_handlers_dir = Path(form.handlers_dir)
                # Якщо шлях відносний, робимо його відносно глобального handlers_dir
                if not form_handlers_dir.is_absolute() and self.handlers_dir:
                    form_handlers_dir = self.handlers_dir / form.handlers_dir

            # Завантажуємо per-form handlers_file (v2.69.0+)
            form_handlers = None
            if form.handlers_file:
                form_handlers = self.load_form_handlers_file(form.name, Path(form.handlers_file))
                if form_handlers:
                    forms_with_own_handlers.append(form)

            # Інжектуємо handlers для цієї форми
            used_handlers = self.inject_form_handlers(form, form_handlers_dir, form_handlers)
            total_used_handlers.update(used_handlers)

            # Інжектуємо standalone helpers для форми з власним handlers_file
            if form_handlers:
                self._inject_standalone_helpers_for_form(form, used_handlers, form_handlers)

        if total_used_handlers:
            print(f"✅ BSL handlers інжектовано для {len(processor.forms)} форм: {len(total_used_handlers)} обробників")

        return total_used_handlers

    def _inject_standalone_helpers(self, form, used_handlers: set) -> None:
        """
        Інжектує standalone helpers - процедури/функції, які не прив'язані до подій/команд,
        але є в handlers_file

        Args:
            form: Form об'єкт куди додаємо helpers
            used_handlers: Множина вже використаних handler names
        """
        # Знаходимо всі процедури, які НЕ використані як handlers
        standalone_helpers = {}
        for proc_name, proc_code in self._loaded_handlers.items():
            if proc_name not in used_handlers:
                standalone_helpers[proc_name] = proc_code

        if standalone_helpers:
            # Додаємо їх у helper_procedures форми
            form.helper_procedures.update(standalone_helpers)
            print(f"✅ Додано {len(standalone_helpers)} standalone helpers: {', '.join(list(standalone_helpers.keys())[:5])}{'...' if len(standalone_helpers) > 5 else ''}")

    def _inject_standalone_helpers_for_form(
        self,
        form,
        used_handlers: set,
        form_handlers: Dict[str, str],
    ) -> None:
        """
        Інжектує standalone helpers з per-form handlers_file (v2.69.0+)

        Args:
            form: Form об'єкт куди додаємо helpers
            used_handlers: Множина вже використаних handler names
            form_handlers: Словник handlers для цієї форми
        """
        # Знаходимо всі процедури з form_handlers, які НЕ використані як handlers
        standalone_helpers = {}
        for proc_name, proc_code in form_handlers.items():
            if proc_name not in used_handlers:
                standalone_helpers[proc_name] = proc_code

        if standalone_helpers:
            # Додаємо їх у helper_procedures форми
            form.helper_procedures.update(standalone_helpers)
            print(f"  ✅ Додано {len(standalone_helpers)} standalone helpers для '{form.name}'")

    def inject_long_operation_handlers(self, processor) -> set:
        """
        Генерує wrapper handlers для long operation commands.

        Для кожної команди з long_operation=True:
        1. Генерує client button handler (entry point)
        2. Генерує server job starter (calls ДлительныеОперации.ВыполнитьВФоне)
        3. Генерує client completion handler (processes result)
        4. Завантажує user-provided background job handler (НаСервере) - ОБОВ'ЯЗКОВО

        User пише ТІЛЬКИ: CommandНаСервере.bsl (business logic)
        Generator створює: CommandКнопка, CommandВФоне, CommandЗавершение

        Args:
            processor: Processor об'єкт

        Raises:
            FileNotFoundError: якщо НаСервере handler не знайдено

        v3.0.0+
        """
        # Збираємо всі long operation команди з усіх форм
        long_operation_commands = []
        for form in processor.forms:
            for cmd in form.commands:
                if cmd.long_operation:
                    long_operation_commands.append((form, cmd))

        if not long_operation_commands:
            return set()  # Немає long operations - повертаємо порожній set

        print(f"🔄 Генерація long operation handlers ({len(long_operation_commands)} команд)...")

        # Відстежуємо використані handlers щоб не додавати їх у standalone helpers
        used_handlers = set()

        for form, cmd in long_operation_commands:
            settings = cmd.long_operation_settings
            if settings is None:
                # Автоматично створено в Command.__post_init__
                from .models import LongOperationSettings
                settings = LongOperationSettings()

            # 0. Try to load OPTIONAL handlers (convention-based)
            validate_handler_name = f'{cmd.name}ПроверкаПередЗапуском'
            validate_code = self.load_handler(validate_handler_name, form.handlers_dir or self.handlers_dir)

            complete_handler_name = f'{cmd.name}ОбработкаРезультата'
            complete_code = self.load_handler(complete_handler_name, form.handlers_dir or self.handlers_dir)

            # 1. Prepare waiting parameters code (used in client button handler)
            waiting_params_parts = []
            if settings.show_progress:
                waiting_params_parts.append(f'\tПараметрыОжидания.ВыводитьОкноОжидания = Истина;')
                waiting_params_parts.append(f'\tПараметрыОжидания.ТекстСообщения = "{settings.progress_message}";')
            else:
                waiting_params_parts.append(f'\tПараметрыОжидания.ВыводитьОкноОжидания = Ложь;')

            if settings.output_messages:
                waiting_params_parts.append(f'\tПараметрыОжидания.ВыводитьСообщения = Истина;')

            if settings.output_progress:
                waiting_params_parts.append(f'\tПараметрыОжидания.ВыводитьПрогрессВыполнения = Истина;')

            waiting_params_code = "\n".join(waiting_params_parts)

            # 2. Prepare validation call (if exists)
            validation_call = ""
            if validate_code:
                validation_call = f"""Если НЕ {cmd.name}ПроверкаПередЗапуском() Тогда
\t\tВозврат;
\tКонецЕсли;
\t"""

            # 3. Generate client button handler (uses template)
            client_button_code = LONG_OPERATION_CLIENT_BUTTON_TEMPLATE.format(
                command_name=cmd.name,
                validation_call=validation_call,
                waiting_params_code=waiting_params_code
            )

            # 4. Prepare parameters code for server starter
            if settings.use_additional_parameters:
                parameters_code = """// Передаем все атрибуты формы
\tДля Каждого Реквизит Из ПолучитьРеквизиты() Цикл
\t\tПараметрыЗадания.Вставить(Реквизит.Имя, ЭтотОбъект[Реквизит.Имя]);
\tКонецЦикла;"""
            else:
                parameters_code = ""  # Empty - user can access parameters in НаСервере if needed

            # Wait initial code
            if settings.wait_completion_initial > 0:
                wait_initial_code = f"\tПараметрыВыполнения.ОжидатьЗавершение = {settings.wait_completion_initial};"
            else:
                wait_initial_code = ""

            # 5. Generate server starter function (returns background job result)
            server_start_code = LONG_OPERATION_SERVER_START_TEMPLATE.format(
                command_name=cmd.name,
                parameters_code=parameters_code,
                job_title=cmd.title_ru,
                wait_initial_code=wait_initial_code,
                processor_name=processor.name
            )

            # 3. Generate client completion handler with optional result processing
            completion_parts = [
                '&НаКлиенте',
                f'Процедура {cmd.name}Завершение(Результат, ДополнительныеПараметры) Экспорт',
                '\t',
                '\t// Проверка отмены операции',
                '\tЕсли Результат = Неопределено Тогда',
                '\t\tСообщить("Операция отменена пользователем");',
                '\t\tВозврат;',
                '\tКонецЕсли;',
                '\t',
                '\t// Проверка ошибок',
                '\tЕсли Результат.Статус = "Ошибка" Тогда',
                '\t\tПоказатьПредупреждение(, Результат.КраткоеПредставлениеОшибки);',
                '\t\tВозврат;',
                '\tКонецЕсли;',
                '\t'
            ]

            if complete_code:
                # Add custom result processing if handler exists
                completion_parts.extend([
                    '\t// Получение результата из хранилища',
                    '\tРезультатОперации = ПолучитьИзВременногоХранилища(Результат.АдресРезультата);',
                    '\t',
                    f'\t{cmd.name}ОбработкаРезультата(РезультатОперации);',
                    '\t'
                ])

            completion_parts.extend([
                '\tСообщить("Операция успешно завершена!");',
                '\t',
                'КонецПроцедуры'
            ])

            completion_handler_code = '\n'.join(completion_parts)

            # 4. Load user-provided НаСервере handler (REQUIRED!)
            server_handler_name = f'{cmd.name}НаСервере'
            server_handler_code = self.load_handler(server_handler_name, form.handlers_dir or self.handlers_dir)

            if not server_handler_code:
                raise FileNotFoundError(
                    f"❌ Long operation command '{cmd.name}' requires handler file: {server_handler_name}.bsl\n\n"
                    f"Create this file with the following signature:\n"
                    f"&НаСервере\n"
                    f"Процедура {server_handler_name}(Параметры, АдресРезультата) Экспорт\n"
                    f"    // Your business logic here\n"
                    f"    // Store result: ПоместитьВоВременноеХранилище(Результат, АдресРезультата);\n"
                    f"КонецПроцедуры"
                )

            # Store all handlers in processor (4 wrappers + optional user handlers)
            processor.long_operation_handlers[f'{cmd.name}Кнопка'] = client_button_code
            processor.long_operation_handlers[f'{cmd.name}ЗапуститьВФоне'] = server_start_code
            processor.long_operation_handlers[f'{cmd.name}Завершение'] = completion_handler_code
            processor.long_operation_handlers[f'{cmd.name}НаСервере'] = server_handler_code

            # Mark НаСервере as used so it's not added to standalone helpers
            used_handlers.add(server_handler_name)

            # Store optional handlers if they exist
            handler_count = 4  # Кнопка, ЗапуститьВФoне, Завершение, НаСервере
            optional_handlers = []

            if validate_code:
                processor.long_operation_handlers[validate_handler_name] = validate_code
                used_handlers.add(validate_handler_name)
                handler_count += 1
                optional_handlers.append('ПроверкаПередЗапуском')

            if complete_code:
                processor.long_operation_handlers[complete_handler_name] = complete_code
                used_handlers.add(complete_handler_name)
                handler_count += 1
                optional_handlers.append('ОбработкаРезультата')

            # Print summary
            optional_str = f" + {', '.join(optional_handlers)}" if optional_handlers else ""
            print(f"   ✅ {cmd.name}: {handler_count} handlers (Кнопка, ЗапуститьВФoне, Завершение, НаСервере{optional_str})")

        return used_handlers

    def inject_all_handlers(self, processor) -> None:
        """
        Інжектує всі BSL обробники в Processor

        Args:
            processor: Processor об'єкт
        """
        # Перевіряємо чи є форми
        if not processor.forms:
            print("⚠️  Немає форм для інжекції BSL handlers")
            return

        # Перевіряємо чи є будь-які джерела handlers (включно з per-form handlers_file v2.69.0+)
        has_any_handlers = (self.handlers_dir or self._loaded_handlers or
                           any(form.handlers_dir or form.handlers_file for form in processor.forms))

        if not has_any_handlers:
            print("⚠️  Немає BSL handlers для інжекції")
            return

        # Виводимо інформацію про джерело handlers
        if self._loaded_handlers:
            print(f"📦 Використання попередньо завантажених BSL handlers...")
        elif self.handlers_dir:
            print(f"📦 Завантаження BSL handlers з {self.handlers_dir}...")
        elif any(form.handlers_file for form in processor.forms):
            # Є per-form handlers_file (v2.69.0+)
            print(f"📦 Завантаження BSL handlers з per-form файлів...")
        else:
            # Є per-form handlers_dir
            print(f"📦 Завантаження BSL handlers з form-specific директорій...")

        # Інжектуємо handlers для кожної форми окремо
        total_used_handlers = self.inject_forms_handlers(processor)

        # Генеруємо long operation handlers (v3.0.0+)
        long_op_used_handlers = self.inject_long_operation_handlers(processor)
        total_used_handlers.update(long_op_used_handlers)

        # Додаємо невикористані процедури з глобального handlers_file як standalone helpers
        # Тільки для форм БЕЗ власного handlers_file (v2.69.0+)
        if self._loaded_handlers and processor.forms:
            forms_without_own_handlers = [f for f in processor.forms if not f.handlers_file]
            if forms_without_own_handlers:
                self._inject_standalone_helpers(forms_without_own_handlers[0], total_used_handlers)

    def _split_procedures(self, code: str) -> Tuple[str, Dict[str, str]]:
        """
        Розділяє BSL код на preamble (код до першої процедури) та процедури/функції

        Args:
            code: BSL код з декількома процедурами/функціями

        Returns:
            Tuple (preamble, procedures):
                - preamble: Код до першої процедури (може бути тілом основного обробника)
                - procedures: Словник {назва_процедури: повний_код_процедури}
        """
        procedures = {}
        preamble_lines = []  # Код до першої процедури
        current_proc_name = None
        current_proc_lines = []
        depth = 0
        found_first_procedure = False  # Прапорець чи знайшли першу процедуру

        # Паттерни для визначення процедур/функцій
        proc_start_pattern = re.compile(
            r'^\s*(?:&\w+\s+)?(?:Процедура|Функция|Procedure|Function|Асинх|Async)\s+(\w+)',
            re.IGNORECASE
        )
        proc_end_pattern = re.compile(
            r'^\s*(?:КонецПроцедуры|КонецФункции|EndProcedure|EndFunction)',
            re.IGNORECASE
        )

        lines = code.split('\n')

        # Паттерн для виявлення директив (&НаСервере, &НаКлиенте тощо) на окремому рядку
        directive_pattern = re.compile(r'^\s*&\w+\s*$', re.IGNORECASE)

        for i, line in enumerate(lines):
            # Перевіряємо початок процедури/функції
            match = proc_start_pattern.match(line)
            if match and depth == 0:
                # Зберігаємо попередню процедуру (якщо є)
                if current_proc_name and current_proc_lines:
                    procedures[current_proc_name] = '\n'.join(current_proc_lines)

                # Позначаємо що знайшли першу процедуру
                found_first_procedure = True

                # Перевіряємо чи попередній рядок містить директиву
                # Якщо так - включаємо його в процедуру, видаляємо з preamble
                if preamble_lines and directive_pattern.match(preamble_lines[-1]):
                    directive_line = preamble_lines.pop()
                    current_proc_lines = [directive_line, line]
                else:
                    current_proc_lines = [line]

                # Починаємо нову процедуру
                current_proc_name = match.group(1)
                depth = 1
                continue

            # Якщо ще не знайшли жодної процедури - це preamble
            if not found_first_procedure:
                preamble_lines.append(line)
                continue

            # Якщо ми всередині процедури
            if current_proc_name:
                current_proc_lines.append(line)

                # Перевіряємо кінець процедури
                if proc_end_pattern.match(line):
                    depth -= 1
                    if depth == 0:
                        # Процедура завершена
                        procedures[current_proc_name] = '\n'.join(current_proc_lines)
                        current_proc_name = None
                        current_proc_lines = []
                # Рахуємо вкладені процедури (хоча в BSL рідко зустрічається)
                elif proc_start_pattern.match(line):
                    depth += 1

        # Зберігаємо останню процедуру (якщо не завершена)
        if current_proc_name and current_proc_lines:
            procedures[current_proc_name] = '\n'.join(current_proc_lines)

        # Очищаємо preamble від кінцевих коментарів та порожніх рядків
        # які є роздільниками між основним кодом та хелперами
        while preamble_lines:
            last_line = preamble_lines[-1].strip()
            # Видаляємо порожні рядки, коментарі та роздільники
            if not last_line or last_line.startswith('//') or '======' in last_line:
                preamble_lines.pop()
            else:
                break

        # Формуємо preamble (прибираємо зайві порожні рядки на початку/кінці)
        preamble = '\n'.join(preamble_lines).strip()

        return preamble, procedures

    def _extract_main_and_helpers(self, code: str, handler_name: str) -> Tuple[str, Dict[str, str]]:
        """
        Розділяє код на основну частину та хелперні функції

        Підтримує два формати BSL файлів:
        1. Тільки тіло процедури (без сигнатури) - повертає як є
        2. Тіло + хелперні функції з сигнатурами - розділяє на main body та helpers

        Args:
            code: BSL код (може містити декілька процедур/функцій)
            handler_name: Ім'я основного обробника

        Returns:
            Tuple (main_code, helpers_dict):
                - main_code: Код основного обробника (тіло або повна процедура)
                - helpers_dict: Словник хелперних функцій {назва: код}
        """
        # Завжди пробуємо розділити код на preamble та процедури
        preamble, procedures = self._split_procedures(code)

        # Випадок 1: Є preamble (код до першої процедури)
        # Це означає що файл має структуру: тіло + хелперні функції
        if preamble:
            # Preamble - це main body (тіло основного обробника)
            # Всі процедури з сигнатурами - це helpers
            return preamble, procedures

        # Випадок 2: Немає preamble, але є процедури з сигнатурами
        if procedures:
            # Якщо тільки одна процедура - це основна, немає хелперів
            if len(procedures) == 1:
                # Повертаємо код як є (вже має сигнатуру)
                proc_code = list(procedures.values())[0]
                return proc_code, {}

            # Якщо кілька процедур - шукаємо основну за ім'ям handler_name
            main_proc_code = None
            helpers = {}

            for proc_name, proc_code in procedures.items():
                # Перевіряємо чи це основна процедура
                if (proc_name == handler_name or
                    handler_name.endswith(proc_name) or
                    proc_name.startswith(handler_name)):
                    main_proc_code = proc_code
                else:
                    helpers[proc_name] = proc_code

            # Якщо не знайшли основну за ім'ям - перша процедура є основною
            if main_proc_code is None:
                first_name = list(procedures.keys())[0]
                main_proc_code = procedures[first_name]
                # Видаляємо з хелперів (якщо раптом додали)
                helpers.pop(first_name, None)

            return main_proc_code, helpers

        # Випадок 3: Немає ні preamble, ні процедур - це тільки тіло
        # (код без жодних сигнатур процедур/функцій)
        return code, {}

    @staticmethod
    def _indent_code(code: str, indent: str = "\t") -> str:
        """
        Додає відступи до BSL коду

        Args:
            code: BSL код
            indent: Символ відступу (за замовчуванням \t)

        Returns:
            Код з відступами
        """
        lines = code.split("\n")
        return "\n".join(f"{indent}{line}" if line.strip() else line for line in lines)
