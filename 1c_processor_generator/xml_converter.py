"""
XML Converter - публічний інтерфейс.

Реалізація захищена в pro/ модулі.

Використання:
    >>> from 1c_processor_generator.xml_converter import XMLConverter
    >>> converter = XMLConverter()
    >>> converter.convert_external_to_internal(source, target)
"""

from .pro.xml_converter_impl import XMLConverter

__all__ = ["XMLConverter"]
