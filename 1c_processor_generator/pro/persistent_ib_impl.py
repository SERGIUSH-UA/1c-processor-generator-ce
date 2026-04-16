"""
Persistent InfoBase Manager - керування кешованою інфобазою для компіляції

Модуль забезпечує управління постійною інфобазою для прискорення компіляції EPF.
Persistent IB економить 3-5 секунд на кожній компіляції, уникаючи повторного
створення тимчасової бази.

Використання:
    >>> manager = PersistentIBManager(designer_path)
    >>> ib_path = manager.get_or_create()
    >>> if ib_path:
    ...     print(f"Використовую IB: {ib_path}")
"""

import subprocess
from pathlib import Path
from typing import Optional
import logging

# v2.52.0: Import from PRO constants (compiled to .pyd for protection)
try:
    # When running as compiled .pyd
    from constants import (
        EPF_COMPILER_CACHE_DIR,
        EPF_COMPILER_PERSISTENT_IB,
    )
except ImportError:
    # When running as part of package
    from .constants import (
        EPF_COMPILER_CACHE_DIR,
        EPF_COMPILER_PERSISTENT_IB,
    )

logger = logging.getLogger(__name__)


# v2.70.1: Windows Defender detection
def _is_windows_defender_block(error_text: str) -> bool:
    """
    Detect if error is caused by Windows Defender blocking 1C.

    Args:
        error_text: Error message from subprocess

    Returns:
        True if Windows Defender is blocking, False otherwise
    """
    if not error_text:
        return False
    error_lower = error_text.lower()
    # Detection patterns for Windows Defender blocking
    patterns = [
        "вирус",  # Russian: virus
        "virus",
        "0x800700e1",  # ERROR_VIRUS_INFECTED
        "потенциально нежелательную программу",  # Russian: potentially unwanted
        "potentially unwanted",
        "malware",
        "threat",
    ]
    return any(p in error_lower for p in patterns)


def _show_windows_defender_help():
    """Show instructions for adding Windows Defender exclusions."""
    print("\n" + "=" * 70)
    print("⚠️  Windows Defender блокує 1C Designer!")
    print("=" * 70)
    print("\n📋 ПРИЧИНА:")
    print("   Windows Defender виявив загрозу у файлах 1C:Enterprise.")
    print("   Це може статися через:")
    print("   • Модифіковану/крякнуту версію 1C (patch, crack, activator)")
    print("   • False positive на легітимній версії (рідко)")
    print("\n   Типова детекція: Trojan:Win32/Kepavll!rfn у файлі h.tmp")
    print("   Це НЕ проблема генератора EPF - це ваша інсталяція 1C.\n")
    print("🔧 РІШЕННЯ:")
    print("   Варіант 1: Використовуйте ліцензійну версію 1C")
    print("   Варіант 2: Додайте виключення в Windows Security:\n")
    print("   1. Відкрийте: Windows Security → Virus & threat protection")
    print("   2. Натисніть: Manage settings → Exclusions → Add exclusion")
    print("   3. Додайте папку: C:\\Program Files\\1cv8")
    print("   4. Додайте папку: %APPDATA%\\1C\\epf_compiler_cache")
    print("   5. Додайте папку: %TEMP% (для h.tmp)\n")
    print("   Або запустіть PowerShell як Administrator:")
    print('   Add-MpPreference -ExclusionPath "C:\\Program Files\\1cv8"')
    print('   Add-MpPreference -ExclusionProcess "1cv8.exe"')
    print('   Add-MpPreference -ExclusionProcess "1cv8s.exe"')
    print("=" * 70 + "\n")


# v2.66.1: Version parsing and compatibility functions
def _parse_platform_version(version: str) -> tuple:
    """
    Parse platform version to (major, minor, patch) tuple.

    Args:
        version: Version string like "8.3.25.1394" or "8.3.25"

    Returns:
        Tuple (8, 3, 25) or None if parsing fails
    """
    if not version:
        return None
    parts = version.split(".")
    if len(parts) >= 3:
        try:
            return (int(parts[0]), int(parts[1]), int(parts[2]))
        except ValueError:
            return None
    return None


def _versions_compatible(stored: str, current: str) -> bool:
    """
    Check if platform versions are compatible (same 8.3.XX).

    Compatibility is determined by major.minor.patch (first 3 parts).
    Build number (4th part) is ignored - different builds of same
    minor version are compatible.

    Args:
        stored: Stored version in cache (e.g., "8.3.25.1394")
        current: Current platform version (e.g., "8.3.25.1500")

    Returns:
        True if versions are compatible, False otherwise
    """
    stored_tuple = _parse_platform_version(stored)
    current_tuple = _parse_platform_version(current)

    if not stored_tuple or not current_tuple:
        return False

    return stored_tuple == current_tuple


class PersistentIBManager:
    """
    Менеджер постійної інфобази для EPF компіляції.

    Persistent IB зберігається в кеші (%APPDATA%/1C/epf_compiler_cache/.data)
    і використовується для всіх компіляцій, що економить 3-5 сек на кожній.

    Attributes:
        designer_path: Шлях до Designer (1cv8.exe)
        cache_dir: Директорія для кешу (з constants)
        ib_path: Шлях до persistent IB (з constants)

    Example:
        >>> manager = PersistentIBManager(Path("C:/Program Files/1cv8/8.3.25/bin/1cv8.exe"))
        >>> ib = manager.get_or_create()
        >>> if ib:
        ...     print(f"IB готова: {ib}")
        ... else:
        ...     print("Помилка створення IB")
    """

    def __init__(
        self,
        designer_path: Path,
        cache_dir: Optional[Path] = None,
        ib_path: Optional[Path] = None,
        platform_version: Optional[str] = None
    ):
        """
        Ініціалізація менеджера persistent IB.

        Args:
            designer_path: Шлях до Designer (1cv8.exe)
            cache_dir: Кастомна директорія кешу (опціонально, для тестування)
            ib_path: Кастомний шлях до IB (опціонально, для тестування)
            platform_version: Версія платформи 1C (наприклад "8.3.25.1394")
        """
        self.designer_path = designer_path
        self.cache_dir = cache_dir or EPF_COMPILER_CACHE_DIR
        self.ib_path = ib_path or EPF_COMPILER_PERSISTENT_IB
        self.platform_version = platform_version
        # v2.64.1: Файл для зберігання версії платформи
        self._version_file = self.ib_path / ".platform_version" if self.ib_path else None

    def get_or_create(self, timeout: int = 60) -> Optional[Path]:
        """
        Отримує існуючу або створює нову persistent IB.

        Якщо IB вже існує - повертає шлях до неї.
        Якщо не існує - створює нову через Designer CREATEINFOBASE.

        Args:
            timeout: Таймаут створення інфобази в секундах (за замовчуванням 60)

        Returns:
            Path до persistent IB або None якщо помилка

        Example:
            >>> manager = PersistentIBManager(designer_path)
            >>> ib = manager.get_or_create()
            >>> if ib and ib.exists():
            ...     print("IB готова для використання")
        """
        if not self.designer_path:
            logger.error("Designer path не вказано")
            return None

        # Створюємо директорію кешу якщо не існує
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Не вдалося створити cache директорію: {e}")
            return None

        # Якщо база вже існує - перевіряємо версію
        if self.ib_path.exists():
            # v2.64.1: Перевіряємо чи версія платформи співпадає
            if self._check_version_compatibility():
                logger.debug(f"Використання існуючої persistent IB: {self.ib_path}")
                return self.ib_path
            else:
                # Версія не співпадає - перестворюємо
                logger.info(f"🔄 Persistent IB створена для іншої платформи, перестворюємо...")
                self._clear_ib()

        # Створюємо нову
        logger.info(f"Створення persistent IB: {self.ib_path}")
        result = self._create_infobase(timeout)

        # Зберігаємо версію платформи
        if result and self.platform_version:
            self._save_version()

        return result

    def clear_cache(self) -> bool:
        """
        Очищає весь кеш (видаляє persistent IB та директорію).

        Використовуйте якщо persistent IB пошкоджена або для звільнення місця.
        Видаляє директорію cache_dir та всі її вмісти.

        Returns:
            True якщо успішно, False якщо помилка

        Example:
            >>> manager = PersistentIBManager(designer_path)
            >>> if manager.clear_cache():
            ...     print("Кеш очищено")
            ... else:
            ...     print("Помилка очистки")

        Note:
            Після очистки кешу persistent IB буде створена заново
            при наступному виклику get_or_create().
        """
        if not self.cache_dir.exists():
            logger.info("Кеш директорія не існує, нічого видаляти")
            return True

        try:
            import shutil
            shutil.rmtree(self.cache_dir)
            logger.info(f"✓ Кеш очищено: {self.cache_dir}")
            return True

        except Exception as e:
            logger.error(f"✗ Помилка очистки кешу: {e}")
            return False

    def exists(self) -> bool:
        """
        Перевіряє чи існує persistent IB.

        Returns:
            True якщо IB існує, False якщо ні
        """
        return self.ib_path.exists()

    def get_cache_info(self) -> dict:
        """
        v2.66.1: Повертає інформацію про кеш для CLI діагностики.

        Returns:
            dict з path, exists, platform_version, created_at або None якщо кеш не існує
        """
        if not self.ib_path or not self.ib_path.exists():
            return None

        info = {
            "path": str(self.ib_path),
            "exists": True,
        }

        if self._version_file and self._version_file.exists():
            try:
                info["platform_version"] = self._version_file.read_text(encoding="utf-8").strip()
                from datetime import datetime
                info["created_at"] = datetime.fromtimestamp(
                    self._version_file.stat().st_mtime
                ).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                pass

        return info

    def _configure_security(self) -> bool:
        """Configure conf.cfg for EPF compilation (v2.56.0+)."""
        try:
            from .conf_cfg_manager import ConfCfgManager
            manager = ConfCfgManager()
            return manager.configure()
        except Exception:
            return False

    def _check_version_compatibility(self) -> bool:
        """
        v2.66.1: Перевіряє чи persistent IB сумісна з поточною платформою.

        Логіка:
        - Якщо версія не визначена → FAILSAFE: інвалідуємо кеш
        - Якщо файл версії не існує → інвалідуємо (старий кеш)
        - Порівняння на рівні minor версії (8.3.XX)

        Returns:
            True якщо версії сумісні, False якщо потрібно перестворити IB
        """
        if not self.platform_version:
            # v2.66.1: FAILSAFE - якщо версія не визначена, краще перестворити IB
            logger.warning(
                "⚠️ Platform version not detected. Invalidating cache for safety. "
                "Tip: Use --compiler-path for reliable detection."
            )
            return False

        if not self._version_file or not self._version_file.exists():
            # Якщо файл версії не існує (старий кеш) - потрібно перестворити
            logger.debug("Файл версії не знайдено, потрібно перестворити IB")
            return False

        try:
            stored_version = self._version_file.read_text(encoding="utf-8").strip()

            # v2.66.1: Використовуємо порівняння на рівні minor версії
            if _versions_compatible(stored_version, self.platform_version):
                logger.debug(f"IB compatible: {stored_version} ~ {self.platform_version}")
                return True
            else:
                logger.info(f"🔄 Platform change: {stored_version} → {self.platform_version}")
                return False

        except Exception as e:
            logger.debug(f"Помилка читання версії: {e}")
            return False

    def _save_version(self) -> bool:
        """
        v2.64.1: Зберігає версію платформи у файл.

        Returns:
            True якщо успішно, False якщо помилка
        """
        if not self._version_file or not self.platform_version:
            return False

        try:
            self._version_file.write_text(self.platform_version, encoding="utf-8")
            logger.debug(f"Збережено версію платформи: {self.platform_version}")
            return True
        except Exception as e:
            logger.debug(f"Помилка збереження версії: {e}")
            return False

    def _clear_ib(self) -> bool:
        """
        v2.64.1: Очищає тільки директорію persistent IB (не весь кеш).

        Returns:
            True якщо успішно, False якщо помилка
        """
        if not self.ib_path or not self.ib_path.exists():
            return True

        try:
            import shutil
            shutil.rmtree(self.ib_path)
            logger.debug(f"Очищено persistent IB: {self.ib_path}")
            return True
        except Exception as e:
            logger.error(f"Помилка очистки IB: {e}")
            return False

    def _create_infobase(self, timeout: int) -> Optional[Path]:
        """
        Створює нову persistent IB через Designer.

        Args:
            timeout: Таймаут виконання в секундах

        Returns:
            Path до створеної IB або None якщо помилка
        """
        create_ib_command = [
            str(self.designer_path),
            "CREATEINFOBASE",
            f"File={self.ib_path}",
        ]

        logger.debug(f"Команда створення IB: {' '.join(create_ib_command)}")

        try:
            result = subprocess.run(
                create_ib_command,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )

            if result.returncode != 0:
                logger.error(f"✗ Помилка створення persistent IB (код {result.returncode})")
                if result.stderr:
                    logger.error(f"Помилка: {result.stderr}")
                    # v2.70.1: Detect Windows Defender blocking
                    if _is_windows_defender_block(result.stderr):
                        _show_windows_defender_help()
                return None

            logger.info(f"✓ Persistent IB створено: {self.ib_path}")

            # Налаштовуємо security для автоматичного завантаження EPF без діалогів
            self._configure_security()

            return self.ib_path

        except subprocess.TimeoutExpired:
            logger.error(f"✗ Таймаут створення persistent IB ({timeout}s)")
            return None

        except Exception as e:
            logger.error(f"✗ Помилка створення persistent IB: {e}")
            return None

    @staticmethod
    def clear_global_cache() -> bool:
        """
        Статичний метод для очистки глобального кешу.

        Використовує константи з constants.py для визначення шляху.

        Returns:
            True якщо успішно, False якщо помилка

        Example:
            >>> PersistentIBManager.clear_global_cache()
            True

        Note:
            Це зручний метод для CLI команд (не потребує ініціалізації об'єкта).
        """
        if not EPF_COMPILER_CACHE_DIR.exists():
            logger.info("ℹ️ Кеш директорія не існує")
            return True

        try:
            import shutil
            shutil.rmtree(EPF_COMPILER_CACHE_DIR)
            logger.info(f"✓ Кеш очищено: {EPF_COMPILER_CACHE_DIR}")
            return True

        except Exception as e:
            logger.error(f"✗ Помилка очистки кешу: {e}")
            return False
