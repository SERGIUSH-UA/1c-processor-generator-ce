"""
Sync tool - Main CLI interface for synchronizing changes from modified EPF/XML back to YAML+BSL.

This module provides the main entry point for the sync command, which:
1. Compares original vs modified XML/BSL
2. Detects changes
3. Maps changes to YAML/BSL updates
4. Applies updates (with backup and preview)

Supports two modes:
- Interactive mode (default): Shows preview, asks for confirmation
- LLM mode (--llm-mode): Automatic application with JSON output for LLM agents
"""

import os
import json
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from ruamel.yaml import YAML

from .xml_differ import XMLDiffer, ChangeType, ElementType, XMLChange
from .bsl_differ import BSLDiffer, BSLCodeExtractor
from .change_mapper import ChangeMapper, YAMLUpdate, BSLUpdate, StructuralUpdate
from .yaml_patcher import YAMLPatcher
from .diff_visualizer import DiffVisualizer  # v2.28.0
from .change_formatter import ChangeFormatter  # v2.28.0
from .yaml_comment_utils import update_value_preserving_comments  # v2.30.0

logger = logging.getLogger(__name__)


class SyncTool:
    """
    Main synchronization tool that orchestrates the sync process.

    This class coordinates XMLDiffer, BSLDiffer, and ChangeMapper to
    detect changes and apply them back to YAML and BSL source files.
    """

    def __init__(
        self,
        original_xml: str,
        modified_xml: str,
        config_path: str,
        handlers_path: str,
        auto_apply: bool = False,
        json_output: bool = False,
        llm_mode: bool = False
    ):
        """
        Initialize sync tool.

        Args:
            original_xml: Path to original generated XML (from snapshot)
            modified_xml: Path to modified XML (from Configurator)
            config_path: Path to YAML config file
            handlers_path: Path to BSL handlers file
            auto_apply: Automatically apply changes without confirmation
            json_output: Output results as JSON (for LLM consumption)
            llm_mode: LLM-friendly mode (auto_apply + json_output + structured output)
        """
        self.original_xml = original_xml
        self.modified_xml = modified_xml
        self.config_path = config_path
        self.handlers_path = handlers_path

        # LLM mode enables both auto-apply and JSON output
        if llm_mode:
            auto_apply = True
            json_output = True

        self.auto_apply = auto_apply
        self.json_output = json_output
        self.llm_mode = llm_mode

        # Initialize components
        self.xml_differ = XMLDiffer(original_xml, modified_xml)
        self.mapper = ChangeMapper(config_path)

        # Store modified tree for XML data extraction (v2.26.0)
        self.modified_tree = self.xml_differ.modified_tree

        # BSL differ will be initialized after extracting BSL from XML
        self.bsl_differ = None

        # Results
        self.yaml_updates: List[YAMLUpdate] = []
        self.bsl_updates: List[BSLUpdate] = []
        self.structural_updates: List[StructuralUpdate] = []  # v2.26.0: add/delete operations

    def run(self) -> Dict:
        """
        Run the full sync process.

        Returns:
            Dictionary with sync results (for JSON output or reporting)
        """
        logger.info("Starting sync process...")

        # Step 1: Detect XML changes
        xml_changes = self.xml_differ.detect_changes()

        # Step 2: Detect BSL changes
        bsl_changes = self._detect_bsl_changes()

        # Step 3: Map changes to updates
        self.yaml_updates = self.mapper.map_xml_changes(xml_changes)
        self.bsl_updates = self.mapper.map_bsl_changes(bsl_changes)

        # Step 3.5: Detect structural changes (v2.26.0)
        self.structural_updates = self._detect_structural_changes(xml_changes)

        # Step 4: Get user approval with conflict resolution UI (if not auto-apply)
        if not self.auto_apply:
            if not self._resolve_conflicts():
                logger.info("Sync cancelled by user")
                return {"status": "cancelled", "reason": "user_cancelled"}

        # Step 5: Create backup
        backup_dir = self._create_backup()

        # Step 6: Apply updates
        try:
            self._apply_yaml_updates()
            self._apply_bsl_updates()
            self._apply_structural_updates()  # v2.26.0

            result = {
                "status": "success",
                "backup_dir": backup_dir,
                "changes_applied": {
                    "yaml_updates": len(self.yaml_updates),
                    "bsl_updates": len(self.bsl_updates),
                    "structural_updates": len(self.structural_updates)  # v2.26.0
                }
            }

            if self.llm_mode:
                result["details"] = self._get_llm_friendly_summary()

            logger.info("Sync completed successfully")
            return result

        except Exception as e:
            logger.error(f"Sync failed: {e}")
            # Restore from backup
            self._restore_from_backup(backup_dir)
            return {
                "status": "error",
                "error": str(e),
                "backup_restored": True
            }

    def _detect_bsl_changes(self) -> List:
        """Detect BSL changes by extracting and comparing BSL code."""
        # Extract BSL from original XML
        original_bsl = self._extract_bsl_from_snapshot()

        # Extract BSL from modified (try .bsl files first, then XML as fallback)
        modified_bsl = self._extract_bsl_from_modified()

        if not original_bsl or not modified_bsl:
            logger.warning("Could not extract BSL code for comparison")
            return []

        # Compare
        self.bsl_differ = BSLDiffer(original_bsl, modified_bsl)
        return self.bsl_differ.detect_changes()

    def _extract_bsl_from_snapshot(self) -> str:
        """
        Extract BSL code from snapshot.

        Snapshot can contain either:
        1. original_handlers.bsl file (combined BSL)
        2. Or we extract from original XML
        """
        snapshot_dir = Path(self.original_xml).parent

        # Try to find original_handlers.bsl in snapshot
        handlers_snapshot = snapshot_dir / "original_handlers.bsl"
        if handlers_snapshot.exists():
            return BSLCodeExtractor.extract_from_bsl_file(str(handlers_snapshot))

        # Otherwise extract from XML
        return BSLCodeExtractor.extract_from_xml(self.original_xml)

    def _extract_bsl_from_modified(self) -> str:
        """
        Extract BSL code from modified XML export directory (v2.31.0).

        Configurator exports BSL to separate .bsl files, not inside XML.
        This method reads BSL from exported directory structure:
        - Ext/ObjectModule.bsl
        - Forms/*/Ext/Form/Module.bsl

        v2.31.0: Removed XML fallback - BSL is never in XML (user clarification).
        """
        modified_xml_path = Path(self.modified_xml)
        modified_dir = modified_xml_path.parent

        # Processor name from XML filename
        processor_name = modified_xml_path.stem

        # Expected directory structure from Configurator export
        processor_dir = modified_dir / processor_name

        collected_bsl = []

        # 1. Try to read ObjectModule.bsl
        object_module_path = processor_dir / "Ext" / "ObjectModule.bsl"
        if object_module_path.exists():
            object_module_bsl = BSLCodeExtractor.extract_from_bsl_file(str(object_module_path))
            if object_module_bsl:
                collected_bsl.append(object_module_bsl)
                logger.info(f"Read ObjectModule.bsl ({len(object_module_bsl)} chars)")

        # 2. Try to read Form Module.bsl (all forms)
        forms_dir = processor_dir / "Forms"
        if forms_dir.exists():
            for form_dir in forms_dir.iterdir():
                if form_dir.is_dir():
                    form_module_path = form_dir / "Ext" / "Form" / "Module.bsl"
                    if form_module_path.exists():
                        form_bsl = BSLCodeExtractor.extract_from_bsl_file(str(form_module_path))
                        if form_bsl:
                            collected_bsl.append(form_bsl)
                            logger.info(f"Read {form_dir.name}/Module.bsl ({len(form_bsl)} chars)")

        # If we found .bsl files, return combined BSL
        if collected_bsl:
            combined = "\n\n".join(collected_bsl)
            logger.info(f"Total modified BSL: {len(combined)} chars from {len(collected_bsl)} modules")
            return combined

        # v2.31.0: No fallback to XML - BSL is never in XML
        logger.warning(f"No .bsl files found in export directory: {processor_dir}")
        logger.warning("Expected structure: ProcessorName/Ext/ObjectModule.bsl or ProcessorName/Forms/*/Ext/Form/Module.bsl")
        return ""

    def _detect_structural_changes(self, xml_changes: List) -> List[StructuralUpdate]:
        """
        Detect structural changes (add/delete elements) from XML changes.

        Args:
            xml_changes: List of XMLChange objects from XMLDiffer

        Returns:
            List of StructuralUpdate objects
        """
        structural_updates = []

        for change in xml_changes:
            if change.change_type == ChangeType.ADD:
                # New element added - extract full data from XML
                element_data = self._extract_element_data(change)
                element_data['_xpath'] = change.xpath  # Store xpath for form index extraction

                structural_updates.append(StructuralUpdate(
                    operation="add",
                    element_type=self._map_element_type(change.element_type),
                    element_data=element_data,
                    parent_path=change.parent_path,  # v2.28.0: hierarchy metadata
                    insertion_index=change.insertion_index,
                    depth=change.depth
                ))

            elif change.change_type == ChangeType.DELETE:
                # Element deleted
                element_name = change.old_value or "unknown"
                structural_updates.append(StructuralUpdate(
                    operation="delete",
                    element_type=self._map_element_type(change.element_type),
                    element_data={
                        "name": element_name,
                        "_xpath": change.xpath
                    },
                    references=[],  # Will be filled by YAMLPatcher during application
                    parent_path=change.parent_path,  # v2.28.0: hierarchy metadata
                    insertion_index=None,  # Not needed for delete
                    depth=change.depth
                ))

        return structural_updates

    def _map_element_type(self, xml_element_type: ElementType) -> str:
        """Map XMLDiffer ElementType to StructuralUpdate element_type."""
        mapping = {
            ElementType.ATTRIBUTE: "attribute",
            ElementType.FORM_ELEMENT: "form_element",
            ElementType.COMMAND: "command",
            ElementType.TABULAR_SECTION: "tabular_section",
            ElementType.TABULAR_SECTION_COLUMN: "tabular_column",
            ElementType.VALUE_TABLE: "value_table",  # v2.27.0
            ElementType.VALUE_TABLE_COLUMN: "value_table_column",
            ElementType.FORM_ATTRIBUTE: "form_attribute",
            ElementType.FORM: "form"  # v2.34.0: Whole form add/delete
        }
        return mapping.get(xml_element_type, "unknown")

    def _extract_element_data(self, xml_change: XMLChange) -> Dict:
        """
        Extract complete element data from XML for add operations.

        Uses XMLDiffer methods instead of xpath for reliable element lookup.
        v2.26.0 - Full implementation with reliable lookup
        """
        try:
            from lxml import etree as ET
        except ImportError:
            logger.warning("lxml not available, using minimal extraction")
            return {"name": xml_change.new_value or "NewElement"}

        # Find element using XMLDiffer methods (more reliable than xpath)
        element_name = xml_change.new_value or "NewElement"

        try:
            # Use XMLDiffer methods to find element by type and name
            elem = None

            if xml_change.element_type == ElementType.ATTRIBUTE:
                # Get all attributes and find by name
                attrs = self.xml_differ._get_processor_attributes(self.modified_tree)
                elem = attrs.get(element_name)
                if elem is not None:
                    return self._parse_attribute_data(elem)

            elif xml_change.element_type == ElementType.FORM_ELEMENT:
                # Get form elements
                form_root = self.xml_differ._get_form_xml(self.modified_tree)
                if form_root is not None:
                    elements = self.xml_differ._get_form_elements(form_root)
                    elem = elements.get(element_name)
                    if elem is not None:
                        return self._parse_form_element_data(elem)

            elif xml_change.element_type == ElementType.COMMAND:
                # Get commands
                commands = self.xml_differ._get_commands(self.modified_tree)
                elem = commands.get(element_name)
                if elem is not None:
                    return self._parse_command_data(elem)

            elif xml_change.element_type == ElementType.TABULAR_SECTION:
                # Get tabular sections
                sections = self.xml_differ._get_tabular_sections(self.modified_tree)
                elem = sections.get(element_name)
                if elem is not None:
                    return self._parse_tabular_section_data(elem)

            elif xml_change.element_type == ElementType.VALUE_TABLE:
                # Get value tables (v2.27.0)
                form_root = self.xml_differ._get_form_xml(self.modified_tree)
                if form_root is not None:
                    value_tables = self.xml_differ._get_value_tables(form_root)
                    elem = value_tables.get(element_name)
                    if elem is not None:
                        return self._parse_value_table_data(elem)

            elif xml_change.element_type == ElementType.FORM_ATTRIBUTE:
                # Get form attributes (v2.27.0)
                form_root = self.xml_differ._get_form_xml(self.modified_tree)
                if form_root is not None:
                    form_attrs = self.xml_differ._get_form_attributes(form_root)
                    elem = form_attrs.get(element_name)
                    if elem is not None:
                        return self._parse_form_attribute_data(elem)

            elif xml_change.element_type == ElementType.FORM:
                # Get form data (v2.34.0)
                return self._parse_form_data(element_name)

            # If element not found, return minimal data
            logger.warning(f"Element '{element_name}' not found for type {xml_change.element_type}")
            return {"name": element_name}

        except Exception as e:
            logger.error(f"Failed to extract element data: {e}")
            return {"name": element_name}

    def _parse_attribute_data(self, elem) -> Dict:
        """Parse processor attribute data from XML element."""
        from lxml import etree as ET

        NAMESPACES = self.xml_differ.NAMESPACES
        data = {}

        # Name (required)
        name_elem = elem.find(".//ns:Properties/ns:Name", namespaces=NAMESPACES)
        data['name'] = name_elem.text if name_elem is not None else "UnknownAttr"

        # Type - use XMLDiffer method and map to YAML types
        type_str = self.xml_differ._get_attribute_type(elem)
        if type_str and type_str != "unknown":
            # Map XML types to YAML types (v2.32.1)
            if type_str in ["decimal", "double", "float"]:
                data['type'] = "number"
            elif type_str == "string":
                data['type'] = "string"
            elif type_str == "boolean":
                data['type'] = "boolean"
            elif type_str in ["date", "dateTime"]:
                data['type'] = "date"
            else:
                data['type'] = type_str

            # Number qualifiers (digits, fraction_digits)
            if data.get('type') == "number":
                digits_elem = elem.find(".//ns:Properties/ns:Type/v8:NumberQualifiers/v8:Digits", namespaces=NAMESPACES)
                if digits_elem is not None and digits_elem.text:
                    data['digits'] = int(digits_elem.text)

                fraction_elem = elem.find(".//ns:Properties/ns:Type/v8:NumberQualifiers/v8:FractionDigits", namespaces=NAMESPACES)
                if fraction_elem is not None and fraction_elem.text:
                    data['fraction_digits'] = int(fraction_elem.text)

        # Synonym (multilingual) - use XMLDiffer method
        synonym_values = self.xml_differ._get_multilang_text(elem, "Synonym")
        for lang, text in synonym_values.items():
            data[f'synonym_{lang}'] = text

        return data

    def _parse_form_element_data(self, elem) -> Dict:
        """
        Parse form element data from XML element.

        v2.28.0: Added recursive parsing of child_items for nested elements.
        """
        from lxml import etree as ET

        NAMESPACES = self.xml_differ.NAMESPACES
        data = {}

        # Name (required) - it's an XML attribute in Form.xml
        # v2.32.1: <InputField name="Field1"> - name is attribute, not child element
        data['name'] = elem.get("name", "UnknownElement")

        # Type - extract from tag name (v2.32.1 fix)
        # In Form.xml: <InputField> → "InputField", <Table> → "Table"
        tag = elem.tag
        if isinstance(tag, str):
            # Remove namespace: "{http://...}InputField" → "InputField"
            element_type = tag.split('}')[-1] if '}' in tag else tag
            data['type'] = element_type

        # DataPath - use local-name() for namespace-independent search
        datapath_elems = elem.xpath(".//*[local-name()='DataPath']")
        if datapath_elems and datapath_elems[0].text:
            # Extract attribute name from DataPath like "Объект.Product" or "Подсчет"
            datapath_text = datapath_elems[0].text
            parts = datapath_text.split(".")
            if len(parts) > 1:
                data['attribute'] = parts[-1]
            else:
                # Form attribute - no "Объект." prefix
                data['attribute'] = datapath_text

        # Title (multilingual) - use XMLDiffer method
        title_values = self.xml_differ._get_multilang_text(elem, "Title")
        for lang, text in title_values.items():
            data[f'title_{lang}'] = text

        # ReadOnly property (v2.32.1)
        readonly_elems = elem.xpath(".//*[local-name()='ReadOnly']")
        if readonly_elems and readonly_elems[0].text:
            readonly_text = readonly_elems[0].text.strip().lower()
            if readonly_text == "true":
                data['read_only'] = True

        # v2.28.0: Parse child_items recursively for nested elements
        # v2.32.1: Use local-name() xpath for namespace-independent search
        child_containers = elem.xpath(".//*[local-name()='ChildItems']")
        if child_containers:
            child_items_container = child_containers[0]
            children = []
            # Iterate all direct children (InputField, Button, Table, etc.)
            for child_elem in child_items_container:
                # Recursive call
                child_data = self._parse_form_element_data(child_elem)
                if child_data:
                    children.append(child_data)

            if children:
                data['child_items'] = children

        # v2.33.0: Parse element events using XMLDiffer method
        element_events = self.xml_differ._get_element_events(elem)
        if element_events:
            data['events'] = element_events

        # v2.33.0: Parse element properties using XMLDiffer method
        element_properties = self.xml_differ._get_element_properties(elem)
        if element_properties:
            # Merge properties into data dict
            data.update(element_properties)

        return data

    def _parse_command_data(self, elem) -> Dict:
        """Parse command data from XML element."""
        NAMESPACES = self.xml_differ.NAMESPACES
        data = {}

        # Name (required)
        name_elem = elem.find("form:Name", namespaces=NAMESPACES)
        data['name'] = name_elem.text if name_elem is not None else "UnknownCommand"

        # Action
        action_elem = elem.find("form:Action", namespaces=NAMESPACES)
        if action_elem is not None and action_elem.text:
            data['action'] = action_elem.text

        # Title (multilingual) - use XMLDiffer method
        title_values = self.xml_differ._get_multilang_text(elem, "Title")
        for lang, text in title_values.items():
            data[f'title_{lang}'] = text

        return data

    def _parse_tabular_section_data(self, elem) -> Dict:
        """Parse tabular section data from XML element."""
        NAMESPACES = self.xml_differ.NAMESPACES
        data = {}

        # Name (required)
        name_elem = elem.find(".//ns:Properties/ns:Name", namespaces=NAMESPACES)
        data['name'] = name_elem.text if name_elem is not None else "UnknownSection"

        # Synonym (multilingual) - use XMLDiffer method
        synonym_values = self.xml_differ._get_multilang_text(elem, "Synonym")
        for lang, text in synonym_values.items():
            data[f'synonym_{lang}'] = text

        # Columns (if any) - v2.32.1: extract full column data including type
        columns = []
        for col in elem.findall(".//ns:ChildObjects/ns:Attribute", namespaces=NAMESPACES):
            col_name = col.find(".//ns:Properties/ns:Name", namespaces=NAMESPACES)
            if col_name is not None:
                col_data = {"name": col_name.text}

                # Column type
                col_type_elem = col.find(".//ns:Properties/ns:Type/v8:Type", namespaces=NAMESPACES)
                if col_type_elem is not None and col_type_elem.text:
                    type_str = col_type_elem.text.split(":")[-1]  # "xs:decimal" → "decimal"
                    # Map to YAML types
                    if type_str in ["decimal", "double", "float"]:
                        col_data['type'] = "number"
                    elif type_str == "string":
                        col_data['type'] = "string"
                    elif type_str == "boolean":
                        col_data['type'] = "boolean"
                    elif type_str in ["date", "dateTime"]:
                        col_data['type'] = "date"

                    # Number qualifiers (digits, fraction_digits)
                    if col_data.get('type') == "number":
                        digits_elem = col.find(".//ns:Properties/ns:Type/v8:NumberQualifiers/v8:Digits", namespaces=NAMESPACES)
                        if digits_elem is not None and digits_elem.text:
                            col_data['digits'] = int(digits_elem.text)

                        fraction_elem = col.find(".//ns:Properties/ns:Type/v8:NumberQualifiers/v8:FractionDigits", namespaces=NAMESPACES)
                        if fraction_elem is not None and fraction_elem.text:
                            col_data['fraction_digits'] = int(fraction_elem.text)

                # Column synonym
                col_synonym = self.xml_differ._get_multilang_text(col, "Synonym")
                for lang, text in col_synonym.items():
                    col_data[f'synonym_{lang}'] = text

                columns.append(col_data)

        if columns:
            data['columns'] = columns

        return data

    def _parse_value_table_data(self, elem) -> Dict:
        """
        Parse ValueTable form attribute data from XML element.
        v2.27.0 feature - ValueTables are form-level attributes with columns.
        """
        NAMESPACES = self.xml_differ.NAMESPACES
        data = {}

        # Name (required)
        name_elem = elem.find("form:Name", namespaces=NAMESPACES)
        data['name'] = name_elem.text if name_elem is not None else "UnknownValueTable"

        # Columns - nested under ValueType/Types/Type/ValueTable/Columns
        columns = []
        for col in elem.findall(".//v8:Column", namespaces=NAMESPACES):
            col_name = col.find("v8:Name", namespaces=NAMESPACES)
            if col_name is not None:
                col_data = {"name": col_name.text}

                # Column type
                col_type = col.find("v8:ValueType/v8:Type", namespaces=NAMESPACES)
                if col_type is not None and col_type.text:
                    # Extract type from string like "xs:string" or "xs:decimal"
                    type_str = col_type.text.split(":")[-1]
                    col_data['type'] = type_str

                columns.append(col_data)

        if columns:
            data['columns'] = columns

        return data

    def _parse_form_attribute_data(self, elem) -> Dict:
        """
        Parse form-only attribute data (SpreadsheetDocument, BinaryData, etc.).
        v2.27.0 feature - form attributes not stored in processor object.
        """
        NAMESPACES = self.xml_differ.NAMESPACES
        data = {}

        # Name (required) - it's an XML attribute in Form.xml
        # v2.32.1: <Attribute name="Подсчет"> - name is attribute, not child element
        data['name'] = elem.get("name", "UnknownFormAttr")

        # Type - use xpath to find in any namespace
        # v2.32.1: Type child element may need namespace handling
        type_elems = elem.xpath(".//v8:Type", namespaces=NAMESPACES)
        if type_elems and type_elems[0].text:
            # Extract type like "SpreadsheetDocument", "BinaryData", or xs:decimal
            type_text = type_elems[0].text
            # Map form attribute types
            if "SpreadsheetDocument" in type_text:
                data['type'] = "SpreadsheetDocument"
            elif "BinaryData" in type_text:
                data['type'] = "BinaryData"
            elif "Picture" in type_text:
                data['type'] = "Picture"
            elif "ValueStorage" in type_text:
                data['type'] = "ValueStorage"
            elif "FormDataTree" in type_text:
                data['type'] = "FormDataTree"
            elif "FormDataCollection" in type_text:
                data['type'] = "FormDataCollection"
            elif "decimal" in type_text:
                data['type'] = "number"
            elif "string" in type_text:
                data['type'] = "string"
            elif "boolean" in type_text:
                data['type'] = "boolean"
            elif "date" in type_text or "dateTime" in type_text:
                data['type'] = "date"
            else:
                data['type'] = "unknown"

        return data

    def _parse_form_data(self, form_name: str) -> Dict:
        """
        Parse complete form data from Form.xml.

        v2.34.0: Extract all form components for whole form synchronization.

        Args:
            form_name: Name of the form to parse

        Returns:
            Dict with complete form structure (name, elements, commands, etc.)
        """
        data = {'name': form_name}

        try:
            # Get Form.xml for this form (from modified tree)
            form_root = self.xml_differ._get_form_xml(self.modified_tree, form_name=form_name)

            if form_root is None:
                logger.warning(f"Form.xml not found for form '{form_name}'")
                return data

            # Extract form elements hierarchically (with nesting)
            elements_tree = self.xml_differ._get_form_elements_hierarchical(form_root)
            if elements_tree:
                # Convert hierarchical elements to YAML format
                data['elements'] = self._convert_elements_tree_to_yaml(elements_tree)

            # Extract commands
            commands_dict = self.xml_differ._get_commands_from_form(form_root)
            if commands_dict:
                commands = []
                for cmd_name, cmd_elem in commands_dict.items():
                    cmd_data = self._parse_command_data(cmd_elem)
                    commands.append(cmd_data)
                data['commands'] = commands

            # Extract form attributes (SpreadsheetDocument, etc.)
            form_attrs_dict = self.xml_differ._get_form_attributes(form_root)
            if form_attrs_dict:
                form_attributes = []
                for attr_name, attr_elem in form_attrs_dict.items():
                    attr_data = self._parse_form_attribute_data(attr_elem)
                    form_attributes.append(attr_data)
                data['form_attributes'] = form_attributes

            # Extract value tables
            value_tables_dict = self.xml_differ._get_value_tables(form_root)
            if value_tables_dict:
                value_tables = []
                for vt_name, vt_elem in value_tables_dict.items():
                    vt_data = self._parse_value_table_data(vt_elem)
                    value_tables.append(vt_data)
                data['value_table_attributes'] = value_tables

            # Set default property (first form is usually default)
            # Note: This is a heuristic - actual default detection would require
            # checking processor properties
            data['default'] = (form_name == "Форма")

            logger.debug(f"Parsed form data for '{form_name}': {len(data.get('elements', []))} elements, "
                        f"{len(data.get('commands', []))} commands")

        except Exception as e:
            logger.error(f"Failed to parse form data for '{form_name}': {e}")

        return data

    def _convert_elements_tree_to_yaml(self, elements_tree: List) -> List[Dict]:
        """
        Convert hierarchical element tree to YAML format.

        Recursively processes nested elements (child_items).

        Args:
            elements_tree: List of ElementNode objects with hierarchy

        Returns:
            List of element dicts suitable for YAML
        """
        result = []
        for element_node in elements_tree:
            # Parse element data from XML element
            elem_data = self._parse_form_element_data(element_node.element)

            # Recursively process child items
            if element_node.children:
                elem_data['child_items'] = self._convert_elements_tree_to_yaml(element_node.children)

            result.append(elem_data)

        return result

    def _extract_form_index_from_xpath(self, xpath: str) -> int:
        """
        Extract form index from xpath.

        XPath examples:
        - "//Form[1]/Items/Item" → form_index = 0 (xpath indices are 1-based)
        - "//Item[@name='Product']" → form_index = 0 (default)

        Returns:
            Form index (0-based)
        """
        import re

        # Look for Form[N] pattern in xpath
        match = re.search(r'/Form\[(\d+)\]', xpath)
        if match:
            # Convert from 1-based XPath index to 0-based Python index
            return int(match.group(1)) - 1

        # Default to first form
        return 0

    def _resolve_conflicts(self) -> bool:
        """
        Interactive conflict resolution - review and approve each change individually.

        Phase 2.4 (v2.26.0): Granular change approval with detailed warnings.
        v2.28.0: Enhanced with DiffVisualizer for better change preview.

        Returns:
            True if at least one change approved, False if all skipped/quit
        """
        if not self.yaml_updates and not self.bsl_updates and not self.structural_updates:
            print("\nNo changes detected.")
            return False

        # v2.28.0: Initialize visualizers
        diff_viz = DiffVisualizer(context_lines=3)
        formatter = ChangeFormatter(use_unicode=True)

        print("\n" + "=" * 70)
        print("CONFLICT RESOLUTION")
        print("=" * 70)
        print("\nOptions for each change:")
        print("  [y] Apply this change")
        print("  [n] Skip this change")
        print("  [a] Apply all remaining changes")
        print("  [s] Skip all remaining changes")
        print("  [d] Show detailed information with diff preview")
        print("  [p] Show side-by-side preview")
        print("  [q] Quit without applying any changes")
        print("=" * 70)

        # Collect all updates to review
        all_updates = []

        # Add YAML updates
        for update in self.yaml_updates:
            all_updates.append(("YAML", update))

        # Add BSL updates
        for update in self.bsl_updates:
            all_updates.append(("BSL", update))

        # Add structural updates
        for update in self.structural_updates:
            all_updates.append(("STRUCTURAL", update))

        # Track approved changes
        approved_yaml = []
        approved_bsl = []
        approved_structural = []

        auto_approve_all = False

        for idx, (change_type, update) in enumerate(all_updates, start=1):
            # Auto-approve if "apply all" selected
            if auto_approve_all:
                if change_type == "YAML":
                    approved_yaml.append(update)
                elif change_type == "BSL":
                    approved_bsl.append(update)
                elif change_type == "STRUCTURAL":
                    approved_structural.append(update)
                continue

            # Show change - v2.28.0: Use better formatting
            print(f"\n[{idx}/{len(all_updates)}] {change_type} Change:")
            print("-" * 70)

            # Use ChangeFormatter for STRUCTURAL updates, simple string for others
            if change_type == "STRUCTURAL":
                formatted = formatter.format_change(update, mode='simple')
                print(f"  {formatted}")
            else:
                print(f"  {update}")

            # Show warnings for structural deletions
            if change_type == "STRUCTURAL" and hasattr(update, 'references') and update.references:
                print(f"\n  ⚠️  WARNING: Found {len(update.references)} references:")
                for ref in update.references[:3]:  # Show first 3 references
                    print(f"      - {ref}")
                if len(update.references) > 3:
                    print(f"      ... and {len(update.references) - 3} more")
                print("\n  ⚠️  Applying this change may break existing code!")

            # Get user decision
            while True:
                choice = input("\nDecision [y/n/a/s/d/q]: ").strip().lower()

                if choice == 'y':
                    if change_type == "YAML":
                        approved_yaml.append(update)
                    elif change_type == "BSL":
                        approved_bsl.append(update)
                    elif change_type == "STRUCTURAL":
                        approved_structural.append(update)
                    print("✓ Change will be applied")
                    break

                elif choice == 'n':
                    print("✗ Change skipped")
                    break

                elif choice == 'a':
                    # Apply this and all remaining
                    if change_type == "YAML":
                        approved_yaml.append(update)
                    elif change_type == "BSL":
                        approved_bsl.append(update)
                    elif change_type == "STRUCTURAL":
                        approved_structural.append(update)
                    auto_approve_all = True
                    print("✓ This and all remaining changes will be applied")
                    break

                elif choice == 's':
                    # Skip this and all remaining
                    print("✗ All remaining changes skipped")
                    # Exit early
                    self.yaml_updates = approved_yaml
                    self.bsl_updates = approved_bsl
                    self.structural_updates = approved_structural

                    total_approved = len(approved_yaml) + len(approved_bsl) + len(approved_structural)
                    print(f"\n{total_approved} change(s) approved, {len(all_updates) - idx} skipped")
                    return total_approved > 0

                elif choice == 'd':
                    # v2.28.0: Show detailed info with visual diff
                    print("\n" + "=" * 70)
                    print("DETAILED VIEW")
                    print("=" * 70)

                    if change_type == "STRUCTURAL":
                        # Use DiffVisualizer for structural changes
                        detailed = formatter.format_change(update, mode='detailed', references=update.references)
                        print(detailed)

                        # Show YAML change preview
                        if update.operation == "add" and update.element_data:
                            viz = diff_viz.visualize_yaml_change(
                                element_type=update.element_type,
                                element_name=update.element_data.get('name', 'unknown'),
                                operation=update.operation,
                                element_data=update.element_data,
                                config=self.config,
                                yaml_path=update.parent_path
                            )
                            print(viz)

                    elif change_type == "BSL":
                        # Show BSL code diff
                        viz = diff_viz.visualize_bsl_change(
                            procedure_name=update.procedure_name,
                            old_code=update.old_code,
                            new_code=update.new_code,
                            operation=update.update_type
                        )
                        print(viz)

                    elif change_type == "YAML":
                        # Show YAML change details
                        print(f"  Path: {update.path}")
                        print(f"  Section: {update.section}")
                        print(f"  Element: {update.element_name}")
                        print(f"  Old value: {update.old_value}")
                        print(f"  New value: {update.new_value}")

                    print("=" * 70)
                    continue  # Ask again

                elif choice == 'p':
                    # v2.28.0: Show side-by-side preview
                    print("\n" + "=" * 70)
                    print("SIDE-BY-SIDE PREVIEW")
                    print("=" * 70)

                    if change_type == "BSL" and update.old_code and update.new_code:
                        # Side-by-side BSL code comparison
                        side_by_side = diff_viz.create_side_by_side(
                            left_title="Before",
                            right_title="After",
                            left_content=update.old_code,
                            right_content=update.new_code,
                            width=35
                        )
                        print(side_by_side)
                    elif change_type == "STRUCTURAL":
                        # Show hierarchical position
                        viz = diff_viz.visualize_structural_change(
                            element_type=update.element_type,
                            element_name=update.element_data.get('name', 'unknown') if update.element_data else 'unknown',
                            operation=update.operation,
                            parent_path=update.parent_path,
                            insertion_index=update.insertion_index,
                            config=self.config
                        )
                        print(viz)
                    else:
                        print("  Preview not available for this change type")

                    print("=" * 70)
                    continue  # Ask again

                elif choice == 'q':
                    print("\n✗ Sync cancelled")
                    return False

                else:
                    print("Invalid choice. Please enter y/n/a/s/d/p/q")
                    continue

        # Update the change lists with approved changes
        self.yaml_updates = approved_yaml
        self.bsl_updates = approved_bsl
        self.structural_updates = approved_structural

        total_approved = len(approved_yaml) + len(approved_bsl) + len(approved_structural)

        if total_approved == 0:
            print("\n✗ No changes approved")
            return False

        print(f"\n✓ {total_approved} change(s) approved")
        return True

    def _create_backup(self) -> str:
        """
        Create backup of YAML and BSL files before modifying.

        Returns:
            Path to backup directory
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = Path(self.config_path).parent / f".sync_backup_{timestamp}"
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Backup YAML config
        shutil.copy2(self.config_path, backup_dir / Path(self.config_path).name)

        # Backup BSL handlers
        if os.path.exists(self.handlers_path):
            shutil.copy2(self.handlers_path, backup_dir / Path(self.handlers_path).name)

        logger.info(f"Created backup in {backup_dir}")
        return str(backup_dir)

    def _restore_from_backup(self, backup_dir: str):
        """Restore files from backup."""
        backup_path = Path(backup_dir)

        # Restore YAML
        yaml_backup = backup_path / Path(self.config_path).name
        if yaml_backup.exists():
            shutil.copy2(yaml_backup, self.config_path)

        # Restore BSL
        bsl_backup = backup_path / Path(self.handlers_path).name
        if bsl_backup.exists():
            shutil.copy2(bsl_backup, self.handlers_path)

        logger.info(f"Restored files from backup {backup_dir}")

    def _apply_yaml_updates(self):
        """Apply YAML updates to config file."""
        if not self.yaml_updates:
            return

        logger.info(f"Applying {len(self.yaml_updates)} YAML updates...")

        # Load YAML with ruamel.yaml (preserves formatting)
        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.default_flow_style = False
        # v2.30.0: Explicit comment preservation settings
        yaml.map_indent = 2
        yaml.sequence_indent = 2
        yaml.sequence_dash_offset = 0

        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.load(f)

        # Apply each update
        for update in self.yaml_updates:
            self._apply_single_yaml_update(config, update)

        # Save updated config
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f)

        logger.info("YAML updates applied successfully")

    def _apply_single_yaml_update(self, config: dict, update: YAMLUpdate):
        """
        Apply a single YAML update to config.

        v2.30.0: Now uses update_value_preserving_comments to preserve YAML comments
        during value updates.

        v2.33.1: Preserves missing multilingual properties (input_hint_*, title_*, etc)
        when working with single-language Configurator.
        """
        # Parse path like "attributes[2].name" or "forms[0].elements[3].title"
        path_parts = self._parse_update_path(update.path)

        # Navigate to parent
        current = config
        for part in path_parts[:-1]:
            if isinstance(part, str):
                current = current[part]
            elif isinstance(part, int):
                current = current[part]

        # Apply update to final field
        final_key = path_parts[-1]

        # v2.33.1: Preserve missing multilingual properties
        # If update removes a multilang property (new_value=None) but it exists in YAML,
        # skip the update to preserve translations from other languages
        if self._is_multilang_property_key(final_key) and update.new_value is None:
            if final_key in current and current[final_key] is not None:
                logger.debug(f"Preserving multilingual property {final_key} "
                           f"(missing in modified XML but exists in YAML)")
                return  # Skip this update, preserve existing value

        # v2.33.0: Special handling for events dict (merge instead of replace)
        if final_key == 'events' and isinstance(update.new_value, dict):
            # Merge events: preserve existing events, add/update new ones
            if 'events' in current:
                # Existing events - merge
                if isinstance(current['events'], dict):
                    current['events'].update(update.new_value)
                else:
                    # Convert to dict if needed
                    current['events'] = update.new_value
            else:
                # No existing events - set new
                update_value_preserving_comments(current, final_key, update.new_value)
            return

        # Special handling for multilingual fields (synonym, title, tooltip)
        if final_key in ['synonym', 'title', 'tooltip']:
            # Parse multilingual value from update (format: "ru:'text', uk:'текст'")
            if isinstance(update.new_value, str) and ':' in update.new_value:
                # Split by language
                lang_values = {}
                for part in update.new_value.split(', '):
                    if ':' in part:
                        lang, value = part.split(':', 1)
                        lang_values[lang] = value.strip("'\"")

                # v2.30.0: Use comment-preserving update
                update_value_preserving_comments(current, final_key, lang_values)
            else:
                # v2.30.0: Use comment-preserving update
                update_value_preserving_comments(current, final_key, update.new_value)
        else:
            # Simple field update
            # v2.30.0: Use comment-preserving update (works for both string and int keys)
            update_value_preserving_comments(current, final_key, update.new_value)

    def _is_multilang_property_key(self, key: str) -> bool:
        """
        Check if property key is multilingual (ends with _ru, _uk, _en).

        Examples: title_ru, tooltip_uk, input_hint_en, synonym_ru

        v2.33.1 helper method.

        Args:
            key: Property key to check

        Returns:
            True if key is multilingual property
        """
        if not isinstance(key, str):
            return False

        # Check if key ends with language suffix
        for lang in ['_ru', '_uk', '_en']:
            if key.endswith(lang):
                # Extract prefix (e.g., 'title' from 'title_ru')
                prefix = key[:-len(lang)]
                # Check if prefix is a known multilingual property
                multilang_prefixes = ['title', 'tooltip', 'input_hint', 'synonym']
                if prefix in multilang_prefixes:
                    return True

        return False

    def _parse_update_path(self, path: str) -> List:
        """
        Parse update path like "attributes[2].name" into list of keys.

        Returns:
            List like ["attributes", 2, "name"]
        """
        import re

        parts = []
        pattern = r'(\w+)|\[(\d+)\]'

        for match in re.finditer(pattern, path):
            if match.group(1):  # Field name
                parts.append(match.group(1))
            elif match.group(2):  # Index
                parts.append(int(match.group(2)))

        return parts

    def _apply_bsl_updates(self):
        """Apply BSL updates to handlers file."""
        if not self.bsl_updates:
            return

        logger.info(f"Applying {len(self.bsl_updates)} BSL updates...")

        # Read current handlers file
        with open(self.handlers_path, 'r', encoding='utf-8-sig') as f:
            current_bsl = f.read()

        # Apply each update
        for update in self.bsl_updates:
            current_bsl = self._apply_single_bsl_update(current_bsl, update)

        # Save updated handlers
        with open(self.handlers_path, 'w', encoding='utf-8-sig') as f:
            f.write(current_bsl)

        logger.info("BSL updates applied successfully")

    def _build_procedure_regex(self, procedure_name: str) -> 're.Pattern':
        """
        Build regex pattern to match procedure by name (v2.31.0).

        This regex-based approach handles whitespace differences between XML export
        and source files, solving the BSL modify bug where exact string matching fails.

        Pattern matches:
        - Optional directives (&НаКлиенте, &НаСервере, etc.)
        - Procedure/Function keyword
        - Procedure name
        - Parameters (any content in parentheses)
        - Optional Export keyword
        - Body (non-greedy match until end keyword)
        - End keyword (КонецПроцедуры/КонецФункции)

        Args:
            procedure_name: Name of the procedure to match

        Returns:
            Compiled regex pattern
        """
        import re

        # Escape procedure name for regex (handles special chars)
        escaped_name = re.escape(procedure_name)

        # Build pattern
        pattern = re.compile(
            rf'(?:&[А-ЯЁа-яёA-Za-z]+\s*)*'  # Optional directives (can be multiple)
            rf'(?:Процедура|Функция)\s+'     # Procedure or Function keyword
            rf'{escaped_name}'               # Procedure name (escaped)
            rf'\s*\([^)]*\)'                 # Parameters in parentheses
            rf'(?:\s+Экспорт)?'              # Optional Export keyword
            rf'.*?'                          # Body (non-greedy)
            rf'Конец(?:Процедуры|Функции)',  # End keyword
            re.DOTALL | re.IGNORECASE        # Match across lines, case-insensitive
        )

        return pattern

    def _apply_single_bsl_update(self, bsl_code: str, update: BSLUpdate) -> str:
        """Apply a single BSL update to code."""
        import re

        if update.update_type == "add":
            # Add new procedure at the end (before last #КонецОбласті if exists)
            # Or just append if no regions
            if '#КонецОбласті' in bsl_code:
                # Find last occurrence
                last_region_end = bsl_code.rfind('#КонецОбласті')
                # Insert before it
                bsl_code = (bsl_code[:last_region_end] +
                           '\n' + update.new_code + '\n\n' +
                           bsl_code[last_region_end:])
            else:
                # Just append
                bsl_code += '\n\n' + update.new_code

        elif update.update_type == "delete":
            # Remove procedure
            # Find and remove the old code
            if update.old_code and update.old_code in bsl_code:
                bsl_code = bsl_code.replace(update.old_code, '')

        elif update.update_type == "modify":
            # Replace old procedure with new one (v2.31.0: regex-based matching)
            if update.new_code and update.procedure_name:
                # Build regex pattern to match procedure by name (not by exact text)
                pattern = self._build_procedure_regex(update.procedure_name)

                # Check if procedure exists
                match = pattern.search(bsl_code)
                if match:
                    # Replace matched procedure with new code
                    bsl_code = pattern.sub(update.new_code, bsl_code, count=1)
                    logger.debug(f"Modified procedure '{update.procedure_name}' using regex matching")
                else:
                    # Procedure not found - log warning
                    logger.warning(f"Could not find procedure '{update.procedure_name}' to modify")
                    # Fallback: Try exact string match (for backward compatibility)
                    if update.old_code and update.old_code in bsl_code:
                        bsl_code = bsl_code.replace(update.old_code, update.new_code)
                        logger.debug(f"Modified procedure '{update.procedure_name}' using exact string matching (fallback)")
                    else:
                        logger.error(f"Failed to modify procedure '{update.procedure_name}' - not found in BSL code")

        return bsl_code

    def _apply_structural_updates(self):
        """
        Apply structural changes (add/delete elements) to YAML config.

        Uses YAMLPatcher for safe operations with reference checking.
        v2.26.0 feature.
        """
        if not self.structural_updates:
            return

        logger.info(f"Applying {len(self.structural_updates)} structural updates...")

        # Load BSL code for reference checking
        bsl_code = ""
        if os.path.exists(self.handlers_path):
            with open(self.handlers_path, 'r', encoding='utf-8-sig') as f:
                bsl_code = f.read()

        # Initialize YAMLPatcher
        patcher = YAMLPatcher(self.config_path, bsl_code)

        # Apply each structural update
        for update in self.structural_updates:
            success = self._apply_single_structural_update(patcher, update)

            if not success:
                logger.warning(f"Failed to apply structural update: {update}")

        # Check for warnings
        warnings = patcher.get_warnings()
        if warnings:
            for warning in warnings:
                logger.warning(warning)

        # Save patched YAML
        if patcher.save():
            logger.info("Structural updates applied successfully")
        else:
            raise Exception("Failed to save structural updates to YAML")

    def _apply_single_structural_update(self, patcher: YAMLPatcher,
                                       update: StructuralUpdate) -> bool:
        """
        Apply a single structural update using YAMLPatcher.

        Args:
            patcher: YAMLPatcher instance
            update: StructuralUpdate to apply

        Returns:
            True if applied successfully
        """
        element_name = update.element_data.get('name', 'unknown')
        xpath = update.element_data.get('_xpath', '')

        # Extract form index from xpath (for form elements and commands)
        form_index = self._extract_form_index_from_xpath(xpath) if xpath else 0

        # Clean element_data (remove internal fields)
        clean_data = {k: v for k, v in update.element_data.items() if not k.startswith('_')}

        if update.operation == "add":
            # Add element
            if update.element_type == "attribute":
                return patcher.add_attribute(clean_data)

            elif update.element_type == "form_element":
                # v2.28.0: Use nested method if parent_path is set
                if update.parent_path:
                    return patcher.add_form_element_nested(
                        form_index,
                        clean_data,
                        parent_path=update.parent_path,
                        insertion_index=update.insertion_index
                    )
                else:
                    return patcher.add_form_element(form_index, clean_data, position=update.insertion_index)

            elif update.element_type == "command":
                return patcher.add_command(form_index, clean_data)

            elif update.element_type == "tabular_section":
                return patcher.add_tabular_section(clean_data)

            elif update.element_type == "value_table":
                # v2.27.0: ValueTable support
                return patcher.add_value_table(form_index, clean_data)

            elif update.element_type == "form_attribute":
                # v2.27.0: FormAttribute support
                return patcher.add_form_attribute(form_index, clean_data)

            elif update.element_type == "form":
                # v2.34.0: Whole form support
                return patcher.add_form(clean_data)

            else:
                logger.warning(f"Add operation not yet supported for {update.element_type}")
                return False

        elif update.operation == "delete":
            # Delete element (with reference checking)
            if update.element_type == "attribute":
                return patcher.delete_attribute(element_name, force=False)

            elif update.element_type == "form_element":
                # v2.28.0: Use nested method if parent_path is set
                if update.parent_path:
                    return patcher.delete_form_element_nested(
                        form_index,
                        element_name,
                        parent_path=update.parent_path,
                        force=False
                    )
                else:
                    return patcher.delete_form_element(form_index, element_name, force=False)

            elif update.element_type == "command":
                return patcher.delete_command(form_index, element_name, force=False)

            elif update.element_type == "tabular_section":
                return patcher.delete_tabular_section(element_name, force=False)

            elif update.element_type == "value_table":
                # v2.27.0: ValueTable support
                return patcher.delete_value_table(form_index, element_name, force=False)

            elif update.element_type == "form_attribute":
                # v2.27.0: FormAttribute support
                return patcher.delete_form_attribute(form_index, element_name, force=False)

            elif update.element_type == "form":
                # v2.34.0: Whole form support
                return patcher.delete_form(element_name, force=False)

            else:
                logger.warning(f"Delete operation not yet supported for {update.element_type}")
                return False

        return False

    def _get_llm_friendly_summary(self) -> Dict:
        """
        Generate LLM-friendly structured summary of changes.

        Returns:
            Dictionary with detailed change information for LLM agent
        """
        return {
            "yaml_changes": [
                {
                    "path": u.path,
                    "section": u.section,
                    "element_name": u.element_name,
                    "old_value": u.old_value,
                    "new_value": u.new_value
                }
                for u in self.yaml_updates
            ],
            "bsl_changes": [
                {
                    "type": u.update_type,
                    "procedure_name": u.procedure_name,
                    "has_code_change": u.old_code != u.new_code if u.old_code and u.new_code else True
                }
                for u in self.bsl_updates
            ],
            "structural_changes": [
                {
                    "operation": u.operation,
                    "element_type": u.element_type,
                    "element_name": u.element_data.get('name', 'unknown'),
                    "has_references": len(u.references) > 0 if u.references else False,
                    "reference_count": len(u.references) if u.references else 0
                }
                for u in self.structural_updates
            ],
            "summary": {
                "total_changes": len(self.yaml_updates) + len(self.bsl_updates) + len(self.structural_updates),
                "yaml_updates": len(self.yaml_updates),
                "bsl_updates": len(self.bsl_updates),
                "structural_updates": len(self.structural_updates),
                "affected_sections": list(set(u.section for u in self.yaml_updates))
            }
        }

    def print_results(self, result: Dict):
        """Print results (JSON or human-readable based on mode)."""
        if self.json_output:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print("\n" + "=" * 70)
            print("SYNC RESULT")
            print("=" * 70)
            print(f"\nStatus: {result['status']}")

            if result['status'] == 'success':
                print(f"Backup created: {result['backup_dir']}")
                print(f"\nChanges applied:")
                print(f"  • YAML updates: {result['changes_applied']['yaml_updates']}")
                print(f"  • BSL updates: {result['changes_applied']['bsl_updates']}")
                if 'structural_updates' in result['changes_applied']:
                    print(f"  • Structural updates: {result['changes_applied']['structural_updates']}")
            elif result['status'] == 'error':
                print(f"\nError: {result['error']}")
                if result.get('backup_restored'):
                    print("Files restored from backup")

            print("\n" + "=" * 70)


def run_sync(
    original_xml: str,
    modified_xml: str,
    config: str,
    handlers: str,
    auto_apply: bool = False,
    json_output: bool = False,
    llm_mode: bool = False
) -> int:
    """
    Main entry point for sync command.

    Args:
        original_xml: Path to original XML (from snapshot)
        modified_xml: Path to modified XML (from Configurator)
        config: Path to YAML config file
        handlers: Path to BSL handlers file
        auto_apply: Auto-apply without confirmation
        json_output: Output as JSON
        llm_mode: LLM-friendly mode

    Returns:
        Exit code (0 for success, 1 for error)
    """
    # Configure logging
    log_level = logging.INFO if not llm_mode else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format='%(levelname)s: %(message)s'
    )

    try:
        tool = SyncTool(
            original_xml=original_xml,
            modified_xml=modified_xml,
            config_path=config,
            handlers_path=handlers,
            auto_apply=auto_apply,
            json_output=json_output,
            llm_mode=llm_mode
        )

        result = tool.run()
        tool.print_results(result)

        return 0 if result['status'] == 'success' else 1

    except Exception as e:
        logger.exception("Sync failed with exception")
        if json_output or llm_mode:
            print(json.dumps({"status": "error", "error": str(e)}, indent=2))
        else:
            print(f"\nERROR: {e}")
        return 1
