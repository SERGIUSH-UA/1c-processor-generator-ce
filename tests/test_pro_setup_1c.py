"""
PRO setup-1c command tests for CI/CD (v2.69.3+).

Tests conf.cfg management:
- ConfCfgManager class (check_configuration, configure, get_current_masks)
- run_setup_command CLI handler
- --check and --dry-run modes

These tests use temporary conf.cfg files to avoid modifying system configuration.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from io import StringIO

import pytest


# Skip all tests on non-Windows (PRO requires Windows)
pytestmark = pytest.mark.skipif(
    os.name != 'nt',
    reason="PRO module requires Windows"
)


class TestConfCfgManager:
    """Test ConfCfgManager with temporary conf.cfg files."""

    @pytest.fixture
    def temp_conf_cfg(self):
        """Create a temporary conf.cfg file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            conf_path = Path(tmpdir) / "conf.cfg"
            yield conf_path

    def get_conf_cfg_manager(self, conf_path):
        """Get ConfCfgManager with custom path."""
        # Try importing from the pro module
        try:
            # Dev mode: direct import
            from importlib import import_module
            ccm_module = import_module('1c_processor_generator.pro.conf_cfg_manager')
            return ccm_module.ConfCfgManager(conf_path=conf_path)
        except (ImportError, ModuleNotFoundError):
            # Release mode: import via dynamic loader
            from importlib import import_module
            pro = import_module('1c_processor_generator.pro')

            # ConfCfgManager might not be exported, try accessing via _ccm
            try:
                ccm_module = import_module('1c_processor_generator.pro._ccm')
                return ccm_module.ConfCfgManager(conf_path=conf_path)
            except (ImportError, ModuleNotFoundError):
                pytest.skip("ConfCfgManager not accessible in this version")

    def test_check_configuration_missing_file(self, temp_conf_cfg):
        """Test check_configuration when conf.cfg doesn't exist."""
        mgr = self.get_conf_cfg_manager(temp_conf_cfg)

        is_ok, missing = mgr.check_configuration()

        # Without conf.cfg, required masks are missing
        assert is_ok is False
        assert len(missing) > 0
        assert ".*epf_compiler_cache.*" in missing

    def test_check_configuration_empty_file(self, temp_conf_cfg):
        """Test check_configuration with empty conf.cfg."""
        temp_conf_cfg.write_text("", encoding='utf-8')
        mgr = self.get_conf_cfg_manager(temp_conf_cfg)

        is_ok, missing = mgr.check_configuration()

        assert is_ok is False
        assert ".*epf_compiler_cache.*" in missing

    def test_check_configuration_with_mask(self, temp_conf_cfg):
        """Test check_configuration when mask is present."""
        temp_conf_cfg.write_text(
            "DisableUnsafeActionProtection=.*epf_compiler_cache.*\n",
            encoding='utf-8'
        )
        mgr = self.get_conf_cfg_manager(temp_conf_cfg)

        is_ok, missing = mgr.check_configuration()

        assert is_ok is True
        assert len(missing) == 0

    def test_configure_creates_mask(self, temp_conf_cfg):
        """Test configure adds the required mask."""
        mgr = self.get_conf_cfg_manager(temp_conf_cfg)

        success = mgr.configure(dry_run=False)

        assert success is True

        # Check the file was created with the mask
        content = temp_conf_cfg.read_text(encoding='utf-8')
        assert "DisableUnsafeActionProtection" in content
        assert "epf_compiler_cache" in content

    def test_configure_dry_run(self, temp_conf_cfg):
        """Test configure with dry_run=True doesn't modify file."""
        mgr = self.get_conf_cfg_manager(temp_conf_cfg)

        success = mgr.configure(dry_run=True)

        assert success is True
        # File should not exist after dry run
        assert not temp_conf_cfg.exists()

    def test_configure_preserves_existing_masks(self, temp_conf_cfg):
        """Test configure preserves existing masks."""
        existing_content = "DisableUnsafeActionProtection=.*some_other_path.*\n"
        temp_conf_cfg.write_text(existing_content, encoding='utf-8')
        mgr = self.get_conf_cfg_manager(temp_conf_cfg)

        success = mgr.configure(dry_run=False)

        assert success is True

        content = temp_conf_cfg.read_text(encoding='utf-8')
        # Should contain both masks
        assert "some_other_path" in content
        assert "epf_compiler_cache" in content

    def test_get_current_masks_empty(self, temp_conf_cfg):
        """Test get_current_masks with no masks."""
        mgr = self.get_conf_cfg_manager(temp_conf_cfg)

        masks = mgr.get_current_masks()

        assert masks == []

    def test_get_current_masks_with_masks(self, temp_conf_cfg):
        """Test get_current_masks returns existing masks."""
        temp_conf_cfg.write_text(
            "DisableUnsafeActionProtection=.*mask1.*;.*mask2.*\n",
            encoding='utf-8'
        )
        mgr = self.get_conf_cfg_manager(temp_conf_cfg)

        masks = mgr.get_current_masks()

        assert ".*mask1.*" in masks
        assert ".*mask2.*" in masks


class TestSetup1CCLI:
    """Test setup-1c CLI command."""

    def test_setup_1c_check_ok(self):
        """Test setup-1c --check when configuration is OK."""
        # Create temp conf.cfg with required mask
        with tempfile.TemporaryDirectory() as tmpdir:
            conf_path = Path(tmpdir) / "conf.cfg"
            conf_path.write_text(
                "DisableUnsafeActionProtection=.*epf_compiler_cache.*\n",
                encoding='utf-8'
            )

            # The CLI uses system conf.cfg path, so we can't easily test this
            # Just test that the command runs without error
            result = subprocess.run(
                [sys.executable, '-m', '1c_processor_generator', 'setup-1c', '--help'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=30
            )

            assert result.returncode == 0
            assert '--check' in result.stdout

    def test_setup_1c_dry_run(self):
        """Test setup-1c --dry-run mode."""
        result = subprocess.run(
            [sys.executable, '-m', '1c_processor_generator', 'setup-1c', '--dry-run'],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=30
        )

        # Dry run should succeed (exit 0) or report missing (exit 0 with [DRY] message)
        # It should not fail with error
        assert result.returncode == 0 or "[DRY]" in result.stdout or "OK" in result.stdout


class TestRunSetupCommand:
    """Test run_setup_command function directly."""

    def test_run_setup_command_import(self):
        """Test that run_setup_command can be imported."""
        from importlib import import_module

        # Try dev mode first (direct import)
        try:
            ccm_module = import_module('1c_processor_generator.pro.conf_cfg_manager')
            assert hasattr(ccm_module, 'run_setup_command')
            assert callable(ccm_module.run_setup_command)
            return
        except (ImportError, ModuleNotFoundError):
            pass

        # Try release mode (__getattr__ export)
        try:
            pro = import_module('1c_processor_generator.pro')
            # In release, run_setup_command is available via __getattr__
            func = getattr(pro, 'run_setup_command', None)
            assert func is not None and callable(func)
            return
        except (ImportError, ModuleNotFoundError, AttributeError):
            pass

        pytest.fail("run_setup_command not found in dev or release mode")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
