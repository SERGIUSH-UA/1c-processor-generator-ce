"""
Protected constants for 1C Processor Generator.
SPDX-License-Identifier: GPL-3.0-or-later
Copyright (c) 2024-2025 ITDEO
This file is part of 1C Processor Generator Community Edition.
"""

import hashlib
import os
from pathlib import Path
from typing import Dict, List, Optional


# ============================================================================
# INTERNAL CONFIGURATION
# ============================================================================

# ============================================================================
# COMPILER CONFIGURATION
# ============================================================================

# --- Cloud compilation API (primary method) ---
CLOUD_COMPILATION_URL: str = "https://compile.1c-cloud.ru/api/v2"
CLOUD_COMPILATION_TIMEOUT: int = 120
CLOUD_API_VERSION: str = "2.5.1"

# --- Local compilation fallback ---
COMPILER_BINARY_COMMAND: str = "/CompileExternalProcessor"
COMPILER_VALIDATE_COMMAND: str = "/ValidateProcessor"
COMPILER_BUILD_COMMAND: str = "/BuildDataProcessor"

# --- Legacy paths (deprecated, kept for compatibility) ---
LEGACY_COMPILER_PATHS: list = [
    "C:/1C/Compiler",
    "D:/1CEnt/bin",
    "C:/Program Files/1C Enterprise/compiler",
]

# --- Internal compilation engine ---
DESIGNER_LOAD_EPF_COMMAND: str = "/LoadExternalDataProcessorOrReportFromFiles"
DESIGNER_DUMP_EPF_COMMAND: str = "/DumpExternalDataProcessorOrReportToFiles"
DESIGNER_CHECK_MODULES_COMMAND: str = "/CheckModules"
DESIGNER_CHECK_CONFIG_COMMAND: str = "/CheckConfig"

CHECK_MODULES_PARAMS: List[str] = [
    "-ThinClient",
    "-Server",
]

CHECK_CONFIG_BASE_PARAMS: List[str] = [
    "-ThinClient",
    "-Server",
]

CHECK_CONFIG_SEMANTIC_CHECKS: Dict[str, str] = {
    "check_incorrect_references": "-IncorrectReferences",
    "check_handlers_existence": "-HandlersExistence",
    "check_empty_handlers": "-EmptyHandlers",
    "check_unreference_procedures": "-UnreferenceProcedures",
    "check_extended_modules": "-ExtendedModulesCheck",
}

DESIGNER_SILENT_PARAMS: List[str] = [
    "/DisableStartupMessages",
    "/DisableStartupDialogs",
]

STANDARD_DESIGNER_PATHS_WINDOWS: List[str] = [
    "C:/Program Files/1cv8",
    "C:/Program Files (x86)/1cv8",
    "C:/Program Files/BAF",        # BAF (Ukrainian 1C alternative)
    "C:/Program Files (x86)/BAF",  # BAF 32-bit
]

ENV_DESIGNER_PATH: str = "PATH_1C_DESIGNER"

EPF_COMPILER_CACHE_DIR: Path = Path(os.environ.get("APPDATA", ".")) / "1C" / "epf_compiler_cache"

# ============================================================================
# v2.57.0+ PRO FEATURE FLAGS (PROTECTED)
# These control which features require PRO license
# CRITICAL: Changing these values is illegal license bypass
# ============================================================================

_BSP_IS_PRO_FEATURE: bool = False  # BSP integration is FREE (v2.71.6+)

# ============================================================================
# v2.54.0+ XML GENERATION CONSTANTS (PROTECTED)
# These are critical for generating valid 1C XML files
# Without these constants, generated files will NOT open in 1C Designer
# ============================================================================

# ClassId - 1C platform internal identifiers (DO NOT MODIFY!)
# These GUIDs identify object types to 1C platform
# Wrong GUID = file won't be recognized as EPF/ERF
CLASS_ID_EXTERNAL_DATA_PROCESSOR: str = "c3831ec8-d8d5-4f93-8a22-f9bfae07327f"
CLASS_ID_EXTERNAL_REPORT: str = "e41aff26-25cf-4bb6-b6c1-3f478a75f374"

# XML namespaces for main processor file
# All 16 namespaces must be present and correct
_XML_NAMESPACES: Dict[str, str] = {
    "xmlns": "http://v8.1c.ru/8.3/MDClasses",
    "xmlns:app": "http://v8.1c.ru/8.2/managed-application/core",
    "xmlns:cfg": "http://v8.1c.ru/8.1/data/enterprise/current-config",
    "xmlns:cmi": "http://v8.1c.ru/8.2/managed-application/cmi",
    "xmlns:ent": "http://v8.1c.ru/8.1/data/enterprise",
    "xmlns:lf": "http://v8.1c.ru/8.2/managed-application/logform",
    "xmlns:mxl": "http://v8.1c.ru/8.2/data/spreadsheet",
    "xmlns:style": "http://v8.1c.ru/8.1/data/ui/style",
    "xmlns:sys": "http://v8.1c.ru/8.1/data/ui/fonts/system",
    "xmlns:v8": "http://v8.1c.ru/8.1/data/core",
    "xmlns:v8ui": "http://v8.1c.ru/8.1/data/ui",
    "xmlns:web": "http://v8.1c.ru/8.1/data/ui/colors/web",
    "xmlns:win": "http://v8.1c.ru/8.1/data/ui/colors/windows",
    "xmlns:xen": "http://v8.1c.ru/8.3/xcf/enums",
    "xmlns:xpr": "http://v8.1c.ru/8.3/xcf/predef",
    "xmlns:xr": "http://v8.1c.ru/8.3/xcf/readable",
    "xmlns:xs": "http://www.w3.org/2001/XMLSchema",
    "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
}

# XML namespaces for form files (Form.xml)
# 17 namespaces including DCS (Data Composition System)
_FORM_XML_NAMESPACES: Dict[str, str] = {
    "xmlns": "http://v8.1c.ru/8.3/xcf/logform",
    "xmlns:app": "http://v8.1c.ru/8.2/managed-application/core",
    "xmlns:cfg": "http://v8.1c.ru/8.1/data/enterprise/current-config",
    "xmlns:dcscor": "http://v8.1c.ru/8.1/data-composition-system/core",
    "xmlns:dcssch": "http://v8.1c.ru/8.1/data-composition-system/schema",
    "xmlns:dcsset": "http://v8.1c.ru/8.1/data-composition-system/settings",
    "xmlns:ent": "http://v8.1c.ru/8.1/data/enterprise",
    "xmlns:lf": "http://v8.1c.ru/8.2/managed-application/logform",
    "xmlns:mxl": "http://v8.1c.ru/8.2/data/spreadsheet",
    "xmlns:pl": "http://v8.1c.ru/8.3/data/planner",
    "xmlns:style": "http://v8.1c.ru/8.1/data/ui/style",
    "xmlns:sys": "http://v8.1c.ru/8.1/data/ui/fonts/system",
    "xmlns:v8": "http://v8.1c.ru/8.1/data/core",
    "xmlns:v8ui": "http://v8.1c.ru/8.1/data/ui",
    "xmlns:web": "http://v8.1c.ru/8.1/data/ui/colors/web",
    "xmlns:win": "http://v8.1c.ru/8.1/data/ui/colors/windows",
    "xmlns:xr": "http://v8.1c.ru/8.3/xcf/readable",
    "xmlns:xs": "http://www.w3.org/2001/XMLSchema",
    "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
}

# Type mapping: YAML type → XML type
# Critical for correct attribute generation
_TYPE_MAPPING: Dict[str, str] = {
    "string": "xs:string",
    "boolean": "xs:boolean",
    "number": "xs:decimal",
    "date": "xs:dateTime",
    "spreadsheet_document": "mxl:SpreadsheetDocument",
    "binary_data": "v8:ValueStorage",
    "html_document": "xs:string",
    "planner": "pl:Planner",
    # Form attribute types (v2.42.0+)
    "value_table": "v8:ValueTable",
    "value_tree": "v8:ValueTree",  # v2.64.0+
    # Catalog references (auto-prefixed)
    "CatalogRef.Пользователи": "cfg:CatalogRef.Пользователи",
    "CatalogRef.ГруппыДоступа": "cfg:CatalogRef.ГруппыДоступа",
    "CatalogRef.ПрофилиГруппДоступа": "cfg:CatalogRef.ПрофилиГруппДоступа",
    "CatalogRef.Номенклатура": "cfg:CatalogRef.Номенклатура",
    "CatalogRef.Контрагенты": "cfg:CatalogRef.Контрагенты",
}

# Element suffixes for form sub-elements
# These are fixed names that 1C expects
_ELEMENT_SUFFIXES: Dict[str, str] = {
    "context_menu": "КонтекстноеМеню",
    "extended_tooltip": "РасширеннаяПодсказка",
    "command_bar": "КоманднаяПанель",
    "search_string": "СтрокаПоиска",
    "view_status": "СостояниеПросмотра",
    "search_control": "УправлениеПоиском",
    "line_number": "НомерСтроки",
}

# TabularSection UUID structure
# Each TabularSection requires exactly 5 UUIDs with specific purposes
TABULAR_SECTION_UUID_FIELDS: List[str] = [
    "uuid",          # Main UUID
    "type_id",       # Type identifier
    "value_id",      # Value identifier
    "row_type_id",   # Row type identifier
    "row_value_id",  # Row value identifier
]

# ============================================================================
# INTEGRITY VERIFICATION
# Prevents tampering - if constants modified, hash won't match
# ============================================================================


# ============================================================================
# PUBLIC API FUNCTIONS
# ============================================================================

def get_xml_namespaces() -> Dict[str, str]:
    """Get XML namespaces for main processor file."""
    return _XML_NAMESPACES.copy()


def get_form_xml_namespaces() -> Dict[str, str]:
    """Get XML namespaces for form files."""
    return _FORM_XML_NAMESPACES.copy()


def get_type_mapping() -> Dict[str, str]:
    """Get YAML to XML type mapping."""
    return _TYPE_MAPPING.copy()


def get_element_suffixes() -> Dict[str, str]:
    """Get element suffixes for form sub-elements."""
    return _ELEMENT_SUFFIXES.copy()


def get_class_id(object_type: str = "processor") -> str:
    """
    Get ClassId for 1C object type.

    Args:
        object_type: "processor" or "report"

    Returns:
        ClassId GUID string
    """
    if object_type == "report":
        return CLASS_ID_EXTERNAL_REPORT
    return CLASS_ID_EXTERNAL_DATA_PROCESSOR


def is_bsp_pro_feature() -> bool:
    """BSP integration is always free in community edition."""
    return False


# ============================================================================
# v2.54.0+ ELEMENT RENDERING (PROTECTED)
# Critical XML generation functions - hidden in .pyd
# ============================================================================

# Element ID structure: how many sub-IDs each element type uses
# This is CRITICAL know-how - wrong numbers = broken XML
_ELEMENT_ID_STRUCTURE: Dict[str, Dict[str, int]] = {
    # Fields with ContextMenu + ExtendedTooltip (3 IDs: base, +1, +2)
    "InputField": {"context_menu": 1, "extended_tooltip": 2, "total": 3},
    "LabelField": {"context_menu": 1, "extended_tooltip": 2, "total": 3},
    "LabelDecoration": {"context_menu": 1, "extended_tooltip": 2, "total": 3},
    "PictureDecoration": {"context_menu": 1, "extended_tooltip": 2, "total": 3},
    "PictureField": {"context_menu": 1, "extended_tooltip": 2, "total": 3},
    "RadioButtonField": {"context_menu": 1, "extended_tooltip": 2, "total": 3},
    "CheckBoxField": {"context_menu": 1, "extended_tooltip": 2, "total": 3},
    "SpreadSheetDocumentField": {"context_menu": 1, "extended_tooltip": 2, "total": 3},
    "HTMLDocumentField": {"context_menu": 1, "extended_tooltip": 2, "total": 3},
    "CalendarField": {"context_menu": 1, "extended_tooltip": 2, "total": 3},
    "ChartField": {"context_menu": 1, "extended_tooltip": 2, "total": 3},
    "PlannerField": {"context_menu": 1, "extended_tooltip": 2, "total": 3},
    # Groups with ExtendedTooltip only (2 IDs: base, +1)
    "Button": {"extended_tooltip": 1, "total": 2},
    "ButtonGroup": {"extended_tooltip": 1, "total": 2},
    "ColumnGroup": {"extended_tooltip": 1, "total": 2},
    "Popup": {"extended_tooltip": 1, "total": 2},
    "UsualGroup": {"extended_tooltip": 1, "total": 2},
    "Pages": {"extended_tooltip": 1, "total": 2},
    "Page": {"extended_tooltip": 1, "total": 2},
    # Table has 4 sub-elements (4 IDs: base, +1 ContextMenu, +2 CommandBar, +3 ExtendedTooltip)
    "Table": {"context_menu": 1, "command_bar": 2, "extended_tooltip": 3, "total": 4},
    # Table column (3 IDs like field)
    "TableColumn": {"context_menu": 1, "extended_tooltip": 2, "total": 3},
}


def get_element_submenu_xml(element_name: str, base_id: int, element_type: str, indent: str = "\t") -> str:
    """
    Generate XML for element's ContextMenu and ExtendedTooltip sub-elements.

    This is critical know-how: each element type has specific sub-elements
    with IDs calculated from base_id.

    Args:
        element_name: Element name (e.g., "ТекстоваяСтрока")
        base_id: Element's base ID
        element_type: Element type (e.g., "InputField")
        indent: Indentation prefix

    Returns:
        XML string with ContextMenu and/or ExtendedTooltip
    """
    structure = _ELEMENT_ID_STRUCTURE.get(element_type, {"total": 3})
    result = []

    # ContextMenu (if element has it)
    if "context_menu" in structure:
        cm_id = base_id + structure["context_menu"]
        cm_suffix = _ELEMENT_SUFFIXES["context_menu"]
        result.append(f'{indent}<ContextMenu name="{element_name}{cm_suffix}" id="{cm_id}"/>')

    # CommandBar (only for Table)
    if "command_bar" in structure:
        cb_id = base_id + structure["command_bar"]
        cb_suffix = _ELEMENT_SUFFIXES["command_bar"]
        result.append(f'{indent}<AutoCommandBar name="{element_name}{cb_suffix}" id="{cb_id}"/>')

    # ExtendedTooltip (all elements have it)
    if "extended_tooltip" in structure:
        et_id = base_id + structure["extended_tooltip"]
        et_suffix = _ELEMENT_SUFFIXES["extended_tooltip"]
        result.append(f'{indent}<ExtendedTooltip name="{element_name}{et_suffix}" id="{et_id}"/>')

    return "\n".join(result)


def get_data_path_xml(
    attribute_name: str,
    is_form_attribute: bool = False,
    is_value_table: bool = False,
    tabular_section: Optional[str] = None,
    indent: str = "\t"
) -> str:
    """
    Generate DataPath XML element.

    This is critical know-how: DataPath format depends on attribute location:
    - Object attribute: Объект.AttributeName
    - Form attribute: AttributeName (no prefix)
    - TabularSection column: Объект.TSName.ColumnName
    - ValueTable column: TSName.ColumnName (no Объект prefix)

    Args:
        attribute_name: Attribute name
        is_form_attribute: True if this is a form-level attribute
        is_value_table: True if inside ValueTable (not TabularSection)
        tabular_section: TabularSection/ValueTable name (for columns)
        indent: Indentation prefix

    Returns:
        XML string like "<DataPath>Объект.Name</DataPath>"
    """
    if tabular_section:
        # Column in table
        if is_value_table:
            path = f"{tabular_section}.{attribute_name}"
        else:
            path = f"Объект.{tabular_section}.{attribute_name}"
    elif is_form_attribute:
        # Form-level attribute (no Объект prefix)
        path = attribute_name
    else:
        # Object-level attribute
        path = f"Объект.{attribute_name}"

    return f'{indent}<DataPath>{path}</DataPath>'


def get_table_data_path_xml(
    tabular_section: str,
    is_value_table: bool = False,
    is_dynamic_list: bool = False,
    indent: str = "\t"
) -> str:
    """
    Generate DataPath XML for Table element.

    Args:
        tabular_section: TabularSection or ValueTable name
        is_value_table: True if this is a ValueTable
        is_dynamic_list: True if this is a DynamicList
        indent: Indentation prefix

    Returns:
        XML string with DataPath
    """
    if is_value_table or is_dynamic_list:
        path = tabular_section
    else:
        path = f"Объект.{tabular_section}"

    return f'{indent}<DataPath>{path}</DataPath>'


def get_line_number_data_path_xml(
    tabular_section: str,
    is_value_table: bool = False,
    indent: str = "\t"
) -> str:
    """
    Generate DataPath XML for LineNumber column in table.

    Args:
        tabular_section: TabularSection or ValueTable name
        is_value_table: True if this is a ValueTable
        indent: Indentation prefix

    Returns:
        XML string with DataPath for line number
    """
    if is_value_table:
        path = f"{tabular_section}.НомерСтроки"
    else:
        path = f"Объект.{tabular_section}.НомерСтроки"

    return f'{indent}<DataPath>{path}</DataPath>'


def get_element_id_increment(element_type: str) -> int:
    """
    Get ID increment for element type.

    Each element reserves multiple IDs for sub-elements.
    This returns how many IDs to skip for next element.

    Args:
        element_type: Element type name

    Returns:
        Number of IDs this element uses
    """
    structure = _ELEMENT_ID_STRUCTURE.get(element_type)
    if structure:
        return structure["total"]
    return 3  # Default: assume 3 (field with ContextMenu + ExtendedTooltip)


def get_element_structure(element_type: str) -> Optional[Dict[str, int]]:
    """
    Get full ID structure for element type.

    Returns dict with sub-element offsets and total count.

    Args:
        element_type: Element type name

    Returns:
        Dict with 'context_menu', 'extended_tooltip', 'command_bar', 'total' offsets
        or None if unknown element type
    """
    return _ELEMENT_ID_STRUCTURE.get(element_type)


# ============================================================================
# INTERNAL API
# ============================================================================

# ============================================================================
# OPAQUE PREDICATES (Anti-LLM Protection)
# Mathematical expressions that always return True or False
# but are difficult for static analysis / LLM to simplify
# ============================================================================


# ============================================================================
# FAKE CODE PATHS (Anti-LLM Distraction)
# Realistic-looking but never-executed code to waste LLM context
# ============================================================================


# ============================================================================
# v2.55.0+ TEMPLATE PROTECTION (ENCODED JINJA2 TEMPLATES)
# ============================================================================
# Templates are stored as compressed base64 blobs in release builds.
# This protects know-how in .j2 files from casual inspection.
# In development mode, returns None (falls back to file loading).
# ============================================================================

# Placeholder for embedded templates (populated by build_release.py)
# Format: {"template_name": "base64_compressed_content", ...}

def get_embedded_template(template_name: str) -> Optional[str]:
    """Community edition: templates always loaded from files, not embedded."""
    return None


def has_embedded_templates() -> bool:
    """Community edition: no embedded templates."""
    return False


def get_all_template_names() -> List[str]:
    """Community edition: no embedded templates."""
    return []
