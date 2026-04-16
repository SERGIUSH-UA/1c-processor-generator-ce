"""
PRO module for 1C Processor Generator.

Community Edition: all local features are free.
Cloud compilation requires PRO license.
"""


# =============================================================================
# PUBLIC API - License management only
# =============================================================================
# CLI-first approach: End users should use CLI commands, not import classes.
# Only license-related classes are exported for activate/status commands.

from .license import LicenseManager, get_license_manager
from .exceptions import LicenseError, ActivationError, VerificationError

# =============================================================================
# INTERNAL IMPORTS - Not part of public API
# =============================================================================
# These are used internally by CLI (__main__.py).
# Do NOT import these directly - use CLI instead.

from .licensed_compiler import LicensedEPFCompiler
from .utils import generate_uuid

# v2.67.0: EPF version helper (used by __main__.py)
try:
    from .epf_version_helper import adjust_platform_version
except ImportError:
    adjust_platform_version = None

# v2.58.0: Excel -> MXL conversion (PRO feature)
try:
    from .excel_to_mxl import ExcelToMXLConverter, convert_excel_to_mxl
    from .excel_reader import check_openpyxl_available
    EXCEL_TO_MXL_AVAILABLE = check_openpyxl_available()
except ImportError:
    EXCEL_TO_MXL_AVAILABLE = False
    ExcelToMXLConverter = None
    convert_excel_to_mxl = None

# =============================================================================
# PUBLIC EXPORTS - Minimal surface for protection
# =============================================================================
# Only license classes are public. Everything else is internal.
# Users should use CLI: python -m 1c_processor_generator yaml --output-format epf

__all__ = [
    # License management (public API)
    "LicenseManager",
    "get_license_manager",
    "LicenseError",
    "ActivationError",
    "VerificationError",
    # v2.58.0: Excel -> MXL (PRO feature)
    "EXCEL_TO_MXL_AVAILABLE",
    "ExcelToMXLConverter",
    "convert_excel_to_mxl",
]
