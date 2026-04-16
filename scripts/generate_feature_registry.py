#!/usr/bin/env python3
"""
Generate feature_registry.json from constants.py and feature_registry_meta.yaml

This script auto-extracts feature information from the codebase and merges it
with human-written descriptions to create a machine-readable feature registry.

Usage:
    python scripts/generate_feature_registry.py
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import yaml

# Add parent directory to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import constants using importlib (module name has special chars)
import importlib.util
spec = importlib.util.spec_from_file_location(
    "constants",
    project_root / "1c_processor_generator" / "constants.py"
)
constants = importlib.util.module_from_spec(spec)
spec.loader.exec_module(constants)


def get_version() -> str:
    """Get current generator version from __init__.py"""
    init_file = Path(__file__).parent.parent / "1c_processor_generator" / "__init__.py"
    if init_file.exists():
        content = init_file.read_text(encoding="utf-8")
        for line in content.splitlines():
            if line.startswith("__version__"):
                return line.split("=")[1].strip().strip('"').strip("'")
    return "unknown"


def load_meta() -> dict:
    """Load feature_registry_meta.yaml"""
    meta_file = Path(__file__).parent / "feature_registry_meta.yaml"
    with open(meta_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def extract_elements(meta: dict) -> dict:
    """Extract element types from constants and merge with meta"""
    elements_meta = meta.get("elements", {}).get("items", {})
    items = []

    for element_type in constants.ELEMENT_ID_INCREMENTS:
        if element_type in ("Page", "TableColumn"):
            # Skip internal element types
            continue

        item_meta = elements_meta.get(element_type, {})
        items.append({
            "name": element_type,
            "description": item_meta.get("description", f"{element_type} form element"),
            "docs": item_meta.get("docs", "docs/reference/API_REFERENCE.md"),
            "since": item_meta.get("since", "1.0.0"),
        })

    return {
        "description": meta.get("elements", {}).get("description", "Form element types"),
        "count": len(items),
        "items": sorted(items, key=lambda x: x["name"]),
    }


def extract_events(meta: dict) -> dict:
    """Extract events from constants and merge with meta"""
    events_meta = meta.get("events", {})
    form_events_meta = events_meta.get("form_events", {})
    element_events_meta = events_meta.get("element_events", {})

    items = []

    # Form events
    for event_name, event_info in constants.FORM_EVENT_SIGNATURES.items():
        item_meta = form_events_meta.get(event_name, {})
        items.append({
            "name": event_name,
            "description": item_meta.get("description", f"Form event: {event_name}"),
            "docs": item_meta.get("docs", "docs/reference/API_REFERENCE.md#form-events"),
            "context": "form",
            "directive": event_info.get("directive", ""),
            "handler": event_info.get("handler", ""),
        })

    # Element events
    for event_name, event_info in constants.ELEMENT_EVENT_SIGNATURES.items():
        item_meta = element_events_meta.get(event_name, {})
        items.append({
            "name": event_name,
            "description": item_meta.get("description", f"Element event: {event_name}"),
            "docs": item_meta.get("docs", "docs/reference/API_REFERENCE.md#element-events"),
            "context": "element",
            "directive": event_info.get("directive", ""),
            "handler": event_info.get("handler", ""),
        })

    return {
        "description": events_meta.get("description", "Event handlers for forms and elements"),
        "count": len(items),
        "items": sorted(items, key=lambda x: x["name"]),
    }


def extract_types(meta: dict) -> dict:
    """Extract data types from constants and merge with meta"""
    types_meta = meta.get("types", {}).get("items", {})
    items = []

    # Base types (not reference types)
    base_types = ["string", "boolean", "number", "date", "spreadsheet_document", "binary_data", "html_document"]

    for type_name in base_types:
        if type_name in constants.TYPE_MAPPING:
            item_meta = types_meta.get(type_name, {})
            items.append({
                "name": type_name,
                "description": item_meta.get("description", f"Data type: {type_name}"),
                "docs": item_meta.get("docs", "docs/reference/API_REFERENCE.md#data-types"),
                "xml_type": constants.TYPE_MAPPING[type_name],
                "since": item_meta.get("since", "1.0.0"),
            })

    # Reference types (patterns)
    for ref_type in ["CatalogRef", "DocumentRef", "EnumRef"]:
        item_meta = types_meta.get(ref_type, {})
        items.append({
            "name": ref_type,
            "description": item_meta.get("description", f"Reference type: {ref_type}.*"),
            "docs": item_meta.get("docs", "docs/reference/API_REFERENCE.md#reference-types"),
            "pattern": f"{ref_type}.<ObjectName>",
        })

    return {
        "description": meta.get("types", {}).get("description", "Data types for attributes"),
        "count": len(items),
        "items": items,
    }


def extract_cli(meta: dict) -> dict:
    """Extract CLI commands from meta (manually maintained)"""
    cli_meta = meta.get("cli", {})
    items = []

    for cmd_name, cmd_info in cli_meta.get("items", {}).items():
        item = {
            "name": cmd_name,
            "description": cmd_info.get("description", f"CLI command: {cmd_name}"),
            "docs": cmd_info.get("docs", "CLAUDE.md#commands"),
        }
        if "since" in cmd_info:
            item["since"] = cmd_info["since"]
        if "options" in cmd_info:
            item["options"] = cmd_info["options"]
        items.append(item)

    return {
        "description": cli_meta.get("description", "CLI commands"),
        "count": len(items),
        "items": sorted(items, key=lambda x: x["name"]),
    }


def extract_tools(meta: dict) -> dict:
    """Extract tools from meta (manually maintained)"""
    tools_meta = meta.get("tools", {})
    items = []

    for tool_name, tool_info in tools_meta.get("items", {}).items():
        item = {
            "name": tool_name,
            "description": tool_info.get("description", f"Tool: {tool_name}"),
            "docs": tool_info.get("docs", "docs/reference/ADVANCED_FEATURES.md"),
        }
        if "since" in tool_info:
            item["since"] = tool_info["since"]
        if "capabilities" in tool_info:
            item["capabilities"] = tool_info["capabilities"]
        items.append(item)

    return {
        "description": tools_meta.get("description", "Built-in tools"),
        "count": len(items),
        "items": items,
    }


def extract_pictures(meta: dict) -> dict:
    """Extract pictures info from constants"""
    pictures_meta = meta.get("pictures", {})

    return {
        "description": pictures_meta.get("description", "Valid StdPicture icons"),
        "docs": pictures_meta.get("docs", "docs/VALID_PICTURES.md"),
        "count": len(constants.VALID_STD_PICTURES),
        "source": "constants.VALID_STD_PICTURES",
        "common": pictures_meta.get("common", []),
    }


def extract_keywords(meta: dict) -> dict:
    """Extract keywords info from constants"""
    keywords_meta = meta.get("keywords", {})

    return {
        "description": keywords_meta.get("description", "BSL reserved keywords"),
        "docs": keywords_meta.get("docs", "docs/reference/API_REFERENCE.md#bsl-reserved-keywords"),
        "count": len(constants.BSL_RESERVED_KEYWORDS),
        "source": "constants.BSL_RESERVED_KEYWORDS",
        "critical": keywords_meta.get("critical", []),
    }


def extract_common_mistakes(meta: dict) -> dict:
    """Extract common LLM hallucinations and corrections"""
    mistakes_meta = meta.get("common_mistakes", {})

    return {
        "description": mistakes_meta.get("description", "Common LLM hallucinations and corrections"),
        "docs": mistakes_meta.get("docs", "docs/CHEATSHEET.md"),
        "items": mistakes_meta.get("items", []),
    }


def generate_registry() -> dict:
    """Generate the complete feature registry"""
    meta = load_meta()

    registry = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "version": get_version(),
        "generated": datetime.now().isoformat(),
        "description": "Machine-readable feature registry for 1C Processor Generator. For AI agents: use this file for programmatic feature discovery.",
        "categories": {
            "elements": extract_elements(meta),
            "events": extract_events(meta),
            "types": extract_types(meta),
            "cli": extract_cli(meta),
            "tools": extract_tools(meta),
            "pictures": extract_pictures(meta),
            "keywords": extract_keywords(meta),
            "common_mistakes": extract_common_mistakes(meta),
        },
    }

    return registry


def main():
    """Main entry point"""
    registry = generate_registry()

    # Output path
    output_file = Path(__file__).parent.parent / "docs" / "feature_registry.json"

    # Write JSON with proper formatting
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)

    print(f"Generated: {output_file}")
    print(f"Version: {registry['version']}")
    print(f"Categories: {len(registry['categories'])}")

    # Print summary
    for cat_name, cat_data in registry["categories"].items():
        count = cat_data.get("count", len(cat_data.get("items", [])))
        print(f"  - {cat_name}: {count} items")


if __name__ == "__main__":
    main()
