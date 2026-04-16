"""
Тести для ElementPreparer (v2.38.0+)

Покриває:
- Підготовка різних типів елементів
- Рекурсивна обробка вкладених елементів
- Автоматична нумерація ID
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

import importlib
preparer_module = importlib.import_module("1c_processor_generator.element_preparer")
models_module = importlib.import_module("1c_processor_generator.models")
id_module = importlib.import_module("1c_processor_generator.id_allocator")

ElementPreparer = preparer_module.ElementPreparer
Processor = models_module.Processor
FormElement = models_module.FormElement
Column = models_module.Column
IDAllocator = id_module.IDAllocator


@pytest.fixture
def simple_processor():
    """Простий процесор для тестів."""
    processor = Processor(name="TestProcessor")
    form = processor.add_form(name="Форма", default=True)
    return processor


@pytest.fixture
def processor_with_tabular():
    """Процесор з табличною частиною."""
    processor = Processor(name="TestProcessor")
    ts = processor.add_tabular_section(name="ТабличнаЧастина")
    ts.columns.append(Column(name="Поле1", type="string"))
    ts.columns.append(Column(name="Поле2", type="number"))
    ts.columns.append(Column(name="Прапорець", type="boolean"))

    form = processor.add_form(name="Форма", default=True)
    return processor


class TestElementPreparerInit:
    """Тести ініціалізації ElementPreparer"""

    def test_init(self, simple_processor):
        """Ініціалізація ElementPreparer"""
        preparer = ElementPreparer(simple_processor)
        assert preparer.processor == simple_processor


class TestPrepareInputField:
    """Тести підготовки InputField"""

    def test_prepare_input_field(self, simple_processor):
        """Підготовка InputField елемента"""
        preparer = ElementPreparer(simple_processor)
        form = simple_processor.get_default_form()

        elem = FormElement(
            element_type="InputField",
            name="TestInput",
            attribute="TestAttr"
        )
        form.elements.append(elem)

        elements, next_id = preparer.prepare_form_elements(form)

        assert len(elements) == 1
        assert elements[0]["type"] == "InputField"
        assert elements[0]["name"] == "TestInput"
        assert elements[0]["attribute"] == "TestAttr"
        assert "id" in elements[0]

    def test_prepare_label_field(self, simple_processor):
        """Підготовка LabelField елемента"""
        preparer = ElementPreparer(simple_processor)
        form = simple_processor.get_default_form()

        elem = FormElement(
            element_type="LabelField",
            name="TestLabel",
            attribute="TestAttr"
        )
        form.elements.append(elem)

        elements, _ = preparer.prepare_form_elements(form)

        assert elements[0]["type"] == "LabelField"
        assert elements[0]["attribute"] == "TestAttr"


class TestPrepareButton:
    """Тести підготовки Button"""

    def test_prepare_button(self, simple_processor):
        """Підготовка Button елемента"""
        preparer = ElementPreparer(simple_processor)
        form = simple_processor.get_default_form()

        elem = FormElement(
            element_type="Button",
            name="TestButton",
            command="TestCommand"
        )
        form.elements.append(elem)

        elements, _ = preparer.prepare_form_elements(form)

        assert elements[0]["type"] == "Button"
        assert elements[0]["command"] == "TestCommand"


class TestPrepareGroup:
    """Тести підготовки UsualGroup"""

    def test_prepare_usual_group(self, simple_processor):
        """Підготовка UsualGroup з вкладеними елементами"""
        preparer = ElementPreparer(simple_processor)
        form = simple_processor.get_default_form()

        child1 = FormElement(element_type="InputField", name="Child1", attribute="Attr1")
        child2 = FormElement(element_type="Button", name="Child2", command="Cmd2")

        elem = FormElement(
            element_type="UsualGroup",
            name="TestGroup",
            child_items=[child1, child2]
        )
        form.elements.append(elem)

        elements, _ = preparer.prepare_form_elements(form)

        assert elements[0]["type"] == "UsualGroup"
        assert len(elements[0]["child_items"]) == 2
        assert elements[0]["child_items"][0]["type"] == "InputField"
        assert elements[0]["child_items"][1]["type"] == "Button"

    def test_prepare_nested_groups(self, simple_processor):
        """Підготовка вкладених UsualGroup"""
        preparer = ElementPreparer(simple_processor)
        form = simple_processor.get_default_form()

        inner_child = FormElement(element_type="InputField", name="InnerChild", attribute="Attr")
        inner_group = FormElement(
            element_type="UsualGroup",
            name="InnerGroup",
            child_items=[inner_child]
        )
        outer_group = FormElement(
            element_type="UsualGroup",
            name="OuterGroup",
            child_items=[inner_group]
        )
        form.elements.append(outer_group)

        elements, _ = preparer.prepare_form_elements(form)

        assert elements[0]["type"] == "UsualGroup"
        assert elements[0]["child_items"][0]["type"] == "UsualGroup"
        assert elements[0]["child_items"][0]["child_items"][0]["type"] == "InputField"


class TestPrepareTable:
    """Тести підготовки Table"""

    def test_prepare_table_with_tabular_section(self, processor_with_tabular):
        """Підготовка Table з TabularSection"""
        preparer = ElementPreparer(processor_with_tabular)
        form = processor_with_tabular.get_default_form()

        elem = FormElement(
            element_type="Table",
            name="TestTable",
            tabular_section="ТабличнаЧастина"
        )
        form.elements.append(elem)

        elements, _ = preparer.prepare_form_elements(form)

        assert elements[0]["type"] == "Table"
        assert elements[0]["tabular_section"] == "ТабличнаЧастина"
        assert elements[0]["is_value_table"] == False
        # Має бути колонки: НомерСтроки + 3 поля
        assert len(elements[0]["columns"]) == 4

    def test_prepare_table_columns_types(self, processor_with_tabular):
        """Перевірка типів колонок таблиці"""
        preparer = ElementPreparer(processor_with_tabular)
        form = processor_with_tabular.get_default_form()

        elem = FormElement(
            element_type="Table",
            name="TestTable",
            tabular_section="ТабличнаЧастина"
        )
        form.elements.append(elem)

        elements, _ = preparer.prepare_form_elements(form)

        columns = elements[0]["columns"]
        # НомерСтроки
        assert columns[0]["type"] == "LineNumber"
        # Поле1, Поле2 - InputField
        assert columns[1]["type"] == "InputField"
        assert columns[2]["type"] == "InputField"
        # Прапорець - CheckBox (boolean)
        assert columns[3]["type"] == "CheckBox"


class TestPreparePages:
    """Тести підготовки Pages"""

    def test_prepare_pages(self, simple_processor):
        """Підготовка Pages з Page елементами"""
        preparer = ElementPreparer(simple_processor)
        form = simple_processor.get_default_form()

        child_elem = FormElement(element_type="InputField", name="PageChild", attribute="Attr")

        # Page елементи тепер FormElement (не dict)
        page1 = FormElement(element_type="Page", name="Page1", properties={})
        page1.child_items.append(child_elem)

        page2 = FormElement(element_type="Page", name="Page2", properties={})

        elem = FormElement(
            element_type="Pages",
            name="TestPages",
            child_items=[page1, page2]
        )
        form.elements.append(elem)

        elements, _ = preparer.prepare_form_elements(form)

        assert elements[0]["type"] == "Pages"
        assert len(elements[0]["page_items"]) == 2
        assert elements[0]["page_items"][0]["name"] == "Page1"
        assert len(elements[0]["page_items"][0]["child_items"]) == 1


class TestPreparePopup:
    """Тести підготовки Popup"""

    def test_prepare_popup(self, simple_processor):
        """Підготовка Popup з кнопками"""
        preparer = ElementPreparer(simple_processor)
        form = simple_processor.get_default_form()

        child_btn = FormElement(element_type="Button", name="PopupBtn", command="Cmd")
        elem = FormElement(
            element_type="Popup",
            name="TestPopup",
            child_items=[child_btn]
        )
        form.elements.append(elem)

        elements, _ = preparer.prepare_form_elements(form)

        assert elements[0]["type"] == "Popup"
        assert len(elements[0]["child_items"]) == 1
        assert elements[0]["child_items"][0]["type"] == "Button"
        assert elements[0]["child_items"][0]["command"] == "Cmd"

    def test_prepare_nested_popup(self, simple_processor):
        """Підготовка вкладеного Popup"""
        preparer = ElementPreparer(simple_processor)
        form = simple_processor.get_default_form()

        inner_popup = FormElement(
            element_type="Popup",
            name="InnerPopup",
            child_items=[]
        )
        outer_popup = FormElement(
            element_type="Popup",
            name="OuterPopup",
            child_items=[inner_popup]
        )
        form.elements.append(outer_popup)

        elements, _ = preparer.prepare_form_elements(form)

        assert elements[0]["type"] == "Popup"
        assert elements[0]["child_items"][0]["type"] == "Popup"


class TestIDAllocation:
    """Тести автоматичної нумерації ID"""

    def test_sequential_ids(self, simple_processor):
        """Перевірка послідовності ID"""
        preparer = ElementPreparer(simple_processor)
        form = simple_processor.get_default_form()

        elem1 = FormElement(element_type="InputField", name="Input1", attribute="Attr1")
        elem2 = FormElement(element_type="InputField", name="Input2", attribute="Attr2")
        elem3 = FormElement(element_type="InputField", name="Input3", attribute="Attr3")

        form.elements.extend([elem1, elem2, elem3])

        elements, next_id = preparer.prepare_form_elements(form)

        # ID повинні бути послідовними
        id1 = elements[0]["id"]
        id2 = elements[1]["id"]
        id3 = elements[2]["id"]

        assert id1 < id2 < id3
        assert next_id > id3

    def test_next_id_returned(self, simple_processor):
        """Перевірка повернення next_id"""
        preparer = ElementPreparer(simple_processor)
        form = simple_processor.get_default_form()

        elem = FormElement(element_type="InputField", name="Input", attribute="Attr")
        form.elements.append(elem)

        elements, next_id = preparer.prepare_form_elements(form)

        # next_id має бути більше за id елемента
        assert next_id > elements[0]["id"]


class TestTableContext:
    """Тести встановлення контексту таблиці"""

    def test_set_table_context_value_table(self, simple_processor):
        """Встановлення data_path для ValueTable"""
        preparer = ElementPreparer(simple_processor)

        elem = FormElement(
            element_type="InputField",
            name="TestField",
            attribute="TestAttr",
            properties={}
        )

        preparer._set_table_context(elem, "МояТаблиця", is_value_table=True)

        assert elem.properties["data_path"] == "МояТаблиця.TestAttr"

    def test_set_table_context_tabular_section(self, simple_processor):
        """Встановлення data_path для TabularSection"""
        preparer = ElementPreparer(simple_processor)

        elem = FormElement(
            element_type="InputField",
            name="TestField",
            attribute="TestAttr",
            properties={}
        )

        preparer._set_table_context(elem, "МояТаблиця", is_value_table=False)

        assert elem.properties["data_path"] == "Объект.МояТаблиця.TestAttr"

    def test_set_table_context_recursive_column_group(self, simple_processor):
        """Рекурсивне встановлення data_path для ColumnGroup"""
        preparer = ElementPreparer(simple_processor)

        child = FormElement(
            element_type="InputField",
            name="ChildField",
            attribute="ChildAttr",
            properties={}
        )
        column_group = FormElement(
            element_type="ColumnGroup",
            name="TestGroup",
            child_items=[child]
        )

        preparer._set_table_context(column_group, "МояТаблиця", is_value_table=True)

        assert child.properties["data_path"] == "МояТаблиця.ChildAttr"


class TestAutoCommandBar:
    """Тести підготовки AutoCommandBar"""

    def test_prepare_auto_command_bar(self, simple_processor):
        """Підготовка AutoCommandBar"""
        preparer = ElementPreparer(simple_processor)
        form = simple_processor.get_default_form()

        popup = FormElement(
            element_type="Popup",
            name="AutoPopup",
            child_items=[]
        )
        form.auto_command_bar_elements.append(popup)

        elements, next_id = preparer.prepare_auto_command_bar(form, start_id=100)

        assert len(elements) == 1
        assert elements[0]["type"] == "Popup"
        assert elements[0]["id"] >= 100
        assert next_id > 100
