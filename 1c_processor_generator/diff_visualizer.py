"""
Diff Visualizer Module (v2.28.0)

Provides visual diff generation for YAML changes, BSL code changes, and structural updates.
Used by both Nested Elements support and Advanced Conflict Resolution.

This is a shared foundation module that prevents code duplication across features.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from ruamel.yaml import YAML
from io import StringIO

logger = logging.getLogger(__name__)


@dataclass
class DiffLine:
    """Represents a single line in a diff view."""
    line_number: Optional[int]
    content: str
    status: str  # 'unchanged', 'added', 'removed', 'modified'
    context: bool = False  # True if this is context line (not changed)


class DiffVisualizer:
    """
    Visual diff generation for sync tool changes.

    Provides multiple visualization modes:
    - Simple: One-line summary (current behavior)
    - Detailed: Multi-line with context
    - Side-by-side: Two-column comparison
    - BSL-specific: Code diff with line numbers

    v2.28.0 feature.
    """

    def __init__(self, context_lines: int = 3):
        """
        Initialize DiffVisualizer.

        Args:
            context_lines: Number of context lines to show before/after changes (default: 3)
        """
        self.context_lines = context_lines
        self.yaml = YAML()
        self.yaml.preserve_quotes = True
        self.yaml.default_flow_style = False
        # v2.30.0: Explicit comment preservation settings
        self.yaml.map_indent = 2
        self.yaml.sequence_indent = 2
        self.yaml.sequence_dash_offset = 0

    def visualize_yaml_change(
        self,
        element_type: str,
        element_name: str,
        operation: str,
        element_data: Optional[Dict[str, Any]],
        config: Dict[str, Any],
        yaml_path: Optional[str] = None
    ) -> str:
        """
        Visualize YAML structural change with context.

        Args:
            element_type: Type of element (attribute, form_element, value_table, etc.)
            element_name: Name of the element
            operation: Operation type ('add', 'delete', 'modify')
            element_data: Element data for add/modify operations
            config: Full YAML config for context
            yaml_path: Path in YAML tree (e.g., 'forms[0].elements[2]')

        Returns:
            Formatted multi-line diff string
        """
        lines = []
        lines.append(f"\n{'=' * 70}")
        lines.append(f"YAML Change: {operation.upper()} {element_type}")
        lines.append(f"Element: {element_name}")

        if yaml_path:
            lines.append(f"Path: {yaml_path}")

        lines.append(f"{'-' * 70}")

        if operation == "add" and element_data:
            lines.append("\n[+] New element to be added:")
            lines.append(self._format_yaml_snippet(element_data, prefix="  + "))

        elif operation == "delete":
            lines.append("\n[-] Element to be deleted:")
            # Try to find element in config
            element = self._find_element_in_config(config, element_type, element_name)
            if element:
                lines.append(self._format_yaml_snippet(element, prefix="  - "))
            else:
                lines.append(f"  - {element_name}")

        elif operation == "modify" and element_data:
            lines.append("\n[~] Element will be modified:")
            old_element = self._find_element_in_config(config, element_type, element_name)
            if old_element:
                lines.append("\n  Before:")
                lines.append(self._format_yaml_snippet(old_element, prefix="    - "))
                lines.append("\n  After:")
                lines.append(self._format_yaml_snippet(element_data, prefix="    + "))
            else:
                lines.append(self._format_yaml_snippet(element_data, prefix="  ~ "))

        lines.append(f"{'=' * 70}\n")
        return "\n".join(lines)

    def visualize_bsl_change(
        self,
        procedure_name: str,
        old_code: Optional[str],
        new_code: Optional[str],
        operation: str
    ) -> str:
        """
        Visualize BSL code change with line numbers and diff markers.

        Args:
            procedure_name: Name of the BSL procedure
            old_code: Original BSL code (None for add)
            new_code: New BSL code (None for delete)
            operation: Operation type ('add', 'delete', 'modify')

        Returns:
            Formatted BSL diff string with line numbers
        """
        lines = []
        lines.append(f"\n{'=' * 70}")
        lines.append(f"BSL Change: {operation.upper()} procedure")
        lines.append(f"Procedure: {procedure_name}")
        lines.append(f"{'-' * 70}")

        if operation == "add" and new_code:
            lines.append("\n[+] New procedure:")
            lines.extend(self._format_bsl_code(new_code, prefix="  + ", start_line=1))

        elif operation == "delete" and old_code:
            lines.append("\n[-] Procedure to be deleted:")
            lines.extend(self._format_bsl_code(old_code, prefix="  - ", start_line=1))

        elif operation == "modify" and old_code and new_code:
            lines.append("\n[~] Procedure modifications:")
            diff_lines = self._compute_line_diff(old_code, new_code)
            lines.extend(self._format_diff_lines(diff_lines))

        lines.append(f"{'=' * 70}\n")
        return "\n".join(lines)

    def visualize_structural_change(
        self,
        element_type: str,
        element_name: str,
        operation: str,
        parent_path: Optional[str],
        insertion_index: Optional[int],
        config: Dict[str, Any]
    ) -> str:
        """
        Visualize where in the structure an element will be added/removed.

        Shows the hierarchy and insertion point for nested elements.

        Args:
            element_type: Type of element
            element_name: Name of element
            operation: 'add' or 'delete'
            parent_path: Path to parent element (e.g., 'forms[0].elements[2]')
            insertion_index: Index where element will be inserted (for add)
            config: Full YAML config

        Returns:
            Formatted structural view showing hierarchy
        """
        lines = []
        lines.append(f"\n{'=' * 70}")
        lines.append(f"Structural Change: {operation.upper()} {element_type}")
        lines.append(f"Element: {element_name}")

        if parent_path:
            lines.append(f"Parent: {parent_path}")

        if insertion_index is not None:
            lines.append(f"Position: index {insertion_index}")

        lines.append(f"{'-' * 70}")

        # Show hierarchy context
        if parent_path:
            parent = self._get_element_by_path(config, parent_path)
            if parent:
                lines.append("\nContext:")
                lines.extend(self._format_hierarchy(parent, element_name, operation, insertion_index))

        lines.append(f"{'=' * 70}\n")
        return "\n".join(lines)

    def create_side_by_side(
        self,
        left_title: str,
        right_title: str,
        left_content: str,
        right_content: str,
        width: int = 35
    ) -> str:
        """
        Create side-by-side comparison view.

        Args:
            left_title: Title for left column (e.g., "Before")
            right_title: Title for right column (e.g., "After")
            left_content: Content for left column
            right_content: Content for right column
            width: Width of each column (default: 35)

        Returns:
            Formatted side-by-side comparison
        """
        lines = []
        separator = " | "
        total_width = width * 2 + len(separator)

        # Header
        lines.append("=" * total_width)
        header = f"{left_title:<{width}}{separator}{right_title:<{width}}"
        lines.append(header)
        lines.append("=" * total_width)

        # Split content into lines
        left_lines = left_content.split('\n')
        right_lines = right_content.split('\n')
        max_lines = max(len(left_lines), len(right_lines))

        # Pad to same length
        left_lines.extend([''] * (max_lines - len(left_lines)))
        right_lines.extend([''] * (max_lines - len(right_lines)))

        # Format each line
        for left, right in zip(left_lines, right_lines):
            # Truncate if too long
            left_display = left[:width - 3] + "..." if len(left) > width else left
            right_display = right[:width - 3] + "..." if len(right) > width else right

            line = f"{left_display:<{width}}{separator}{right_display:<{width}}"
            lines.append(line)

        lines.append("=" * total_width)
        return "\n".join(lines)

    def _format_yaml_snippet(self, data: Any, prefix: str = "") -> str:
        """Format YAML data as string with optional prefix."""
        stream = StringIO()
        self.yaml.dump(data, stream)
        yaml_str = stream.getvalue()

        if prefix:
            lines = yaml_str.split('\n')
            return '\n'.join(prefix + line for line in lines if line)
        return yaml_str

    def _format_bsl_code(
        self,
        code: str,
        prefix: str = "",
        start_line: int = 1
    ) -> List[str]:
        """
        Format BSL code with line numbers and optional prefix.

        Args:
            code: BSL code string
            prefix: Prefix for each line (e.g., '  + ' for additions)
            start_line: Starting line number

        Returns:
            List of formatted lines
        """
        lines = code.split('\n')
        formatted = []

        for i, line in enumerate(lines, start=start_line):
            line_num = f"{i:4d}"
            formatted.append(f"{prefix}{line_num} | {line}")

        return formatted

    def _compute_line_diff(self, old_code: str, new_code: str) -> List[DiffLine]:
        """
        Compute line-by-line diff between old and new code.

        Simple implementation: Shows all old lines as removed, all new lines as added.
        For v2.28.0, can be enhanced with proper diff algorithm (difflib).

        Args:
            old_code: Original code
            new_code: New code

        Returns:
            List of DiffLine objects
        """
        diff_lines = []
        old_lines = old_code.split('\n')
        new_lines = new_code.split('\n')

        # Simple approach: show all old as removed, all new as added
        for i, line in enumerate(old_lines, start=1):
            diff_lines.append(DiffLine(
                line_number=i,
                content=line,
                status='removed'
            ))

        diff_lines.append(DiffLine(
            line_number=None,
            content="--- Changed to ---",
            status='separator'
        ))

        for i, line in enumerate(new_lines, start=1):
            diff_lines.append(DiffLine(
                line_number=i,
                content=line,
                status='added'
            ))

        return diff_lines

    def _format_diff_lines(self, diff_lines: List[DiffLine]) -> List[str]:
        """Format DiffLine objects into display strings."""
        formatted = []

        for diff_line in diff_lines:
            if diff_line.status == 'separator':
                formatted.append(f"\n  {diff_line.content}\n")
            elif diff_line.status == 'removed':
                line_num = f"{diff_line.line_number:4d}" if diff_line.line_number else "    "
                formatted.append(f"  - {line_num} | {diff_line.content}")
            elif diff_line.status == 'added':
                line_num = f"{diff_line.line_number:4d}" if diff_line.line_number else "    "
                formatted.append(f"  + {line_num} | {diff_line.content}")
            elif diff_line.status == 'unchanged':
                line_num = f"{diff_line.line_number:4d}" if diff_line.line_number else "    "
                formatted.append(f"    {line_num} | {diff_line.content}")

        return formatted

    def _find_element_in_config(
        self,
        config: Dict[str, Any],
        element_type: str,
        element_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Find element in YAML config by type and name.

        Args:
            config: Full YAML config
            element_type: Type of element
            element_name: Name to search for

        Returns:
            Element dict if found, None otherwise
        """
        # Handle different element types
        if element_type == "attribute":
            for attr in config.get('attributes', []):
                if attr.get('name') == element_name:
                    return attr

        elif element_type == "tabular_section":
            for ts in config.get('tabular_sections', []):
                if ts.get('name') == element_name:
                    return ts

        elif element_type in ["form_element", "form"]:
            # Search in forms
            for form in config.get('forms', []):
                if element_type == "form" and form.get('name') == element_name:
                    return form

                # Search in form elements
                for elem in form.get('elements', []):
                    if elem.get('name') == element_name:
                        return elem

        elif element_type == "command":
            for form in config.get('forms', []):
                for cmd in form.get('commands', []):
                    if cmd.get('name') == element_name:
                        return cmd

        elif element_type == "value_table":
            for form in config.get('forms', []):
                for vt in form.get('value_tables', []):
                    if vt.get('name') == element_name:
                        return vt

        elif element_type == "form_attribute":
            for form in config.get('forms', []):
                for fa in form.get('form_attributes', []):
                    if fa.get('name') == element_name:
                        return fa

        return None

    def _get_element_by_path(
        self,
        config: Dict[str, Any],
        path: str
    ) -> Optional[Any]:
        """
        Get element from config by path string.

        Args:
            config: Full YAML config
            path: Path string like 'forms[0].elements[2].child_items[1]'

        Returns:
            Element at path, or None if not found
        """
        try:
            current = config
            parts = path.replace('[', '.').replace(']', '').split('.')

            for part in parts:
                if not part:
                    continue

                if part.isdigit():
                    current = current[int(part)]
                else:
                    current = current.get(part)
                    if current is None:
                        return None

            return current
        except (KeyError, IndexError, TypeError, AttributeError):
            return None

    def _format_hierarchy(
        self,
        parent: Dict[str, Any],
        target_name: str,
        operation: str,
        insertion_index: Optional[int]
    ) -> List[str]:
        """
        Format hierarchical view of elements showing where change happens.

        Args:
            parent: Parent element dict
            target_name: Name of element being added/deleted
            operation: 'add' or 'delete'
            insertion_index: Index for insertion

        Returns:
            List of formatted lines showing hierarchy
        """
        lines = []

        # Show parent info
        parent_name = parent.get('name', 'Unknown')
        parent_type = parent.get('type', parent.get('element_type', 'Unknown'))
        lines.append(f"  Parent: {parent_name} ({parent_type})")

        # Show children if any
        children = parent.get('child_items', parent.get('elements', []))
        if children:
            lines.append(f"  Children ({len(children)}):")

            for idx, child in enumerate(children):
                child_name = child.get('name', 'Unknown')
                marker = ""

                if operation == "add" and insertion_index == idx:
                    lines.append(f"    {idx}. [+] >>> {target_name} will be inserted here <<<")
                    marker = " "

                status = "[-]" if (operation == "delete" and child_name == target_name) else "   "
                lines.append(f"    {marker}{idx}. {status} {child_name}")

            # If inserting at end
            if operation == "add" and insertion_index == len(children):
                lines.append(f"    {len(children)}. [+] >>> {target_name} will be inserted here <<<")
        else:
            lines.append("  Children: (none)")
            if operation == "add":
                lines.append(f"    0. [+] >>> {target_name} will be first child <<<")

        return lines
