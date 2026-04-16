"""
Designer Log Parser - публічний інтерфейс.

Реалізація захищена в pro/ модулі.

Використання:
    >>> from 1c_processor_generator.designer_log_parser import DesignerLogParser, ValidationError
    >>> parser = DesignerLogParser()
    >>> errors, warnings = parser.parse_check_modules_log(log_path)
"""

from .pro.log_parser_impl import DesignerLogParser, ValidationError

__all__ = ["DesignerLogParser", "ValidationError"]
