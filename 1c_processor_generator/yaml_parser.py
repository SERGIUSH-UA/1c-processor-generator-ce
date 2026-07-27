"""
YAML Parser для генератора зовнішніх обробок 1C

v2.45.0 - Data reference validation + ListChoiceMode fix

Парсить YAML конфігурацію та створює Processor об'єкт.
Використовує декларативні схеми для парсингу елементів форми.
"""

import os
import yaml
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from difflib import get_close_matches

from .models import (
    Processor,
    Attribute,
    TabularSection,
    Column,
    Form,
    FormElement,
    Command,
    LongOperationSettings,
    ValueTableAttribute,
    ValueTreeAttribute,  # v2.64.0+
    DynamicListAttribute,
    DynamicListParameter,
    DynamicListColumn,
    ValidationConfig,
    Template,
    TemplatePlaceholder,
    TemplateAssets,
    FormAttribute,
    FormParameter,
    # v2.57.0+ BSP integration
    BSPConfig,
    BSPCommand,
)
from .test_parser import parse_tests_yaml
from .parsing import ElementParser, normalize_multilang


# =============================================================================
# Type Normalization (v2.71.0+)
# =============================================================================
# ⚠️ INTERNAL IMPLEMENTATION - NOT A STANDARD! ⚠️
#
# This normalization exists ONLY as a fallback error correction mechanism.
# It should NOT be treated as an excuse to generate incorrect types.
#
# CANONICAL FORMATS (always use these in documentation and examples):
#   - form_attribute types: snake_case (spreadsheet_document, binary_data, string, etc.)
#   - Element types: PascalCase (SpreadSheetDocumentField, HTMLDocumentField, InputField, etc.)
#
# WHY THIS EXISTS:
# LLMs sometimes generate type names with variations due to training data inconsistencies.
# Rather than failing validation, we silently correct common mistakes to improve UX.
#
# THIS IS NOT A FEATURE - it's damage control. Always generate correct types.
# =============================================================================

# form_attribute type aliases (snake_case is canonical)
FORM_ATTRIBUTE_TYPE_ALIASES = {
    # === spreadsheet_document ===
    "SpreadsheetDocument": "spreadsheet_document",
    "SpreadSheetDocument": "spreadsheet_document",
    "spreadsheetDocument": "spreadsheet_document",
    "Spreadsheet": "spreadsheet_document",
    "MXL": "spreadsheet_document",

    # === binary_data ===
    "BinaryData": "binary_data",
    "binaryData": "binary_data",
    "Binary": "binary_data",
    "Blob": "binary_data",

    # === string ===
    "String": "string",
    "Text": "string",
    "Строка": "string",

    # === number ===
    "Number": "number",
    "Numeric": "number",
    "Integer": "number",
    "Decimal": "number",
    "Число": "number",

    # === date ===
    "Date": "date",
    "DateTime": "date",
    "Дата": "date",

    # === boolean ===
    "Boolean": "boolean",
    "Bool": "boolean",
    "Булево": "boolean",

    # === planner ===
    "Planner": "planner",
    "Планировщик": "planner",
}

# Element type aliases (PascalCase is canonical)
ELEMENT_TYPE_ALIASES = {
    # === SpreadSheetDocumentField (most common mistake!) ===
    "SpreadsheetDocumentField": "SpreadSheetDocumentField",
    "spreadsheetdocumentfield": "SpreadSheetDocumentField",
    "Spreadsheetdocumentfield": "SpreadSheetDocumentField",
    "spreadSheetDocumentField": "SpreadSheetDocumentField",
    "SpreadsheetField": "SpreadSheetDocumentField",
    "SpreadSheet": "SpreadSheetDocumentField",

    # === HTMLDocumentField ===
    "HtmlDocumentField": "HTMLDocumentField",
    "htmldocumentfield": "HTMLDocumentField",
    "HTMLField": "HTMLDocumentField",
    "HtmlField": "HTMLDocumentField",

    # === InputField ===
    "Inputfield": "InputField",
    "inputfield": "InputField",
    "inputField": "InputField",
    "Input": "InputField",
    "TextField": "InputField",
    "TextInput": "InputField",

    # === LabelField ===
    "Labelfield": "LabelField",
    "labelfield": "LabelField",
    "labelField": "LabelField",

    # === LabelDecoration ===
    "Labeldecoration": "LabelDecoration",
    "labeldecoration": "LabelDecoration",
    "labelDecoration": "LabelDecoration",
    "Label": "LabelDecoration",
    "StaticText": "LabelDecoration",

    # === PictureDecoration ===
    "Picturedecoration": "PictureDecoration",
    "picturedecoration": "PictureDecoration",
    "pictureDecoration": "PictureDecoration",
    "Picture": "PictureDecoration",
    "Image": "PictureDecoration",
    "ImageDecoration": "PictureDecoration",

    # === PictureField ===
    "Picturefield": "PictureField",
    "picturefield": "PictureField",
    "pictureField": "PictureField",
    "ImageField": "PictureField",

    # === Table ===
    "table": "Table",
    "DataTable": "Table",
    "Grid": "Table",
    "DataGrid": "Table",

    # === Button ===
    "button": "Button",
    "CommandButton": "Button",
    "Btn": "Button",

    # === RadioButtonField ===
    "Radiobuttonfield": "RadioButtonField",
    "radiobuttonfield": "RadioButtonField",
    "radioButtonField": "RadioButtonField",
    "RadioButton": "RadioButtonField",
    "Radio": "RadioButtonField",

    # === CheckBoxField ===
    "Checkboxfield": "CheckBoxField",
    "checkboxfield": "CheckBoxField",
    "checkBoxField": "CheckBoxField",
    "CheckBox": "CheckBoxField",
    "Checkbox": "CheckBoxField",

    # === CalendarField ===
    "Calendarfield": "CalendarField",
    "calendarfield": "CalendarField",
    "calendarField": "CalendarField",
    "Calendar": "CalendarField",
    "DatePicker": "CalendarField",

    # === ChartField ===
    "Chartfield": "ChartField",
    "chartfield": "ChartField",
    "chartField": "ChartField",
    "Chart": "ChartField",
    "Diagram": "ChartField",

    # === PlannerField ===
    "Plannerfield": "PlannerField",
    "plannerfield": "PlannerField",
    "plannerField": "PlannerField",
    "Scheduler": "PlannerField",
    "Kanban": "PlannerField",

    # === UsualGroup ===
    "Usualgroup": "UsualGroup",
    "usualgroup": "UsualGroup",
    "usualGroup": "UsualGroup",
    "Group": "UsualGroup",
    "FormGroup": "UsualGroup",
    "Panel": "UsualGroup",

    # === ButtonGroup ===
    "Buttongroup": "ButtonGroup",
    "buttongroup": "ButtonGroup",
    "buttonGroup": "ButtonGroup",

    # === ColumnGroup ===
    "Columngroup": "ColumnGroup",
    "columngroup": "ColumnGroup",
    "columnGroup": "ColumnGroup",

    # === Popup ===
    "popup": "Popup",
    "PopupMenu": "Popup",
    "Menu": "Popup",
    "DropDown": "Popup",

    # === Pages ===
    "pages": "Pages",
    "TabControl": "Pages",
    "Tabs": "Pages",
    "TabPages": "Pages",

    # === Page ===
    "page": "Page",
    "Tab": "Page",
    "TabPage": "Page",
}


def _normalize_form_attribute_types(config: Dict) -> tuple:
    """Normalize form_attribute types from various formats to snake_case.

    Returns:
        tuple: (config, list of warnings)
    """
    warnings = []
    if "forms" not in config:
        return config, warnings

    for form in config["forms"]:
        form_name = form.get("name", "Unknown")
        if "form_attributes" not in form:
            continue
        for attr in form["form_attributes"]:
            if "type" in attr:
                original = attr["type"]
                normalized = FORM_ATTRIBUTE_TYPE_ALIASES.get(original, original)
                if normalized != original:
                    attr["type"] = normalized
                    warnings.append(
                        f"form_attribute '{attr.get('name', '?')}' in form '{form_name}': "
                        f"type '{original}' → '{normalized}'"
                    )

    return config, warnings


def _normalize_element_types_recursive(elements: List[Dict], form_name: str, warnings: List[str]) -> None:
    """Recursively normalize element types in nested structures."""
    for elem in elements:
        if "type" in elem:
            original = elem["type"]
            normalized = ELEMENT_TYPE_ALIASES.get(original, original)
            if normalized != original:
                elem["type"] = normalized
                warnings.append(
                    f"element '{elem.get('name', '?')}' in form '{form_name}': "
                    f"type '{original}' → '{normalized}'"
                )

        # Recurse into nested elements
        if "elements" in elem:
            _normalize_element_types_recursive(elem["elements"], form_name, warnings)

        # Recurse into pages (for Pages element)
        if "pages" in elem:
            for page in elem["pages"]:
                if "elements" in page:
                    _normalize_element_types_recursive(page["elements"], form_name, warnings)


def _normalize_element_types(config: Dict) -> tuple:
    """Normalize element type variations to canonical PascalCase.

    Returns:
        tuple: (config, list of warnings)
    """
    warnings = []
    if "forms" not in config:
        return config, warnings

    for form in config["forms"]:
        form_name = form.get("name", "Unknown")
        if "elements" in form:
            _normalize_element_types_recursive(form["elements"], form_name, warnings)

    return config, warnings


def _normalize_attribute_types(config: Dict) -> tuple:
    """Normalize attribute types from various formats to snake_case.

    Applies to: attributes, tabular_sections columns, value_tables columns.

    Returns:
        tuple: (config, list of warnings)
    """
    warnings = []

    # Normalize top-level attributes
    for attr in config.get("attributes", []):
        if "type" in attr:
            original = attr["type"]
            normalized = FORM_ATTRIBUTE_TYPE_ALIASES.get(original, original)
            if normalized != original:
                attr["type"] = normalized
                warnings.append(
                    f"attribute '{attr.get('name', '?')}': type '{original}' → '{normalized}'"
                )

    # Normalize tabular_sections columns
    for ts in config.get("tabular_sections", []):
        for col in ts.get("columns", []):
            if "type" in col:
                original = col["type"]
                normalized = FORM_ATTRIBUTE_TYPE_ALIASES.get(original, original)
                if normalized != original:
                    col["type"] = normalized
                    warnings.append(
                        f"tabular_section '{ts.get('name', '?')}'.'{col.get('name', '?')}': "
                        f"type '{original}' → '{normalized}'"
                    )

    # Normalize value_tables columns
    for vt in config.get("value_tables", []):
        for col in vt.get("columns", []):
            if "type" in col:
                original = col["type"]
                normalized = FORM_ATTRIBUTE_TYPE_ALIASES.get(original, original)
                if normalized != original:
                    col["type"] = normalized
                    warnings.append(
                        f"value_table '{vt.get('name', '?')}'.'{col.get('name', '?')}': "
                        f"type '{original}' → '{normalized}'"
                    )

    return config, warnings


class YAMLParser:
    """Парсер YAML конфігурації в Processor об'єкт."""

    # Default languages for backward compatibility
    DEFAULT_LANGUAGES = ["ru", "uk", "en"]

    def __init__(self, yaml_path: Path):
        """
        Args:
            yaml_path: Шлях до YAML файлу
        """
        self.yaml_path = Path(yaml_path)
        self.config: Dict = {}
        self._element_parser = ElementParser()
        # Compact multilang support (v2.69.0+)
        self.languages: List[str] = self.DEFAULT_LANGUAGES.copy()
        # Втрати при конвертації макетів (Excel → MXL), v2.78.0+
        self._template_warnings: List[str] = []

    def load_yaml(self) -> bool:
        """
        Завантажує YAML файл.

        Returns:
            True якщо успішно, False якщо помилка
        """
        try:
            with open(self.yaml_path, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f)
            return True
        except Exception as e:
            print(f"❌ Помилка читання YAML: {e}")
            return False

    def validate_schema(self) -> bool:
        """
        Валідує YAML через JSON Schema.

        Returns:
            True якщо валідний, False якщо помилки
        """
        try:
            schema_path = Path(__file__).parent / "yaml_schema.json"
            with open(schema_path, "r", encoding="utf-8") as f:
                schema = json.load(f)

            try:
                import jsonschema
            except ImportError:
                raise ImportError(
                    "jsonschema is required for YAML validation.\n"
                    "Install it with: pip install jsonschema\n"
                    "Or install all dependencies: pip install -r requirements.txt"
                )

            try:
                # Normalize types before validation (v2.71.0+)
                # This allows LLMs to use various type formats
                self.config, attr_warnings = _normalize_form_attribute_types(self.config)
                self.config, elem_warnings = _normalize_element_types(self.config)
                self.config, type_warnings = _normalize_attribute_types(self.config)

                jsonschema.validate(instance=self.config, schema=schema)
                print("✅ YAML структура валідна")

                # Print warnings about normalized types
                all_warnings = attr_warnings + elem_warnings + type_warnings
                if all_warnings:
                    print(f"⚠️  Виправлено {len(all_warnings)} тип(ів) - використовуйте канонічні формати:")
                    for warning in all_warnings:
                        print(f"   • {warning}")
                    print("   📖 Канонічні формати: types → snake_case, elements → PascalCase")

                return True
            except jsonschema.ValidationError as e:
                # Enhanced error message for pattern errors (v2.73.0+)
                enhanced_message = self._enhance_validation_error(e)
                print(f"❌ YAML структура не валідна: {enhanced_message}")
                print(f"   Шлях: {' -> '.join(str(p) for p in e.path)}")

                # Try to provide helpful suggestions
                suggestion = self._get_validation_suggestion(e)
                if suggestion:
                    print(f"   💡 {suggestion}")

                return False
        except Exception as e:
            print(f"❌ Помилка валідації: {e}")
            return False

    def _enhance_validation_error(self, error) -> str:
        """
        v2.73.0+ Enhanced error message for validation errors.

        Provides human-readable explanations instead of raw regex patterns.
        """
        # Pattern validation errors (identifier validation)
        if error.validator == "pattern":
            instance = error.instance
            if isinstance(instance, str):
                # Check for Ukrainian letters
                ukrainian_only = "іїєґІЇЄҐ"
                found_ukrainian = [c for c in instance if c in ukrainian_only]
                if found_ukrainian:
                    chars = ", ".join(f"'{c}'" for c in set(found_ukrainian))
                    return (
                        f"'{instance}' містить українські літери: {chars}. "
                        f"Використовуйте російські літери (и, е) або латиницю."
                    )

                # Check for invalid characters
                import re
                identifier_pattern = r'^[А-ЯІЇЄҐа-яіїєґЁёA-Za-z_][А-ЯІЇЄҐа-яіїєґЁёA-Za-z0-9_]*$'
                if not re.match(identifier_pattern, instance):
                    # Find invalid characters
                    valid_chars = set("АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдежзийклмнопрстуфхцчшщъыьэюя"
                                     "ЁёІіЇїЄєҐґABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_")
                    invalid = [c for c in instance if c not in valid_chars]
                    if invalid:
                        chars = ", ".join(f"'{c}'" for c in set(invalid))
                        return f"'{instance}' містить недопустимі символи: {chars}"

                    # Starts with digit
                    if instance and instance[0].isdigit():
                        return f"'{instance}' не може починатися з цифри"

        # Enum validation errors
        if error.validator == "enum":
            valid_values = error.validator_value
            if len(valid_values) <= 10:
                return f"'{error.instance}' не є допустимим значенням. Допустимі: {', '.join(map(str, valid_values))}"

        # Return original message for other errors
        return error.message

    def _get_validation_suggestion(self, error) -> Optional[str]:
        """
        Generate helpful suggestion for validation error.

        Checks common_mistakes from feature_registry.json and uses
        fuzzy matching to suggest correct element types/events.
        """
        # Valid element types for fuzzy matching
        valid_element_types = [
            "InputField", "LabelField", "LabelDecoration", "PictureDecoration",
            "PictureField", "RadioButtonField", "CheckBoxField", "Button",
            "ButtonGroup", "ColumnGroup", "Popup", "UsualGroup", "Pages",
            "Table", "SpreadSheetDocumentField", "HTMLDocumentField"
        ]

        # Common mistakes mapping (from feature_registry)
        common_mistakes = {
            "CommandBar": "UsualGroup with group_type: CommandBar",
            "FormGroup": "UsualGroup with group_direction",
            "TextBox": "InputField",
            "Label": "LabelField (data-bound) or LabelDecoration (static)",
            "Image": "PictureDecoration (static) or PictureField (editable)",
            "Grid": "Table",
            "DataGrid": "Table",
            "Tab": "Pages",
            "TabControl": "Pages",
            "Dropdown": "InputField with choice_list",
            "ComboBox": "InputField with choice_list",
            "Select": "InputField with choice_list",
        }

        # Try to extract the invalid value from the error
        try:
            instance = error.instance
            if isinstance(instance, dict):
                invalid_type = instance.get("type", "")

                # Check common mistakes first
                if invalid_type in common_mistakes:
                    return f"Did you mean: type: {common_mistakes[invalid_type]}?"

                # Try fuzzy matching for similar types
                if invalid_type:
                    matches = get_close_matches(
                        invalid_type,
                        valid_element_types,
                        n=1,
                        cutoff=0.5
                    )
                    if matches:
                        return f"Did you mean: type: {matches[0]}?"

                # Check for common event mistakes
                invalid_event = None
                for key in ["event", "events"]:
                    if key in instance:
                        events = instance[key]
                        if isinstance(events, dict):
                            for event_name in events.keys():
                                if event_name in ["OnClick", "onclick"]:
                                    return "Did you mean: Click (not OnClick)? OnClick is only for HTMLDocumentField."
                                if event_name in ["OnRowActivate", "RowActivate"]:
                                    return "Did you mean: OnActivateRow?"

        except Exception:
            pass

        return None

    def parse(self) -> Optional[Processor]:
        """
        Парсить YAML конфігурацію в Processor об'єкт.

        Returns:
            Processor об'єкт або None якщо помилка
        """
        if not self.load_yaml():
            return None

        if not self.validate_schema():
            return None

        try:
            processor = self._create_processor()

            # v2.57.0+ BSP Integration (PRO feature)
            self._parse_bsp_config(processor)

            # Парсимо основні секції
            self._parse_attributes(processor)
            self._parse_tabular_sections(processor)
            self._parse_validation_config(processor)
            self._parse_tests_config(processor)
            self._parse_object_module(processor)
            self._parse_templates(processor)
            self._parse_forms(processor)

            # v2.47.0+ Validate data references (tabular_section, value_tables)
            self._validate_data_references(processor)

            # v2.41.0+ Process auto_field for templates
            self._process_template_auto_fields(processor)

            # v2.42.0+ Process template: property on HTMLDocumentField
            self._process_template_linked_fields(processor)

            # v2.78.0+: втрати конвертації макетів мають дожити до фінального виводу
            processor.generation_warnings.extend(self._template_warnings)

            print(f"✅ YAML успішно розпарсено: {processor.name}")
            return processor

        except Exception as e:
            print(f"❌ Помилка парсингу YAML: {e}")
            import traceback
            traceback.print_exc()
            return None

    # =========================================================================
    # Processor Creation
    # =========================================================================

    def _create_processor(self) -> Processor:
        """Створює Processor об'єкт з базової конфігурації."""
        # Parse languages first (v2.69.0+) - before processor_config normalization
        self.languages = self.config.get("languages", self.DEFAULT_LANGUAGES.copy())

        # Reinitialize element parser with languages for compact syntax support
        self._element_parser = ElementParser(languages=self.languages)

        processor_config = normalize_multilang(
            self.config.get("processor", {}),
            languages=self.languages
        )

        processor = Processor(
            name=processor_config["name"],
            synonym_ru=processor_config.get("synonym_ru", processor_config["name"]),
            synonym_uk=processor_config.get("synonym_uk", processor_config["name"]),
            synonym_en=processor_config.get("synonym_en", processor_config["name"]),
            platform_version=processor_config.get("platform_version", "2.11"),
            languages=self.languages,  # v2.69.0+
        )

        # Set config directory for SVG path resolution
        processor.config_dir = str(self.yaml_path.parent)

        return processor

    # =========================================================================
    # Attributes & Tabular Sections
    # =========================================================================

    def _parse_attributes(self, processor: Processor) -> None:
        """Парсить секцію attributes."""
        for attr_config in self.config.get("attributes", []):
            attr_config = normalize_multilang(attr_config, languages=self.languages)
            attr = Attribute(
                name=attr_config["name"],
                type=attr_config["type"],
                synonym_ru=attr_config.get("synonym_ru", attr_config["name"]),
                synonym_uk=attr_config.get("synonym_uk", attr_config["name"]),
                synonym_en=attr_config.get("synonym_en", attr_config["name"]),
                length=attr_config.get("length"),
                digits=attr_config.get("digits"),
                fraction_digits=attr_config.get("fraction_digits"),
            )
            processor.attributes.append(attr)

    def _parse_tabular_sections(self, processor: Processor) -> None:
        """Парсить секцію tabular_sections."""
        for ts_config in self.config.get("tabular_sections", []):
            ts_config = normalize_multilang(ts_config, languages=self.languages)
            ts = TabularSection(
                name=ts_config["name"],
                synonym_ru=ts_config.get("synonym_ru", ts_config["name"]),
                synonym_uk=ts_config.get("synonym_uk", ts_config["name"]),
                synonym_en=ts_config.get("synonym_en", ts_config["name"]),
            )
            ts.columns = self._parse_columns(ts_config.get("columns", []))
            processor.tabular_sections.append(ts)

    def _parse_columns(self, columns_config: List[Dict]) -> List[Column]:
        """Універсальний парсер колонок для TabularSection та ValueTable."""
        columns = []
        for col_config in columns_config:
            col_config = normalize_multilang(col_config, languages=self.languages)
            col = Column(
                name=col_config["name"],
                type=col_config["type"],
                synonym_ru=col_config.get("synonym_ru", col_config["name"]),
                synonym_uk=col_config.get("synonym_uk", col_config["name"]),
                synonym_en=col_config.get("synonym_en", col_config["name"]),
                length=col_config.get("length"),
                digits=col_config.get("digits"),
                fraction_digits=col_config.get("fraction_digits"),
                read_only=col_config.get("read_only", False),
            )
            columns.append(col)
        return columns

    # =========================================================================
    # Forms Parsing - UNIFIED
    # =========================================================================

    def _parse_forms(self, processor: Processor) -> None:
        """Парсить секцію forms."""
        forms_config = self.config.get("forms", [])

        if not forms_config:
            return

        for form_config in forms_config:
            # Підтримка include файлів
            if "include" in form_config:
                form_config = self._load_form_include(form_config)
                if form_config is None:
                    continue

            form = self._parse_single_form(form_config)
            processor.forms.append(form)

    def _validate_data_references(self, processor: Processor) -> None:
        """
        v2.47.0+ Validates data references in forms.

        Checks:
        1. Root-level 'value_tables:' is ignored - emit warning
        2. Table elements referencing undefined tabular_section/value_table - emit error
        """
        errors = []

        # Check 1: Root-level value_tables (silently ignored!)
        if "value_tables" in self.config:
            root_vt_names = [vt.get("name", "?") for vt in self.config.get("value_tables", [])]
            print(f"⚠️  WARNING: Root-level 'value_tables:' is ignored!")
            print(f"   Value tables at root level: {', '.join(root_vt_names)}")
            print(f"   💡 Move 'value_tables:' inside each form that uses it.")
            print(f"   Example:")
            print(f"     forms:")
            print(f"       - name: Форма")
            print(f"         value_tables:  # <-- Must be inside form!")
            print(f"           - name: {root_vt_names[0] if root_vt_names else 'YourTable'}")
            print()

        # Check 2: Table elements referencing undefined tabular_section
        for form in processor.forms:
            # Build set of valid table names for this form
            valid_value_tables = {vt.name for vt in form.value_table_attributes}
            valid_value_trees = {vt.name for vt in form.value_tree_attributes}  # v2.64.0+
            valid_tabular_sections = {ts.name for ts in processor.tabular_sections}
            valid_dynamic_lists = {dl.name for dl in form.dynamic_list_attributes}

            # Check all Table elements recursively
            self._check_table_references(
                form.elements,
                form.name,
                valid_value_tables | valid_dynamic_lists | valid_value_trees,  # Include value_trees
                valid_tabular_sections,
                errors
            )

        if errors:
            print("❌ Validation errors:")
            for error in errors:
                print(f"   • {error}")
            raise ValueError(f"Found {len(errors)} data reference error(s)")

    def _check_table_references(
        self,
        elements: List,
        form_name: str,
        valid_value_tables: set,
        valid_tabular_sections: set,
        errors: List[str]
    ) -> None:
        """Recursively checks Table elements for valid tabular_section references."""
        for elem in elements:
            # Handle both FormElement objects and dicts (prepared data for validation)
            if isinstance(elem, dict):
                elem_type = elem.get("type")
                elem_name = elem.get("name", "?")
                ts_name = elem.get("tabular_section")
                child_items = elem.get("child_items", [])
            else:
                elem_type = elem.element_type
                elem_name = elem.name
                ts_name = elem.tabular_section
                child_items = elem.child_items

            if elem_type == "Table":
                if ts_name:
                    # Check if it's a valid reference
                    if ts_name not in valid_value_tables and ts_name not in valid_tabular_sections:
                        errors.append(
                            f"Form '{form_name}', Table '{elem_name}': "
                            f"tabular_section '{ts_name}' not found. "
                            f"Define it in form's value_tables:, value_trees: or root tabular_sections:"
                        )

            # Recursively check child elements
            if child_items:
                self._check_table_references(
                    child_items,
                    form_name,
                    valid_value_tables,
                    valid_tabular_sections,
                    errors
                )

    def _load_form_include(self, form_config: Dict) -> Optional[Dict]:
        """Завантажує include файл для форми."""
        include_path = Path(form_config["include"])
        if not include_path.is_absolute():
            include_path = self.yaml_path.parent / include_path

        try:
            with open(include_path, "r", encoding="utf-8") as f:
                included_config = yaml.safe_load(f)
            # Merge: базові поля з form_config мають пріоритет
            return {**included_config, **form_config}
        except Exception as e:
            print(f"⚠️ Помилка завантаження include файлу {include_path}: {e}")
            return None

    def _parse_single_form(self, config: Dict) -> Form:
        """Парсить одну форму."""
        # Резолвимо handlers_dir
        handlers_dir_value = config.get("handlers_dir")
        if handlers_dir_value:
            handlers_dir_path = Path(handlers_dir_value)
            if not handlers_dir_path.is_absolute():
                handlers_dir_value = str(self.yaml_path.parent / handlers_dir_value)

        # Резолвимо handlers_file (v2.69.0+)
        handlers_file_value = config.get("handlers_file")
        if handlers_file_value:
            handlers_file_path = Path(handlers_file_value)
            if not handlers_file_path.is_absolute():
                handlers_file_value = str(self.yaml_path.parent / handlers_file_value)

        form = Form(
            name=config["name"],
            default=config.get("default", False),
            include=config.get("include"),
            handlers_dir=handlers_dir_value,
            handlers_file=handlers_file_value,
        )

        # Documentation file
        self._load_form_documentation(form, config)

        # Properties
        self._parse_form_properties(form, config.get("properties", {}))

        # Events
        form.events = config.get("events", {})

        # Parameters
        self._parse_form_parameters(form, config.get("parameters", []))

        # Elements - через ElementParser
        for elem_config in config.get("elements", []):
            elem = self._element_parser.parse(elem_config)
            if elem:
                form.elements.append(elem)

        # AutoCommandBar
        for elem_config in config.get("auto_command_bar", []):
            elem = self._element_parser.parse(elem_config)
            if elem:
                form.auto_command_bar_elements.append(elem)

        # Commands
        for cmd_config in config.get("commands", []):
            form.commands.append(self._parse_command(cmd_config))

        # FormAttributes
        for fa_config in config.get("form_attributes", []):
            form.form_attributes.append(self._parse_form_attribute(fa_config))

        # ValueTables
        for vt_config in config.get("value_tables", []):
            form.value_table_attributes.append(self._parse_value_table_config(vt_config))

        # ValueTrees (v2.64.0+)
        for vt_config in config.get("value_trees", []):
            form.value_tree_attributes.append(self._parse_value_tree_config(vt_config))

        # DynamicLists
        for dl_config in config.get("dynamic_lists", []):
            form.dynamic_list_attributes.append(self._parse_dynamic_list_config(dl_config))

        # ConditionalAppearances (v2.67.0+) - form-level
        if "conditional_appearances" in config:
            form.conditional_appearances = self._element_parser._parse_conditional_appearances(
                config["conditional_appearances"]
            )

        return form

    def _load_form_documentation(self, form: Form, config: Dict) -> None:
        """Завантажує документацію форми з файлу."""
        documentation_file = config.get("documentation_file")
        if not documentation_file:
            return

        doc_path = Path(documentation_file)
        if not doc_path.is_absolute():
            doc_path = self.yaml_path.parent / doc_path

        try:
            with open(doc_path, 'r', encoding='utf-8') as f:
                form.documentation_file = documentation_file
                form.documentation = f.read().strip()
            print(f"📄 Завантажено документацію з файлу: {documentation_file}")
        except FileNotFoundError:
            print(f"⚠️ Файл документації не знайдено: {doc_path}")
            raise ValueError(f"Documentation file not found: {doc_path}")
        except Exception as e:
            print(f"⚠️ Помилка читання файлу документації {doc_path}: {e}")
            raise

    def _parse_form_properties(self, form: Form, props: Dict) -> None:
        """Єдиний метод парсингу form properties."""
        if props.get("title"):
            form.properties["Title"] = True
            for lang in ["ru", "uk", "en"]:
                key = f"title_{lang}"
                if props.get(key):
                    form.properties[f"Title_{lang}"] = props[key]

        if "auto_title" in props:
            form.properties["AutoTitle"] = props["auto_title"]

        if "window_opening_mode" in props:
            form.properties["WindowOpeningMode"] = props["window_opening_mode"]

        if "command_bar_location" in props:
            form.properties["CommandBarLocation"] = props["command_bar_location"]

    def _parse_form_parameters(self, form: Form, params_config: List[Dict]) -> None:
        """Парсить параметри форми."""
        for param_config in params_config:
            param = FormParameter(
                name=param_config["name"],
                type=param_config["type"],
                synonym_ru=param_config.get("synonym_ru"),
                synonym_uk=param_config.get("synonym_uk"),
                synonym_en=param_config.get("synonym_en"),
                key_parameter=param_config.get("key_parameter", False),
            )
            form.parameters.append(param)

    def _parse_form_attribute(self, config: Dict) -> FormAttribute:
        """Парсить FormAttribute.

        Для planner типу підтримуються додаткові налаштування:
        - time_scale: Hour, Day, Week, Month
        - time_scale_interval: int (default 1)
        - time_scale_format: string (auto-generated if not specified)
        - display_current_date: bool (default True)
        - show_weekends: bool (default True)
        """
        return FormAttribute(
            name=config["name"],
            type=config["type"],
            synonym_ru=config.get("synonym_ru"),
            synonym_uk=config.get("synonym_uk"),
            synonym_en=config.get("synonym_en"),
            title_ru=config.get("title_ru"),
            title_uk=config.get("title_uk"),
            title_en=config.get("title_en"),
            # Planner-specific settings (v2.47.0+)
            time_scale=config.get("time_scale"),
            time_scale_interval=config.get("time_scale_interval", 1),
            time_scale_format=config.get("time_scale_format"),
            display_current_date=config.get("display_current_date", True),
            show_weekends=config.get("show_weekends", True),
        )

    # =========================================================================
    # Command Parsing - UNIFIED
    # =========================================================================

    def _parse_command(self, config: Dict) -> Command:
        """Єдиний метод парсингу Command."""
        config = normalize_multilang(config, languages=self.languages)

        long_operation_settings = None
        if "long_operation_settings" in config:
            long_operation_settings = self._parse_long_operation_settings(
                config["long_operation_settings"]
            )

        # Дефолт для title - використовуємо name якщо не задано
        name = config["name"]
        title_ru = config.get("title_ru") or name
        title_uk = config.get("title_uk") or name

        return Command(
            name=name,
            title_ru=title_ru,
            title_uk=title_uk,
            title_en=config.get("title_en"),
            action=config["handler"],
            tooltip_ru=config.get("tooltip_ru"),
            tooltip_uk=config.get("tooltip_uk"),
            tooltip_en=config.get("tooltip_en"),
            picture=config.get("picture"),
            shortcut=config.get("shortcut"),
            long_operation=config.get("long_operation", False),
            long_operation_settings=long_operation_settings,
        )

    def _parse_long_operation_settings(self, config: Optional[Dict]) -> Optional[LongOperationSettings]:
        """Парсить налаштування фонового завдання."""
        if config is None:
            return None

        return LongOperationSettings(
            show_progress=config.get("show_progress", True),
            allow_cancel=config.get("allow_cancel", True),
            progress_message=config.get("progress_message", "Выполнение операции..."),
            progress_message_uk=config.get("progress_message_uk", "Виконання операції..."),
            progress_message_en=config.get("progress_message_en", "Operation in progress..."),
            timeout_seconds=config.get("timeout_seconds", 300),
            wait_completion_initial=config.get("wait_completion_initial", 0),
            use_additional_parameters=config.get("use_additional_parameters", False),
            output_messages=config.get("output_messages", True),
            output_progress=config.get("output_progress", False),
        )

    # =========================================================================
    # ValueTable & DynamicList
    # =========================================================================

    def _parse_value_table_config(self, config: Dict) -> ValueTableAttribute:
        """Парсить ValueTable конфігурацію."""
        config = normalize_multilang(config, languages=self.languages)
        vt = ValueTableAttribute(
            name=config["name"],
            title_ru=config.get("title_ru", config["name"]),
            title_uk=config.get("title_uk", config["name"]),
            title_en=config.get("title_en", config["name"]),
        )
        vt.columns = self._parse_columns(config.get("columns", []))
        return vt

    def _parse_value_tree_config(self, config: Dict) -> ValueTreeAttribute:
        """Парсить ValueTree конфігурацію (v2.64.0+).

        ValueTree - ієрархічна структура даних для Tree mode.
        """
        config = normalize_multilang(config, languages=self.languages)
        vt = ValueTreeAttribute(
            name=config["name"],
            title_ru=config.get("title_ru", config["name"]),
            title_uk=config.get("title_uk", config["name"]),
            title_en=config.get("title_en", config["name"]),
        )
        vt.columns = self._parse_columns(config.get("columns", []))
        return vt

    def _parse_dynamic_list_config(self, config: Dict) -> DynamicListAttribute:
        """Парсить DynamicList конфігурацію."""
        # Параметри
        parameters = []
        for param_config in config.get("parameters", []):
            param = DynamicListParameter(
                name=param_config["name"],
                type=param_config["type"],
                default_value=param_config.get("default_value"),
            )
            parameters.append(param)

        # Колонки
        columns = []
        for col_config in config.get("columns", []):
            col_config = normalize_multilang(col_config, languages=self.languages)
            col = DynamicListColumn(
                field=col_config["field"],
                title_ru=col_config.get("title_ru"),
                title_uk=col_config.get("title_uk"),
                title_en=col_config.get("title_en"),
                width=col_config.get("width"),
            )
            columns.append(col)

        config = normalize_multilang(config, languages=self.languages)
        return DynamicListAttribute(
            name=config["name"],
            title_ru=config.get("title_ru", config["name"]),
            title_uk=config.get("title_uk", config["name"]),
            title_en=config.get("title_en", config["name"]),
            manual_query=config.get("manual_query", False),
            main_table=config.get("main_table"),
            query_text=config.get("query_text"),
            key_fields=config.get("key_fields", []),
            parameters=parameters,
            use_always_fields=config.get("use_always_fields", []),
            functional_options=config.get("functional_options", []),
            auto_save_user_settings=config.get("auto_save_user_settings"),
            main_attribute=config.get("main_attribute", False),
            columns=columns,
            skip_stub_validation=config.get("skip_stub_validation", False),
        )

    # =========================================================================
    # Validation & Tests Config
    # =========================================================================

    def _parse_validation_config(self, processor: Processor) -> None:
        """Парсить секцію validation."""
        validation_data = self.config.get("validation", {})

        if not validation_data:
            processor.validation = ValidationConfig()
            return

        # Support both new names and old names (backwards compatibility)
        syntax_enabled = validation_data.get(
            "syntax_check_enabled",
            validation_data.get("check_modules_enabled", True)  # Old name fallback
        )
        semantic_enabled = validation_data.get(
            "semantic_check_enabled",
            validation_data.get("check_config_enabled", False)  # Old name fallback
        )

        processor.validation = ValidationConfig(
            syntax_check_enabled=syntax_enabled,
            check_thin_client=validation_data.get("check_thin_client", True),
            check_server=validation_data.get("check_server", True),
            check_web_client=validation_data.get("check_web_client", False),
            check_external_connection=validation_data.get("check_external_connection", False),
            check_thick_client=validation_data.get("check_thick_client", False),
            semantic_check_enabled=semantic_enabled,
            check_incorrect_references=validation_data.get("check_incorrect_references", True),
            check_handlers_existence=validation_data.get("check_handlers_existence", True),
            check_empty_handlers=validation_data.get("check_empty_handlers", True),
            check_unreference_procedures=validation_data.get("check_unreference_procedures", False),
            check_extended_modules=validation_data.get("check_extended_modules", True),
        )

    def _parse_tests_config(self, processor: Processor) -> None:
        """Парсить tests_file з processor конфігу."""
        processor_config = self.config.get("processor", {})
        tests_file = processor_config.get("tests_file")

        if not tests_file:
            processor.tests_config = None
            return

        tests_path = Path(tests_file)
        if not tests_path.is_absolute():
            tests_path = self.yaml_path.parent / tests_file

        if not tests_path.exists():
            print(f"⚠️ Файл tests.yaml не знайдено: {tests_path}")
            raise ValueError(f"Tests file not found: {tests_path}")

        try:
            print(f"📄 Завантаження tests.yaml: {tests_file}")
            tests_config = parse_tests_yaml(tests_path)

            if tests_config:
                processor.tests_config = tests_config
                print(
                    f"✅ Tests config завантажено: "
                    f"{len(tests_config.declarative_tests)} declarative, "
                    f"{len(tests_config.procedural_tests.procedures) if tests_config.procedural_tests else 0} procedural"
                )
            else:
                print(f"⚠️ Не вдалося розпарсити tests.yaml")
                processor.tests_config = None

        except Exception as e:
            print(f"❌ Помилка парсингу tests.yaml: {e}")
            raise

    # =========================================================================
    # Object Module
    # =========================================================================

    def _parse_object_module(self, processor: Processor) -> None:
        """Парсить секцію object_module."""
        if "object_module" not in self.config:
            return

        om_config = self.config["object_module"]

        if "file" not in om_config:
            print("⚠️ object_module: відсутнє поле 'file'")
            return

        file_path = Path(om_config["file"])
        if not file_path.is_absolute():
            file_path = self.yaml_path.parent / file_path

        if not file_path.exists():
            print(f"⚠️ ObjectModule файл не знайдено: {file_path}")
            return

        try:
            processor.object_module_bsl = file_path.read_text(encoding="utf-8-sig")
            print(f"✅ ObjectModule завантажено з {file_path.name}")
        except Exception as e:
            print(f"❌ Помилка читання ObjectModule файлу: {e}")
            import traceback
            traceback.print_exc()

    # =========================================================================
    # BSP Integration (v2.57.0+ PRO Feature)
    # =========================================================================

    def _parse_bsp_config(self, processor: Processor) -> None:
        """
        Парсить секцію bsp для інтеграції з БСП.

        PRO Feature: Потребує PRO ліцензії.

        YAML structure:
            bsp:
              type: print_form  # print_form, object_filling, report, etc.
              version: "1.0"
              safe_mode: true
              information: "Опис обробки"
              targets:
                - Документ.СчетНаОплату
              commands:
                - id: СчетНаОплату
                  title:
                    ru: Счет на оплату
                    uk: Рахунок на оплату
                  usage: server_method
        """
        if "bsp" not in self.config:
            return

        bsp_data = self.config["bsp"]

        # PRO feature check
        from .constants import is_bsp_pro_feature

        if is_bsp_pro_feature():
            # Server mode: PG_PRO_MODE=1 bypasses license check (for licensed web API)
            if os.environ.get("PG_PRO_MODE", "").strip() == "1":
                pass  # Skip license check - already verified by API
            else:
                try:
                    from .pro import get_license_manager
                    mgr = get_license_manager()
                    is_licensed, error = mgr.check_pro_feature("bsp_integration")

                    if not is_licensed:
                        print(f"⚠️  BSP integration requires PRO license: {error}")
                        raise ValueError(
                            "BSP integration is a PRO feature. "
                            "Purchase license at https://itdeo.tech/1c-processor-generator/#pricing"
                        )
                except ImportError:
                    # PRO module not available - raise error
                    raise ValueError(
                        "BSP integration requires PRO license. "
                        "PRO modules not found. Install the PRO version."
                    )

        # Import BSP type mappings from protected module
        from .pro.bsp_generator_impl import (
            get_bsp_type_mapping,
            get_bsp_usage_mapping,
        )

        bsp_type_mapping = get_bsp_type_mapping()
        bsp_usage_mapping = get_bsp_usage_mapping()

        # Parse type
        raw_type = bsp_data.get("type", "print_form")
        internal_type = bsp_type_mapping.get(raw_type)
        if not internal_type:
            valid_types = ", ".join(bsp_type_mapping.keys())
            raise ValueError(f"Invalid bsp.type: '{raw_type}'. Valid types: {valid_types}")

        # Parse commands
        commands = []
        for cmd_data in bsp_data.get("commands", []):
            cmd_data = normalize_multilang(cmd_data, languages=self.languages)

            # Parse usage
            raw_usage = cmd_data.get("usage", "server_method")
            internal_usage = bsp_usage_mapping.get(raw_usage)
            if not internal_usage:
                valid_usages = ", ".join(bsp_usage_mapping.keys())
                raise ValueError(
                    f"Invalid bsp.commands[].usage: '{raw_usage}'. Valid usages: {valid_usages}"
                )

            cmd = BSPCommand(
                id=cmd_data["id"],
                title_ru=cmd_data.get("title_ru", cmd_data["id"]),
                title_uk=cmd_data.get("title_uk"),
                title_en=cmd_data.get("title_en"),
                usage=internal_usage,
                modifier=cmd_data.get("modifier"),
                handler=cmd_data.get("handler"),
                template_name=cmd_data.get("template_name"),
                show_notification=cmd_data.get("show_notification", True),
                check_posting=cmd_data.get("check_posting", True),
                hide=cmd_data.get("hide", False),
                replaced_commands=cmd_data.get("replaced_commands"),
            )
            commands.append(cmd)

        # Create BSPConfig
        processor.bsp_config = BSPConfig(
            type=internal_type,
            version=bsp_data.get("version", "1.0"),
            safe_mode=bsp_data.get("safe_mode", True),
            information=bsp_data.get("information"),
            targets=bsp_data.get("targets", []),
            commands=commands,
            print_handler=bsp_data.get("print_handler", "Печать"),
        )

        print(f"✅ BSP config parsed: type={internal_type}, {len(commands)} command(s)")

    # =========================================================================
    # Templates
    # =========================================================================

    def _parse_templates(self, processor: Processor) -> None:
        """Парсить секцію templates."""
        templates_config = self.config.get("templates", [])

        if not templates_config:
            return

        print("   Loading templates...")

        for tmpl_config in templates_config:
            if "name" not in tmpl_config:
                raise ValueError("Template missing required field: 'name'")
            if "type" not in tmpl_config:
                raise ValueError(f"Template '{tmpl_config['name']}' missing required field: 'type'")
            if "file" not in tmpl_config:
                raise ValueError(f"Template '{tmpl_config['name']}' missing required field: 'file'")

            template_name = tmpl_config["name"]
            template_type = tmpl_config["type"]
            file_path = tmpl_config["file"]

            if template_type not in {"HTMLDocument", "SpreadsheetDocument"}:
                raise ValueError(
                    f"Template '{template_name}': Invalid type '{template_type}'. "
                    f"Valid types: HTMLDocument, SpreadsheetDocument"
                )

            content_path = Path(file_path)
            if not content_path.is_absolute():
                content_path = self.yaml_path.parent / file_path

            if not content_path.exists():
                raise ValueError(f"Template '{template_name}': File not found: {content_path}")

            template = Template(
                name=template_name,
                template_type=template_type,
                file_path=str(file_path),
                auto_field=tmpl_config.get("auto_field", False),
                field_name=tmpl_config.get("field_name"),
                target_form=tmpl_config.get("target_form"),
                automation_file=tmpl_config.get("automation"),
            )

            try:
                if template_type == "HTMLDocument":
                    template.content = content_path.read_text(encoding="utf-8")
                    print(f"      Loaded HTML template: {template_name} ({len(template.content)} chars)")
                elif template_type == "SpreadsheetDocument":
                    # v2.63.0: Auto-convert Excel (.xlsx) to MXL
                    if str(content_path).lower().endswith('.xlsx'):
                        try:
                            from .pro import convert_excel_to_mxl, EXCEL_TO_MXL_AVAILABLE
                            if not EXCEL_TO_MXL_AVAILABLE:
                                raise ValueError(
                                    f"Template '{template_name}': Excel conversion requires openpyxl. "
                                    "Install: pip install openpyxl>=3.1.0"
                                )
                            print(f"      Converting Excel → MXL: {content_path.name}")
                            conversion_warnings = []
                            mxl_content = convert_excel_to_mxl(
                                str(content_path),
                                warnings_out=conversion_warnings
                            )
                            template.content_binary = mxl_content.encode('utf-8')
                            # v2.78.0+: не мовчати про те, що не перенеслося з Excel
                            for warning in conversion_warnings:
                                print(f"      ⚠️ {warning}")
                            self._template_warnings.extend(
                                f"{content_path.name}: {w}" for w in conversion_warnings
                            )
                            print(f"      Converted SpreadsheetDocument: {template_name} ({len(template.content_binary)} bytes)")
                        except ImportError:
                            raise ValueError(
                                f"Template '{template_name}': Excel conversion requires PRO module. "
                                "Use .mxl file directly or convert with: python -m 1c_processor_generator excel2mxl"
                            )
                    else:
                        template.content_binary = content_path.read_bytes()
                        print(f"      Loaded SpreadsheetDocument: {template_name} ({len(template.content_binary)} bytes)")
            except Exception as e:
                raise ValueError(f"Template '{template_name}': Error loading file: {e}")

            if tmpl_config.get("automation"):
                self._load_template_automation(template, tmpl_config["automation"])

            processor.templates.append(template)

        print(f"   Templates loaded: {len(processor.templates)}")

    def _load_template_automation(self, template: Template, automation_path: str) -> None:
        """Завантажує automation файл для template."""
        auto_file = Path(automation_path)
        if not auto_file.is_absolute():
            auto_file = self.yaml_path.parent / automation_path

        if not auto_file.exists():
            raise ValueError(f"Template '{template.name}': Automation file not found: {auto_file}")

        try:
            auto_config = yaml.safe_load(auto_file.read_text(encoding="utf-8"))
        except Exception as e:
            raise ValueError(f"Template '{template.name}': Error loading automation file: {e}")

        if not auto_config:
            return

        # Placeholders
        for ph_config in auto_config.get("placeholders", []):
            if "name" not in ph_config:
                raise ValueError(f"Template '{template.name}': Placeholder missing 'name' field")

            placeholder = TemplatePlaceholder(
                name=ph_config["name"],
                bsl_value=ph_config.get("bsl_value"),
                attribute=ph_config.get("attribute"),
            )

            if not placeholder.bsl_value and not placeholder.attribute:
                raise ValueError(
                    f"Template '{template.name}': Placeholder '{placeholder.name}' "
                    f"must have either 'bsl_value' or 'attribute'"
                )

            template.placeholders.append(placeholder)

        # Assets
        assets_config = auto_config.get("assets")
        if assets_config:
            styles = []
            scripts = []

            for style_cfg in assets_config.get("styles", []):
                if "file" in style_cfg:
                    css_path = Path(style_cfg["file"])
                    if not css_path.is_absolute():
                        css_path = auto_file.parent / style_cfg["file"]

                    if not css_path.exists():
                        raise ValueError(f"Template '{template.name}': CSS file not found: {css_path}")

                    css_content = css_path.read_text(encoding="utf-8")
                    styles.append({"file": style_cfg["file"], "content": css_content})
                    print(f"         Loaded CSS: {style_cfg['file']} ({len(css_content)} chars)")
                elif "inline" in style_cfg:
                    styles.append({"inline": style_cfg["inline"]})

            for script_cfg in assets_config.get("scripts", []):
                if "file" in script_cfg:
                    js_path = Path(script_cfg["file"])
                    if not js_path.is_absolute():
                        js_path = auto_file.parent / script_cfg["file"]

                    if not js_path.exists():
                        raise ValueError(f"Template '{template.name}': JS file not found: {js_path}")

                    js_content = js_path.read_text(encoding="utf-8")
                    scripts.append({"file": script_cfg["file"], "content": js_content})
                    print(f"         Loaded JS: {script_cfg['file']} ({len(js_content)} chars)")
                elif "inline" in script_cfg:
                    scripts.append({"inline": script_cfg["inline"]})

            template.assets = TemplateAssets(styles=styles, scripts=scripts)

            if template.template_type == "HTMLDocument" and template.content:
                self._inject_assets_into_html(template)

        if template.placeholders:
            print(f"         Loaded {len(template.placeholders)} placeholders")

    def _inject_assets_into_html(self, template: Template) -> None:
        """Інжектує CSS/JS assets в HTML контент."""
        if not template.assets:
            return

        html = template.content

        # CSS → <head>
        if template.assets.styles:
            css_parts = []
            for style in template.assets.styles:
                if "content" in style:
                    css_parts.append(style["content"])
                elif "inline" in style:
                    css_parts.append(style["inline"])

            if css_parts:
                css_block = "\n<style>\n" + "\n".join(css_parts) + "\n</style>"

                if "</head>" in html:
                    html = html.replace("</head>", css_block + "\n</head>")
                elif "<body" in html.lower():
                    import re
                    html = re.sub(
                        r"(<body[^>]*>)",
                        css_block + r"\n\1",
                        html,
                        count=1,
                        flags=re.IGNORECASE
                    )
                else:
                    html = css_block + "\n" + html

        # JS → </body>
        if template.assets.scripts:
            js_parts = []
            for script in template.assets.scripts:
                if "content" in script:
                    js_parts.append(script["content"])
                elif "inline" in script:
                    js_parts.append(script["inline"])

            if js_parts:
                js_block = "\n<script>\n" + "\n".join(js_parts) + "\n</script>"

                if "</body>" in html:
                    html = html.replace("</body>", js_block + "\n</body>")
                else:
                    html = html + js_block

        template.content = html
        print(f"         Injected assets into HTML")

    def _process_template_auto_fields(self, processor: Processor) -> None:
        """Обробляє auto_field для всіх templates."""
        for template in processor.templates:
            if not template.auto_field:
                continue

            print(f"   ⚠️ DEPRECATED: auto_field on template '{template.name}' is deprecated (v2.42.0+)")
            print(f"      Use 'template: {template.name}' property on HTMLDocumentField instead.")

            if template.template_type != "HTMLDocument":
                print(f"   ⚠️ Warning: auto_field only supported for HTMLDocument templates")
                continue

            field_name = template.field_name or f"{template.name}Field"
            attr_name = f"{template.name}HTML"

            # Find target form
            target_form = None
            if template.target_form:
                for form in processor.forms:
                    if form.name == template.target_form:
                        target_form = form
                        break
                if not target_form:
                    raise ValueError(f"Template '{template.name}': target_form '{template.target_form}' not found")
            else:
                for form in processor.forms:
                    if form.default:
                        target_form = form
                        break
                if not target_form and processor.forms:
                    target_form = processor.forms[0]

            if not target_form:
                raise ValueError(f"Template '{template.name}': No form found for auto_field")

            form_attr = FormAttribute(
                name=attr_name,
                type="html_document",
                title_ru=template.name,
            )
            target_form.form_attributes.append(form_attr)

            html_field = FormElement(
                name=field_name,
                element_type="HTMLDocumentField",
                attribute=attr_name,
            )
            target_form.elements.append(html_field)

            print(f"      auto_field: Added {attr_name} attribute + {field_name} element to {target_form.name}")

    def _process_template_linked_fields(self, processor: Processor) -> None:
        """Обробляє HTMLDocumentField з template: property."""
        def process_elements(elements: list, form: Form, template_map: dict) -> None:
            for elem in elements:
                if elem.element_type == "HTMLDocumentField":
                    template_ref = elem.properties.get("template_ref")
                    if template_ref and not elem.attribute:
                        template = template_map.get(template_ref)
                        if not template:
                            raise ValueError(f"HTMLDocumentField '{elem.name}': template '{template_ref}' not found")

                        attr_name = f"{template_ref}HTML"

                        form_attr = FormAttribute(
                            name=attr_name,
                            type="string",
                            title_ru=template.name,
                        )
                        form.form_attributes.append(form_attr)

                        elem.attribute = attr_name
                        elem.properties["_linked_template"] = template

                        print(f"      template link: {elem.name} -> {template_ref} (attr: {attr_name})")

                # Рекурсивно для child_items (Pages → Page → elements)
                if elem.child_items:
                    process_elements(elem.child_items, form, template_map)

        template_map = {t.name: t for t in processor.templates}

        if not template_map:
            return

        for form in processor.forms:
            process_elements(form.elements, form, template_map)


# =============================================================================
# Public API
# =============================================================================

def parse_yaml_config(
    yaml_path: Path,
    handlers_dir: Optional[Path] = None,
    handlers_file: Optional[Path] = None,
    normalize_bsl_escapes: bool = False,
) -> Optional[Processor]:
    """
    Парсить YAML конфігурацію та створює Processor об'єкт.

    Args:
        yaml_path: Шлях до YAML файлу
        handlers_dir: Шлях до директорії з окремими BSL файлами (старий підхід)
        handlers_file: Шлях до монолітного BSL файлу (новий підхід)
        normalize_bsl_escapes: Нормалізувати escape-послідовності в BSL (v2.72.0+)

    Returns:
        Processor об'єкт або None якщо помилка
    """
    parser = YAMLParser(yaml_path)
    processor = parser.parse()

    # Інжекція handlers
    needs_injection = False
    if processor:
        has_global_handlers = handlers_dir or handlers_file
        has_form_handlers = (
            hasattr(processor, "forms") and processor.forms and
            any(form.handlers_dir or form.handlers_file for form in processor.forms)
        )
        needs_injection = has_global_handlers or has_form_handlers

    if needs_injection:
        from .bsl_injector import BSLInjector

        injector = BSLInjector(
            handlers_dir=handlers_dir,
            handlers_file=handlers_file,
            normalize_escapes=normalize_bsl_escapes
        )
        injector.inject_all_handlers(processor)

        # v2.66.0+: Передаємо код з регіону #Область МодульОбъекта в Processor
        if injector._object_module_from_handlers:
            processor.object_module_from_handlers = injector._object_module_from_handlers

        # v2.48.0+: Валідація handlers
        from .validators import HandlerValidator

        handler_validator = HandlerValidator(
            processor=processor,
            loaded_handlers=injector._loaded_handlers,
            handlers_file=handlers_file,
        )
        is_valid, errors, warnings = handler_validator.validate()

        if warnings:
            print("⚠️  Попередження (handlers):")
            for warning in warnings:
                print(f"   - {warning}")

        if not is_valid:
            print("⚠️  Проблеми валідації handlers (генерація продовжується):")
            for error in errors:
                print(f"   - {error}")

        # v2.78.0+: Переносимо в processor, щоб попередження було видно і в кінці
        # виводу, а не лише тут - інакше воно тоне у логах перед "✨ Готово!"
        processor.generation_warnings.extend(warnings)
        processor.generation_warnings.extend(errors)

    return processor
