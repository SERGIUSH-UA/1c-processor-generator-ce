"""
PRO module configuration.
SPDX-License-Identifier: GPL-3.0-or-later
Copyright (c) 2024-2025 ITDEO
This file is part of 1C Processor Generator Community Edition.
"""

from pathlib import Path
import os

# --- Cloud compilation service (primary) ---
CLOUD_API_URL = "https://compile.1c-cloud.ru/api/v3"
CLOUD_API_KEY_ENV = "ONEC_CLOUD_API_KEY"
CLOUD_COMPILATION_TIMEOUT = 180

# --- License service ---
LICENSE_API_URL = "https://license.itdeo.tech/api"
LICENSE_API_TIMEOUT = 15
LICENSE_API_RETRIES = 3

# --- Offline configuration ---
GRACE_PERIOD_DAYS = 7
EXPIRY_WARNING_DAYS = 7

# --- Cache paths ---
EPF_COMPILER_CACHE_DIR = Path(os.environ.get("APPDATA", ".")) / "1C" / "epf_compiler_cache"
LICENSE_TOKEN_FILE = EPF_COMPILER_CACHE_DIR / "license_token.json"
TELEMETRY_SENT_FILE = EPF_COMPILER_CACHE_DIR / ".telemetry_sent"
VERSION_CHECK_CACHE_FILE = EPF_COMPILER_CACHE_DIR / ".version_check"
VERSION_CHECK_CACHE_HOURS = 72  # 3 days
EPF_COMPILER_PERSISTENT_IB = EPF_COMPILER_CACHE_DIR / ".data"
CONF_CFG_LOCALAPPDATA = Path(os.environ.get("LOCALAPPDATA", ".")) / "1C" / "1cv8" / "conf" / "conf.cfg"
CACHE_VERSION = 1

# --- Cloud security ---
ENCRYPTION_SALT = b"1c-processor-generator-v2.50"

# --- Features ---
PRO_FEATURES = [
    "cloud_compilation",  # Only cloud compilation requires PRO license
]

# --- Cloud compilation service (gen.itdeo.tech) ---
CLOUD_COMPILE_URL = "https://gen.itdeo.tech/generate"
CLOUD_HEALTH_URL = "https://gen.itdeo.tech/health"
CLOUD_VERSION_URL = "https://gen.itdeo.tech/version"
CLOUD_COMPILE_TIMEOUT = 180
CLOUD_COMPILE_RETRIES = 2

PURCHASE_URL = "https://itdeo.tech/1c-processor-generator"  # Cloud PRO
ACCOUNT_URL = "https://itdeo.tech/account"  # Cloud PRO account
SUPPORT_EMAIL = "itdeo.tech@gmail.com"
