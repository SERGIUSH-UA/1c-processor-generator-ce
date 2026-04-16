"""
Element Preparer Implementation - protected module.

v2.55.0 - Critical logic protection

This module contains the actual element preparation logic.
Compiled to .pyd to protect know-how from LLM analysis.
"""

from typing import List, Dict, Tuple, Any, Optional


class ElementPreparerImpl:
    """
    Implementation of element preparation logic.

    Protected from reverse engineering via Cython compilation.
    """

    def __init__(self, processor, id_allocator_class):
        """
        Initialize with processor and IDAllocator class.

        Args:
            processor: Processor object
            id_allocator_class: IDAllocator class for ID allocation
        """
        self.processor = processor
        self._IDAllocator = id_allocator_class

    def _detect_is_value_table(self, table_elem, form) -> bool:
        """Auto-detect if table references ValueTable."""
        explicit_value = table_elem.properties.get("is_value_table")
        if explicit_value is not None:
            return explicit_value

        ts_name = table_elem.tabular_section
        if ts_name and form.value_table_attributes:
            return any(vt.name == ts_name for vt in form.value_table_attributes)

        return False

    def _detect_is_value_tree(self, table_elem, form) -> bool:
        """Auto-detect if table references ValueTree (v2.64.0+)."""
        # Check explicit representation property first
        representation = table_elem.properties.get("representation")
        if representation == "tree":
            return True

        ts_name = table_elem.tabular_section
        if ts_name and form.value_tree_attributes:
            return any(vt.name == ts_name for vt in form.value_tree_attributes)

        return False

    def prepare_form_elements(self, form) -> Tuple[List[Dict], int]:
        """Prepare all form elements with automatic ID numbering."""
        form_elements = []
        allocator = self._IDAllocator()

        for elem in form.elements:
            if elem.element_type == "Popup":
                elem_data = self._prepare_popup(elem, allocator)
            elif elem.element_type == "Pages":
                elem_data = self._prepare_pages(elem, allocator, form)
            else:
                elem_data = self._prepare_element(elem, allocator, form)

            form_elements.append(elem_data)

        return form_elements, allocator.current

    def _prepare_element(self, element, allocator, form) -> Dict:
        """Recursive processing of single FormElement."""
        # v2.74.0: Support nested Pages (Pages inside Page)
        if element.element_type == "Pages":
            return self._prepare_pages(element, allocator, form)

        elem_id = allocator.allocate(element.element_type, element.name)

        elem_data = {
            "type": element.element_type,
            "name": element.name,
            "id": elem_id,
            "properties": element.properties,
            "events": element.event_handlers,
            # v2.67.0+ ConditionalAppearance support
            "conditional_appearances": getattr(element, "conditional_appearances", []),
        }

        handler = self._get_type_handler(element.element_type)
        if handler:
            handler(element, elem_data, allocator, form)

        return elem_data

    def _get_type_handler(self, element_type: str):
        """Get handler for specific element type."""
        handlers = {
            "InputField": self._handle_input_field,
            "LabelField": self._handle_input_field,
            "RadioButtonField": self._handle_input_field,
            "CheckBoxField": self._handle_input_field,
            "SpreadSheetDocumentField": self._handle_input_field,
            "HTMLDocumentField": self._handle_input_field,
            "CalendarField": self._handle_input_field,
            "ChartField": self._handle_input_field,
            "PlannerField": self._handle_input_field,
            "Button": self._handle_button,
            "Table": self._handle_table,
            "ButtonGroup": self._handle_button_group,
            "UsualGroup": self._handle_usual_group,
            "ColumnGroup": self._handle_column_group,
        }
        return handlers.get(element_type)

    def _handle_input_field(self, element, elem_data: Dict, allocator, form):
        """Handle input fields."""
        elem_data["attribute"] = element.attribute

        is_form_attribute = any(
            fa.name == element.attribute for fa in form.form_attributes
        )
        elem_data["is_form_attribute"] = is_form_attribute

    def _handle_button(self, element, elem_data: Dict, allocator, form):
        """Handle buttons."""
        elem_data["command"] = element.command

    def _handle_button_group(self, element, elem_data: Dict, allocator, form):
        """Handle button groups."""
        child_items = []
        if element.child_items:
            for child_elem in element.child_items:
                child_data = self._prepare_element(child_elem, allocator, form)
                child_items.append(child_data)
        elem_data["child_items"] = child_items

    def _handle_usual_group(self, element, elem_data: Dict, allocator, form):
        """Handle UsualGroup (recursive)."""
        child_items = []
        if element.child_items:
            for child_elem in element.child_items:
                child_data = self._prepare_element(child_elem, allocator, form)
                child_items.append(child_data)
        elem_data["child_items"] = child_items

    def _handle_column_group(self, element, elem_data: Dict, allocator, form):
        """Handle ColumnGroup."""
        child_items = []
        for child_elem in element.child_items:
            child_data = self._prepare_element(child_elem, allocator, form)
            child_items.append(child_data)
        elem_data["child_items"] = child_items

    def _handle_table(self, element, elem_data: Dict, allocator, form):
        """Handle Table element."""
        table_id = elem_data["id"]
        table_data = self._prepare_table(element, table_id, allocator, form)
        elem_data.update(table_data)

    def _prepare_table(self, table_elem, table_id: int, allocator, form) -> Dict:
        """Prepare Table element with columns and IDs."""
        if table_elem.child_items:
            return self._prepare_table_with_child_items(table_elem, allocator, form)

        is_value_table = self._detect_is_value_table(table_elem, form)
        is_value_tree = self._detect_is_value_tree(table_elem, form)  # v2.64.0+
        is_dynamic_list = table_elem.properties.get("is_dynamic_list", False)

        if is_dynamic_list:
            return self._prepare_dynamic_list_table(table_elem, allocator, form)

        if is_value_tree:
            return self._prepare_value_tree_table(table_elem, allocator, form)

        return self._prepare_standard_table(table_elem, allocator, form, is_value_table)

    def _prepare_table_with_child_items(self, table_elem, allocator, form) -> Dict:
        """Prepare Table with explicit child_items."""
        child_items = []
        is_value_table = self._detect_is_value_table(table_elem, form)
        is_value_tree = self._detect_is_value_tree(table_elem, form)  # v2.69.0+ FIX

        # ValueTree is form-level like ValueTable, so treat same for DataPath
        if is_value_tree:
            is_value_table = True

        for child_elem in table_elem.child_items:
            self._set_table_context(child_elem, table_elem.tabular_section, is_value_table)
            child_data = self._prepare_element(child_elem, allocator, form)
            child_items.append(child_data)

        return {
            "tabular_section": table_elem.tabular_section,
            "is_value_table": is_value_table,
            "is_dynamic_list": table_elem.properties.get("is_dynamic_list", False),
            "events": table_elem.event_handlers,
            "child_items": child_items,
            "columns": [],
        }

    def _prepare_dynamic_list_table(self, table_elem, allocator, form) -> Dict:
        """Prepare DynamicList table."""
        columns = []
        dynamic_list_attributes = form.dynamic_list_attributes

        dl_attr = next(
            (dl for dl in dynamic_list_attributes if dl.name == table_elem.tabular_section),
            None
        )

        if dl_attr:
            if dl_attr.columns:
                for col in dl_attr.columns:
                    col_id = allocator.allocate_table_column(f"{dl_attr.name}{col.field}")
                    columns.append({
                        "type": "LabelField",
                        "name": f"{dl_attr.name}{col.field}",
                        "data_path": f"{dl_attr.name}.{col.field}",
                        "title_ru": col.title_ru if col.title_ru else col.field,
                        "title_uk": col.title_uk if col.title_uk else col.field,
                        "width": col.width,
                        "id": col_id
                    })
            elif not dl_attr.manual_query:
                col_id = allocator.allocate_table_column(f"{dl_attr.name}Description")
                columns.append({
                    "type": "LabelField",
                    "name": f"{dl_attr.name}Description",
                    "data_path": f"{dl_attr.name}.Description",
                    "title_ru": "Наименование",
                    "title_uk": "Найменування",
                    "width": None,
                    "id": col_id
                })

        return {
            "tabular_section": table_elem.tabular_section,
            "is_value_table": True,
            "is_dynamic_list": True,
            "events": table_elem.event_handlers,
            "columns": columns,
        }

    def _prepare_standard_table(self, table_elem, allocator, form, is_value_table: bool) -> Dict:
        """Prepare standard table (TabularSection or ValueTable)."""
        columns_source = None
        if is_value_table:
            columns_source = next(
                (vt for vt in form.value_table_attributes if vt.name == table_elem.tabular_section),
                None
            )
        else:
            columns_source = next(
                (ts for ts in self.processor.tabular_sections if ts.name == table_elem.tabular_section),
                None
            )

        if not columns_source:
            return {
                "tabular_section": table_elem.tabular_section,
                "is_value_table": is_value_table,
                "events": table_elem.event_handlers,
                "columns": [],
            }

        columns = []

        if not is_value_table:
            col_id = allocator.allocate_table_column("НомерСтроки")
            columns.append({"type": "LineNumber", "name": "НомерСтроки", "id": col_id})

        for col in columns_source.columns:
            col_type = "CheckBox" if col.type in ["boolean", "xs:boolean"] else "InputField"
            col_id = allocator.allocate_table_column(col.name)
            columns.append({
                "type": col_type,
                "name": col.name,
                "id": col_id,
                "read_only": col.read_only
            })

        return {
            "tabular_section": table_elem.tabular_section,
            "is_value_table": is_value_table,
            "events": table_elem.event_handlers,
            "columns": columns,
        }

    def _prepare_value_tree_table(self, table_elem, allocator, form) -> Dict:
        """Prepare ValueTree table (v2.64.0+).

        ValueTree is a hierarchical structure displayed as tree.
        Similar to ValueTable but with parent-child relationships.
        """
        # Get tree attribute
        tree_attr = next(
            (vt for vt in form.value_tree_attributes if vt.name == table_elem.tabular_section),
            None
        )

        if not tree_attr:
            return {
                "tabular_section": table_elem.tabular_section,
                "is_value_table": True,  # ValueTree is form-level like ValueTable
                "is_value_tree": True,
                "events": table_elem.event_handlers,
                "columns": [],
                # Tree-specific properties
                "representation": "tree",
                "initial_tree_view": table_elem.properties.get("initial_tree_view", "no_expand"),
                "show_root": table_elem.properties.get("show_root", True),
                "allow_root_choice": table_elem.properties.get("allow_root_choice", False),
                "choice_folders_and_items": table_elem.properties.get("choice_folders_and_items", "folders_and_items"),
            }

        columns = []
        for col in tree_attr.columns:
            col_type = "CheckBox" if col.type in ["boolean", "xs:boolean"] else "InputField"
            col_id = allocator.allocate_table_column(col.name)
            columns.append({
                "type": col_type,
                "name": col.name,
                "id": col_id,
                "read_only": col.read_only
            })

        return {
            "tabular_section": table_elem.tabular_section,
            "is_value_table": True,  # ValueTree is form-level like ValueTable
            "is_value_tree": True,
            "events": table_elem.event_handlers,
            "columns": columns,
            # Tree-specific properties
            "representation": "tree",
            "initial_tree_view": table_elem.properties.get("initial_tree_view", "no_expand"),
            "show_root": table_elem.properties.get("show_root", True),
            "allow_root_choice": table_elem.properties.get("allow_root_choice", False),
            "choice_folders_and_items": table_elem.properties.get("choice_folders_and_items", "folders_and_items"),
        }

    def _set_table_context(self, element, tabular_section: str, is_value_table: bool):
        """Recursively set data_path for table elements."""
        field_types = [
            "InputField", "LabelField", "CheckBoxField",
            "PictureField", "RadioButtonField"
        ]

        if element.element_type in field_types:
            if element.attribute and "data_path" not in element.properties:
                if is_value_table:
                    element.properties["data_path"] = f"{tabular_section}.{element.attribute}"
                else:
                    element.properties["data_path"] = f"Объект.{tabular_section}.{element.attribute}"

        elif element.element_type == "ColumnGroup":
            for child in element.child_items:
                self._set_table_context(child, tabular_section, is_value_table)

    def _prepare_pages(self, elem, allocator, form) -> Dict:
        """Prepare Pages element."""
        pages_id = allocator.allocate("Pages", elem.name)

        page_items = []
        if elem.child_items:
            for page_elem in elem.child_items:
                page_id = allocator.allocate("Page", page_elem.name)
                page_data = {
                    "type": "Page",
                    "name": page_elem.name,
                    "id": page_id,
                    "properties": page_elem.properties or {},
                }

                nested_items = []
                if page_elem.child_items:
                    for nested_elem in page_elem.child_items:
                        nested_data = self._prepare_element(nested_elem, allocator, form)
                        nested_items.append(nested_data)

                page_data["child_items"] = nested_items
                page_items.append(page_data)

        return {
            "type": "Pages",
            "name": elem.name,
            "id": pages_id,
            "properties": elem.properties,
            "events": elem.event_handlers,
            "page_items": page_items
        }

    def _prepare_popup(self, elem, allocator) -> Dict:
        """Prepare Popup element."""
        popup_id = allocator.allocate("Popup", elem.name)

        child_items = []
        if elem.child_items:
            for child_elem in elem.child_items:
                if child_elem.element_type == "Popup":
                    child_data = self._prepare_popup(child_elem, allocator)
                else:
                    child_id = allocator.allocate(child_elem.element_type, child_elem.name)
                    child_data = {
                        "type": child_elem.element_type,
                        "name": child_elem.name,
                        "id": child_id,
                        "properties": child_elem.properties,
                    }
                    if child_elem.element_type == "Button":
                        child_data["command"] = child_elem.command
                child_items.append(child_data)

        return {
            "type": "Popup",
            "name": elem.name,
            "id": popup_id,
            "properties": elem.properties,
            "events": elem.event_handlers,
            "child_items": child_items
        }

    def prepare_auto_command_bar(self, form, start_id: int) -> Tuple[List[Dict], int]:
        """Prepare AutoCommandBar elements."""
        allocator = self._IDAllocator(_start_id=start_id)
        auto_elements = []

        for elem in form.auto_command_bar_elements:
            if elem.element_type == "Popup":
                elem_data = self._prepare_popup(elem, allocator)
            else:
                elem_data = self._prepare_element(elem, allocator, form)
            auto_elements.append(elem_data)

        return auto_elements, allocator.current
