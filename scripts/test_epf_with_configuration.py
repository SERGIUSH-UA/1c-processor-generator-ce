"""
Тестовий скрипт для compile_epf_with_configuration
Перевіряє повний цикл: YAML → XML → Configuration → EPF
"""

import sys
import shutil
from pathlib import Path

# Додати кореневу папку проекту до sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import importlib
import logging

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

# Import modules dynamically
yaml_parser_module = importlib.import_module('1c_processor_generator.yaml_parser')
metadata_analyzer_module = importlib.import_module('1c_processor_generator.metadata_analyzer')
generator_module = importlib.import_module('1c_processor_generator.generator')
epf_compiler_module = importlib.import_module('1c_processor_generator.epf_compiler')

YAMLParser = yaml_parser_module.YAMLParser
MetadataAnalyzer = metadata_analyzer_module.MetadataAnalyzer
ProcessorGenerator = generator_module.ProcessorGenerator
EPFCompiler = epf_compiler_module.EPFCompiler


def test_full_cycle_with_catalogref():
    """Тест повного циклу з CatalogRef: YAML → XML → Configuration → EPF"""

    yaml_path = project_root / "tests" / "fixtures" / "stripe_tax_config.yaml"
    output_dir = project_root / "tmp" / "test_epf_with_config"

    print("="*80)
    print("EPF Compilation with Configuration Test")
    print("="*80 + "\n")

    # Очистити output директорію
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    print(f"📄 Input YAML: {yaml_path}")
    print(f"📁 Output dir: {output_dir}\n")

    # Крок 1: Парсинг YAML
    print("Step 1/5: Parsing YAML...")
    parser = YAMLParser(str(yaml_path))
    processor = parser.parse()
    print(f"✅ Parsed processor: {processor.name}")
    print(f"   Attributes: {len(processor.attributes)}")
    print(f"   Forms: {len(processor.forms)}\n")

    # Крок 2: Аналіз метаданих
    print("Step 2/5: Analyzing metadata...")
    requirements = MetadataAnalyzer.analyze_processor(processor)
    MetadataAnalyzer.print_analysis(processor, requirements)

    # Перевірка чи потрібна Configuration
    if requirements.is_empty():
        print("\n⚠️ No CatalogRef/DocumentRef types - using simple compilation")
        return False

    # Крок 3: Генерація Processor XML
    print("\nStep 3/5: Generating Processor XML...")
    processor_xml_dir = output_dir / "processor_xml"
    processor_gen = ProcessorGenerator(processor)
    processor_gen.generate(str(processor_xml_dir))
    print(f"✅ Generated Processor XML: {processor_xml_dir}\n")

    # Крок 4: Ініціалізація EPFCompiler
    print("Step 4/5: Initializing EPFCompiler...")
    compiler = EPFCompiler(use_persistent_ib=False)  # Не використовуємо persistent для тесту

    if not compiler.designer_path:
        print("❌ Designer not found! Cannot compile EPF.")
        print("\nPlease ensure 1C Designer is installed or set PATH_1C_DESIGNER environment variable.")
        return False

    print(f"✅ Designer found: {compiler.designer_path}\n")

    # Крок 5: Компіляція EPF з Configuration
    print("Step 5/5: Compiling EPF with Configuration...")
    output_epf = output_dir / f"{processor.name}.epf"

    success = compiler.compile_epf_with_configuration(
        processor_xml_dir=processor_xml_dir,
        output_epf=output_epf,
        processor=processor,
        requirements=requirements,
        timeout=300  # 5 хвилин на всі кроки
    )

    # Результати
    print("\n" + "="*80)
    print("Test Results")
    print("="*80)

    if success:
        print("✅ SUCCESS: EPF compiled with Configuration!")
        print(f"   EPF file: {output_epf}")
        if output_epf.exists():
            size = output_epf.stat().st_size
            print(f"   File size: {size} bytes ({size / 1024:.2f} KB)")
        return True
    else:
        print("❌ FAILED: EPF compilation failed")
        print("\nCheck logs:")
        log_files = list(output_dir.glob("*.log"))
        for log_file in log_files:
            print(f"   - {log_file}")
        return False


if __name__ == "__main__":
    print("\n" + "="*80)
    print("EPF with Configuration Test Suite")
    print("="*80 + "\n")

    try:
        success = test_full_cycle_with_catalogref()

        if success:
            print("\n🎉 All tests passed!")
            sys.exit(0)
        else:
            print("\n❌ Tests failed!")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
