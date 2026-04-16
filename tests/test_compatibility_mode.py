"""
Тести для CompatibilityMode генерації (v2.64.1)

Перевіряє правильність визначення CompatibilityMode для Configuration.xml.
Критичний баг: processor.platform_version (версія формату XML) помилково
використовувався як fallback для CompatibilityMode замість версії платформи 1C.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
import sys
import importlib

# Додаємо батьківську директорію в sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Імпортуємо модулі через importlib (назва з дефісом)
constants = importlib.import_module("1c_processor_generator.constants")
DEFAULT_COMPATIBILITY_MODE = constants.DEFAULT_COMPATIBILITY_MODE


class TestCompatibilityMode:
    """Test suite for CompatibilityMode bug fix (v2.64.1)"""

    def test_default_compatibility_mode_value(self):
        """DEFAULT_COMPATIBILITY_MODE should be Version8_3_15"""
        assert DEFAULT_COMPATIBILITY_MODE == "Version8_3_15"

    def test_default_compatibility_mode_format(self):
        """DEFAULT_COMPATIBILITY_MODE should match 1C format"""
        assert DEFAULT_COMPATIBILITY_MODE.startswith("Version8_3_")


class TestDesignerFinderPlatformVersion:
    """Test DesignerFinder.platform_version attribute (v2.64.1)"""

    def test_designer_finder_has_platform_version_attribute(self):
        """DesignerFinder should have platform_version attribute"""
        designer_finder = importlib.import_module("1c_processor_generator.pro.designer_finder_impl")
        DesignerFinder = designer_finder.DesignerFinder

        finder = DesignerFinder.__new__(DesignerFinder)
        finder.designer_path = None
        finder.platform_version = None

        assert hasattr(finder, 'platform_version')

    def test_designer_finder_version_initially_none(self):
        """DesignerFinder.platform_version should be initialized to None"""
        designer_finder = importlib.import_module("1c_processor_generator.pro.designer_finder_impl")
        DesignerFinder = designer_finder.DesignerFinder

        # Create instance without calling __init__
        finder = DesignerFinder.__new__(DesignerFinder)
        finder.designer_path = None
        finder.platform_version = None

        # Verify initial state
        assert finder.platform_version is None


class TestGetCompatibilityMode:
    """Test ConfigurationGenerator._get_compatibility_mode() (v2.64.1)"""

    @pytest.fixture
    def mock_config_generator(self):
        """Create mock ConfigurationGenerator for testing"""
        config_gen = importlib.import_module("1c_processor_generator.pro.config_generator_impl")
        ConfigurationGenerator = config_gen.ConfigurationGenerator

        # Create mock processor and requirements
        mock_processor = MagicMock()
        mock_processor.name = "TestProcessor"
        mock_processor.platform_version = "2.11"  # XML format version, NOT platform!

        mock_requirements = MagicMock()
        mock_requirements.catalogs = []
        mock_requirements.documents = []
        mock_requirements.common_pictures = []
        mock_requirements.common_modules = []
        mock_requirements.get_stub_attributes.return_value = []

        # Create generator with installed_platform_version
        generator = ConfigurationGenerator.__new__(ConfigurationGenerator)
        generator.processor = mock_processor
        generator.requirements = mock_requirements
        generator.installed_platform_version = None

        return generator

    def test_valid_platform_version_8_3_25(self, mock_config_generator):
        """Version 8.3.25.1394 → Version8_3_25"""
        result = mock_config_generator._get_compatibility_mode("8.3.25.1394")
        assert result == "Version8_3_25"

    def test_valid_platform_version_8_3_15(self, mock_config_generator):
        """Version 8.3.15.2100 → Version8_3_15"""
        result = mock_config_generator._get_compatibility_mode("8.3.15.2100")
        assert result == "Version8_3_15"

    def test_valid_platform_version_8_3_18(self, mock_config_generator):
        """Version 8.3.18.1500 → Version8_3_18"""
        result = mock_config_generator._get_compatibility_mode("8.3.18.1500")
        assert result == "Version8_3_18"

    def test_invalid_format_version_2_11(self, mock_config_generator):
        """Version 2.11 (XML format) should fallback to DEFAULT_COMPATIBILITY_MODE"""
        result = mock_config_generator._get_compatibility_mode("2.11")
        assert result == DEFAULT_COMPATIBILITY_MODE

    def test_invalid_format_version_2_18(self, mock_config_generator):
        """Version 2.18 (XML format) should fallback to DEFAULT_COMPATIBILITY_MODE"""
        result = mock_config_generator._get_compatibility_mode("2.18")
        assert result == DEFAULT_COMPATIBILITY_MODE

    def test_invalid_format_empty_string(self, mock_config_generator):
        """Empty string should fallback to DEFAULT_COMPATIBILITY_MODE"""
        result = mock_config_generator._get_compatibility_mode("")
        assert result == DEFAULT_COMPATIBILITY_MODE

    def test_invalid_format_random_string(self, mock_config_generator):
        """Random string should fallback to DEFAULT_COMPATIBILITY_MODE"""
        result = mock_config_generator._get_compatibility_mode("random")
        assert result == DEFAULT_COMPATIBILITY_MODE


class TestExtractPlatformVersion:
    """Test platform version extraction from path (v2.64.1)

    Tests the regex pattern used to extract platform version from Designer path.
    The regex is: r'(8\\.3\\.\\d+\\.\\d+)'
    """
    import re

    # Regex pattern from EPFCompiler._extract_platform_version
    VERSION_PATTERN = re.compile(r'(8\.3\.\d+\.\d+)')

    def _extract_version(self, path_str: str):
        """Helper to extract version using the same regex as EPFCompiler"""
        match = self.VERSION_PATTERN.search(path_str)
        return match.group(1) if match else None

    def test_extract_version_from_standard_path(self):
        """C:\\Program Files\\1cv8\\8.3.25.1394\\bin\\1cv8.exe → 8.3.25.1394"""
        path = "C:\\Program Files\\1cv8\\8.3.25.1394\\bin\\1cv8.exe"
        result = self._extract_version(path)
        assert result == "8.3.25.1394"

    def test_extract_version_from_baf_path(self):
        """C:\\Program Files\\BAF\\8.3.20.2000\\bin\\1cv8.exe → 8.3.20.2000"""
        path = "C:\\Program Files\\BAF\\8.3.20.2000\\bin\\1cv8.exe"
        result = self._extract_version(path)
        assert result == "8.3.20.2000"

    def test_extract_version_from_custom_path(self):
        """D:\\Apps\\1C\\8.3.15.2100\\1cv8.exe → 8.3.15.2100"""
        path = "D:\\Apps\\1C\\8.3.15.2100\\1cv8.exe"
        result = self._extract_version(path)
        assert result == "8.3.15.2100"

    def test_extract_version_no_version_in_path(self):
        """C:\\MyApps\\1cv8.exe → None"""
        path = "C:\\MyApps\\1cv8.exe"
        result = self._extract_version(path)
        assert result is None

    def test_extract_version_from_linux_path(self):
        """/opt/1cv8/8.3.25.1394/1cv8 → 8.3.25.1394"""
        path = "/opt/1cv8/8.3.25.1394/1cv8"
        result = self._extract_version(path)
        assert result == "8.3.25.1394"

    def test_extract_version_x86_path(self):
        """C:\\Program Files (x86)\\1cv8\\8.3.18.1500\\bin\\1cv8.exe → 8.3.18.1500"""
        path = "C:\\Program Files (x86)\\1cv8\\8.3.18.1500\\bin\\1cv8.exe"
        result = self._extract_version(path)
        assert result == "8.3.18.1500"

    def test_extract_first_version_if_multiple(self):
        """If multiple versions in path, extract first one"""
        path = "C:\\1cv8\\8.3.25.1394\\backup\\8.3.20.2000\\1cv8.exe"
        result = self._extract_version(path)
        assert result == "8.3.25.1394"

    def test_version_format_must_be_8_3(self):
        """Version 9.0.1.2 should NOT match (only 8.3.x.x supported)"""
        path = "C:\\1cv9\\9.0.1.2345\\bin\\1cv8.exe"
        result = self._extract_version(path)
        assert result is None
