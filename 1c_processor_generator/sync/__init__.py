"""
Sync Tool - Extensible Handler Architecture.

This package provides a pluggable system for synchronizing different element types
between 1C XML exports and YAML configuration files.

Usage:
    from sync import HandlerRegistry

    registry = HandlerRegistry.instance()
    handler = registry.get("attribute")
    data = handler.extract_from_xml(element, namespaces)
"""

from .registry import HandlerRegistry
from .base_handler import BaseElementHandler

__all__ = ["HandlerRegistry", "BaseElementHandler"]
