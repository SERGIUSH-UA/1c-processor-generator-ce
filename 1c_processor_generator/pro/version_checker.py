"""
Version checker - check for new CLI versions.
SPDX-License-Identifier: GPL-3.0-or-later
Copyright (c) 2024-2025 ITDEO
This file is part of 1C Processor Generator Community Edition.
"""

import hashlib
import json
import os
import platform
import sys
import threading
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Inline constants (avoid relative imports for .pyd compatibility)
_LICENSE_API_URL = "https://license.itdeo.tech/api"
_LICENSE_API_TIMEOUT = 15
_EPF_COMPILER_CACHE_DIR = Path(os.environ.get("APPDATA", ".")) / "1C" / "epf_compiler_cache"
_VERSION_CHECK_CACHE_FILE = _EPF_COMPILER_CACHE_DIR / ".version_check"
_VERSION_CHECK_CACHE_HOURS = 72  # 3 days

_version_thread = None
_notification_shown = False


def _get_cli_version() -> str:
    """Get CLI version with multiple fallbacks."""
    # Try direct import
    try:
        from .. import __version__
        return __version__
    except Exception:
        pass

    # Try absolute import
    try:
        import importlib
        pkg = importlib.import_module("1c_processor_generator")
        return getattr(pkg, "__version__", "unknown")
    except Exception:
        pass

    # Try importlib.metadata
    try:
        from importlib.metadata import version
        return version("1c-processor-generator")
    except Exception:
        pass

    return "unknown"


def _generate_machine_id() -> str:
    """Machine ID disabled in community edition."""
    return "community"


def _detect_ci_type() -> str | None:
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


def _get_system_info() -> dict:
    """System info collection disabled in community edition."""
    return {}



def check_version_in_background() -> None:
    """
    Check for new version in background (daemon thread).

    - Runs non-blocking in background
    - Uses cache to avoid frequent API calls (72h interval)
    - Shows notification if new version available
    - Silently ignores all errors
    """
    global _version_thread

    # Don't start multiple threads
    if _version_thread is not None and _version_thread.is_alive():
        return

    def _check():
        try:
            _check_and_notify()
        except Exception:
            # Silently ignore all errors - never break CLI
            pass

    _version_thread = threading.Thread(target=_check, daemon=True)
    _version_thread.start()


def _check_and_notify() -> None:
    """Internal: check version and show notification if needed."""
    current_version = _get_cli_version()
    if current_version == "unknown":
        return

    # Read cache
    cache = _read_cache()

    # Check if cache is valid (< 72h)
    if cache and _is_cache_valid(cache):
        # Use cached data
        latest_version = cache.get("latest_version", "")
        if latest_version and _compare_versions(current_version, latest_version):
            _show_update_notification(current_version, latest_version)
        return

    # Cache expired or missing - make API request
    latest_version = _fetch_latest_version(current_version)
    if not latest_version:
        return

    # Write new cache
    _write_cache(latest_version)

    # Show notification if update available
    if _compare_versions(current_version, latest_version):
        _show_update_notification(current_version, latest_version)


def _is_cache_valid(cache: dict) -> bool:
    """Check if cache is still valid (< 72 hours old)."""
    try:
        checked_at_str = cache.get("checked_at", "")
        if not checked_at_str:
            return False
        # Normalize timezone: add UTC if missing, convert Z to +00:00
        if checked_at_str.endswith("Z"):
            checked_at_str = checked_at_str[:-1] + "+00:00"
        checked_at = datetime.fromisoformat(checked_at_str)
        if checked_at.tzinfo is None:
            checked_at = checked_at.replace(tzinfo=timezone.utc)
        expires_at = checked_at + timedelta(hours=_VERSION_CHECK_CACHE_HOURS)
        return datetime.now(timezone.utc) < expires_at
    except Exception:
        return False


def _read_cache() -> dict | None:
    """Read version check cache."""
    try:
        if not _VERSION_CHECK_CACHE_FILE.exists():
            return None
        with open(_VERSION_CHECK_CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _write_cache(latest_version: str) -> None:
    """Write version check cache."""
    try:
        # Ensure cache directory exists
        _EPF_COMPILER_CACHE_DIR.mkdir(parents=True, exist_ok=True)

        cache = {
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "latest_version": latest_version,
        }
        with open(_VERSION_CHECK_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)
    except Exception:
        pass  # Ignore write errors


def _fetch_latest_version(current_version: str) -> str | None:
    """Fetch latest version from API."""
    try:
        url = f"{_LICENSE_API_URL}/check-version"
        data = {
            "cli_version": current_version,
            "machine_id": _generate_machine_id(),
            "system_info": _get_system_info(),
        }
        request_data = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=request_data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": f"1c-processor-generator/{current_version}",
                "X-CLI-Version": current_version,
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=_LICENSE_API_TIMEOUT) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result.get("latest_version", "")
    except Exception:
        return None


def _compare_versions(current: str, latest: str) -> bool:
    """
    Compare semantic versions.

    Returns True if latest > current.
    """
    try:
        def parse_version(v: str) -> tuple:
            # Remove 'v' prefix if present
            v = v.lstrip("v")
            # Split by dots and convert to integers
            parts = v.split(".")
            return tuple(int(p) for p in parts[:3])

        current_tuple = parse_version(current)
        latest_tuple = parse_version(latest)
        return latest_tuple > current_tuple
    except Exception:
        return False


def _show_update_notification(current: str, latest: str) -> None:
    """Show update notification to user."""
    global _notification_shown

    # Only show once per session
    if _notification_shown:
        return
    _notification_shown = True

    # Format notification
    msg_line1 = f"  New version available: {latest} (current: {current})"
    msg_line2 = "  Update: pip install -U git+https://github.com/SERGIUSH-UA/1c-processor-generator-pro.git"

    # Calculate box width
    max_len = max(len(msg_line1), len(msg_line2))
    box_width = max_len + 2

    # Print notification
    print(file=sys.stderr)
    print("\u256d" + "\u2500" * box_width + "\u256e", file=sys.stderr)
    print("\u2502" + msg_line1.ljust(box_width) + "\u2502", file=sys.stderr)
    print("\u2502" + msg_line2.ljust(box_width) + "\u2502", file=sys.stderr)
    print("\u2570" + "\u2500" * box_width + "\u256f", file=sys.stderr)
    print(file=sys.stderr)
