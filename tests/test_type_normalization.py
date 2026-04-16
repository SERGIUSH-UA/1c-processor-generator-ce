"""
Tests for type normalization in yaml_parser.py (v2.71.5+)

Tests that LLM-generated type variations are correctly normalized
before schema validation.
"""

import pytest
import importlib

# Import module with numeric prefix
yaml_parser = importlib.import_module("1c_processor_generator.yaml_parser")

_normalize_form_attribute_types = yaml_parser._normalize_form_attribute_types
_normalize_element_types = yaml_parser._normalize_element_types
_normalize_element_types_recursive = yaml_parser._normalize_element_types_recursive
FORM_ATTRIBUTE_TYPE_ALIASES = yaml_parser.FORM_ATTRIBUTE_TYPE_ALIASES
ELEMENT_TYPE_ALIASES = yaml_parser.ELEMENT_TYPE_ALIASES


class TestFormAttributeTypeNormalization:
    """Tests for form_attribute type normalization (PascalCase → snake_case)."""

    def test_spreadsheet_document_variations(self):
        """Test SpreadsheetDocument variations are normalized."""
        variations = [
            "SpreadsheetDocument",
            "SpreadSheetDocument",
            "spreadsheetDocument",
            "Spreadsheet",
            "MXL",
        ]
        for var in variations:
            config = {
                "forms": [{"form_attributes": [{"name": "Test", "type": var}]}]
            }
            result, warnings = _normalize_form_attribute_types(config)
            assert result["forms"][0]["form_attributes"][0]["type"] == "spreadsheet_document", \
                f"Failed for variation: {var}"
            assert len(warnings) == 1, f"Expected 1 warning for {var}"

    def test_binary_data_variations(self):
        """Test BinaryData variations are normalized."""
        variations = ["BinaryData", "binaryData", "Binary", "Blob"]
        for var in variations:
            config = {
                "forms": [{"form_attributes": [{"name": "Test", "type": var}]}]
            }
            result, warnings = _normalize_form_attribute_types(config)
            assert result["forms"][0]["form_attributes"][0]["type"] == "binary_data", \
                f"Failed for variation: {var}"
            assert len(warnings) == 1

    def test_string_variations(self):
        """Test String variations are normalized."""
        variations = ["String", "Text", "Строка"]
        for var in variations:
            config = {
                "forms": [{"form_attributes": [{"name": "Test", "type": var}]}]
            }
            result, warnings = _normalize_form_attribute_types(config)
            assert result["forms"][0]["form_attributes"][0]["type"] == "string", \
                f"Failed for variation: {var}"
            assert len(warnings) == 1

    def test_number_variations(self):
        """Test Number variations are normalized."""
        variations = ["Number", "Numeric", "Integer", "Decimal", "Число"]
        for var in variations:
            config = {
                "forms": [{"form_attributes": [{"name": "Test", "type": var}]}]
            }
            result, warnings = _normalize_form_attribute_types(config)
            assert result["forms"][0]["form_attributes"][0]["type"] == "number", \
                f"Failed for variation: {var}"
            assert len(warnings) == 1

    def test_date_variations(self):
        """Test Date variations are normalized."""
        variations = ["Date", "DateTime", "Дата"]
        for var in variations:
            config = {
                "forms": [{"form_attributes": [{"name": "Test", "type": var}]}]
            }
            result, warnings = _normalize_form_attribute_types(config)
            assert result["forms"][0]["form_attributes"][0]["type"] == "date", \
                f"Failed for variation: {var}"
            assert len(warnings) == 1

    def test_boolean_variations(self):
        """Test Boolean variations are normalized."""
        variations = ["Boolean", "Bool", "Булево"]
        for var in variations:
            config = {
                "forms": [{"form_attributes": [{"name": "Test", "type": var}]}]
            }
            result, warnings = _normalize_form_attribute_types(config)
            assert result["forms"][0]["form_attributes"][0]["type"] == "boolean", \
                f"Failed for variation: {var}"
            assert len(warnings) == 1

    def test_planner_variations(self):
        """Test Planner variations are normalized."""
        variations = ["Planner", "Планировщик"]
        for var in variations:
            config = {
                "forms": [{"form_attributes": [{"name": "Test", "type": var}]}]
            }
            result, warnings = _normalize_form_attribute_types(config)
            assert result["forms"][0]["form_attributes"][0]["type"] == "planner", \
                f"Failed for variation: {var}"
            assert len(warnings) == 1

    def test_correct_types_unchanged(self):
        """Test that correct snake_case types remain unchanged."""
        correct_types = ["spreadsheet_document", "binary_data", "string", "number", "date", "boolean", "planner"]
        for correct in correct_types:
            config = {
                "forms": [{"form_attributes": [{"name": "Test", "type": correct}]}]
            }
            result, warnings = _normalize_form_attribute_types(config)
            assert result["forms"][0]["form_attributes"][0]["type"] == correct
            assert len(warnings) == 0, f"No warnings expected for canonical type {correct}"

    def test_unknown_types_unchanged(self):
        """Test that unknown types pass through unchanged."""
        config = {
            "forms": [{"form_attributes": [{"name": "Test", "type": "UnknownType"}]}]
        }
        result, warnings = _normalize_form_attribute_types(config)
        assert result["forms"][0]["form_attributes"][0]["type"] == "UnknownType"
        assert len(warnings) == 0

    def test_empty_config(self):
        """Test that empty config is handled gracefully."""
        result1, warnings1 = _normalize_form_attribute_types({})
        assert result1 == {}
        assert warnings1 == []

        result2, warnings2 = _normalize_form_attribute_types({"forms": []})
        assert result2 == {"forms": []}
        assert warnings2 == []

    def test_multiple_attributes(self):
        """Test normalization of multiple attributes."""
        config = {
            "forms": [{
                "form_attributes": [
                    {"name": "Doc", "type": "SpreadsheetDocument"},
                    {"name": "Data", "type": "BinaryData"},
                    {"name": "Str", "type": "string"},  # Already correct
                ]
            }]
        }
        result, warnings = _normalize_form_attribute_types(config)
        attrs = result["forms"][0]["form_attributes"]
        assert attrs[0]["type"] == "spreadsheet_document"
        assert attrs[1]["type"] == "binary_data"
        assert attrs[2]["type"] == "string"
        assert len(warnings) == 2  # Only 2 were normalized


class TestElementTypeNormalization:
    """Tests for element type normalization (various → canonical PascalCase)."""

    def test_spreadsheet_document_field_variations(self):
        """Test SpreadsheetDocumentField - the most common LLM mistake!"""
        variations = [
            "SpreadsheetDocumentField",  # Missing capital S in Sheet
            "spreadsheetdocumentfield",
            "Spreadsheetdocumentfield",
            "spreadSheetDocumentField",
            "SpreadsheetField",
            "SpreadSheet",
        ]
        for var in variations:
            config = {"forms": [{"elements": [{"type": var, "name": "Test"}]}]}
            result, warnings = _normalize_element_types(config)
            assert result["forms"][0]["elements"][0]["type"] == "SpreadSheetDocumentField", \
                f"Failed for variation: {var}"
            assert len(warnings) == 1, f"Expected 1 warning for {var}"

    def test_html_document_field_variations(self):
        """Test HTMLDocumentField variations."""
        variations = ["HtmlDocumentField", "htmldocumentfield", "HTMLField", "HtmlField"]
        for var in variations:
            config = {"forms": [{"elements": [{"type": var, "name": "Test"}]}]}
            result, warnings = _normalize_element_types(config)
            assert result["forms"][0]["elements"][0]["type"] == "HTMLDocumentField", \
                f"Failed for variation: {var}"
            assert len(warnings) == 1

    def test_input_field_variations(self):
        """Test InputField variations."""
        variations = ["Inputfield", "inputfield", "inputField", "Input", "TextField", "TextInput"]
        for var in variations:
            config = {"forms": [{"elements": [{"type": var, "name": "Test"}]}]}
            result, warnings = _normalize_element_types(config)
            assert result["forms"][0]["elements"][0]["type"] == "InputField", \
                f"Failed for variation: {var}"
            assert len(warnings) == 1

    def test_table_variations(self):
        """Test Table variations (alternative names)."""
        variations = ["table", "DataTable", "Grid", "DataGrid"]
        for var in variations:
            config = {"forms": [{"elements": [{"type": var, "name": "Test"}]}]}
            result, warnings = _normalize_element_types(config)
            assert result["forms"][0]["elements"][0]["type"] == "Table", \
                f"Failed for variation: {var}"
            assert len(warnings) == 1

    def test_usual_group_variations(self):
        """Test UsualGroup variations."""
        variations = ["Usualgroup", "usualgroup", "usualGroup", "Group", "FormGroup", "Panel"]
        for var in variations:
            config = {"forms": [{"elements": [{"type": var, "name": "Test"}]}]}
            result, warnings = _normalize_element_types(config)
            assert result["forms"][0]["elements"][0]["type"] == "UsualGroup", \
                f"Failed for variation: {var}"
            assert len(warnings) == 1

    def test_pages_variations(self):
        """Test Pages variations."""
        variations = ["pages", "TabControl", "Tabs", "TabPages"]
        for var in variations:
            config = {"forms": [{"elements": [{"type": var, "name": "Test"}]}]}
            result, warnings = _normalize_element_types(config)
            assert result["forms"][0]["elements"][0]["type"] == "Pages", \
                f"Failed for variation: {var}"
            assert len(warnings) == 1

    def test_checkbox_field_variations(self):
        """Test CheckBoxField variations."""
        variations = ["Checkboxfield", "checkboxfield", "checkBoxField", "CheckBox", "Checkbox"]
        for var in variations:
            config = {"forms": [{"elements": [{"type": var, "name": "Test"}]}]}
            result, warnings = _normalize_element_types(config)
            assert result["forms"][0]["elements"][0]["type"] == "CheckBoxField", \
                f"Failed for variation: {var}"
            assert len(warnings) == 1

    def test_correct_types_unchanged(self):
        """Test that correct PascalCase types remain unchanged."""
        correct_types = [
            "InputField", "LabelField", "LabelDecoration", "PictureDecoration",
            "PictureField", "Table", "Button", "RadioButtonField", "CheckBoxField",
            "SpreadSheetDocumentField", "HTMLDocumentField", "CalendarField",
            "ChartField", "PlannerField", "UsualGroup", "ButtonGroup", "ColumnGroup",
            "Popup", "Pages", "Page"
        ]
        for correct in correct_types:
            config = {"forms": [{"elements": [{"type": correct, "name": "Test"}]}]}
            result, warnings = _normalize_element_types(config)
            assert result["forms"][0]["elements"][0]["type"] == correct
            assert len(warnings) == 0, f"No warnings expected for canonical type {correct}"

    def test_nested_elements(self):
        """Test normalization in nested element structures."""
        config = {
            "forms": [{
                "elements": [{
                    "type": "usualGroup",
                    "name": "Group1",
                    "elements": [
                        {"type": "inputField", "name": "Field1"},
                        {"type": "Grid", "name": "Table1"},
                    ]
                }]
            }]
        }
        result, warnings = _normalize_element_types(config)
        elements = result["forms"][0]["elements"]
        assert elements[0]["type"] == "UsualGroup"
        assert elements[0]["elements"][0]["type"] == "InputField"
        assert elements[0]["elements"][1]["type"] == "Table"
        assert len(warnings) == 3  # usualGroup, inputField, Grid

    def test_pages_with_nested_elements(self):
        """Test normalization in Pages with nested page elements."""
        config = {
            "forms": [{
                "elements": [{
                    "type": "TabControl",
                    "name": "Pages1",
                    "pages": [
                        {
                            "name": "Page1",
                            "elements": [
                                {"type": "inputField", "name": "Field1"},
                            ]
                        }
                    ]
                }]
            }]
        }
        result, warnings = _normalize_element_types(config)
        pages_elem = result["forms"][0]["elements"][0]
        assert pages_elem["type"] == "Pages"
        assert pages_elem["pages"][0]["elements"][0]["type"] == "InputField"
        assert len(warnings) == 2  # TabControl, inputField

    def test_warnings_contain_details(self):
        """Test that warnings contain useful information."""
        config = {
            "forms": [{
                "name": "TestForm",
                "elements": [{"type": "inputField", "name": "MyField"}]
            }]
        }
        result, warnings = _normalize_element_types(config)
        assert len(warnings) == 1
        assert "MyField" in warnings[0]
        assert "TestForm" in warnings[0]
        assert "inputField" in warnings[0]
        assert "InputField" in warnings[0]


class TestAliasesCompleteness:
    """Tests to verify alias dictionaries are complete."""

    def test_form_attribute_aliases_count(self):
        """Verify we have expected number of form_attribute aliases."""
        assert len(FORM_ATTRIBUTE_TYPE_ALIASES) >= 25, \
            f"Expected at least 25 aliases, got {len(FORM_ATTRIBUTE_TYPE_ALIASES)}"

    def test_element_type_aliases_count(self):
        """Verify we have expected number of element type aliases."""
        assert len(ELEMENT_TYPE_ALIASES) >= 80, \
            f"Expected at least 80 aliases, got {len(ELEMENT_TYPE_ALIASES)}"

    def test_all_form_attribute_canonical_types_covered(self):
        """Verify all canonical form_attribute types have at least one alias."""
        canonical_types = {"spreadsheet_document", "binary_data", "string", "number", "date", "boolean", "planner"}
        covered = set(FORM_ATTRIBUTE_TYPE_ALIASES.values())
        assert canonical_types == covered, \
            f"Missing canonical types: {canonical_types - covered}"

    def test_most_common_element_types_covered(self):
        """Verify most common element types have aliases."""
        # These are the types that commonly get misspelled
        important_types = {
            "SpreadSheetDocumentField",
            "HTMLDocumentField",
            "InputField",
            "Table",
            "UsualGroup",
            "Pages",
            "CheckBoxField",
        }
        covered = set(ELEMENT_TYPE_ALIASES.values())
        missing = important_types - covered
        assert not missing, f"Missing important element types: {missing}"


class TestIntegrationWithYAMLParser:
    """Integration tests with actual YAMLParser."""

    def test_parser_normalizes_types(self, tmp_path):
        """Test that YAMLParser normalizes types during validation."""
        # Create test config with incorrect types
        config_content = """
processor:
  name: TestProcessor

forms:
  - name: Form1
    default: true
    form_attributes:
      - name: Doc
        type: SpreadsheetDocument
    elements:
      - type: SpreadsheetDocumentField
        name: DocField
        attribute: Doc
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content, encoding="utf-8")

        # Parse with YAMLParser
        YAMLParser = yaml_parser.YAMLParser
        parser = YAMLParser(config_file)
        assert parser.load_yaml()
        assert parser.validate_schema()

        # Verify types were normalized
        form = parser.config["forms"][0]
        assert form["form_attributes"][0]["type"] == "spreadsheet_document"
        assert form["elements"][0]["type"] == "SpreadSheetDocumentField"
