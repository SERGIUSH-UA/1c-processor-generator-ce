"""
Base handler interface for sync element types.

Each element type (attribute, form_element, command, template, etc.) implements
this interface to provide consistent sync operations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from lxml import etree


class ChangeType(Enum):
    """Types of changes that can be detected."""
    ADD = "add"
    DELETE = "delete"
    RENAME = "rename"
    PROPERTY_CHANGE = "property_change"
    TYPE_CHANGE = "type_change"


@dataclass
class ElementChange:
    """Represents a single change detected for an element."""
    change_type: ChangeType
    element_type: str  # handler's element_type_name
    xpath: str
    old_value: Any
    new_value: Any
    element_name: Optional[str] = None
    property_name: Optional[str] = None
    # Hierarchy metadata for nested elements
    parent_path: Optional[str] = None
    insertion_index: Optional[int] = None
    depth: int = 0
    parent_name: Optional[str] = None


class BaseElementHandler(ABC):
    """
    Abstract base class for element-specific sync handlers.

    Each handler encapsulates:
    - XML extraction logic
    - Element comparison logic
    - YAML add/delete operations
    - Reference checking for safe deletion

    Subclasses must implement all abstract methods.
    """

    # Common XML namespaces used by 1C
    NAMESPACES = {
        'ns': 'http://v8.1c.ru/8.3/MDClasses',
        'v8': 'http://v8.1c.ru/8.1/data/core',
        'form': 'http://v8.1c.ru/8.3/xcf/logform',
        'xr': 'http://v8.1c.ru/8.3/xcf/readable',
    }

    @property
    @abstractmethod
    def element_type_name(self) -> str:
        """
        Human-readable type name for this handler.

        Examples: 'attribute', 'form_element', 'command', 'template'
        Used as key in registry and for logging.
        """
        pass

    @property
    @abstractmethod
    def yaml_section(self) -> str:
        """
        YAML section path where elements of this type live.

        Examples:
        - 'attributes' for processor attributes
        - 'forms[].elements' for form elements
        - 'forms[].parameters' for form parameters
        - 'templates' for templates
        """
        pass

    @property
    def supports_nesting(self) -> bool:
        """
        Whether this element type supports child elements.

        Override to return True for elements like Group, Table, ColumnGroup
        that can contain other elements.
        """
        return False

    @property
    def is_form_level(self) -> bool:
        """
        Whether this element type lives at form level (vs processor level).

        Form-level elements require form_index for add/delete operations.
        Examples: form_element, command, form_attribute, form_parameter

        Processor-level elements: attribute, tabular_section, template
        """
        return False

    @abstractmethod
    def extract_from_xml(
        self,
        elem: "etree._Element",
        namespaces: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Extract element data from XML element.

        Args:
            elem: lxml Element to extract data from
            namespaces: XML namespaces dict (defaults to self.NAMESPACES)

        Returns:
            Dictionary with element data (name, type, properties, etc.)
            Must include at minimum {'name': str}
        """
        pass

    @abstractmethod
    def get_elements_from_tree(
        self,
        tree: "etree._ElementTree",
        namespaces: Optional[Dict[str, str]] = None,
        form_root: Optional["etree._Element"] = None
    ) -> Dict[str, "etree._Element"]:
        """
        Get all elements of this type from XML tree.

        Args:
            tree: lxml ElementTree (main processor XML)
            namespaces: XML namespaces dict
            form_root: Optional form XML root (for form-level elements)

        Returns:
            Dictionary mapping element names to their XML elements.
            {element_name: etree._Element}
        """
        pass

    @abstractmethod
    def compare_element_details(
        self,
        name: str,
        original: "etree._Element",
        modified: "etree._Element",
        namespaces: Optional[Dict[str, str]] = None
    ) -> List[ElementChange]:
        """
        Compare two elements and return list of property changes.

        This is called for elements that exist in both original and modified.
        Should detect property changes, type changes, etc.

        Args:
            name: Element name
            original: Original XML element
            modified: Modified XML element
            namespaces: XML namespaces dict

        Returns:
            List of ElementChange for each detected change
        """
        pass

    @abstractmethod
    def add_to_yaml(
        self,
        config: Dict,
        data: Dict,
        form_index: int = 0,
        parent_path: Optional[str] = None,
        insertion_index: Optional[int] = None
    ) -> bool:
        """
        Add element to YAML config.

        Args:
            config: YAML config dictionary (modified in place)
            data: Element data dictionary (from extract_from_xml)
            form_index: Form index for form-level elements
            parent_path: Parent element path for nested elements
            insertion_index: Where to insert in parent's children list

        Returns:
            True if added successfully, False otherwise
        """
        pass

    @abstractmethod
    def delete_from_yaml(
        self,
        config: Dict,
        name: str,
        form_index: int = 0,
        parent_path: Optional[str] = None,
        force: bool = False
    ) -> bool:
        """
        Delete element from YAML config.

        Args:
            config: YAML config dictionary (modified in place)
            name: Element name to delete
            form_index: Form index for form-level elements
            parent_path: Parent element path for nested elements
            force: Skip reference checking if True

        Returns:
            True if deleted successfully, False otherwise
        """
        pass

    def check_references(
        self,
        config: Dict,
        bsl_code: str,
        name: str
    ) -> List[str]:
        """
        Check for references to element before deletion.

        Override this method to implement element-specific reference checking.

        Args:
            config: YAML config dictionary
            bsl_code: Combined BSL handler code
            name: Element name to check

        Returns:
            List of reference descriptions (empty if no references found)
        """
        return []

    # ==================== Helper methods ====================

    def get_multilang_text(
        self,
        elem: "etree._Element",
        prop_name: str,
        namespaces: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """
        Extract multilingual text property from XML element.

        Args:
            elem: XML element
            prop_name: Property name (e.g., 'Title', 'Synonym', 'ToolTip')
            namespaces: XML namespaces

        Returns:
            Dictionary with language keys: {'ru': '...', 'uk': '...', 'en': '...'}
        """
        ns = namespaces or self.NAMESPACES
        result = {}

        # Try direct text node first
        prop_elems = elem.xpath(f".//*[local-name()='{prop_name}']")
        if not prop_elems:
            return result

        prop_elem = prop_elems[0]

        # Check for v8:item structure (multilingual)
        items = prop_elem.xpath(".//v8:item", namespaces=ns)
        if items:
            for item in items:
                lang_elem = item.find("v8:lang", namespaces=ns)
                content_elem = item.find("v8:content", namespaces=ns)
                if lang_elem is not None and content_elem is not None:
                    lang = lang_elem.text
                    content = content_elem.text or ""
                    if lang == "ru":
                        result["ru"] = content
                    elif lang == "uk":
                        result["uk"] = content
                    elif lang == "en":
                        result["en"] = content
        else:
            # Single value, assume Russian
            if prop_elem.text:
                result["ru"] = prop_elem.text

        return result

    def get_xpath(self, elem: "etree._Element") -> str:
        """
        Get XPath to element (for logging/debugging).

        Args:
            elem: XML element

        Returns:
            XPath string
        """
        parts = []
        current = elem
        while current is not None:
            parent = current.getparent()
            if parent is not None:
                siblings = [c for c in parent if c.tag == current.tag]
                if len(siblings) > 1:
                    index = siblings.index(current) + 1
                    parts.append(f"{current.tag.split('}')[-1]}[{index}]")
                else:
                    parts.append(current.tag.split('}')[-1])
            else:
                parts.append(current.tag.split('}')[-1])
            current = parent
        return "/" + "/".join(reversed(parts))

    def _create_change(
        self,
        change_type: ChangeType,
        xpath: str,
        old_value: Any,
        new_value: Any,
        element_name: Optional[str] = None,
        property_name: Optional[str] = None,
        **kwargs
    ) -> ElementChange:
        """
        Create an ElementChange with this handler's element type.

        Helper method to reduce boilerplate in subclasses.
        """
        return ElementChange(
            change_type=change_type,
            element_type=self.element_type_name,
            xpath=xpath,
            old_value=old_value,
            new_value=new_value,
            element_name=element_name,
            property_name=property_name,
            **kwargs
        )
