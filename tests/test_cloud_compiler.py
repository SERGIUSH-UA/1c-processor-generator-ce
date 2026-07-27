"""
Unit tests for CloudCompiler (v2.75.0+).

Tests cloud EPF compilation with mocked HTTP:
- Template file collection from YAML
- Auth headers construction
- Successful compilation (base64 EPF -> file)
- Error handling (401, 429, 500, 503, timeout)
- Health check
- Version check
"""

import base64
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, PropertyMock
from datetime import datetime, timedelta, timezone
from io import BytesIO

import pytest


# Skip on non-Windows
pytestmark = pytest.mark.skipif(
    os.name != 'nt',
    reason="PRO module requires Windows"
)


@pytest.fixture
def mock_license_manager():
    """Create a mocked LicenseManager with valid token."""
    mgr = MagicMock()
    mock_token = MagicMock()
    mock_token.token = "test-jwt-token-12345"
    mock_token.features = ["epf_compilation", "cloud_compilation"]
    mock_token.expires_at = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
    mock_token.watermark_removed = True
    mock_token.license_type = "year"
    mgr._get_valid_token.return_value = mock_token
    return mgr


@pytest.fixture
def cloud_compiler(mock_license_manager):
    """Create a CloudCompiler instance with mocked license."""
    from importlib import import_module
    mod = import_module('1c_processor_generator.pro.cloud_compiler')
    compiler = mod.CloudCompiler(mock_license_manager)
    compiler._machine_id = "test-machine-id-abc123"
    return compiler


@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary project with config and handlers."""
    config = tmp_path / "config.yaml"
    config.write_text(
        "name: TestProcessor\n"
        "synonym_ru: Тест\n"
        "attributes:\n"
        "  - name: Field1\n"
        "    type: string\n",
        encoding="utf-8",
    )

    handlers = tmp_path / "handlers.bsl"
    handlers.write_text(
        "#Область ПриОткрытии\n"
        "  // test\n"
        "#КонецОбласти\n",
        encoding="utf-8",
    )

    return tmp_path, config, handlers


@pytest.fixture
def temp_project_with_templates(tmp_path):
    """Create a temporary project with templates section in YAML."""
    # Create template files
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "card.html").write_text("<html>test</html>", encoding="utf-8")
    (templates_dir / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\nfake_png_data")

    config = tmp_path / "config.yaml"
    config.write_text(
        "name: TestProcessor\n"
        "synonym_ru: Тест\n"
        "templates:\n"
        "  - name: Card\n"
        "    type: HTMLDocument\n"
        "    file: templates/card.html\n"
        "  - name: Logo\n"
        "    type: SpreadsheetDocument\n"
        "    file: templates/logo.png\n",
        encoding="utf-8",
    )

    handlers = tmp_path / "handlers.bsl"
    handlers.write_text("// empty\n", encoding="utf-8")

    return tmp_path, config, handlers


class TestAuthHeaders:
    """Test authorization header construction."""

    def test_auth_headers_contain_bearer_token(self, cloud_compiler):
        """Auth headers should include Bearer token from license."""
        headers = cloud_compiler._get_auth_headers()
        assert headers["Authorization"] == "Bearer test-jwt-token-12345"

    def test_auth_headers_contain_machine_id(self, cloud_compiler):
        """Auth headers should include X-Machine-ID."""
        headers = cloud_compiler._get_auth_headers()
        assert headers["X-Machine-ID"] == "test-machine-id-abc123"

    def test_auth_headers_contain_client_type(self, cloud_compiler):
        """Auth headers should identify as CLI client."""
        headers = cloud_compiler._get_auth_headers()
        assert headers["X-Client-Type"] == "cli"

    def test_auth_headers_no_token_raises(self, mock_license_manager):
        """Should raise CloudAuthError when no valid token."""
        from importlib import import_module
        mod = import_module('1c_processor_generator.pro.cloud_compiler')

        mock_license_manager._get_valid_token.return_value = None
        compiler = mod.CloudCompiler(mock_license_manager)

        with pytest.raises(mod.CloudAuthError):
            compiler._get_auth_headers()


class TestTemplateFileCollection:
    """Test collecting template files from YAML config."""

    def test_collect_html_template(self, cloud_compiler, temp_project_with_templates):
        """HTML templates should be collected as text."""
        tmp_path, config, _ = temp_project_with_templates
        yaml_content = config.read_text(encoding="utf-8")

        files = cloud_compiler._collect_template_files(config, yaml_content)

        assert "templates/card.html" in files
        assert files["templates/card.html"] == "<html>test</html>"

    def test_collect_binary_template_as_base64(self, cloud_compiler, temp_project_with_templates):
        """Binary templates should be bare base64 — no prefix, as the API contract expects."""
        tmp_path, config, _ = temp_project_with_templates
        yaml_content = config.read_text(encoding="utf-8")

        files = cloud_compiler._collect_template_files(config, yaml_content)

        assert "templates/logo.png" in files
        b64_data = files["templates/logo.png"]
        assert not b64_data.startswith("base64:")

        # Server decodes with validate=True — any non-alphabet char (like ':') would be rejected
        decoded = base64.b64decode(b64_data, validate=True)
        assert decoded == b"\x89PNG\r\n\x1a\nfake_png_data"

    def test_no_templates_returns_empty(self, cloud_compiler, temp_project):
        """Config without templates should return empty dict."""
        _, config, _ = temp_project
        yaml_content = config.read_text(encoding="utf-8")

        files = cloud_compiler._collect_template_files(config, yaml_content)
        assert files == {}

    def test_missing_template_file_skipped(self, cloud_compiler, tmp_path):
        """Missing template files should be skipped with warning."""
        config = tmp_path / "config.yaml"
        config.write_text(
            "name: Test\n"
            "templates:\n"
            "  - name: Missing\n"
            "    type: HTMLDocument\n"
            "    file: nonexistent.html\n",
            encoding="utf-8",
        )
        yaml_content = config.read_text(encoding="utf-8")

        files = cloud_compiler._collect_template_files(config, yaml_content)
        assert "nonexistent.html" not in files

    @pytest.mark.parametrize("filename,payload", [
        ("invoice.mxl", b"\xef\xbb\xbf<?xml version=\"1.0\"?><document/>"),
        ("invoice.xlsx", b"PK\x03\x04fake_xlsx_zip_bytes"),
    ])
    def test_spreadsheet_templates_are_base64(self, cloud_compiler, tmp_path, filename, payload):
        """
        The reported bug was hit by .mxl/.xlsx specifically - both must be sent
        as bare base64 the server can decode with validate=True.
        """
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        (templates_dir / filename).write_bytes(payload)

        config = tmp_path / "config.yaml"
        config.write_text(
            "name: Test\n"
            "templates:\n"
            "  - name: Invoice\n"
            "    type: SpreadsheetDocument\n"
            f"    file: templates/{filename}\n",
            encoding="utf-8",
        )

        files = cloud_compiler._collect_template_files(config, config.read_text(encoding="utf-8"))

        key = f"templates/{filename}"
        assert key in files
        assert base64.b64decode(files[key], validate=True) == payload

    def test_windows_path_separators_normalized(self, cloud_compiler, tmp_path):
        """
        Keys must be POSIX paths. A YAML written on Windows may use backslashes,
        and the server would not match them against the paths inside the config.
        """
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        (templates_dir / "card.html").write_text("<html>test</html>", encoding="utf-8")

        config = tmp_path / "config.yaml"
        config.write_text(
            "name: Test\n"
            "templates:\n"
            "  - name: Card\n"
            "    type: HTMLDocument\n"
            "    file: templates\\card.html\n",
            encoding="utf-8",
        )

        files = cloud_compiler._collect_template_files(config, config.read_text(encoding="utf-8"))

        assert "templates/card.html" in files
        assert "templates\\card.html" not in files

    def test_binary_content_with_text_extension_raises(self, cloud_compiler, tmp_path):
        """
        Sending undecodable bytes as text would silently break on the server,
        so it must fail loudly here with a fix recipe (not a UnicodeDecodeError).
        """
        from importlib import import_module
        mod = import_module('1c_processor_generator.pro.cloud_compiler')

        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        (templates_dir / "card.html").write_bytes(b"\xff\xfe\x00binary\x00")

        config = tmp_path / "config.yaml"
        config.write_text(
            "name: Test\n"
            "templates:\n"
            "  - name: Card\n"
            "    type: HTMLDocument\n"
            "    file: templates/card.html\n",
            encoding="utf-8",
        )

        with pytest.raises(mod.CloudCompileError, match="BINARY_EXTENSIONS"):
            cloud_compiler._collect_template_files(config, config.read_text(encoding="utf-8"))


class TestErrorMessageExtraction:
    """Server 400 bodies come in several shapes - none should degrade to a bare HTTP error."""

    @pytest.mark.parametrize("body,expected", [
        ({"error": "Invalid base64 content"}, "Invalid base64 content"),
        ({"detail": "Validation failed"}, "Validation failed"),
        ({"message": "Bad request"}, "Bad request"),
        ({"errors": ["first", "second"]}, "first; second"),
        ({"errors": [{"message": "structured"}]}, "structured"),
    ])
    def test_extracts_message(self, cloud_compiler, body, expected):
        assert cloud_compiler._extract_error_message(body) == expected

    def test_unknown_shape_returns_none(self, cloud_compiler):
        assert cloud_compiler._extract_error_message({"unexpected": "shape"}) is None
        assert cloud_compiler._extract_error_message("not a dict") is None


class TestHealthCheck:
    """Test cloud service health check."""

    def test_health_check_success(self, cloud_compiler):
        """Should return True when service is healthy."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)

        with patch('urllib.request.urlopen', return_value=mock_response):
            assert cloud_compiler.check_available() is True

    def test_health_check_failure(self, cloud_compiler):
        """Should return False when service is down."""
        import urllib.error
        with patch('urllib.request.urlopen', side_effect=urllib.error.URLError("Connection refused")):
            assert cloud_compiler.check_available() is False


class TestVersionCheck:
    """Test cloud service version check."""

    def test_version_success(self, cloud_compiler):
        """Should return version dict on success."""
        version_data = {"version": "1.2.3", "generator": "2.74.0"}
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(version_data).encode("utf-8")
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)

        with patch('urllib.request.urlopen', return_value=mock_response):
            result = cloud_compiler.get_version()

        assert result == version_data
        assert result["version"] == "1.2.3"

    def test_version_failure(self, cloud_compiler):
        """Should return None on failure."""
        import urllib.error
        with patch('urllib.request.urlopen', side_effect=urllib.error.URLError("timeout")):
            assert cloud_compiler.get_version() is None


class TestCompile:
    """Test cloud EPF compilation."""

    def _make_success_response(self, processor_name="TestProcessor"):
        """Helper to create a successful compile response."""
        fake_epf = b"FAKE_EPF_BINARY_DATA_1234567890"
        return {
            "success": True,
            "output_base64": base64.b64encode(fake_epf).decode("ascii"),
            "processor_name": processor_name,
            "messages": ["Compiled in 5.2s"],
        }

    def test_compile_success(self, cloud_compiler, temp_project):
        """Successful compilation should write EPF to output dir."""
        tmp_path, config, handlers = temp_project
        output_dir = tmp_path / "output"

        response_data = self._make_success_response()
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(response_data).encode("utf-8")
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)

        with patch('urllib.request.urlopen', return_value=mock_response):
            success, messages, errors = cloud_compiler.compile(
                config_path=config,
                handlers_file=handlers,
                output_dir=output_dir,
            )

        assert success is True
        assert len(errors) == 0
        assert any("EPF створено" in m for m in messages)

        # Verify EPF file was written
        epf_file = output_dir / "TestProcessor.epf"
        assert epf_file.exists()
        assert epf_file.read_bytes() == b"FAKE_EPF_BINARY_DATA_1234567890"

    def test_compile_auth_error(self, cloud_compiler, temp_project):
        """401 should return auth error."""
        _, config, handlers = temp_project
        import urllib.error

        http_error = urllib.error.HTTPError(
            url="https://gen.itdeo.tech/generate",
            code=401,
            msg="Unauthorized",
            hdrs={},
            fp=BytesIO(b'{"error": "Invalid token"}'),
        )

        with patch('urllib.request.urlopen', side_effect=http_error):
            success, messages, errors = cloud_compiler.compile(
                config_path=config,
                handlers_file=handlers,
                output_dir=Path(tempfile.mkdtemp()),
            )

        assert success is False
        assert any("автентифікації" in e for e in errors)

    def test_compile_rate_limit(self, cloud_compiler, temp_project):
        """429 should return rate limit error."""
        _, config, handlers = temp_project
        import urllib.error

        http_error = urllib.error.HTTPError(
            url="https://gen.itdeo.tech/generate",
            code=429,
            msg="Too Many Requests",
            hdrs={},
            fp=BytesIO(b'{}'),
        )

        with patch('urllib.request.urlopen', side_effect=http_error):
            success, messages, errors = cloud_compiler.compile(
                config_path=config,
                handlers_file=handlers,
                output_dir=Path(tempfile.mkdtemp()),
            )

        assert success is False
        assert any("ліміт" in e for e in errors)

    def test_compile_server_error_with_details(self, cloud_compiler, temp_project):
        """Server-side validation error should show details."""
        _, config, handlers = temp_project

        response_data = {
            "success": False,
            "errors": ["YAML validation: missing 'name' field", "BSL syntax error on line 5"],
        }
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(response_data).encode("utf-8")
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)

        with patch('urllib.request.urlopen', return_value=mock_response):
            success, messages, errors = cloud_compiler.compile(
                config_path=config,
                handlers_file=handlers,
                output_dir=Path(tempfile.mkdtemp()),
            )

        assert success is False
        assert len(errors) == 2
        assert "missing 'name'" in errors[0]

    def test_compile_network_error_retries(self, cloud_compiler, temp_project):
        """Network errors should trigger retries."""
        _, config, handlers = temp_project
        import urllib.error

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise urllib.error.URLError("Connection refused")

        with patch('urllib.request.urlopen', side_effect=side_effect):
            with patch('time.sleep'):  # Speed up test
                success, messages, errors = cloud_compiler.compile(
                    config_path=config,
                    handlers_file=handlers,
                    output_dir=Path(tempfile.mkdtemp()),
                )

        assert success is False
        # Should have retried (initial + CLOUD_COMPILE_RETRIES)
        assert call_count == 3  # 1 initial + 2 retries

    def test_compile_handlers_dir(self, cloud_compiler, tmp_path):
        """Should concatenate .bsl files from handlers directory."""
        config = tmp_path / "config.yaml"
        config.write_text("name: Test\n", encoding="utf-8")

        handlers_dir = tmp_path / "handlers"
        handlers_dir.mkdir()
        (handlers_dir / "01_open.bsl").write_text("// open\n", encoding="utf-8")
        (handlers_dir / "02_close.bsl").write_text("// close\n", encoding="utf-8")

        output_dir = tmp_path / "output"
        response_data = self._make_success_response("Test")
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(response_data).encode("utf-8")
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)

        sent_payload = {}

        original_urlopen = None

        def capture_request(req, **kwargs):
            sent_payload['data'] = json.loads(req.data.decode("utf-8"))
            return mock_response

        with patch('urllib.request.urlopen', side_effect=capture_request):
            success, _, _ = cloud_compiler.compile(
                config_path=config,
                handlers_dir=handlers_dir,
                output_dir=output_dir,
            )

        assert success is True
        # Handlers should be concatenated
        assert "// open" in sent_payload['data']['handlers_content']
        assert "// close" in sent_payload['data']['handlers_content']
