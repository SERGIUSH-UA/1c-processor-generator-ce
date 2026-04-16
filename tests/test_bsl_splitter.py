"""
Unit тести для bsl_splitter.py - extract_module_variables()
"""

import pytest
from pathlib import Path
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

import importlib
bsl_splitter_module = importlib.import_module("1c_processor_generator.bsl_splitter")

BSLSplitter = bsl_splitter_module.BSLSplitter


class TestExtractModuleVariables:
    """Тести для extract_module_variables()"""

    def _create_temp_bsl(self, content: str) -> Path:
        """Створює тимчасовий BSL файл з контентом"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.bsl', delete=False, encoding='utf-8-sig') as f:
            f.write(content)
            return Path(f.name)

    def test_simple_variable(self):
        """Проста декларація Перем"""
        content = """Перем МояЗмінна;

&НаКлиенте
Процедура Тест(Команда)
КонецПроцедуры
"""
        bsl_file = self._create_temp_bsl(content)
        try:
            splitter = BSLSplitter(bsl_file)
            module_vars = splitter.extract_module_variables()

            assert module_vars is not None
            assert "Перем МояЗмінна;" in module_vars
        finally:
            bsl_file.unlink()

    def test_multiple_variables_single_line(self):
        """Кілька змінних в одній декларації"""
        content = """Перем Var1, Var2, Var3;

&НаКлиенте
Процедура Тест(Команда)
КонецПроцедуры
"""
        bsl_file = self._create_temp_bsl(content)
        try:
            splitter = BSLSplitter(bsl_file)
            module_vars = splitter.extract_module_variables()

            assert module_vars is not None
            assert "Перем Var1, Var2, Var3;" in module_vars
        finally:
            bsl_file.unlink()

    def test_variable_with_client_directive(self):
        """Змінна з директивою &НаКлиенте"""
        content = """&НаКлиенте
Перем КлієнтськийКеш;

&НаКлиенте
Процедура Тест(Команда)
КонецПроцедуры
"""
        bsl_file = self._create_temp_bsl(content)
        try:
            splitter = BSLSplitter(bsl_file)
            module_vars = splitter.extract_module_variables()

            assert module_vars is not None
            assert "&НаКлиенте" in module_vars
            assert "Перем КлієнтськийКеш;" in module_vars
        finally:
            bsl_file.unlink()

    def test_variable_with_server_directive(self):
        """Змінна з директивою &НаСервере"""
        content = """&НаСервере
Перем СерверныйКеш;

&НаСервере
Процедура Тест()
КонецПроцедуры
"""
        bsl_file = self._create_temp_bsl(content)
        try:
            splitter = BSLSplitter(bsl_file)
            module_vars = splitter.extract_module_variables()

            assert module_vars is not None
            assert "&НаСервере" in module_vars
            assert "Перем СерверныйКеш;" in module_vars
        finally:
            bsl_file.unlink()

    def test_multiple_variable_declarations(self):
        """Кілька окремих декларацій Перем"""
        content = """&НаКлиенте
Перем Направление, Змейка;

&НаСервере
Перем СерверныйКеш;

Перем БезДирективи;

&НаКлиенте
Процедура Тест(Команда)
КонецПроцедуры
"""
        bsl_file = self._create_temp_bsl(content)
        try:
            splitter = BSLSplitter(bsl_file)
            module_vars = splitter.extract_module_variables()

            assert module_vars is not None
            assert "Перем Направление, Змейка;" in module_vars
            assert "Перем СерверныйКеш;" in module_vars
            assert "Перем БезДирективи;" in module_vars
        finally:
            bsl_file.unlink()

    def test_variable_with_export(self):
        """Змінна з Экспорт"""
        content = """Перем ПараметрыПриложения Экспорт;

&НаКлиенте
Процедура Тест(Команда)
КонецПроцедуры
"""
        bsl_file = self._create_temp_bsl(content)
        try:
            splitter = BSLSplitter(bsl_file)
            module_vars = splitter.extract_module_variables()

            assert module_vars is not None
            assert "Перем ПараметрыПриложения Экспорт;" in module_vars
        finally:
            bsl_file.unlink()

    def test_variable_with_inline_comment(self):
        """Змінна з inline коментарем"""
        content = """Перем мПериод Экспорт; // Период движений

&НаКлиенте
Процедура Тест(Команда)
КонецПроцедуры
"""
        bsl_file = self._create_temp_bsl(content)
        try:
            splitter = BSLSplitter(bsl_file)
            module_vars = splitter.extract_module_variables()

            assert module_vars is not None
            assert "Перем мПериод Экспорт;" in module_vars
            # Коментар має бути збережений
            assert "// Период движений" in module_vars
        finally:
            bsl_file.unlink()

    def test_no_module_variables(self):
        """Файл без модульних змінних"""
        content = """&НаКлиенте
Процедура Тест(Команда)
    Перем ЛокальнаЗмінна;  // Це локальна, не модульна
КонецПроцедуры
"""
        bsl_file = self._create_temp_bsl(content)
        try:
            splitter = BSLSplitter(bsl_file)
            module_vars = splitter.extract_module_variables()

            # Локальна змінна всередині процедури НЕ має витягуватись
            assert module_vars is None
        finally:
            bsl_file.unlink()

    def test_procedure_level_variables_not_extracted(self):
        """Локальні змінні всередині процедур НЕ витягуються"""
        content = """Перем МодульнаЗмінна;

&НаКлиенте
Процедура Тест(Команда)
    Перем ЛокальнаЗмінна;
    ЛокальнаЗмінна = 1;
КонецПроцедуры

&НаСервере
Процедура Тест2()
    Перем ІншаЛокальна;
КонецПроцедуры
"""
        bsl_file = self._create_temp_bsl(content)
        try:
            splitter = BSLSplitter(bsl_file)
            module_vars = splitter.extract_module_variables()

            assert module_vars is not None
            assert "Перем МодульнаЗмінна;" in module_vars
            # Локальні змінні НЕ мають бути в результаті
            assert "ЛокальнаЗмінна" not in module_vars
            assert "ІншаЛокальна" not in module_vars
        finally:
            bsl_file.unlink()

    def test_english_var_keyword(self):
        """Англійське ключове слово Var"""
        content = """Var MyVariable;

Procedure Test()
EndProcedure
"""
        bsl_file = self._create_temp_bsl(content)
        try:
            splitter = BSLSplitter(bsl_file)
            module_vars = splitter.extract_module_variables()

            assert module_vars is not None
            assert "Var MyVariable;" in module_vars
        finally:
            bsl_file.unlink()

    def test_variables_removed_from_content(self):
        """Змінні видаляються з content після витягування"""
        content = """Перем МояЗмінна;

&НаКлиенте
Процедура Тест(Команда)
КонецПроцедуры
"""
        bsl_file = self._create_temp_bsl(content)
        try:
            splitter = BSLSplitter(bsl_file)

            # До витягування - Перем є в content
            assert "Перем МояЗмінна;" in splitter.content

            module_vars = splitter.extract_module_variables()

            # Після витягування - Перем НЕ має бути в content
            assert "Перем МояЗмінна;" not in splitter.content
            # Але процедура має залишитись
            assert "Процедура Тест" in splitter.content
        finally:
            bsl_file.unlink()

    def test_extract_procedures_after_variables(self):
        """Процедури коректно витягуються після витягування змінних"""
        content = """&НаКлиенте
Перем Направление, Змейка;

&НаКлиенте
Процедура НачатьИгру(Команда)
    Змейка = Новый Массив;
КонецПроцедуры

&НаКлиенте
Процедура ОстановитьИгру(Команда)
    Сообщить("Стоп");
КонецПроцедуры
"""
        bsl_file = self._create_temp_bsl(content)
        try:
            splitter = BSLSplitter(bsl_file)

            # Спочатку витягуємо змінні
            module_vars = splitter.extract_module_variables()
            assert module_vars is not None

            # Потім витягуємо процедури
            procedures = splitter.extract_procedures()

            assert len(procedures) == 2
            assert "НачатьИгру" in procedures
            assert "ОстановитьИгру" in procedures
            assert "Змейка = Новый Массив;" in procedures["НачатьИгру"]
        finally:
            bsl_file.unlink()


class TestModuleVariablePattern:
    """Тести для MODULE_VARIABLE_PATTERN regex"""

    def test_pattern_matches_simple(self):
        """Простий патерн"""
        import re
        pattern = BSLSplitter.MODULE_VARIABLE_PATTERN

        text = "Перем МояЗмінна;"
        match = pattern.search(text)
        assert match is not None

    def test_pattern_matches_with_directive(self):
        """Патерн з директивою"""
        import re
        pattern = BSLSplitter.MODULE_VARIABLE_PATTERN

        text = "&НаКлиенте\nПерем МояЗмінна;"
        match = pattern.search(text)
        assert match is not None

    def test_pattern_matches_multiple_vars(self):
        """Патерн з кількома змінними"""
        import re
        pattern = BSLSplitter.MODULE_VARIABLE_PATTERN

        text = "Перем Var1, Var2, Var3;"
        match = pattern.search(text)
        assert match is not None

    def test_pattern_matches_with_export(self):
        """Патерн з Экспорт"""
        import re
        pattern = BSLSplitter.MODULE_VARIABLE_PATTERN

        text = "Перем МояЗмінна Экспорт;"
        match = pattern.search(text)
        assert match is not None
