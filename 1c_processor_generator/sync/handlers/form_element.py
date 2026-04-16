"""
Handler for Form Elements.

Form elements are UI components: InputField, Button, Table, Group, etc.
They live at form level and can be nested.

v2.42.0+: Enhanced property mapping support.
"""

from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from ..base_handler import BaseElementHandler, ChangeType, ElementChange

if TYPE_CHECKING:
    from lxml import etree


# Property extraction specifications
# (xml_tag, yaml_key, value_type)
# value_type: 'int', 'bool', 'str', 'enum'
SIMPLE_PROPERTIES = [
    ("Width", "width", "int"),
    ("Height", "height", "int"),
    ("ReadOnly", "read_only", "bool"),
    ("HorizontalStretch", "horizontal_stretch", "bool"),
    ("VerticalStretch", "vertical_stretch", "bool"),
    ("HorizontalAlign", "horizontal_align", "enum"),
    ("VerticalAlign", "vertical_align", "enum"),
    ("TitleLocation", "title_location", "enum"),
    ("Hyperlink", "hyperlink", "bool"),
    # InputField specific
    ("ChoiceMode", "choice_mode", "enum"),
    ("QuickChoice", "quick_choice", "enum"),
    ("ChoiceHistoryOnInput", "choice_history_on_input", "enum"),
    ("MultiLine", "multiline", "bool"),
    ("PasswordMode", "password_mode", "bool"),
    ("TextEdit", "text_edit", "bool"),
    ("AutoMaxWidth", "auto_max_width", "int"),
    ("AutoMaxHeight", "auto_max_height", "int"),
    # Group specific
    ("Grouping", "group_direction", "enum"),
    ("Group", "group_direction", "enum"),  # Alternative tag
    ("Representation", "representation", "enum"),
    ("ShowTitle", "show_title", "bool"),
    ("Behavior", "behavior", "enum"),
    # Table specific
    ("RowPictureDataPath", "row_picture_data_path", "str"),
    # PictureDecoration / PictureField specific
    ("Picture", "picture", "str"),
    ("PictureSize", "picture_size", "enum"),
    ("Zoomable", "zoomable", "bool"),
    # ColumnGroup specific
    ("ShowInHeader", "show_in_header", "bool"),
]


class FormElementHandler(BaseElementHandler):
    """
    Handler for form element sync operations.

    YAML location: forms[].elements[]
    XML location: Form.xml //form:ChildItems//*

    v2.42.0+: Full property mapping support including:
    - Alignment (horizontal_align, vertical_align)
    - Font properties (font.bold, font.size, etc.)
    - Choice properties (choice_mode, quick_choice)
    - Visual properties (picture, picture_size, zoomable)
    """

    @property
    def element_type_name(self) -> str:
        return "form_element"

    @property
    def yaml_section(self) -> str:
        return "forms[].elements"

    @property
    def supports_nesting(self) -> bool:
        return True  # Groups, Tables can have children

    @property
    def is_form_level(self) -> bool:
        return True

    def extract_from_xml(
        self,
        elem: "etree._Element",
        namespaces: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Extract form element data from XML."""
        ns = namespaces or self.NAMESPACES
        data: Dict[str, Any] = {}

        # Name
        name = elem.get("name")
        data['name'] = name if name else "UnknownElement"

        # Type from tag
        tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
        data['type'] = self._tag_to_type(tag)

        # Title (multilingual)
        title = self.get_multilang_text(elem, "Title", ns)
        if title:
            if 'ru' in title:
                data['title_ru'] = title['ru']
            if 'uk' in title:
                data['title_uk'] = title['uk']
            if 'en' in title:
                data['title_en'] = title['en']

        # Tooltip (multilingual)
        tooltip = self.get_multilang_text(elem, "ToolTip", ns)
        if tooltip:
            if 'ru' in tooltip:
                data['tooltip_ru'] = tooltip['ru']
            if 'uk' in tooltip:
                data['tooltip_uk'] = tooltip['uk']
            if 'en' in tooltip:
                data['tooltip_en'] = tooltip['en']

        # InputHint (multilingual, v2.36.0+)
        input_hint = self.get_multilang_text(elem, "InputHint", ns)
        if input_hint:
            if 'ru' in input_hint:
                data['input_hint_ru'] = input_hint['ru']
            if 'uk' in input_hint:
                data['input_hint_uk'] = input_hint['uk']
            if 'en' in input_hint:
                data['input_hint_en'] = input_hint['en']

        # DataPath (for attribute binding)
        data_path_elem = elem.find(".//*[local-name()='DataPath']")
        if data_path_elem is not None and data_path_elem.text:
            path = data_path_elem.text
            # Extract attribute name from "Объект.AttributeName"
            if '.' in path:
                data['attribute'] = path.split('.')[-1]

        # Extract all simple properties
        for xml_tag, yaml_key, value_type in SIMPLE_PROPERTIES:
            value = self._get_property(elem, xml_tag, value_type)
            if value is not None:
                data[yaml_key] = value

        # Font (v2.35.1+ LabelDecoration support)
        font_data = self._extract_font(elem, ns)
        if font_data:
            data['font'] = font_data

        return data

    def get_elements_from_tree(
        self,
        tree: "etree._ElementTree",
        namespaces: Optional[Dict[str, str]] = None,
        form_root: Optional["etree._Element"] = None
    ) -> Dict[str, "etree._Element"]:
        """Get form elements from Form.xml."""
        ns = namespaces or self.NAMESPACES
        elements = {}

        if form_root is None:
            return elements

        # Get all named elements
        for elem in form_root.xpath(".//*[@name]", namespaces=ns):
            name = elem.get("name")
            if name:
                elements[name] = elem

        return elements

    def compare_element_details(
        self,
        name: str,
        original: "etree._Element",
        modified: "etree._Element",
        namespaces: Optional[Dict[str, str]] = None
    ) -> List[ElementChange]:
        """Compare two form elements (v2.42.0+ full property support)."""
        ns = namespaces or self.NAMESPACES
        changes = []

        # Compare multilingual properties
        for prop_name in ("Title", "ToolTip", "InputHint"):
            orig_val = self.get_multilang_text(original, prop_name, ns)
            mod_val = self.get_multilang_text(modified, prop_name, ns)
            if orig_val != mod_val:
                changes.append(self._create_change(
                    ChangeType.PROPERTY_CHANGE,
                    self.get_xpath(modified) + f"/{prop_name}",
                    orig_val,
                    mod_val,
                    element_name=name,
                    property_name=prop_name.lower()
                ))

        # Compare all simple properties
        for xml_tag, yaml_key, value_type in SIMPLE_PROPERTIES:
            orig_val = self._get_property(original, xml_tag, value_type)
            mod_val = self._get_property(modified, xml_tag, value_type)
            if orig_val != mod_val:
                changes.append(self._create_change(
                    ChangeType.PROPERTY_CHANGE,
                    self.get_xpath(modified) + f"/{xml_tag}",
                    orig_val,
                    mod_val,
                    element_name=name,
                    property_name=yaml_key
                ))

        # Compare font (v2.35.1+)
        orig_font = self._extract_font(original, ns)
        mod_font = self._extract_font(modified, ns)
        if orig_font != mod_font:
            changes.append(self._create_change(
                ChangeType.PROPERTY_CHANGE,
                self.get_xpath(modified) + "/Font",
                orig_font,
                mod_font,
                element_name=name,
                property_name="font"
            ))

        return changes

    def add_to_yaml(
        self,
        config: Dict,
        data: Dict,
        form_index: int = 0,
        parent_path: Optional[str] = None,
        insertion_index: Optional[int] = None
    ) -> bool:
        """Add form element to YAML."""
        if 'forms' not in config or form_index >= len(config['forms']):
            return False

        form = config['forms'][form_index]
        if 'elements' not in form:
            form['elements'] = []

        # Check for duplicate
        existing_names = [e.get('name') for e in form['elements']]
        if data.get('name') in existing_names:
            return False

        # Add at position or end
        if insertion_index is not None and 0 <= insertion_index <= len(form['elements']):
            form['elements'].insert(insertion_index, data)
        else:
            form['elements'].append(data)

        return True

    def delete_from_yaml(
        self,
        config: Dict,
        name: str,
        form_index: int = 0,
        parent_path: Optional[str] = None,
        force: bool = False
    ) -> bool:
        """Delete form element from YAML."""
        if 'forms' not in config or form_index >= len(config['forms']):
            return False

        form = config['forms'][form_index]
        if 'elements' not in form:
            return False

        for idx, elem in enumerate(form['elements']):
            if elem.get('name') == name:
                del form['elements'][idx]
                return True

        return False

    def check_references(
        self,
        config: Dict,
        bsl_code: str,
        name: str
    ) -> List[str]:
        """Check for references to form element in BSL."""
        references = []

        patterns = [
            f"Элементы.{name}",
            f"Items.{name}",
            f'"{name}"',
            f"'{name}'"
        ]

        for pattern in patterns:
            if pattern in bsl_code:
                references.append(f"BSL code: {pattern}")

        return references

    # ==================== Private helpers ====================

    def _tag_to_type(self, tag: str) -> str:
        """Convert XML tag to YAML element type."""
        tag_map = {
            'InputField': 'InputField',
            'Button': 'Button',
            'Table': 'Table',
            'UsualGroup': 'Group',
            'LabelDecoration': 'LabelDecoration',
            'LabelField': 'LabelField',
            'CheckBoxField': 'CheckBoxField',
            'RadioButtonField': 'RadioButtonField',
            'PictureField': 'PictureField',
            'HTMLDocumentField': 'HTMLDocumentField',
            'SpreadsheetDocumentField': 'SpreadsheetDocumentField',
            'ButtonGroup': 'ButtonGroup',
            'ColumnGroup': 'ColumnGroup',
        }
        return tag_map.get(tag, tag)

    def _get_int_prop(self, elem: "etree._Element", prop: str) -> Optional[int]:
        """Get integer property value."""
        prop_elem = elem.find(f".//*[local-name()='{prop}']")
        if prop_elem is not None and prop_elem.text:
            try:
                return int(prop_elem.text)
            except ValueError:
                pass
        return None

    def _get_property(
        self,
        elem: "etree._Element",
        xml_tag: str,
        value_type: str
    ) -> Optional[Any]:
        """
        Get property value from XML element by tag and type.

        Args:
            elem: XML element
            xml_tag: XML tag name to find
            value_type: 'int', 'bool', 'str', 'enum'

        Returns:
            Extracted value or None
        """
        # Try xpath with local-name() for namespace-agnostic search
        try:
            results = elem.xpath(f".//*[local-name()='{xml_tag}']")
            prop_elem = results[0] if results else None
        except Exception:
            # Fallback to direct find
            prop_elem = elem.find(f".//{xml_tag}")
            if prop_elem is None:
                prop_elem = elem.find(xml_tag)

        if prop_elem is None or prop_elem.text is None:
            return None

        text = prop_elem.text.strip()

        if value_type == 'int':
            try:
                return int(text)
            except ValueError:
                return None
        elif value_type == 'bool':
            return text.lower() == 'true'
        elif value_type in ('str', 'enum'):
            return text if text else None

        return text

    def _extract_font(
        self,
        elem: "etree._Element",
        ns: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        """
        Extract font properties from XML element.

        v2.35.1+: LabelDecoration font support.

        Font structure in XML:
            <Font xmlns="..." faceName="..." height="..." bold="true"/>

        Returns:
            Dict with font properties or None if no font found.
            Example: {'bold': True, 'size': 12, 'color': 'Red'}
        """
        # Try xpath with local-name() for namespace-agnostic search
        try:
            results = elem.xpath(".//*[local-name()='Font']")
            font_elem = results[0] if results else None
        except Exception:
            # Fallback to direct find
            font_elem = elem.find(".//Font")
            if font_elem is None:
                font_elem = elem.find("Font")
        if font_elem is None:
            return None

        font_data: Dict[str, Any] = {}

        # Bold
        bold_attr = font_elem.get('bold')
        if bold_attr and bold_attr.lower() == 'true':
            font_data['bold'] = True

        # Italic
        italic_attr = font_elem.get('italic')
        if italic_attr and italic_attr.lower() == 'true':
            font_data['italic'] = True

        # Size (height in XML)
        height_attr = font_elem.get('height')
        if height_attr:
            try:
                font_data['size'] = int(height_attr)
            except ValueError:
                pass

        # FaceName (font family)
        face_attr = font_elem.get('faceName')
        if face_attr:
            font_data['face_name'] = face_attr

        # Scale
        scale_attr = font_elem.get('scale')
        if scale_attr:
            try:
                font_data['scale'] = int(scale_attr)
            except ValueError:
                pass

        return font_data if font_data else None
