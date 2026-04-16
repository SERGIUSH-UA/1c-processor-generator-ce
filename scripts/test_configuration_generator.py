"""
Тестовий скрипт для перевірки ConfigurationGenerator
"""

import sys
import shutil
from pathlib import Path

# Додати кореневу папку проекту до sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import importlib

# Import modules dynamically
yaml_parser_module = importlib.import_module('1c_processor_generator.yaml_parser')
metadata_analyzer_module = importlib.import_module('1c_processor_generator.metadata_analyzer')
configuration_generator_module = importlib.import_module('1c_processor_generator.configuration_generator')
generator_module = importlib.import_module('1c_processor_generator.generator')

YAMLParser = yaml_parser_module.YAMLParser
MetadataAnalyzer = metadata_analyzer_module.MetadataAnalyzer
ConfigurationGenerator = configuration_generator_module.ConfigurationGenerator
ProcessorGenerator = generator_module.ProcessorGenerator


def test_stripe_tax_configuration():
    """Тест повного циклу: YAML → Processor XML → Configuration XML"""

    yaml_path = project_root / "tests" / "fixtures" / "stripe_tax_config.yaml"
    output_dir = project_root / "tmp" / "test_config_generation"

    print("="*60)
    print("Configuration Generator Test")
    print("="*60 + "\n")

    # Очистити output директорію
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    print(f"📄 Input YAML: {yaml_path}")
    print(f"📁 Output dir: {output_dir}\n")

    # Крок 1: Парсинг YAML
    print("Step 1: Parsing YAML...")
    parser = YAMLParser(str(yaml_path))
    processor = parser.parse()
    print(f"✅ Parsed processor: {processor.name}")
    print(f"   Attributes: {len(processor.attributes)}")
    print(f"   Forms: {len(processor.forms)}\n")

    # Крок 2: Аналіз метаданих
    print("Step 2: Analyzing metadata...")
    requirements = MetadataAnalyzer.analyze_processor(processor)
    MetadataAnalyzer.print_analysis(processor, requirements)

    # Перевірка чи потрібна Configuration
    if requirements.is_empty():
        print("\n⚠️ No CatalogRef/DocumentRef types found - Configuration not needed")
        return False

    # Крок 3: Генерація Processor XML
    print("\nStep 3: Generating Processor XML...")
    processor_xml_dir = output_dir / "processor_xml"
    processor_gen = ProcessorGenerator(processor)
    processor_gen.generate(str(processor_xml_dir))
    print(f"✅ Generated Processor XML: {processor_xml_dir}\n")

    # Крок 4: Генерація Configuration
    print("Step 4: Generating Configuration...")
    config_gen = ConfigurationGenerator(processor, requirements)
    config_dir = config_gen.generate_configuration(output_dir, processor_xml_dir)

    # Виведення підсумку
    config_gen.print_generation_summary()

    # Крок 5: Перевірка згенерованих файлів
    print("Step 5: Verifying generated files...\n")

    expected_files = [
        config_dir / "Configuration.xml",
        config_dir / "Languages" / "Русский.xml",
        config_dir / "DataProcessors" / processor.name / f"{processor.name}.xml"
    ]

    # Додати файли для кожного довідника
    for catalog_name in requirements.catalogs:
        expected_files.append(config_dir / "Catalogs" / f"{catalog_name}.xml")

    # Додати файли для кожного документа
    for document_name in requirements.documents:
        expected_files.append(config_dir / "Documents" / f"{document_name}.xml")

    all_exist = True
    for file_path in expected_files:
        if file_path.exists():
            size = file_path.stat().st_size
            print(f"✅ {file_path.relative_to(output_dir)} ({size} bytes)")
        else:
            print(f"❌ Missing: {file_path.relative_to(output_dir)}")
            all_exist = False

    if all_exist:
        print("\n🎉 All expected files generated successfully!")
        print(f"\n📂 Configuration directory: {config_dir}")
        return True
    else:
        print("\n❌ Some files are missing!")
        return False


def test_simple_generation():
    """Тест генерації для простого процесора (без CatalogRef)"""

    print("\n" + "="*60)
    print("Test 2: Simple Processor (no CatalogRef)")
    print("="*60 + "\n")

    from importlib import import_module
    models_module = import_module('1c_processor_generator.models')
    Processor = models_module.Processor

    processor = Processor(
        name="SimpleTest",
        synonym_ru="Простой тест"
    )
    processor.add_attribute("Name", "string", length=100)
    processor.add_attribute("Amount", "number", digits=15, fraction_digits=2)

    requirements = MetadataAnalyzer.analyze_processor(processor)

    print(f"Processor: {processor.name}")
    print(f"Requirements: {requirements}")

    if requirements.is_empty():
        print("✅ Correctly detected: Configuration generation not needed")
        return True
    else:
        print("❌ ERROR: Should not require Configuration!")
        return False


if __name__ == "__main__":
    print("\n" + "="*60)
    print("ConfigurationGenerator Test Suite")
    print("="*60 + "\n")

    results = []

    # Test 1: Full cycle with Stripe Tax
    try:
        results.append(("Stripe Tax Configuration", test_stripe_tax_configuration()))
    except Exception as e:
        print(f"\n❌ Test 1 failed with error: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Stripe Tax Configuration", False))

    # Test 2: Simple processor (no CatalogRef)
    try:
        results.append(("Simple processor", test_simple_generation()))
    except Exception as e:
        print(f"\n❌ Test 2 failed with error: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Simple processor", False))

    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")

    all_passed = all(result[1] for result in results)

    if all_passed:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)
