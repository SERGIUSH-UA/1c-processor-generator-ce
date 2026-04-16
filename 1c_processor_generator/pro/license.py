"""
License management for 1C Processor Generator PRO.

Handles:
- Machine ID generation (hardware fingerprint)
- JWT token caching and verification (encrypted)
- License activation and status checking
- Offline grace period management
"""

import base64
import hashlib
import json
import logging
import os
import platform
import re
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Tuple, List
import urllib.request
import urllib.error

try:
    from cryptography.fernet import Fernet
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False

# Get version for X-CLI-Version header
def get_cli_version() -> str:
    """
    Get CLI version with multiple fallbacks for both dev and compiled .pyd.

    Public function - exported from compiled .pyd.
    """
    import importlib

    # Try 1: Direct import from parent package (dev mode)
    try:
        from .. import __version__ as pkg_version
        if pkg_version and pkg_version != "unknown":
            return pkg_version
    except (ImportError, ValueError):
        pass

    # Try 2: Absolute import of main package (works in compiled .pyd)
    try:
        main_pkg = importlib.import_module("1c_processor_generator")
        if hasattr(main_pkg, "__version__") and main_pkg.__version__:
            return main_pkg.__version__
    except Exception:
        pass

    # Try 3: importlib.metadata (works when installed via pip)
    try:
        from importlib.metadata import version
        return version("1c-processor-generator")
    except Exception:
        pass

    # Try 4: Read from VERSION file - try multiple paths
    try:
        from pathlib import Path
        # Path when running from source
        candidates = [
            Path(__file__).parent.parent.parent / "VERSION",  # dev mode
            Path(__file__).parent.parent / "VERSION",  # if in 1c_processor_generator/
        ]
        # Path when running from compiled .pyd in _bins/
        # __file__ = .../pro/_bins/win_amd64/cp314/_lic.pyd
        # VERSION is at .../VERSION (5 levels up)
        if "_bins" in str(Path(__file__)):
            candidates.append(Path(__file__).parent.parent.parent.parent.parent.parent / "VERSION")

        for version_file in candidates:
            if version_file.exists():
                content = version_file.read_text(encoding="utf-8")
                for line in content.strip().split("\n"):
                    if line.startswith("DEV_VERSION="):
                        return line.split("=", 1)[1].strip()
    except Exception:
        pass

    return "unknown"


# Module-level version (for compatibility)
__version__ = get_cli_version()

# Public constant for Cython export
CLI_VERSION = __version__

try:
    # When running as compiled .pyd or from pro/ directory
    from constants import (
        LICENSE_API_URL,
        LICENSE_API_TIMEOUT,
        LICENSE_API_RETRIES,
        LICENSE_TOKEN_FILE,
        TELEMETRY_SENT_FILE,
        GRACE_PERIOD_DAYS,
        EXPIRY_WARNING_DAYS,
        CACHE_VERSION,
        ENCRYPTION_SALT,
        PRO_FEATURES,
        PURCHASE_URL,
        ACCOUNT_URL,
        SUPPORT_EMAIL,
    )
    from exceptions import (
        LicenseError,
        ActivationError,
        VerificationError,
        MachineIdError,
        TokenExpiredError,
        GracePeriodExpiredError,
        MachineMismatchError,
        NetworkError,
    )
except ImportError:
    # When running as part of package
    from .constants import (
        LICENSE_API_URL,
        LICENSE_API_TIMEOUT,
        LICENSE_API_RETRIES,
        LICENSE_TOKEN_FILE,
        TELEMETRY_SENT_FILE,
        GRACE_PERIOD_DAYS,
        EXPIRY_WARNING_DAYS,
        CACHE_VERSION,
        ENCRYPTION_SALT,
        PRO_FEATURES,
        PURCHASE_URL,
        ACCOUNT_URL,
        SUPPORT_EMAIL,
    )
    from .exceptions import (
        LicenseError,
        ActivationError,
        VerificationError,
        MachineIdError,
        TokenExpiredError,
        GracePeriodExpiredError,
        MachineMismatchError,
        NetworkError,
    )

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class LicenseStatus:
    """Current license status."""
    is_licensed: bool
    license_type: str  # "free", "quarter", "year", "lifetime"
    features: List[str]
    watermark_removed: bool
    expires_at: Optional[str]  # ISO datetime or None for lifetime
    machines_used: int
    machines_limit: int
    days_until_expiry: Optional[int]
    is_offline: bool
    grace_period_remaining: Optional[int]  # days
    license_key: Optional[str] = None  # License key for verification


@dataclass
class ActivationResult:
    """Result of license activation."""
    success: bool
    token: Optional[str]
    error_message: Optional[str]
    license_type: Optional[str]
    expires_at: Optional[str]


@dataclass
class CachedToken:
    """Cached license token data."""
    token: str
    machine_id: str
    license_key: str
    features: List[str]
    watermark_removed: bool
    expires_at: Optional[str]
    last_online_verify: str  # ISO datetime
    license_type: str


# =============================================================================
# Machine ID Generation
# =============================================================================

def generate_machine_id() -> str:
    """
    Generate stable hardware fingerprint using multiple sources.

    Components (Windows):
    1. CPU ID (via wmic)
    2. First network MAC address
    3. System drive volume serial number
    4. BIOS serial number (hard to spoof)
    5. Windows Product ID (unique per installation)
    6. Motherboard serial number (v2.51.0)

    Returns:
        SHA-256 hash of combined components (lowercase hex, 64 chars)

    Raises:
        MachineIdError: If unable to generate machine ID
    """
    components = []

    # 1. CPU ID
    try:
        cpu_id = _get_cpu_id()
        if cpu_id:
            components.append(f"cpu:{cpu_id}")
    except Exception as e:
        logger.debug(f"Failed to get CPU ID: {e}")

    # 2. MAC Address
    try:
        mac = _get_mac_address()
        if mac:
            components.append(f"mac:{mac}")
    except Exception as e:
        logger.debug(f"Failed to get MAC address: {e}")

    # 3. Volume Serial
    try:
        vol_serial = _get_volume_serial()
        if vol_serial:
            components.append(f"vol:{vol_serial}")
    except Exception as e:
        logger.debug(f"Failed to get volume serial: {e}")

    # 4. BIOS Serial (hard to spoof)
    try:
        bios_serial = _get_bios_serial()
        if bios_serial:
            components.append(f"bios:{bios_serial}")
    except Exception as e:
        logger.debug(f"Failed to get BIOS serial: {e}")

    # 5. Windows Product ID (unique per installation)
    try:
        win_product_id = _get_windows_product_id()
        if win_product_id:
            components.append(f"wpid:{win_product_id}")
    except Exception as e:
        logger.debug(f"Failed to get Windows Product ID: {e}")

    # 6. Motherboard Serial (v2.51.0 - additional security)
    try:
        mb_serial = _get_motherboard_serial()
        if mb_serial:
            components.append(f"mb:{mb_serial}")
    except Exception as e:
        logger.debug(f"Failed to get motherboard serial: {e}")

    # v2.51.0 Security: Require at least 3 hardware components
    # Fallback only used if truly necessary (VMs, containers)
    if len(components) < 3:
        import os
        import socket
        fallback = f"fallback:{socket.gethostname()}:{os.getenv('USERNAME', 'unknown')}"
        components.append(fallback)
        logger.warning("SECURITY: Using weak fallback for machine ID - only %d hardware components available", len(components) - 1)

    # Generate hash
    combined = "|".join(sorted(components))
    machine_id = hashlib.sha256(combined.encode()).hexdigest()

    logger.debug(f"Generated machine ID: {machine_id[:16]}... ({len(components)} components)")
    return machine_id


def _get_cpu_id() -> Optional[str]:
    """Get CPU ID via wmic (Windows)."""
    try:
        result = subprocess.run(
            ["wmic", "cpu", "get", "ProcessorId"],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        lines = result.stdout.strip().split("\n")
        if len(lines) >= 2:
            return lines[1].strip()
    except Exception:
        pass
    return None


def _get_mac_address() -> Optional[str]:
    """Get first MAC address."""
    try:
        mac = uuid.getnode()
        # Ensure it's a real MAC (not random)
        if (mac >> 40) % 2 == 0:  # Check multicast bit
            return format(mac, '012x')
    except Exception:
        pass
    return None


def _get_volume_serial() -> Optional[str]:
    """Get C: drive volume serial number (Windows)."""
    try:
        result = subprocess.run(
            ["cmd", "/c", "vol", "C:"],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        # Parse "Volume Serial Number is XXXX-XXXX"
        for line in result.stdout.split("\n"):
            if "Serial" in line or "серийный" in line.lower():
                parts = line.split()
                for part in parts:
                    if "-" in part and len(part) == 9:  # XXXX-XXXX format
                        return part.replace("-", "")
    except Exception:
        pass
    return None


def _get_bios_serial() -> Optional[str]:
    """Get BIOS serial number (Windows)."""
    try:
        result = subprocess.run(
            ["wmic", "bios", "get", "serialnumber"],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        lines = result.stdout.strip().split('\n')
        if len(lines) >= 2:
            serial = lines[-1].strip()
            # Skip generic/empty values
            if serial and serial not in ("To Be Filled By O.E.M.", "Default string", "None", ""):
                return serial
    except Exception:
        pass
    return None


def _get_windows_product_id() -> Optional[str]:
    """Get Windows Product ID from registry."""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"
        )
        product_id, _ = winreg.QueryValueEx(key, "ProductId")
        winreg.CloseKey(key)
        if product_id:
            return product_id
    except Exception:
        pass
    return None


def _get_motherboard_serial() -> Optional[str]:
    """Get motherboard serial number via wmic (Windows) - v2.51.0."""
    try:
        result = subprocess.run(
            ["wmic", "baseboard", "get", "serialnumber"],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        lines = result.stdout.strip().split("\n")
        if len(lines) >= 2:
            serial = lines[1].strip()
            # Filter out generic/default values
            if serial and serial.lower() not in ['to be filled by o.e.m.', 'default string', 'none', '']:
                return serial
    except Exception:
        pass
    return None


# =============================================================================
# System Info Collection (for analytics)
# =============================================================================

def _detect_is_ci() -> bool:
    """Detect if running in CI/CD environment."""
    ci_vars = ['CI', 'GITHUB_ACTIONS', 'GITLAB_CI', 'JENKINS_URL',
               'CIRCLECI', 'TRAVIS', 'TF_BUILD', 'BUILDKITE',
               'CODEBUILD_BUILD_ID', 'TEAMCITY_VERSION']
    return any(os.environ.get(var) for var in ci_vars)


def _detect_ci_type() -> Optional[str]:
    """Detect specific CI/CD system type."""
    if os.environ.get('GITHUB_ACTIONS'):
        return 'github'
    if os.environ.get('GITLAB_CI'):
        return 'gitlab'
    if os.environ.get('JENKINS_URL'):
        return 'jenkins'
    if os.environ.get('CIRCLECI'):
        return 'circleci'
    if os.environ.get('TRAVIS'):
        return 'travis'
    if os.environ.get('TF_BUILD'):
        return 'azure'
    if os.environ.get('BUILDKITE'):
        return 'buildkite'
    if os.environ.get('CODEBUILD_BUILD_ID'):
        return 'aws_codebuild'
    if os.environ.get('TEAMCITY_VERSION'):
        return 'teamcity'
    if os.environ.get('CI'):
        return 'unknown'
    return None


def get_system_info() -> dict:
    """
    Collect system information for analytics.

    Returns dict with:
    - os: Operating system name (e.g., "Windows")
    - os_version: OS version (e.g., "10.0.22631")
    - os_release: OS release (e.g., "10")
    - python: Python version (e.g., "3.11.5")
    - arch: Architecture (e.g., "AMD64")
    - platform_1c: 1C platform version or None if not installed
    - is_ci: True if running in CI/CD environment
    - ci_type: CI/CD system type (github, gitlab, etc.) or None
    """
    info = {
        "os": platform.system(),
        "os_version": platform.version(),
        "os_release": platform.release(),
        "python": platform.python_version(),
        "arch": platform.machine(),
        "platform_1c": None,
    }

    # 1C Platform detection (lazy import to avoid circular dependency)
    try:
        from ..designer_finder import DesignerFinder
        finder = DesignerFinder()
        if finder.designer_path:
            # v2.70.0: Use platform_version from DesignerFinder (more reliable)
            # Falls back to regex extraction from path if not available
            if finder.platform_version:
                info["platform_1c"] = finder.platform_version
            else:
                # Fallback: Extract version from path: .../8.3.25.1234/bin/1cv8.exe
                path_str = str(finder.designer_path)
                match = re.search(r'(\d+\.\d+\.\d+\.\d+)', path_str)
                info["platform_1c"] = match.group(1) if match else "detected_unknown_version"
        else:
            # 1C not found - this is normal, not an error
            info["platform_1c"] = None
    except ImportError:
        # designer_finder module not available (e.g., minimal install)
        logger.debug("designer_finder module not available")
        info["platform_1c"] = None
    except Exception as e:
        # Actual error during detection
        logger.debug(f"Failed to detect 1C platform: {e}")
        info["platform_1c"] = f"error:{type(e).__name__}"

    # CI/CD detection (v2.70.0)
    info["is_ci"] = _detect_is_ci()
    info["ci_type"] = _detect_ci_type()

    return info


# Cache system info (collected once per session)
_system_info_cache: Optional[dict] = None


def get_system_info_cached() -> dict:
    """Get cached system info (collected once per session)."""
    global _system_info_cache
    if _system_info_cache is None:
        _system_info_cache = get_system_info()
    return _system_info_cache


# =============================================================================
# Datetime Helpers (v2.68.1 - Python 3.14 compatibility fix)
# =============================================================================

def _parse_iso_datetime(dt_string: str) -> datetime:
    """
    Parse ISO datetime string ensuring timezone-aware result.

    Handles:
    - 'Z' suffix (Python < 3.11 doesn't support it natively)
    - Missing timezone info (defaults to UTC)
    - Various ISO formats

    Args:
        dt_string: ISO format datetime string

    Returns:
        Timezone-aware datetime object (always UTC or explicit offset)

    Raises:
        ValueError: If dt_string is empty or None
    """
    if not dt_string:
        raise ValueError("Empty datetime string")

    # Handle 'Z' suffix for Python < 3.11 compatibility
    if dt_string.endswith('Z'):
        dt_string = dt_string[:-1] + '+00:00'

    dt = datetime.fromisoformat(dt_string)

    # Ensure timezone-aware (default to UTC if naive)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt


# =============================================================================
# License Manager
# =============================================================================

class LicenseManager:
    """
    Manages license verification and activation.

    Usage:
        >>> mgr = LicenseManager()
        >>> is_licensed, error = mgr.check_pro_feature("epf_compilation")
        >>> if not is_licensed:
        ...     print(error)
    """

    def __init__(self):
        self._cached_token: Optional[CachedToken] = None
        self._machine_id: Optional[str] = None

    @property
    def machine_id(self) -> str:
        """Get machine ID (cached)."""
        if self._machine_id is None:
            self._machine_id = generate_machine_id()
        return self._machine_id

    def activate_license(self, license_key: str) -> ActivationResult:
        """
        Activate license on this machine.

        Args:
            license_key: License key (format: PRO-XXXX-XXXX-XXXX)

        Returns:
            ActivationResult with success status and token
        """
        logger.info(f"Activating license: {license_key[:8]}...")

        try:
            # Call activation API
            response = self._api_request(
                "/activate",
                {
                    "license_key": license_key,
                    "machine_id": self.machine_id,
                }
            )

            if response.get("success"):
                # Save token to cache
                token_data = CachedToken(
                    token=response["token"],
                    machine_id=self.machine_id,
                    license_key=license_key,
                    features=response.get("features", PRO_FEATURES),
                    watermark_removed=response.get("watermark_removed", True),
                    expires_at=response.get("expires_at"),
                    last_online_verify=datetime.now(timezone.utc).isoformat(),
                    license_type=response.get("type", "unknown"),
                )
                self._save_token_cache(token_data)
                self._cached_token = token_data

                logger.info("License activated successfully")
                return ActivationResult(
                    success=True,
                    token=response["token"],
                    error_message=None,
                    license_type=response.get("type"),
                    expires_at=response.get("expires_at"),
                )
            else:
                error = response.get("message", "Activation failed")
                logger.error(f"Activation failed: {error}")
                return ActivationResult(
                    success=False,
                    token=None,
                    error_message=error,
                    license_type=None,
                    expires_at=None,
                )

        except NetworkError as e:
            logger.error(f"Network error during activation: {e}")
            return ActivationResult(
                success=False,
                token=None,
                error_message=f"Сервер ліцензій недоступний: {e}",
                license_type=None,
                expires_at=None,
            )
        except Exception as e:
            logger.error(f"Activation error: {e}")
            return ActivationResult(
                success=False,
                token=None,
                error_message=str(e),
                license_type=None,
                expires_at=None,
            )

    def request_trial(self, email: str) -> ActivationResult:
        """
        Request 7-day trial license.

        Server validates:
        - One trial per email
        - One trial per machine_id

        Args:
            email: User's email address

        Returns:
            ActivationResult with success status
        """
        logger.info(f"Requesting trial for: {email}")

        try:
            response = self._api_request(
                "/trial",
                {
                    "email": email,
                    "machine_id": self.machine_id,
                }
            )

            if "license_key" in response:
                # Auto-activate the trial
                logger.info(f"Trial license received, activating...")
                return self.activate_license(response["license_key"])
            else:
                error_msg = response.get("detail", response.get("message", "Trial request failed"))
                logger.error(f"Trial request failed: {error_msg}")
                return ActivationResult(
                    success=False,
                    token=None,
                    error_message=error_msg,
                    license_type=None,
                    expires_at=None,
                )

        except NetworkError as e:
            logger.error(f"Network error during trial request: {e}")
            return ActivationResult(
                success=False,
                token=None,
                error_message=f"Сервер ліцензій недоступний: {e}",
                license_type=None,
                expires_at=None,
            )
        except Exception as e:
            logger.error(f"Trial request error: {e}")
            return ActivationResult(
                success=False,
                token=None,
                error_message=str(e),
                license_type=None,
                expires_at=None,
            )

    def check_pro_feature(self, feature: str):
        """
        Check if feature is available.

        Community edition: all local features are free.
        Only cloud_compilation checks actual license.
        """
        if feature != "cloud_compilation":
            return True, ""

        # For cloud: check actual license
        token = self._get_valid_token()
        if token is None:
            return False, "Cloud compilation requires PRO license. Run: python -m 1c_processor_generator activate <key>"

        if "cloud_compilation" not in getattr(token, "features", []):
            return False, "Your PRO license does not include cloud_compilation feature."

        return True, ""


    def _show_expiry_warning(self, days_left: int) -> None:
        """Show expiry warning (once per session)."""
        if getattr(self, '_expiry_warned', False):
            return
        self._expiry_warned = True

        print(f"\n⚠️  Ваша PRO ліцензія закінчується через {days_left} днів!")
        print(f"   Поновити: {ACCOUNT_URL}\n")

    def get_license_status(self) -> LicenseStatus:
        """Get current license status."""
        token = self._get_valid_token()

        if token is None:
            return LicenseStatus(
                is_licensed=False,
                license_type="free",
                features=[],
                watermark_removed=False,
                expires_at=None,
                machines_used=0,
                machines_limit=0,
                days_until_expiry=None,
                is_offline=False,
                grace_period_remaining=None,
                license_key=None,
            )

        now = datetime.now(timezone.utc)

        # Calculate days until expiry
        days_until_expiry = None
        if token.expires_at:
            try:
                expires = _parse_iso_datetime(token.expires_at)
                delta = expires - now
                days_until_expiry = max(0, delta.days)
            except Exception:
                pass

        # Check if offline
        is_offline = False
        grace_remaining = None
        try:
            last_verify = _parse_iso_datetime(token.last_online_verify)
            days_since_verify = (now - last_verify).days
            is_offline = days_since_verify > 0
            if is_offline:
                grace_remaining = max(0, GRACE_PERIOD_DAYS - days_since_verify)
        except Exception:
            pass

        return LicenseStatus(
            is_licensed=True,
            license_type=token.license_type,
            features=token.features,
            watermark_removed=token.watermark_removed,
            expires_at=token.expires_at,
            machines_used=1,  # Current machine
            machines_limit=self._get_machine_limit(token.license_type),
            days_until_expiry=days_until_expiry,
            is_offline=is_offline,
            grace_period_remaining=grace_remaining,
            license_key=token.license_key,
        )

    def is_watermark_removed(self) -> bool:
        """Always True in community edition (no watermark)."""
        return True


    def clear_cache(self) -> bool:
        """Clear license cache (for troubleshooting)."""
        try:
            if LICENSE_TOKEN_FILE.exists():
                LICENSE_TOKEN_FILE.unlink()
                logger.info("License cache cleared")
            self._cached_token = None
            return True
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return False

    # =========================================================================
    # Private Methods
    # =========================================================================

    def _get_valid_token(self, check_expiry: bool = True) -> Optional[CachedToken]:
        """
        Get valid token (from cache or online verification).

        Args:
            check_expiry: If True, check token expiration

        Returns:
            CachedToken if valid, None otherwise
        """
        # Try memory cache first
        if self._cached_token is not None:
            if self._validate_token(self._cached_token, check_expiry):
                return self._cached_token

        # Load from disk cache
        token = self._load_token_cache()
        if token is None:
            return None

        # v2.51.0 Security: Strict machine ID validation
        if token.machine_id != self.machine_id:
            logger.warning(
                "SECURITY: Machine ID mismatch detected! "
                "Token machine_id: %s..., Current machine_id: %s... "
                "This may indicate an attempt to copy the license to another machine.",
                token.machine_id[:16], self.machine_id[:16]
            )
            return None

        # Check if online verification needed
        if self._should_verify_online(token):
            try:
                verified_token = self._verify_online(token)
                if verified_token:
                    token = verified_token
            except NetworkError:
                # Check grace period
                if not self._check_grace_period(token):
                    logger.warning("Grace period expired")
                    return None
                logger.info("Using cached token (offline mode)")

        if self._validate_token(token, check_expiry):
            self._cached_token = token
            return token

        return None

    def _validate_token(self, token: CachedToken, check_expiry: bool) -> bool:
        """Validate token data."""
        if not token.token:
            return False

        if check_expiry and token.expires_at:
            try:
                expires = _parse_iso_datetime(token.expires_at)
                if expires < datetime.now(timezone.utc):
                    return False
            except Exception:
                pass

        return True

    def _should_verify_online(self, token: CachedToken) -> bool:
        """
        Check if online verification is needed.

        v2.51.0 Security: Also detects time manipulation attempts.
        """
        try:
            last_verify = _parse_iso_datetime(token.last_online_verify)
            now = datetime.now(timezone.utc)

            # v2.51.0 Security: Detect time rollback (clock manipulation)
            # If last_verify is in the future, someone may have rolled back the clock
            if last_verify > now + timedelta(hours=1):  # 1 hour tolerance for timezone issues
                logger.warning(
                    "SECURITY: Time manipulation detected! "
                    "Last verification (%s) is in the future. "
                    "Forcing online verification.",
                    last_verify.isoformat()
                )
                return True

            # Verify every 24 hours
            return (now - last_verify) > timedelta(hours=24)
        except Exception:
            return True

    def _verify_online(self, token: CachedToken) -> Optional[CachedToken]:
        """Verify token with server."""
        try:
            response = self._api_request(
                "/verify",
                {
                    "token": token.token,
                    "machine_id": self.machine_id,
                }
            )

            if response.get("valid"):
                # Update cache with fresh data
                token.last_online_verify = datetime.now(timezone.utc).isoformat()
                token.features = response.get("features", token.features)
                token.expires_at = response.get("expires_at", token.expires_at)
                self._save_token_cache(token)
                return token

            logger.warning(f"Token verification failed: {response.get('error')}")
            return None

        except NetworkError:
            raise
        except Exception as e:
            logger.error(f"Verification error: {e}")
            return None

    def _check_grace_period(self, token: CachedToken) -> bool:
        """Check if within offline grace period."""
        try:
            last_verify = _parse_iso_datetime(token.last_online_verify)
            now = datetime.now(timezone.utc)
            days_offline = (now - last_verify).days
            return days_offline <= GRACE_PERIOD_DAYS
        except Exception:
            return False

    def _derive_encryption_key(self) -> bytes:
        """Derive encryption key from machine_id (machine-bound encryption)."""
        combined = (self.machine_id + ENCRYPTION_SALT.decode()).encode()
        key_bytes = hashlib.sha256(combined).digest()
        return base64.urlsafe_b64encode(key_bytes)

    def _load_token_cache(self) -> Optional[CachedToken]:
        """Load and decrypt token from disk cache."""
        try:
            if not LICENSE_TOKEN_FILE.exists():
                return None

            # v2.51.0 Security: cryptography is required
            if not CRYPTOGRAPHY_AVAILABLE:
                logger.error("SECURITY: cryptography library is required for PRO features")
                return None

            with open(LICENSE_TOKEN_FILE, "rb") as f:
                file_content = f.read()

            # Try encrypted format first (standard)
            try:
                fernet = Fernet(self._derive_encryption_key())
                decrypted = fernet.decrypt(file_content)
                data = json.loads(decrypted.decode("utf-8"))

                # Handle cache version migration
                version = data.pop("version", 1)
                if version > CACHE_VERSION:
                    logger.warning("Cache version from future, may be incompatible")

                return CachedToken(**data)
            except Exception:
                # Try legacy plaintext format (migration only)
                pass

            # v2.51.0: One-time migration from legacy plaintext to encrypted
            # After migration, plaintext is removed
            try:
                data = json.loads(file_content.decode("utf-8"))
                logger.warning("SECURITY: Migrating legacy plaintext token to encrypted format")
                token = CachedToken(**data)
                # Re-save as encrypted (will overwrite plaintext)
                self._save_token_cache(token)
                return token
            except Exception:
                pass

            return None
        except Exception as e:
            logger.debug(f"Failed to load token cache: {e}")
            return None

    def _save_token_cache(self, token: CachedToken) -> bool:
        """Save encrypted token to disk cache."""
        try:
            LICENSE_TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)

            # Add cache version for future migrations
            data = {"version": CACHE_VERSION, **asdict(token)}
            json_data = json.dumps(data).encode("utf-8")

            if not CRYPTOGRAPHY_AVAILABLE:
                # v2.51.0 Security: cryptography is now required, no plaintext fallback
                logger.error("SECURITY: cryptography library is required for PRO features")
                raise ImportError(
                    "PRO features require the 'cryptography' library. "
                    "Install it with: pip install cryptography"
                )

            # Save encrypted (v2.51.0: plaintext fallback removed)
            fernet = Fernet(self._derive_encryption_key())
            encrypted = fernet.encrypt(json_data)
            with open(LICENSE_TOKEN_FILE, "wb") as f:
                f.write(encrypted)

            return True
        except Exception as e:
            logger.error(f"Failed to save token cache: {e}")
            return False

    def _api_request(self, endpoint: str, data: dict) -> dict:
        """Make API request to license server with retry logic."""
        url = f"{LICENSE_API_URL}{endpoint}"
        last_error = None

        for attempt in range(LICENSE_API_RETRIES):
            try:
                request_data = json.dumps(data).encode("utf-8")
                req = urllib.request.Request(
                    url,
                    data=request_data,
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": f"1c-processor-generator/{__version__}",
                        "X-CLI-Version": __version__,
                        "X-System-Info": json.dumps(get_system_info_cached()),
                    },
                    method="POST"
                )

                with urllib.request.urlopen(req, timeout=LICENSE_API_TIMEOUT) as response:
                    return json.loads(response.read().decode("utf-8"))

            except urllib.error.URLError as e:
                last_error = e
                if attempt < LICENSE_API_RETRIES - 1:
                    sleep_time = 2 ** attempt  # 1, 2, 4 seconds
                    logger.debug(f"API request failed (attempt {attempt + 1}), retrying in {sleep_time}s: {e}")
                    time.sleep(sleep_time)
                continue
            except Exception as e:
                raise LicenseError(f"API error: {e}")

        raise NetworkError(f"Не вдалося з'єднатися з сервером після {LICENSE_API_RETRIES} спроб: {last_error}")

    def _get_no_license_message(self, feature: str) -> str:
        """Get message for unlicensed user."""
        feature_names = {
            "epf_compilation": "EPF компіляція",
            "check_config": "CheckConfig валідація",
            "check_modules": "CheckModules валідація",
        }
        feature_name = feature_names.get(feature, feature)

        return (
            f"{'=' * 60}\n"
            f"{feature_name} потребує PRO ліцензії\n"
            f"{'=' * 60}\n\n"
            f"Придбати PRO: {PURCHASE_URL}\n\n"
            f"Альтернатива: використайте --output-format xml\n"
            f"{'=' * 60}"
        )

    def _get_expired_message(self, expires_at: str) -> str:
        """Get message for expired license."""
        return (
            f"{'=' * 60}\n"
            f"Ваша PRO ліцензія закінчилась {expires_at[:10]}\n"
            f"{'=' * 60}\n\n"
            f"Поновити ліцензію: {ACCOUNT_URL}\n"
            f"{'=' * 60}"
        )

    def _get_machine_limit(self, license_type: str) -> int:
        """Get machine limit for license type."""
        limits = {
            "quarter": 2,
            "year": 3,
            "lifetime": 3,
        }
        return limits.get(license_type, 0)


# =============================================================================
# First-Run Telemetry (v2.59.0)
# =============================================================================

import atexit

_telemetry_thread: Optional[threading.Thread] = None


def send_first_run_telemetry() -> None:
    """Telemetry disabled in community edition."""
    pass


def _wait_for_telemetry():
    """Wait for telemetry thread to complete (max 5 seconds)."""
    if _telemetry_thread and _telemetry_thread.is_alive():
        _telemetry_thread.join(timeout=5)


# Ensure telemetry completes before process exits
atexit.register(_wait_for_telemetry)


# =============================================================================
# Module-level convenience functions
# =============================================================================

_license_manager: Optional[LicenseManager] = None
_license_manager_lock = threading.Lock()


def get_license_manager() -> LicenseManager:
    """Get thread-safe singleton LicenseManager instance."""
    global _license_manager
    if _license_manager is None:
        with _license_manager_lock:
            # Double-check locking pattern
            if _license_manager is None:
                _license_manager = LicenseManager()
    return _license_manager


def is_pro_licensed() -> bool:
    """Quick check if user has PRO license."""
    mgr = get_license_manager()
    is_licensed, _ = mgr.check_pro_feature("epf_compilation")
    return is_licensed


def is_watermark_removed() -> bool:
    """Check if watermark should be removed."""
    mgr = get_license_manager()
    return mgr.is_watermark_removed()
