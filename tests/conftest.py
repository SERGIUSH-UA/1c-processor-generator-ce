"""
Pytest конфігурація та загальні fixtures для тестів
"""

import pytest
from pathlib import Path
import tempfile
import shutil
from typing import Generator
import sys

# Додаємо батьківську директорію в sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

import importlib
models = importlib.import_module("1c_processor_generator.models")

Processor = models.Processor
Attribute = models.Attribute
TabularSection = models.TabularSection
Column = models.Column
FormElement = models.FormElement
Command = models.Command
ValueTableAttribute = models.ValueTableAttribute


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Тимчасова директорія для тестів"""
    tmp = Path(tempfile.mkdtemp())
    yield tmp
    # Cleanup
    if tmp.exists():
        shutil.rmtree(tmp)


@pytest.fixture
def fixtures_dir() -> Path:
    """Директорія з тестовими fixtures"""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def simple_processor() -> Processor:
    """Простий процесор для тестування"""
    processor = Processor(
        name="ТестовыйПроцессор",
        synonym_ru="Тестовый процессор",
        synonym_uk="Тестовий процесор",
    )

    # Додаємо атрибут
    processor.add_attribute(
        name="ТекстоваяСтрока",
        type="string",
        synonym_ru="Текстовая строка",
        synonym_uk="Текстовий рядок",
        length=100,
    )

    # Створюємо форму
    form = processor.add_form(name="Форма", default=True)

    # Додаємо поле вводу
    form.elements.append(FormElement(
        element_type="InputField",
        name="ТекстоваяСтрокаПоле",
        attribute="ТекстоваяСтрока",
    ))

    # Додаємо команду
    form.commands.append(Command(
        name="ВыполнитьДействие",
        title_ru="Выполнить действие",
        title_uk="Виконати дію",
        action="ВыполнитьДействие",
    ))

    # Додаємо кнопку
    form.elements.append(FormElement(
        element_type="Button",
        name="ВыполнитьДействиеКнопка",
        command="ВыполнитьДействие",
    ))

    return processor


@pytest.fixture
def complex_processor() -> Processor:
    """Складний процесор з табличними частинами"""
    processor = Processor(
        name="СложныйПроцессор",
        synonym_ru="Сложный процессор",
        synonym_uk="Складний процесор",
    )

    # Додаємо атрибути
    processor.add_attribute(
        name="Заголовок",
        type="string",
        synonym_ru="Заголовок",
        synonym_uk="Заголовок",
        length=200,
    )

    processor.add_attribute(
        name="Дата",
        type="date",
        synonym_ru="Дата",
        synonym_uk="Дата",
    )

    # Додаємо табличну частину
    ts = processor.add_tabular_section(
        name="Строки",
        synonym_ru="Строки",
        synonym_uk="Рядки",
    )

    ts.columns.append(Column(
        name="Номенклатура",
        type="CatalogRef.Номенклатура",
        synonym_ru="Номенклатура",
        synonym_uk="Номенклатура",
    ))

    ts.columns.append(Column(
        name="Количество",
        type="number",
        synonym_ru="Количество",
        synonym_uk="Кількість",
        digits=10,
        fraction_digits=2,
    ))

    # Створюємо форму
    form = processor.add_form(name="Форма", default=True)

    # Додаємо ValueTable до форми
    vt = ValueTableAttribute(
        name="Результаты",
        title_ru="Результаты",
        title_uk="Результати",
    )

    vt.columns.append(Column(
        name="Описание",
        type="string",
        synonym_ru="Описание",
        synonym_uk="Опис",
        length=300,
    ))

    form.value_table_attributes.append(vt)

    # Додаємо елементи форми
    form.elements.append(FormElement(
        element_type="InputField",
        name="ЗаголовокПоле",
        attribute="Заголовок",
    ))

    form.elements.append(FormElement(
        element_type="Table",
        name="СтрокиТаблица",
        tabular_section="Строки",
    ))

    form.elements.append(FormElement(
        element_type="Table",
        name="РезультатыТаблица",
        tabular_section="Результаты",
        properties={"is_value_table": True},
    ))

    # Додаємо події форми
    form.events["OnOpen"] = "ПриОткрытии"

    return processor


@pytest.fixture
def valid_uuids() -> list:
    """Список валідних UUID"""
    return [
        "12345678-1234-1234-1234-123456789abc",
        "abcdef12-3456-7890-abcd-ef1234567890",
        "00000000-0000-0000-0000-000000000000",
        "ffffffff-ffff-ffff-ffff-ffffffffffff",
    ]


@pytest.fixture
def invalid_uuids() -> list:
    """Список невалідних UUID"""
    return [
        "12345678-1234-1234-1234-12345678ZABC",  # Невалідний символ Z
        "12345678-1234-1234-1234",  # Занадто короткий
        "12345678-1234-1234-1234-123456789abc-extra",  # Занадто довгий
        "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",  # Невалідні символи
        "",  # Порожній
    ]


@pytest.fixture
def valid_identifiers() -> list:
    """Список валідних ідентифікаторів 1C"""
    return [
        "ПростоИмя",
        "СложноеИмяСЦифрами123",
        "_ПриватноеИмя",
        "Simple",
        "MixedЛатинКириллица",  # Тільки російська кирилиця (без української і, ї, є, ґ)
    ]


@pytest.fixture
def invalid_identifiers() -> list:
    """Список невалідних ідентифікаторів 1C"""
    return [
        "123Начинается",  # Починається з цифри
        "Містить Пробіл",
        "Містить-Дефіс",
        "Містить.Точку",
        "",  # Порожній
    ]


@pytest.fixture
def valid_types() -> list:
    """Список валідних типів даних"""
    return [
        "string",
        "number",
        "date",
        "boolean",
        "xs:string",
        "xs:decimal",
        "xs:dateTime",
        "xs:boolean",
        "CatalogRef.Номенклатура",
        "cfg:CatalogRef.Пользователи",
        "DocumentRef.ПриходнаяНакладная",
        "cfg:DocumentRef.РасходнаяНакладная",
    ]


@pytest.fixture
def invalid_types() -> list:
    """Список невалідних типів даних"""
    return [
        "invalid_type",
        "Catalog.Номенклатура",  # Має бути CatalogRef
        "Document.Накладная",  # Має бути DocumentRef
        "",
    ]


# ============================================================================
# EPF Compiler Fixtures (v2.8.0)
# ============================================================================

@pytest.fixture
def mock_designer_path(tmp_path) -> Path:
    """Mock шлях до Designer (1cv8.exe)"""
    designer_dir = tmp_path / "1cv8" / "8.3.25.1394" / "bin"
    designer_dir.mkdir(parents=True)
    designer = designer_dir / "1cv8.exe"
    designer.touch()
    return designer


@pytest.fixture
def mock_xml_root(tmp_path) -> Path:
    """Mock XML структура процесора"""
    xml_dir = tmp_path / "ТестовыйПроцессор"
    xml_dir.mkdir()

    # Створюємо мінімальний валідний XML
    xml_file = xml_dir / "ТестовыйПроцессор.xml"
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<MetaDataObject xmlns="http://v8.1c.ru/8.3/MDClasses" xmlns:app="http://v8.1c.ru/8.2/managed-application/core">
  <ExternalDataProcessor uuid="12345678-1234-1234-1234-123456789abc">
    <Properties>
      <Name>ТестовыйПроцессор</Name>
      <Synonym>
        <v8:item>
          <v8:lang>ru</v8:lang>
          <v8:content>Тестовый процессор</v8:content>
        </v8:item>
      </Synonym>
    </Properties>
  </ExternalDataProcessor>
</MetaDataObject>"""
    xml_file.write_text(xml_content, encoding="utf-8")
    return xml_file


@pytest.fixture
def mock_registry_data() -> dict:
    """Mock дані Windows реєстру для тестування пошуку Designer"""
    return {
        "8.3.25.1394": "C:/Program Files/1cv8/8.3.25.1394",
        "8.3.24.1537": "C:/Program Files/1cv8/8.3.24.1537",
        "8.3.23.1880": "C:/Program Files/1cv8/8.3.23.1880",
    }


@pytest.fixture
def mock_subprocess_result():
    """Mock результат subprocess.run для успішної компіляції"""
    from unittest.mock import Mock

    result = Mock()
    result.returncode = 0
    result.stdout = "Загрузка внешней обработки завершена успешно"
    result.stderr = ""
    return result


@pytest.fixture(scope="session")
def real_designer_path():
    """Знаходить справжній Designer в системі (для інтеграційних тестів)"""
    try:
        import importlib
        epf_compiler = importlib.import_module("1c_processor_generator.epf_compiler")
        EPFCompiler = epf_compiler.EPFCompiler

        compiler = EPFCompiler()
        return compiler.designer_path
    except Exception:
        return None


def pytest_configure(config):
    """Реєстрація custom markers"""
    config.addinivalue_line(
        "markers", "integration: integration tests that require real 1C Designer"
    )
