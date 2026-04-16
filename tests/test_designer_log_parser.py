"""
Тести для DesignerLogParser (v2.38.0+)

Покриває:
- Парсинг різних форматів помилок Designer
- Класифікація errors vs warnings
- Edge cases: порожні логи, некоректний формат
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

import importlib
parser_module = importlib.import_module("1c_processor_generator.designer_log_parser")

DesignerLogParser = parser_module.DesignerLogParser
ValidationError = parser_module.ValidationError


class TestValidationError:
    """Тести для dataclass ValidationError"""

    def test_create_validation_error(self):
        """Створення ValidationError"""
        error = ValidationError(
            module="TestModule",
            line=10,
            column=5,
            message="Test message",
            severity="error"
        )
        assert error.module == "TestModule"
        assert error.line == 10
        assert error.column == 5
        assert error.message == "Test message"
        assert error.severity == "error"

    def test_validation_error_str(self):
        """Форматований вивід ValidationError"""
        error = ValidationError(
            module="Module.ObjectModule",
            line=45,
            column=12,
            message="Неизвестный метод",
            severity="error"
        )
        result = str(error)
        assert "Module.ObjectModule" in result
        assert "45" in result
        assert "12" in result
        assert "error" in result
        assert "Неизвестный метод" in result


class TestDesignerLogParser:
    """Тести для DesignerLogParser"""

    def test_parse_russian_format(self):
        """Парсинг формату 'Строка X, Колонка Y: message'"""
        parser = DesignerLogParser()

        log_content = """Модуль объекта обработки "TestProcessor":
Строка 45, Колонка 12: Неизвестный метод "НеіснуючийМетод"
"""
        errors, warnings = parser.parse_log_content(log_content)

        assert len(errors) == 1
        assert errors[0].line == 45
        assert errors[0].column == 12
        assert "Неизвестный метод" in errors[0].message
        assert errors[0].severity == "error"

    def test_parse_path_format(self):
        """Парсинг формату '{Module.Path(line,col)}: message'"""
        parser = DesignerLogParser()

        log_content = """{DataProcessor.Test.Forms.Form.Module(25,8)}: Ожидается символ ';'
"""
        errors, warnings = parser.parse_log_content(log_content)

        assert len(errors) == 1
        assert errors[0].line == 25
        assert errors[0].column == 8
        assert errors[0].module == "DataProcessor.Test.Forms.Form.Module"
        assert "Ожидается" in errors[0].message

    def test_classify_error_keywords(self):
        """Класифікація помилок за ключовими словами"""
        parser = DesignerLogParser()

        # Ключові слова помилок
        error_messages = [
            "Неизвестный метод Test",
            "Unknown identifier X",
            "Переменная не определена",
            "Invalid parameter type",
            "Ожидается выражение",
            "Not found: SomeModule",
        ]

        for msg in error_messages:
            severity = parser._classify_severity(msg)
            assert severity == "error", f"'{msg}' should be classified as error"

    def test_classify_warning(self):
        """Класифікація попереджень"""
        parser = DesignerLogParser()

        # Повідомлення без ключових слів помилок - це warnings
        warning_messages = [
            "Переменная может быть не инициализирована",
            "Рекомендуется использовать КонецЕсли",
            "Variable may be unused",
        ]

        for msg in warning_messages:
            severity = parser._classify_severity(msg)
            assert severity == "warning", f"'{msg}' should be classified as warning"

    def test_parse_multiple_errors(self):
        """Парсинг кількох помилок в одному логу"""
        parser = DesignerLogParser()

        log_content = """Модуль объекта обработки "TestProcessor":
Строка 10, Колонка 5: Неизвестный метод "Test1"
Строка 20, Колонка 15: Ожидается символ ';'
Строка 30, Колонка 1: Переменная не определена "x"
"""
        errors, warnings = parser.parse_log_content(log_content)

        assert len(errors) == 3
        assert errors[0].line == 10
        assert errors[1].line == 20
        assert errors[2].line == 30

    def test_parse_mixed_errors_warnings(self):
        """Парсинг змішаних помилок і попереджень"""
        parser = DesignerLogParser()

        log_content = """Модуль объекта обработки "TestProcessor":
Строка 10, Колонка 5: Неизвестный метод "Test"
Строка 20, Колонка 15: Переменная может быть не инициализирована
"""
        errors, warnings = parser.parse_log_content(log_content)

        assert len(errors) == 1
        assert len(warnings) == 1
        assert errors[0].line == 10
        assert warnings[0].line == 20

    def test_parse_empty_log(self):
        """Парсинг порожнього логу"""
        parser = DesignerLogParser()

        errors, warnings = parser.parse_log_content("")

        assert len(errors) == 0
        assert len(warnings) == 0

    def test_parse_log_without_errors(self):
        """Парсинг логу без помилок"""
        parser = DesignerLogParser()

        log_content = """Модуль объекта обработки "TestProcessor":
Проверка завершена успешно.
"""
        errors, warnings = parser.parse_log_content(log_content)

        assert len(errors) == 0
        assert len(warnings) == 0

    def test_module_tracking(self):
        """Відстеження поточного модуля"""
        parser = DesignerLogParser()

        log_content = """Модуль объекта обработки "Processor1":
Строка 10, Колонка 5: Error in Processor1
Модуль формы "Form1":
Строка 20, Колонка 10: Error in Form1
"""
        errors, warnings = parser.parse_log_content(log_content)

        assert len(errors) == 2
        assert 'Processor1' in errors[0].module
        assert 'Form1' in errors[1].module

    def test_format_errors(self):
        """Форматування списку помилок"""
        parser = DesignerLogParser()

        errors = [
            ValidationError("Module1", 10, 5, "Error 1", "error"),
            ValidationError("Module2", 20, 10, "Error 2", "error"),
            ValidationError("Module3", 30, 15, "Error 3", "error"),
        ]

        formatted = parser.format_errors(errors, max_count=2)

        assert "Module1" in formatted
        assert "Module2" in formatted
        assert "... and 1 more errors" in formatted

    def test_format_no_errors(self):
        """Форматування порожнього списку"""
        parser = DesignerLogParser()
        formatted = parser.format_errors([])
        assert formatted == "No errors"

    def test_to_dict_list(self):
        """Конвертація в список словників"""
        parser = DesignerLogParser()

        errors = [
            ValidationError("Module1", 10, 5, "Error 1", "error"),
            ValidationError("Module2", 20, 10, "Error 2", "warning"),
        ]

        dict_list = parser.to_dict_list(errors)

        assert len(dict_list) == 2
        assert dict_list[0]['line'] == 10
        assert dict_list[0]['column'] == 5
        assert dict_list[0]['message'] == "Error 1"
        assert dict_list[0]['module'] == "Module1"

    def test_parse_lowercase_stroka(self):
        """Парсинг з нижнім регістром 'строка'"""
        parser = DesignerLogParser()

        log_content = """строка 15, колонка 8: Ошибка синтаксиса
"""
        errors, warnings = parser.parse_log_content(log_content)

        assert len(errors) == 1
        assert errors[0].line == 15
        assert errors[0].column == 8


class TestDesignerLogParserFile:
    """Тести з файлами логів"""

    def test_parse_nonexistent_file(self):
        """Парсинг неіснуючого файлу"""
        parser = DesignerLogParser()

        errors, warnings = parser.parse_check_modules_log(
            Path("nonexistent_log.txt")
        )

        assert len(errors) == 0
        assert len(warnings) == 0

    def test_parse_file(self, tmp_path):
        """Парсинг реального файлу"""
        parser = DesignerLogParser()

        # Створюємо тимчасовий лог файл
        log_file = tmp_path / "test.log"
        log_file.write_text(
            """Модуль объекта обработки "Test":
Строка 10, Колонка 5: Неизвестный метод "X"
""",
            encoding="utf-8"
        )

        errors, warnings = parser.parse_check_modules_log(log_file)

        assert len(errors) == 1
        assert errors[0].line == 10


class TestDesignerLogParserEdgeCases:
    """Edge cases для DesignerLogParser"""

    def test_unicode_in_message(self):
        """Unicode символи в повідомленні"""
        parser = DesignerLogParser()

        # Використовуємо російське ключове слово "неизвестн" для класифікації як error
        log_content = """Модуль "Тест":
Строка 1, Колонка 1: Неизвестный идентификатор "ПриміткаУкр"
"""
        errors, warnings = parser.parse_log_content(log_content)

        assert len(errors) == 1
        assert "ПриміткаУкр" in errors[0].message

    def test_multiline_module_name(self):
        """Довга назва модуля"""
        parser = DesignerLogParser()

        log_content = """Модуль объекта обработки "ОченьДлинноеИмяОбработкиДляТестирования":
Строка 100, Колонка 50: Error message
"""
        errors, warnings = parser.parse_log_content(log_content)

        assert len(errors) == 1
        assert "ОченьДлинноеИмяОбработкиДляТестирования" in errors[0].module

    def test_special_characters_in_path(self):
        """Спеціальні символи в шляху модуля"""
        parser = DesignerLogParser()

        log_content = """{DataProcessor.Test_Name.Forms.Form_1.Module(10,5)}: Error
"""
        errors, warnings = parser.parse_log_content(log_content)

        assert len(errors) == 1
        assert "Test_Name" in errors[0].module

    def test_large_line_numbers(self):
        """Великі номери рядків"""
        parser = DesignerLogParser()

        log_content = """Строка 99999, Колонка 500: Ошибка на дуже великому рядку
"""
        errors, warnings = parser.parse_log_content(log_content)

        assert len(errors) == 1
        assert errors[0].line == 99999
        assert errors[0].column == 500
