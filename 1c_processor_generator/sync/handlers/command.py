"""
Handler for Form Commands.

Commands are form-level actions (buttons, menu items).
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ..base_handler import BaseElementHandler, ChangeType, ElementChange

if TYPE_CHECKING:
    from lxml import etree


class CommandHandler(BaseElementHandler):
    """
    Handler for form command sync operations.

    YAML location: forms[].commands[]
    XML location: Form.xml //form:Commands/form:Command
    """

    @property
    def element_type_name(self) -> str:
        return "command"

    @property
    def yaml_section(self) -> str:
        return "forms[].commands"

    @property
    def is_form_level(self) -> bool:
        return True

    def extract_from_xml(
        self,
        elem: "etree._Element",
        namespaces: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Extract command data from XML."""
        ns = namespaces or self.NAMESPACES
        data: Dict[str, Any] = {}

        # Name
        name = elem.get("name")
        data['name'] = name if name else "UnknownCommand"

        # Title (multilingual)
        title = self.get_multilang_text(elem, "Title", ns)
        if title:
            if 'ru' in title:
                data['title_ru'] = title['ru']
            if 'uk' in title:
                data['title_uk'] = title['uk']
            if 'en' in title:
                data['title_en'] = title['en']

        # Tooltip
        tooltip = self.get_multilang_text(elem, "ToolTip", ns)
        if tooltip:
            if 'ru' in tooltip:
                data['tooltip_ru'] = tooltip['ru']
            if 'uk' in tooltip:
                data['tooltip_uk'] = tooltip['uk']
            if 'en' in tooltip:
                data['tooltip_en'] = tooltip['en']

        # Action
        action_elem = elem.find(".//*[local-name()='Action']")
        if action_elem is not None and action_elem.text:
            data['action'] = action_elem.text

        return data

    def get_elements_from_tree(
        self,
        tree: "etree._ElementTree",
        namespaces: Optional[Dict[str, str]] = None,
        form_root: Optional["etree._Element"] = None
    ) -> Dict[str, "etree._Element"]:
        """Get commands from Form.xml."""
        ns = namespaces or self.NAMESPACES
        commands = {}

        if form_root is None:
            return commands

        for cmd in form_root.xpath(".//form:Commands/form:Command", namespaces=ns):
            name = cmd.get("name")
            if name:
                commands[name] = cmd

        return commands

    def compare_element_details(
        self,
        name: str,
        original: "etree._Element",
        modified: "etree._Element",
        namespaces: Optional[Dict[str, str]] = None
    ) -> List[ElementChange]:
        """Compare two commands."""
        ns = namespaces or self.NAMESPACES
        changes = []

        # Compare title
        orig_title = self.get_multilang_text(original, "Title", ns)
        mod_title = self.get_multilang_text(modified, "Title", ns)
        if orig_title != mod_title:
            changes.append(self._create_change(
                ChangeType.PROPERTY_CHANGE,
                self.get_xpath(modified) + "/Title",
                orig_title,
                mod_title,
                element_name=name,
                property_name="title"
            ))

        # Compare tooltip
        orig_tooltip = self.get_multilang_text(original, "ToolTip", ns)
        mod_tooltip = self.get_multilang_text(modified, "ToolTip", ns)
        if orig_tooltip != mod_tooltip:
            changes.append(self._create_change(
                ChangeType.PROPERTY_CHANGE,
                self.get_xpath(modified) + "/ToolTip",
                orig_tooltip,
                mod_tooltip,
                element_name=name,
                property_name="tooltip"
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
        """Add command to YAML."""
        if 'forms' not in config or form_index >= len(config['forms']):
            return False

        form = config['forms'][form_index]
        if 'commands' not in form:
            form['commands'] = []

        existing_names = [c.get('name') for c in form['commands']]
        if data.get('name') in existing_names:
            return False

        form['commands'].append(data)
        return True

    def delete_from_yaml(
        self,
        config: Dict,
        name: str,
        form_index: int = 0,
        parent_path: Optional[str] = None,
        force: bool = False
    ) -> bool:
        """Delete command from YAML."""
        if 'forms' not in config or form_index >= len(config['forms']):
            return False

        form = config['forms'][form_index]
        if 'commands' not in form:
            return False

        for idx, cmd in enumerate(form['commands']):
            if cmd.get('name') == name:
                del form['commands'][idx]
                return True

        return False

    def check_references(
        self,
        config: Dict,
        bsl_code: str,
        name: str
    ) -> List[str]:
        """Check for references to command in BSL."""
        references = []

        if name in bsl_code:
            references.append(f"BSL code: {name}")

        return references
