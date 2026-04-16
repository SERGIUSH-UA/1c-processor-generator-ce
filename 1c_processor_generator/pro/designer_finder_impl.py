"""
Пошук 1C Designer (1cv8.exe) в системі

Модуль забезпечує автоматичний пошук Designer через:
1. Змінну середовища PATH_1C_DESIGNER
2. Windows реєстр (HKLM\\SOFTWARE\\1C\\1CEStart)
3. Стандартні директорії (C:\\Program Files\\1cv8\\)

Використання:
    >>> finder = DesignerFinder()
    >>> designer_path = finder.find()
    >>> if designer_path:
    ...     print(f"Designer знайдено: {designer_path}")
"""

import os
from pathlib import Path
from typing import Optional, List
import logging

# v2.64.4: Enable DEBUG logging when debug env var is set
# v2.64.7: Obfuscated env var name
_DBG_KEY = bytes([0x31,0x43,0x5f,0x50,0x47,0x5f,0x44,0x45,0x42,0x55,0x47]).decode()
DEBUG_MODE = os.environ.get(_DBG_KEY, "").lower() in ("1", "true", "yes")
if DEBUG_MODE:
    logging.basicConfig(level=logging.DEBUG, format='%(name)s: %(message)s')

try:
    # When running as compiled .pyd
    from _protected import (
        STANDARD_DESIGNER_PATHS_WINDOWS,
        ENV_DESIGNER_PATH,
    )
except ImportError:
    # When running as part of package
    from .._protected import (
        STANDARD_DESIGNER_PATHS_WINDOWS,
        ENV_DESIGNER_PATH,
    )

logger = logging.getLogger(__name__)


class DesignerFinder:
    """
    Клас для пошуку 1C Designer в системі.

    Виконує каскадний пошук через різні джерела:
    1. Змінна середовища PATH_1C_DESIGNER
    2. Windows реєстр
    3. Стандартні шляхи

    Attributes:
        designer_path: Знайдений шлях до Designer або None

    Example:
        >>> finder = DesignerFinder()
        >>> if finder.designer_path:
        ...     print(f"Знайдено: {finder.designer_path}")
        ... else:
        ...     print("Designer не знайдено")
    """

    def __init__(self, explicit_path: Optional[str] = None):
        """
        Ініціалізація з опціональним явним шляхом.

        Args:
            explicit_path: Явний шлях до 1cv8.exe. Якщо вказано і валідний,
                          автоматичний пошук не виконується.
        """
        self.designer_path: Optional[Path] = None
        # v2.64.1: Зберігаємо версію платформи разом з шляхом
        # Заповнюється при знаходженні через реєстр або стандартні шляхи
        self.platform_version: Optional[str] = None

        if explicit_path:
            # v2.64.6: Діагностика (тільки при DEBUG_MODE)
            if DEBUG_MODE:
                print(f"📝 _df.__init__: explicit_path={explicit_path}")
            self.designer_path = self._validate_path(Path(explicit_path))
            if DEBUG_MODE:
                print(f"📝 _df.__init__: validated_path={self.designer_path}")
            if self.designer_path:
                # v2.64.3: Спочатку пробуємо отримати версію з exe, потім зі шляху
                self.platform_version = self._get_file_version(self.designer_path)
                if self.platform_version:
                    if DEBUG_MODE:
                        print(f"📝 _df.__init__: version from exe={self.platform_version}")
                    logger.debug(f"Версію отримано з exe metadata: {self.platform_version}")
                else:
                    if DEBUG_MODE:
                        print(f"📝 _df.__init__: exe version failed, trying path extraction")
                    self.platform_version = self._extract_version_from_path(self.designer_path)
                    if self.platform_version:
                        if DEBUG_MODE:
                            print(f"📝 _df.__init__: version from path={self.platform_version}")
                        logger.debug(f"Версію отримано зі шляху: {self.platform_version}")
                    else:
                        if DEBUG_MODE:
                            print(f"⚠️ _df.__init__: FAILED to extract version from path: {self.designer_path}")
                        logger.warning(f"⚠️ Не вдалося визначити версію для: {self.designer_path}")
            else:
                if DEBUG_MODE:
                    print(f"⚠️ _df.__init__: path validation FAILED for: {explicit_path}")
                logger.warning(f"Вказаний Designer не знайдено: {explicit_path}")

        if not self.designer_path:
            self.designer_path = self.find()

    def find(self) -> Optional[Path]:
        """
        Виконує каскадний пошук Designer.

        Порядок пошуку:
        1. Змінна середовища PATH_1C_DESIGNER
        2. Windows реєстр (HKLM\\SOFTWARE\\1C\\1CEStart)
        3. Стандартні шляхи (C:\\Program Files\\1cv8\\)

        Returns:
            Path до 1cv8.exe або None якщо не знайдено
        """
        designer = None

        # 1. Змінна середовища
        designer = self._find_from_env()
        if designer:
            logger.info(f"Designer знайдено через змінну середовища: {designer}")

        # 2. Windows реєстр
        if not designer:
            designer = self._find_from_registry()
            if designer:
                logger.info(f"Designer знайдено через реєстр: {designer}")

        # 3. Стандартні шляхи
        if not designer:
            designer = self._find_from_standard_paths()
            if designer:
                logger.info(f"Designer знайдено у стандартному шляху: {designer}")

        if not designer:
            logger.warning("Designer не знайдено жодним способом")
            return None

        # v2.64.4: Страховка - якщо Designer знайдено але версія не визначена,
        # пробуємо отримати з метаданих exe файлу
        if not self.platform_version:
            self.platform_version = self._get_file_version(designer)
            if self.platform_version:
                logger.info(f"Версію платформи отримано з exe: {self.platform_version}")
            else:
                # Останній fallback - спробувати витягти зі шляху
                self.platform_version = self._extract_version_from_path(designer)
                if self.platform_version:
                    logger.info(f"Версію платформи отримано зі шляху: {self.platform_version}")
                else:
                    # v2.64.4: Діагностичне повідомлення для debug
                    logger.warning(f"⚠️ Не вдалося визначити версію платформи для: {designer}")

        return designer

    def _validate_path(self, path: Path) -> Optional[Path]:
        """
        Перевіряє чи є path валідним Designer.

        Args:
            path: Шлях для перевірки

        Returns:
            Path якщо валідний, None якщо ні
        """
        if not path.exists():
            return None

        # Support both Windows (1cv8.exe) and Linux (1cv8)
        valid_names = ("1cv8.exe", "1cv8")
        if path.name.lower() in valid_names:
            return path
        return None

    def _extract_version_from_path(self, path: Path) -> Optional[str]:
        """
        v2.64.1: Витягує версію платформи з шляху до Designer.

        Шлях має формат:
        - Windows: C:\\Program Files\\1cv8\\8.3.25.1394\\bin\\1cv8.exe
        - Linux: /opt/1cv8/x86_64/8.3.27.1936/1cv8
        - Linux symlink: /opt/1cv8/current/1cv8 -> /opt/1cv8/x86_64/8.3.27.1936/1cv8

        Args:
            path: Шлях до 1cv8.exe або 1cv8

        Returns:
            Версія платформи (наприклад "8.3.25.1394") або None
        """
        import re

        # Try original path first
        path_str = str(path)
        match = re.search(r'(8\.3\.\d+\.\d+)', path_str)
        if match:
            return match.group(1)

        # On Linux, resolve symlinks (e.g., /opt/1cv8/current -> /opt/1cv8/x86_64/8.3.27.1936)
        try:
            resolved_path = str(path.resolve())
            if resolved_path != path_str:
                match = re.search(r'(8\.3\.\d+\.\d+)', resolved_path)
                if match:
                    return match.group(1)
        except Exception:
            pass

        return None

    def _get_file_version(self, path: Path) -> Optional[str]:
        """
        v2.64.3: Отримує версію з метаданих exe файлу (FileVersion).

        Працює для будь-якого шляху, не залежить від назви директорії.
        Використовує win32api.GetFileVersionInfo() для читання версії.

        Args:
            path: Шлях до 1cv8.exe

        Returns:
            Версія у форматі "8.3.25.1394" або None
        """
        try:
            import win32api
            info = win32api.GetFileVersionInfo(str(path), "\\")
            ms = info['FileVersionMS']
            ls = info['FileVersionLS']
            version = f"{ms >> 16}.{ms & 0xFFFF}.{ls >> 16}.{ls & 0xFFFF}"
            # Перевірка що це версія 1C (8.x.x.x)
            if version.startswith("8."):
                logger.debug(f"Got version from exe metadata: {version}")
                return version
            return None
        except ImportError:
            logger.debug("win32api not available, skipping exe version detection")
            return None
        except Exception as e:
            logger.debug(f"Cannot get file version from {path}: {e}")
            return None

    def _find_from_env(self) -> Optional[Path]:
        """
        Пошук Designer через змінну середовища PATH_1C_DESIGNER.

        Returns:
            Path до 1cv8.exe або None
        """
        env_path = os.environ.get(ENV_DESIGNER_PATH)
        if not env_path:
            logger.debug(f"Змінна середовища {ENV_DESIGNER_PATH} не встановлена")
            return None

        designer = Path(env_path)
        validated = self._validate_path(designer)

        if not validated:
            logger.warning(
                f"{ENV_DESIGNER_PATH} вказує на неіснуючий файл: {env_path}"
            )
        else:
            # v2.64.3: Спочатку пробуємо отримати версію з exe, потім зі шляху
            self.platform_version = (
                self._get_file_version(validated) or
                self._extract_version_from_path(validated)
            )
            if self.platform_version:
                logger.debug(f"Версія платформи: {self.platform_version}")

        return validated

    def _find_from_registry(self) -> Optional[Path]:
        """
        Пошук Designer через Windows реєстр.

        Шукає в HKLM\\SOFTWARE\\1C\\1CEStart для знаходження встановлених
        версій платформи. Повертає найновішу версію.

        Returns:
            Path до 1cv8.exe найновішої версії або None
        """
        try:
            import winreg  # Windows-specific
        except ImportError:
            logger.debug("winreg недоступний (не Windows платформа)")
            return None

        try:
            # Відкриваємо ключ реєстру 1C
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\1C\1CEStart",
                0,
                winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
            )

            # Читаємо всі версії
            versions = self._enum_registry_keys(key)
            winreg.CloseKey(key)

            if not versions:
                logger.debug("Версії платформи в реєстрі не знайдено")
                return None

            # Сортуємо версії (найновіша перша)
            versions.sort(reverse=True)
            logger.debug(f"Знайдено версії в реєстрі: {versions}")

            # Шукаємо Designer для найновішої версії
            return self._find_designer_for_versions(versions)

        except Exception as e:
            logger.debug(f"Помилка пошуку в реєстрі: {e}")
            return None

    def _enum_registry_keys(self, key) -> List[str]:
        """
        Перераховує всі підключі в реєстрі.

        Args:
            key: Відкритий ключ реєстру

        Returns:
            Список назв підключів
        """
        import winreg

        versions = []
        i = 0
        while True:
            try:
                version = winreg.EnumKey(key, i)
                versions.append(version)
                i += 1
            except OSError:
                break

        return versions

    def _find_designer_for_versions(self, versions: List[str]) -> Optional[Path]:
        """
        Шукає Designer для списку версій.

        Args:
            versions: Відсортований список версій (найновіша перша)

        Returns:
            Path до Designer або None
        """
        import winreg

        for version in versions:
            try:
                version_key = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    rf"SOFTWARE\1C\1CEStart\{version}",
                    0,
                    winreg.KEY_READ | winreg.KEY_WOW64_64KEY,
                )

                install_path = winreg.QueryValueEx(version_key, "InstallLocation")[0]
                winreg.CloseKey(version_key)

                designer = Path(install_path) / "bin" / "1cv8.exe"

                if designer.exists():
                    logger.debug(f"Designer знайдено для версії {version}: {designer}")
                    # v2.64.1: Зберігаємо версію платформи
                    self.platform_version = version
                    return designer

            except Exception as e:
                logger.debug(f"Помилка читання версії {version}: {e}")
                continue

        return None

    def _find_from_standard_paths(self) -> Optional[Path]:
        """
        Пошук Designer у стандартних директоріях.

        Шукає в:
        - C:\\Program Files\\1cv8\\
        - C:\\Program Files (x86)\\1cv8\\

        Returns:
            Path до 1cv8.exe найновішої версії або None
        """
        for base_path_str in STANDARD_DESIGNER_PATHS_WINDOWS:
            base_path = Path(base_path_str)

            if not base_path.exists():
                logger.debug(f"Стандартний шлях не існує: {base_path}")
                continue

            # Шукаємо найновішу версію (8.3.xx.yyyy)
            versions = self._get_platform_versions(base_path)

            if not versions:
                logger.debug(f"Версії не знайдено в {base_path}")
                continue

            logger.debug(f"Знайдено версії в {base_path}: {[v.name for v in versions]}")

            # Перевіряємо кожну версію (найновіша перша)
            for version_dir in versions:
                designer = version_dir / "bin" / "1cv8.exe"

                if designer.exists():
                    logger.debug(f"Designer знайдено: {designer}")
                    # v2.64.1: Зберігаємо версію платформи з назви директорії
                    self.platform_version = version_dir.name
                    return designer

        return None

    def _get_platform_versions(self, base_path: Path) -> List[Path]:
        """
        Знаходить всі версії платформи в базовій директорії.

        Args:
            base_path: Базова директорія (наприклад, C:\\Program Files\\1cv8)

        Returns:
            Список директорій версій, відсортований від найновішої до найстарішої
        """
        if not base_path.exists():
            return []

        # Шукаємо директорії з патерном 8.3.xx.yyyy
        try:
            versions = sorted(
                [d for d in base_path.iterdir() if d.is_dir() and d.name.startswith("8.3")],
                reverse=True,  # Найновіша версія перша
            )
        except (OSError, FileNotFoundError):
            # Шлях існує але недоступний, або був видалений між exists() та iterdir()
            return []

        return versions
