"""
Parsing module - DRY архітектура для парсингу YAML конфігурацій.

v2.43.0

Модулі:
- schemas: Декларативні схеми елементів форми
- extractors: Функції витягування properties
- elements: ElementParser для парсингу form elements
"""

from .schemas import SCHEMAS, ElementSchema, PropSpec, get_schema
from .extractors import normalize_multilang, extract_props
from .elements import ElementParser

__all__ = [
    "SCHEMAS",
    "ElementSchema",
    "PropSpec",
    "get_schema",
    "normalize_multilang",
    "extract_props",
    "ElementParser",
]
