"""
Designer Finder - публічний інтерфейс.

Реалізація захищена в pro/ модулі.

Використання:
    >>> from 1c_processor_generator.designer_finder import DesignerFinder
    >>> finder = DesignerFinder()
    >>> print(finder.designer_path)
"""

from .pro.designer_finder_impl import DesignerFinder

__all__ = ["DesignerFinder"]
