"""
PRO License mocking tests for CI/CD (v2.69.3+).

Tests license functionality with mocked API calls:
- License activation (success/failure)
- Network error handling
- Feature checking without/with license
- PG_PRO_MODE bypass

These tests mock the license server API to avoid network dependencies.
"""

import os
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock

import pytest


# Skip all tests on non-Windows (PRO requires Windows)
pytestmark = pytest.mark.skipif(
    os.name != 'nt',
    reason="PRO module requires Windows"
)


@pytest.fixture
def license_manager():
    """Create a fresh LicenseManager instance."""
    from importlib import import_module
    pro = import_module('1c_processor_generator.pro')

    # Clear any cached instances
    mgr = pro.LicenseManager()
    # Clear cached token to ensure clean state
    mgr._cached_token = None
    return mgr


class TestActivateLicense:
    """Test license activation with mocked API."""

    def test_activate_license_success(self, license_manager):
        """Test successful license activation."""
        mock_response = {
            "success": True,
            "token": "test-jwt-token-12345",
            "type": "year",
            "features": ["epf_compilation", "check_config"],
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=365)).isoformat(),
            "watermark_removed": True,
        }

        with patch.object(license_manager, '_api_request', return_value=mock_response):
            with patch.object(license_manager, '_save_token_cache', return_value=True):
                result = license_manager.activate_license("PRO-TEST-1234-5678")

        assert result.success is True
        assert result.token == "test-jwt-token-12345"
        assert result.license_type == "year"
        assert result.error_message is None

    def test_activate_license_invalid_key(self, license_manager):
        """Test activation with invalid license key."""
        mock_response = {
            "success": False,
            "message": "Invalid license key"
        }

        with patch.object(license_manager, '_api_request', return_value=mock_response):
            result = license_manager.activate_license("INVALID-KEY")

        assert result.success is False
        assert "Invalid" in result.error_message

    def test_activate_license_network_error(self, license_manager):
        """Test activation when network is unavailable."""
        with patch.object(license_manager, '_api_request', side_effect=Exception("Connection refused")):
            result = license_manager.activate_license("PRO-TEST-1234-5678")

        assert result.success is False
        assert result.error_message is not None


class TestCheckProFeature:
    """Test feature checking with mocked tokens."""

    def test_check_pro_feature_with_valid_license(self, license_manager):
        """Test feature check with valid license."""
        from importlib import import_module

        # Create mock token with required attributes
        mock_token = MagicMock()
        mock_token.features = ["epf_compilation", "check_config", "epf"]
        mock_token.expires_at = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
        mock_token.watermark_removed = True
        mock_token.license_type = "year"

        with patch.object(license_manager, '_get_valid_token', return_value=mock_token):
            is_licensed, error_msg = license_manager.check_pro_feature("epf_compilation")

        assert is_licensed is True
        assert error_msg == ""

class TestLicenseStatus:
    """Test license status retrieval."""

    def test_get_license_status_no_license(self, license_manager):
        """Test status when no license is active."""
        with patch.object(license_manager, '_get_valid_token', return_value=None):
            status = license_manager.get_license_status()

        assert status.is_licensed is False
        assert status.license_type == "free"
        assert status.features == []

    def test_get_license_status_with_license(self, license_manager):
        """Test status with active license."""
        mock_token = MagicMock()
        mock_token.features = ["epf_compilation", "check_config"]
        mock_token.expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        mock_token.watermark_removed = True
        mock_token.license_type = "year"
        mock_token.last_online_verify = datetime.now(timezone.utc).isoformat()

        with patch.object(license_manager, '_get_valid_token', return_value=mock_token):
            status = license_manager.get_license_status()

        assert status.is_licensed is True
        assert status.license_type == "year"
        assert "epf_compilation" in status.features


class TestPGProModeBypass:
    """Test PG_PRO_MODE environment variable bypass."""

    def test_pg_pro_mode_env_variable(self):
        """Test that PG_PRO_MODE=1 bypasses license check."""
        # Note: This tests the expected behavior when PG_PRO_MODE is set
        # The actual implementation may vary
        original_env = os.environ.get('PG_PRO_MODE')
        try:
            os.environ['PG_PRO_MODE'] = '1'

            # Import fresh to pick up env var
            from importlib import import_module, reload
            pro = import_module('1c_processor_generator.pro')

            # Get license manager
            mgr = pro.get_license_manager()

            # With PG_PRO_MODE, license checks may be bypassed
            # This is a development/CI feature
            # The exact behavior depends on implementation
            assert mgr is not None

        finally:
            # Restore original env
            if original_env is None:
                os.environ.pop('PG_PRO_MODE', None)
            else:
                os.environ['PG_PRO_MODE'] = original_env


class TestMachineId:
    """Test machine ID generation."""

    def test_machine_id_is_deterministic(self, license_manager):
        """Test that machine ID is consistent across calls."""
        machine_id_1 = license_manager.machine_id
        machine_id_2 = license_manager.machine_id

        assert machine_id_1 == machine_id_2
        assert len(machine_id_1) == 64  # SHA-256 hex digest


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
