"""
Debug скрипт для діагностики EPF компіляції складних обробок

Використання:
    python scripts/debug_epf_compilation.py

Що робить:
- Генерує XML з stripe_tax_config.yaml
- Компілює в EPF з детальним логуванням
- Зберігає всі логи Designer
- Виводить детальну діагностичну інформацію
"""

import sys
from pathlib import Path
import time
import logging

# Додаємо шлях до модулів
sys.path.insert(0, str(Path(__file__).parent.parent))

import importlib
yaml_parser = importlib.import_module("1c_processor_generator.yaml_parser")
generator_module = importlib.import_module("1c_processor_generator.generator")
epf_compiler_module = importlib.import_module("1c_processor_generator.epf_compiler")

parse_yaml_config = yaml_parser.parse_yaml_config
ProcessorGenerator = generator_module.ProcessorGenerator
EPFCompiler = epf_compiler_module.EPFCompiler

# Налаштування логування
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('debug_epf_compilation.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


def analyze_xml_structure(processor_root: Path, processor_name: str):
    """Аналіз структури згенерованого XML"""
    logger.info("=" * 80)
    logger.info("АНАЛІЗ СТРУКТУРИ XML")
    logger.info("=" * 80)

    main_xml = processor_root / f"{processor_name}.xml"
    form_xml = processor_root / processor_name / "Forms" / "Форма" / "Ext" / "Form.xml"
    form_meta_xml = processor_root / processor_name / "Forms" / "Форма.xml"
    form_module = processor_root / processor_name / "Forms" / "Форма" / "Ext" / "Form" / "Module.bsl"

    files_info = {
        "Main XML": main_xml,
        "Form Meta XML": form_meta_xml,
        "Form Structure XML": form_xml,
        "Form Module BSL": form_module,
    }

    for name, file_path in files_info.items():
        if file_path.exists():
            size = file_path.stat().st_size
            logger.info(f"✓ {name}: {size:,} bytes ({size / 1024:.1f} KB)")

            # Перевірка кодування для XML
            if file_path.suffix == ".xml":
                with open(file_path, "rb") as f:
                    first_bytes = f.read(3)
                    has_bom = first_bytes == b'\xef\xbb\xbf'
                    logger.info(f"  └─ UTF-8 BOM: {'✓ Є' if has_bom else '✗ Відсутній'}")

                # Базова валідація XML
                try:
                    import xml.etree.ElementTree as ET
                    tree = ET.parse(file_path)
                    root = tree.getroot()
                    logger.info(f"  └─ XML валідний: ✓ Root tag: {root.tag.split('}')[-1]}")
                except Exception as e:
                    logger.error(f"  └─ XML ПОМИЛКА: {e}")
        else:
            logger.warning(f"✗ {name}: НЕ ЗНАЙДЕНО")

    logger.info("")


def test_compilation_with_persistent_ib(
    xml_root: Path,
    output_epf: Path,
    designer_path: str = None,
    timeout: int = 300
):
    """Тест компіляції з persistent IB"""
    logger.info("=" * 80)
    logger.info("ТЕСТ 1: Компіляція з Persistent IB (default)")
    logger.info("=" * 80)

    compiler = EPFCompiler(designer_path, use_persistent_ib=True)

    if not compiler.designer_path:
        logger.error("✗ Designer не знайдено!")
        return False

    logger.info(f"Designer: {compiler.designer_path}")
    logger.info(f"Timeout: {timeout}s")
    logger.info(f"XML: {xml_root}")
    logger.info(f"Output: {output_epf}")
    logger.info("")

    start_time = time.time()
    result = compiler.compile_epf(xml_root, output_epf, timeout=timeout)
    elapsed = time.time() - start_time

    logger.info(f"Час виконання: {elapsed:.1f}s")
    logger.info(f"Результат: {'✓ УСПІХ' if result else '✗ ПОМИЛКА'}")

    if output_epf.exists():
        size = output_epf.stat().st_size
        logger.info(f"EPF створено: {size:,} bytes ({size / 1024:.1f} KB)")
    else:
        logger.error("EPF файл НЕ створено")

    logger.info("")
    return result


def test_compilation_without_persistent_ib(
    xml_root: Path,
    output_epf: Path,
    designer_path: str = None,
    timeout: int = 300
):
    """Тест компіляції без persistent IB (тимчасова база)"""
    logger.info("=" * 80)
    logger.info("ТЕСТ 2: Компіляція без Persistent IB (тимчасова база)")
    logger.info("=" * 80)

    # Видаляємо попередній EPF якщо існує
    if output_epf.exists():
        output_epf.unlink()
        logger.info("Попередній EPF видалено")

    compiler = EPFCompiler(designer_path, use_persistent_ib=False)

    logger.info(f"Designer: {compiler.designer_path}")
    logger.info(f"Timeout: {timeout}s")
    logger.info("")

    start_time = time.time()
    result = compiler.compile_epf(xml_root, output_epf, timeout=timeout)
    elapsed = time.time() - start_time

    logger.info(f"Час виконання: {elapsed:.1f}s")
    logger.info(f"Результат: {'✓ УСПІХ' if result else '✗ ПОМИЛКА'}")

    if output_epf.exists():
        size = output_epf.stat().st_size
        logger.info(f"EPF створено: {size:,} bytes ({size / 1024:.1f} KB)")
    else:
        logger.error("EPF файл НЕ створено")

    logger.info("")
    return result


def main():
    """Головна функція"""
    logger.info("🔍 DEBUG: EPF компіляція для ТестированиеStripeTax")
    logger.info("=" * 80)
    logger.info("")

    # Шляхи
    project_root = Path(__file__).parent.parent
    fixtures_dir = project_root / "tests" / "fixtures"
    output_dir = project_root / "tmp" / "debug_epf"

    yaml_path = fixtures_dir / "stripe_tax_config.yaml"

    # Створюємо output директорію
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"YAML конфігурація: {yaml_path}")
    logger.info(f"Вихідна директорія: {output_dir}")
    logger.info("")

    # Перевірка існування YAML
    if not yaml_path.exists():
        logger.error(f"✗ YAML файл не знайдено: {yaml_path}")
        sys.exit(1)

    # ========================================
    # КРОК 1: Парсинг YAML
    # ========================================
    logger.info("=" * 80)
    logger.info("КРОК 1: Парсинг YAML конфігурації")
    logger.info("=" * 80)

    try:
        processor = parse_yaml_config(yaml_path, handlers_dir=None)
        logger.info(f"✓ Processor створено: {processor.name}")
        logger.info(f"  ├─ Атрибутів: {len(processor.attributes)}")

        form = processor.get_default_form()
        logger.info(f"  ├─ ValueTables: {len(form.value_table_attributes)}")
        logger.info(f"  ├─ Команд: {len(form.commands)}")
        logger.info(f"  └─ Елементів форми: {len(form.elements)}")
        logger.info("")
    except Exception as e:
        logger.error(f"✗ Помилка парсингу YAML: {e}", exc_info=True)
        sys.exit(1)

    # ========================================
    # КРОК 2: Генерація XML
    # ========================================
    logger.info("=" * 80)
    logger.info("КРОК 2: Генерація XML")
    logger.info("=" * 80)

    try:
        generator = ProcessorGenerator(processor)
        processor_root = generator.generate(str(output_dir), dry_run=False)

        if not processor_root:
            logger.error("✗ Помилка генерації XML")
            sys.exit(1)

        logger.info(f"✓ XML згенеровано: {processor_root}")
        logger.info("")

        # Аналіз структури
        analyze_xml_structure(processor_root, processor.name)

    except Exception as e:
        logger.error(f"✗ Помилка генерації XML: {e}", exc_info=True)
        sys.exit(1)

    # ========================================
    # КРОК 3: Компіляція EPF (Persistent IB)
    # ========================================
    xml_root = processor_root / f"{processor.name}.xml"
    epf_path_1 = output_dir / f"{processor.name}_persistent.epf"

    result_1 = test_compilation_with_persistent_ib(
        xml_root,
        epf_path_1,
        timeout=300
    )

    # ========================================
    # КРОК 4: Компіляція EPF (Temp IB)
    # ========================================
    epf_path_2 = output_dir / f"{processor.name}_temp.epf"

    result_2 = test_compilation_without_persistent_ib(
        xml_root,
        epf_path_2,
        timeout=300
    )

    # ========================================
    # ПІДСУМКИ
    # ========================================
    logger.info("=" * 80)
    logger.info("ПІДСУМКИ")
    logger.info("=" * 80)

    logger.info(f"XML генерація: ✓ УСПІШНО")
    logger.info(f"EPF компіляція (Persistent IB): {'✓ УСПІШНО' if result_1 else '✗ ПОМИЛКА'}")
    logger.info(f"EPF компіляція (Temp IB): {'✓ УСПІШНО' if result_2 else '✗ ПОМИЛКА'}")
    logger.info("")

    if result_1 or result_2:
        logger.info("🎉 Хоча б одна компіляція успішна!")
        logger.info(f"   Перевірте EPF файли в: {output_dir}")
    else:
        logger.error("❌ Обидві компіляції зазнали невдачі")
        logger.error("   Перевірте логи вище для деталей")
        logger.error(f"   Повний лог збережено: debug_epf_compilation.log")

    logger.info("")
    logger.info("=" * 80)

    sys.exit(0 if (result_1 or result_2) else 1)


if __name__ == "__main__":
    main()
