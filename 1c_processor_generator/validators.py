"""
Валідатори для перевірки коректності генерованих структур
"""

import re
from pathlib import Path
from typing import List, Tuple, Dict, Optional, Set
from difflib import get_close_matches
from .constants import (
    VALID_STD_PICTURES, BSL_RESERVED_KEYWORDS, FORM_BUILTIN_METHODS,
    VALID_FUNCTION_KEYS, VALID_SPECIAL_KEYS, VALID_MODIFIERS, VALID_KEY_NAMES,
)

# Зарезервовані назви метаданих 1C (не можуть використовуватися як імена реквізитів, таблиць, тощо)
RESERVED_METADATA_NAMES = {
    # Системні колекції метаданих (регістронезалежно)
    "Документы",
    "Справочники",
    "Регистры",
    "Перечисления",
    "Отчеты",
    "Обработки",
    "ПланыВидовХарактеристик",
    "ПланыСчетов",
    "ПланыВидовРасчета",
    "БизнесПроцессы",
    "Задачи",
    "ОбменДанными",
    "ХранилищаНастроек",
    # Системні реквізити
    "Параметры",
    "ДополнительныеСвойства",
    "Ссылка",  # може бути проблематичним у деяких контекстах
    "ПометкаУдаления",
    "Предопределенный",
    "Владелец",
    "Родитель",
}


class ValidationError(Exception):
    """Помилка валідації"""
    pass


def validate_uuid(uuid: str) -> Tuple[bool, str]:
    """
    Перевіряє чи UUID валідний для 1C

    Returns:
        (True, "") якщо валідний
        (False, "повідомлення про помилку") якщо невалідний
    """
    # UUID має формат: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    # де x - hex цифра (0-9, a-f)
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'

    if not re.match(uuid_pattern, uuid.lower()):
        # Перевірка на невалідні символи
        invalid_chars = set(re.findall(r'[^0-9a-f\-]', uuid.lower()))
        if invalid_chars:
            return False, f"UUID містить невалідні символи: {', '.join(invalid_chars)}. Дозволені тільки 0-9, a-f"
        return False, "UUID має невірний формат. Очікується: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    return True, ""


def validate_identifier(name: str) -> Tuple[bool, str]:
    """
    Перевіряє чи ім'я ідентифікатора валідне для 1C

    1C ідентифікатори:
    - Починаються з букви або _
    - Містять букви, цифри, _
    - Підтримують кирилицю
    """
    if not name:
        return False, "Ім'я не може бути порожнім"

    # Перевірка першого символу
    if not re.match(r'^[а-яА-ЯёЁa-zA-Z_]', name):
        return False, f"Ім'я '{name}' повинно починатися з букви або підкреслення"

    # Перевірка решти символів
    if not re.match(r'^[а-яА-ЯёЁa-zA-Z0-9_]+$', name):
        invalid_chars = set(re.findall(r'[^а-яА-ЯёЁa-zA-Z0-9_]', name))
        return False, f"Ім'я '{name}' містить невалідні символи: {', '.join(invalid_chars)}"

    return True, ""


def validate_id_sequence(ids: List[int]) -> Tuple[bool, str]:
    """
    Перевіряє чи послідовність ID коректна

    - AutoCommandBar має бути -1
    - Решта ID мають бути унікальними та > 0
    """
    if -1 not in ids:
        return False, "Відсутній AutoCommandBar з id=-1"

    positive_ids = [id for id in ids if id > 0]

    if len(positive_ids) != len(set(positive_ids)):
        duplicates = [id for id in positive_ids if positive_ids.count(id) > 1]
        return False, f"Знайдені дубльовані ID: {set(duplicates)}"

    return True, ""


def validate_type(type_str: str) -> Tuple[bool, str]:
    """
    Перевіряє чи тип даних валідний
    """
    valid_base_types = ["xs:string", "xs:boolean", "xs:decimal", "xs:dateTime"]

    # Базові типи
    if type_str in valid_base_types:
        return True, ""

    # Типи string, boolean, number, date, spreadsheet_document (конвертуються автоматично)
    if type_str in ["string", "boolean", "number", "date", "spreadsheet_document"]:
        return True, ""

    # Довідникові типи
    if type_str.startswith("cfg:CatalogRef.") or type_str.startswith("CatalogRef."):
        return True, ""

    # Документи
    if type_str.startswith("cfg:DocumentRef.") or type_str.startswith("DocumentRef."):
        return True, ""

    return False, f"Невідомий тип даних: {type_str}"


def validate_processor_name(name: str) -> Tuple[bool, str]:
    """
    Перевіряє чи назва обробки валідна

    Рекомендації:
    - PascalCase
    - Кирилиця
    - Без пробілів
    """
    is_valid, error = validate_identifier(name)
    if not is_valid:
        return False, error

    # Перевірка на пробіли
    if ' ' in name:
        return False, f"Назва обробки '{name}' не повинна містити пробіли. Використовуйте PascalCase"

    # Рекомендація: має починатися з великої літери
    if not name[0].isupper():
        return False, f"Назва обробки '{name}' має починатися з великої літери (PascalCase)"

    return True, ""


def validate_all_uuids(uuids: List[str]) -> List[str]:
    """
    Перевіряє всі UUID та повертає список помилок
    """
    errors = []

    for i, uuid in enumerate(uuids):
        is_valid, error = validate_uuid(uuid)
        if not is_valid:
            errors.append(f"UUID #{i+1}: {error}")

    # Перевірка на унікальність
    if len(uuids) != len(set(uuids)):
        duplicates = [uuid for uuid in uuids if uuids.count(uuid) > 1]
        errors.append(f"Знайдені дубльовані UUID: {set(duplicates)}")

    return errors


def validate_length_for_string(length: int) -> Tuple[bool, str]:
    """Перевіряє чи довжина рядка валідна"""
    if length <= 0:
        return False, "Довжина рядка має бути > 0"
    if length > 1024:
        return False, "Довжина рядка не може перевищувати 1024 (рекомендація 1C)"
    return True, ""


def validate_number_qualifiers(digits: int, fraction_digits: int) -> Tuple[bool, str]:
    """Перевіряє чи кваліфікатори числа валідні"""
    if digits <= 0:
        return False, "Загальна кількість цифр має бути > 0"
    if fraction_digits < 0:
        return False, "Кількість десяткових знаків не може бути < 0"
    if fraction_digits >= digits:
        return False, "Кількість десяткових знаків має бути < загальної кількості цифр"
    if digits > 38:
        return False, "Загальна кількість цифр не може перевищувати 38 (обмеження 1C)"
    return True, ""


def validate_picture(picture: str) -> Tuple[bool, str]:
    """
    Перевіряє чи картинка валідна

    Підтримуються:
    - StdPicture.* - стандартні картинки платформи
    - CommonPicture.* - загальні картинки конфігурації
    """
    if not picture:
        return True, ""  # Картинка опціональна

    # Перевірка StdPicture
    if picture.startswith("StdPicture."):
        if picture in VALID_STD_PICTURES:
            return True, ""

        # Fuzzy matching: suggest similar valid pictures
        suggestions = get_close_matches(
            picture,
            VALID_STD_PICTURES,
            n=5,           # Top 5 suggestions
            cutoff=0.4     # Lower cutoff to catch more variants
        )

        if suggestions:
            # Build helpful error message with suggestions
            suggestions_str = "\n    ".join(suggestions)
            return False, (
                f"Невідома стандартна картинка: {picture}\n\n"
                f"💡 Схожі валідні картинки:\n"
                f"    {suggestions_str}\n\n"
                f"Повний список: docs/VALID_PICTURES.md або constants.VALID_STD_PICTURES"
            )
        else:
            # No close matches - show common examples
            return False, (
                f"Невідома стандартна картинка: {picture}\n\n"
                f"Не знайдено схожих варіантів. Можливо, ви мали на увазі:\n"
                f"    StdPicture.ExecuteTask (виконати)\n"
                f"    StdPicture.SaveFile (зберегти)\n"
                f"    StdPicture.OpenFile (відкрити)\n"
                f"    StdPicture.Refresh (оновити)\n\n"
                f"Повний список: docs/VALID_PICTURES.md"
            )

    # Перевірка CommonPicture (дозволяємо будь-які, бо вони можуть бути в конфігурації)
    if picture.startswith("CommonPicture."):
        return True, ""

    return False, (
        f"Невірний формат картинки: {picture}. "
        f"Очікується StdPicture.* або CommonPicture.*"
    )


def validate_choice_list(choice_list: list, context: str) -> Tuple[bool, str]:
    """
    Перевіряє формат choice_list (v2.69.0+)

    Очікуваний формат:
    choice_list:
      - v: "Value"      # обов'язково
        ru: "Опис"      # обов'язково (мінімум одна мова)
        uk: "Опис"      # опціонально
        en: "Desc"      # опціонально
        t: "xs:string"  # опціонально

    Args:
        choice_list: Список елементів choice_list
        context: Контекст для повідомлення про помилку (напр. "InputField 'Статус'")

    Returns:
        (is_valid, error_message)
    """
    if not choice_list:
        return True, ""

    if not isinstance(choice_list, list):
        return False, (
            f"{context}: choice_list має бути списком, отримано {type(choice_list).__name__}"
        )

    for i, item in enumerate(choice_list):
        if isinstance(item, str):
            return False, (
                f"{context}: choice_list[{i}] має бути об'єктом {{v, ru}}, отримано рядок \"{item}\"\n\n"
                f"💡 Правильний формат (v2.69.0+):\n"
                f"    choice_list:\n"
                f"      - v: \"Value\"     # значення (без пробілів)\n"
                f"        ru: \"Опис\"     # відображення\n"
                f"        uk: \"Опис\"     # опціонально"
            )

        if not isinstance(item, dict):
            return False, (
                f"{context}: choice_list[{i}] має бути об'єктом, отримано {type(item).__name__}"
            )

        # Перевірка обов'язкових ключів
        if 'v' not in item:
            # Можливо старий формат з 'value'
            if 'value' in item:
                return False, (
                    f"{context}: choice_list[{i}] використовує застарілий ключ 'value'\n\n"
                    f"💡 Новий формат (v2.69.0+):\n"
                    f"    - v: \"{item.get('value', '')}\"     # замість 'value'\n"
                    f"      ru: \"...\"                        # замість 'presentation_ru'"
                )
            return False, (
                f"{context}: choice_list[{i}] відсутній обов'язковий ключ 'v' (value)"
            )

        # Перевірка наявності хоча б однієї мови
        has_lang = any(item.get(lang) for lang in ['ru', 'uk', 'en'])
        if not has_lang:
            # Можливо старий формат з 'presentation_ru'
            if item.get('presentation_ru') or item.get('presentation'):
                return False, (
                    f"{context}: choice_list[{i}] використовує застарілі ключі\n\n"
                    f"💡 Новий формат (v2.69.0+):\n"
                    f"    - v: \"{item.get('v', '')}\"     # value\n"
                    f"      ru: \"...\"                   # замість 'presentation_ru'"
                )
            return False, (
                f"{context}: choice_list[{i}] потрібен мінімум один ключ мови: ru, uk, або en"
            )

        # Перевірка що 'v' не порожній
        if not item.get('v') and item.get('v') != 0:  # 0 може бути валідним значенням
            return False, (
                f"{context}: choice_list[{i}] значення 'v' не може бути порожнім"
            )

    return True, ""


# ============================================
# PROPERTY VALIDATION (v2.69.0+)
# ============================================

# Valid enum values for element properties
VALID_HORIZONTAL_ALIGN = {"Left", "Right", "Center", "Auto"}
VALID_VERTICAL_ALIGN = {"Top", "Bottom", "Center", "Auto"}
VALID_TITLE_LOCATION = {"None", "Left", "Right", "Top", "Bottom", "Auto"}
VALID_GROUP_DIRECTION = {"Horizontal", "Vertical"}
VALID_REPRESENTATION = {"None", "NormalSeparation", "WeakSeparation", "StrongSeparation"}  # For Group
VALID_TABLE_REPRESENTATION = {"list", "tree"}  # For Table (v2.64.0+)
VALID_BUTTON_REPRESENTATION = {"Text", "Picture", "PictureAndText", "TextPicture"}  # v2.70.1+
VALID_POPUP_REPRESENTATION = {"Picture", "Text", "PictureAndText", "TextPicture", "Auto"}  # v2.70.1+
VALID_BEHAVIOR = {"Usual", "Collapsible"}
VALID_RADIO_BUTTON_TYPE = {"RadioButton", "Tumbler"}
VALID_PICTURE_SIZE = {"Proportionally", "Stretch", "AutoSize", "Tile", "RealSize"}
VALID_CHART_TYPE = {"Line", "Area", "StackedArea", "Bar", "Bar3D", "Pie", "Pie3D", "Doughnut", "Radar", "Stock", "Funnel"}

# v2.70.1+ - Additional enum validations
VALID_INITIAL_TREE_VIEW = {"no_expand", "expand_top_level", "expand_all_levels"}  # Table (tree mode)
VALID_CHOICE_MODE = {"QuickChoice", "Parameters", "BothWays"}  # InputField
VALID_CHOICE_FOLDERS_AND_ITEMS = {"Folders", "Items", "FoldersAndItems", "folders", "items", "folders_and_items"}  # InputField (both cases)
VALID_CHOICE_HISTORY_ON_INPUT = {"Auto", "DontUse", "UseAlways"}  # InputField
VALID_PAGES_REPRESENTATION = {"TabsOnTop", "TabsOnBottom", "TabsOnLeftHorizontal", "None"}  # Pages
VALID_STRETCH = {"No", "Horizontally", "Vertically", "HorizontalAndVertically"}  # SpreadSheetDocumentField
VALID_PLANNER_PERIOD = {"Day", "Week", "Month", "Year"}  # PlannerField
VALID_GROUP_LAYOUT = {"Horizontal", "Vertical"}  # ColumnGroup
VALID_WINDOW_OPENING_MODE = {"LockOwnerWindow", "LockWholeInterface", "Independent"}  # Form
VALID_COMMAND_BAR_LOCATION = {"None", "Top", "Bottom"}  # Form
VALID_TIME_SCALE = {"Hour", "Day", "Week", "Month"}  # PlannerField
VALID_TOOLTIP_REPRESENTATION = {"None", "Button", "ShowTop", "ShowBottom", "ShowLeft", "ShowRight", "Balloon", "ShowAuto"}  # All elements
VALID_CHOICE_BUTTON_REPRESENTATION = {"Auto", "ShowInInputField", "ShowInDropList", "ShowInDropListAndInInputField"}  # InputField

# Common misspellings and aliases
ENUM_ALIASES = {
    # horizontal_align
    "center": "Center", "middle": "Center", "left": "Left", "right": "Right",
    # vertical_align
    "top": "Top", "bottom": "Bottom",
    # title_location
    "none": "None", "above": "Top", "below": "Bottom",
    # group_direction
    "horizontal": "Horizontal", "vertical": "Vertical", "row": "Horizontal", "column": "Vertical",
    # representation
    "normal": "NormalSeparation", "weak": "WeakSeparation", "strong": "StrongSeparation",
    "border": "NormalSeparation", "frame": "NormalSeparation",
    # behavior
    "collapsible": "Collapsible", "expandable": "Collapsible", "collapse": "Collapsible",
    # radio_button_type
    "radio": "RadioButton", "tumbler": "Tumbler", "switch": "Tumbler", "toggle": "Tumbler",
    # picture_size
    "proportionally": "Proportionally", "stretch": "Stretch", "auto": "AutoSize",
    "fit": "Proportionally", "fill": "Stretch", "tile": "Tile",
}


def validate_enum(value: str, valid_values: set, property_name: str, context: str) -> Tuple[bool, str]:
    """
    Validates enum property value with fuzzy matching suggestions.

    Args:
        value: The value to validate
        valid_values: Set of valid enum values
        property_name: Property name (e.g., "horizontal_align")
        context: Context for error message

    Returns:
        (is_valid, error_message)
    """
    if not value:
        return True, ""

    # Check exact match
    if value in valid_values:
        return True, ""

    # Check aliases (common misspellings)
    if value.lower() in ENUM_ALIASES:
        suggested = ENUM_ALIASES[value.lower()]
        if suggested in valid_values:
            return False, (
                f"{context}: {property_name}=\"{value}\" невірне значення\n\n"
                f"💡 Можливо ви мали на увазі: {suggested}\n"
                f"   {property_name}: {suggested}"
            )

    # Fuzzy matching
    suggestions = get_close_matches(value, valid_values, n=3, cutoff=0.4)
    if suggestions:
        suggestions_str = ", ".join(suggestions)
        return False, (
            f"{context}: {property_name}=\"{value}\" невірне значення\n\n"
            f"💡 Схожі варіанти: {suggestions_str}\n"
            f"   Доступні: {', '.join(sorted(valid_values))}"
        )

    return False, (
        f"{context}: {property_name}=\"{value}\" невірне значення\n\n"
        f"💡 Доступні значення: {', '.join(sorted(valid_values))}"
    )


def validate_font(font, context: str) -> Tuple[bool, str]:
    """
    Validates font property format.

    Expected format:
        font:
          size: 16           # or height
          bold: true
          italic: false
          underline: false
          face_name: "Arial"

    Args:
        font: Font property value
        context: Context for error message

    Returns:
        (is_valid, error_message)
    """
    if not font:
        return True, ""

    if isinstance(font, str):
        return False, (
            f"{context}: font має бути об'єктом, отримано рядок \"{font}\"\n\n"
            f"💡 Правильний формат:\n"
            f"    font:\n"
            f"      size: 14\n"
            f"      bold: true"
        )

    if not isinstance(font, dict):
        return False, (
            f"{context}: font має бути об'єктом, отримано {type(font).__name__}"
        )

    valid_keys = {"size", "height", "bold", "italic", "underline", "strikethrough",
                  "scale", "face_name", "faceName", "kind", "ref"}
    unknown_keys = set(font.keys()) - valid_keys
    if unknown_keys:
        suggestions = []
        for key in unknown_keys:
            matches = get_close_matches(key, valid_keys, n=1, cutoff=0.5)
            if matches:
                suggestions.append(f"'{key}' → '{matches[0]}'")

        if suggestions:
            return False, (
                f"{context}: font містить невідомі ключі: {unknown_keys}\n\n"
                f"💡 Можливо ви мали на увазі: {', '.join(suggestions)}\n"
                f"   Доступні: {', '.join(sorted(valid_keys))}"
            )
        return False, (
            f"{context}: font містить невідомі ключі: {unknown_keys}\n\n"
            f"💡 Доступні ключі: {', '.join(sorted(valid_keys))}"
        )

    # Validate boolean fields
    for bool_key in ["bold", "italic", "underline", "strikethrough"]:
        if bool_key in font and not isinstance(font[bool_key], bool):
            return False, (
                f"{context}: font.{bool_key} має бути boolean (true/false), "
                f"отримано {type(font[bool_key]).__name__}"
            )

    return True, ""


def validate_color(color: str, property_name: str, context: str) -> Tuple[bool, str]:
    """
    Validates color in HEX format (#RRGGBB or #RGB).

    Args:
        color: Color value
        property_name: Property name (e.g., "text_color")
        context: Context for error message

    Returns:
        (is_valid, error_message)
    """
    if not color:
        return True, ""

    if not isinstance(color, str):
        return False, (
            f"{context}: {property_name} має бути рядком у форматі #RRGGBB, "
            f"отримано {type(color).__name__}"
        )

    # Named colors are not supported
    named_colors = {"red", "green", "blue", "white", "black", "yellow", "orange", "gray", "grey"}
    if color.lower() in named_colors:
        # Suggest HEX equivalents
        color_map = {
            "red": "#FF0000", "green": "#00FF00", "blue": "#0000FF",
            "white": "#FFFFFF", "black": "#000000", "yellow": "#FFFF00",
            "orange": "#FFA500", "gray": "#808080", "grey": "#808080"
        }
        hex_color = color_map.get(color.lower(), "#RRGGBB")
        return False, (
            f"{context}: {property_name}=\"{color}\" - іменовані кольори не підтримуються\n\n"
            f"💡 Використовуйте HEX формат: {hex_color}"
        )

    # Check HEX format
    import re
    if not re.match(r'^#([0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})$', color):
        return False, (
            f"{context}: {property_name}=\"{color}\" невірний формат кольору\n\n"
            f"💡 Використовуйте HEX формат:\n"
            f"    {property_name}: \"#RRGGBB\"   # повний (напр. #FF5500)\n"
            f"    {property_name}: \"#RGB\"      # скорочений (напр. #F50)"
        )

    return True, ""


def validate_shortcut(shortcut: str, context: str = "") -> Tuple[bool, str]:
    """
    Validates command shortcut format (v2.72.0+).

    Valid shortcuts:
    - F1-F12 (function keys)
    - Special keys: Insert, Delete, Escape, Home, End, PageUp, PageDown,
                    Tab, Enter, Backspace, Up, Down, Left, Right, Space
    - Modifier combinations: Ctrl+X, Alt+F4, Ctrl+Shift+S
    - WARNING: Single letters (A-Z) without modifiers can conflict with text input

    Args:
        shortcut: Shortcut string (e.g., "Ctrl+S", "F5", "Escape")
        context: Context for error message

    Returns:
        (is_valid, warning_message) - warning_message can contain ⚠️ for warnings
    """
    if not shortcut:
        return True, ""

    shortcut = shortcut.strip()

    # Valid F-keys (F1-F12)
    if re.match(r'^F([1-9]|1[0-2])$', shortcut):
        return True, ""

    # Valid special keys (without modifiers)
    if shortcut in VALID_SPECIAL_KEYS:
        return True, ""

    # Pattern for modifier combinations: Ctrl+X, Alt+F4, Ctrl+Shift+S
    modifier_pattern = r'^(Ctrl\+)?(Alt\+)?(Shift\+)?(.+)$'
    match = re.match(modifier_pattern, shortcut)

    if not match:
        return False, (
            f"{context}: shortcut=\"{shortcut}\" - невірний формат\n\n"
            f"💡 Валідні формати:\n"
            f"    F1-F12, Escape, Insert, Delete\n"
            f"    Ctrl+S, Alt+F4, Ctrl+Shift+S"
        )

    has_ctrl, has_alt, has_shift, key = match.groups()
    has_modifier = has_ctrl or has_alt or has_shift

    # Validate the key part
    if key not in VALID_KEY_NAMES:
        # Check for common mistakes
        suggestions = get_close_matches(key, VALID_KEY_NAMES, n=3, cutoff=0.4)
        if suggestions:
            return False, (
                f"{context}: shortcut=\"{shortcut}\" - невідома клавіша '{key}'\n\n"
                f"💡 Схожі: {', '.join(suggestions)}"
            )
        return False, (
            f"{context}: shortcut=\"{shortcut}\" - невідома клавіша '{key}'\n\n"
            f"💡 Валідні клавіші: F1-F12, A-Z, 0-9, Insert, Delete, Escape, Home, End, "
            f"PageUp, PageDown, Tab, Enter, Backspace, Up, Down, Left, Right, Space"
        )

    # Warning for single letters without modifiers
    # This can conflict with text input in InputFields
    single_letters = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    if not has_modifier and key in single_letters:
        return True, (
            f"⚠️ {context}: shortcut=\"{shortcut}\" - одиночна клавіша "
            f"може конфліктувати з вводом тексту в InputField. "
            f"Рекомендуємо: Ctrl+{key} або F1-F12."
        )

    return True, ""


def validate_conditional_appearance(ca: dict, index: int, context: str) -> Tuple[bool, str]:
    """
    Validates conditional_appearance structure.

    Expected format:
        conditional_appearances:
          - filter:
              field: "Статус"
              comparison: Equal
              value: "Ошибка"
            appearance:
              text_color: "#FF0000"

    Args:
        ca: Conditional appearance item
        index: Item index
        context: Context for error message

    Returns:
        (is_valid, error_message)
    """
    if not ca:
        return True, ""

    if not isinstance(ca, dict):
        return False, (
            f"{context}: conditional_appearances[{index}] має бути об'єктом, "
            f"отримано {type(ca).__name__}"
        )

    # Check required keys
    if 'filter' not in ca and 'appearance' not in ca:
        return False, (
            f"{context}: conditional_appearances[{index}] потрібен 'filter' або 'appearance'\n\n"
            f"💡 Формат:\n"
            f"    conditional_appearances:\n"
            f"      - filter:\n"
            f"          field: \"Статус\"\n"
            f"          comparison: Equal\n"
            f"          value: \"Ошибка\"\n"
            f"        appearance:\n"
            f"          text_color: \"#FF0000\""
        )

    # Validate filter
    if 'filter' in ca:
        flt = ca['filter']
        if not isinstance(flt, dict):
            return False, (
                f"{context}: conditional_appearances[{index}].filter має бути об'єктом"
            )

        valid_comparisons = {"Equal", "NotEqual", "Greater", "GreaterOrEqual",
                           "Less", "LessOrEqual", "Contains", "InList", "Filled"}
        if 'comparison' in flt and flt['comparison'] not in valid_comparisons:
            suggestions = get_close_matches(flt['comparison'], valid_comparisons, n=2, cutoff=0.4)
            if suggestions:
                return False, (
                    f"{context}: conditional_appearances[{index}].filter.comparison=\"{flt['comparison']}\" невірне\n\n"
                    f"💡 Можливо: {', '.join(suggestions)}\n"
                    f"   Доступні: {', '.join(sorted(valid_comparisons))}"
                )
            return False, (
                f"{context}: conditional_appearances[{index}].filter.comparison=\"{flt['comparison']}\" невірне\n\n"
                f"💡 Доступні: {', '.join(sorted(valid_comparisons))}"
            )

    # Validate appearance
    if 'appearance' in ca:
        app = ca['appearance']
        if not isinstance(app, dict):
            return False, (
                f"{context}: conditional_appearances[{index}].appearance має бути об'єктом"
            )

        # Validate colors in appearance
        for color_key in ['text_color', 'back_color', 'border_color']:
            if color_key in app:
                is_valid, error = validate_color(
                    app[color_key],
                    f"appearance.{color_key}",
                    f"{context}: conditional_appearances[{index}]"
                )
                if not is_valid:
                    return False, error

    return True, ""


def validate_handler_name(handler_name: str) -> Tuple[bool, str]:
    """
    Перевіряє чи ім'я handler/процедури не є зарезервованим словом BSL або вбудованим методом форми

    Args:
        handler_name: Ім'я обробника (використовується як ім'я процедури)

    Returns:
        (True, "") якщо валідне
        (False, "повідомлення про помилку") якщо зарезервоване слово або конфліктує з вбудованим методом
    """
    if not handler_name:
        return True, ""  # Handler опціональний

    # Перевірка чи є зарезервованим словом BSL (регістронезалежно)
    if handler_name in BSL_RESERVED_KEYWORDS:
        return False, (
            f"Ім'я обробника '{handler_name}' є зарезервованим ключовим словом BSL і не може "
            f"використовуватися як ім'я процедури. "
            f"Використовуйте інше ім'я, наприклад: 'Команда{handler_name}', '{handler_name}Команда', "
            f"'{handler_name}Обработчик', тощо."
        )

    # Перевірка чи є вбудованим методом форми (регістронезалежно)
    if handler_name in FORM_BUILTIN_METHODS:
        return False, (
            f"Ім'я обробника '{handler_name}' конфліктує з вбудованим методом керованої форми 1C і не може "
            f"використовуватися як ім'я процедури. "
            f"Використовуйте інше ім'я, наприклад: '{handler_name}Форму', '{handler_name}Обработчик', "
            f"'Команда{handler_name}', тощо."
        )

    return True, ""


def validate_reserved_metadata_name(name: str, object_type: str = "об'єкт") -> Tuple[bool, str]:
    """
    Перевіряє чи ім'я не є зарезервованим системним іменем метаданих 1C

    Args:
        name: Ім'я для перевірки
        object_type: Тип об'єкта (для повідомлення про помилку)

    Returns:
        (True, "") якщо валідне
        (False, "повідомлення про помилку") якщо зарезервоване
    """
    if not name:
        return True, ""

    # Перевірка регістронезалежно
    if name in RESERVED_METADATA_NAMES:
        return False, (
            f"Ім'я '{name}' є зарезервованим системним іменем метаданих 1C і не може "
            f"використовуватися як ім'я {object_type}а. "
            f"Використовуйте інше ім'я, наприклад: '{name}Список', 'Мои{name}', "
            f"'{name}Таблица', тощо."
        )

    return True, ""


class ProcessorValidator:
    """Валідатор для повної перевірки обробки"""

    def __init__(self, processor):
        self.processor = processor
        self.errors = []
        self.warnings = []

    def _validate_name_and_reserved(self, name: str, context: str, object_type: str = "об'єкт") -> None:
        """
        Універсальний метод валідації імені та перевірки на зарезервовані слова

        Args:
            name: Ім'я для валідації
            context: Контекст для повідомлення про помилку (напр. "Атрибут 'Name'")
            object_type: Тип об'єкта для перевірки reserved names
        """
        is_valid, error = validate_identifier(name)
        if not is_valid:
            self.errors.append(f"{context}: {error}")

        is_valid, error = validate_reserved_metadata_name(name, object_type)
        if not is_valid:
            self.errors.append(f"{context}: {error}")

    def _validate_column(self, col_name: str, col_type: str, context: str) -> None:
        """
        Універсальний метод валідації колонки (ім'я + тип)

        Args:
            col_name: Ім'я колонки
            col_type: Тип колонки
            context: Контекст для повідомлення про помилку
        """
        is_valid, error = validate_identifier(col_name)
        if not is_valid:
            self.errors.append(f"{context}: {error}")

        is_valid, error = validate_type(col_type)
        if not is_valid:
            self.errors.append(f"{context}: {error}")

    def _validate_handler(self, handler_name: str, context: str) -> None:
        """
        Універсальний метод валідації handler name

        Args:
            handler_name: Ім'я handler
            context: Контекст для повідомлення про помилку
        """
        is_valid, error = validate_handler_name(handler_name)
        if not is_valid:
            self.errors.append(f"{context}: {error}")

    def _validate_long_operations(self) -> None:
        """
        Валідація long operation команд (v3.0.0+).

        Перевірки:
        - timeout_seconds в діапазоні 1-3600
        - progress_message not empty якщо show_progress=True
        - Попередження якщо long_operation=True але немає форм/кнопок
        """
        for form in self.processor.forms:
            for cmd in form.commands:
                if not cmd.long_operation:
                    continue

                context = f"Форма '{form.name}' - Long operation команда '{cmd.name}'"
                settings = cmd.long_operation_settings

                # Validate timeout_seconds
                if settings and settings.timeout_seconds:
                    if settings.timeout_seconds < 1:
                        self.errors.append(f"{context}: timeout_seconds має бути >= 1 (поточне: {settings.timeout_seconds})")
                    elif settings.timeout_seconds > 3600:
                        self.errors.append(f"{context}: timeout_seconds надто великий (max 3600, поточне: {settings.timeout_seconds})")

                # Validate progress_message
                if settings and settings.show_progress:
                    msg = settings.progress_message
                    # Handle both string and multilang dict formats
                    is_empty = not msg or (isinstance(msg, str) and msg.strip() == "") or (isinstance(msg, dict) and not any(msg.values()))
                    if is_empty:
                        self.warnings.append(f"{context}: show_progress=True але progress_message порожній")

                # Check if there's a button for this command
                has_button = any(
                    elem.element_type == "Button" and elem.command == cmd.name
                    for elem in form.elements
                )
                if not has_button:
                    self.warnings.append(
                        f"{context}: long_operation=True але немає Button на формі. "
                        f"Додайте Button з command='{cmd.name}' для виклику операції."
                    )

    def validate(self) -> Tuple[bool, List[str], List[str]]:
        """
        Повна валідація обробки

        Returns:
            (True/False, список помилок, список попереджень)
        """
        self.errors = []
        self.warnings = []

        # Перевірка назви
        is_valid, error = validate_processor_name(self.processor.name)
        if not is_valid:
            self.errors.append(f"Назва обробки: {error}")

        # Перевірка UUID
        all_uuids = [
            self.processor.main_uuid,
            self.processor.object_id,
            self.processor.type_id,
            self.processor.value_id,
            self.processor.form_uuid,
        ]

        # Додаємо UUID атрибутів
        for attr in self.processor.attributes:
            all_uuids.append(attr.uuid)

        # Додаємо UUID табличних частин
        for ts in self.processor.tabular_sections:
            all_uuids.extend([
                ts.uuid,
                ts.type_id,
                ts.value_id,
                ts.row_type_id,
                ts.row_value_id,
            ])
            for col in ts.columns:
                all_uuids.append(col.uuid)

        # Додаємо UUID команд та форм
        for form in self.processor.forms:
            all_uuids.append(form.uuid)
            # Додаємо UUID команд форми
            for cmd in form.commands:
                all_uuids.append(cmd.uuid)

        uuid_errors = validate_all_uuids(all_uuids)
        self.errors.extend(uuid_errors)

        # Перевірка атрибутів
        for attr in self.processor.attributes:
            self._validate_name_and_reserved(attr.name, f"Атрибут '{attr.name}'", "атрибут")

            is_valid, error = validate_type(attr.type)
            if not is_valid:
                self.errors.append(f"Атрибут '{attr.name}': {error}")

        # Перевірка табличних частин
        for ts in self.processor.tabular_sections:
            self._validate_name_and_reserved(ts.name, f"Таблична частина '{ts.name}'", "таблична частин")

            for col in ts.columns:
                self._validate_column(col.name, col.type, f"Колонка '{ts.name}.{col.name}'")

        # Перевірка ValueTable атрибутів (у формах)
        for form in self.processor.forms:
            for vt in form.value_table_attributes:
                self._validate_name_and_reserved(vt.name, f"Форма '{form.name}' - ValueTable '{vt.name}'", "ValueTable атрибут")

                for col in vt.columns:
                    self._validate_column(col.name, col.type, f"Форма '{form.name}' - ValueTable колонка '{vt.name}.{col.name}'")

        # Перевірка DynamicList атрибутів (у формах)
        for form in self.processor.forms:
            for dl in form.dynamic_list_attributes:
                self._validate_name_and_reserved(dl.name, f"Форма '{form.name}' - DynamicList '{dl.name}'", "DynamicList атрибут")

                # Перевірка use_always_fields - має бути Table на формі
                if dl.use_always_fields:
                    # Шукаємо Table на формі з цим DynamicList
                    has_table = any(
                        elem.element_type == "Table"
                        and elem.properties.get("is_dynamic_list", False)
                        and elem.tabular_section == dl.name
                        for elem in form.elements
                    )
                    if not has_table:
                        self.warnings.append(
                            f"Форма '{form.name}' - DynamicList '{dl.name}': use_always_fields визначено, але немає Table "
                            f"на формі для відображення цього списку. UseAlways буде проігноровано."
                        )

        # Перевірка картинок в командах та елементах (у формах)
        for form in self.processor.forms:
            # Перевірка елементів форми
            for elem in form.elements:
                # Popup в form.elements буде проігноровано (має бути в auto_command_bar)
                if elem.element_type == "Popup":
                    self.warnings.append(
                        f"Форма '{form.name}' - Елемент '{elem.name}': Popup в form.elements буде проігноровано. "
                        "Використовуйте form.auto_command_bar для Popup елементів."
                    )

                # SVG source validation (v2.23.0+)
                if 'svg_source' in elem.properties:
                    svg_path = elem.properties['svg_source']
                    context = f"Форма '{form.name}' - Елемент '{elem.name}'"

                    # Check if file exists (relative to config.yaml or absolute)
                    from pathlib import Path
                    svg_file = Path(svg_path)
                    if not svg_file.is_absolute():
                        # Try relative to config_dir if available
                        if hasattr(self.processor, 'config_dir') and self.processor.config_dir:
                            svg_file = Path(self.processor.config_dir) / svg_path

                    if not svg_file.exists():
                        self.errors.append(f"{context}: SVG file not found: {svg_path}")
                    else:
                        # Validate SVG structure
                        try:
                            from .svg_converter import SVGConverter
                            converter = SVGConverter()
                            converter.validate_svg(str(svg_file))
                        except Exception as e:
                            self.errors.append(f"{context}: Invalid SVG file: {e}")

            # Перевірка картинок в командах
            for cmd in form.commands:
                if hasattr(cmd, 'picture') and cmd.picture:
                    is_valid, error = validate_picture(cmd.picture)
                    if not is_valid:
                        self.errors.append(f"Форма '{form.name}' - Команда '{cmd.name}': {error}")

            # Перевірка картинок в елементах форми (PictureDecoration, Button) (v2.46.0+)
            self._validate_element_pictures(form.elements, form.name)

            # Перевірка choice_list в елементах форми (v2.69.0+)
            self._validate_element_choice_lists(form.elements, form.name)

            # Перевірка властивостей елементів (enum, font, color, conditional_appearances) (v2.69.0+)
            self._validate_element_properties(form.elements, form.name)

            # Перевірка form-level conditional_appearances (v2.68.0+)
            if hasattr(form, 'conditional_appearances') and form.conditional_appearances:
                context = f"Форма '{form.name}'"
                for i, ca in enumerate(form.conditional_appearances):
                    # ca is ConditionalAppearanceItem dataclass - validate its appearance colors
                    if hasattr(ca, 'appearance') and ca.appearance:
                        app = ca.appearance
                        for color_attr in ['text_color', 'back_color', 'border_color']:
                            color_val = getattr(app, color_attr, None)
                            if color_val:
                                is_valid, error = validate_color(
                                    color_val, color_attr,
                                    f"{context}: conditional_appearances[{i}].appearance"
                                )
                                if not is_valid:
                                    self.errors.append(error)

        # Перевірка long operation команд (v3.0.0+)
        self._validate_long_operations()

        # Перевірка картинок і команд у формах (continue)
        for form in self.processor.forms:
            # Перевірка картинок в AutoCommandBar (Popup елементи)
            if hasattr(form, 'auto_command_bar') and form.auto_command_bar:
                for elem in form.auto_command_bar:
                    if elem.element_type == "Popup" and hasattr(elem, 'picture') and elem.picture:
                        is_valid, error = validate_picture(elem.picture)
                        if not is_valid:
                            self.errors.append(f"Форма '{form.name}' - Popup '{elem.name}': {error}")

        # Валідація forms
        # Перевірка унікальності імен форм
        form_names = [form.name for form in self.processor.forms]
        if len(form_names) != len(set(form_names)):
            duplicates = [name for name in form_names if form_names.count(name) > 1]
            self.errors.append(
                f"Знайдено дублікати імен форм: {set(duplicates)}. "
                f"Кожна форма повинна мати унікальне ім'я."
            )

        # Перевірка default форм
        default_forms = [form for form in self.processor.forms if form.default]
        if len(default_forms) == 0:
            self.warnings.append(
                "Жодна форма не позначена як default=True. "
                "Рекомендується позначити одну форму як default."
            )
        elif len(default_forms) > 1:
            default_names = [form.name for form in default_forms]
            self.errors.append(
                f"Декілька форм позначені як default=True: {default_names}. "
                f"Тільки одна форма може бути default."
            )

        # Валідація form-level enum властивостей (v2.70.1+)
        for form in self.processor.forms:
            context = f"Форма '{form.name}'"

            # WindowOpeningMode validation
            if hasattr(form, 'window_opening_mode') and form.window_opening_mode:
                is_valid, error = validate_enum(
                    form.window_opening_mode, VALID_WINDOW_OPENING_MODE,
                    'window_opening_mode', context
                )
                if not is_valid:
                    self.errors.append(error)

            # CommandBarLocation validation
            if hasattr(form, 'command_bar_location') and form.command_bar_location:
                is_valid, error = validate_enum(
                    form.command_bar_location, VALID_COMMAND_BAR_LOCATION,
                    'command_bar_location', context
                )
                if not is_valid:
                    self.errors.append(error)

        # Перевірка handlers_dir (чи існує директорія)
        from pathlib import Path
        for form in self.processor.forms:
            if form.handlers_dir:
                handlers_path = Path(form.handlers_dir)
                if not handlers_path.exists():
                    self.errors.append(
                        f"Форма '{form.name}': handlers_dir не існує: {form.handlers_dir}"
                    )
                elif not handlers_path.is_dir():
                    self.errors.append(
                        f"Форма '{form.name}': handlers_dir не є директорією: {form.handlers_dir}"
                    )

        # Перевірка handlers_file (чи існує файл) - v2.69.0+
        for form in self.processor.forms:
            if form.handlers_file:
                handlers_file_path = Path(form.handlers_file)
                if not handlers_file_path.exists():
                    self.errors.append(
                        f"Форма '{form.name}': handlers_file не існує: {form.handlers_file}"
                    )
                elif not handlers_file_path.is_file():
                    self.errors.append(
                        f"Форма '{form.name}': handlers_file не є файлом: {form.handlers_file}"
                    )

        for form in self.processor.forms:
            # Валідація команд форми
            for cmd in form.commands:
                # Перевірка чи не є команда стандартною (v2.15.1+)
                from .constants import STANDARD_FORM_COMMANDS
                if cmd.name in STANDARD_FORM_COMMANDS:
                    self.errors.append(
                        f"Форма '{form.name}' - Команда '{cmd.name}': не можна визначати стандартні команди 1C "
                        f"({', '.join(sorted(STANDARD_FORM_COMMANDS))}). "
                        f"Стандартні команди доступні автоматично і не потребують визначення."
                    )

                self._validate_handler(cmd.action, f"Форма '{form.name}' - Команда '{cmd.name}'")

                # v2.72.0+: Валідація shortcut команди
                if hasattr(cmd, 'shortcut') and cmd.shortcut:
                    is_valid, message = validate_shortcut(
                        cmd.shortcut,
                        f"Форма '{form.name}' - Команда '{cmd.name}'"
                    )
                    if not is_valid:
                        self.errors.append(message)
                    elif message:  # Warning (starts with ⚠️)
                        self.warnings.append(message)

            # Валідація подій форми
            for event_name, handler_name in form.events.items():
                self._validate_handler(handler_name, f"Форма '{form.name}' - Подія '{event_name}'")

            # Валідація подій елементів форми
            for elem in form.elements:
                if hasattr(elem, 'event_handlers') and elem.event_handlers:
                    for event_name, handler_name in elem.event_handlers.items():
                        self._validate_handler(handler_name, f"Форма '{form.name}' - Елемент '{elem.name}.{event_name}'")

        # Валідація ObjectModule
        om_errors, om_warnings = self._validate_object_module()
        self.errors.extend(om_errors)
        self.warnings.extend(om_warnings)

        # Валідація Form Modules (v2.16.0+)
        fm_errors, fm_warnings = self._validate_form_modules()
        self.errors.extend(fm_errors)
        self.warnings.extend(fm_warnings)

        # Попередження
        if not self.processor.attributes and not self.processor.tabular_sections:
            self.warnings.append("Обробка не має жодного реквізиту або табличної частини")

        # Перевірка чи є хоча б одна форма з елементами
        has_any_elements = any(form.elements for form in self.processor.forms)
        if not has_any_elements:
            self.warnings.append("Форма не має жодного елемента")

        # v2.69.0+: Валідація посилань attribute в елементах форми
        ref_errors = self._validate_form_element_references()
        self.errors.extend(ref_errors)

        return len(self.errors) == 0, self.errors, self.warnings

    def _validate_form_element_references(self) -> List[str]:
        """
        v2.69.3+: Валідація посилань attribute в елементах форми.

        Перевіряє що:
        - InputField.attribute посилається на існуючий атрибут:
          - processor.attributes (processor-level)
          - form.form_attributes (form-level)

        Returns:
            Список помилок
        """
        errors = []
        processor_attrs = {a.name for a in self.processor.attributes}

        for form in self.processor.forms:
            # Collect form-level attributes
            form_attrs = set()
            if hasattr(form, 'form_attributes') and form.form_attributes:
                form_attrs = {a.name for a in form.form_attributes}

            # Combine processor + form level attributes
            valid_attrs = processor_attrs | form_attrs

            errors.extend(self._check_element_attribute_refs(
                form.elements,
                form.name,
                valid_attrs
            ))

        return errors

    def _check_element_attribute_refs(
        self,
        elements,
        form_name: str,
        valid_attrs: set
    ) -> List[str]:
        """
        Рекурсивно перевіряє attribute посилання в елементах форми.

        Args:
            elements: Список елементів форми
            form_name: Назва форми для повідомлень
            valid_attrs: Набір валідних імен атрибутів

        Returns:
            Список помилок
        """
        errors = []
        if not elements:
            return errors

        for elem in elements:
            # Перевіряємо attribute посилання
            if hasattr(elem, 'attribute') and elem.attribute:
                if elem.attribute not in valid_attrs:
                    errors.append(
                        f"Form '{form_name}', {elem.element_type} '{elem.name}': "
                        f"attribute '{elem.attribute}' not found in processor.attributes"
                    )

            # Рекурсивно перевіряємо child_items
            if hasattr(elem, 'child_items') and elem.child_items:
                errors.extend(self._check_element_attribute_refs(
                    elem.child_items,
                    form_name,
                    valid_attrs
                ))

        return errors

    def _validate_bsl_code(self, code: str, module_name: str) -> Tuple[List[str], List[str]]:
        """
        Валідує BSL код (універсальна функція для ObjectModule та FormModule)

        Перевірки:
        - BSL reserved keywords (критична помилка)
        - Українські літери в назвах процедур/функцій (критична помилка)

        Args:
            code: BSL код для перевірки
            module_name: Назва модулю для повідомлень (e.g., "ObjectModule", "Форма.Форма")

        Returns:
            (errors, warnings)
        """
        errors = []
        warnings = []

        if not code or not code.strip():
            return errors, warnings

        # Витягуємо всі назви процедур/функцій
        pattern = re.compile(
            r'^\s*(?:&\w+\s+)?(?:Процедура|Функция|Procedure|Function|Асинх|Async)\s+(\w+)',
            re.MULTILINE | re.IGNORECASE
        )
        procedures = pattern.findall(code)

        # Перевірка на BSL reserved keywords
        for proc_name in procedures:
            if proc_name in BSL_RESERVED_KEYWORDS:
                errors.append(
                    f"{module_name}: процедура '{proc_name}' конфліктує з зарезервованим словом BSL"
                )

        # Перевірка на українські літери в назвах процедур/функцій
        # Тільки українські унікальні літери: і, ї, є, ґ (та їх великі версії)
        ukrainian_pattern = re.compile(r'[іІїЇєЄґҐ]')
        for proc_name in procedures:
            if ukrainian_pattern.search(proc_name):
                errors.append(
                    f"{module_name}: процедура '{proc_name}' містить українські літери (і, ї, є, ґ). "
                    f"Використовуйте тільки латиницю або російську кирилицю для назв процедур."
                )

        return errors, warnings

    def _validate_object_module(self) -> Tuple[List[str], List[str]]:
        """
        Валідує ObjectModule.bsl

        Перевірки:
        - Порожній файл (критична помилка)
        - BSL reserved keywords (критична помилка)
        - Українські літери в назвах процедур/функцій (критична помилка)
        - Відсутність умовної компіляції #Если Сервер (попередження)
        - Відсутність регіонів (попередження)

        Returns:
            (errors, warnings)
        """
        errors = []
        warnings = []

        if not self.processor.object_module_bsl:
            return errors, warnings

        code = self.processor.object_module_bsl

        # 1. Перевірка що не порожній
        if not code.strip():
            errors.append("ObjectModule.bsl порожній")
            return errors, warnings

        # 2. Валідація BSL коду (reserved keywords, українські літери)
        bsl_errors, bsl_warnings = self._validate_bsl_code(code, "ObjectModule")
        errors.extend(bsl_errors)
        warnings.extend(bsl_warnings)

        # 3. Попередження якщо немає обгортки #Если Сервер
        if "#Если" not in code and "#If" not in code:
            warnings.append(
                "ObjectModule: немає умовної компіляції (#Если Сервер Або ТолстыйКлиентОбычноеПриложение Или ВнешнееСоединение Тогда). "
                "Рекомендується додати для коректної роботи."
            )

        # 4. Попередження якщо немає регіонів
        if "#Область" not in code and "#Region" not in code:
            warnings.append(
                "ObjectModule: немає регіонів (#Область). "
                "Рекомендується структурувати код за регіонами (#Область ПрограммныйИнтерфейс, #Область СлужебныеПроцедурыИФункции)."
            )

        return errors, warnings

    def _validate_element_pictures(self, elements, form_name: str, parent_path: str = "") -> None:
        """
        Рекурсивно валідує картинки в елементах форми (v2.46.0+)

        Перевіряє:
        - PictureDecoration.picture
        - Button.picture (якщо явно задано)

        Args:
            elements: Список елементів форми
            form_name: Ім'я форми (для повідомлень про помилки)
            parent_path: Шлях до батьківського елемента
        """
        if not elements:
            return

        for elem in elements:
            elem_path = f"{parent_path}/{elem.name}" if parent_path else elem.name

            # Перевірка картинки в PictureDecoration та Button
            if elem.element_type in ("PictureDecoration", "Button"):
                picture = elem.properties.get('picture') if elem.properties else None
                if picture:
                    is_valid, error = validate_picture(picture)
                    if not is_valid:
                        self.errors.append(f"Форма '{form_name}' - {elem.element_type} '{elem_path}': {error}")

            # Рекурсія для дочірніх елементів (включаючи Page)
            if elem.child_items:
                self._validate_element_pictures(elem.child_items, form_name, elem_path)

    def _validate_element_choice_lists(self, elements, form_name: str, parent_path: str = "") -> None:
        """
        Рекурсивно валідує choice_list в елементах форми (v2.69.0+)

        Перевіряє:
        - InputField.choice_list
        - RadioButtonField.choice_list

        Args:
            elements: Список елементів форми
            form_name: Ім'я форми (для повідомлень про помилки)
            parent_path: Шлях до батьківського елемента
        """
        if not elements:
            return

        for elem in elements:
            elem_path = f"{parent_path}/{elem.name}" if parent_path else elem.name

            # Перевірка choice_list в InputField та RadioButtonField
            if elem.element_type in ("InputField", "RadioButtonField"):
                choice_list = elem.properties.get('choice_list') if elem.properties else None
                if choice_list:
                    context = f"Форма '{form_name}' - {elem.element_type} '{elem_path}'"
                    is_valid, error = validate_choice_list(choice_list, context)
                    if not is_valid:
                        self.errors.append(error)

            # Рекурсія для дочірніх елементів
            if elem.child_items:
                self._validate_element_choice_lists(elem.child_items, form_name, elem_path)

    def _validate_element_properties(self, elements, form_name: str, parent_path: str = "") -> None:
        """
        Рекурсивно валідує властивості елементів форми (v2.69.0+)

        Перевіряє:
        - Enum properties (horizontal_align, vertical_align, title_location, etc.)
        - Font properties
        - Color properties (text_color, back_color, border_color)
        - conditional_appearances

        Args:
            elements: Список елементів форми
            form_name: Ім'я форми (для повідомлень про помилки)
            parent_path: Шлях до батьківського елемента
        """
        if not elements:
            return

        for elem in elements:
            elem_path = f"{parent_path}/{elem.name}" if parent_path else elem.name
            context = f"Форма '{form_name}' - {elem.element_type} '{elem_path}'"
            props = elem.properties or {}

            # === Enum validations ===
            enum_checks = [
                ('horizontal_align', VALID_HORIZONTAL_ALIGN),
                ('vertical_align', VALID_VERTICAL_ALIGN),
                ('title_location', VALID_TITLE_LOCATION),
                ('group_direction', VALID_GROUP_DIRECTION),
                ('behavior', VALID_BEHAVIOR),
                ('radio_button_type', VALID_RADIO_BUTTON_TYPE),
                ('picture_size', VALID_PICTURE_SIZE),
                # v2.70.1+ - Additional enum validations
                ('initial_tree_view', VALID_INITIAL_TREE_VIEW),
                ('choice_mode', VALID_CHOICE_MODE),
                ('choice_folders_and_items', VALID_CHOICE_FOLDERS_AND_ITEMS),
                ('choice_history_on_input', VALID_CHOICE_HISTORY_ON_INPUT),
                ('stretch', VALID_STRETCH),
                ('period', VALID_PLANNER_PERIOD),
                ('group_layout', VALID_GROUP_LAYOUT),
                ('time_scale', VALID_TIME_SCALE),
                ('tooltip_representation', VALID_TOOLTIP_REPRESENTATION),
                ('choice_button_representation', VALID_CHOICE_BUTTON_REPRESENTATION),
            ]
            for prop_name, valid_values in enum_checks:
                if prop_name in props:
                    is_valid, error = validate_enum(
                        props[prop_name], valid_values, prop_name, context
                    )
                    if not is_valid:
                        self.errors.append(error)

            # === Representation validation (element-type-specific) ===
            if 'representation' in props:
                if elem.element_type == 'Table':
                    valid_repr = VALID_TABLE_REPRESENTATION
                elif elem.element_type == 'Button':
                    valid_repr = VALID_BUTTON_REPRESENTATION
                elif elem.element_type == 'Popup':
                    valid_repr = VALID_POPUP_REPRESENTATION
                elif elem.element_type == 'UsualGroup':
                    valid_repr = VALID_REPRESENTATION
                else:
                    # PlannerField and other elements - skip validation
                    valid_repr = None

                if valid_repr is not None:
                    is_valid, error = validate_enum(
                        props['representation'], valid_repr, 'representation', context
                    )
                    if not is_valid:
                        self.errors.append(error)

            # === Pages-specific validation ===
            if 'pages_representation' in props:
                is_valid, error = validate_enum(
                    props['pages_representation'], VALID_PAGES_REPRESENTATION, 'pages_representation', context
                )
                if not is_valid:
                    self.errors.append(error)

            # === Font validation ===
            if 'font' in props:
                is_valid, error = validate_font(props['font'], context)
                if not is_valid:
                    self.errors.append(error)

            # === Color validations ===
            color_props = ['text_color', 'back_color', 'border_color']
            for color_prop in color_props:
                if color_prop in props:
                    is_valid, error = validate_color(
                        props[color_prop], color_prop, context
                    )
                    if not is_valid:
                        self.errors.append(error)

            # === Element-level conditional appearances validation ===
            if hasattr(elem, 'conditional_appearances') and elem.conditional_appearances:
                for i, ca in enumerate(elem.conditional_appearances):
                    # ca is ConditionalAppearanceItem dataclass - validate its appearance colors
                    if hasattr(ca, 'appearance') and ca.appearance:
                        app = ca.appearance
                        for color_attr in ['text_color', 'back_color', 'border_color']:
                            color_val = getattr(app, color_attr, None)
                            if color_val:
                                is_valid, error = validate_color(
                                    color_val, color_attr,
                                    f"{context}: conditional_appearances[{i}].appearance"
                                )
                                if not is_valid:
                                    self.errors.append(error)

            # Рекурсія для дочірніх елементів
            if elem.child_items:
                self._validate_element_properties(elem.child_items, form_name, elem_path)

    def _validate_form_modules(self) -> Tuple[List[str], List[str]]:
        """
        Валідує Form Module BSL для всіх форм

        Перевірки:
        - BSL reserved keywords (критична помилка)
        - Українські літери в назвах процедур/функцій (критична помилка)

        Returns:
            (errors, warnings)
        """
        errors = []
        warnings = []

        for form in self.processor.forms:
            module_name = f"Форма.{form.name}"

            # Перевіряємо BSL код подій форми (events_bsl)
            if hasattr(form, 'events_bsl') and form.events_bsl:
                for event_name, event_code in form.events_bsl.items():
                    bsl_errors, bsl_warnings = self._validate_bsl_code(
                        event_code,
                        f"{module_name}.{event_name}"
                    )
                    errors.extend(bsl_errors)
                    warnings.extend(bsl_warnings)

            # Перевіряємо BSL код команд
            for cmd in form.commands:
                if hasattr(cmd, 'bsl_code') and cmd.bsl_code:
                    bsl_errors, bsl_warnings = self._validate_bsl_code(
                        cmd.bsl_code,
                        f"{module_name}.Команда.{cmd.name}"
                    )
                    errors.extend(bsl_errors)
                    warnings.extend(bsl_warnings)

            # Перевіряємо helper procedures якщо є (helper_procedures Dict)
            if hasattr(form, 'helper_procedures') and form.helper_procedures:
                for proc_name, proc_code in form.helper_procedures.items():
                    bsl_errors, bsl_warnings = self._validate_bsl_code(
                        proc_code,
                        f"{module_name}.Helper.{proc_name}"
                    )
                    errors.extend(bsl_errors)
                    warnings.extend(bsl_warnings)

        return errors, warnings


class HandlerValidator:
    """
    Валідатор для перевірки BSL handlers (v2.48.0+, extended v2.71.5+)

    Перевіряє:
    1. Handler name match - handlers в config.yaml мають існувати в handlers.bsl
    2. Full signatures - handlers мають мати правильну структуру (директива + Процедура/Функция)
    3. Form-level access - попередження про неправильний доступ через Объект.:
       - ValueTable (value_tables) - доступ напряму TableName
       - form_attributes (SpreadsheetDocument, BinaryData, HTMLDocument) - доступ напряму AttrName
    """

    # Regex для виявлення сигнатури процедури/функції
    SIGNATURE_PATTERN = re.compile(
        r'^(\s*&\w+\s*\n)?\s*(Процедура|Функция|Procedure|Function|Асинх|Async)\s+(\w+)',
        re.MULTILINE | re.IGNORECASE
    )

    # Regex для виявлення директив
    DIRECTIVE_PATTERN = re.compile(
        r'^\s*&(НаКлиенте|НаСервере|НаСервереБезКонтекста|НаКлиентеНаСервереБезКонтекста|'
        r'OnClient|OnServer|AtServerNoContext|AtClientAtServerNoContext)',
        re.MULTILINE | re.IGNORECASE
    )

    # Regex для виявлення закриваючого тегу
    END_PROCEDURE_PATTERN = re.compile(
        r'(КонецПроцедуры|КонецФункции|EndProcedure|EndFunction)',
        re.IGNORECASE
    )

    # Regex для виявлення доступу до ValueTable через Объект.TableName
    # Шукаємо: Объект.TableName або Объект["TableName"]
    OBJECT_ACCESS_PATTERN = re.compile(
        r'Объект\.(\w+)|Объект\["(\w+)"\]',
        re.IGNORECASE
    )

    def __init__(
        self,
        processor,
        loaded_handlers: Optional[Dict[str, str]] = None,
        handlers_file: Optional[Path] = None,
    ):
        """
        Args:
            processor: Processor об'єкт з config.yaml
            loaded_handlers: Словник завантажених handlers {name: code}
            handlers_file: Шлях до handlers.bsl файлу (для завантаження якщо loaded_handlers немає)
        """
        self.processor = processor
        self.errors: List[str] = []
        self.warnings: List[str] = []

        # Завантажуємо handlers якщо не передано
        if loaded_handlers:
            self._loaded_handlers = loaded_handlers
        elif handlers_file and handlers_file.exists():
            self._loaded_handlers = self._load_handlers(handlers_file)
        else:
            self._loaded_handlers = {}

        # Збираємо ValueTable імена з форм
        self._value_table_names: Set[str] = set()
        for form in processor.forms:
            for vt in form.value_table_attributes:
                self._value_table_names.add(vt.name)

        # Збираємо form_attributes імена (SpreadsheetDocument, BinaryData, HTMLDocument)
        self._form_attribute_names: Set[str] = set()
        for form in processor.forms:
            if hasattr(form, 'form_attributes') and form.form_attributes:
                for attr in form.form_attributes:
                    self._form_attribute_names.add(attr.name)

    def _load_handlers(self, handlers_file: Path) -> Dict[str, str]:
        """Завантажує handlers з BSL файлу"""
        from .bsl_splitter import BSLSplitter

        try:
            splitter = BSLSplitter(handlers_file)
            return splitter.extract_procedures()
        except Exception as e:
            self.errors.append(f"Помилка завантаження handlers.bsl: {e}")
            return {}

    def _collect_required_handlers(self) -> Set[str]:
        """
        Збирає всі handler names з config.yaml (форми, події, команди, елементи)

        Returns:
            Множина імен handlers, які потрібні
        """
        required = set()

        for form in self.processor.forms:
            # Обробники подій форми
            for event_name, handler_name in form.events.items():
                required.add(handler_name)
                # Також перевіряємо серверний обробник для OnCreateAtServer
                if event_name == "OnCreateAtServer":
                    required.add(f"{handler_name}НаСервере")

            # Обробники команд
            for cmd in form.commands:
                if cmd.action:
                    # long_operation команди мають автогенерований handler
                    # Не потрібно шукати його в handlers.bsl
                    if cmd.long_operation:
                        continue
                    required.add(cmd.action)
                    # Серверний обробник (якщо є)
                    required.add(f"{cmd.action}НаСервере")

            # Обробники подій елементів
            for elem in form.elements:
                if elem.event_handlers:
                    for event_name, handler_name in elem.event_handlers.items():
                        required.add(handler_name)
                        # Серверний обробник для OnActivateRow, Selection, тощо
                        required.add(f"{handler_name}НаСервере")

                # Рекурсивно для child_items
                required.update(self._collect_element_handlers(elem.child_items))

        return required

    def _collect_element_handlers(self, elements) -> Set[str]:
        """Рекурсивно збирає handlers з вкладених елементів"""
        handlers = set()
        if not elements:
            return handlers

        for elem in elements:
            if elem.event_handlers:
                for handler_name in elem.event_handlers.values():
                    handlers.add(handler_name)
                    handlers.add(f"{handler_name}НаСервере")

            if elem.child_items:
                handlers.update(self._collect_element_handlers(elem.child_items))

        return handlers

    def validate_handler_names_match(self) -> Tuple[List[str], List[str]]:
        """
        Перевіряє що всі handlers з config.yaml існують в handlers.bsl

        Помилка: handler name в config не знайдено в handlers.bsl
        Попередження: handler в handlers.bsl не використовується в config

        Returns:
            (errors, warnings)
        """
        errors = []
        warnings = []

        if not self._loaded_handlers:
            # Немає handlers.bsl - пропускаємо
            return errors, warnings

        required_handlers = self._collect_required_handlers()
        available_handlers = set(self._loaded_handlers.keys())

        # Шукаємо відсутні handlers
        for handler_name in required_handlers:
            # Серверні handlers (НаСервере) опціональні
            if handler_name.endswith("НаСервере"):
                continue

            if handler_name not in available_handlers:
                # Шукаємо схожі handlers для підказки
                similar = get_close_matches(
                    handler_name,
                    available_handlers,
                    n=3,
                    cutoff=0.6
                )

                if similar:
                    errors.append(
                        f"Handler '{handler_name}' не знайдено в handlers.bsl. "
                        f"Схожі: {', '.join(similar)}"
                    )
                else:
                    errors.append(
                        f"Handler '{handler_name}' не знайдено в handlers.bsl"
                    )

        return errors, warnings

    def validate_handler_signatures(self) -> Tuple[List[str], List[str]]:
        """
        Перевіряє що всі handlers мають правильну структуру:
        - Директива (&НаКлиенте, &НаСервере, тощо)
        - Процедура/Функция з назвою
        - КонецПроцедуры/КонецФункции

        Returns:
            (errors, warnings)
        """
        errors = []
        warnings = []

        # v2.78.0+: Директиви компіляції - поняття модуля форми. Якщо форм немає
        # (напр. BSP print_form, де код живе в ObjectModule), вимагати директиву
        # неправильно: у модулі об'єкта вона зробила б код невалідним.
        require_directive = bool(getattr(self.processor, "forms", None))

        for handler_name, handler_code in self._loaded_handlers.items():
            # 1. Перевірка наявності директиви
            if require_directive and not self.DIRECTIVE_PATTERN.search(handler_code):
                errors.append(
                    f"Handler '{handler_name}' не має директиви компіляції "
                    f"(&НаКлиенте, &НаСервере, тощо). "
                    f"Додайте директиву на початок процедури."
                )

            # 2. Перевірка наявності сигнатури процедури/функції
            sig_match = self.SIGNATURE_PATTERN.search(handler_code)
            if not sig_match:
                errors.append(
                    f"Handler '{handler_name}' не має коректної сигнатури. "
                    f"Очікується: Процедура {handler_name}(...) або Функция {handler_name}(...)"
                )
            else:
                # Перевіряємо чи назва в сигнатурі відповідає імені файлу
                proc_name = sig_match.group(3)
                if proc_name != handler_name:
                    warnings.append(
                        f"Handler '{handler_name}' має іншу назву в сигнатурі: '{proc_name}'. "
                        f"Рекомендується використовувати однакові імена."
                    )

            # 3. Перевірка наявності закриваючого тегу
            if not self.END_PROCEDURE_PATTERN.search(handler_code):
                errors.append(
                    f"Handler '{handler_name}' не має закриваючого тегу "
                    f"(КонецПроцедуры/КонецФункции). "
                    f"Додайте закриваючий тег в кінці процедури."
                )

        return errors, warnings

    @staticmethod
    def _declares_procedure(code: str, name: str) -> bool:
        """Чи оголошена в коді процедура/функція з такою назвою (не згадка в коментарі)"""
        if not code:
            return False
        pattern = re.compile(
            r"(?:^|\n)\s*(?:Процедура|Функция|Procedure|Function)\s+" + re.escape(name) + r"\s*\(",
            re.IGNORECASE
        )
        return bool(pattern.search(code))

    def validate_bsp_print_handlers(self) -> Tuple[List[str], List[str]]:
        """
        Перевіряє що для кожної команди друку BSP є код у модулі об'єкта (v2.78.0+)

        Єдиний канал з handlers.bsl у ObjectModule - регіон #Область МодульОбъекта.
        Процедура, оголошена поза цим регіоном, завантажується, але нікуди не
        потрапляє: у ObjectModule генерується TODO-заглушка, і обробка друкує
        порожній документ. Без цієї перевірки втрата коду відбувається мовчки.

        Returns:
            (errors, warnings)
        """
        errors: List[str] = []
        warnings: List[str] = []

        bsp_config = getattr(self.processor, "bsp_config", None)
        if not bsp_config or bsp_config.type != "PrintForm":
            return errors, warnings

        object_module_code = "\n".join(
            part for part in (
                getattr(self.processor, "object_module_bsl", None),
                getattr(self.processor, "object_module_from_handlers", None),
            ) if part
        )

        for cmd in bsp_config.commands:
            handler_name = cmd.handler or f"Печать{cmd.id}"

            if self._declares_procedure(object_module_code, handler_name):
                continue

            if handler_name in self._loaded_handlers or self._declares_procedure(
                "\n".join(self._loaded_handlers.values()), handler_name
            ):
                warnings.append(
                    f"Handler '{handler_name}' (команда друку '{cmd.id}') знайдено в handlers.bsl, "
                    f"але він НЕ потрапить у модуль об'єкта: код друку має бути всередині регіону "
                    f"#Область МодульОбъекта ... #КонецОбласти. "
                    f"Зараз замість нього буде згенеровано TODO-заглушку."
                )
            else:
                warnings.append(
                    f"Для команди друку '{cmd.id}' не знайдено функцію '{handler_name}'. "
                    f"Додайте її в handlers.bsl всередині регіону #Область МодульОбъекта, "
                    f"інакше буде згенеровано TODO-заглушку (порожній друк)."
                )

        return errors, warnings

    def validate_form_level_access(self) -> Tuple[List[str], List[str]]:
        """
        Перевіряє чи немає некоректного доступу до form-level атрибутів через Объект.Name

        Form-level атрибути доступні напряму (Name), а не через Объект.:
        - ValueTable (value_tables)
        - form_attributes (SpreadsheetDocument, BinaryData, HTMLDocument)

        Returns:
            (errors, warnings)
        """
        errors = []
        warnings = []

        if not self._value_table_names and not self._form_attribute_names:
            return errors, warnings

        for handler_name, handler_code in self._loaded_handlers.items():
            # Шукаємо всі звернення до Объект.X
            for match in self.OBJECT_ACCESS_PATTERN.finditer(handler_code):
                accessed_name = match.group(1) or match.group(2)

                if accessed_name in self._value_table_names:
                    warnings.append(
                        f"Handler '{handler_name}': використано Объект.{accessed_name}, "
                        f"але '{accessed_name}' - це ValueTable на рівні форми. "
                        f"Доступ напряму: {accessed_name} (без Объект.)"
                    )

                if accessed_name in self._form_attribute_names:
                    warnings.append(
                        f"Handler '{handler_name}': використано Объект.{accessed_name}, "
                        f"але '{accessed_name}' - це form_attribute (SpreadsheetDocument/BinaryData/HTMLDocument). "
                        f"Доступ напряму: {accessed_name} (без Объект.)"
                    )

        return errors, warnings

    # Backward compatibility alias
    def validate_valuetable_access(self) -> Tuple[List[str], List[str]]:
        """Deprecated: use validate_form_level_access instead"""
        return self.validate_form_level_access()

    def validate(self) -> Tuple[bool, List[str], List[str]]:
        """
        Повна валідація handlers

        Returns:
            (success, errors, warnings)
        """
        self.errors = []
        self.warnings = []

        # 1. Перевірка імен handlers
        name_errors, name_warnings = self.validate_handler_names_match()
        self.errors.extend(name_errors)
        self.warnings.extend(name_warnings)

        # 2. Перевірка сигнатур handlers
        sig_errors, sig_warnings = self.validate_handler_signatures()
        self.errors.extend(sig_errors)
        self.warnings.extend(sig_warnings)

        # 3. Перевірка доступу до form-level атрибутів (ValueTable, form_attributes)
        fl_errors, fl_warnings = self.validate_form_level_access()
        self.errors.extend(fl_errors)
        self.warnings.extend(fl_warnings)

        # 4. Перевірка handlers друку BSP (v2.78.0+)
        bsp_errors, bsp_warnings = self.validate_bsp_print_handlers()
        self.errors.extend(bsp_errors)
        self.warnings.extend(bsp_warnings)

        return len(self.errors) == 0, self.errors, self.warnings
