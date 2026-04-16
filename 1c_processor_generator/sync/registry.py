"""
Handler Registry for Sync Tool.

Provides a singleton registry for element handlers, enabling:
- Handler discovery by element type
- Iteration over all handlers for sync operations
- Easy registration of new element types
"""

import logging
from typing import Dict, Iterator, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .base_handler import BaseElementHandler

logger = logging.getLogger(__name__)


class HandlerRegistry:
    """
    Singleton registry for element handlers.

    Usage:
        # Get singleton instance
        registry = HandlerRegistry.instance()

        # Get handler by type
        handler = registry.get("attribute")
        if handler:
            data = handler.extract_from_xml(elem)

        # Iterate all handlers
        for name, handler in registry.all_handlers().items():
            elements = handler.get_elements_from_tree(tree)
    """

    _instance: Optional["HandlerRegistry"] = None
    _handlers: Dict[str, "BaseElementHandler"]
    _initialized: bool

    def __new__(cls) -> "HandlerRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._handlers = {}
            cls._instance._initialized = False
        return cls._instance

    @classmethod
    def instance(cls) -> "HandlerRegistry":
        """
        Get the singleton registry instance.

        On first call, initializes and registers all built-in handlers.
        """
        registry = cls()
        if not registry._initialized:
            registry._register_builtin_handlers()
            registry._initialized = True
        return registry

    @classmethod
    def reset(cls) -> None:
        """
        Reset the singleton (for testing purposes).
        """
        if cls._instance is not None:
            cls._instance._handlers.clear()
            cls._instance._initialized = False

    def register(self, handler: "BaseElementHandler") -> None:
        """
        Register a handler for an element type.

        Args:
            handler: Handler instance to register

        Raises:
            ValueError: If handler with same element_type_name already registered
        """
        name = handler.element_type_name
        if name in self._handlers:
            logger.warning(f"Handler for '{name}' already registered, replacing")
        self._handlers[name] = handler
        logger.debug(f"Registered handler for '{name}'")

    def unregister(self, element_type: str) -> bool:
        """
        Unregister a handler by element type.

        Args:
            element_type: Element type name to unregister

        Returns:
            True if handler was unregistered, False if not found
        """
        if element_type in self._handlers:
            del self._handlers[element_type]
            logger.debug(f"Unregistered handler for '{element_type}'")
            return True
        return False

    def get(self, element_type: str) -> Optional["BaseElementHandler"]:
        """
        Get handler for element type.

        Args:
            element_type: Element type name (e.g., 'attribute', 'template')

        Returns:
            Handler instance or None if not found
        """
        return self._handlers.get(element_type)

    def all_handlers(self) -> Dict[str, "BaseElementHandler"]:
        """
        Get all registered handlers.

        Returns:
            Dictionary mapping element type names to handlers
        """
        return self._handlers.copy()

    def handler_names(self) -> Iterator[str]:
        """
        Iterate over registered handler names.
        """
        return iter(self._handlers.keys())

    def __contains__(self, element_type: str) -> bool:
        """Check if handler is registered."""
        return element_type in self._handlers

    def __len__(self) -> int:
        """Number of registered handlers."""
        return len(self._handlers)

    def _register_builtin_handlers(self) -> None:
        """
        Register all built-in handlers.

        Called automatically on first instance() call.
        """
        # Import handlers here to avoid circular imports
        from .handlers import (
            AttributeHandler,
            FormElementHandler,
            CommandHandler,
            TabularSectionHandler,
            ValueTableHandler,
            FormAttributeHandler,
            FormHandler,
            TemplateHandler,
            FormParameterHandler,
        )

        builtin_handlers = [
            AttributeHandler(),
            FormElementHandler(),
            CommandHandler(),
            TabularSectionHandler(),
            ValueTableHandler(),
            FormAttributeHandler(),
            FormHandler(),
            TemplateHandler(),
            FormParameterHandler(),
        ]

        for handler in builtin_handlers:
            self.register(handler)

        logger.info(f"Registered {len(builtin_handlers)} built-in handlers")
