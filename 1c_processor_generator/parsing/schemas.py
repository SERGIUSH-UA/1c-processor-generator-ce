"""
Element Schemas - декларативні схеми для form elements.

v2.43.0 DRY Refactoring

Визначає структуру всіх типів елементів форми для schema-based парсингу.
Кожна схема описує:
- Які properties підтримує елемент
- Чи має attribute, command, tabular_section
- Чи може мати дочірні елементи

Використання:
    >>> from parsing.schemas import SCHEMAS, get_schema
    >>> schema = get_schema("InputField")
    >>> schema.has_attribute  # True
"""

from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict


@dataclass
class PropSpec:
    """Специфікація однієї property елемента."""

    key: str  # YAML ключ
    target: Optional[str] = None  # Target key якщо відрізняється від key
    multilang: bool = False  # True = key_ru, key_uk, key_en
    default: Any = None  # Default value якщо не вказано


@dataclass
class ElementSchema:
    """Декларативна схема типу елемента форми."""

    element_type: str
    props: List[PropSpec] = field(default_factory=list)
    has_attribute: bool = False  # InputField, LabelField, etc.
    has_command: bool = False  # Button
    has_tabular_section: bool = False  # Table
    has_children: bool = False  # UsualGroup, Pages, ButtonGroup, etc.
    children_key: str = "elements"  # Ключ для дочірніх елементів


# =============================================================================
# Reusable property groups (DRY)
# =============================================================================

MULTILANG_TITLE = [
    PropSpec("title", multilang=True),
    PropSpec("tooltip", multilang=True),
]

ALIGNMENT_PROPS = [
    PropSpec("horizontal_align"),
    PropSpec("vertical_align"),
]

SIZE_PROPS = [
    PropSpec("width"),
    PropSpec("height"),
    PropSpec("horizontal_stretch"),
    PropSpec("vertical_stretch"),
]

# v2.72.0+: Visibility properties (visible, enabled)
VISIBILITY_PROPS = [
    PropSpec("visible"),   # Boolean: true/false - element visibility
    PropSpec("enabled"),   # Boolean: true/false - element enabled state
]


# =============================================================================
# Element Schemas - all 15 types
# =============================================================================

SCHEMAS: Dict[str, ElementSchema] = {
    # -------------------------------------------------------------------------
    # InputField - основне поле вводу
    # -------------------------------------------------------------------------
    "InputField": ElementSchema(
        element_type="InputField",
        has_attribute=True,
        props=[
            *MULTILANG_TITLE,
            PropSpec("tooltip", multilang=True),
            PropSpec("input_hint", multilang=True),
            *SIZE_PROPS,
            *ALIGNMENT_PROPS,
            *VISIBILITY_PROPS,  # v2.72.0+
            PropSpec("read_only"),
            PropSpec("multi_line", target="multiline"),
            PropSpec("multiline"),
            PropSpec("password_mode"),
            PropSpec("text_edit"),
            PropSpec("auto_max_width"),
            PropSpec("auto_max_height"),
            PropSpec("title_location"),
            PropSpec("choice_list"),
            PropSpec("choice_mode"),
            PropSpec("choice_folders_and_items"),
            PropSpec("quick_choice"),
            PropSpec("choice_history_on_input"),
            # v2.42.0+: Colors, fonts, choice button picture
            PropSpec("title_text_color"),
            PropSpec("title_font"),
            PropSpec("text_color"),
            PropSpec("back_color"),
            PropSpec("border_color"),
            PropSpec("font"),
            PropSpec("choice_button_picture"),
            PropSpec("choice_button"),
            # v2.67.0+: Conditional Appearance
            PropSpec("conditional_appearances"),
            # v2.68.0+: Table column properties (heights, footer_font)
            PropSpec("title_height"),
            PropSpec("footer_font"),
            # v2.71.0+: InputField button controls
            PropSpec("mark_negatives"),
            PropSpec("open_button"),
            PropSpec("clear_button"),
            PropSpec("drop_list_button"),
            PropSpec("spin_button"),
            PropSpec("create_button"),
            # v2.71.1+: AutoMarkIncomplete
            PropSpec("auto_mark_incomplete"),
        ],
    ),
    # -------------------------------------------------------------------------
    # LabelField - поле-надпис з прив'язкою до атрибута
    # -------------------------------------------------------------------------
    "LabelField": ElementSchema(
        element_type="LabelField",
        has_attribute=True,
        props=[
            *MULTILANG_TITLE,
            PropSpec("data_path"),
            PropSpec("hyperlink"),
            *ALIGNMENT_PROPS,
            *VISIBILITY_PROPS,  # v2.72.0+
            # v2.67.0+: Conditional Appearance
            PropSpec("conditional_appearances"),
        ],
    ),
    # -------------------------------------------------------------------------
    # LabelDecoration - декоративний надпис
    # -------------------------------------------------------------------------
    "LabelDecoration": ElementSchema(
        element_type="LabelDecoration",
        props=[
            *MULTILANG_TITLE,
            PropSpec("formatted"),  # For FormattedString support (v2.45.0+)
            PropSpec("hyperlink"),
            PropSpec("font"),
            *ALIGNMENT_PROPS,
            *VISIBILITY_PROPS,  # v2.72.0+
        ],
    ),
    # -------------------------------------------------------------------------
    # PictureDecoration - декоративне зображення
    # -------------------------------------------------------------------------
    "PictureDecoration": ElementSchema(
        element_type="PictureDecoration",
        props=[
            PropSpec("svg_source"),
            PropSpec("picture"),
            PropSpec("svg_width"),
            PropSpec("svg_height"),
            PropSpec("form_width"),
            PropSpec("form_height"),
            PropSpec("width"),
            PropSpec("height"),
            PropSpec("alignment"),
            PropSpec("hyperlink"),
            PropSpec("picture_size", default="Proportionally"),
            PropSpec("zoomable"),
            *VISIBILITY_PROPS,  # v2.72.0+
        ],
    ),
    # -------------------------------------------------------------------------
    # PictureField - поле зображення з прив'язкою до атрибута
    # -------------------------------------------------------------------------
    "PictureField": ElementSchema(
        element_type="PictureField",
        has_attribute=True,
        props=[
            PropSpec("title_location"),
            PropSpec("picture_size"),
            PropSpec("zoomable"),
            PropSpec("width"),
            PropSpec("height"),
            *VISIBILITY_PROPS,  # v2.72.0+
        ],
    ),
    # -------------------------------------------------------------------------
    # Table - таблиця (TabularSection, ValueTable, or ValueTree)
    # -------------------------------------------------------------------------
    "Table": ElementSchema(
        element_type="Table",
        has_tabular_section=True,
        has_children=True,
        props=[
            PropSpec("read_only"),
            PropSpec("height"),
            PropSpec("horizontal_stretch"),
            PropSpec("is_value_table"),
            PropSpec("is_dynamic_list"),
            # Tree-specific properties (v2.64.0+)
            PropSpec("representation"),           # "list" | "tree"
            PropSpec("initial_tree_view"),        # "no_expand" | "expand_top_level" | "expand_all_levels"
            PropSpec("show_root"),                # boolean
            PropSpec("allow_root_choice"),        # boolean
            PropSpec("choice_folders_and_items"), # "folders" | "items" | "folders_and_items"
            # v2.67.0+: Conditional Appearance
            PropSpec("conditional_appearances"),
            # v2.68.0+: Table heights
            PropSpec("height_in_table_rows"),     # кількість видимих рядків
            PropSpec("header_height"),            # висота заголовка колонок
            PropSpec("title_height"),             # висота назви таблиці
            PropSpec("footer_height"),            # висота підвалу
            # v2.71.2+: Table properties
            PropSpec("search_string_location"),   # None | CommandBar
            PropSpec("row_picture_data_path"),    # DataPath for row icons
            PropSpec("selection_mode"),           # SingleRow | MultiRow
            # Table drag-drop properties (v2.71.2+)
            PropSpec("auto_insert_new_row"),
            PropSpec("enable_start_drag"),
            PropSpec("enable_drag"),
            *VISIBILITY_PROPS,  # v2.72.0+
        ],
    ),
    # -------------------------------------------------------------------------
    # Button - кнопка з прив'язкою до команди
    # -------------------------------------------------------------------------
    "Button": ElementSchema(
        element_type="Button",
        has_command=True,
        props=[
            PropSpec("width"),
            PropSpec("representation"),
            *ALIGNMENT_PROPS,
            *VISIBILITY_PROPS,  # v2.72.0+
            # v2.67.0+: Conditional Appearance
            PropSpec("conditional_appearances"),
            # v2.71.1+: DefaultButton
            PropSpec("default_button"),
            # v2.71.3+: ShapeRepresentation
            PropSpec("shape_representation"),
        ],
    ),
    # -------------------------------------------------------------------------
    # RadioButtonField - перемикач
    # -------------------------------------------------------------------------
    "RadioButtonField": ElementSchema(
        element_type="RadioButtonField",
        has_attribute=True,
        props=[
            PropSpec("radio_button_type"),
            PropSpec("choice_list"),
            PropSpec("title_location"),
            *VISIBILITY_PROPS,  # v2.72.0+
            # v2.67.0+: Conditional Appearance
            PropSpec("conditional_appearances"),
        ],
    ),
    # -------------------------------------------------------------------------
    # CheckBoxField - прапорець
    # -------------------------------------------------------------------------
    "CheckBoxField": ElementSchema(
        element_type="CheckBoxField",
        has_attribute=True,
        props=[
            PropSpec("width"),
            PropSpec("title_location"),
            *VISIBILITY_PROPS,  # v2.72.0+
            # v2.67.0+: Conditional Appearance
            PropSpec("conditional_appearances"),
        ],
    ),
    # -------------------------------------------------------------------------
    # SpreadSheetDocumentField - поле табличного документа
    # -------------------------------------------------------------------------
    "SpreadSheetDocumentField": ElementSchema(
        element_type="SpreadSheetDocumentField",
        has_attribute=True,
        props=[
            PropSpec("title_location"),
            PropSpec("vertical_scrollbar"),
            PropSpec("horizontal_scrollbar"),
            PropSpec("show_grid"),
            PropSpec("show_headers"),
            PropSpec("edit"),
            PropSpec("protection"),
            *VISIBILITY_PROPS,  # v2.72.0+
        ],
    ),
    # -------------------------------------------------------------------------
    # HTMLDocumentField - поле HTML документа
    # -------------------------------------------------------------------------
    "HTMLDocumentField": ElementSchema(
        element_type="HTMLDocumentField",
        has_attribute=True,
        props=[
            PropSpec("title_location"),
            PropSpec("width"),
            PropSpec("height"),
            PropSpec("horizontal_stretch"),
            PropSpec("vertical_stretch"),
            PropSpec("stretch"),
            PropSpec("template", target="template_ref"),
            *VISIBILITY_PROPS,  # v2.72.0+
        ],
    ),
    # -------------------------------------------------------------------------
    # CalendarField - поле календаря (v2.46.0+)
    # -------------------------------------------------------------------------
    "CalendarField": ElementSchema(
        element_type="CalendarField",
        has_attribute=True,
        props=[
            PropSpec("title_location"),
            PropSpec("width"),
            PropSpec("height"),
            PropSpec("show_current_date"),
            PropSpec("first_day_of_week"),
            PropSpec("begin_of_representation_period"),
            PropSpec("end_of_representation_period"),
            *VISIBILITY_PROPS,  # v2.72.0+
        ],
    ),
    # -------------------------------------------------------------------------
    # ChartField - поле діаграми (v2.46.0+)
    # -------------------------------------------------------------------------
    "ChartField": ElementSchema(
        element_type="ChartField",
        has_attribute=True,
        props=[
            PropSpec("title_location"),
            PropSpec("width"),
            PropSpec("height"),
            PropSpec("chart_type"),
            PropSpec("show_legend"),
            PropSpec("transparent_background"),
            *VISIBILITY_PROPS,  # v2.72.0+
        ],
    ),
    # -------------------------------------------------------------------------
    # PlannerField - поле планувальника (v2.46.0+, enhanced v2.47.0)
    # -------------------------------------------------------------------------
    "PlannerField": ElementSchema(
        element_type="PlannerField",
        has_attribute=True,
        props=[
            PropSpec("title_location"),
            PropSpec("width"),
            PropSpec("height"),
            PropSpec("enable_drag"),  # v2.47.0+ enable drag-drop
            PropSpec("show_weekends"),
            PropSpec("period"),
            PropSpec("representation"),
            *VISIBILITY_PROPS,  # v2.72.0+
        ],
    ),
    # -------------------------------------------------------------------------
    # UsualGroup - група елементів
    # -------------------------------------------------------------------------
    "UsualGroup": ElementSchema(
        element_type="UsualGroup",
        has_children=True,
        props=[
            *MULTILANG_TITLE,
            PropSpec("show_title", default=False),
            PropSpec("group_direction", default="Vertical"),
            PropSpec("representation", default="None"),
            PropSpec("behavior"),
            PropSpec("read_only"),
            *VISIBILITY_PROPS,  # v2.72.0+
        ],
    ),
    # -------------------------------------------------------------------------
    # ButtonGroup - група кнопок
    # -------------------------------------------------------------------------
    "ButtonGroup": ElementSchema(
        element_type="ButtonGroup",
        has_children=True,
        props=[
            *MULTILANG_TITLE,
            PropSpec("group_direction", default="Horizontal"),
            *VISIBILITY_PROPS,  # v2.72.0+
        ],
    ),
    # -------------------------------------------------------------------------
    # ColumnGroup - група колонок таблиці
    # -------------------------------------------------------------------------
    "ColumnGroup": ElementSchema(
        element_type="ColumnGroup",
        has_children=True,
        props=[
            *MULTILANG_TITLE,
            PropSpec("group_layout", default="Horizontal"),
            PropSpec("show_in_header", default=True),
            *ALIGNMENT_PROPS,
            *VISIBILITY_PROPS,  # v2.72.0+
        ],
    ),
    # -------------------------------------------------------------------------
    # Popup - спливаюче меню
    # -------------------------------------------------------------------------
    "Popup": ElementSchema(
        element_type="Popup",
        has_children=True,
        children_key="child_items",
        props=[
            *MULTILANG_TITLE,
            PropSpec("picture"),
            PropSpec("representation"),
            *VISIBILITY_PROPS,  # v2.72.0+
        ],
    ),
    # -------------------------------------------------------------------------
    # Pages - сторінки (закладки)
    # Примітка: має спеціальну структуру з pages замість elements
    # -------------------------------------------------------------------------
    "Pages": ElementSchema(
        element_type="Pages",
        has_children=True,
        children_key="pages",  # Спеціальний ключ!
        props=[
            PropSpec("pages_representation", default="TabsOnTop"),
            *VISIBILITY_PROPS,  # v2.72.0+
        ],
    ),
    # -------------------------------------------------------------------------
    # Page - окрема сторінка всередині Pages
    # -------------------------------------------------------------------------
    "Page": ElementSchema(
        element_type="Page",
        has_children=True,
        children_key="elements",
        props=[
            PropSpec("title", multilang=True),
            *VISIBILITY_PROPS,  # v2.72.0+
        ],
    ),
}


# =============================================================================
# Validation helpers
# =============================================================================

# Дозволені дочірні типи для ColumnGroup
COLUMN_GROUP_ALLOWED_CHILDREN = {"LabelField", "InputField", "CheckBoxField", "PictureField"}


def get_schema(element_type: str) -> Optional[ElementSchema]:
    """
    Отримує схему для типу елемента.

    Args:
        element_type: Тип елемента (InputField, Table, etc.)

    Returns:
        ElementSchema або None якщо тип невідомий
    """
    return SCHEMAS.get(element_type)
