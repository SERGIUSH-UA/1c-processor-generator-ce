"""
Element Parser - registry-based парсер для form elements.

v2.43.0 DRY Refactoring

Замінює 600-рядковий _create_simple_element метод на чистий schema-based підхід.

Використання:
    >>> from parsing.elements import ElementParser
    >>> parser = ElementParser()
    >>> element = parser.parse({"type": "InputField", "name": "Field1", "attribute": "Attr1"})
"""

from typing import Dict, Optional, List, Any, Callable
from ..models import FormElement, ConditionalAppearanceItem, ConditionalFilter, AppearanceStyle
from .schemas import SCHEMAS, ElementSchema, COLUMN_GROUP_ALLOWED_CHILDREN, get_schema
from .extractors import normalize_multilang, extract_props


class ElementParser:
    """
    Registry-based parser для form elements.

    Підтримує:
    - Schema-based парсинг для стандартних елементів
    - Custom parsers для складних типів (Pages, Popup, ColumnGroup)
    - Рекурсивний парсинг дочірніх елементів
    """

    # Default languages for backward compatibility
    DEFAULT_LANGUAGES = ["ru", "uk", "en"]

    def __init__(self, languages: Optional[List[str]] = None):
        """
        Ініціалізація з реєстрацією custom parsers.

        Args:
            languages: Список мов для compact multilang syntax (v2.69.0+)
        """
        self.languages = languages if languages is not None else self.DEFAULT_LANGUAGES
        self._custom_parsers: Dict[str, Callable[[Dict[str, Any]], Optional[FormElement]]] = {
            "Pages": self._parse_pages,
            "ColumnGroup": self._parse_column_group,
        }

    def parse(self, config: Dict[str, Any]) -> Optional[FormElement]:
        """
        Головний метод парсингу елемента.

        Args:
            config: YAML конфігурація елемента

        Returns:
            FormElement або None якщо тип невідомий
        """
        # Нормалізуємо multilang поля з підтримкою compact syntax (v2.69.0+)
        config = normalize_multilang(config, languages=self.languages)
        elem_type = config.get("type")

        if not elem_type:
            print("⚠️ Element config missing 'type' field")
            return None

        # Custom parser?
        if elem_type in self._custom_parsers:
            return self._custom_parsers[elem_type](config)

        # Schema-based parsing
        schema = get_schema(elem_type)
        if not schema:
            print(f"⚠️ Unknown element type: {elem_type}")
            return None

        return self._parse_by_schema(config, schema)

    def _parse_by_schema(self, config: Dict[str, Any], schema: ElementSchema) -> FormElement:
        """
        Парсинг елемента за декларативною схемою.

        Args:
            config: Нормалізована конфігурація
            schema: Схема елемента

        Returns:
            FormElement з витягнутими properties
        """
        props = extract_props(config, schema)

        # Отримуємо tabular_section з можливим встановленням is_value_table в props
        tabular_section = None
        if schema.has_tabular_section:
            tabular_section = self._get_tabular_section(config, props)

        # Парсимо conditional_appearances (v2.67.0+)
        conditional_appearances = []
        if "conditional_appearances" in config:
            conditional_appearances = self._parse_conditional_appearances(config["conditional_appearances"])

        elem = FormElement(
            element_type=schema.element_type,
            name=config["name"],
            attribute=config.get("attribute") if schema.has_attribute else None,
            command=config.get("command") if schema.has_command else None,
            tabular_section=tabular_section,
            event_handlers=config.get("events", {}),
            properties=props,
            conditional_appearances=conditional_appearances,
        )

        # Рекурсивно парсимо дочірні елементи
        if schema.has_children:
            children_key = schema.children_key
            # Підтримка обох варіантів: elements та child_items
            children_config = config.get(children_key, config.get("child_items", []))
            child_items = self._parse_children(children_config)
            elem.child_items = child_items

        return elem

    def _parse_children(self, children_config: List[Dict[str, Any]]) -> List[FormElement]:
        """
        Рекурсивно парсить дочірні елементи.

        Args:
            children_config: Список конфігурацій дочірніх елементів

        Returns:
            Список FormElement
        """
        children = []
        for child_config in children_config:
            child = self.parse(child_config)
            if child:
                children.append(child)
        return children

    def _get_tabular_section(self, config: Dict[str, Any], props: Dict[str, Any]) -> Optional[str]:
        """
        Отримує ім'я tabular section з конфігурації.

        Підтримує:
        - tabular_section: для TabularSection
        - value_table: для ValueTable (автоматично встановлює is_value_table=True)

        Args:
            config: Конфігурація елемента
            props: Properties елемента (для встановлення is_value_table)

        Returns:
            Ім'я tabular section або None
        """
        # Якщо використовується ключ value_table: - встановлюємо is_value_table=True
        if "value_table" in config:
            props["is_value_table"] = True
            return config["value_table"]
        return config.get("tabular_section")

    # =========================================================================
    # Custom Parsers для складних типів
    # =========================================================================

    def _parse_pages(self, config: Dict[str, Any]) -> FormElement:
        """
        Спеціальний парсер для Pages.

        Pages має структуру:
        - pages: список сторінок (Page)
        - Кожна Page має child_items/elements

        Args:
            config: Конфігурація Pages елемента

        Returns:
            FormElement типу Pages з вкладеними Page (FormElement) елементами
        """
        schema = get_schema("Pages")
        props = extract_props(config, schema)

        pages_elem = FormElement(
            element_type="Pages",
            name=config["name"],
            properties=props,
        )

        # Парсимо сторінки
        pages_config = config.get("pages", [])
        for page_config in pages_config:
            page_config = normalize_multilang(page_config, languages=self.languages)
            title = page_config.get("title", page_config["name"])

            # Створюємо FormElement замість dict
            page = FormElement(
                element_type="Page",
                name=page_config["name"],
                properties={
                    "title_ru": page_config.get("title_ru", title),
                    "title_uk": page_config.get("title_uk", title),
                    "title_en": page_config.get("title_en", title),
                },
            )

            # Парсимо вкладені елементи Page
            children_config = page_config.get("elements", page_config.get("child_items", []))
            for child_config in children_config:
                child = self.parse(child_config)
                if child:
                    page.child_items.append(child)

            pages_elem.child_items.append(page)

        return pages_elem

    def _parse_column_group(self, config: Dict[str, Any]) -> FormElement:
        """
        Спеціальний парсер для ColumnGroup з валідацією дочірніх типів.

        ColumnGroup може містити тільки:
        - LabelField
        - InputField
        - CheckBoxField
        - PictureField

        Args:
            config: Конфігурація ColumnGroup

        Returns:
            FormElement типу ColumnGroup
        """
        schema = get_schema("ColumnGroup")
        props = extract_props(config, schema)
        name = config["name"]

        # Рекурсивно парсимо дочірні елементи з валідацією
        children_config = config.get("elements", config.get("child_items", []))
        child_items = []

        for child_config in children_config:
            child_type = child_config.get("type")

            # Валідація типу дочірнього елемента
            if child_type not in COLUMN_GROUP_ALLOWED_CHILDREN:
                print(
                    f"⚠️ ColumnGroup '{name}' може містити тільки field елементи "
                    f"({', '.join(COLUMN_GROUP_ALLOWED_CHILDREN)}). Знайдено: {child_type}"
                )
                continue

            child = self.parse(child_config)
            if child:
                child_items.append(child)

        return FormElement(
            element_type="ColumnGroup",
            name=name,
            properties=props,
            child_items=child_items,
        )

    # =========================================================================
    # ConditionalAppearance Parsing (v2.67.0+)
    # =========================================================================

    def _parse_conditional_appearances(
        self, ca_list: List[Dict[str, Any]]
    ) -> List[ConditionalAppearanceItem]:
        """
        Парсить список правил умовного оформлення.

        Args:
            ca_list: Список конфігурацій правил з YAML

        Returns:
            Список ConditionalAppearanceItem

        Example YAML:
            conditional_appearances:
              - name: WhiteCells
                selection: [Piece]
                filter:
                  field: IsWhite
                  comparison: Equal
                  value: true
                  value_type: boolean
                appearance:
                  back_color: "#F5F5DC"
        """
        items = []
        for ca_config in ca_list:
            # Парсимо filter
            filter_obj = None
            if "filter" in ca_config:
                f = ca_config["filter"]
                filter_obj = ConditionalFilter(
                    field=f["field"],
                    comparison=f.get("comparison", "Equal"),
                    value=f.get("value"),
                    value_type=f.get("value_type", "string"),
                )

            # Парсимо appearance
            appearance_obj = None
            if "appearance" in ca_config:
                a = ca_config["appearance"]
                appearance_obj = AppearanceStyle(
                    back_color=a.get("back_color"),
                    text_color=a.get("text_color"),
                    font_bold=a.get("font_bold"),
                    font_italic=a.get("font_italic"),
                    visible=a.get("visible"),
                    enabled=a.get("enabled"),
                )

            item = ConditionalAppearanceItem(
                name=ca_config.get("name", "Rule"),
                selection=ca_config.get("selection", []),
                filter=filter_obj,
                appearance=appearance_obj,
            )
            items.append(item)

        return items
