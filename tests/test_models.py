"""
Unit тести для models.py
"""

import pytest
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import importlib
models = importlib.import_module("1c_processor_generator.models")

generate_uuid = models.generate_uuid
Column = models.Column
TabularSection = models.TabularSection
Attribute = models.Attribute
FormElement = models.FormElement
FormGroup = models.FormGroup
Command = models.Command
ValueTableAttribute = models.ValueTableAttribute
Processor = models.Processor


class TestGenerateUUID:
    """Тести для generate_uuid()"""

    def test_uuid_format(self):
        """UUID має відповідати формату xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"""
        uuid = generate_uuid()
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        assert re.match(uuid_pattern, uuid), f"UUID {uuid} не відповідає формату"

    def test_uuid_lowercase(self):
        """UUID має бути lowercase"""
        uuid = generate_uuid()
        assert uuid == uuid.lower(), "UUID має бути lowercase"

    def test_uuid_uniqueness(self):
        """Генеровані UUID мають бути унікальними"""
        uuids = [generate_uuid() for _ in range(100)]
        assert len(uuids) == len(set(uuids)), "UUID мають бути унікальними"


class TestColumn:
    """Тести для Column dataclass"""

    def test_column_creation(self):
        """Створення колонки з мінімальними параметрами"""
        col = Column(name="Название", type="string")
        assert col.name == "Название"
        assert col.type == "string"
        assert col.synonym_ru == "Название"  # Автоматично з __post_init__
        assert col.synonym_uk == "Название"
        assert col.uuid is not None

    def test_column_with_synonyms(self):
        """Створення колонки з синонімами"""
        col = Column(
            name="Name",
            type="string",
            synonym_ru="Название",
            synonym_uk="Назва",
        )
        assert col.synonym_ru == "Название"
        assert col.synonym_uk == "Назва"

    def test_column_with_length(self):
        """Створення колонки string з довжиною"""
        col = Column(name="Text", type="string", length=100)
        assert col.length == 100

    def test_column_with_number_qualifiers(self):
        """Створення колонки number з кваліфікаторами"""
        col = Column(name="Amount", type="number", digits=15, fraction_digits=2)
        assert col.digits == 15
        assert col.fraction_digits == 2


class TestTabularSection:
    """Тести для TabularSection dataclass"""

    def test_tabular_section_creation(self):
        """Створення табличної частини"""
        ts = TabularSection(name="Lines")
        assert ts.name == "Lines"
        assert ts.synonym_ru == "Lines"
        assert ts.synonym_uk == "Lines"
        assert len(ts.columns) == 0
        assert ts.uuid is not None
        assert ts.type_id is not None
        assert ts.value_id is not None
        assert ts.row_type_id is not None
        assert ts.row_value_id is not None

    def test_tabular_section_with_columns(self):
        """Таблична частина з колонками"""
        ts = TabularSection(name="Lines")
        ts.columns.append(Column(name="Product", type="string"))
        ts.columns.append(Column(name="Quantity", type="number"))
        assert len(ts.columns) == 2


class TestAttribute:
    """Тести для Attribute dataclass"""

    def test_attribute_creation(self):
        """Створення атрибута"""
        attr = Attribute(name="Title", type="string")
        assert attr.name == "Title"
        assert attr.type == "string"
        assert attr.synonym_ru == "Title"
        assert attr.synonym_uk == "Title"
        assert attr.uuid is not None

    def test_attribute_with_length(self):
        """Атрибут string з довжиною"""
        attr = Attribute(name="Description", type="string", length=500)
        assert attr.length == 500


class TestFormElement:
    """Тести для FormElement dataclass"""

    def test_input_field_element(self):
        """InputField елемент"""
        elem = FormElement(
            element_type="InputField",
            name="TitleField",
            attribute="Title",
        )
        assert elem.element_type == "InputField"
        assert elem.name == "TitleField"
        assert elem.attribute == "Title"

    def test_button_element(self):
        """Button елемент"""
        elem = FormElement(
            element_type="Button",
            name="ExecuteButton",
            command="Execute",
        )
        assert elem.element_type == "Button"
        assert elem.command == "Execute"

    def test_table_element(self):
        """Table елемент"""
        elem = FormElement(
            element_type="Table",
            name="LinesTable",
            tabular_section="Lines",
        )
        assert elem.element_type == "Table"
        assert elem.tabular_section == "Lines"

    def test_element_with_events(self):
        """Елемент з обробниками подій"""
        elem = FormElement(
            element_type="InputField",
            name="Field",
            attribute="Value",
            event_handlers={"OnChange": "FieldOnChange"},
        )
        assert "OnChange" in elem.event_handlers
        assert elem.event_handlers["OnChange"] == "FieldOnChange"


class TestCommand:
    """Тести для Command dataclass"""

    def test_command_creation(self):
        """Створення команди"""
        cmd = Command(
            name="Execute",
            title_ru="Выполнить",
            title_uk="Виконати",
            action="ExecuteAction",
        )
        assert cmd.name == "Execute"
        assert cmd.title_ru == "Выполнить"
        assert cmd.title_uk == "Виконати"
        assert cmd.action == "ExecuteAction"
        assert cmd.uuid is not None

    def test_command_with_picture(self):
        """Команда з картинкою"""
        cmd = Command(
            name="Refresh",
            title_ru="Обновить",
            title_uk="Оновити",
            action="RefreshData",
            picture="StdPicture.Refresh",
        )
        assert cmd.picture == "StdPicture.Refresh"

    def test_command_with_shortcut(self):
        """Команда з гарячою клавішею"""
        cmd = Command(
            name="Save",
            title_ru="Сохранить",
            title_uk="Зберегти",
            action="SaveData",
            shortcut="F5",
        )
        assert cmd.shortcut == "F5"


class TestValueTableAttribute:
    """Тести для ValueTableAttribute dataclass"""

    def test_value_table_creation(self):
        """Створення ValueTable атрибута"""
        vt = ValueTableAttribute(
            name="Results",
            title_ru="Результаты",
            title_uk="Результати",
        )
        assert vt.name == "Results"
        assert vt.title_ru == "Результаты"
        assert len(vt.columns) == 0
        assert vt.id == 1  # Default ID

    def test_value_table_with_columns(self):
        """ValueTable з колонками"""
        vt = ValueTableAttribute(name="Data")
        vt.columns.append(Column(name="Value", type="string"))
        assert len(vt.columns) == 1


class TestProcessor:
    """Тести для Processor dataclass"""

    def test_processor_creation(self):
        """Створення процесора"""
        processor = Processor(name="TestProcessor")
        assert processor.name == "TestProcessor"
        assert processor.synonym_ru == "TestProcessor"  # __post_init__
        assert processor.synonym_uk == "TestProcessor"
        assert processor.platform_version == "2.11"  # Default
        assert processor.main_uuid is not None
        assert processor.object_id is not None
        assert processor.form_uuid is not None

    def test_processor_with_synonyms(self):
        """Процесор з синонімами"""
        processor = Processor(
            name="Processor",
            synonym_ru="Процессор",
            synonym_uk="Процесор",
        )
        assert processor.synonym_ru == "Процессор"
        assert processor.synonym_uk == "Процесор"

    def test_add_attribute(self):
        """Додавання атрибута"""
        processor = Processor(name="Test")
        attr = processor.add_attribute(name="Title", type="string", length=100)
        assert len(processor.attributes) == 1
        assert processor.attributes[0].name == "Title"
        assert isinstance(attr, Attribute)

    def test_add_tabular_section(self):
        """Додавання табличної частини"""
        processor = Processor(name="Test")
        ts = processor.add_tabular_section(name="Lines")
        assert len(processor.tabular_sections) == 1
        assert processor.tabular_sections[0].name == "Lines"
        assert isinstance(ts, TabularSection)

    def test_add_form_element(self):
        """Додавання елемента форми"""
        processor = Processor(name="Test")
        form = processor.add_form(name="Форма", default=True)
        elem = FormElement(
            element_type="InputField",
            name="Field",
            attribute="Value",
        )
        form.elements.append(elem)
        assert len(form.elements) == 1
        assert form.elements[0].element_type == "InputField"
        assert isinstance(elem, FormElement)

    def test_add_command(self):
        """Додавання команди"""
        processor = Processor(name="Test")
        form = processor.add_form(name="Форма", default=True)
        cmd = Command(
            name="Execute",
            title_ru="Выполнить",
            title_uk="Виконати",
            action="ExecuteAction",
        )
        form.commands.append(cmd)
        assert len(form.commands) == 1
        assert form.commands[0].name == "Execute"
        assert isinstance(cmd, Command)

    def test_add_form_event(self):
        """Додавання події форми"""
        processor = Processor(name="Test")
        form = processor.add_form(name="Форма", default=True)
        form.events["OnOpen"] = "OnOpenHandler"
        assert "OnOpen" in form.events
        assert form.events["OnOpen"] == "OnOpenHandler"

    def test_set_form_property(self):
        """Встановлення властивості форми"""
        processor = Processor(name="Test")
        form = processor.add_form(name="Форма", default=True)
        form.properties["Title"] = "Test Form"
        assert "Title" in form.properties
        assert form.properties["Title"] == "Test Form"

    def test_add_value_table_attribute(self):
        """Додавання ValueTable атрибута"""
        processor = Processor(name="Test")
        form = processor.add_form(name="Форма", default=True)
        vt = ValueTableAttribute(
            name="Results",
            title_ru="Результаты",
        )
        form.value_table_attributes.append(vt)
        assert len(form.value_table_attributes) == 1
        assert form.value_table_attributes[0].name == "Results"
        assert isinstance(vt, ValueTableAttribute)

    def test_processor_complex_structure(self):
        """Процесор зі складною структурою"""
        processor = Processor(name="ComplexProcessor")

        # Атрибути
        processor.add_attribute(name="Title", type="string")
        processor.add_attribute(name="Date", type="date")

        # Таблична частина
        ts = processor.add_tabular_section(name="Lines")
        ts.columns.append(Column(name="Product", type="string"))

        # Форма
        form = processor.add_form(name="Форма", default=True)

        # ValueTable
        vt = ValueTableAttribute(name="Results")
        vt.columns.append(Column(name="Value", type="number"))
        form.value_table_attributes.append(vt)

        # Елементи форми
        form.elements.append(FormElement(element_type="InputField", name="TitleField", attribute="Title"))
        form.elements.append(FormElement(element_type="Table", name="LinesTable", tabular_section="Lines"))

        # Команди
        form.commands.append(Command(name="Execute", title_ru="Выполнить", title_uk="Виконати", action="ExecuteAction"))

        # Події
        form.events["OnOpen"] = "OnOpenHandler"

        # Перевірки
        assert len(processor.attributes) == 2
        assert len(processor.tabular_sections) == 1
        assert len(form.value_table_attributes) == 1
        assert len(form.elements) == 2
        assert len(form.commands) == 1
        assert len(form.events) == 1


class TestFormGroup:
    """Тести для FormGroup dataclass"""

    def test_usual_group_creation(self):
        """Створення UsualGroup"""
        group = FormGroup(
            group_type="UsualGroup",
            name="MainGroup",
            title_ru="Основная группа",
        )
        assert group.group_type == "UsualGroup"
        assert group.name == "MainGroup"
        assert group.title_ru == "Основная группа"

    def test_group_with_child_items(self):
        """Група з вкладеними елементами"""
        group = FormGroup(group_type="UsualGroup", name="Group")
        # Child items можуть бути додані пізніше
        assert len(group.child_items) == 0
