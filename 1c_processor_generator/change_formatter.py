"""
Change Formatter Module (v2.28.0)

Provides flexible formatting for sync tool changes in multiple modes.
Used by both Nested Elements support and Advanced Conflict Resolution.

Supports:
- Simple mode: One-line summary (current behavior)
- Detailed mode: Multi-line with metadata
- Diff mode: Uses DiffVisualizer for visual comparison
- Hierarchy mode: Shows position in nested structure

This is a shared foundation module that prevents code duplication across features.
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class StructuralUpdate:
    """
    Represents a structural change to be applied to YAML config.

    This mirrors the StructuralUpdate from sync_tool.py but is included here
    for type hints and independence.
    """
    operation: str  # 'add' or 'delete'
    element_type: str  # 'attribute', 'form_element', 'command', etc.
    element_name: str
    element_data: Optional[Dict[str, Any]] = None
    form_index: int = 0
    parent_path: Optional[str] = None  # v2.28.0: for nested elements
    insertion_index: Optional[int] = None  # v2.28.0: where to insert
    depth: int = 0  # v2.28.0: nesting depth


class ChangeFormatter:
    """
    Flexible formatter for structural updates and changes.

    Provides multiple formatting modes to support different use cases:
    - Simple: Quick one-line summaries
    - Detailed: Multi-line with all metadata
    - Hierarchical: Shows position in nested structure
    - With references: Includes reference information

    v2.28.0 feature.
    """

    def __init__(self, use_unicode: bool = True):
        """
        Initialize ChangeFormatter.

        Args:
            use_unicode: Use Unicode symbols for better visual display (default: True)
        """
        self.use_unicode = use_unicode

        # Symbols for operations
        if use_unicode:
            self.symbols = {
                'add': '➕',
                'delete': '➖',
                'modify': '🔄',
                'tree': '└─',
                'branch': '├─',
                'indent': '│  ',
                'space': '   '
            }
        else:
            self.symbols = {
                'add': '[+]',
                'delete': '[-]',
                'modify': '[~]',
                'tree': '`-',
                'branch': '+-',
                'indent': '|  ',
                'space': '   '
            }

    def format_change(
        self,
        update: StructuralUpdate,
        mode: str = 'simple',
        config: Optional[Dict[str, Any]] = None,
        references: Optional[List[str]] = None
    ) -> str:
        """
        Format structural update in specified mode.

        Args:
            update: StructuralUpdate to format
            mode: Format mode ('simple', 'detailed', 'hierarchical')
            config: Full YAML config (required for hierarchical mode)
            references: List of references (optional)

        Returns:
            Formatted string representation
        """
        if mode == 'simple':
            return self._format_simple(update)
        elif mode == 'detailed':
            return self._format_detailed(update, references)
        elif mode == 'hierarchical':
            return self._format_hierarchical(update, config, references)
        else:
            logger.warning(f"Unknown format mode: {mode}, using simple")
            return self._format_simple(update)

    def _format_simple(self, update: StructuralUpdate) -> str:
        """
        Format as simple one-line summary.

        This is the current default behavior in sync_tool.py.

        Args:
            update: StructuralUpdate to format

        Returns:
            One-line summary string
        """
        symbol = self.symbols.get(update.operation, '?')
        op = update.operation.upper()
        elem_type = update.element_type.replace('_', ' ')
        name = update.element_name

        return f"{symbol} {op} {elem_type}: {name}"

    def _format_detailed(
        self,
        update: StructuralUpdate,
        references: Optional[List[str]] = None
    ) -> str:
        """
        Format with detailed metadata.

        Shows all available information about the change including
        form index, parent path, insertion index, depth.

        Args:
            update: StructuralUpdate to format
            references: Optional list of reference strings

        Returns:
            Multi-line detailed string
        """
        lines = []

        # Header
        symbol = self.symbols.get(update.operation, '?')
        op = update.operation.upper()
        elem_type = update.element_type.replace('_', ' ')
        lines.append(f"{symbol} {op} {elem_type}: {update.element_name}")

        # Metadata
        metadata = []
        metadata.append(f"  Form: index {update.form_index}")

        if update.parent_path:
            metadata.append(f"  Parent: {update.parent_path}")

        if update.insertion_index is not None:
            metadata.append(f"  Position: index {update.insertion_index}")

        if update.depth > 0:
            metadata.append(f"  Depth: {update.depth} level(s)")

        if update.element_data:
            # Show key fields from element data
            if 'type' in update.element_data:
                metadata.append(f"  Type: {update.element_data['type']}")
            if 'attribute' in update.element_data:
                metadata.append(f"  Attribute: {update.element_data['attribute']}")
            if 'value_table' in update.element_data:
                metadata.append(f"  ValueTable: {update.element_data['value_table']}")

        lines.extend(metadata)

        # References if provided
        if references:
            lines.append(f"  References: {len(references)}")
            for ref in references[:3]:  # Show first 3
                lines.append(f"    - {ref}")
            if len(references) > 3:
                lines.append(f"    ... and {len(references) - 3} more")

        return '\n'.join(lines)

    def _format_hierarchical(
        self,
        update: StructuralUpdate,
        config: Optional[Dict[str, Any]],
        references: Optional[List[str]] = None
    ) -> str:
        """
        Format showing position in hierarchy.

        Displays the change in context of the nested structure, showing
        parent elements and siblings.

        Args:
            update: StructuralUpdate to format
            config: Full YAML config
            references: Optional list of references

        Returns:
            Multi-line hierarchical view
        """
        lines = []

        # Header
        symbol = self.symbols.get(update.operation, '?')
        op = update.operation.upper()
        elem_type = update.element_type.replace('_', ' ')
        lines.append(f"{symbol} {op} {elem_type}: {update.element_name}")

        # Build hierarchy path
        if config and update.parent_path:
            path_parts = self._parse_path(update.parent_path)
            lines.append("\n  Hierarchy:")
            lines.extend(self._format_path_hierarchy(path_parts, config, update))
        elif config:
            # Top-level element
            lines.append(f"\n  Location: Top-level in form {update.form_index}")

        # References
        if references:
            lines.append(f"\n  {self.symbols['modify']} References ({len(references)}):")
            for ref in references[:5]:
                lines.append(f"    - {ref}")
            if len(references) > 5:
                lines.append(f"    ... and {len(references) - 5} more")

        return '\n'.join(lines)

    def format_references(
        self,
        references: List[str],
        max_display: int = 10,
        title: str = "References found"
    ) -> str:
        """
        Format list of references.

        Args:
            references: List of reference strings
            max_display: Maximum number to display before truncating
            title: Title for the list

        Returns:
            Formatted reference list
        """
        if not references:
            return "No references found"

        lines = []
        lines.append(f"{self.symbols['modify']} {title} ({len(references)}):")

        for i, ref in enumerate(references[:max_display]):
            lines.append(f"  {i+1}. {ref}")

        if len(references) > max_display:
            remaining = len(references) - max_display
            lines.append(f"  ... and {remaining} more")

        return '\n'.join(lines)

    def format_summary(
        self,
        updates: List[StructuralUpdate],
        title: str = "Structural Changes Summary"
    ) -> str:
        """
        Format summary of multiple changes.

        Args:
            updates: List of StructuralUpdate objects
            title: Title for the summary

        Returns:
            Formatted summary string
        """
        if not updates:
            return "No structural changes"

        lines = []
        lines.append(f"\n{'=' * 60}")
        lines.append(f"{title}")
        lines.append(f"{'=' * 60}")

        # Count by operation
        add_count = sum(1 for u in updates if u.operation == 'add')
        delete_count = sum(1 for u in updates if u.operation == 'delete')
        modify_count = sum(1 for u in updates if u.operation == 'modify')

        lines.append(f"\nTotal: {len(updates)} change(s)")
        if add_count > 0:
            lines.append(f"  {self.symbols['add']} Add: {add_count}")
        if delete_count > 0:
            lines.append(f"  {self.symbols['delete']} Delete: {delete_count}")
        if modify_count > 0:
            lines.append(f"  {self.symbols['modify']} Modify: {modify_count}")

        # Group by element type
        lines.append("\nBy element type:")
        type_counts = {}
        for update in updates:
            elem_type = update.element_type
            type_counts[elem_type] = type_counts.get(elem_type, 0) + 1

        for elem_type, count in sorted(type_counts.items()):
            lines.append(f"  - {elem_type.replace('_', ' ')}: {count}")

        # List all changes
        lines.append(f"\nChanges:")
        for i, update in enumerate(updates, 1):
            symbol = self.symbols.get(update.operation, '?')
            lines.append(f"  {i}. {symbol} {update.operation.upper()} "
                        f"{update.element_type}: {update.element_name}")

        lines.append(f"{'=' * 60}\n")
        return '\n'.join(lines)

    def _parse_path(self, path: str) -> List[Dict[str, Any]]:
        """
        Parse path string into components.

        Args:
            path: Path string like 'forms[0].elements[2].child_items[1]'

        Returns:
            List of path components with type and index
        """
        components = []
        parts = path.replace('[', '.').replace(']', '').split('.')

        i = 0
        while i < len(parts):
            if not parts[i]:
                i += 1
                continue

            component = {'key': parts[i]}

            # Check if next part is a number (index)
            if i + 1 < len(parts) and parts[i + 1].isdigit():
                component['index'] = int(parts[i + 1])
                i += 2
            else:
                i += 1

            components.append(component)

        return components

    def _format_path_hierarchy(
        self,
        path_parts: List[Dict[str, Any]],
        config: Dict[str, Any],
        update: StructuralUpdate
    ) -> List[str]:
        """
        Format hierarchical path with tree structure.

        Args:
            path_parts: Parsed path components
            config: Full YAML config
            update: Current update being formatted

        Returns:
            List of formatted lines showing tree structure
        """
        lines = []
        current = config
        indent_level = 0

        for i, part in enumerate(path_parts):
            is_last = (i == len(path_parts) - 1)
            symbol = self.symbols['tree'] if is_last else self.symbols['branch']
            indent = self.symbols['indent'] * indent_level

            # Get the key
            key = part['key']
            index = part.get('index')

            # Navigate to current element
            try:
                if index is not None:
                    current = current[key][index]
                    name = current.get('name', f'{key}[{index}]')
                    elem_type = current.get('type', current.get('element_type', key))
                    lines.append(f"  {indent}{symbol} {elem_type}: {name}")
                else:
                    current = current.get(key, {})
                    lines.append(f"  {indent}{symbol} {key}")
            except (KeyError, IndexError, TypeError):
                lines.append(f"  {indent}{symbol} {key}[{index if index is not None else '?'}]")

            indent_level += 1

        # Add the target element being added/deleted
        final_indent = self.symbols['indent'] * indent_level
        symbol = self.symbols.get(update.operation, '?')
        lines.append(f"  {final_indent}{self.symbols['tree']} {symbol} {update.element_name} "
                    f"[{update.operation.upper()}]")

        return lines

    def format_conflict(
        self,
        element_name: str,
        element_type: str,
        reason: str,
        suggestions: Optional[List[str]] = None
    ) -> str:
        """
        Format conflict message with suggestions.

        Args:
            element_name: Name of conflicting element
            element_type: Type of element
            reason: Reason for conflict
            suggestions: Optional list of suggestions to resolve

        Returns:
            Formatted conflict message
        """
        lines = []
        lines.append(f"\n⚠️  CONFLICT: {element_type} '{element_name}'")
        lines.append(f"Reason: {reason}")

        if suggestions:
            lines.append("\nSuggestions:")
            for i, suggestion in enumerate(suggestions, 1):
                lines.append(f"  {i}. {suggestion}")

        return '\n'.join(lines)

    def format_warning(
        self,
        message: str,
        details: Optional[List[str]] = None
    ) -> str:
        """
        Format warning message.

        Args:
            message: Warning message
            details: Optional list of detail strings

        Returns:
            Formatted warning
        """
        lines = []
        lines.append(f"⚠️  WARNING: {message}")

        if details:
            for detail in details:
                lines.append(f"  - {detail}")

        return '\n'.join(lines)

    def format_success(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Format success message.

        Args:
            message: Success message
            details: Optional dict of detail key-value pairs

        Returns:
            Formatted success message
        """
        lines = []
        lines.append(f"✅ {message}")

        if details:
            for key, value in details.items():
                lines.append(f"  {key}: {value}")

        return '\n'.join(lines)
