"""
Centralized ID allocation for form elements.

v2.38.0 Technical Debt Refactoring - Phase 2.1

This module provides a single source of truth for ID management,
replacing the scattered `current_id += ELEMENT_ID_INCREMENTS[...]` patterns
throughout generator.py.

v2.53.0+: ELEMENT_ID_INCREMENTS moved to pro/generation_context.py (.pyd)
"""

from dataclasses import dataclass, field
from typing import Dict, Optional

# v2.53.0+: Critical constants in PRO module (.pyd)
from .pro.generation_context import get_generation_context

# Get element increments from protected context
_gen_ctx = get_generation_context()
ELEMENT_ID_INCREMENTS = _gen_ctx["element_id_increments"]


@dataclass
class IDAllocator:
    """
    Allocates sequential IDs for form elements.

    Each 1C form element requires a unique ID, and some elements
    require additional IDs for sub-elements (ContextMenu, ExtendedTooltip,
    CommandBar). This class centralizes all ID allocation logic.

    Usage:
        allocator = IDAllocator()
        input_id = allocator.allocate("InputField")  # Returns 1, advances to 4
        button_id = allocator.allocate("Button")     # Returns 4, advances to 6

    Element ID Increments:
        - InputField: 3 (Element + ContextMenu + ExtendedTooltip)
        - LabelField: 3
        - Button: 2 (Element + ExtendedTooltip)
        - Table: 4 (Element + ContextMenu + CommandBar + ExtendedTooltip)
        - UsualGroup: 2
        - etc.

    See constants.py ELEMENT_ID_INCREMENTS for full mapping.
    """

    _start_id: int = 1
    _current_id: int = field(default=1, init=False)
    _allocations: Dict[str, int] = field(default_factory=dict, init=False)
    _debug: bool = False

    def __post_init__(self):
        """Initialize current_id from start_id."""
        self._current_id = self._start_id

    def allocate(self, element_type: str, element_name: Optional[str] = None) -> int:
        """
        Allocate ID for element and return it.

        Args:
            element_type: Element type name (must exist in ELEMENT_ID_INCREMENTS)
            element_name: Optional element name for debugging

        Returns:
            Allocated ID for this element

        Example:
            >>> allocator = IDAllocator()
            >>> allocator.allocate("InputField")  # Returns 1
            >>> allocator.allocate("Button")      # Returns 4
            >>> allocator.peek()                  # Returns 6
        """
        allocated_id = self._current_id
        increment = ELEMENT_ID_INCREMENTS.get(element_type, 3)  # Default: 3
        self._current_id += increment

        # Track allocations for debugging
        if self._debug:
            key = f"{element_type}:{element_name or 'unnamed'}@{allocated_id}"
            self._allocations[key] = increment

        return allocated_id

    def allocate_table_column(self, column_name: Optional[str] = None) -> int:
        """
        Convenience method for table columns.

        Args:
            column_name: Optional column name for debugging

        Returns:
            Allocated ID for the column
        """
        return self.allocate("TableColumn", column_name)

    def allocate_page(self, page_name: Optional[str] = None) -> int:
        """
        Convenience method for pages.

        Args:
            page_name: Optional page name for debugging

        Returns:
            Allocated ID for the page
        """
        return self.allocate("Page", page_name)

    def peek(self) -> int:
        """
        Get current ID without incrementing (for lookahead scenarios).

        Returns:
            Current ID value
        """
        return self._current_id

    def skip(self, count: int) -> None:
        """
        Skip N IDs (for special cases).

        Args:
            count: Number of IDs to skip
        """
        self._current_id += count

    def reserve(self, count: int) -> int:
        """
        Reserve a block of IDs and return the starting ID.

        Useful when you need multiple sequential IDs for complex elements.

        Args:
            count: Number of IDs to reserve

        Returns:
            Starting ID of the reserved block
        """
        start_id = self._current_id
        self._current_id += count
        return start_id

    @property
    def current(self) -> int:
        """Current ID value (same as peek())."""
        return self._current_id

    def reset(self, start_id: int = 1) -> None:
        """
        Reset allocator to specific starting ID.

        Args:
            start_id: New starting ID (default: 1)
        """
        self._current_id = start_id
        self._allocations.clear()

    def get_allocations(self) -> Dict[str, int]:
        """
        Get allocation history (only available when debug=True).

        Returns:
            Dictionary of element_key -> increment
        """
        return self._allocations.copy()

    def __repr__(self) -> str:
        return f"IDAllocator(current={self._current_id}, allocations={len(self._allocations)})"


def create_allocator(start_id: int = 1, debug: bool = False) -> IDAllocator:
    """
    Factory function to create IDAllocator.

    Args:
        start_id: Starting ID (default: 1)
        debug: Enable allocation tracking (default: False)

    Returns:
        New IDAllocator instance
    """
    return IDAllocator(_start_id=start_id, _debug=debug)
