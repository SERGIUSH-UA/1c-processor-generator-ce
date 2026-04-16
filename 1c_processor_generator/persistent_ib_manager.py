"""
Persistent IB Manager - публічний інтерфейс.

Реалізація захищена в pro/ модулі.

Використання:
    >>> from 1c_processor_generator.persistent_ib_manager import PersistentIBManager
    >>> manager = PersistentIBManager(designer_path)
    >>> ib_path = manager.get_or_create()
"""

from .pro.persistent_ib_impl import PersistentIBManager

__all__ = ["PersistentIBManager"]
