"""
Element Preparer - wrapper module.

v2.55.0 - Actual implementation moved to pro/element_preparer_impl.py
"""

from typing import List, Dict, Tuple
from .id_allocator import IDAllocator
from .pro.element_preparer_impl import ElementPreparerImpl


class ElementPreparer:
    """
    Element preparation for form generation.

    Wrapper class that delegates to protected implementation.
    """

    def __init__(self, processor):
        """Initialize ElementPreparer."""
        self._impl = ElementPreparerImpl(processor, IDAllocator)
        self._processor = processor

    @property
    def processor(self):
        """Processor object (backward compatibility)."""
        return self._processor

    def prepare_form_elements(self, form) -> Tuple[List[Dict], int]:
        """Prepare all form elements."""
        return self._impl.prepare_form_elements(form)

    def prepare_auto_command_bar(self, form, start_id: int) -> Tuple[List[Dict], int]:
        """Prepare AutoCommandBar elements."""
        return self._impl.prepare_auto_command_bar(form, start_id)

    def _set_table_context(self, element, tabular_section: str, is_value_table: bool):
        """Set table context (internal, for testing)."""
        return self._impl._set_table_context(element, tabular_section, is_value_table)

    def _prepare_popup(self, elem, allocator):
        """Prepare popup element (internal, used by generator)."""
        return self._impl._prepare_popup(elem, allocator)
