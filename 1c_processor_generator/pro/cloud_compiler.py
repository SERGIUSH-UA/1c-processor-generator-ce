"""
Cloud EPF compilation via gen.itdeo.tech API.

Sends YAML config + BSL handlers to the cloud service which generates XML
and compiles EPF using Docker-based 1C Designer.

v2.75.0+: Cloud compilation feature (requires PRO license with cloud_compilation).

IMPORTANT: User code (YAML + BSL) is sent to the server for compilation.
"""

import base64
import json
import logging
import os
import sys
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import urllib.request
import urllib.error

try:
    from .license import LicenseManager, get_license_manager, generate_machine_id
    from .constants import (
        CLOUD_COMPILE_URL,
        CLOUD_HEALTH_URL,
        CLOUD_VERSION_URL,
        CLOUD_COMPILE_TIMEOUT,
        CLOUD_COMPILE_RETRIES,
    )
except ImportError:
    from license import LicenseManager, get_license_manager, generate_machine_id
    from constants import (
        CLOUD_COMPILE_URL,
        CLOUD_HEALTH_URL,
        CLOUD_VERSION_URL,
        CLOUD_COMPILE_TIMEOUT,
        CLOUD_COMPILE_RETRIES,
    )

try:
    from .. import __version__
except (ImportError, ValueError):
    try:
        import importlib
        _pkg = importlib.import_module("1c_processor_generator")
        __version__ = getattr(_pkg, "__version__", "unknown")
    except Exception:
        __version__ = "unknown"

logger = logging.getLogger(__name__)

# Binary file extensions that should be base64-encoded
BINARY_EXTENSIONS = {'.mxl', '.xlsx', '.xls', '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico'}


class CloudCompileError(Exception):
    """Base error for cloud compilation."""
    pass


class CloudAuthError(CloudCompileError):
    """Authentication error (401)."""
    pass


class CloudUnavailableError(CloudCompileError):
    """Cloud service unavailable."""
    pass


class CloudRateLimitError(CloudCompileError):
    """Rate limit exceeded (429)."""
    pass


class CloudCompiler:
    """
    HTTP client for cloud EPF compilation via gen.itdeo.tech.

    Sends YAML + BSL to the cloud, receives compiled EPF back.
    Requires PRO license with 'cloud_compilation' feature.
    """

    def __init__(self, license_manager: LicenseManager):
        self._license_manager = license_manager
        self._machine_id = None

    @property
    def machine_id(self) -> str:
        if self._machine_id is None:
            self._machine_id = generate_machine_id()
        return self._machine_id

    def _get_auth_headers(self) -> Dict[str, str]:
        """Build authorization headers using JWT from LicenseManager."""
        token = self._license_manager._get_valid_token()
        if token is None:
            raise CloudAuthError("Немає валідного токена. Активуйте ліцензію: python -m 1c_processor_generator activate <key>")

        return {
            "Authorization": f"Bearer {token.token}",
            "X-Machine-ID": self.machine_id,
            "X-Client-Type": "cli",
            "User-Agent": f"1c-processor-generator/{__version__}",
            "Content-Type": "application/json",
        }

    def check_available(self) -> bool:
        """
        Check if cloud service is available (GET /health).

        Returns:
            True if service is healthy, False otherwise.
        """
        try:
            req = urllib.request.Request(
                CLOUD_HEALTH_URL,
                headers={"User-Agent": f"1c-processor-generator/{__version__}"},
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.status == 200
        except Exception as e:
            logger.debug(f"Health check failed: {e}")
            return False

    def get_version(self) -> Optional[dict]:
        """
        Get cloud service version info (GET /version).

        Returns:
            Dict with version info or None if unavailable.
        """
        try:
            req = urllib.request.Request(
                CLOUD_VERSION_URL,
                headers={"User-Agent": f"1c-processor-generator/{__version__}"},
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as e:
            logger.debug(f"Version check failed: {e}")
            return None

    def compile(
        self,
        config_path: Path,
        handlers_file: Optional[Path] = None,
        handlers_dir: Optional[Path] = None,
        output_dir: Path = None,
        ignore_validation_errors: bool = False,
    ) -> Tuple[bool, List[str], List[str]]:
        """
        Compile EPF via cloud service.

        Args:
            config_path: Path to YAML config file.
            handlers_file: Path to monolithic BSL handlers file.
            handlers_dir: Path to handlers directory (legacy).
            output_dir: Output directory for EPF file.
            ignore_validation_errors: Ignore BSL validation errors.

        Returns:
            Tuple of (success, messages, errors).
        """
        # Read config
        yaml_content = config_path.read_text(encoding="utf-8")

        # Read handlers
        handlers_content = ""
        if handlers_file and handlers_file.exists():
            handlers_content = handlers_file.read_text(encoding="utf-8")
        elif handlers_dir and handlers_dir.exists():
            # Concatenate all .bsl files from directory
            bsl_files = sorted(handlers_dir.glob("*.bsl"))
            parts = []
            for bsl_file in bsl_files:
                parts.append(bsl_file.read_text(encoding="utf-8"))
            handlers_content = "\n\n".join(parts)

        # Collect template files referenced in YAML
        template_files = self._collect_template_files(config_path, yaml_content)

        # Build payload
        payload = {
            "yaml_config": yaml_content,
            "handlers_content": handlers_content,
            "template_files": template_files,
            "output_format": "epf",
            "ignore_validation_errors": ignore_validation_errors,
        }

        # Send request with retry
        messages = []
        errors = []

        try:
            response_data = self._send_compile_request(payload)
        except CloudAuthError as e:
            errors.append(str(e))
            return False, messages, errors
        except CloudRateLimitError:
            errors.append("Перевищено ліміт запитів. Зачекайте і спробуйте ще раз")
            return False, messages, errors
        except CloudUnavailableError as e:
            errors.append(f"Хмарний сервіс недоступний: {e}")
            return False, messages, errors
        except CloudCompileError as e:
            errors.append(str(e))
            return False, messages, errors

        # Process response
        if response_data.get("success"):
            # Decode EPF from base64
            epf_base64 = response_data.get("output_base64", "")
            if not epf_base64:
                errors.append("Сервер не повернув EPF файл")
                return False, messages, errors

            epf_data = base64.b64decode(epf_base64)
            processor_name = self._get_name_from_yaml(yaml_content) or response_data.get("processor_name") or "Processor"
            epf_filename = f"{processor_name}.epf"

            # Write EPF file
            output_dir = Path(output_dir) if output_dir else Path.cwd() / "tmp"
            output_dir.mkdir(parents=True, exist_ok=True)
            epf_path = output_dir / epf_filename
            epf_path.write_bytes(epf_data)

            messages.append(f"EPF створено: {epf_path}")
            messages.append(f"Розмір: {len(epf_data):,} bytes")

            # Collect server-side messages
            if response_data.get("messages"):
                messages.extend(response_data["messages"])

            return True, messages, errors
        else:
            # Compilation failed on server
            server_errors = response_data.get("errors", [])
            if server_errors:
                errors.extend(server_errors)
            else:
                errors.append(response_data.get("error", "Невідома помилка компіляції"))

            server_messages = response_data.get("messages", [])
            if server_messages:
                messages.extend(server_messages)

            return False, messages, errors

    def _collect_template_files(self, config_path: Path, yaml_content: str) -> Dict[str, str]:
        """
        Collect template files referenced in YAML config.

        Reads the YAML to find templates section and loads referenced files.
        Binary files are base64-encoded with 'base64:' prefix.

        Returns:
            Dict mapping relative path -> file content (or base64: prefixed for binary).
        """
        template_files = {}

        try:
            import yaml
            config = yaml.safe_load(yaml_content)
        except Exception:
            return template_files

        if not config or not isinstance(config, dict):
            return template_files

        templates_section = config.get("templates", [])
        if not templates_section:
            return template_files

        config_dir = config_path.parent

        for tmpl in templates_section:
            if not isinstance(tmpl, dict):
                continue

            file_path_str = tmpl.get("file")
            if not file_path_str:
                continue

            file_path = Path(file_path_str)
            if not file_path.is_absolute():
                file_path = config_dir / file_path_str

            if not file_path.exists():
                logger.warning(f"Template file not found: {file_path}")
                continue

            # Check if binary
            ext = file_path.suffix.lower()
            if ext in BINARY_EXTENSIONS:
                content = base64.b64encode(file_path.read_bytes()).decode("ascii")
                template_files[file_path_str] = f"base64:{content}"
            else:
                template_files[file_path_str] = file_path.read_text(encoding="utf-8")

            # Also check for automation file
            automation_path = tmpl.get("automation")
            if automation_path:
                auto_file = Path(automation_path)
                if not auto_file.is_absolute():
                    auto_file = config_dir / automation_path
                if auto_file.exists():
                    template_files[automation_path] = auto_file.read_text(encoding="utf-8")

            # Check for assets directory
            assets_dir = tmpl.get("assets")
            if assets_dir:
                assets_path = Path(assets_dir)
                if not assets_path.is_absolute():
                    assets_path = config_dir / assets_dir
                if assets_path.exists() and assets_path.is_dir():
                    for asset_file in assets_path.rglob("*"):
                        if asset_file.is_file():
                            rel_path = str(asset_file.relative_to(config_dir)).replace("\\", "/")
                            ext = asset_file.suffix.lower()
                            if ext in BINARY_EXTENSIONS:
                                content = base64.b64encode(asset_file.read_bytes()).decode("ascii")
                                template_files[rel_path] = f"base64:{content}"
                            else:
                                template_files[rel_path] = asset_file.read_text(encoding="utf-8")

        return template_files

    @staticmethod
    def _get_name_from_yaml(yaml_content: str) -> Optional[str]:
        """Extract processor name from YAML content."""
        try:
            import yaml
            config = yaml.safe_load(yaml_content)
            if config and isinstance(config, dict):
                # name can be top-level or under processor:
                name = config.get("name")
                if not name and isinstance(config.get("processor"), dict):
                    name = config["processor"].get("name")
                return name
        except Exception:
            pass
        return None

    def _send_compile_request(self, payload: dict) -> dict:
        """
        Send compile request with retry logic and progress spinner.

        Returns:
            Parsed JSON response from server.

        Raises:
            CloudAuthError: Authentication failed (401).
            CloudRateLimitError: Rate limit exceeded (429).
            CloudUnavailableError: Service unavailable (503).
            CloudCompileError: Other compilation errors.
        """
        headers = self._get_auth_headers()
        request_data = json.dumps(payload).encode("utf-8")

        last_error = None

        for attempt in range(CLOUD_COMPILE_RETRIES + 1):
            # Start progress spinner
            stop_event = threading.Event()
            spinner_thread = threading.Thread(
                target=self._progress_spinner,
                args=(stop_event,),
                daemon=True,
            )
            spinner_thread.start()

            try:
                req = urllib.request.Request(
                    CLOUD_COMPILE_URL,
                    data=request_data,
                    headers=headers,
                    method="POST",
                )

                with urllib.request.urlopen(req, timeout=CLOUD_COMPILE_TIMEOUT) as response:
                    stop_event.set()
                    spinner_thread.join(timeout=1)
                    sys.stderr.write("\n")
                    return json.loads(response.read().decode("utf-8"))

            except urllib.error.HTTPError as e:
                stop_event.set()
                spinner_thread.join(timeout=1)
                sys.stderr.write("\n")

                if e.code == 401:
                    raise CloudAuthError(
                        "Помилка автентифікації. Спробуйте: python -m 1c_processor_generator activate <key>"
                    )
                elif e.code == 429:
                    raise CloudRateLimitError("Rate limit exceeded")
                elif e.code == 503:
                    if attempt < CLOUD_COMPILE_RETRIES:
                        wait_time = 5 * (attempt + 1)
                        logger.debug(f"Service busy, retrying in {wait_time}s (attempt {attempt + 1})")
                        sys.stderr.write(f"   Сервер зайнятий, повтор через {wait_time} сек...\n")
                        time.sleep(wait_time)
                        last_error = e
                        continue
                    raise CloudUnavailableError("Сервер зайнятий. Спробуйте пізніше")
                elif 400 <= e.code < 500:
                    # Client errors - don't retry
                    try:
                        error_body = json.loads(e.read().decode("utf-8"))
                        error_msg = error_body.get("error", str(e))
                    except Exception:
                        error_msg = str(e)
                    raise CloudCompileError(error_msg)
                else:
                    last_error = e
                    if attempt < CLOUD_COMPILE_RETRIES:
                        wait_time = 2 ** (attempt + 1)
                        logger.debug(f"Server error {e.code}, retrying in {wait_time}s")
                        time.sleep(wait_time)
                        continue
                    raise CloudCompileError(f"Помилка сервера: {e.code}")

            except urllib.error.URLError as e:
                stop_event.set()
                spinner_thread.join(timeout=1)
                sys.stderr.write("\n")
                last_error = e
                if attempt < CLOUD_COMPILE_RETRIES:
                    wait_time = 2 ** (attempt + 1)
                    logger.debug(f"Network error, retrying in {wait_time}s: {e}")
                    sys.stderr.write(f"   Мережева помилка, повтор через {wait_time} сек...\n")
                    time.sleep(wait_time)
                    continue

            except Exception as e:
                stop_event.set()
                spinner_thread.join(timeout=1)
                sys.stderr.write("\n")
                last_error = e
                if attempt < CLOUD_COMPILE_RETRIES:
                    wait_time = 2 ** (attempt + 1)
                    time.sleep(wait_time)
                    continue

        raise CloudCompileError(
            f"Не вдалося з'єднатися з хмарним сервісом після {CLOUD_COMPILE_RETRIES + 1} спроб: {last_error}"
        )

    @staticmethod
    def _progress_spinner(stop_event: threading.Event) -> None:
        """Show progress dots in stderr while waiting for compilation."""
        sys.stderr.write("   Компіляція")
        sys.stderr.flush()
        while not stop_event.is_set():
            stop_event.wait(timeout=2)
            if not stop_event.is_set():
                sys.stderr.write(".")
                sys.stderr.flush()
