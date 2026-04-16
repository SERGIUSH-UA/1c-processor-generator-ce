"""
Тестовий скрипт для перевірки MetadataAnalyzer
"""

import sys
from pathlib import Path

# Додати кореневу папку проекту до sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import importlib

# Import modules dynamically (module name starts with digit)
yaml_parser_module = importlib.import_module('1c_processor_generator.yaml_parser')
metadata_analyzer_module = importlib.import_module('1c_processor_generator.metadata_analyzer')
models_module = importlib.import_module('1c_processor_generator.models')

YAMLParser = yaml_parser_module.YAMLParser
MetadataAnalyzer = metadata_analyzer_module.MetadataAnalyzer
Processor = models_module.Processor
Attribute = models_module.Attribute

def test_stripe_tax_analyzer():
    """Тест MetadataAnalyzer на файлі stripe_tax_config.yaml"""

    yaml_path = project_root / "tests" / "fixtures" / "stripe_tax_config.yaml"

    print(f"📄 Loading YAML from: {yaml_path}\n")

    # Парсимо YAML в Processor об'єкт
    parser = YAMLParser(str(yaml_path))
    processor = parser.parse()

    print(f"✅ Parsed processor: {processor.name}")
    print(f"   Attributes: {len(processor.attributes)}")
    print(f"   Tabular sections: {len(processor.tabular_sections)}")
    print(f"   Forms: {len(processor.forms)}\n")

    # Аналізуємо метадані
    requirements = MetadataAnalyzer.analyze_processor(processor)

    # Виводимо детальний аналіз
    MetadataAnalyzer.print_analysis(processor, requirements)

    # Перевірка очікуваних результатів
    expected_catalogs = {"Организации", "Контрагенты", "Номенклатура"}
    expected_documents = set()

    if requirements.catalogs == expected_catalogs:
        print(f"\n✅ Catalogs match expected: {expected_catalogs}")
    else:
        print(f"\n❌ ERROR: Expected {expected_catalogs}, got {requirements.catalogs}")
        return False

    if requirements.documents == expected_documents:
        print(f"✅ Documents match expected: {expected_documents}")
    else:
        print(f"❌ ERROR: Expected {expected_documents}, got {requirements.documents}")
        return False

    # Перевірка кількості UUID
    expected_uuid_count = 35  # 2 (base) + 3 catalogs * 11 = 35
    actual_uuid_count = MetadataAnalyzer.calculate_uuid_count(requirements)

    if actual_uuid_count == expected_uuid_count:
        print(f"✅ UUID count matches: {actual_uuid_count}")
    else:
        print(f"❌ ERROR: Expected {expected_uuid_count} UUIDs, got {actual_uuid_count}")
        return False

    print("\n🎉 All tests passed!")
    return True

def test_simple_processor():
    """Тест на простому процесорі без CatalogRef"""

    print("\n" + "="*60)
    print("Test 2: Simple processor without CatalogRef")
    print("="*60 + "\n")

    processor = Processor(
        name="SimpleProcessor",
        synonym_ru="Простая обработка"
    )

    processor.add_attribute("Name", "string", length=100)
    processor.add_attribute("Amount", "number", digits=15, fraction_digits=2)
    processor.add_attribute("Date", "date")

    requirements = MetadataAnalyzer.analyze_processor(processor)

    print(f"Processor: {processor.name}")
    print(f"Catalogs found: {requirements.catalogs}")
    print(f"Documents found: {requirements.documents}")
    print(f"Is empty: {requirements.is_empty()}")

    if requirements.is_empty():
        print("✅ Correctly detected no metadata needed")
        return True
    else:
        print("❌ ERROR: Should be empty!")
        return False

def test_composite_types():
    """Тест на composite типах (CatalogRef + DocumentRef + string)"""

    print("\n" + "="*60)
    print("Test 3: Composite types")
    print("="*60 + "\n")

    processor = Processor(
        name="CompositeProcessor",
        synonym_ru="Обработка с составными типами"
    )

    # Composite type: CatalogRef + DocumentRef + string
    processor.add_attribute(
        "CompositeField",
        "CatalogRef.Товары, DocumentRef.Накладная, string",
        synonym_ru="Составное поле"
    )

    requirements = MetadataAnalyzer.analyze_processor(processor)

    print(f"Processor: {processor.name}")
    print(f"Catalogs found: {requirements.catalogs}")
    print(f"Documents found: {requirements.documents}")

    expected_catalogs = {"Товары"}
    expected_documents = {"Накладная"}

    if requirements.catalogs == expected_catalogs and requirements.documents == expected_documents:
        print("✅ Correctly extracted composite types")
        return True
    else:
        print(f"❌ ERROR: Expected catalogs={expected_catalogs}, documents={expected_documents}")
        print(f"   Got catalogs={requirements.catalogs}, documents={requirements.documents}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("MetadataAnalyzer Test Suite")
    print("="*60 + "\n")

    results = []

    # Test 1: Stripe Tax YAML (real-world example)
    try:
        results.append(("Stripe Tax YAML", test_stripe_tax_analyzer()))
    except Exception as e:
        print(f"❌ Test 1 failed with error: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Stripe Tax YAML", False))

    # Test 2: Simple processor without CatalogRef
    try:
        results.append(("Simple processor", test_simple_processor()))
    except Exception as e:
        print(f"❌ Test 2 failed with error: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Simple processor", False))

    # Test 3: Composite types
    try:
        results.append(("Composite types", test_composite_types()))
    except Exception as e:
        print(f"❌ Test 3 failed with error: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Composite types", False))

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
