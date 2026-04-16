"""
EPF Compiler - компіляція XML процесорів у EPF формат через 1C Designer

Модуль забезпечує автоматичну компіляцію згенерованих XML процесорів
у бінарний EPF формат для безпосереднього запуску в 1С:Підприємство.

Використання:
    >>> compiler = EPFCompiler()
    >>> if compiler.designer_path:
    ...     compiler.compile_epf(
    ...         xml_root=Path("МояОбробка/МояОбробка.xml"),
    ...         output_epf=Path("МояОбробка.epf")
    ...     )
"""

import subprocess
import tempfile
import secrets
import os
from pathlib import Path
from typing import Optional, List, Dict, Tuple
import logging
import shutil
from dataclasses import dataclass

# v2.52.0: Debug mode for development (internal use only)
# v2.64.5: Obfuscated env var name to prevent discovery
_DBG_KEY = bytes([0x31,0x43,0x5f,0x50,0x47,0x5f,0x44,0x45,0x42,0x55,0x47]).decode()
DEBUG_MODE = os.environ.get(_DBG_KEY, "").lower() in ("1", "true", "yes")

# v2.64.4: Enable DEBUG logging when DEBUG_MODE is on
if DEBUG_MODE:
    import logging
    logging.basicConfig(level=logging.DEBUG, format='%(name)s: %(message)s')

try:
    # When running as compiled .pyd
    from _protected import (
        DESIGNER_SILENT_PARAMS,
        DESIGNER_LOAD_EPF_COMMAND,
        DESIGNER_DUMP_EPF_COMMAND,
        DESIGNER_CHECK_MODULES_COMMAND,
        DESIGNER_CHECK_CONFIG_COMMAND,
        CHECK_MODULES_PARAMS,
        CHECK_CONFIG_BASE_PARAMS,
        CHECK_CONFIG_SEMANTIC_CHECKS,
    )
    from designer_finder_impl import DesignerFinder
    from persistent_ib_impl import (
        PersistentIBManager,
        _is_windows_defender_block,
        _show_windows_defender_help,
    )
    from xml_converter_impl import XMLConverter
    from log_parser_impl import DesignerLogParser
except ImportError:
    # When running as part of package
    from .._protected import (
        DESIGNER_SILENT_PARAMS,
        DESIGNER_LOAD_EPF_COMMAND,
        DESIGNER_DUMP_EPF_COMMAND,
        DESIGNER_CHECK_MODULES_COMMAND,
        DESIGNER_CHECK_CONFIG_COMMAND,
        CHECK_MODULES_PARAMS,
        CHECK_CONFIG_BASE_PARAMS,
        CHECK_CONFIG_SEMANTIC_CHECKS,
    )
    from .designer_finder_impl import DesignerFinder
    from .persistent_ib_impl import (
        PersistentIBManager,
        _is_windows_defender_block,
        _show_windows_defender_help,
    )
    from .xml_converter_impl import XMLConverter
    from .log_parser_impl import DesignerLogParser

logger = logging.getLogger(__name__)


@dataclass
class CompilationContext:
    """
    Контекст компіляції EPF з Configuration.

    Зберігає всі необхідні параметри для передачі між кроками компіляції.
    """
    processor_xml_dir: Path
    output_epf: Path
    processor: any  # Processor об'єкт з models.py
    requirements: any  # MetadataRequirements з metadata_analyzer.py
    timeout: int = 180


class EPFCompiler:
    """
    Компілятор XML процесорів у EPF формат через 1C Designer.

    Підтримує два режими компіляції:
    1. Швидкий режим - для простих процесорів без CatalogRef/DocumentRef
    2. Configuration mode - для складних процесорів з метаданими

    Attributes:
        designer_path: Шлях до знайденого Designer (1cv8.exe)
        use_persistent_ib: Використовувати persistent IB кеш
        ib_manager: Менеджер persistent IB
        xml_converter: Конвертор XML файлів

    Example:
        >>> compiler = EPFCompiler()
        >>> if compiler.designer_path:
        ...     success = compiler.compile_epf(
        ...         xml_root=Path("МояОбробка/МояОбробка.xml"),
        ...         output_epf=Path("МояОбробка.epf")
        ...     )
    """


    def __init__(
        self,
        designer_path: Optional[str] = None,
        use_persistent_ib: bool = True
    ):
        """
        Ініціалізація EPF компілятора.

        IMPORTANT: This class should only be instantiated via LicensedEPFCompiler.
        Direct instantiation will raise a RuntimeError.

        Args:
            designer_path: Явний шлях до 1cv8.exe (Designer).
                          Якщо не вказано - виконується автоматичний пошук.
            use_persistent_ib: Використовувати постійну кеш-базу (швидше на 3-5 сек).
                              За замовчуванням True.
        """
        # Community edition: no license guard

        self.use_persistent_ib = use_persistent_ib

        # Пошук Designer
        finder = DesignerFinder(explicit_path=designer_path)
        self.designer_path = finder.designer_path

        if self.designer_path:
            logger.info(f"Designer знайдено: {self.designer_path}")
            # v2.64.3: Порядок визначення версії:
            # 1. DesignerFinder (реєстр, exe metadata, шлях)
            # 2. File version (win32api)
            # 3. Path extraction (regex)
            self.installed_platform_version = (
                finder.platform_version or
                self._get_file_version(self.designer_path) or
                self._extract_platform_version(self.designer_path)
            )
            if self.installed_platform_version:
                logger.info(f"Версія платформи: {self.installed_platform_version}")
            # Ініціалізуємо менеджер persistent IB
            # v2.64.1: Передаємо версію платформи для перевірки сумісності
            self.ib_manager = PersistentIBManager(
                self.designer_path,
                platform_version=self.installed_platform_version
            )
            # v2.56.0: Auto-configure conf.cfg on first use
            self._ensure_conf_cfg_configured()
        else:
            logger.warning("Designer не знайдено. EPF компіляція недоступна.")
            self.ib_manager = None
            self.installed_platform_version = None

        # Ініціалізуємо XML converter
        self.xml_converter = XMLConverter()

        # Ініціалізуємо парсер логів Designer (v2.38.0+)
        self.log_parser = DesignerLogParser()

        # Зберігаємо посилання на останню temp_ib для тестів (v2.16.0+)
        self.last_temp_ib: Optional[Path] = None

    def _extract_platform_version(self, designer_path: Path) -> Optional[str]:
        """
        v2.62.7: Витягує версію платформи з шляху до Designer.

        Шлях до Designer має формат:
        - C:\\Program Files\\1cv8\\8.3.25.1394\\bin\\1cv8.exe
        - C:\\Program Files\\BAF\\8.3.25.1394\\bin\\1cv8.exe

        Args:
            designer_path: Шлях до 1cv8.exe

        Returns:
            Версія платформи (наприклад "8.3.25.1394") або None
        """
        import re

        # Шукаємо версію в шляху: 8.3.XX.YYYY
        path_str = str(designer_path)
        match = re.search(r'(8\.3\.\d+\.\d+)', path_str)

        if match:
            return match.group(1)

        logger.warning(f"Не вдалося витягнути версію платформи з шляху: {path_str}")
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

    def compile_epf(
        self,
        xml_root: Path,
        output_epf: Path,
        timeout: int = 120,
    ) -> bool:
        """
        Компіляція XML процесора в EPF формат через Designer.

        Швидкий режим - для простих процесорів без CatalogRef/DocumentRef.
        Використовує тимчасову або persistent IB для компіляції.

        Args:
            xml_root: Шлях до головного XML файлу процесора (ProcessorName.xml)
            output_epf: Шлях до вихідного EPF файлу
            timeout: Таймаут виконання в секундах (за замовчуванням 120)

        Returns:
            True якщо компіляція успішна, False якщо помилка

        Raises:
            FileNotFoundError: Якщо xml_root не існує
        """
        if not self.designer_path:
            logger.error("Designer не знайдено. Неможливо скомпілювати EPF.")
            return False

        if not xml_root.exists():
            logger.error(f"XML файл не знайдено: {xml_root}")
            raise FileNotFoundError(f"XML файл не знайдено: {xml_root}")

        logger.info(f"Компіляція EPF: {xml_root} → {output_epf}")

        # Визначаємо яку інфобазу використовувати
        temp_ib = self._get_infobase(timeout)
        if not temp_ib:
            return False

        # Завантажуємо EPF через Designer
        return self._load_epf_to_ib(temp_ib, xml_root, output_epf, timeout)

    def compile_epf_with_configuration(
        self,
        processor_xml_dir: Path,
        output_epf: Path,
        processor,  # Processor об'єкт з models.py
        requirements,  # MetadataRequirements з metadata_analyzer.py
        timeout: int = 180,
        ignore_validation_errors: bool = False,
    ) -> bool:
        """
        Компіляція EPF з підтримкою метаданих (CatalogRef/DocumentRef).

        Configuration mode - для процесорів, які містять CatalogRef або DocumentRef типи.
        Автоматично генерує мінімальну Configuration.xml з необхідними довідниками/документами.

        Args:
            processor_xml_dir: Директорія з згенерованим ProcessorName/ XML
            output_epf: Шлях до вихідного EPF файлу
            processor: Processor об'єкт з models.py
            requirements: MetadataRequirements з metadata_analyzer.py
            timeout: Таймаут виконання в секундах (за замовчуванням 180)
            ignore_validation_errors: Ігнорувати помилки валідації BSL (за замовчуванням False)

        Returns:
            True якщо компіляція успішна, False якщо помилка

        Note:
            Використовує 6.5-крокову процедуру з валідацією BSL:
            1. Генерація Configuration.xml (тільки метадані)
            2. Підготовка інфобази
            3. Завантаження Configuration в БД
            4. Оновлення БД (створення таблиць)
            4.5. Валідація BSL модулів через /CheckModules ⭐
            5. Підготовка ExternalDataProcessor з cfg: префіксами
            6. Завантаження EPF
        """
        if not self.designer_path:
            logger.error("Designer не знайдено. Неможливо скомпілювати EPF.")
            return False

        # Створюємо контекст компіляції
        context = CompilationContext(
            processor_xml_dir=processor_xml_dir,
            output_epf=output_epf,
            processor=processor,
            requirements=requirements,
            timeout=timeout
        )

        self._print_compilation_header(context)

        # Виконуємо 6.5 кроків компіляції з валідацією
        try:
            return self._execute_configuration_compilation(context, ignore_validation_errors)
        except Exception as e:
            logger.error(f"✗ Помилка компіляції з Configuration: {e}")
            return False

    def decompile_epf(
        self,
        epf_path: Path,
        output_dir: Path,
        timeout: int = 120,
    ) -> bool:
        """
        Декомпіляція EPF назад в XML формат через Designer.

        Зворотня операція до compile_epf(). Розпаковує бінарний EPF файл
        в XML структуру для подальшого редагування або регенерації.

        Args:
            epf_path: Шлях до EPF файлу для декомпіляції
            output_dir: Директорія для XML файлів (буде створена якщо не існує)
            timeout: Таймаут виконання в секундах (за замовчуванням 120)

        Returns:
            True якщо декомпіляція успішна, False якщо помилка

        Raises:
            FileNotFoundError: Якщо epf_path не існує
        """
        if not self.designer_path:
            logger.error("Designer не знайдено. Неможливо декомпілювати EPF.")
            return False

        if not epf_path.exists():
            logger.error(f"EPF файл не знайдено: {epf_path}")
            raise FileNotFoundError(f"EPF файл не знайдено: {epf_path}")

        logger.info(f"Декомпіляція EPF: {epf_path} → {output_dir}")

        # Створюємо вихідну директорію
        output_dir.mkdir(parents=True, exist_ok=True)

        # Отримуємо інфобазу
        temp_ib = self._get_infobase(timeout)
        if not temp_ib:
            return False

        # Декомпіляція EPF через Designer
        dump_command = [
            str(self.designer_path),
            "DESIGNER",
            f"/F{temp_ib}",
            *DESIGNER_SILENT_PARAMS,
            DESIGNER_DUMP_EPF_COMMAND,
            str(output_dir.absolute()),  # куди вигружати
            str(epf_path.absolute()),    # що вигружати
        ]

        logger.debug(f"Декомпіляція: {' '.join(dump_command)}")

        try:
            result = subprocess.run(
                dump_command,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )

            if result.stdout:
                logger.debug(f"Designer stdout:\n{result.stdout}")
            if result.stderr:
                logger.warning(f"Designer stderr:\n{result.stderr}")

            # Перевіряємо чи створено XML файли
            xml_files = list(output_dir.glob("*.xml"))
            if xml_files:
                logger.info(f"✓ XML створено: {output_dir} ({len(xml_files)} файлів)")
                return True
            else:
                logger.error(f"✗ XML файли не створено в: {output_dir}")
                logger.error(f"Designer return code: {result.returncode}")
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"✗ Таймаут декомпіляції ({timeout}s перевищено)")
            return False
        except Exception as e:
            logger.error(f"✗ Помилка декомпіляції: {e}")
            return False

    # ========================================================================
    # Private helper methods
    # ========================================================================

    def _create_obfuscated_log(self, parent: Path, extension: str = ".tmp", readable_name: str = "") -> Path:
        """
        Creates an obfuscated log file path.

        v2.52.0: Know-how protection - random file names instead of readable.
        In DEBUG_MODE: uses readable names for easier debugging.

        Args:
            parent: Parent directory for the log file
            extension: File extension (default .tmp)
            readable_name: Readable name suffix for debug mode (e.g., "designer_out")

        Returns:
            Path to obfuscated log file (e.g., ".a7f3b2c1.tmp" or "debug_designer_out.log")
        """
        if DEBUG_MODE and readable_name:
            return parent / f"debug_{readable_name}.log"
        return parent / f".{secrets.token_hex(4)}{extension}"

    def _cleanup_log(self, log_file: Path) -> None:
        """
        Deletes a log file after use.

        v2.52.0: Know-how protection - immediate cleanup of Designer logs.
        In DEBUG_MODE: logs are kept for debugging.

        Args:
            log_file: Path to log file to delete
        """
        if DEBUG_MODE:
            logger.debug(f"DEBUG_MODE: keeping log file {log_file.name}")
            return

        try:
            if log_file and log_file.exists():
                log_file.unlink(missing_ok=True)
                logger.debug(f"Cleanup: {log_file.name}")
        except Exception:
            pass  # Ignore cleanup errors

    def _get_infobase(self, timeout: int) -> Optional[Path]:
        """
        Отримує інфобазу для компіляції (persistent або тимчасову).

        Args:
            timeout: Таймаут для створення БД

        Returns:
            Path до інфобази або None якщо помилка
        """
        if self.use_persistent_ib and self.ib_manager:
            temp_ib = self.ib_manager.get_or_create(timeout=timeout // 2)
            if temp_ib:
                logger.debug(f"Використання persistent IB: {temp_ib}")
                return temp_ib
            else:
                logger.warning("⚠️ Помилка persistent IB, використовую тимчасову")

        # Fallback: створюємо тимчасову інфобазу
        # v2.52.0: Obfuscated directory name for know-how protection
        # In DEBUG_MODE: use readable name for easier debugging
        dir_name = "debug_temp_ib" if DEBUG_MODE else secrets.token_hex(8)
        temp_ib = Path(tempfile.mkdtemp()) / dir_name
        logger.debug(f"Тимчасова інфобаза: {temp_ib}")

        if not self._create_temp_infobase(temp_ib, timeout // 2):
            return None

        return temp_ib

    def _create_temp_infobase(self, temp_ib: Path, timeout: int) -> bool:
        """Створює тимчасову інфобазу."""
        create_ib_command = [
            str(self.designer_path),
            "CREATEINFOBASE",
            f"File={temp_ib}",
        ]

        logger.debug(f"Створення інфобази: {' '.join(create_ib_command)}")

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
                logger.error(f"✗ Помилка створення тимчасової інфобази (код {result.returncode})")
                if result.stderr:
                    logger.error(f"Помилка: {result.stderr}")
                    # v2.70.1: Detect Windows Defender blocking
                    if _is_windows_defender_block(result.stderr):
                        _show_windows_defender_help()
                return False

            return True

        except subprocess.TimeoutExpired:
            logger.error(f"✗ Таймаут створення інфобази ({timeout}s)")
            return False
        except Exception as e:
            logger.error(f"✗ Помилка створення інфобази: {e}")
            return False

    def _load_epf_to_ib(
        self,
        temp_ib: Path,
        xml_root: Path,
        output_epf: Path,
        timeout: int,
        save_logs: bool = True,
    ) -> bool:
        """
        Завантажує EPF з XML в існуючу інфобазу.

        Args:
            temp_ib: Шлях до інфобази (persistent або тимчасова)
            xml_root: Шлях до XML файлу процесора
            output_epf: Шлях до вихідного EPF
            timeout: Таймаут виконання
            save_logs: Зберігати логи Designer при помилках

        Returns:
            True якщо успішно, False якщо помилка
        """
        # Створюємо лог-файл для Designer (v2.52.0: obfuscated)
        designer_log_file = self._create_obfuscated_log(
            output_epf.parent, readable_name="designer_out"
        )

        # Завантажуємо EPF через Designer
        load_epf_command = [
            str(self.designer_path),
            "DESIGNER",
            f"/F{temp_ib}",
            f"/Out{designer_log_file}",
            *DESIGNER_SILENT_PARAMS,
            DESIGNER_LOAD_EPF_COMMAND,
            str(xml_root.absolute()),
            str(output_epf.absolute()),
        ]

        logger.debug(f"Завантаження EPF: {' '.join(load_epf_command)}")
        logger.info(f"Designer лог: {designer_log_file}")

        try:
            result = subprocess.run(
                load_epf_command,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )

            # Читаємо лог файл Designer
            designer_log_content = self._read_designer_log(designer_log_file)
            # v2.52.0: Cleanup log immediately after reading
            self._cleanup_log(designer_log_file)

            # Логуємо вихід Designer
            if result.stdout:
                logger.debug(f"Designer stdout:\n{result.stdout}")
            if result.stderr:
                logger.warning(f"Designer stderr:\n{result.stderr}")

            # Перевіряємо чи створено EPF файл
            if output_epf.exists():
                file_size = output_epf.stat().st_size
                logger.info(f"✓ EPF створено: {output_epf} ({file_size} bytes)")
                return True
            else:
                logger.error(f"✗ EPF файл не створено: {output_epf}")
                logger.error(f"Designer return code: {result.returncode}")

                if designer_log_content:
                    logger.error(f"Designer /Out log:\n{designer_log_content}")

                if save_logs:
                    self._save_designer_logs(
                        output_epf, load_epf_command, result.returncode,
                        result.stdout, result.stderr, designer_log_content
                    )

                return False

        except subprocess.TimeoutExpired as e:
            logger.error(f"✗ Таймаут завантаження EPF ({timeout}s перевищено)")

            if save_logs:
                self._save_designer_logs(
                    output_epf, load_epf_command, -1,
                    f"TIMEOUT: Процес перевищив {timeout}s", str(e)
                )

            return False

        except Exception as e:
            logger.error(f"✗ Помилка завантаження EPF: {e}")

            if save_logs:
                self._save_designer_logs(
                    output_epf, load_epf_command, -2,
                    "", f"EXCEPTION: {type(e).__name__}: {e}"
                )

            return False

    def _read_designer_log(self, log_file: Path) -> str:
        """Читає лог файл Designer."""
        if not log_file.exists():
            return ""

        try:
            with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            logger.debug(f"Designer /Out log:\n{content}")
            return content
        except Exception as e:
            logger.warning(f"Не вдалося прочитати лог Designer: {e}")
            return ""

    def _ensure_conf_cfg_configured(self) -> None:
        """Auto-configure conf.cfg for EPF compilation (v2.56.0+)."""
        try:
            from .conf_cfg_manager import ConfCfgManager

            manager = ConfCfgManager()
            is_ok, _ = manager.check_configuration()

            if not is_ok:
                if manager.configure():
                    logger.debug("conf.cfg auto-configured")
        except Exception:
            pass  # Silent fail - will show error at compilation time if needed

    def _save_designer_logs(
        self,
        output_epf: Path,
        command: list,
        returncode: int,
        stdout: str,
        stderr: str,
        designer_out_log: str = ""
    ):
        """Зберігає логи Designer при помилках компіляції.

        В DEBUG_MODE - повні логи з командою.
        В production - тільки повідомлення про помилку (без команди).
        """
        # v2.53.0: In production, don't save logs with sensitive commands
        if not DEBUG_MODE:
            # Only log error message, not full debug info
            logger.error(
                f"Compilation failed (code {returncode}). "
                f"Enable DEBUG_MODE for detailed logs."
            )
            return

        # DEBUG_MODE: save full logs for development
        log_file = output_epf.parent / f"{output_epf.stem}_debug.log"

        try:
            import datetime

            with open(log_file, "w", encoding="utf-8") as f:
                f.write("=" * 80 + "\n")
                f.write("DEBUG COMPILATION LOG\n")
                f.write("=" * 80 + "\n\n")

                f.write(f"Time: {datetime.datetime.now().isoformat()}\n\n")

                f.write("Command:\n")
                f.write(f"{' '.join(command)}\n\n")

                f.write(f"Return Code: {returncode}\n\n")

                f.write("=" * 80 + "\n")
                f.write("PLATFORM OUTPUT:\n")
                f.write("=" * 80 + "\n")
                f.write(designer_out_log if designer_out_log else "(empty or not available)\n")
                f.write("\n")

                f.write("=" * 80 + "\n")
                f.write("STDOUT:\n")
                f.write("=" * 80 + "\n")
                f.write(stdout if stdout else "(empty)\n")
                f.write("\n")

                f.write("=" * 80 + "\n")
                f.write("STDERR:\n")
                f.write("=" * 80 + "\n")
                f.write(stderr if stderr else "(empty)\n")

            logger.info(f"[DEBUG] Logs saved: {log_file}")

        except Exception as e:
            logger.warning(f"Could not save debug logs: {e}")

    # ========================================================================
    # Configuration compilation methods (6 steps with validation)
    # ========================================================================

    def _execute_configuration_compilation(
        self,
        context: CompilationContext,
        ignore_validation_errors: bool = False
    ) -> bool:
        """
        Виконує компіляцію EPF з Configuration (6 кроків з валідацією).

        Steps:
        1. Generate Configuration (metadata + DataProcessor_Validation)
        2. Prepare InfoBase
        3. Load Configuration to DB
        4. Update DB (create tables for catalogs/documents)
        4.5. Validate BSL modules (/CheckModules on DataProcessor_Validation)
        5. Prepare ExternalDataProcessor (original name + cfg: prefixes)
        6. Load EPF (original name as External)

        Args:
            context: Контекст компіляції
            ignore_validation_errors: Ігнорувати помилки валідації BSL (за замовчуванням False)

        Returns:
            True якщо успішно, False якщо помилка
        """
        # Імпортуємо ConfigurationGenerator динамічно
        try:
            # When running as compiled .pyd
            from config_generator_impl import ConfigurationGenerator
        except ImportError:
            # When running as part of package
            from .config_generator_impl import ConfigurationGenerator

        # Step 1: Генерація Configuration (метадані + DataProcessor для валідації)
        logger.info("⚙️ Step 1/6: Generating Configuration (metadata + DataProcessor for validation)...")
        # v2.62.7: Передаємо версію встановленої платформи для CompatibilityMode
        config_gen = ConfigurationGenerator(
            context.processor,
            context.requirements,
            installed_platform_version=self.installed_platform_version
        )

        with tempfile.TemporaryDirectory() as temp_config_dir:
            temp_config_path = Path(temp_config_dir)

            # Визначаємо чи є метадані
            has_metadata = context.requirements.has_metadata()

            # ЗАВЖДИ включаємо DataProcessor в Configuration для валідації
            # Суфікс "_Validation" щоб уникнути конфлікту з ExternalDataProcessor
            config_dir = config_gen.generate_configuration(
                temp_config_path,
                context.processor_xml_dir,
                include_processor=True,  # Завжди включаємо для валідації BSL
                processor_suffix="_Validation"
            )

            logger.info(f"✓ Configuration generated: {config_dir}")

            # Step 2: Підготовка інфобази
            temp_ib = self._step2_prepare_infobase(context)
            if not temp_ib:
                return False

            # Зберігаємо temp_ib для можливого використання в тестах (v2.16.0+)
            self.last_temp_ib = temp_ib

            # Step 3: Завантаження Configuration
            if not self._step3_load_configuration(temp_ib, config_dir, context):
                return False

            # Step 4: Оновлення БД
            if not self._step4_update_database(temp_ib, context):
                return False

            # ✨ Step 4.5: Валідація BSL модулів через /CheckModules
            if not self._step4_5_check_modules(temp_ib, context, ignore_validation_errors):
                return False

            # ✨ Step 4.6: Семантична перевірка через /CheckConfig (v2.12.0+)
            if not self._step4_6_check_config(temp_ib, context, ignore_validation_errors):
                return False

            # Якщо є метадані - продовжуємо з Configuration mode
            # Якщо немає метаданих - після валідації використовуємо чисту базу
            if has_metadata:
                # Step 5: Підготовка ExternalDataProcessor з cfg: префіксами
                external_xml = self._step5_prepare_external_processor(context)
                if not external_xml:
                    return False

                # Step 6: Завантаження EPF через Configuration
                success = self._step6_load_epf(temp_ib, external_xml, context)
            else:
                # Немає метаданих - валідація пройшла успішно
                # Використовуємо ЧИСТУ базу для фінального EPF (без Configuration)
                logger.info("\n✅ Validation completed successfully (no metadata)")
                logger.info("⚙️ Step 5-6/6: Compiling EPF with clean database...")

                # Створюємо НОВУ чисту інфобазу (не persistent, без Configuration)
                # v2.52.0: Obfuscated directory name for know-how protection
                # In DEBUG_MODE: use readable name for easier debugging
                dir_name = "debug_clean_ib" if DEBUG_MODE else secrets.token_hex(8)
                clean_ib = Path(tempfile.mkdtemp()) / dir_name
                logger.info(f"✓ Clean infobase created: {clean_ib}")

                # Завантажуємо EPF з оригінальних файлів (без cfg: префіксів)
                xml_root = context.processor_xml_dir / context.processor.name / f"{context.processor.name}.xml"
                success = self._load_epf_to_ib(
                    clean_ib,
                    xml_root,
                    context.output_epf,
                    context.timeout // 3
                )

            if success:
                logger.info(f"\n{'='*60}")
                logger.info("✓ EPF Compilation with Configuration - SUCCESS")
                logger.info(f"{'='*60}\n")
            else:
                logger.error(f"\n{'='*60}")
                logger.error("✗ EPF Compilation with Configuration - FAILED")
                logger.error(f"{'='*60}\n")

            return success

    def _step2_prepare_infobase(self, context: CompilationContext) -> Optional[Path]:
        """Step 2: Підготовка інфобази."""
        logger.info("\n⚙️ Step 2/6: Preparing infobase...")

        temp_ib = self._get_infobase(context.timeout)

        if temp_ib:
            if self.use_persistent_ib and self.ib_manager and self.ib_manager.exists():
                logger.info(f"✓ Using persistent IB: {temp_ib}")
            else:
                logger.info(f"✓ Infobase created: {temp_ib}")

        return temp_ib

    def _step3_load_configuration(
        self,
        temp_ib: Path,
        config_dir: Path,
        context: CompilationContext
    ) -> bool:
        """Step 3: Завантаження Configuration в БД."""
        logger.info("\n⚙️ Step 3/6: Loading Configuration to DB...")

        # v2.52.0: Obfuscated log file name
        load_config_log = self._create_obfuscated_log(
            context.output_epf.parent, readable_name="load_config"
        )

        load_config_command = [
            str(self.designer_path),
            "DESIGNER",
            f"/F{temp_ib}",
            f"/Out{load_config_log}",
            *DESIGNER_SILENT_PARAMS,
            "/LoadConfigFromFiles",
            str(config_dir.absolute()),
        ]

        logger.debug(f"Command: {' '.join(load_config_command)}")

        try:
            result = subprocess.run(
                load_config_command,
                capture_output=True,
                text=True,
                timeout=context.timeout // 3,
                encoding="utf-8",
                errors="replace",
            )

            if result.returncode != 0:
                logger.error(f"✗ Failed to load Configuration (code {result.returncode})")
                if load_config_log.exists():
                    with open(load_config_log, "r", encoding="utf-8", errors="replace") as f:
                        logger.error(f"Designer log:\n{f.read()}")
                # v2.52.0: Cleanup log after reading
                self._cleanup_log(load_config_log)
                return False

            # v2.52.0: Cleanup log on success
            self._cleanup_log(load_config_log)
            logger.info("✓ Configuration loaded to DB")
            return True

        except subprocess.TimeoutExpired:
            logger.error("✗ Timeout loading Configuration")
            self._cleanup_log(load_config_log)
            return False
        except Exception as e:
            logger.error(f"✗ Error loading Configuration: {e}")
            self._cleanup_log(load_config_log)
            return False

    def _step4_update_database(self, temp_ib: Path, context: CompilationContext) -> bool:
        """Step 4: Оновлення БД (створення таблиць)."""
        logger.info("\n⚙️ Step 4/6: Updating DB (creating catalog/document tables)...")

        # v2.52.0: Obfuscated log file name
        update_db_log = self._create_obfuscated_log(
            context.output_epf.parent, readable_name="update_db"
        )

        update_db_command = [
            str(self.designer_path),
            "DESIGNER",
            f"/F{temp_ib}",
            f"/Out{update_db_log}",
            *DESIGNER_SILENT_PARAMS,
            "/UpdateDBCfg",
        ]

        logger.debug(f"Command: {' '.join(update_db_command)}")

        try:
            result = subprocess.run(
                update_db_command,
                capture_output=True,
                text=True,
                timeout=context.timeout // 3,
                encoding="utf-8",
                errors="replace",
            )

            if result.returncode != 0:
                logger.error(f"✗ Failed to update DB (code {result.returncode})")
                if update_db_log.exists():
                    with open(update_db_log, "r", encoding="utf-8", errors="replace") as f:
                        logger.error(f"Designer log:\n{f.read()}")
                # v2.52.0: Cleanup log after reading
                self._cleanup_log(update_db_log)
                return False

            # v2.52.0: Cleanup log on success
            self._cleanup_log(update_db_log)
            logger.info("✓ DB updated (catalog/document tables created)")
            return True

        except subprocess.TimeoutExpired:
            logger.error("✗ Timeout updating DB")
            self._cleanup_log(update_db_log)
            return False
        except Exception as e:
            logger.error(f"✗ Error updating DB: {e}")
            self._cleanup_log(update_db_log)
            return False

    def _step4_5_check_modules(
        self,
        temp_ib: Path,
        context: CompilationContext,
        ignore_errors: bool = False
    ) -> bool:
        """
        Step 4.5: Перевірка BSL модулів через /CheckModules.

        Configuration містить DataProcessor з суфіксом _Validation для перевірки.
        Після валідації EPF буде згенеровано з оригінальною назвою як External.

        Args:
            temp_ib: Інфобаза з завантаженою Configuration і DataProcessor_Validation
            context: Контекст компіляції
            ignore_errors: True = warnings only, False = critical errors (за замовчуванням)

        Returns:
            True якщо валідація пройшла або ignore_errors=True
            False якщо критичні помилки і ignore_errors=False
        """
        logger.info("\n⚙️ Step 4.5/6: Checking BSL modules syntax...")

        # v2.52.0: Obfuscated log file names
        check_log = self._create_obfuscated_log(
            context.output_epf.parent, readable_name="check_modules"
        )
        check_result = self._create_obfuscated_log(
            context.output_epf.parent, readable_name="check_modules_result"
        )

        # Команда /CheckModules
        check_command = [
            str(self.designer_path),
            "DESIGNER",
            f"/F{temp_ib}",
            f"/Out{check_log}",
            *DESIGNER_SILENT_PARAMS,
            DESIGNER_CHECK_MODULES_COMMAND,
            *CHECK_MODULES_PARAMS,
            f"/DumpResult{check_result}"
        ]

        logger.debug(f"Command: {' '.join(check_command)}")

        try:
            result = subprocess.run(
                check_command,
                capture_output=True,
                text=True,
                timeout=context.timeout // 3,
                encoding="utf-8",
                errors="replace"
            )

            # Парсинг результатів через DesignerLogParser (v2.38.0+)
            errors, warnings = self.log_parser.parse_check_modules_log(check_log, check_result)
            # v2.52.0: Cleanup logs immediately after parsing
            self._cleanup_log(check_log)
            self._cleanup_log(check_result)

            if errors:
                error_msg = f"✗ BSL validation failed: {len(errors)} errors"
                logger.error(error_msg)

                # Виводимо перші 10 помилок через форматер
                logger.error(self.log_parser.format_errors(errors, max_count=10))

                if ignore_errors:
                    logger.warning("⚠️ Continuing despite validation errors (--ignore-validation-errors)")
                    return True
                else:
                    logger.error("💡 Use --ignore-validation-errors to force compilation")
                    return False

            if warnings:
                logger.warning(f"⚠️ BSL validation warnings: {len(warnings)}")
                for i, warning in enumerate(warnings[:5], 1):
                    logger.warning(f"  {i}. {warning.message}")

            logger.info("✓ BSL modules validation passed")
            return True

        except subprocess.TimeoutExpired:
            logger.error(f"✗ Timeout checking modules ({context.timeout // 3}s)")
            self._cleanup_log(check_log)
            self._cleanup_log(check_result)
            return False if not ignore_errors else True
        except Exception as e:
            logger.error(f"✗ Error checking modules: {e}")
            self._cleanup_log(check_log)
            self._cleanup_log(check_result)
            return False if not ignore_errors else True

    def _step4_6_check_config(
        self,
        temp_ib: Path,
        context: CompilationContext,
        ignore_errors: bool = False
    ) -> bool:
        """
        Step 4.6: Семантична перевірка через /CheckConfig (v2.12.0+).

        Глибша перевірка конфігурації з DataProcessor_Validation:
        - Некоректні посилання на видалені об'єкти/форми
        - Існування назначених обробників
        - Пусті обробники (знижують продуктивність)
        - Невикористовувані процедури/функції
        - Розширена перевірка типів через точку

        Args:
            temp_ib: Інфобаза з завантаженою Configuration і DataProcessor_Validation
            context: Контекст компіляції
            ignore_errors: True = warnings only, False = critical errors (за замовчуванням)

        Returns:
            True якщо валідація пройшла або ignore_errors=True або check_config_enabled=False
            False якщо критичні помилки і ignore_errors=False
        """
        # Перевіряємо чи увімкнена CheckConfig
        if not context.processor.validation.check_config_enabled:
            logger.info("\n⏭️ Step 4.6/6: CheckConfig disabled, skipping semantic checks...")
            return True

        logger.info("\n⚙️ Step 4.6/6: Running semantic checks (/CheckConfig)...")

        # v2.52.0: Obfuscated log file names
        check_log = self._create_obfuscated_log(
            context.output_epf.parent, readable_name="check_config"
        )
        check_result = self._create_obfuscated_log(
            context.output_epf.parent, readable_name="check_config_result"
        )

        # Збираємо параметри на основі ValidationConfig
        params = self._build_check_config_params(context.processor.validation)

        # Команда /CheckConfig
        check_command = [
            str(self.designer_path),
            "DESIGNER",
            f"/F{temp_ib}",
            f"/Out{check_log}",
            *DESIGNER_SILENT_PARAMS,
            DESIGNER_CHECK_CONFIG_COMMAND,
            *params,
            f"/DumpResult{check_result}"
        ]

        logger.debug(f"Command: {' '.join(check_command)}")

        try:
            result = subprocess.run(
                check_command,
                capture_output=True,
                text=True,
                timeout=context.timeout // 3,
                encoding="utf-8",
                errors="replace"
            )

            # Парсинг результатів через DesignerLogParser (v2.38.0+)
            errors, warnings = self.log_parser.parse_check_modules_log(check_log, check_result)
            # v2.52.0: Cleanup logs immediately after parsing
            self._cleanup_log(check_log)
            self._cleanup_log(check_result)

            if errors:
                error_msg = f"✗ Semantic validation failed (/CheckConfig): {len(errors)} errors"
                logger.error(error_msg)

                # Виводимо перші 10 помилок через форматер
                logger.error(self.log_parser.format_errors(errors, max_count=10))

                if ignore_errors:
                    logger.warning("⚠️ Continuing despite semantic errors (--ignore-validation-errors)")
                    return True
                else:
                    logger.error("💡 Use --ignore-validation-errors to force compilation")
                    return False

            if warnings:
                logger.warning(f"⚠️ Semantic validation warnings: {len(warnings)}")
                for i, warning in enumerate(warnings[:5], 1):
                    logger.warning(f"  {i}. {warning.message}")

            logger.info("✓ Semantic validation passed (/CheckConfig)")
            return True

        except subprocess.TimeoutExpired:
            logger.error(f"✗ Timeout checking config ({context.timeout // 3}s)")
            self._cleanup_log(check_log)
            self._cleanup_log(check_result)
            return False if not ignore_errors else True
        except Exception as e:
            logger.error(f"✗ Error checking config: {e}")
            self._cleanup_log(check_log)
            self._cleanup_log(check_result)
            return False if not ignore_errors else True

    def _build_check_config_params(self, validation_config) -> list:
        """
        Збирає параметри для /CheckConfig на основі ValidationConfig.

        Args:
            validation_config: ValidationConfig з Processor

        Returns:
            Список параметрів для Designer /CheckConfig

        Example:
            >>> params = compiler._build_check_config_params(processor.validation)
            >>> # ['-ThinClient', '-Server', '-IncorrectReferences', '-HandlersExistence']
        """
        params = []

        # Базові параметри режимів клієнта (завжди включені для /CheckConfig)
        params.extend(CHECK_CONFIG_BASE_PARAMS)

        # Додаємо опціональні семантичні перевірки на основі ValidationConfig
        for check_name, param_flag in CHECK_CONFIG_SEMANTIC_CHECKS.items():
            if getattr(validation_config, check_name, False):
                params.append(param_flag)

        logger.debug(f"CheckConfig params: {' '.join(params)}")
        return params

    def _step5_prepare_external_processor(self, context: CompilationContext) -> Optional[Path]:
        """
        Step 5: Підготовка ExternalDataProcessor з cfg: префіксами (якщо є метадані).

        Якщо є метадані (CatalogRef/DocumentRef) → додаємо cfg: префікси
        Якщо метаданих немає (тільки validation) → використовуємо оригінальні файли
        """
        # Знаходимо оригінальний ExternalDataProcessor XML
        original_processor_xml = context.processor_xml_dir / context.processor.name / f"{context.processor.name}.xml"

        if not original_processor_xml.exists():
            logger.error(f"✗ Original processor XML not found: {original_processor_xml}")
            return None

        # Перевіряємо чи потрібні cfg: префікси (тільки якщо є метадані)
        has_metadata = context.requirements.has_metadata()

        if has_metadata:
            logger.info("\n⚙️ Step 5/6: Preparing ExternalDataProcessor with cfg: prefixes...")

            # Створюємо тимчасову копію з cfg: префіксами
            # v2.52.0: Obfuscated directory name for know-how protection
            # In DEBUG_MODE: use readable name for easier debugging
            dir_name = f"debug_{context.processor.name}" if DEBUG_MODE else secrets.token_hex(8)
            external_processor_temp = Path(tempfile.mkdtemp()) / dir_name
            shutil.copytree(
                context.processor_xml_dir / context.processor.name,
                external_processor_temp,
                dirs_exist_ok=True
            )

            # Додаємо cfg: префікси до всіх XML файлів
            modified_count = self.xml_converter.add_cfg_prefix(external_processor_temp)

            logger.info(f"✓ ExternalDataProcessor prepared ({modified_count} files modified)")

            external_xml = external_processor_temp / f"{context.processor.name}.xml"
        else:
            # Немає метаданих - використовуємо оригінальні файли без cfg: префіксів
            logger.info("\n⚙️ Step 5/6: Using original ExternalDataProcessor (no metadata, cfg: prefixes not needed)...")
            external_xml = original_processor_xml
            logger.info(f"✓ ExternalDataProcessor ready: {external_xml}")

        return external_xml

    def _step6_load_epf(
        self,
        temp_ib: Path,
        external_xml: Path,
        context: CompilationContext
    ) -> bool:
        """Step 6: Завантаження EPF (з cfg: префіксами)."""
        logger.info("\n⚙️ Step 6/6: Loading EPF with cfg: prefixes...")
        logger.info(f"Processor XML: {external_xml}")

        return self._load_epf_to_ib(
            temp_ib,
            external_xml,
            context.output_epf,
            context.timeout // 3
        )

    def _parse_check_modules_log(
        self,
        log_file: Path,
        result_file: Optional[Path] = None
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Парсить вивід /CheckModules і повертає списки помилок та попереджень.

        .. deprecated:: 2.38.0
            Використовуйте self.log_parser.parse_check_modules_log() напряму.
            Цей метод збережено для зворотної сумісності.

        Args:
            log_file: Шлях до лог файлу Designer (/Out)
            result_file: Шлях до файлу результату (/DumpResult) - опціонально

        Returns:
            (errors, warnings) - списки словників з детальною інформацією

        Формат помилок:
            {
                'line': 45,
                'column': 12,
                'message': 'Неизвестный метод "НесуществующийМетод"',
                'module': 'Модуль объекта обработки "ProcessorName"'
            }
        """
        # Делегуємо до DesignerLogParser (v2.38.0+)
        errors, warnings = self.log_parser.parse_check_modules_log(log_file, result_file)

        # Конвертуємо ValidationError у dict для зворотної сумісності
        return (
            self.log_parser.to_dict_list(errors),
            self.log_parser.to_dict_list(warnings)
        )

    def _print_compilation_header(self, context: CompilationContext):
        """Виводить заголовок компіляції."""
        logger.info(f"\n{'='*60}")
        logger.info("EPF Compilation with Configuration Mode")
        logger.info(f"{'='*60}")
        logger.info(f"Processor: {context.processor.name}")
        logger.info(f"Catalogs: {len(context.requirements.catalogs)}")
        logger.info(f"Documents: {len(context.requirements.documents)}")
        logger.info(f"Output: {context.output_epf}")
        logger.info(f"{'='*60}\n")
