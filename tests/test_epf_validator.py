"""
Unit тести для epf_validator.py

EPFValidator - заглушка для валідації EPF файлів.
Реальна функціональність потребує PRO ліцензії.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import importlib
epf_validator_module = importlib.import_module("1c_processor_generator.epf_validator")

EPFValidator = epf_validator_module.EPFValidator
ValidationResult = epf_validator_module.ValidationResult
ValidationError = epf_validator_module.ValidationError


class TestEPFValidatorInit:
    """Тести ініціалізації EPFValidator"""

    def test_init_without_platform_path(self):
        """Ініціалізація без шляху до платформи"""
        validator = EPFValidator()
        assert validator.platform_path is None

    def test_init_with_platform_path(self):
        """Ініціалізація з шляхом до платформи"""
        validator = EPFValidator(platform_path="/path/to/1cv8.exe")
        assert validator.platform_path == "/path/to/1cv8.exe"

    def test_validator_epf_path(self):
        """Перевірка шляху до validator.epf"""
        validator = EPFValidator()
        assert validator.validator_epf.name == "validator.epf"
        assert "resources" in str(validator.validator_epf)


class TestValidateEPF:
    """Тести методу validate_epf"""

    def test_validate_epf_raises_not_implemented(self, tmp_path):
        """validate_epf повинен повертати NotImplementedError"""
        epf_file = tmp_path / "Test.epf"
        epf_file.touch()

        validator = EPFValidator()

        with pytest.raises(NotImplementedError) as exc_info:
            validator.validate_epf(epf_file)

        assert "PRO license" in str(exc_info.value)


class TestValidationDataclasses:
    """Тести для ValidationError та ValidationResult"""

    def test_validation_error_str(self):
        """Строкове представлення ValidationError"""
        error = ValidationError(
            line=45,
            column=12,
            message="Test error",
            severity="error",
            module="ObjectModule"
        )

        error_str = str(error)
        assert "ERROR" in error_str
        assert "Line 45" in error_str
        assert "Col 12" in error_str

    def test_validation_result_str_success(self, tmp_path):
        """Строкове представлення ValidationResult (успіх)"""
        epf_file = tmp_path / "Test.epf"
        epf_file.touch()

        result = ValidationResult(
            success=True,
            epf_path=epf_file,
            error_count=0,
            warning_count=0,
            errors=[],
            elapsed_time=1.5,
            log_content="OK"
        )

        result_str = str(result)
        assert "passed" in result_str.lower() or "✓" in result_str

    def test_validation_result_str_failure(self, tmp_path):
        """Строкове представлення ValidationResult (помилка)"""
        epf_file = tmp_path / "Test.epf"
        epf_file.touch()

        result = ValidationResult(
            success=False,
            epf_path=epf_file,
            error_count=3,
            warning_count=1,
            errors=[],
            elapsed_time=2.0,
            log_content="FAILED"
        )

        result_str = str(result)
        assert "failed" in result_str.lower() or "✗" in result_str
