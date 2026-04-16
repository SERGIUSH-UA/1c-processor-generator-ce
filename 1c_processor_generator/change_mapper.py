"""
Change mapping module that converts XML/BSL changes to YAML/BSL file updates.

This module maps detected changes from XMLDiffer and BSLDiffer to concrete
updates that need to be applied to YAML config and BSL handler files.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union
import logging
from ruamel.yaml import YAML

from .xml_differ import XMLChange, ChangeType, ElementType
from .bsl_differ import BSLChange, BSLChangeType

logger = logging.getLogger(__name__)


@dataclass
class YAMLUpdate:
    """
    Represents an update to be applied to YAML config.

    Examples:
        - path: "attributes[name=Product].synonym"
          old_value: "Товар"
          new_value: "Product"

        - path: "forms[0].elements[name=ProductField].title"
          old_value: "Товар"
          new_value: "Product"
    """
    path: str  # JSONPath-like path to field
    old_value: Any
    new_value: Any
    section: str  # Section name (attributes, forms, commands, etc.)
    element_name: Optional[str] = None  # Name of element being updated

    def __str__(self) -> str:
        return f"YAML: {self.path}: '{self.old_value}' → '{self.new_value}'"


@dataclass
class BSLUpdate:
    """
    Represents an update to be applied to BSL handlers file.

    Examples:
        - update_type: "add"
          procedure_name: "NewProcedure"
          new_code: "Процедура NewProcedure()..."

        - update_type: "modify"
          procedure_name: "Calculate"
          old_code: "..."
          new_code: "..."
    """
    update_type: str  # "add", "delete", "modify"
    procedure_name: str
    old_code: Optional[str] = None
    new_code: Optional[str] = None

    def __str__(self) -> str:
        if self.update_type == "add":
            return f"BSL: Add procedure '{self.procedure_name}'"
        elif self.update_type == "delete":
            return f"BSL: Delete procedure '{self.procedure_name}'"
        else:
            return f"BSL: Modify procedure '{self.procedure_name}'"


@dataclass
class StructuralUpdate:
    """
    Represents a structural change (add/delete element).

    This is different from YAMLUpdate which modifies existing elements.
    Structural updates add or remove entire elements.

    v2.26.0+ feature
    v2.28.0: Added hierarchy metadata for nested elements support
    """
    operation: str  # "add", "delete"
    element_type: str  # "attribute", "form_element", "command", "tabular_column"
    element_data: Dict[str, Any]  # Complete element data for add, or minimal data for delete
    references: Optional[List[str]] = None  # References found (for delete)

    # v2.28.0: Hierarchy metadata for nested elements
    parent_path: Optional[str] = None  # YAML path to parent (e.g., 'forms[0].elements[2]')
    insertion_index: Optional[int] = None  # Index where to insert
    depth: int = 0  # Nesting depth (0 = top-level)

    def __str__(self) -> str:
        if self.operation == "add":
            name = self.element_data.get('name', 'unknown')
            return f"STRUCTURAL: Add {self.element_type} '{name}'"
        else:
            name = self.element_data.get('name', 'unknown')
            ref_count = len(self.references) if self.references else 0
            return f"STRUCTURAL: Delete {self.element_type} '{name}' ({ref_count} references)"


class ChangeMapper:
    """
    Maps XML/BSL changes to YAML/BSL file updates.

    This class knows the structure of YAML config and can generate
    precise update paths for any detected change.
    """

    def __init__(self, config_path: str):
        """
        Initialize mapper with YAML config.

        Args:
            config_path: Path to YAML config file
        """
        self.config_path = config_path
        self.config = self._load_config(config_path)

    def _load_config(self, config_path: str) -> dict:
        """Load YAML config file."""
        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.default_flow_style = False
        # v2.30.0: Explicit comment preservation settings
        yaml.map_indent = 2
        yaml.sequence_indent = 2
        yaml.sequence_dash_offset = 0

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.load(f)
        except Exception as e:
            logger.error(f"Failed to load config {config_path}: {e}")
            raise

    def map_xml_changes(self, xml_changes: List[XMLChange]) -> List[YAMLUpdate]:
        """
        Map XML changes to YAML updates.

        Args:
            xml_changes: List of detected XML changes

        Returns:
            List of YAML updates to apply
        """
        updates = []

        for change in xml_changes:
            mapped = self._map_single_xml_change(change)
            if mapped:
                if isinstance(mapped, list):
                    updates.extend(mapped)
                else:
                    updates.append(mapped)

        return updates

    def map_bsl_changes(self, bsl_changes: List[BSLChange]) -> List[BSLUpdate]:
        """
        Map BSL changes to BSL file updates.

        Args:
            bsl_changes: List of detected BSL changes

        Returns:
            List of BSL updates to apply
        """
        updates = []

        for change in bsl_changes:
            mapped = self._map_single_bsl_change(change)
            if mapped:
                updates.append(mapped)

        return updates

    def _map_single_xml_change(self, change: XMLChange) -> Optional[Union[YAMLUpdate, List[YAMLUpdate]]]:
        """Map a single XML change to YAML update(s)."""

        if change.element_type == ElementType.ATTRIBUTE:
            return self._map_attribute_change(change)

        elif change.element_type == ElementType.FORM_ELEMENT:
            return self._map_form_element_change(change)

        elif change.element_type == ElementType.COMMAND:
            return self._map_command_change(change)

        elif change.element_type == ElementType.TABULAR_SECTION:
            return self._map_tabular_section_change(change)

        elif change.element_type == ElementType.TABULAR_SECTION_COLUMN:
            return self._map_tabular_column_change(change)

        elif change.element_type == ElementType.FORM:
            return self._map_form_change(change)

        return None

    def _map_single_bsl_change(self, change: BSLChange) -> Optional[BSLUpdate]:
        """Map a single BSL change to BSL update."""

        if change.change_type == BSLChangeType.PROCEDURE_ADDED:
            return BSLUpdate(
                update_type="add",
                procedure_name=change.procedure_name,
                new_code=change.new_code
            )

        elif change.change_type == BSLChangeType.PROCEDURE_DELETED:
            return BSLUpdate(
                update_type="delete",
                procedure_name=change.procedure_name,
                old_code=change.old_code
            )

        elif change.change_type == BSLChangeType.PROCEDURE_MODIFIED:
            return BSLUpdate(
                update_type="modify",
                procedure_name=change.procedure_name,
                old_code=change.old_code,
                new_code=change.new_code
            )

        return None

    # ==================== Attribute mapping ====================

    def _map_attribute_change(self, change: XMLChange) -> Optional[Union[YAMLUpdate, List[YAMLUpdate]]]:
        """Map processor attribute change to YAML update."""

        if change.change_type == ChangeType.RENAME:
            # Attribute renamed - need to update multiple places
            return self._handle_attribute_rename(change.old_value, change.new_value)

        elif change.change_type == ChangeType.PROPERTY_CHANGE:
            # Property changed (synonym, tooltip, etc.)
            attr_name = change.element_name
            property_name = change.property_name

            # Find attribute index in YAML
            attr_idx = self._find_attribute_index(attr_name)
            if attr_idx is None:
                logger.warning(f"Attribute '{attr_name}' not found in YAML")
                return None

            # Map property name to YAML field
            yaml_field = self._map_property_to_yaml_field(property_name)

            path = f"attributes[{attr_idx}].{yaml_field}"

            return YAMLUpdate(
                path=path,
                old_value=change.old_value,
                new_value=change.new_value,
                section="attributes",
                element_name=attr_name
            )

        elif change.change_type == ChangeType.TYPE_CHANGE:
            # Type changed
            attr_name = change.element_name
            attr_idx = self._find_attribute_index(attr_name)
            if attr_idx is None:
                return None

            path = f"attributes[{attr_idx}].type"

            return YAMLUpdate(
                path=path,
                old_value=change.old_value,
                new_value=change.new_value,
                section="attributes",
                element_name=attr_name
            )

        elif change.change_type == ChangeType.ADD:
            # v2.26.0: Generate structural update for add
            logger.info(f"Attribute added: {change.new_value}")
            # Return StructuralUpdate instead of YAMLUpdate
            # NOTE: This will be handled by YAMLPatcher, not direct YAML update
            return None  # For now, still requires manual intervention (full implementation in sync_tool.py)

        elif change.change_type == ChangeType.DELETE:
            # v2.26.0: Generate structural update for delete
            logger.info(f"Attribute deleted: {change.old_value}")
            return None  # For now, still requires manual intervention

        return None

    def _handle_attribute_rename(self, old_name: str, new_name: str) -> List[YAMLUpdate]:
        """
        Handle attribute rename - needs to update multiple places.

        When attribute is renamed, we need to update:
        1. Attribute name in attributes[] section
        2. All form elements that reference this attribute (DataPath, attribute field)
        3. Potentially tabular section columns if this is a reference
        """
        updates = []

        # 1. Update attribute name itself
        attr_idx = self._find_attribute_index(old_name)
        if attr_idx is not None:
            updates.append(YAMLUpdate(
                path=f"attributes[{attr_idx}].name",
                old_value=old_name,
                new_value=new_name,
                section="attributes",
                element_name=old_name
            ))

        # 2. Update form elements that reference this attribute
        form_updates = self._find_form_element_references(old_name, new_name)
        updates.extend(form_updates)

        return updates

    def _find_form_element_references(self, old_attr_name: str, new_attr_name: str) -> List[YAMLUpdate]:
        """Find all form elements that reference an attribute and create updates."""
        updates = []

        # Check forms section
        if 'forms' not in self.config:
            return updates

        for form_idx, form in enumerate(self.config['forms']):
            if 'elements' not in form:
                continue

            for elem_idx, element in enumerate(form['elements']):
                # Check if element references the attribute
                if element.get('attribute') == old_attr_name:
                    path = f"forms[{form_idx}].elements[{elem_idx}].attribute"
                    updates.append(YAMLUpdate(
                        path=path,
                        old_value=old_attr_name,
                        new_value=new_attr_name,
                        section="forms",
                        element_name=element.get('name', 'unknown')
                    ))

        return updates

    # ==================== Form element mapping ====================

    def _map_form_element_change(self, change: XMLChange) -> Optional[YAMLUpdate]:
        """Map form element change to YAML update."""

        if change.change_type == ChangeType.RENAME:
            # Form element renamed
            elem_name = change.old_value
            new_name = change.new_value

            elem_path = self._find_form_element_path(elem_name)
            if elem_path is None:
                logger.warning(f"Form element '{elem_name}' not found in YAML")
                return None

            path = f"{elem_path}.name"

            return YAMLUpdate(
                path=path,
                old_value=elem_name,
                new_value=new_name,
                section="forms",
                element_name=elem_name
            )

        elif change.change_type == ChangeType.PROPERTY_CHANGE:
            # Property changed (title, tooltip, width, etc.)
            elem_name = change.element_name
            property_name = change.property_name

            elem_path = self._find_form_element_path(elem_name)
            if elem_path is None:
                return None

            yaml_field = self._map_property_to_yaml_field(property_name)
            path = f"{elem_path}.{yaml_field}"

            return YAMLUpdate(
                path=path,
                old_value=change.old_value,
                new_value=change.new_value,
                section="forms",
                element_name=elem_name
            )

        return None

    # ==================== Command mapping ====================

    def _map_command_change(self, change: XMLChange) -> Optional[YAMLUpdate]:
        """Map command change to YAML update."""

        if change.change_type == ChangeType.RENAME:
            cmd_name = change.old_value
            new_name = change.new_value

            cmd_path = self._find_command_path(cmd_name)
            if cmd_path is None:
                return None

            path = f"{cmd_path}.name"

            return YAMLUpdate(
                path=path,
                old_value=cmd_name,
                new_value=new_name,
                section="forms",
                element_name=cmd_name
            )

        elif change.change_type == ChangeType.PROPERTY_CHANGE:
            cmd_name = change.element_name
            property_name = change.property_name

            cmd_path = self._find_command_path(cmd_name)
            if cmd_path is None:
                return None

            yaml_field = self._map_property_to_yaml_field(property_name)
            path = f"{cmd_path}.{yaml_field}"

            return YAMLUpdate(
                path=path,
                old_value=change.old_value,
                new_value=change.new_value,
                section="forms",
                element_name=cmd_name
            )

        return None

    # ==================== Tabular section mapping ====================

    def _map_tabular_section_change(self, change: XMLChange) -> Optional[YAMLUpdate]:
        """Map tabular section change to YAML update."""

        if change.change_type == ChangeType.RENAME:
            section_name = change.old_value
            new_name = change.new_value

            section_idx = self._find_tabular_section_index(section_name)
            if section_idx is None:
                return None

            path = f"tabular_sections[{section_idx}].name"

            return YAMLUpdate(
                path=path,
                old_value=section_name,
                new_value=new_name,
                section="tabular_sections",
                element_name=section_name
            )

        return None

    def _map_tabular_column_change(self, change: XMLChange) -> Optional[YAMLUpdate]:
        """Map tabular section column change to YAML update."""

        # parent_name is tabular section name (stored in element_name for columns)
        section_name = change.element_name

        if change.change_type == ChangeType.RENAME:
            col_name = change.old_value
            new_name = change.new_value

            col_path = self._find_tabular_column_path(section_name, col_name)
            if col_path is None:
                return None

            path = f"{col_path}.name"

            return YAMLUpdate(
                path=path,
                old_value=col_name,
                new_value=new_name,
                section="tabular_sections",
                element_name=f"{section_name}.{col_name}"
            )

        elif change.change_type == ChangeType.TYPE_CHANGE:
            col_name = change.element_name

            col_path = self._find_tabular_column_path(section_name, col_name)
            if col_path is None:
                return None

            path = f"{col_path}.type"

            return YAMLUpdate(
                path=path,
                old_value=change.old_value,
                new_value=change.new_value,
                section="tabular_sections",
                element_name=f"{section_name}.{col_name}"
            )

        return None

    # ==================== Form mapping ====================

    def _map_form_change(self, change: XMLChange) -> Optional[YAMLUpdate]:
        """
        Map form change to YAML update.

        v2.34.0: Forms only support ADD/DELETE operations (handled via StructuralUpdate).
        RENAME and PROPERTY_CHANGE are not currently supported for whole forms.

        Returns:
            None (ADD/DELETE handled by SyncTool._detect_structural_changes)
        """
        # Forms only have ADD/DELETE changes, which are handled via StructuralUpdate
        # in SyncTool._detect_structural_changes(), not via YAMLUpdate.
        # If we need to support form rename or property changes in the future,
        # they would be implemented here.
        return None

    # ==================== Helper methods for finding elements in YAML ====================

    def _find_attribute_index(self, attr_name: str) -> Optional[int]:
        """Find index of attribute in YAML config."""
        if 'attributes' not in self.config:
            return None

        for idx, attr in enumerate(self.config['attributes']):
            if attr.get('name') == attr_name:
                return idx

        return None

    def _find_form_element_path(self, elem_name: str) -> Optional[str]:
        """Find path to form element in YAML config."""
        if 'forms' not in self.config:
            return None

        for form_idx, form in enumerate(self.config['forms']):
            if 'elements' not in form:
                continue

            for elem_idx, element in enumerate(form['elements']):
                if element.get('name') == elem_name:
                    return f"forms[{form_idx}].elements[{elem_idx}]"

        return None

    def _find_command_path(self, cmd_name: str) -> Optional[str]:
        """Find path to command in YAML config."""
        if 'forms' not in self.config:
            return None

        for form_idx, form in enumerate(self.config['forms']):
            if 'commands' not in form:
                continue

            for cmd_idx, command in enumerate(form['commands']):
                if command.get('name') == cmd_name:
                    return f"forms[{form_idx}].commands[{cmd_idx}]"

        return None

    def _find_tabular_section_index(self, section_name: str) -> Optional[int]:
        """Find index of tabular section in YAML config."""
        if 'tabular_sections' not in self.config:
            return None

        for idx, section in enumerate(self.config['tabular_sections']):
            if section.get('name') == section_name:
                return idx

        return None

    def _find_tabular_column_path(self, section_name: str, col_name: str) -> Optional[str]:
        """Find path to tabular section column in YAML config."""
        section_idx = self._find_tabular_section_index(section_name)
        if section_idx is None:
            return None

        section = self.config['tabular_sections'][section_idx]
        if 'columns' not in section:
            return None

        for col_idx, column in enumerate(section['columns']):
            if column.get('name') == col_name:
                return f"tabular_sections[{section_idx}].columns[{col_idx}]"

        return None

    def _map_property_to_yaml_field(self, property_name: str) -> str:
        """
        Map XML property name to YAML field name.

        XML properties (Synonym, Title, ToolTip) map to YAML fields (synonym, title, tooltip).
        """
        mapping = {
            'synonym': 'synonym',
            'title': 'title',
            'tooltip': 'tooltip',
            'width': 'width',
            'height': 'height',
        }

        return mapping.get(property_name.lower(), property_name.lower())
