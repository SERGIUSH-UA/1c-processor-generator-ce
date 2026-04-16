"""
PRO module - conf.cfg manager.
Copyright (c) 2024-2025 ITDEO. All rights reserved.
"""

import logging
import os
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ConfCfgManager:
    """Менеджер conf.cfg."""

    CONF_PATH = Path(os.environ.get("LOCALAPPDATA", ".")) / "1C" / "1cv8" / "conf" / "conf.cfg"
    PARAM_NAME = "DisableUnsafeActionProtection"

    REQUIRED_MASKS = [
        ".*epf_compiler_cache.*",
    ]

    def __init__(self, conf_path: Optional[Path] = None):
        self.conf_path = conf_path or self.CONF_PATH

    def check_configuration(self) -> tuple[bool, list[str]]:
        """Перевіряє конфігурацію. Повертає (is_ok, missing_masks)."""
        current_masks = self.get_current_masks()
        missing = [m for m in self.REQUIRED_MASKS if m not in current_masks]
        return (len(missing) == 0, missing)

    def configure(self, dry_run: bool = False) -> bool:
        """Налаштовує conf.cfg. Повертає True якщо успішно."""
        try:
            is_ok, missing_masks = self.check_configuration()
            if is_ok:
                return True

            if dry_run:
                return True

            lines, current_value = self._parse_conf_cfg()

            if current_value:
                existing = [m.strip() for m in current_value.split(";") if m.strip()]
                new_value = ";".join(existing + missing_masks)
            else:
                new_value = ";".join(self.REQUIRED_MASKS)

            return self._write_conf_cfg(lines, new_value)

        except PermissionError:
            logger.debug("Permission denied")
            return False
        except Exception:
            return False

    def get_current_masks(self) -> list[str]:
        """Повертає поточні маски."""
        _, current_value = self._parse_conf_cfg()
        if not current_value:
            return []
        return [m.strip() for m in current_value.split(";") if m.strip()]

    def _parse_conf_cfg(self) -> tuple[list[str], Optional[str]]:
        if not self.conf_path.exists():
            return ([], None)

        try:
            content = self.conf_path.read_text(encoding="utf-8")
        except Exception:
            return ([], None)

        lines = content.splitlines()
        current_value = None
        pattern = re.compile(rf"^\s*{re.escape(self.PARAM_NAME)}\s*=\s*(.*)$", re.IGNORECASE)

        for line in lines:
            match = pattern.match(line)
            if match:
                current_value = match.group(1).strip()
                break

        return (lines, current_value)

    def _write_conf_cfg(self, lines: list[str], new_value: str) -> bool:
        try:
            self.conf_path.parent.mkdir(parents=True, exist_ok=True)

            pattern = re.compile(rf"^\s*{re.escape(self.PARAM_NAME)}\s*=", re.IGNORECASE)
            found = False
            new_lines = []

            for line in lines:
                if pattern.match(line):
                    new_lines.append(f"{self.PARAM_NAME}={new_value}")
                    found = True
                else:
                    new_lines.append(line)

            if not found:
                while new_lines and (not new_lines[-1].strip() or new_lines[-1].strip() == "\\"):
                    new_lines.pop()
                new_lines.append(f"{self.PARAM_NAME}={new_value}")

            content = "\n".join(new_lines)
            if not content.endswith("\n"):
                content += "\n"

            self.conf_path.write_text(content, encoding="utf-8")
            logger.debug("conf.cfg updated")
            return True

        except Exception:
            return False


def run_setup_command(check: bool = False, dry_run: bool = False) -> int:
    """CLI command handler for setup-1c."""
    m = ConfCfgManager()
    ok, missing = m.check_configuration()

    if check:
        if ok:
            print("OK")
            return 0
        print(f"MISSING: {';'.join(missing)}")
        return 1

    if ok:
        print(f"OK: {m.conf_path}")
        return 0

    if dry_run:
        print(f"[DRY] {';'.join(missing)}")
        return 0

    if m.configure():
        print(f"Done: {m.conf_path}")
        return 0

    print(f"Error: {m.conf_path}")
    return 1
