"""
Тести для BSL валідації через /CheckModules
"""

import pytest
import sys
from pathlib import Path

# Імпорт з пакету 1c_processor_generator
sys.path.insert(0, str(Path(__file__).parent.parent))
from importlib import import_module
epf_compiler_module = import_module('1c_processor_generator.epf_compiler')
EPFCompiler = epf_compiler_module.EPFCompiler

# v2.52.0: Internal marker for test instantiation


def create_test_compiler(**kwargs):
    """Helper to create EPFCompiler for tests with internal marker."""
    return EPFCompiler(**kwargs)


class TestCheckModulesLogParser:
    """Тести для парсера логів /CheckModules"""

    def test_parse_format1_error(self):
        """Парсинг помилки у форматі 'Строка X, Колонка Y: Message'"""
        log_content = """
Модуль формы обработки "TestProcessor":
Строка 45, Колонка 12: Неизвестный метод "НесуществующийМетод"
"""
        log_file = Path("test.log")

        compiler = create_test_compiler()

        # Створюємо тимчасовий файл
        log_file.write_text(log_content, encoding='utf-8')

        try:
            errors, warnings = compiler._parse_check_modules_log(log_file)

            assert len(errors) == 1
            assert len(warnings) == 0

            error = errors[0]
            assert error['line'] == 45
            assert error['column'] == 12
            assert 'Неизвестный метод' in error['message']
            assert 'TestProcessor' in error['module']
        finally:
            if log_file.exists():
                log_file.unlink()

    def test_parse_format2_error(self):
        """Парсинг помилки у форматі '{Module(line,col)}: Message'"""
        log_content = """{Обработка.TestProcessor.Форма.Форма.Форма(25,30)}: Ожидается символ ';'
{Обработка.TestProcessor.Форма.Форма.Форма(28,1)}: Неопознанный оператор
"""
        log_file = Path("test.log")

        compiler = create_test_compiler()

        log_file.write_text(log_content, encoding='utf-8')

        try:
            errors, warnings = compiler._parse_check_modules_log(log_file)

            assert len(errors) == 2
            assert len(warnings) == 0

            error1 = errors[0]
            assert error1['line'] == 25
            assert error1['column'] == 30
            assert 'Ожидается' in error1['message']
            assert 'TestProcessor' in error1['module']

            error2 = errors[1]
            assert error2['line'] == 28
            assert error2['column'] == 1
            assert 'Неопознанный' in error2['message']
        finally:
            if log_file.exists():
                log_file.unlink()

    def test_parse_warnings(self):
        """Парсинг попереджень (не errors)"""
        log_content = """{Обработка.TestProcessor.Форма.Форма.Форма(10,5)}: Рекомендуется использовать...
"""
        log_file = Path("test.log")

        compiler = create_test_compiler()

        log_file.write_text(log_content, encoding='utf-8')

        try:
            errors, warnings = compiler._parse_check_modules_log(log_file)

            assert len(errors) == 0
            assert len(warnings) == 1

            warning = warnings[0]
            assert warning['line'] == 10
            assert warning['column'] == 5
            assert 'Рекомендуется' in warning['message']
        finally:
            if log_file.exists():
                log_file.unlink()

    def test_parse_mixed_errors_and_warnings(self):
        """Парсинг змішаних помилок та попереджень"""
        log_content = """{Обработка.Test.Форма(10,5)}: Рекомендуется использовать
{Обработка.Test.Форма(15,10)}: Неизвестный метод
{Обработка.Test.Форма(20,1)}: Ожидается символ
"""
        log_file = Path("test.log")

        compiler = create_test_compiler()

        log_file.write_text(log_content, encoding='utf-8')

        try:
            errors, warnings = compiler._parse_check_modules_log(log_file)

            assert len(errors) == 2
            assert len(warnings) == 1
        finally:
            if log_file.exists():
                log_file.unlink()

    def test_empty_log(self):
        """Парсинг порожнього логу"""
        log_file = Path("empty.log")

        compiler = create_test_compiler()

        log_file.write_text("", encoding='utf-8')

        try:
            errors, warnings = compiler._parse_check_modules_log(log_file)

            assert len(errors) == 0
            assert len(warnings) == 0
        finally:
            if log_file.exists():
                log_file.unlink()

    def test_nonexistent_log(self):
        """Обробка неіснуючого лог файлу"""
        log_file = Path("nonexistent.log")

        compiler = create_test_compiler()

        errors, warnings = compiler._parse_check_modules_log(log_file)

        assert len(errors) == 0
        assert len(warnings) == 0


class TestErrorClassification:
    """Тести для класифікації помилок vs попереджень"""

    def test_expected_semicolon_is_error(self):
        """'Ожидается символ' - це помилка"""
        log_content = "{Test(1,1)}: Ожидается символ ';'"
        log_file = Path("test.log")
        compiler = create_test_compiler()
        log_file.write_text(log_content, encoding='utf-8')

        try:
            errors, warnings = compiler._parse_check_modules_log(log_file)
            assert len(errors) == 1
            assert len(warnings) == 0
        finally:
            if log_file.exists():
                log_file.unlink()

    def test_unrecognized_operator_is_error(self):
        """'Неопознанный оператор' - це помилка"""
        log_content = "{Test(1,1)}: Неопознанный оператор"
        log_file = Path("test.log")
        compiler = create_test_compiler()
        log_file.write_text(log_content, encoding='utf-8')

        try:
            errors, warnings = compiler._parse_check_modules_log(log_file)
            assert len(errors) == 1
            assert len(warnings) == 0
        finally:
            if log_file.exists():
                log_file.unlink()

    def test_unknown_method_is_error(self):
        """'Неизвестный метод' - це помилка"""
        log_content = "{Test(1,1)}: Неизвестный метод 'Foo'"
        log_file = Path("test.log")
        compiler = create_test_compiler()
        log_file.write_text(log_content, encoding='utf-8')

        try:
            errors, warnings = compiler._parse_check_modules_log(log_file)
            assert len(errors) == 1
            assert len(warnings) == 0
        finally:
            if log_file.exists():
                log_file.unlink()
