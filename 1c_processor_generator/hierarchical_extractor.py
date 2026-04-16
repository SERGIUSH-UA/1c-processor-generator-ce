"""
Hierarchical Extractor Module (v2.28.0)

Provides tree-based XML extraction preserving parent-child relationships.
Solves the flat extraction problem in xml_differ.py for nested elements.

Used by both Nested Elements support and Advanced Conflict Resolution.

Key problem solved:
- xml_differ.py uses `.//form:Item` which flattens ALL descendants
- This loses parent-child relationships needed for nested UsualGroup/Pages
- HierarchicalExtractor preserves full tree structure with depth/index/parent

This is a shared foundation module that prevents code duplication across features.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from lxml import etree

logger = logging.getLogger(__name__)


@dataclass
class ElementNode:
    """
    Represents a form element in a tree structure.

    Preserves hierarchical information lost in flat extraction:
    - Parent reference
    - Children list
    - Depth in tree
    - Index among siblings

    v2.28.0 feature.
    """
    name: str
    element_type: str
    element: etree._Element  # Original XML element
    parent: Optional['ElementNode'] = None
    children: List['ElementNode'] = field(default_factory=list)
    depth: int = 0
    index: int = 0  # Index among siblings at same level
    path: Optional[str] = None  # YAML path like 'forms[0].elements[2].child_items[1]'

    def is_leaf(self) -> bool:
        """Check if this is a leaf node (no children)."""
        return len(self.children) == 0

    def is_root(self) -> bool:
        """Check if this is a root node (no parent)."""
        return self.parent is None

    def get_siblings(self) -> List['ElementNode']:
        """Get list of sibling nodes at same level."""
        if self.parent:
            return self.parent.children
        return []

    def get_ancestors(self) -> List['ElementNode']:
        """Get list of ancestor nodes from root to parent."""
        ancestors = []
        current = self.parent
        while current:
            ancestors.insert(0, current)
            current = current.parent
        return ancestors

    def find_child(self, name: str) -> Optional['ElementNode']:
        """Find direct child by name."""
        for child in self.children:
            if child.name == name:
                return child
        return None


class HierarchicalExtractor:
    """
    Extract form elements from XML preserving tree structure.

    Provides tree-based extraction instead of flat dictionary extraction.
    Preserves parent-child relationships, depth, and sibling order.

    Critical for v2.28.0 nested elements support.
    """

    # XML Namespaces (same as xml_differ.py)
    NAMESPACES = {
        "v8": "http://v8.1c.ru/8.1/data/core",
        "ns": "http://v8.1c.ru/8.3/MDClasses",
        "form": "http://v8.1c.ru/8.3/xcf/logform",
        "xsi": "http://www.w3.org/2001/XMLSchema-instance"
    }

    def __init__(self):
        """Initialize HierarchicalExtractor."""
        pass

    def extract_form_elements_tree(
        self,
        form_root: etree._Element,
        form_index: int = 0
    ) -> List[ElementNode]:
        """
        Extract form elements as tree structure.

        Instead of flat dict like xml_differ._get_form_elements(),
        this returns a list of root ElementNode objects with full tree.

        Args:
            form_root: Root element of form XML
            form_index: Index of this form in YAML config

        Returns:
            List of root ElementNode objects (top-level elements)
        """
        root_elements = []

        # Find ChildItems container (top-level form elements)
        # Use local-name() to ignore namespace - requires xpath(), not find()
        containers = form_root.xpath(".//*[local-name()='ChildItems']")
        child_items_container = containers[0] if containers else None
        if child_items_container is None:
            logger.debug("No ChildItems container found in form")
            return root_elements

        # Process each top-level Item (direct children with various element types)
        # v2.32.1: Elements can be InputField, Button, Table, etc. - not generic "Item"
        for index, item_elem in enumerate(child_items_container):
            node = self._extract_element_recursive(
                item_elem,
                parent_node=None,
                depth=0,
                index=index,
                form_index=form_index,
                parent_path=f"forms[{form_index}].elements"
            )
            if node:
                root_elements.append(node)

        return root_elements

    def _extract_element_recursive(
        self,
        element: etree._Element,
        parent_node: Optional[ElementNode],
        depth: int,
        index: int,
        form_index: int,
        parent_path: str
    ) -> Optional[ElementNode]:
        """
        Recursively extract element and its children.

        Args:
            element: XML element to extract
            parent_node: Parent ElementNode (None for root)
            depth: Current depth in tree
            index: Index among siblings
            form_index: Form index in config
            parent_path: Path to parent in YAML (e.g., 'forms[0].elements')

        Returns:
            ElementNode with full subtree, or None if extraction fails
        """
        # Get element name - it's an XML attribute, not a child element
        # v2.32.1: name is attribute: <InputField name="Field1">
        name = element.get("name")
        if not name:
            logger.debug(f"Element at depth {depth} has no 'name' attribute, skipping")
            return None

        # Get element type
        elem_type = self._get_element_type(element)
        if not elem_type:
            logger.debug(f"Element {name} has no type, skipping")
            return None

        # Build path
        path = f"{parent_path}[{index}]"

        # Create node
        node = ElementNode(
            name=name,
            element_type=elem_type,
            element=element,
            parent=parent_node,
            depth=depth,
            index=index,
            path=path
        )

        # Extract children if this element type supports nesting
        if self._supports_children(elem_type):
            # v2.32.1: Use local-name() for namespace-independent search - requires xpath()
            containers = element.xpath(".//*[local-name()='ChildItems']")
            children_container = containers[0] if containers else None
            if children_container is not None:
                child_index = 0
                # Iterate through all direct children (not by tag name, since they vary)
                for child_elem in children_container:
                    child_node = self._extract_element_recursive(
                        child_elem,
                        parent_node=node,
                        depth=depth + 1,
                        index=child_index,
                        form_index=form_index,
                        parent_path=f"{path}.child_items"
                    )
                    if child_node:
                        node.children.append(child_node)
                        child_index += 1

        return node

    def _get_element_type(self, element: etree._Element) -> Optional[str]:
        """
        Get element type from XML.

        v2.32.1: In Form.xml, type is the element tag name (InputField, Table, Button, etc.)

        Args:
            element: XML element

        Returns:
            Element type string (e.g., 'InputField', 'UsualGroup'), or None
        """
        # v2.32.1: Type is the tag local name (ignoring namespace)
        # <InputField> -> "InputField", <Table> -> "Table", etc.
        tag = element.tag
        if isinstance(tag, str):
            # Remove namespace: "{http://...}InputField" -> "InputField"
            return tag.split('}')[-1] if '}' in tag else tag
        return None

    def _supports_children(self, element_type: str) -> bool:
        """
        Check if element type can have children.

        Args:
            element_type: Element type string

        Returns:
            True if element type supports child_items
        """
        # Element types that can contain children
        container_types = {
            'UsualGroup',
            'CommandBarGroup',
            'Page',
            'Pages',
            'ColumnGroup',
            'FormGroup'
        }
        return element_type in container_types

    def find_element_path(
        self,
        root_elements: List[ElementNode],
        element_name: str
    ) -> Optional[str]:
        """
        Find YAML path to element by name.

        Searches recursively through tree.

        Args:
            root_elements: List of root ElementNode objects
            element_name: Name of element to find

        Returns:
            YAML path string (e.g., 'forms[0].elements[2].child_items[1]'), or None
        """
        for root in root_elements:
            path = self._find_element_path_recursive(root, element_name)
            if path:
                return path
        return None

    def _find_element_path_recursive(
        self,
        node: ElementNode,
        element_name: str
    ) -> Optional[str]:
        """
        Recursively search for element by name.

        Args:
            node: Current node
            element_name: Name to search for

        Returns:
            Path if found, None otherwise
        """
        # Check current node
        if node.name == element_name:
            return node.path

        # Search children
        for child in node.children:
            path = self._find_element_path_recursive(child, element_name)
            if path:
                return path

        return None

    def get_insertion_point(
        self,
        root_elements: List[ElementNode],
        parent_name: Optional[str],
        position: str = 'end'
    ) -> Tuple[Optional[str], int]:
        """
        Determine where to insert new element.

        Args:
            root_elements: List of root ElementNode objects
            parent_name: Name of parent element (None for top-level)
            position: Where to insert ('start', 'end', or numeric index)

        Returns:
            Tuple of (parent_path, insertion_index)
            - parent_path: YAML path to parent's child_items array
            - insertion_index: Index where to insert new element
        """
        if parent_name is None:
            # Top-level insertion
            parent_path = root_elements[0].path.rsplit('[', 1)[0] if root_elements else "forms[0].elements"

            if position == 'start':
                return (parent_path, 0)
            elif position == 'end':
                return (parent_path, len(root_elements))
            elif position.isdigit():
                index = int(position)
                return (parent_path, min(index, len(root_elements)))
            else:
                return (parent_path, len(root_elements))

        # Find parent node
        parent_node = self._find_node_by_name(root_elements, parent_name)
        if not parent_node:
            logger.warning(f"Parent element '{parent_name}' not found")
            return (None, 0)

        # Check if parent can have children
        if not self._supports_children(parent_node.element_type):
            logger.warning(f"Parent element '{parent_name}' of type '{parent_node.element_type}' cannot have children")
            return (None, 0)

        # Build path to parent's child_items
        parent_path = f"{parent_node.path}.child_items"

        # Determine index
        if position == 'start':
            return (parent_path, 0)
        elif position == 'end':
            return (parent_path, len(parent_node.children))
        elif position.isdigit():
            index = int(position)
            return (parent_path, min(index, len(parent_node.children)))
        else:
            return (parent_path, len(parent_node.children))

    def _find_node_by_name(
        self,
        root_elements: List[ElementNode],
        name: str
    ) -> Optional[ElementNode]:
        """
        Find node by name in tree.

        Args:
            root_elements: List of root nodes
            name: Name to search for

        Returns:
            ElementNode if found, None otherwise
        """
        for root in root_elements:
            node = self._find_node_by_name_recursive(root, name)
            if node:
                return node
        return None

    def _find_node_by_name_recursive(
        self,
        node: ElementNode,
        name: str
    ) -> Optional[ElementNode]:
        """
        Recursively search for node by name.

        Args:
            node: Current node
            name: Name to search for

        Returns:
            ElementNode if found, None otherwise
        """
        if node.name == name:
            return node

        for child in node.children:
            found = self._find_node_by_name_recursive(child, name)
            if found:
                return found

        return None

    def flatten_tree(
        self,
        root_elements: List[ElementNode]
    ) -> Dict[str, ElementNode]:
        """
        Convert tree structure to flat dict (for compatibility).

        Creates a flat dict like xml_differ._get_form_elements() but
        with ElementNode objects containing hierarchy info.

        Args:
            root_elements: List of root ElementNode objects

        Returns:
            Dict mapping element name to ElementNode
        """
        flat_dict = {}

        for root in root_elements:
            self._flatten_recursive(root, flat_dict)

        return flat_dict

    def _flatten_recursive(
        self,
        node: ElementNode,
        flat_dict: Dict[str, ElementNode]
    ):
        """
        Recursively add nodes to flat dict.

        Args:
            node: Current node
            flat_dict: Dict to populate
        """
        flat_dict[node.name] = node

        for child in node.children:
            self._flatten_recursive(child, flat_dict)

    def compare_trees(
        self,
        original_roots: List[ElementNode],
        modified_roots: List[ElementNode]
    ) -> Dict[str, Any]:
        """
        Compare two element trees and detect changes.

        Detects:
        - Added elements (in modified, not in original)
        - Deleted elements (in original, not in modified)
        - Moved elements (different parent or index)
        - Modified elements (same location, different attributes)

        Args:
            original_roots: Original tree roots
            modified_roots: Modified tree roots

        Returns:
            Dict with 'added', 'deleted', 'moved', 'modified' lists
        """
        changes = {
            'added': [],
            'deleted': [],
            'moved': [],
            'modified': []
        }

        # Flatten both trees
        original_flat = self.flatten_tree(original_roots)
        modified_flat = self.flatten_tree(modified_roots)

        # Find added and deleted
        original_names = set(original_flat.keys())
        modified_names = set(modified_flat.keys())

        added_names = modified_names - original_names
        deleted_names = original_names - modified_names
        common_names = original_names & modified_names

        # Process added
        for name in added_names:
            node = modified_flat[name]
            changes['added'].append({
                'name': name,
                'type': node.element_type,
                'path': node.path,
                'depth': node.depth,
                'parent': node.parent.name if node.parent else None
            })

        # Process deleted
        for name in deleted_names:
            node = original_flat[name]
            changes['deleted'].append({
                'name': name,
                'type': node.element_type,
                'path': node.path,
                'depth': node.depth,
                'parent': node.parent.name if node.parent else None
            })

        # Process common elements (check for moves or modifications)
        for name in common_names:
            orig_node = original_flat[name]
            mod_node = modified_flat[name]

            # Check if moved (different parent or index)
            orig_parent = orig_node.parent.name if orig_node.parent else None
            mod_parent = mod_node.parent.name if mod_node.parent else None

            if orig_parent != mod_parent or orig_node.index != mod_node.index:
                changes['moved'].append({
                    'name': name,
                    'type': mod_node.element_type,
                    'from_path': orig_node.path,
                    'to_path': mod_node.path,
                    'from_parent': orig_parent,
                    'to_parent': mod_parent,
                    'from_index': orig_node.index,
                    'to_index': mod_node.index
                })

            # Check if modified (different attributes - simplified check)
            # Full implementation would compare all XML attributes
            if orig_node.element_type != mod_node.element_type:
                changes['modified'].append({
                    'name': name,
                    'path': mod_node.path,
                    'changes': {
                        'type': {
                            'old': orig_node.element_type,
                            'new': mod_node.element_type
                        }
                    }
                })

        return changes

    def print_tree(
        self,
        root_elements: List[ElementNode],
        indent: str = "",
        show_path: bool = False
    ) -> str:
        """
        Format tree structure as string for debugging.

        Args:
            root_elements: List of root nodes
            indent: Current indentation
            show_path: Include YAML path in output

        Returns:
            Formatted tree string
        """
        lines = []

        for i, root in enumerate(root_elements):
            lines.extend(self._print_node(root, indent, i == len(root_elements) - 1, show_path))

        return '\n'.join(lines)

    def _print_node(
        self,
        node: ElementNode,
        indent: str,
        is_last: bool,
        show_path: bool
    ) -> List[str]:
        """
        Format single node and children.

        Args:
            node: Node to format
            indent: Current indentation
            is_last: Is this the last sibling?
            show_path: Include path?

        Returns:
            List of formatted lines
        """
        lines = []

        # Format current node
        marker = "└─" if is_last else "├─"
        path_str = f" [{node.path}]" if show_path else ""
        lines.append(f"{indent}{marker} {node.name} ({node.element_type}){path_str}")

        # Format children
        child_indent = indent + ("   " if is_last else "│  ")
        for i, child in enumerate(node.children):
            child_is_last = (i == len(node.children) - 1)
            lines.extend(self._print_node(child, child_indent, child_is_last, show_path))

        return lines
