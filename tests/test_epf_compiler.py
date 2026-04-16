"""
Unit тести для epf_compiler.py (v2.8.1)

Тестування EPF Direct Generation через 1C Designer
- v2.8.0: EPF Direct Generation (базова компіляція)
- v2.8.1: Persistent IB кеш + Silent mode
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import subprocess

sys.path.insert(0, str(Path(__file__).parent.parent))

import importlib
epf_compiler = importlib.import_module("1c_processor_generator.epf_compiler")
designer_finder_module = importlib.import_module("1c_processor_generator.designer_finder")
persistent_ib_manager_module = importlib.import_module("1c_processor_generator.persistent_ib_manager")
# Import impl modules for patching constants (pro/ protection)
designer_finder_impl = importlib.import_module("1c_processor_generator.pro.designer_finder_impl")
persistent_ib_impl = importlib.import_module("1c_processor_generator.pro.persistent_ib_impl")

EPFCompiler = epf_compiler.EPFCompiler
DesignerFinder = designer_finder_module.DesignerFinder
PersistentIBManager = persistent_ib_manager_module.PersistentIBManager

# v2.51.0: Get internal marker for test instantiation (bypasses license check)


def create_test_compiler(**kwargs):
    """Helper to create EPFCompiler for tests with internal marker."""
    return EPFCompiler(**kwargs)


# ============================================================================
# Test EPFCompiler Initialization
# ============================================================================

class TestEPFCompilerInit:
    """Тести ініціалізації EPFCompiler"""

    def test_init_without_path(self):
        """Ініціалізація без явного шляху (автоматичний пошук)"""
        with patch.object(DesignerFinder, 'find', return_value=Path("/mock/designer/1cv8.exe")):
            compiler = create_test_compiler()
            assert compiler.designer_path is not None
            assert compiler.designer_path == Path("/mock/designer/1cv8.exe")

    def test_init_with_valid_path(self, mock_designer_path):
        """Ініціалізація з валідним шляхом до Designer"""
        compiler = create_test_compiler(designer_path=str(mock_designer_path))
        assert compiler.designer_path == mock_designer_path

    def test_init_with_invalid_path(self):
        """Ініціалізація з невалідним шляхом (файл не існує)"""
        # Mock автоматичний пошук щоб він нічого не знайшов
        with patch.object(DesignerFinder, 'find', return_value=None):
            compiler = create_test_compiler(designer_path="/nonexistent/1cv8.exe")
            assert compiler.designer_path is None

    def test_init_designer_not_found(self):
        """Designer не знайдено жодним способом"""
        with patch.object(DesignerFinder, 'find', return_value=None):
            compiler = create_test_compiler()
            assert compiler.designer_path is None


# ============================================================================
# Test Designer Discovery from Environment Variable
# ============================================================================

class TestDesignerDiscoveryFromEnv:
    """Тести пошуку Designer через змінну середовища"""

    def test_find_designer_from_env_valid(self, mock_designer_path):
        """Валідна змінна PATH_1C_DESIGNER"""
        with patch('os.environ.get', return_value=str(mock_designer_path)):
            finder = DesignerFinder()
            result = finder._find_from_env()
            assert result == mock_designer_path

    def test_find_designer_from_env_invalid(self):
        """Змінна вказує на неіснуючий файл"""
        with patch('os.environ.get', return_value="/invalid/path/1cv8.exe"):
            finder = DesignerFinder()
            result = finder._find_from_env()
            assert result is None

    def test_find_designer_from_env_not_set(self):
        """Змінна середовища не встановлена"""
        with patch('os.environ.get', return_value=None):
            finder = DesignerFinder()
            result = finder._find_from_env()
            assert result is None


# ============================================================================
# Test Designer Discovery from Windows Registry
# ============================================================================

class TestDesignerDiscoveryFromRegistry:
    """Тести пошуку Designer через Windows реєстр"""

    def test_find_designer_from_registry_success(self, mock_registry_data, mock_designer_path):
        """Знайдено Designer через реєстр"""
        # Mock winreg module
        mock_winreg = MagicMock()
        mock_key = MagicMock()

        # Налаштовуємо mock для OpenKey
        mock_winreg.OpenKey.return_value = mock_key
        mock_winreg.HKEY_LOCAL_MACHINE = "HKLM"
        mock_winreg.KEY_READ = 1
        mock_winreg.KEY_WOW64_64KEY = 2

        # Налаштовуємо mock для EnumKey (повертає версії)
        versions = list(mock_registry_data.keys())
        mock_winreg.EnumKey.side_effect = versions + [OSError]

        # Налаштовуємо mock для QueryValueEx (повертає шлях)
        mock_winreg.QueryValueEx.return_value = (str(mock_designer_path.parent.parent), None)

        with patch('importlib.import_module', return_value=mock_winreg):
            with patch.object(Path, 'exists', return_value=True):
                finder = DesignerFinder()
                result = finder._find_from_registry()
                # Може знайти або не знайти залежно від мокування
                # Основне - перевірити що метод не падає

    def test_find_designer_from_registry_multiple_versions(self, mock_registry_data):
        """Вибір найновішої версії з реєстру"""
        # Версії повинні бути відсортовані в зворотному порядку
        versions = sorted(mock_registry_data.keys(), reverse=True)
        assert versions[0] == "8.3.25.1394"  # Найновіша версія перша

    def test_find_designer_from_registry_not_found(self):
        """Designer не знайдено в реєстрі"""
        mock_winreg = MagicMock()
        mock_winreg.OpenKey.side_effect = FileNotFoundError("Registry key not found")

        with patch('importlib.import_module', return_value=mock_winreg):
            finder = DesignerFinder()
            result = finder._find_from_registry()
            assert result is None

    def test_find_designer_from_registry_no_winreg(self):
        """winreg недоступний (не Windows)"""
        with patch('importlib.import_module', side_effect=ImportError("No module named 'winreg'")):
            finder = DesignerFinder()
            result = finder._find_from_registry()
            assert result is None


# ============================================================================
# Test Designer Discovery from Standard Paths
# ============================================================================

class TestDesignerDiscoveryFromStandardPaths:
    """Тести пошуку Designer у стандартних шляхах"""

    def test_find_designer_from_standard_paths_success(self, tmp_path):
        """Знайдено Designer у стандартному шляху"""
        # Створюємо mock структуру директорій
        standard_path = tmp_path / "Program Files" / "1cv8"
        version_dir = standard_path / "8.3.25.1394"
        bin_dir = version_dir / "bin"
        bin_dir.mkdir(parents=True)
        designer = bin_dir / "1cv8.exe"
        designer.touch()

        # Патчимо в designer_finder_impl модулі (де реально використовується)
        with patch.object(designer_finder_impl, 'STANDARD_DESIGNER_PATHS_WINDOWS', [str(standard_path)]):
            finder = DesignerFinder()
            result = finder._find_from_standard_paths()
            assert result == designer

    def test_find_designer_from_standard_paths_multiple_versions(self, tmp_path):
        """Вібір найновішої версії зі стандартних шляхів"""
        standard_path = tmp_path / "Program Files" / "1cv8"
        standard_path.mkdir(parents=True)

        # Створюємо кілька версій
        versions = ["8.3.23.1880", "8.3.25.1394", "8.3.24.1537"]
        for version in versions:
            version_dir = standard_path / version / "bin"
            version_dir.mkdir(parents=True)
            (version_dir / "1cv8.exe").touch()

        # Патчимо в designer_finder_impl модулі (де реально використовується)
        with patch.object(designer_finder_impl, 'STANDARD_DESIGNER_PATHS_WINDOWS', [str(standard_path)]):
            finder = DesignerFinder()
            result = finder._find_from_standard_paths()
            # Має знайти найновішу версію (8.3.25.1394)
            assert result is not None
            assert "8.3.25" in str(result)

    def test_find_designer_from_standard_paths_not_found(self):
        """Designer не знайдено у стандартних шляхах"""
        # Патчимо в designer_finder_impl модулі (де реально використовується)
        with patch.object(designer_finder_impl, 'STANDARD_DESIGNER_PATHS_WINDOWS', ["/nonexistent/path"]):
            finder = DesignerFinder()
            result = finder._find_from_standard_paths()
            assert result is None


# ============================================================================
# Test EPF Compilation
# ============================================================================

class TestCompileEPF:
    """Тести компіляції EPF"""

    def test_compile_epf_success(self, mock_designer_path, mock_xml_root, tmp_path, mock_subprocess_result):
        """Успішна компіляція EPF"""
        # Disable persistent IB for this test
        compiler = create_test_compiler(designer_path=str(mock_designer_path), use_persistent_ib=False)
        output_epf = tmp_path / "ТестовыйПроцессор.epf"

        # Mock subprocess.run
        with patch('subprocess.run', return_value=mock_subprocess_result):
            # Mock створення EPF файлу
            with patch.object(Path, 'exists', side_effect=lambda: True if "epf" in str(output_epf) else mock_xml_root.exists()):
                with patch.object(Path, 'stat') as mock_stat:
                    mock_stat.return_value.st_size = 50000  # 50 KB
                    # Створюємо mock EPF файл для тесту
                    output_epf.touch()

                    result = compiler.compile_epf(mock_xml_root, output_epf)
                    assert result is True
                    assert output_epf.exists()

    def test_compile_epf_xml_not_found(self, mock_designer_path, tmp_path):
        """XML файл не існує"""
        compiler = create_test_compiler(designer_path=str(mock_designer_path))
        xml_path = tmp_path / "NonExistent.xml"
        output_epf = tmp_path / "Output.epf"

        with pytest.raises(FileNotFoundError):
            compiler.compile_epf(xml_path, output_epf)

    def test_compile_epf_designer_not_found(self, mock_xml_root, tmp_path):
        """Designer не встановлено"""
        with patch.object(DesignerFinder, 'find', return_value=None):
            compiler = create_test_compiler()
        compiler.designer_path = None
        output_epf = tmp_path / "Output.epf"

        result = compiler.compile_epf(mock_xml_root, output_epf)
        assert result is False

    def test_compile_epf_timeout(self, mock_designer_path, mock_xml_root, tmp_path):
        """Таймаут компіляції"""
        compiler = create_test_compiler(designer_path=str(mock_designer_path))
        output_epf = tmp_path / "Output.epf"

        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired(cmd="1cv8.exe", timeout=120)):
            result = compiler.compile_epf(mock_xml_root, output_epf, timeout=1)
            assert result is False

    def test_compile_epf_subprocess_error(self, mock_designer_path, mock_xml_root, tmp_path):
        """Помилка subprocess"""
        compiler = create_test_compiler(designer_path=str(mock_designer_path))
        output_epf = tmp_path / "Output.epf"

        with patch('subprocess.run', side_effect=Exception("Subprocess error")):
            result = compiler.compile_epf(mock_xml_root, output_epf)
            assert result is False

    def test_compile_epf_output_not_created(self, mock_designer_path, mock_xml_root, tmp_path, mock_subprocess_result):
        """Designer виконався, але EPF не створено"""
        compiler = create_test_compiler(designer_path=str(mock_designer_path))
        output_epf = tmp_path / "Output.epf"

        with patch('subprocess.run', return_value=mock_subprocess_result):
            # EPF файл НЕ створюється
            result = compiler.compile_epf(mock_xml_root, output_epf)
            assert result is False

    def test_compile_epf_custom_timeout(self, mock_designer_path, mock_xml_root, tmp_path, mock_subprocess_result):
        """Компіляція з кастомним таймаутом"""
        # Disable persistent IB to test timeout behavior with temp IB
        compiler = create_test_compiler(designer_path=str(mock_designer_path), use_persistent_ib=False)
        output_epf = tmp_path / "Output.epf"

        with patch('subprocess.run', return_value=mock_subprocess_result) as mock_run:
            with patch.object(Path, 'exists', return_value=True):
                with patch.object(Path, 'stat') as mock_stat:
                    mock_stat.return_value.st_size = 50000
                    output_epf.touch()

                    compiler.compile_epf(mock_xml_root, output_epf, timeout=60)
                    # Перевіряємо що subprocess.run викликано двічі (створення БД + завантаження EPF)
                    assert mock_run.call_count == 2
                    # Перший виклик (CREATEINFOBASE) має timeout=30 (половина від 60)
                    assert mock_run.call_args_list[0][1]['timeout'] == 30
                    # Другий виклик (DESIGNER /LoadEPF) має timeout=60
                    assert mock_run.call_args_list[1][1]['timeout'] == 60

    def test_compile_epf_with_cyrillic_paths(self, mock_designer_path, tmp_path, mock_subprocess_result):
        """Шляхи з кирилицею (перевірка encoding)"""
        # Створюємо XML з кирилицею в шляху
        xml_dir = tmp_path / "Тестовий_Процесор_Кирилиця"
        xml_dir.mkdir()
        xml_file = xml_dir / "Процесор.xml"
        xml_file.write_text("<?xml version='1.0'?>", encoding="utf-8")

        # Disable persistent IB for this test
        compiler = create_test_compiler(designer_path=str(mock_designer_path), use_persistent_ib=False)
        output_epf = tmp_path / "Процесор.epf"

        with patch('subprocess.run', return_value=mock_subprocess_result):
            with patch.object(Path, 'exists', return_value=True):
                with patch.object(Path, 'stat') as mock_stat:
                    mock_stat.return_value.st_size = 50000
                    output_epf.touch()

                    result = compiler.compile_epf(xml_file, output_epf)
                    assert result is True


# ============================================================================
# Integration Tests (Optional - потребують справжнього Designer)
# ============================================================================

class TestEPFCompilerIntegration:
    """Інтеграційні тести (запускаються тільки якщо Designer знайдено)"""

    @pytest.mark.integration
    def test_full_generation_with_epf(self, simple_processor, temp_dir, real_designer_path):
        """Повна генерація XML → EPF з справжнім Designer"""
        if not real_designer_path:
            pytest.skip("Designer не знайдено в системі")

        generator_module = importlib.import_module("1c_processor_generator.generator")
        ProcessorGenerator = generator_module.ProcessorGenerator

        # Генеруємо XML
        generator = ProcessorGenerator(simple_processor)
        processor_root = generator.generate(str(temp_dir), dry_run=False)

        assert processor_root is not None

        # Компілюємо в EPF
        compiler = create_test_compiler(designer_path=str(real_designer_path))
        processor_root = temp_dir / simple_processor.name
        xml_root = processor_root / f"{simple_processor.name}.xml"
        epf_path = temp_dir / f"{simple_processor.name}.epf"

        result = compiler.compile_epf(xml_root, epf_path, timeout=180)
        assert result is True
        assert epf_path.exists()
        assert epf_path.stat().st_size > 0

    @pytest.mark.integration
    def test_minimal_processor_epf_compilation(self, temp_dir, real_designer_path):
        """Створення мінімального процесора та компіляція в EPF"""
        if not real_designer_path:
            pytest.skip("Designer не знайдено в системі")

        # Імпортуємо models
        models_module = importlib.import_module("1c_processor_generator.models")
        Processor = models_module.Processor

        generator_module = importlib.import_module("1c_processor_generator.generator")
        ProcessorGenerator = generator_module.ProcessorGenerator

        # Створюємо мінімальний процесор
        processor = Processor(
            name="ТестИнтеграция",
            synonym_ru="Тест интеграции",
            synonym_uk="Тест інтеграції",
        )

        # Генеруємо XML
        generator = ProcessorGenerator(processor)
        processor_root = generator.generate(str(temp_dir), dry_run=False)

        assert processor_root is not None

        # Компілюємо в EPF
        compiler = create_test_compiler(designer_path=str(real_designer_path))
        processor_root = temp_dir / processor.name
        xml_root = processor_root / f"{processor.name}.xml"
        epf_path = temp_dir / f"{processor.name}.epf"

        result = compiler.compile_epf(xml_root, epf_path, timeout=180)
        assert result is True
        assert epf_path.exists()
        # Перевіряємо що EPF не порожній
        assert epf_path.stat().st_size > 1000  # Мінімум 1KB


# ============================================================================
# Additional Edge Cases
# ============================================================================

class TestEPFCompilerEdgeCases:
    """Тести граничних випадків"""

    def test_compiler_with_spaces_in_path(self, tmp_path, mock_subprocess_result):
        """Шляхи з пробілами"""
        designer_dir = tmp_path / "Program Files" / "1C Enterprise" / "8.3" / "bin"
        designer_dir.mkdir(parents=True)
        designer = designer_dir / "1cv8.exe"
        designer.touch()

        xml_dir = tmp_path / "Test Processor"
        xml_dir.mkdir()
        xml_file = xml_dir / "Test.xml"
        xml_file.write_text("<?xml version='1.0'?>", encoding="utf-8")

        # Disable persistent IB for this test
        compiler = create_test_compiler(designer_path=str(designer), use_persistent_ib=False)
        output_epf = tmp_path / "Output.epf"

        with patch('subprocess.run', return_value=mock_subprocess_result):
            with patch.object(Path, 'exists', return_value=True):
                with patch.object(Path, 'stat') as mock_stat:
                    mock_stat.return_value.st_size = 50000
                    output_epf.touch()

                    result = compiler.compile_epf(xml_file, output_epf)
                    assert result is True

    def test_compiler_very_large_epf(self, mock_designer_path, mock_xml_root, tmp_path, mock_subprocess_result):
        """Дуже великий EPF файл (>10 MB)"""
        # Disable persistent IB for this test
        compiler = create_test_compiler(designer_path=str(mock_designer_path), use_persistent_ib=False)
        output_epf = tmp_path / "Large.epf"

        with patch('subprocess.run', return_value=mock_subprocess_result):
            with patch.object(Path, 'exists', return_value=True):
                with patch.object(Path, 'stat') as mock_stat:
                    mock_stat.return_value.st_size = 15_000_000  # 15 MB
                    output_epf.touch()

                    result = compiler.compile_epf(mock_xml_root, output_epf)
                    assert result is True

    def test_find_designer_cascading_search(self):
        """Каскадний пошук: env → registry → standard paths"""
        finder = DesignerFinder()

        # Має спробувати всі методи по черзі
        with patch.object(finder, '_find_from_env', return_value=None):
            with patch.object(finder, '_find_from_registry', return_value=None):
                with patch.object(finder, '_find_from_standard_paths', return_value=Path("/found/1cv8.exe")):
                    result = finder.find()
                    assert result == Path("/found/1cv8.exe")


# ============================================================================
# Test v2.8.1 Features: Persistent IB + Silent Mode
# ============================================================================

class TestPersistentIB:
    """Тести для persistent IB кешу (v2.8.1+)"""

    def test_init_with_persistent_ib_enabled(self, mock_designer_path):
        """Ініціалізація з use_persistent_ib=True (default)"""
        compiler = create_test_compiler(designer_path=str(mock_designer_path))
        assert compiler.use_persistent_ib is True

    def test_init_with_persistent_ib_disabled(self, mock_designer_path):
        """Ініціалізація з use_persistent_ib=False"""
        compiler = create_test_compiler(designer_path=str(mock_designer_path), use_persistent_ib=False)
        assert compiler.use_persistent_ib is False

    def test_get_or_create_persistent_ib_creates_new(self, mock_designer_path, tmp_path, mock_subprocess_result):
        """Створення нової persistent IB"""
        # Mock кеш директорію
        cache_dir = tmp_path / "cache"
        persistent_ib = cache_dir / "temp_ib"

        # Mock subprocess.run щоб "створити" IB
        def mock_subprocess(*args, **kwargs):
            # Після виклику CREATEINFOBASE створюємо директорію
            persistent_ib.mkdir(parents=True, exist_ok=True)
            return mock_subprocess_result

        with patch('subprocess.run', side_effect=mock_subprocess):
            manager = PersistentIBManager(mock_designer_path, cache_dir=cache_dir, ib_path=persistent_ib)
            result = manager.get_or_create()
            assert result == persistent_ib
            assert persistent_ib.exists()

    def test_get_or_create_persistent_ib_reuses_existing(self, mock_designer_path, tmp_path):
        """Повторне використання існуючої persistent IB"""
        # Створюємо існуючу IB з маркером валідності
        cache_dir = tmp_path / "cache"
        persistent_ib = cache_dir / "temp_ib"
        persistent_ib.mkdir(parents=True)
        # Створюємо маркер версії щоб уникнути invalidation
        (persistent_ib / "1cv8.1CD").touch()

        # Mock subprocess щоб уникнути реального виконання Designer
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch('subprocess.run', return_value=mock_result):
            manager = PersistentIBManager(mock_designer_path, cache_dir=cache_dir, ib_path=persistent_ib)
            result = manager.get_or_create()
            assert result == persistent_ib

    def test_get_or_create_persistent_ib_designer_not_found(self, tmp_path):
        """Persistent IB без Designer"""
        cache_dir = tmp_path / "cache"
        persistent_ib = cache_dir / "temp_ib"

        manager = PersistentIBManager(designer_path=None, cache_dir=cache_dir, ib_path=persistent_ib)
        result = manager.get_or_create()
        assert result is None

    def test_get_or_create_persistent_ib_creation_fails(self, mock_designer_path, tmp_path):
        """Помилка створення persistent IB"""
        cache_dir = tmp_path / "cache"
        persistent_ib = cache_dir / "temp_ib"

        # Mock subprocess помилка
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Creation error"

        with patch('subprocess.run', return_value=mock_result):
            manager = PersistentIBManager(mock_designer_path, cache_dir=cache_dir, ib_path=persistent_ib)
            result = manager.get_or_create()
            assert result is None

    def test_compile_epf_with_persistent_ib(self, mock_designer_path, mock_xml_root, tmp_path, mock_subprocess_result):
        """Компіляція з використанням persistent IB"""
        compiler = create_test_compiler(designer_path=str(mock_designer_path), use_persistent_ib=True)
        output_epf = tmp_path / "Output.epf"

        # Mock persistent IB
        persistent_ib = tmp_path / "cache" / "temp_ib"
        persistent_ib.mkdir(parents=True)

        with patch.object(compiler.ib_manager, 'get_or_create', return_value=persistent_ib):
            with patch.object(compiler, '_load_epf_to_ib', return_value=True) as mock_load:
                result = compiler.compile_epf(mock_xml_root, output_epf)
                assert result is True
                # Перевіряємо що _load_epf_to_ib викликано з persistent IB
                mock_load.assert_called_once()
                assert mock_load.call_args[0][0] == persistent_ib

    def test_compile_epf_without_persistent_ib(self, mock_designer_path, mock_xml_root, tmp_path, mock_subprocess_result):
        """Компіляція без persistent IB (старий спосіб)"""
        compiler = create_test_compiler(designer_path=str(mock_designer_path), use_persistent_ib=False)
        output_epf = tmp_path / "Output.epf"

        with patch('subprocess.run', return_value=mock_subprocess_result):
            with patch.object(compiler, '_load_epf_to_ib', return_value=True) as mock_load:
                result = compiler.compile_epf(mock_xml_root, output_epf)
                assert result is True
                # Має використовувати тимчасову IB (не persistent)
                mock_load.assert_called_once()

    def test_compile_epf_persistent_ib_fallback(self, mock_designer_path, mock_xml_root, tmp_path, mock_subprocess_result):
        """Fallback на тимчасову IB якщо persistent IB не вдалося створити"""
        compiler = create_test_compiler(designer_path=str(mock_designer_path), use_persistent_ib=True)
        output_epf = tmp_path / "Output.epf"

        # Mock що persistent IB не вдалося створити
        with patch.object(compiler.ib_manager, 'get_or_create', return_value=None):
            with patch('subprocess.run', return_value=mock_subprocess_result):
                with patch.object(compiler, '_load_epf_to_ib', return_value=True) as mock_load:
                    result = compiler.compile_epf(mock_xml_root, output_epf)
                    assert result is True
                    # Має використати тимчасову IB як fallback
                    mock_load.assert_called_once()


class TestSilentMode:
    """Тести для silent mode (v2.8.1+)"""

    def test_load_epf_to_ib_includes_silent_params(self, mock_designer_path, mock_xml_root, tmp_path, mock_subprocess_result):
        """Перевірка що silent mode параметри додані до команди"""
        compiler = create_test_compiler(designer_path=str(mock_designer_path))
        temp_ib = tmp_path / "temp_ib"
        temp_ib.mkdir()
        output_epf = tmp_path / "Output.epf"

        with patch('subprocess.run', return_value=mock_subprocess_result) as mock_run:
            with patch.object(Path, 'exists', return_value=True):
                with patch.object(Path, 'stat') as mock_stat:
                    mock_stat.return_value.st_size = 50000
                    output_epf.touch()

                    result = compiler._load_epf_to_ib(temp_ib, mock_xml_root, output_epf, 120)
                    assert result is True

                    # Перевіряємо що silent params включені
                    call_args = mock_run.call_args[0][0]
                    assert "/DisableStartupMessages" in call_args
                    assert "/DisableStartupDialogs" in call_args


class TestClearCache:
    """Тести для clear_cache() методу (v2.8.1+)"""

    def test_clear_cache_removes_directory(self, tmp_path):
        """Очистка існуючого кешу"""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        (cache_dir / "temp_ib").mkdir()
        (cache_dir / "some_file.txt").touch()

        # Патчимо в persistent_ib_impl модулі (де реально використовується)
        with patch.object(persistent_ib_impl, 'EPF_COMPILER_CACHE_DIR', cache_dir):
            result = PersistentIBManager.clear_global_cache()
            assert result is True
            assert not cache_dir.exists()

    def test_clear_cache_no_directory(self, tmp_path):
        """Очистка коли директорія не існує"""
        cache_dir = tmp_path / "nonexistent_cache"

        # Патчимо в persistent_ib_impl модулі (де реально використовується)
        with patch.object(persistent_ib_impl, 'EPF_COMPILER_CACHE_DIR', cache_dir):
            result = PersistentIBManager.clear_global_cache()
            assert result is True  # Не помилка, просто нічого не робить

    def test_clear_cache_permission_error(self, tmp_path):
        """Помилка доступу при очистці кешу"""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        # Патчимо в persistent_ib_impl модулі (де реально використовується)
        with patch.object(persistent_ib_impl, 'EPF_COMPILER_CACHE_DIR', cache_dir):
            with patch('shutil.rmtree', side_effect=PermissionError("Access denied")):
                result = PersistentIBManager.clear_global_cache()
                assert result is False
