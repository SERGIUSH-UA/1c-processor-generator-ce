"""
PRO Cloud compilation integration tests (v2.75.0+).

Tests the full CLI flow with --cloud flag using mocked HTTP and license.
"""

import base64
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta, timezone
from io import BytesIO
from importlib import import_module

import pytest


# Skip on non-Windows
pytestmark = pytest.mark.skipif(
    os.name != 'nt',
    reason="PRO module requires Windows"
)


# Import modules for patch.object()
main_mod = import_module('1c_processor_generator.__main__')
cloud_mod = import_module('1c_processor_generator.pro.cloud_compiler')


@pytest.fixture
def mock_valid_license():
    """Mock a valid PRO license with cloud_compilation feature."""
    mock_token = MagicMock()
    mock_token.token = "test-jwt-token"
    mock_token.features = ["epf_compilation", "cloud_compilation"]
    mock_token.expires_at = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
    mock_token.watermark_removed = True
    mock_token.license_type = "year"
    mock_token.machine_id = "test-machine"

    mock_mgr = MagicMock()
    mock_mgr._get_valid_token.return_value = mock_token
    mock_mgr.check_pro_feature.return_value = (True, "")
    mock_mgr.machine_id = "test-machine"
    return mock_mgr


@pytest.fixture
def sample_project(tmp_path):
    """Create a sample project for testing."""
    config = tmp_path / "config.yaml"
    config.write_text(
        "processor:\n"
        "  name: CloudTestProcessor\n"
        "  synonym_ru: Тест хмарної компіляції\n"
        "  attributes:\n"
        "    - name: TestField\n"
        "      type: string\n",
        encoding="utf-8",
    )

    handlers = tmp_path / "handlers.bsl"
    handlers.write_text(
        "#Область ПриОткрытии\n"
        "  Сообщить(\"Привіт\");\n"
        "#КонецОбласти\n",
        encoding="utf-8",
    )

    output = tmp_path / "output"
    return tmp_path, config, handlers, output


class TestCloudCompileFlow:
    """Test full --cloud compile flow through _cloud_compile."""

    def _make_cloud_response(self, processor_name="CloudTestProcessor"):
        """Create a mock successful cloud response."""
        fake_epf = b"COMPILED_EPF_DATA_CLOUD"
        return {
            "success": True,
            "output_base64": base64.b64encode(fake_epf).decode("ascii"),
            "processor_name": processor_name,
            "messages": ["Compiled successfully"],
        }

    def test_cloud_compile_full_flow(self, mock_valid_license, sample_project):
        """Test complete --cloud compilation flow."""
        _, config, handlers, output = sample_project

        # Mock args
        args = MagicMock()
        args.config = config
        args.handlers_file = handlers
        args.handlers = None
        args.output = output
        args.output_format = "epf"
        args.cloud = True
        args.ignore_validation_errors = False

        # Mock health check
        health_response = MagicMock()
        health_response.status = 200
        health_response.__enter__ = Mock(return_value=health_response)
        health_response.__exit__ = Mock(return_value=False)

        # Mock version check
        version_response = MagicMock()
        version_response.read.return_value = json.dumps({"version": "1.0.0"}).encode("utf-8")
        version_response.__enter__ = Mock(return_value=version_response)
        version_response.__exit__ = Mock(return_value=False)

        # Mock compile
        compile_response = MagicMock()
        compile_response.read.return_value = json.dumps(self._make_cloud_response()).encode("utf-8")
        compile_response.__enter__ = Mock(return_value=compile_response)
        compile_response.__exit__ = Mock(return_value=False)

        def urlopen_side_effect(req, **kwargs):
            url = req.full_url if hasattr(req, 'full_url') else str(req)
            if "health" in url:
                return health_response
            elif "version" in url:
                return version_response
            else:
                return compile_response

        with patch.object(main_mod, 'get_license_manager', return_value=mock_valid_license):
            with patch('urllib.request.urlopen', side_effect=urlopen_side_effect):
                with patch.object(cloud_mod, 'generate_machine_id', return_value="test-machine"):
                    result = main_mod._cloud_compile(args)

        assert result == 0

        # Verify EPF was created
        epf_file = output / "CloudTestProcessor.epf"
        assert epf_file.exists()
        assert epf_file.read_bytes() == b"COMPILED_EPF_DATA_CLOUD"

    def test_cloud_compile_no_license(self, sample_project):
        """Test --cloud without PRO license."""
        _, config, handlers, output = sample_project

        args = MagicMock()
        args.config = config
        args.output_format = "epf"
        args.cloud = True

        mock_mgr = MagicMock()
        mock_mgr.check_pro_feature.return_value = (False, "cloud_compilation потребує PRO ліцензії")

        with patch.object(main_mod, 'get_license_manager', return_value=mock_mgr):
            result = main_mod._cloud_compile(args)

        assert result == 1

    def test_cloud_compile_service_unavailable(self, mock_valid_license, sample_project):
        """Test --cloud when service is down."""
        import urllib.error

        _, config, handlers, output = sample_project

        args = MagicMock()
        args.config = config
        args.handlers_file = handlers
        args.handlers = None
        args.output = output
        args.output_format = "epf"
        args.cloud = True
        args.ignore_validation_errors = False

        with patch.object(main_mod, 'get_license_manager', return_value=mock_valid_license):
            with patch('urllib.request.urlopen', side_effect=urllib.error.URLError("Connection refused")):
                with patch.object(cloud_mod, 'generate_machine_id', return_value="test-machine"):
                    result = main_mod._cloud_compile(args)

        # Should fail because health check fails
        assert result == 1


class TestCloudArgParsing:
    """Test --cloud argument parsing."""

    def test_cloud_flag_parsed(self):
        """Test that --cloud flag is recognized by argparse."""
        parser = main_mod.create_parser()

        args = parser.parse_args([
            "yaml",
            "--config", "test.yaml",
            "--handlers-file", "handlers.bsl",
            "--output-format", "epf",
            "--cloud",
        ])

        assert args.cloud is True
        assert args.output_format == "epf"

    def test_cloud_flag_default_false(self):
        """Test that --cloud defaults to False."""
        parser = main_mod.create_parser()
        args = parser.parse_args([
            "yaml",
            "--config", "test.yaml",
        ])

        assert args.cloud is False
