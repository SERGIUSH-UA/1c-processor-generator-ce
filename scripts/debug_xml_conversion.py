"""
Debug script для перевірки конвертації ExternalDataProcessor → DataProcessor
"""
import sys
from pathlib import Path

# Додати кореневу папку проекту до sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import importlib

# Import modules dynamically
yaml_parser_module = importlib.import_module('1c_processor_generator.yaml_parser')
metadata_analyzer_module = importlib.import_module('1c_processor_generator.metadata_analyzer')
generator_module = importlib.import_module('1c_processor_generator.generator')
config_gen_module = importlib.import_module('1c_processor_generator.configuration_generator')

YAMLParser = yaml_parser_module.YAMLParser
MetadataAnalyzer = metadata_analyzer_module.MetadataAnalyzer
ProcessorGenerator = generator_module.ProcessorGenerator
ConfigurationGenerator = config_gen_module.ConfigurationGenerator

# Paths
yaml_path = project_root / "tests" / "fixtures" / "stripe_tax_config.yaml"
output_dir = project_root / "tmp" / "debug_xml_conversion"

# Clean and create output
import shutil
if output_dir.exists():
    shutil.rmtree(output_dir)
output_dir.mkdir(parents=True)

print("Step 1: Parsing YAML...")
parser = YAMLParser(str(yaml_path))
processor = parser.parse()
print(f"✅ Processor: {processor.name}")

print("\nStep 2: Analyzing metadata...")
requirements = MetadataAnalyzer.analyze_processor(processor)
print(f"✅ Catalogs: {len(requirements.catalogs)}")

print("\nStep 3: Generating Processor XML...")
processor_xml_dir = output_dir / "processor_xml"
processor_gen = ProcessorGenerator(processor)
processor_gen.generate(str(processor_xml_dir))
print(f"✅ Processor XML: {processor_xml_dir}")

print("\nStep 4: Generating Configuration...")
config_dir_output = output_dir / "configuration_output"
config_gen = ConfigurationGenerator(processor, requirements)
config_dir = config_gen.generate_configuration(config_dir_output, processor_xml_dir)
print(f"✅ Configuration: {config_dir}")

print("\n" + "="*80)
print("Generated files:")
print("="*80)

# Show DataProcessor XML location
dp_xml = config_dir / "DataProcessors" / f"{processor.name}.xml"
print(f"\nDataProcessor XML: {dp_xml}")
if dp_xml.exists():
    print(f"File size: {dp_xml.stat().st_size} bytes")
    print(f"\nFirst 50 lines:")
    print("-" * 80)
    lines = dp_xml.read_text(encoding='utf-8').split('\n')[:50]
    for i, line in enumerate(lines, 1):
        print(f"{i:3}: {line}")
