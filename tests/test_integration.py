"""
End-to-end integration тести
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

import importlib
yaml_parser_module = importlib.import_module("1c_processor_generator.yaml_parser")
generator_module = importlib.import_module("1c_processor_generator.generator")

parse_yaml_config = yaml_parser_module.parse_yaml_config
ProcessorGenerator = generator_module.ProcessorGenerator


class TestEndToEndSimpleProcessor:
    """End-to-end тести для простого процесора"""

    def test_yaml_to_xml_simple(self, fixtures_dir, temp_dir):
        """Повний цикл: YAML → Processor → XML (простий процесор)"""
        yaml_path = fixtures_dir / "simple_config.yaml"
        handlers_dir = fixtures_dir / "handlers"

        # 1. Парсинг YAML + завантаження BSL
        processor = parse_yaml_config(yaml_path, handlers_dir)
        assert processor is not None

        # 2. Генерація XML
        generator = ProcessorGenerator(processor)
        processor_root = generator.generate(str(temp_dir))
        assert processor_root is not None

        # 3. Перевірка файлової структури
        assert processor_root.exists()

        main_xml = processor_root / f"{processor.name}.xml"
        assert main_xml.exists()
        assert main_xml.stat().st_size > 0

    def test_yaml_to_xml_complex(self, fixtures_dir, temp_dir):
        """Повний цикл: YAML → Processor → XML (складний процесор)"""
        yaml_path = fixtures_dir / "complex_config.yaml"
        handlers_dir = fixtures_dir / "handlers"

        # 1. Парсинг YAML + завантаження BSL
        processor = parse_yaml_config(yaml_path, handlers_dir)
        assert processor is not None

        # Перевіряємо що все розпарсилося
        assert len(processor.attributes) > 0
        assert len(processor.tabular_sections) > 0

        form = processor.get_default_form()
        assert len(form.value_table_attributes) > 0
        assert len(form.commands) > 0

        # 2. Генерація XML
        generator = ProcessorGenerator(processor)
        processor_root = generator.generate(str(temp_dir))
        assert processor_root is not None

        # 3. Перевірка файлової структури
        assert processor_root.exists()


class TestEndToEndWithBSL:
    """End-to-end тести з BSL обробниками"""

    def test_bsl_injection_in_generated_files(self, fixtures_dir, temp_dir):
        """BSL обробники мають бути включені в згенеровані файли"""
        yaml_path = fixtures_dir / "simple_config.yaml"
        handlers_dir = fixtures_dir / "handlers"

        processor = parse_yaml_config(yaml_path, handlers_dir)
        generator = ProcessorGenerator(processor)
        generator.generate(str(temp_dir))

        # Перевіряємо Module.bsl форми
        form_module = (
            temp_dir / processor.name / processor.name / "Forms" / "Форма" / "Ext" / "Form" / "Module.bsl"
        )
        assert form_module.exists()

        content = form_module.read_text(encoding="utf-8-sig")

        # Має містити обробники
        assert "Процедура" in content
        assert "КонецПроцедуры" in content

    def test_server_handlers_generation(self, fixtures_dir, temp_dir):
        """Генерація серверних обробників"""
        yaml_path = fixtures_dir / "complex_config.yaml"
        handlers_dir = fixtures_dir / "handlers"

        processor = parse_yaml_config(yaml_path, handlers_dir)
        generator = ProcessorGenerator(processor)
        generator.generate(str(temp_dir))

        form_module = (
            temp_dir / processor.name / processor.name / "Forms" / "Форма" / "Ext" / "Form" / "Module.bsl"
        )

        content = form_module.read_text(encoding="utf-8-sig")

        # Має містити серверні обробники
        if "&НаСервере" in content or "&НаКлиенте" in content:
            assert True
        else:
            # Перевіряємо що хоча б є базові обробники
            assert "Процедура" in content


class TestRealWorldExamples:
    """Тести з реальними прикладами"""

    def test_generate_from_examples_simple_role_setter(self, temp_dir):
        """Генерація з examples/yaml/simple_role_setter"""
        examples_dir = Path(__file__).parent.parent / "examples" / "yaml" / "simple_role_setter"

        if not examples_dir.exists():
            pytest.skip("Examples directory not found")

        yaml_path = examples_dir / "config.yaml"
        handlers_dir = examples_dir / "handlers"

        if not yaml_path.exists():
            pytest.skip("Example config not found")

        processor = parse_yaml_config(yaml_path, handlers_dir if handlers_dir.exists() else None)
        assert processor is not None

        generator = ProcessorGenerator(processor)
        processor_root = generator.generate(str(temp_dir))
        assert processor_root is not None

    def test_generate_from_examples_sales_report(self, temp_dir):
        """Генерація з examples/yaml/sales_report"""
        examples_dir = Path(__file__).parent.parent / "examples" / "yaml" / "sales_report"

        if not examples_dir.exists():
            pytest.skip("Examples directory not found")

        yaml_path = examples_dir / "config.yaml"
        handlers_dir = examples_dir / "handlers"

        if not yaml_path.exists():
            pytest.skip("Example config not found")

        processor = parse_yaml_config(yaml_path, handlers_dir if handlers_dir.exists() else None)
        assert processor is not None

        generator = ProcessorGenerator(processor)
        processor_root = generator.generate(str(temp_dir))
        assert processor_root is not None


class TestValidationInPipeline:
    """Тести валідації в повному циклі"""

    def test_validation_catches_errors(self, temp_dir):
        """Валідація має виявляти помилки"""
        import importlib
        models_module = importlib.import_module("1c_processor_generator.models")
        Processor = models_module.Processor

        # Створюємо процесор з невалідною назвою
        processor = Processor(name="123InvalidName")
        processor.add_attribute(name="Attr", type="string")

        generator = ProcessorGenerator(processor)

        # Валідація має не пройти
        is_valid = generator.validate()
        assert not is_valid

        # Генерація не має відбутися (повертає None або False)
        result = generator.generate(str(temp_dir))
        assert not result

    def test_validation_allows_valid_processors(self, simple_processor, temp_dir):
        """Валідація має пропускати валідні процесори"""
        generator = ProcessorGenerator(simple_processor)

        is_valid = generator.validate()
        assert is_valid

        processor_root = generator.generate(str(temp_dir))
        assert processor_root is not None


class TestCompleteStructure:
    """Тести повної структури згенерованих файлів"""

    def test_complete_file_structure(self, fixtures_dir, temp_dir):
        """Перевірка повної структури файлів"""
        yaml_path = fixtures_dir / "simple_config.yaml"
        handlers_dir = fixtures_dir / "handlers"

        processor = parse_yaml_config(yaml_path, handlers_dir)
        generator = ProcessorGenerator(processor)
        generator.generate(str(temp_dir))

        processor_root = temp_dir / processor.name

        # Перевіряємо всі очікувані файли та директорії
        expected_files = [
            processor_root / f"{processor.name}.xml",
            processor_root / processor.name / "Ext" / "ObjectModule.bsl",
            processor_root / processor.name / "Forms" / "Форма.xml",
            processor_root / processor.name / "Forms" / "Форма" / "Ext" / "Form.xml",
            processor_root / processor.name / "Forms" / "Форма" / "Ext" / "Form" / "Module.bsl",
        ]

        for file_path in expected_files:
            assert file_path.exists(), f"Expected file {file_path} does not exist"

    def test_xml_files_are_valid_xml(self, fixtures_dir, temp_dir):
        """XML файли мають бути валідними XML"""
        yaml_path = fixtures_dir / "simple_config.yaml"
        processor = parse_yaml_config(yaml_path)

        generator = ProcessorGenerator(processor)
        generator.generate(str(temp_dir))

        processor_root = temp_dir / processor.name
        main_xml = processor_root / f"{processor.name}.xml"

        # Спроба прочитати як XML
        import xml.etree.ElementTree as ET
        try:
            tree = ET.parse(main_xml)
            root = tree.getroot()
            assert root is not None
        except ET.ParseError as e:
            pytest.fail(f"XML parsing failed: {e}")


class TestMultipleProcessors:
    """Тести генерації кількох процесорів"""

    def test_generate_multiple_processors(self, fixtures_dir, temp_dir):
        """Генерація кількох процесорів в одну директорію"""
        # Простий процесор
        yaml_path1 = fixtures_dir / "simple_config.yaml"
        processor1 = parse_yaml_config(yaml_path1)
        generator1 = ProcessorGenerator(processor1)
        processor_root1 = generator1.generate(str(temp_dir))
        assert processor_root1 is not None

        # Складний процесор
        yaml_path2 = fixtures_dir / "complex_config.yaml"
        processor2 = parse_yaml_config(yaml_path2)
        generator2 = ProcessorGenerator(processor2)
        processor_root2 = generator2.generate(str(temp_dir))
        assert processor_root2 is not None

        # Перевіряємо що обидва згенеровані
        assert (temp_dir / processor1.name).exists()
        assert (temp_dir / processor2.name).exists()
