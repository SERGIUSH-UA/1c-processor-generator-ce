"""
Tests for ValueTree + Table DataPath generation and attribute validation (v2.69.0+).

Bug fix: Table elements with tabular_section pointing to value_tree
should generate DataPath without "Объект." prefix.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import importlib
generator_module = importlib.import_module("1c_processor_generator.generator")
models_module = importlib.import_module("1c_processor_generator.models")
validators_module = importlib.import_module("1c_processor_generator.validators")

ProcessorGenerator = generator_module.ProcessorGenerator
Processor = models_module.Processor
Attribute = models_module.Attribute
Form = models_module.Form
FormElement = models_module.FormElement
ValueTreeAttribute = models_module.ValueTreeAttribute
Column = models_module.Column
ProcessorValidator = validators_module.ProcessorValidator


class TestValueTreeDataPath:
    """Tests for ValueTree DataPath generation."""

    def test_detect_is_value_table_returns_true_for_value_tree(self):
        """_detect_is_value_table() should return True for value_tree references."""
        # Create processor with form that has value_tree
        processor = Processor(name="TestProcessor")
        form = Form(name="TestForm")
        form.value_tree_attributes = [
            ValueTreeAttribute(
                name="ДеревоДанных",
                columns=[Column(name="Наименование", type="string")]
            )
        ]
        processor.forms = [form]

        # Create table element that references value_tree
        table_elem = FormElement(
            element_type="Table",
            name="TestTable",
            tabular_section="ДеревоДанных"
        )

        # Test detection
        generator = ProcessorGenerator(processor)
        is_value_table = generator._detect_is_value_table(table_elem, form)

        # Should return True because value_tree is form-level (like value_table)
        assert is_value_table is True

    def test_detect_is_value_table_returns_false_for_tabular_section(self):
        """_detect_is_value_table() should return False for processor-level tabular_sections."""
        processor = Processor(name="TestProcessor")
        form = Form(name="TestForm")
        form.value_tree_attributes = []  # No value_trees
        processor.forms = [form]

        # Create table element that references tabular_section (not in value_tables/trees)
        table_elem = FormElement(
            element_type="Table",
            name="TestTable",
            tabular_section="SomeTabularSection"
        )

        generator = ProcessorGenerator(processor)
        is_value_table = generator._detect_is_value_table(table_elem, form)

        # Should return False because it's not in value_tables or value_trees
        assert is_value_table is False

    def test_detect_is_value_table_explicit_override(self):
        """Explicit is_value_table property should override auto-detection."""
        processor = Processor(name="TestProcessor")
        form = Form(name="TestForm")
        form.value_tree_attributes = [
            ValueTreeAttribute(name="ДеревоДанных", columns=[])
        ]
        processor.forms = [form]

        # Create table with explicit is_value_table=False
        table_elem = FormElement(
            element_type="Table",
            name="TestTable",
            tabular_section="ДеревоДанных",
            properties={"is_value_table": False}  # Explicit override
        )

        generator = ProcessorGenerator(processor)
        is_value_table = generator._detect_is_value_table(table_elem, form)

        # Explicit False should override auto-detection
        assert is_value_table is False


class TestAttributeValidation:
    """Tests for InputField.attribute validation."""

    def test_valid_attribute_reference(self):
        """Valid attribute reference should pass validation."""
        processor = Processor(name="TestProcessor")
        processor.attributes = [
            Attribute(name="ТестовыйАтрибут", type="string")
        ]
        form = Form(name="TestForm")
        form.elements = [
            FormElement(
                element_type="InputField",
                name="ПолеВвода",
                attribute="ТестовыйАтрибут"
            )
        ]
        processor.forms = [form]

        validator = ProcessorValidator(processor)
        errors = validator._validate_form_element_references()

        assert len(errors) == 0

    def test_invalid_attribute_reference(self):
        """Invalid attribute reference should produce error."""
        processor = Processor(name="TestProcessor")
        processor.attributes = [
            Attribute(name="СуществующийАтрибут", type="string")
        ]
        form = Form(name="TestForm")
        form.elements = [
            FormElement(
                element_type="InputField",
                name="ПолеВвода",
                attribute="НесуществующийАтрибут"
            )
        ]
        processor.forms = [form]

        validator = ProcessorValidator(processor)
        errors = validator._validate_form_element_references()

        assert len(errors) == 1
        assert "НесуществующийАтрибут" in errors[0]
        assert "not found in processor.attributes" in errors[0]

    def test_nested_element_attribute_validation(self):
        """Nested elements should also be validated for attribute references."""
        processor = Processor(name="TestProcessor")
        processor.attributes = [
            Attribute(name="ВалидныйАтрибут", type="string")
        ]
        form = Form(name="TestForm")

        # Create nested structure: UsualGroup -> InputField
        nested_input = FormElement(
            element_type="InputField",
            name="ВложенноеПоле",
            attribute="НевалидныйАтрибут"  # Invalid
        )
        group = FormElement(
            element_type="UsualGroup",
            name="Группа",
            child_items=[nested_input]
        )
        form.elements = [group]
        processor.forms = [form]

        validator = ProcessorValidator(processor)
        errors = validator._validate_form_element_references()

        assert len(errors) == 1
        assert "НевалидныйАтрибут" in errors[0]

    def test_element_without_attribute_passes(self):
        """Elements without attribute property should pass validation."""
        processor = Processor(name="TestProcessor")
        processor.attributes = []
        form = Form(name="TestForm")
        form.elements = [
            FormElement(
                element_type="Button",
                name="Кнопка",
                command="SomeCommand"
            ),
            FormElement(
                element_type="LabelDecoration",
                name="Надпись"
            )
        ]
        processor.forms = [form]

        validator = ProcessorValidator(processor)
        errors = validator._validate_form_element_references()

        assert len(errors) == 0
