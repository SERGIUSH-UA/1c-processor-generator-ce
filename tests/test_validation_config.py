"""
Тести для ValidationConfig та парсингу секції validation з YAML (v2.12.0+)
"""

import pytest
import tempfile
import sys
from pathlib import Path

# Додаємо батьківську директорію в sys.path для імпорту
sys.path.insert(0, str(Path(__file__).parent.parent))

import importlib
models = importlib.import_module("1c_processor_generator.models")
yaml_parser = importlib.import_module("1c_processor_generator.yaml_parser")
epf_compiler_module = importlib.import_module("1c_processor_generator.epf_compiler")

ValidationConfig = models.ValidationConfig
Processor = models.Processor
YAMLParser = yaml_parser.YAMLParser
EPFCompiler = epf_compiler_module.EPFCompiler

# v2.52.0: Internal marker for test instantiation


def create_test_compiler(**kwargs):
    """Helper to create EPFCompiler for tests with internal marker."""
    return EPFCompiler(**kwargs)


class TestValidationConfigDefaults:
    """Тести для значень ValidationConfig за замовчуванням"""

    def test_default_validation_config(self):
        """Тест що ValidationConfig має правильні default значення"""
        config = ValidationConfig()

        # CheckModules defaults
        assert config.check_modules_enabled == True
        assert config.check_thin_client == True
        assert config.check_server == True
        assert config.check_web_client == False
        assert config.check_external_connection == False
        assert config.check_thick_client == False

        # CheckConfig defaults (v2.74.0+: semantic validation enabled by default)
        assert config.check_config_enabled == True  # Enabled by default since v2.74.0
        assert config.check_incorrect_references == True
        assert config.check_handlers_existence == True
        assert config.check_empty_handlers == True
        assert config.check_unreference_procedures == False
        assert config.check_extended_modules == True


class TestYAMLValidationParsing:
    """Тести для парсингу секції validation з YAML"""

    def test_yaml_without_validation_section(self, tmp_path):
        """Тест що YAML без секції validation використовує defaults"""
        yaml_content = """
processor:
  name: ТестоваяОбработка

attributes:
  - name: Реквизит1
    type: string
"""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        parser = YAMLParser(yaml_file)
        processor = parser.parse()

        assert processor is not None
        assert processor.validation is not None
        assert isinstance(processor.validation, ValidationConfig)

        # Перевіряємо що використовуються defaults (v2.74.0+: semantic enabled)
        assert processor.validation.check_modules_enabled == True
        assert processor.validation.check_config_enabled == True  # Enabled by default
        assert processor.validation.check_web_client == False

    def test_yaml_with_empty_validation_section(self, tmp_path):
        """Тест що YAML з порожньою секцією validation використовує defaults"""
        yaml_content = """
processor:
  name: ТестоваяОбработка

validation: {}

attributes:
  - name: Реквизит1
    type: string
"""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        parser = YAMLParser(yaml_file)
        processor = parser.parse()

        assert processor is not None
        assert processor.validation.check_modules_enabled == True
        assert processor.validation.check_config_enabled == True  # Enabled by default

    def test_yaml_with_partial_validation_override(self, tmp_path):
        """Тест що YAML з частковим override працює коректно"""
        yaml_content = """
processor:
  name: ТестоваяОбработка

validation:
  check_web_client: true
  check_config_enabled: true

attributes:
  - name: Реквизит1
    type: string
"""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        parser = YAMLParser(yaml_file)
        processor = parser.parse()

        assert processor is not None

        # Перевіряємо override значення
        assert processor.validation.check_web_client == True
        assert processor.validation.check_config_enabled == True

        # Перевіряємо що інші залишились defaults
        assert processor.validation.check_thin_client == True
        assert processor.validation.check_server == True
        assert processor.validation.check_extended_modules == True

    def test_yaml_with_full_validation_override(self, tmp_path):
        """Тест що YAML з повним override всіх параметрів працює"""
        yaml_content = """
processor:
  name: ТестоваяОбработка

validation:
  # CheckModules
  check_modules_enabled: false
  check_thin_client: false
  check_server: false
  check_web_client: true
  check_external_connection: true
  check_thick_client: true

  # CheckConfig
  check_config_enabled: true
  check_incorrect_references: false
  check_handlers_existence: false
  check_empty_handlers: false
  check_unreference_procedures: true
  check_extended_modules: false

attributes:
  - name: Реквизит1
    type: string
"""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        parser = YAMLParser(yaml_file)
        processor = parser.parse()

        assert processor is not None

        # CheckModules - всі змінені
        assert processor.validation.check_modules_enabled == False
        assert processor.validation.check_thin_client == False
        assert processor.validation.check_server == False
        assert processor.validation.check_web_client == True
        assert processor.validation.check_external_connection == True
        assert processor.validation.check_thick_client == True

        # CheckConfig - всі змінені
        assert processor.validation.check_config_enabled == True
        assert processor.validation.check_incorrect_references == False
        assert processor.validation.check_handlers_existence == False
        assert processor.validation.check_empty_handlers == False
        assert processor.validation.check_unreference_procedures == True
        assert processor.validation.check_extended_modules == False

    def test_yaml_validation_section_with_all_true(self, tmp_path):
        """Тест максимальної валідації (всі параметри true)"""
        yaml_content = """
processor:
  name: ПродакшенОбработка

validation:
  check_modules_enabled: true
  check_thin_client: true
  check_server: true
  check_web_client: true
  check_external_connection: true
  check_thick_client: true

  check_config_enabled: true
  check_incorrect_references: true
  check_handlers_existence: true
  check_empty_handlers: true
  check_unreference_procedures: true
  check_extended_modules: true

attributes:
  - name: Реквизит1
    type: string
"""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        parser = YAMLParser(yaml_file)
        processor = parser.parse()

        assert processor is not None

        # Всі параметри мають бути True
        assert processor.validation.check_modules_enabled == True
        assert processor.validation.check_thin_client == True
        assert processor.validation.check_server == True
        assert processor.validation.check_web_client == True
        assert processor.validation.check_external_connection == True
        assert processor.validation.check_thick_client == True

        assert processor.validation.check_config_enabled == True
        assert processor.validation.check_incorrect_references == True
        assert processor.validation.check_handlers_existence == True
        assert processor.validation.check_empty_handlers == True
        assert processor.validation.check_unreference_procedures == True
        assert processor.validation.check_extended_modules == True


class TestBuildCheckConfigParams:
    """Тести для _build_check_config_params в EPFCompiler"""

    def test_build_params_all_disabled(self):
        """Тест що при всіх disabled параметри тільки базові"""
        config = ValidationConfig(
            semantic_check_enabled=False,
            check_incorrect_references=False,
            check_handlers_existence=False,
            check_empty_handlers=False,
            check_unreference_procedures=False,
            check_extended_modules=False,
        )

        compiler = create_test_compiler()
        params = compiler._build_check_config_params(config)

        # Тільки базові параметри (ThinClient, Server)
        assert "-ThinClient" in params
        assert "-Server" in params
        assert len(params) == 2

    def test_build_params_all_enabled(self):
        """Тест що при всіх enabled всі параметри включені"""
        config = ValidationConfig(
            semantic_check_enabled=True,
            check_incorrect_references=True,
            check_handlers_existence=True,
            check_empty_handlers=True,
            check_unreference_procedures=True,
            check_extended_modules=True,
        )

        compiler = create_test_compiler()
        params = compiler._build_check_config_params(config)

        # Базові + всі семантичні перевірки
        assert "-ThinClient" in params
        assert "-Server" in params
        assert "-IncorrectReferences" in params
        assert "-HandlersExistence" in params
        assert "-EmptyHandlers" in params
        assert "-UnreferenceProcedures" in params
        assert "-ExtendedModulesCheck" in params
        assert len(params) == 7  # 2 базових + 5 семантичних

    def test_build_params_partial_enabled(self):
        """Тест що при частковому enabled тільки вибрані параметри"""
        config = ValidationConfig(
            semantic_check_enabled=True,
            check_incorrect_references=True,
            check_handlers_existence=False,  # disabled
            check_empty_handlers=True,
            check_unreference_procedures=False,  # disabled
            check_extended_modules=True,
        )

        compiler = create_test_compiler()
        params = compiler._build_check_config_params(config)

        # Базові + тільки enabled семантичні перевірки
        assert "-ThinClient" in params
        assert "-Server" in params
        assert "-IncorrectReferences" in params
        assert "-EmptyHandlers" in params
        assert "-ExtendedModulesCheck" in params

        # Disabled параметри НЕ мають бути
        assert "-HandlersExistence" not in params
        assert "-UnreferenceProcedures" not in params

        assert len(params) == 5  # 2 базових + 3 enabled семантичних


class TestValidationExample:
    """Тести для прикладу validation_example"""

    def test_validation_example_parses_correctly(self):
        """Тест що приклад validation_example парситься без помилок"""
        example_path = Path(__file__).parent.parent / "examples" / "yaml" / "validation_example" / "config.yaml"

        if not example_path.exists():
            pytest.skip("validation_example не знайдено")

        parser = YAMLParser(example_path)
        processor = parser.parse()

        assert processor is not None
        assert processor.name == "ПрикладВалидации"

        # Перевіряємо що validation налаштована як в прикладі
        assert processor.validation.check_web_client == True
        assert processor.validation.check_config_enabled == True
        assert processor.validation.check_incorrect_references == True
        assert processor.validation.check_extended_modules == True


if __name__ == "__main__":
    # Можна запустити тести напряму
    pytest.main([__file__, "-v"])
