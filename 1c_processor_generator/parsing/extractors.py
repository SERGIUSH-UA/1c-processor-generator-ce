"""
Property Extractors - DRY функції витягування properties.

v2.43.0 DRY Refactoring
v2.69.0 Compact Multilang Support (array, pipe formats)

Централізована логіка витягування properties з YAML конфігурації.
Замінює повторюваний код типу:
    if "width" in config:
        props["width"] = config["width"]

Використання:
    >>> from parsing.extractors import normalize_multilang, extract_props
    >>> config = normalize_multilang(raw_config, languages=["ru", "uk"])
    >>> props = extract_props(config, schema)
"""

import re
from typing import Dict, List, Any, Optional, Union
from .schemas import PropSpec, ElementSchema


# Default languages for backward compatibility
DEFAULT_LANGUAGES = ["ru", "uk", "en"]


def parse_multilang_value(
    value: Union[str, List[str], Dict[str, str]],
    languages: List[str]
) -> Dict[str, str]:
    """
    Парсить мультимовне значення в будь-якому форматі.

    Підтримує три формати:
    1. Dict: {"ru": "...", "uk": "...", "en": "..."}
    2. Array: ["...", "...", "..."] - слідує порядку languages
    3. Pipe: "... | ... | ..." - розділяє по |, слідує порядку languages
    4. String: "..." - одне значення для всіх мов

    Fallback: якщо значень менше ніж мов → використовується ПЕРШЕ (primary).

    Args:
        value: Значення в будь-якому форматі
        languages: Список мов у порядку застосування

    Returns:
        Dict з мовами як ключами

    Example:
        >>> parse_multilang_value("A | B", ["ru", "uk", "en"])
        {"ru": "A", "uk": "B", "en": "A"}

        >>> parse_multilang_value(["A", "B", "C"], ["ru", "uk", "en"])
        {"ru": "A", "uk": "B", "en": "C"}

    v2.69.0+
    """
    if not languages:
        languages = DEFAULT_LANGUAGES

    # Format 1: Dict (current) → pass through
    if isinstance(value, dict):
        return value

    # Format 2: Array → map to languages (fallback to first)
    if isinstance(value, list):
        if not value:
            # Empty array → empty string for all languages
            return {lang: "" for lang in languages}
        result = {}
        for i, lang in enumerate(languages):
            result[lang] = value[i] if i < len(value) else value[0]
        return result

    # Format 3: String with pipe → split (fallback to first)
    if isinstance(value, str):
        # Check for unescaped pipe: has | but not preceded by \
        # Use regex to find unescaped pipes
        if '|' in value:
            # Split by unescaped pipe (not preceded by \)
            parts = re.split(r'(?<!\\)\|', value)
            # Unescape \| → |
            parts = [p.strip().replace('\\|', '|') for p in parts]

            # If we got multiple parts, treat as pipe format
            if len(parts) > 1:
                result = {}
                for i, lang in enumerate(languages):
                    result[lang] = parts[i] if i < len(parts) else parts[0]
                return result
            else:
                # Single part (only escaped pipes) - unescape and return for all
                return {lang: parts[0] for lang in languages}

        # Format 4: Plain string → same for all
        return {lang: value for lang in languages}

    # Fallback: convert to string
    return {lang: str(value) for lang in languages}


def normalize_multilang(
    config: Dict[str, Any],
    fields: Optional[List[str]] = None,
    languages: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Нормалізує мовні поля в плоский формат.

    Підтримує чотири формати (v2.69.0+):
    1. Плоский: title_ru, title_uk, title_en (не потребує перетворення)
    2. Вкладений dict: title: {ru: "...", uk: "..."}
    3. Array: title: ["...", "..."] (потребує languages)
    4. Pipe: title: "... | ..." (потребує languages)

    Args:
        config: Словник з конфігурацією
        fields: Список полів для нормалізації (за замовчуванням: synonym, title, tooltip, input_hint)
        languages: Список мов у порядку застосування (за замовчуванням: ["ru", "uk", "en"])

    Returns:
        Нормалізований словник з плоскими полями

    Example:
        >>> config = {"name": "Test", "title": {"ru": "Тест", "uk": "Тест"}}
        >>> normalize_multilang(config)
        {"name": "Test", "title_ru": "Тест", "title_uk": "Тест"}

        >>> config = {"name": "Test", "title": ["Тест", "Тест"]}
        >>> normalize_multilang(config, languages=["ru", "uk"])
        {"name": "Test", "title_ru": "Тест", "title_uk": "Тест"}

        >>> config = {"name": "Test", "title": "Тест | Тест"}
        >>> normalize_multilang(config, languages=["ru", "uk"])
        {"name": "Test", "title_ru": "Тест", "title_uk": "Тест"}
    """
    if fields is None:
        fields = ["synonym", "title", "tooltip", "input_hint"]

    if languages is None:
        languages = DEFAULT_LANGUAGES

    result = config.copy()

    for field in fields:
        if field not in config:
            continue

        value = config[field]

        # Skip if already flat format (title_ru exists)
        if any(f"{field}_{lang}" in config for lang in languages):
            continue

        # Parse using the new multilang parser
        parsed = parse_multilang_value(value, languages)

        # Apply parsed values to result
        for lang, text in parsed.items():
            result[f"{field}_{lang}"] = text

        # Remove the original field
        if field in result:
            del result[field]

    return result


def extract_props(config: Dict[str, Any], schema: ElementSchema) -> Dict[str, Any]:
    """
    Витягує всі properties за декларативною схемою.

    Args:
        config: Словник з конфігурацією елемента (вже нормалізований)
        schema: Схема елемента

    Returns:
        Словник properties для FormElement
    """
    props: Dict[str, Any] = {}

    for spec in schema.props:
        if spec.multilang:
            _extract_multilang_prop(config, props, spec.key)
        else:
            _extract_simple_prop(config, props, spec)

    return props


def _extract_multilang_prop(config: Dict[str, Any], props: Dict[str, Any], key: str) -> None:
    """
    Витягує multilang property (key_ru, key_uk, key_en).

    Підтримує:
    - Повний формат: key_ru, key_uk, key_en
    - Частковий: тільки деякі мови
    - Fallback: старий формат з одним key

    Args:
        config: Source конфігурація
        props: Target properties dict
        key: Базовий ключ (title, tooltip, etc.)
    """
    has_any = any(f"{key}_{lang}" in config for lang in ["ru", "uk", "en"])

    if has_any:
        for lang in ["ru", "uk", "en"]:
            full_key = f"{key}_{lang}"
            if full_key in config:
                props[full_key] = config[full_key]

    # Fallback для старого формату (одномовний key)
    if key in config:
        props[key] = config[key]


def _extract_simple_prop(config: Dict[str, Any], props: Dict[str, Any], spec: PropSpec) -> None:
    """
    Витягує просту (не multilang) property.

    Args:
        config: Source конфігурація
        props: Target properties dict
        spec: Специфікація property
    """
    if spec.key in config:
        target = spec.target or spec.key
        props[target] = config[spec.key]
    elif spec.default is not None:
        target = spec.target or spec.key
        props[target] = spec.default


def extract_simple_props(config: Dict[str, Any], props: Dict[str, Any], keys: List[str]) -> None:
    """
    Утилітна функція для простого копіювання properties.

    Для випадків коли не використовується schema-based підхід.

    Args:
        config: Source конфігурація
        props: Target properties dict
        keys: Список ключів для копіювання

    Example:
        >>> extract_simple_props(config, props, ["width", "height", "read_only"])
    """
    for key in keys:
        if key in config:
            props[key] = config[key]
