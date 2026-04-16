"""
Скрипт для порівняння Configuration DataProcessor vs External DataProcessor
Допомагає знайти конфлікти UUID та назв
"""
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

def extract_uuids(xml_file):
    """Витягує всі UUID з XML файлу"""
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        # Шукаємо всі елементи з UUID
        uuids = []
        for elem in root.iter():
            # UUID в тегах
            if 'UUID' in elem.tag or elem.tag.endswith('Uuid'):
                if elem.text:
                    uuids.append((elem.tag, elem.text.strip()))
            
            # UUID в атрибутах
            for attr_name, attr_value in elem.attrib.items():
                if 'uuid' in attr_name.lower() or 'id' in attr_name.lower():
                    uuids.append((f"{elem.tag}@{attr_name}", attr_value))
        
        return uuids
    except Exception as e:
        return []

def compare_directories(config_dir, external_dir, output_file):
    """Порівнює два дерева XML файлів"""
    config_path = Path(config_dir)
    external_path = Path(external_dir)
    
    results = []
    results.append("="*80)
    results.append("ПОРІВНЯННЯ Configuration DataProcessor vs External DataProcessor")
    results.append("="*80)
    
    # Знаходимо всі XML файли в обох директоріях
    config_xmls = {f.name: f for f in config_path.rglob("*.xml")}
    external_xmls = {f.name: f for f in external_path.rglob("*.xml")}
    
    results.append(f"\nЗнайдено XML файлів:")
    results.append(f"  Configuration: {len(config_xmls)}")
    results.append(f"  External: {len(external_xmls)}")
    
    # Порівнюємо UUID
    all_config_uuids = {}
    all_external_uuids = {}
    
    for name, xml_file in config_xmls.items():
        uuids = extract_uuids(xml_file)
        for tag, uuid in uuids:
            if uuid not in all_config_uuids:
                all_config_uuids[uuid] = []
            all_config_uuids[uuid].append((name, tag))
    
    for name, xml_file in external_xmls.items():
        uuids = extract_uuids(xml_file)
        for tag, uuid in uuids:
            if uuid not in all_external_uuids:
                all_external_uuids[uuid] = []
            all_external_uuids[uuid].append((name, tag))
    
    # Знаходимо конфлікти UUID
    conflicts = set(all_config_uuids.keys()) & set(all_external_uuids.keys())
    
    results.append(f"\n{'='*80}")
    results.append(f"КОНФЛІКТИ UUID: {len(conflicts)}")
    results.append(f"{'='*80}")
    
    for uuid in sorted(conflicts):
        results.append(f"\n⚠️ UUID КОНФЛІКТ: {uuid}")
        results.append(f"  Configuration файли:")
        for name, tag in all_config_uuids[uuid]:
            results.append(f"    - {name}: {tag}")
        results.append(f"  External файли:")
        for name, tag in all_external_uuids[uuid]:
            results.append(f"    - {name}: {tag}")
    
    # Порівнюємо схожі файли
    common_files = set(config_xmls.keys()) & set(external_xmls.keys())
    
    results.append(f"\n{'='*80}")
    results.append(f"СПІЛЬНІ ФАЙЛИ: {len(common_files)}")
    results.append(f"{'='*80}")
    
    for name in sorted(common_files):
        results.append(f"\n📄 {name}")
        results.append(f"  Config:   {config_xmls[name]}")
        results.append(f"  External: {external_xmls[name]}")
    
    # Записуємо результат
    output = "\n".join(results)
    Path(output_file).write_text(output, encoding='utf-8')
    print(output)
    return len(conflicts)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python compare_config_vs_external.py <config_dataprocessor_dir> <external_processor_dir> [output_file]")
        sys.exit(1)
    
    config_dir = sys.argv[1]
    external_dir = sys.argv[2]
    output_file = sys.argv[3] if len(sys.argv) > 3 else "tmp/comparison_result.txt"
    
    conflicts = compare_directories(config_dir, external_dir, output_file)
    
    if conflicts > 0:
        print(f"\n❌ Знайдено {conflicts} конфліктів UUID!")
        sys.exit(1)
    else:
        print(f"\n✅ Конфліктів UUID не знайдено")
        sys.exit(0)
