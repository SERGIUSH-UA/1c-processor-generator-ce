"""
1C External Data Processor Generator

Автоматична генерація зовнішніх обробок для 1C:Enterprise 8.3
"""

__version__ = "2.78.0"
__author__ = "SERGIUSH"
__license__ = "GPL-3.0-or-later"
__copyright__ = "Copyright (c) 2024-2025 ITDEO. GPL-3.0-or-later."


from .generator import ProcessorGenerator
from .models import Processor, Attribute, TabularSection, Column

__all__ = [
    "ProcessorGenerator",
    "Processor",
    "Attribute",
    "TabularSection",
    "Column",
]
