"""
Utility functions for PRO module.

Contains shared utilities extracted from public modules for protected compilation.
"""

from uuid import uuid4


def generate_uuid() -> str:
    """Генерує валідний UUID для 1C (lowercase)"""
    return str(uuid4()).lower()
