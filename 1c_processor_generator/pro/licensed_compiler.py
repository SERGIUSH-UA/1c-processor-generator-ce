"""
Licensed EPF Compiler wrapper for 1C Processor Generator PRO.

Wraps EPFCompiler with license checking before compilation.
"""

import sys
import logging
from pathlib import Path
from typing import Optional

try:
    # When running as compiled .pyd
    from license import get_license_manager
except ImportError:
    # When running as part of package
    from .license import get_license_manager

logger = logging.getLogger(__name__)


class LicensedEPFCompiler:
    """
    Wrapper around EPFCompiler with license checking.

    This class provides the same interface as EPFCompiler but adds
    license verification before any compilation operation.

    Usage:
        >>> compiler = LicensedEPFCompiler()
        >>> if compiler.platform_path:
        ...     compiler.compile_epf(xml_root, output_epf)  # License checked internally
    """

    def __init__(
        self,
        platform_path: Optional[str] = None,
        use_persistent_ib: bool = True
    ):
        """
        Initialize Licensed EPF Compiler.

        Args:
            platform_path: Explicit path to 1C platform executable.
                          If not specified, auto-detection is performed.
            use_persistent_ib: Use persistent IB cache (faster by 3-5 sec).
        """
        self._platform_path = platform_path
        self._use_persistent_ib = use_persistent_ib
        self._compiler = None  # Lazy initialization
        self._license_mgr = get_license_manager()

    @property
    def platform_path(self) -> Optional[Path]:
        """Get platform path (lazy init compiler to check)."""
        self._ensure_compiler()
        return self._compiler.designer_path if self._compiler else None

    @staticmethod
    def find_platform(explicit_path: Optional[str] = None) -> Optional[Path]:
        """
        Find 1C platform path.

        This is a convenience method that wraps internal finder,
        hiding the implementation from external code.

        Args:
            explicit_path: Explicit path to platform executable (optional)

        Returns:
            Path to platform executable, or None if not found
        """
        try:
            # When running as compiled .pyd
            from designer_finder_impl import DesignerFinder
        except ImportError:
            # When running as part of package
            from .designer_finder_impl import DesignerFinder
        finder = DesignerFinder(explicit_path=explicit_path)
        return finder.find()

    @staticmethod
    def get_persistent_ib(platform_path: Path, timeout: int = 60) -> Optional[Path]:
        """
        Get or create persistent Information Base.

        This is a convenience method that wraps internal IB manager,
        hiding the implementation from external code.

        Args:
            platform_path: Path to 1C platform
            timeout: Timeout for IB creation in seconds

        Returns:
            Path to persistent IB, or None on error
        """
        try:
            # When running as compiled .pyd
            from persistent_ib_impl import PersistentIBManager
        except ImportError:
            # When running as part of package
            from .persistent_ib_impl import PersistentIBManager
        manager = PersistentIBManager(platform_path)
        return manager.get_or_create(timeout=timeout)

    @property
    def use_persistent_ib(self) -> bool:
        """Get persistent IB setting."""
        return self._use_persistent_ib

    @property
    def last_temp_ib(self) -> Optional[Path]:
        """Get last temp IB path (for tests)."""
        if self._compiler:
            return self._compiler.last_temp_ib
        return None

    def compile_epf(
        self,
        xml_root: Path,
        output_epf: Path,
        timeout: int = 120,
    ) -> bool:
        """
        Compile XML processor to EPF format via Designer.

        This method checks PRO license before compilation.

        Args:
            xml_root: Path to main processor XML file
            output_epf: Path to output EPF file
            timeout: Execution timeout in seconds

        Returns:
            True if compilation successful, False otherwise
        """
        # Check license
        if not self._check_license("epf_compilation"):
            return False

        # Ensure compiler is initialized
        self._ensure_compiler()

        if not self._compiler:
            logger.error("EPFCompiler not initialized")
            return False

        # Delegate to actual compiler
        return self._compiler.compile_epf(xml_root, output_epf, timeout)

    def compile_epf_with_configuration(
        self,
        processor_xml_dir: Path,
        output_epf: Path,
        processor,
        requirements,
        timeout: int = 180,
        ignore_validation_errors: bool = False,
    ) -> bool:
        """
        Compile EPF with metadata support (CatalogRef/DocumentRef).

        This method checks PRO license before compilation.

        Args:
            processor_xml_dir: Directory with generated XML
            output_epf: Path to output EPF file
            processor: Processor object from models.py
            requirements: MetadataRequirements from metadata_analyzer.py
            timeout: Execution timeout in seconds
            ignore_validation_errors: Ignore BSL validation errors

        Returns:
            True if compilation successful, False otherwise
        """
        # Check license for EPF compilation
        if not self._check_license("epf_compilation"):
            return False

        # Check license for CheckConfig if enabled
        if processor.validation.check_config_enabled:
            if not self._check_license("check_config", show_message=False):
                # Downgrade: disable check_config but continue
                logger.warning("CheckConfig disabled (requires PRO license)")
                processor.validation.check_config_enabled = False

        # Ensure compiler is initialized
        self._ensure_compiler()

        if not self._compiler:
            logger.error("EPFCompiler not initialized")
            return False

        # Delegate to actual compiler
        return self._compiler.compile_epf_with_configuration(
            processor_xml_dir,
            output_epf,
            processor,
            requirements,
            timeout,
            ignore_validation_errors,
        )

    def decompile_epf(
        self,
        epf_path: Path,
        output_dir: Path,
        timeout: int = 120,
    ) -> bool:
        """
        Decompile EPF back to XML format.

        This method checks PRO license before decompilation.

        Args:
            epf_path: Path to EPF file to decompile
            output_dir: Directory for XML output
            timeout: Execution timeout in seconds

        Returns:
            True if decompilation successful, False otherwise
        """
        # Check license for decompilation (PRO feature)
        if not self._check_license("epf_compilation"):
            return False

        self._ensure_compiler()

        if not self._compiler:
            logger.error("EPFCompiler not initialized")
            return False

        return self._compiler.decompile_epf(epf_path, output_dir, timeout)

    # =========================================================================
    # Private Methods
    # =========================================================================

    def _ensure_compiler(self) -> None:
        """Lazy initialize EPFCompiler."""
        if self._compiler is None:
            try:
                # When running as compiled .pyd
                from epf_compiler_impl import EPFCompiler
            except ImportError:
                # When running as part of package
                from .epf_compiler_impl import EPFCompiler
            self._compiler = EPFCompiler(
                self._platform_path,
                use_persistent_ib=self._use_persistent_ib,
            )

    def _check_license(self, feature: str, show_message: bool = True) -> bool:
        """
        Check if feature is licensed.

        Community edition: all local features are free.
        Only cloud_compilation requires PRO license.
        """
        if feature != "cloud_compilation":
            return True

        # Server mode bypass
        import os
        if os.environ.get("PG_PRO_MODE", "").strip() == "1":
            return True

        is_licensed, error_message = self._license_mgr.check_pro_feature(feature)

        if not is_licensed and show_message:
            self._show_upgrade_message(error_message)

        return is_licensed

    def _show_upgrade_message(self, error_message: str) -> None:
        """Show upgrade message to user."""
        print()
        print(error_message)
        print()


# =============================================================================
# Convenience function
# =============================================================================

def create_compiler(
    platform_path: Optional[str] = None,
    use_persistent_ib: bool = True,
):
    """
    Create compiler with license checking.

    This function always returns LicensedEPFCompiler which performs
    license verification before any operation.

    Args:
        platform_path: Explicit path to 1C platform
        use_persistent_ib: Use persistent IB cache

    Returns:
        LicensedEPFCompiler instance
    """
    return LicensedEPFCompiler(platform_path, use_persistent_ib)
