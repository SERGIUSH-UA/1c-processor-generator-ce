"""
Handler for Templates (Макети).

Templates are processor-level assets: HTMLDocument, SpreadsheetDocument.
v2.40.0+ feature.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ..base_handler import BaseElementHandler, ChangeType, ElementChange

if TYPE_CHECKING:
    from lxml import etree


class TemplateHandler(BaseElementHandler):
    """
    Handler for Template sync operations.

    YAML location: templates[]
    XML location: //ns:Template (references) and Templates/*/Ext/Template.xml

    Templates are processor-level objects containing:
    - HTMLDocument - HTML content for rich displays
    - SpreadsheetDocument - Excel-like tables/reports
    """

    @property
    def element_type_name(self) -> str:
        return "template"

    @property
    def yaml_section(self) -> str:
        return "templates"

    @property
    def is_form_level(self) -> bool:
        return False  # Processor-level

    def extract_from_xml(
        self,
        elem: "etree._Element",
        namespaces: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Extract template data from XML."""
        ns = namespaces or self.NAMESPACES
        data: Dict[str, Any] = {}

        # Name from Properties
        name_elem = elem.find(".//ns:Properties/ns:Name", namespaces=ns)
        if name_elem is not None and name_elem.text:
            data['name'] = name_elem.text
        else:
            # Try attribute
            name = elem.get("name")
            data['name'] = name if name else "UnknownTemplate"

        # TemplateType (HTMLDocument, SpreadsheetDocument, etc.)
        type_elem = elem.find(".//ns:Properties/ns:TemplateType", namespaces=ns)
        if type_elem is not None and type_elem.text:
            data['type'] = type_elem.text

        # Synonym (multilingual)
        synonym = self.get_multilang_text(elem, "Synonym", ns)
        if synonym:
            if 'ru' in synonym:
                data['synonym_ru'] = synonym['ru']
            if 'uk' in synonym:
                data['synonym_uk'] = synonym['uk']
            if 'en' in synonym:
                data['synonym_en'] = synonym['en']

        return data

    def get_elements_from_tree(
        self,
        tree: "etree._ElementTree",
        namespaces: Optional[Dict[str, str]] = None,
        form_root: Optional["etree._Element"] = None
    ) -> Dict[str, "etree._Element"]:
        """Get templates from processor XML."""
        ns = namespaces or self.NAMESPACES
        templates = {}

        # Templates are listed in ChildObjects section
        for tmpl in tree.xpath("//ns:Template", namespaces=ns):
            # Get name from Properties
            name_elem = tmpl.find(".//ns:Properties/ns:Name", namespaces=ns)
            if name_elem is not None and name_elem.text:
                templates[name_elem.text] = tmpl
            else:
                # Try ns:Name directly (reference format)
                name_elem = tmpl.find("ns:Name", namespaces=ns)
                if name_elem is not None and name_elem.text:
                    templates[name_elem.text] = tmpl

        return templates

    def compare_element_details(
        self,
        name: str,
        original: "etree._Element",
        modified: "etree._Element",
        namespaces: Optional[Dict[str, str]] = None
    ) -> List[ElementChange]:
        """Compare two templates."""
        ns = namespaces or self.NAMESPACES
        changes = []

        # Compare template type
        orig_type = self._get_template_type(original, ns)
        mod_type = self._get_template_type(modified, ns)
        if orig_type != mod_type:
            changes.append(self._create_change(
                ChangeType.TYPE_CHANGE,
                self.get_xpath(modified) + "/TemplateType",
                orig_type,
                mod_type,
                element_name=name
            ))

        # Compare synonym
        orig_synonym = self.get_multilang_text(original, "Synonym", ns)
        mod_synonym = self.get_multilang_text(modified, "Synonym", ns)
        if orig_synonym != mod_synonym:
            changes.append(self._create_change(
                ChangeType.PROPERTY_CHANGE,
                self.get_xpath(modified) + "/Synonym",
                orig_synonym,
                mod_synonym,
                element_name=name,
                property_name="synonym"
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
        """Add template to YAML."""
        if 'templates' not in config:
            config['templates'] = []

        # Check for duplicate
        existing_names = [t.get('name') for t in config['templates']]
        if data.get('name') in existing_names:
            return False

        # Convert type to lowercase for YAML convention
        if 'type' in data:
            data['type'] = data['type']  # Keep as-is (HTMLDocument, SpreadsheetDocument)

        # Add at position or end
        if insertion_index is not None and 0 <= insertion_index <= len(config['templates']):
            config['templates'].insert(insertion_index, data)
        else:
            config['templates'].append(data)

        return True

    def delete_from_yaml(
        self,
        config: Dict,
        name: str,
        form_index: int = 0,
        parent_path: Optional[str] = None,
        force: bool = False
    ) -> bool:
        """Delete template from YAML."""
        if 'templates' not in config:
            return False

        for idx, tmpl in enumerate(config['templates']):
            if tmpl.get('name') == name:
                del config['templates'][idx]
                return True

        return False

    def check_references(
        self,
        config: Dict,
        bsl_code: str,
        name: str
    ) -> List[str]:
        """Check for references to template in BSL and form elements."""
        references = []

        # Check BSL code for template usage
        patterns = [
            f'ПолучитьМакет("{name}")',
            f"ПолучитьМакет('{name}')",
            f'GetTemplate("{name}")',
            f"GetTemplate('{name}')",
            f'GetForm("{name}")',  # Sometimes used for template access
            f'"{name}"',  # Generic string reference
        ]

        for pattern in patterns:
            if pattern in bsl_code:
                references.append(f"BSL code: {pattern}")

        # Check if template has auto_field (creates form element dependency)
        if 'templates' in config:
            for tmpl in config['templates']:
                if tmpl.get('name') == name and tmpl.get('auto_field'):
                    field_name = tmpl.get('field_name', f'{name}Field')
                    references.append(
                        f"Auto-generated form element: {field_name} "
                        f"(auto_field=true)"
                    )

        # Check form elements for HTMLDocumentField referencing this template
        if 'forms' in config:
            for form_idx, form in enumerate(config['forms']):
                if 'elements' not in form:
                    continue

                for elem_idx, element in enumerate(form['elements']):
                    # Check if any element references this template
                    if element.get('template') == name:
                        references.append(
                            f"Form element: forms[{form_idx}].elements[{elem_idx}] "
                            f"(name={element.get('name')}) references template"
                        )

        return references

    # ==================== Private helpers ====================

    def _get_template_type(
        self,
        elem: "etree._Element",
        ns: Dict[str, str]
    ) -> Optional[str]:
        """Get template type from XML element."""
        type_elem = elem.find(".//ns:Properties/ns:TemplateType", namespaces=ns)
        if type_elem is not None and type_elem.text:
            return type_elem.text
        return None
