"""
Integration тести для yaml_parser.py
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

import importlib
yaml_parser_module = importlib.import_module("1c_processor_generator.yaml_parser")
models_module = importlib.import_module("1c_processor_generator.models")

YAMLParser = yaml_parser_module.YAMLParser
parse_yaml_config = yaml_parser_module.parse_yaml_config
Processor = models_module.Processor


class TestYAMLParser:
    """Тести для YAMLParser"""

    def test_load_simple_yaml(self, fixtures_dir):
        """Завантаження простого YAML"""
        yaml_path = fixtures_dir / "simple_config.yaml"
        parser = YAMLParser(yaml_path)
        assert parser.load_yaml()
        assert "processor" in parser.config

    def test_load_complex_yaml(self, fixtures_dir):
        """Завантаження складного YAML"""
        yaml_path = fixtures_dir / "complex_config.yaml"
        parser = YAMLParser(yaml_path)
        assert parser.load_yaml()
        assert "processor" in parser.config
        assert "tabular_sections" in parser.config
        assert "forms" in parser.config

    def test_load_nonexistent_yaml(self, temp_dir):
        """Спроба завантажити неіснуючий файл"""
        yaml_path = temp_dir / "nonexistent.yaml"
        parser = YAMLParser(yaml_path)
        assert not parser.load_yaml()

    def test_parse_simple_config(self, fixtures_dir):
        """Парсинг простої конфігурації"""
        yaml_path = fixtures_dir / "simple_config.yaml"
        parser = YAMLParser(yaml_path)
        processor = parser.parse()

        assert processor is not None
        assert isinstance(processor, Processor)
        assert processor.name == "ТестовыйПроцессор"
        assert len(processor.attributes) == 2

        # Отримуємо форму
        form = processor.get_default_form()
        assert form is not None
        assert len(form.commands) == 1
        assert len(form.elements) == 3  # 2 InputFields + 1 Button

    def test_parse_complex_config(self, fixtures_dir):
        """Парсинг складної конфігурації"""
        yaml_path = fixtures_dir / "complex_config.yaml"
        parser = YAMLParser(yaml_path)
        processor = parser.parse()

        assert processor is not None
        assert processor.name == "СложныйПроцессор"
        assert len(processor.attributes) == 3
        assert len(processor.tabular_sections) == 1

        # Отримуємо форму
        form = processor.get_default_form()
        assert form is not None
        assert len(form.value_table_attributes) == 1
        assert len(form.commands) == 2

    def test_parse_attributes(self, fixtures_dir):
        """Парсинг атрибутів"""
        yaml_path = fixtures_dir / "simple_config.yaml"
        parser = YAMLParser(yaml_path)
        processor = parser.parse()

        # Перевіряємо атрибут ТекстоваяСтрока
        text_attr = next((a for a in processor.attributes if a.name == "ТекстоваяСтрока"), None)
        assert text_attr is not None
        assert text_attr.type == "string"
        assert text_attr.length == 100

        # Перевіряємо атрибут Число
        number_attr = next((a for a in processor.attributes if a.name == "Число"), None)
        assert number_attr is not None
        assert number_attr.type == "number"
        assert number_attr.digits == 10
        assert number_attr.fraction_digits == 2

    def test_parse_tabular_sections(self, fixtures_dir):
        """Парсинг табличних частин"""
        yaml_path = fixtures_dir / "complex_config.yaml"
        parser = YAMLParser(yaml_path)
        processor = parser.parse()

        ts = processor.tabular_sections[0]
        assert ts.name == "Строки"
        assert len(ts.columns) == 3

        # Перевіряємо колонки
        col_names = [col.name for col in ts.columns]
        assert "Номенклатура" in col_names
        assert "Количество" in col_names
        assert "Цена" in col_names

    def test_parse_value_tables(self, fixtures_dir):
        """Парсинг ValueTable"""
        yaml_path = fixtures_dir / "complex_config.yaml"
        parser = YAMLParser(yaml_path)
        processor = parser.parse()

        # Отримуємо форму
        form = processor.get_default_form()
        assert form is not None

        vt = form.value_table_attributes[0]
        assert vt.name == "Результаты"
        assert len(vt.columns) == 2

    def test_parse_form_elements(self, fixtures_dir):
        """Парсинг елементів форми"""
        yaml_path = fixtures_dir / "simple_config.yaml"
        parser = YAMLParser(yaml_path)
        processor = parser.parse()

        # Отримуємо форму
        form = processor.get_default_form()
        assert form is not None

        # Перевіряємо InputField
        input_field = next((e for e in form.elements if e.element_type == "InputField"), None)
        assert input_field is not None
        assert input_field.attribute is not None

        # Перевіряємо Button
        button = next((e for e in form.elements if e.element_type == "Button"), None)
        assert button is not None
        assert button.command is not None

    def test_parse_commands(self, fixtures_dir):
        """Парсинг команд"""
        yaml_path = fixtures_dir / "simple_config.yaml"
        parser = YAMLParser(yaml_path)
        processor = parser.parse()

        # Отримуємо форму
        form = processor.get_default_form()
        assert form is not None

        cmd = form.commands[0]
        assert cmd.name == "ВыполнитьДействие"
        assert cmd.title_ru == "Выполнить действие"
        assert cmd.title_uk == "Виконати дію"
        assert cmd.action == "ВыполнитьДействие"
        assert cmd.shortcut == "F5"

    def test_parse_form_events(self, fixtures_dir):
        """Парсинг подій форми"""
        yaml_path = fixtures_dir / "simple_config.yaml"
        parser = YAMLParser(yaml_path)
        processor = parser.parse()

        # Отримуємо форму
        form = processor.get_default_form()
        assert form is not None

        assert "OnOpen" in form.events
        assert form.events["OnOpen"] == "ПриОткрытии"

    def test_parse_with_handlers(self, fixtures_dir):
        """Парсинг з BSL handlers"""
        yaml_path = fixtures_dir / "simple_config.yaml"
        handlers_dir = fixtures_dir / "handlers"
        processor = parse_yaml_config(yaml_path, handlers_dir)

        assert processor is not None
        # Отримуємо форму
        form = processor.get_default_form()
        assert form is not None
        # BSL код має бути завантажений
        assert hasattr(form, "events_bsl")


class TestYAMLValidation:
    """Тести валідації YAML схеми"""

    def test_validate_simple_config(self, fixtures_dir):
        """Валідація простої конфігурації"""
        yaml_path = fixtures_dir / "simple_config.yaml"
        parser = YAMLParser(yaml_path)
        parser.load_yaml()
        # Якщо jsonschema встановлено, має пройти валідацію
        is_valid = parser.validate_schema()
        # Повертає True навіть якщо jsonschema не встановлено
        assert is_valid

    def test_validate_complex_config(self, fixtures_dir):
        """Валідація складної конфігурації"""
        yaml_path = fixtures_dir / "complex_config.yaml"
        parser = YAMLParser(yaml_path)
        parser.load_yaml()
        assert parser.validate_schema()


class TestFormElementParsing:
    """Тести парсингу різних типів елементів форми"""

    def test_parse_table_element(self, fixtures_dir):
        """Парсинг Table елемента"""
        yaml_path = fixtures_dir / "complex_config.yaml"
        parser = YAMLParser(yaml_path)
        processor = parser.parse()

        # Отримуємо форму
        form = processor.get_default_form()
        assert form is not None

        # Знаходимо Table елемент
        table = next((e for e in form.elements if e.element_type == "Table"), None)
        assert table is not None
        assert table.tabular_section is not None

    def test_parse_checkbox_element(self, fixtures_dir):
        """Парсинг CheckBoxField елемента"""
        yaml_path = fixtures_dir / "complex_config.yaml"
        parser = YAMLParser(yaml_path)
        processor = parser.parse()

        # Отримуємо форму
        form = processor.get_default_form()
        assert form is not None

        checkbox = next((e for e in form.elements if e.element_type == "CheckBoxField"), None)
        assert checkbox is not None
        assert checkbox.attribute == "Активен"

    def test_parse_table_with_events(self, fixtures_dir):
        """Парсинг Table з обробниками подій"""
        yaml_path = fixtures_dir / "complex_config.yaml"
        parser = YAMLParser(yaml_path)
        processor = parser.parse()

        # Отримуємо форму
        form = processor.get_default_form()
        assert form is not None

        table = next(
            (e for e in form.elements if e.name == "СтрокиТаблица"),
            None
        )
        assert table is not None
        assert "OnActivateRow" in table.event_handlers


class TestPopupParsing:
    """Тести парсингу Popup елементів"""

    def test_parse_simple_popup(self, temp_dir):
        """Парсинг простого Popup в AutoCommandBar"""
        yaml_content = """
processor:
  name: ТестPopup

forms:
  - name: Форма
    default: true
    commands:
      - name: КомандаТест
        title_ru: Команда тест
        title_uk: Команда тест
        handler: КомандаТест
    auto_command_bar:
      - type: Popup
        name: МенюДействия
        title_ru: Действия
        title_uk: Дії
        picture: StdPicture.ExecuteTask
        child_items:
          - type: Button
            name: КнопкаТест
            command: КомандаТест
    elements: []
"""
        yaml_path = temp_dir / "popup_test.yaml"
        yaml_path.write_text(yaml_content, encoding="utf-8")

        parser = YAMLParser(yaml_path)
        processor = parser.parse()

        assert processor is not None

        # Отримуємо форму
        form = processor.get_default_form()
        assert form is not None
        assert len(form.auto_command_bar_elements) == 1

        popup = form.auto_command_bar_elements[0]
        assert popup.element_type == "Popup"
        assert popup.name == "МенюДействия"
        assert popup.properties.get("title_ru") == "Действия"
        assert popup.properties.get("picture") == "StdPicture.ExecuteTask"
        assert len(popup.child_items) == 1

        button = popup.child_items[0]
        assert button.element_type == "Button"
        assert button.command == "КомандаТест"

    def test_parse_nested_popup(self, temp_dir):
        """Парсинг вкладених Popup елементів"""
        yaml_content = """
processor:
  name: ТестNestedPopup

forms:
  - name: Форма
    default: true
    commands:
      - name: Команда1
        title_ru: Команда 1
        title_uk: Команда 1
        handler: Команда1
      - name: Команда2
        title_ru: Команда 2
        title_uk: Команда 2
        handler: Команда2
    auto_command_bar:
      - type: Popup
        name: Меню1
        title_ru: Меню уровень 1
        child_items:
          - type: Popup
            name: Меню2
            title_ru: Меню уровень 2
            child_items:
              - type: Button
                name: Кнопка1
                command: Команда1
          - type: Button
            name: Кнопка2
            command: Команда2
    elements: []
"""
        yaml_path = temp_dir / "nested_popup_test.yaml"
        yaml_path.write_text(yaml_content, encoding="utf-8")

        parser = YAMLParser(yaml_path)
        processor = parser.parse()

        assert processor is not None

        # Отримуємо форму
        form = processor.get_default_form()
        assert form is not None
        assert len(form.auto_command_bar_elements) == 1

        popup1 = form.auto_command_bar_elements[0]
        assert popup1.element_type == "Popup"
        assert len(popup1.child_items) == 2

        # Перший child - вкладений Popup
        popup2 = popup1.child_items[0]
        assert popup2.element_type == "Popup"
        assert len(popup2.child_items) == 1

        # Другий child - Button
        button2 = popup1.child_items[1]
        assert button2.element_type == "Button"

    def test_parse_popup_with_representation(self, temp_dir):
        """Парсинг Popup з representation властивістю"""
        yaml_content = """
processor:
  name: ТестRepresentation

forms:
  - name: Форма
    default: true
    commands:
      - name: КомандаТест
        title_ru: Команда
        title_uk: Команда
        handler: КомандаТест
    auto_command_bar:
      - type: Popup
        name: МенюДействия
        title_ru: Действия
        representation: PictureAndText
        picture: StdPicture.More
        child_items:
          - type: Button
            name: КнопкаТест
            command: КомандаТест
    elements: []
"""
        yaml_path = temp_dir / "popup_repr_test.yaml"
        yaml_path.write_text(yaml_content, encoding="utf-8")

        parser = YAMLParser(yaml_path)
        processor = parser.parse()

        assert processor is not None

        # Отримуємо форму
        form = processor.get_default_form()
        assert form is not None

        popup = form.auto_command_bar_elements[0]
        assert popup.properties.get("representation") == "PictureAndText"
        assert popup.properties.get("picture") == "StdPicture.More"


class TestDynamicListParsing:
    """Тести парсингу DynamicList"""

    def test_parse_simple_dynamic_list(self, temp_dir):
        """Парсинг простого DynamicList (auto-query з main_table)"""
        yaml_content = """
processor:
  name: ТестПростогоСписка

forms:
  - name: Форма
    default: true
    dynamic_lists:
      - name: СписокДокументов
        title_ru: Список документов
        title_uk: Список документів
        main_table: Document.Заказ
    elements:
      - type: Table
        name: СписокДокументовТаблица
        tabular_section: СписокДокументов
        is_dynamic_list: true
"""
        yaml_path = temp_dir / "simple_dynamic_list_test.yaml"
        yaml_path.write_text(yaml_content, encoding="utf-8")

        parser = YAMLParser(yaml_path)
        processor = parser.parse()

        assert processor is not None

        # Отримуємо форму
        form = processor.get_default_form()
        assert form is not None

        # Перевіряємо DynamicList атрибут
        assert len(form.dynamic_list_attributes) == 1

        dl = form.dynamic_list_attributes[0]
        assert dl.name == "СписокДокументов"
        assert dl.title_ru == "Список документов"
        assert dl.title_uk == "Список документів"
        assert dl.main_table == "Document.Заказ"
        assert dl.manual_query is False
        assert dl.query_text is None or dl.query_text == ""
        assert len(dl.use_always_fields) == 0
        assert len(dl.columns) == 0

        # Перевіряємо Table елемент з is_dynamic_list
        table = next(
            (e for e in form.elements if e.element_type == "Table"),
            None
        )
        assert table is not None
        assert table.tabular_section == "СписокДокументов"
        assert table.properties.get("is_dynamic_list") is True

    def test_parse_complex_dynamic_list(self, temp_dir):
        """Парсинг складного DynamicList з manual_query, use_always_fields, columns"""
        yaml_content = """
processor:
  name: ТестСложногоСписка

forms:
  - name: Форма
    default: true
    dynamic_lists:
      - name: СписокПлатежей
        title_ru: Список платежей
        title_uk: Список платежів
        main_attribute: true
        manual_query: true
        main_table: Document.ПлатежноеПоручение
        query_text: |
          ВЫБРАТЬ
            Док.Ссылка,
            Док.Дата,
            Док.Номер,
            Док.Сумма
          ИЗ Документ.ПлатежноеПоручение КАК Док
        use_always_fields:
          - Ссылка
          - Дата
        columns:
          - field: Дата
            title_ru: Дата
            title_uk: Дата
            width: 12
          - field: Номер
            title_ru: Номер
            title_uk: Номер
            width: 8
          - field: Сумма
            title_ru: Сумма
            title_uk: Сума
            width: 15
    elements:
      - type: Table
        name: СписокПлатежейТаблица
        tabular_section: СписокПлатежей
        is_dynamic_list: true
"""
        yaml_path = temp_dir / "complex_dynamic_list_test.yaml"
        yaml_path.write_text(yaml_content, encoding="utf-8")

        parser = YAMLParser(yaml_path)
        processor = parser.parse()

        assert processor is not None

        # Отримуємо форму
        form = processor.get_default_form()
        assert form is not None

        # Перевіряємо DynamicList атрибут
        assert len(form.dynamic_list_attributes) == 1

        dl = form.dynamic_list_attributes[0]
        assert dl.name == "СписокПлатежей"
        assert dl.title_ru == "Список платежей"
        assert dl.title_uk == "Список платежів"
        assert dl.main_attribute is True
        assert dl.manual_query is True
        assert dl.main_table == "Document.ПлатежноеПоручение"
        assert "ВЫБРАТЬ" in dl.query_text
        assert "Документ.ПлатежноеПоручение" in dl.query_text

        # Перевіряємо use_always_fields
        assert len(dl.use_always_fields) == 2
        assert "Ссылка" in dl.use_always_fields
        assert "Дата" in dl.use_always_fields

        # Перевіряємо columns
        assert len(dl.columns) == 3
        assert dl.columns[0].field == "Дата"
        assert dl.columns[0].title_ru == "Дата"
        assert dl.columns[0].width == 12
        assert dl.columns[1].field == "Номер"
        assert dl.columns[1].width == 8
        assert dl.columns[2].field == "Сумма"
        assert dl.columns[2].width == 15

        # Перевіряємо Table елемент
        table = next(
            (e for e in form.elements if e.element_type == "Table"),
            None
        )
        assert table is not None
        assert table.tabular_section == "СписокПлатежей"
        assert table.properties.get("is_dynamic_list") is True

    def test_parse_dynamic_list_without_table_element(self, temp_dir):
        """Парсинг DynamicList без Table елемента на формі"""
        yaml_content = """
processor:
  name: ТестБезТаблицы

forms:
  - name: Форма
    default: true
    dynamic_lists:
      - name: СписокДокументов
        title_ru: Список документов
        main_table: Document.Заказ
        use_always_fields:
          - Ссылка
    elements:
      - type: LabelDecoration
        name: ПростаяМетка
        title_ru: Тест
        title_uk: Тест
"""
        yaml_path = temp_dir / "dynamic_list_no_table_test.yaml"
        yaml_path.write_text(yaml_content, encoding="utf-8")

        parser = YAMLParser(yaml_path)
        processor = parser.parse()

        assert processor is not None

        # Отримуємо форму
        form = processor.get_default_form()
        assert form is not None

        # DynamicList має бути створений
        assert len(form.dynamic_list_attributes) == 1
        dl = form.dynamic_list_attributes[0]
        assert dl.name == "СписокДокументов"
        assert len(dl.use_always_fields) == 1

        # Але Table елемента немає
        tables = [e for e in form.elements if e.element_type == "Table"]
        assert len(tables) == 0

    def test_dynamic_list_properties_structure(self, temp_dir):
        """Перевірка що is_dynamic_list читається як property"""
        yaml_content = """
processor:
  name: ТестСтруктурыProperties

forms:
  - name: Форма
    default: true
    dynamic_lists:
      - name: Список
        title_ru: Список
        main_table: Document.Test
    elements:
      - type: Table
        name: СписокТаблица
        tabular_section: Список
        is_dynamic_list: true
"""
        yaml_path = temp_dir / "properties_test.yaml"
        yaml_path.write_text(yaml_content, encoding="utf-8")

        parser = YAMLParser(yaml_path)
        processor = parser.parse()

        assert processor is not None

        # Отримуємо форму
        form = processor.get_default_form()
        assert form is not None

        table = form.elements[0]

        # Критично важливо: is_dynamic_list має бути в properties
        assert "is_dynamic_list" in table.properties
        assert table.properties["is_dynamic_list"] is True


class TestNewFormatParsing:
    """Тести парсингу нового формату (forms:)"""

    def test_correct_placement_inside_form(self, temp_dir):
        """form_attributes/value_tables правильно парсяться ВСЕРЕДИНІ форми"""
        yaml_content = """
processor:
  name: ТестПравильногоРазмещения

forms:
  - name: Form
    default: true
    form_attributes:
      - name: PreviewHTML
        type: spreadsheet_document
    value_tables:
      - name: DataTable
        columns:
          - name: Column1
            type: string
    elements:
      - type: LabelDecoration
        name: TestLabel
        title_ru: Test
        title_uk: Test
"""
        yaml_path = temp_dir / "correct_placement_test.yaml"
        yaml_path.write_text(yaml_content, encoding="utf-8")

        parser = YAMLParser(yaml_path)
        processor = parser.parse()

        assert processor is not None

        form = processor.get_default_form()
        assert form is not None
        assert len(form.form_attributes) == 1
        assert form.form_attributes[0].name == "PreviewHTML"
        assert len(form.value_table_attributes) == 1
        assert form.value_table_attributes[0].name == "DataTable"

    def test_events_commands_inside_form(self, temp_dir):
        """events, commands правильно парсяться ВСЕРЕДИНІ форми"""
        yaml_content = """
processor:
  name: ТестСобытийВнутриФормы

forms:
  - name: Form
    default: true
    events:
      OnOpen: ПриОткрытии
      OnClose: ПриЗакрытии
    commands:
      - name: Команда1
        title_ru: Команда 1
        title_uk: Команда 1
        handler: Команда1
    elements:
      - type: LabelDecoration
        name: TestLabel
        title_ru: Test
        title_uk: Test
"""
        yaml_path = temp_dir / "correct_events_test.yaml"
        yaml_path.write_text(yaml_content, encoding="utf-8")

        parser = YAMLParser(yaml_path)
        processor = parser.parse()

        assert processor is not None

        form = processor.get_default_form()
        assert form is not None
        assert len(form.events) == 2
        assert form.events["OnOpen"] == "ПриОткрытии"
        assert form.events["OnClose"] == "ПриЗакрытии"
        assert len(form.commands) == 1
        assert form.commands[0].name == "Команда1"
        assert len(form.elements) == 1
