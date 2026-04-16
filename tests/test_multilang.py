"""
Tests for compact multilang syntax (v2.69.0+).

Tests the parse_multilang_value() and normalize_multilang() functions
for array, pipe, and fallback behavior.
"""

import sys
import importlib
from pathlib import Path

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

extractors_module = importlib.import_module("1c_processor_generator.parsing.extractors")
parse_multilang_value = extractors_module.parse_multilang_value
normalize_multilang = extractors_module.normalize_multilang
DEFAULT_LANGUAGES = extractors_module.DEFAULT_LANGUAGES


class TestParseMultilangValue:
    """Tests for parse_multilang_value function."""

    def test_dict_format_passthrough(self):
        """Dict format should pass through unchanged."""
        languages = ["ru", "uk", "en"]
        value = {"ru": "Тест", "uk": "Тест", "en": "Test"}

        result = parse_multilang_value(value, languages)

        assert result == {"ru": "Тест", "uk": "Тест", "en": "Test"}

    def test_array_format_full(self):
        """Array with all languages should map correctly."""
        languages = ["ru", "uk", "en"]
        value = ["Тест RU", "Тест UK", "Test EN"]

        result = parse_multilang_value(value, languages)

        assert result == {"ru": "Тест RU", "uk": "Тест UK", "en": "Test EN"}

    def test_array_format_fallback_to_first(self):
        """Array with fewer values should fallback to first (primary)."""
        languages = ["ru", "uk", "en"]
        value = ["Тест RU", "Тест UK"]

        result = parse_multilang_value(value, languages)

        assert result == {"ru": "Тест RU", "uk": "Тест UK", "en": "Тест RU"}

    def test_array_format_single_value(self):
        """Array with single value should apply to all."""
        languages = ["ru", "uk", "en"]
        value = ["Same"]

        result = parse_multilang_value(value, languages)

        assert result == {"ru": "Same", "uk": "Same", "en": "Same"}

    def test_pipe_format_full(self):
        """Pipe string with all values should map correctly."""
        languages = ["ru", "uk", "en"]
        value = "Тест RU | Тест UK | Test EN"

        result = parse_multilang_value(value, languages)

        assert result == {"ru": "Тест RU", "uk": "Тест UK", "en": "Test EN"}

    def test_pipe_format_fallback_to_first(self):
        """Pipe with fewer values should fallback to first (primary)."""
        languages = ["ru", "uk", "en"]
        value = "Тест RU | Тест UK"

        result = parse_multilang_value(value, languages)

        assert result == {"ru": "Тест RU", "uk": "Тест UK", "en": "Тест RU"}

    def test_pipe_format_with_spaces(self):
        """Pipe format should trim whitespace."""
        languages = ["ru", "uk"]
        value = "  Тест  |  Тест  "

        result = parse_multilang_value(value, languages)

        assert result == {"ru": "Тест", "uk": "Тест"}

    def test_pipe_escape(self):
        """Escaped pipe (\\|) should be preserved in output."""
        languages = ["ru", "uk"]
        value = r"A \| B | А \| Б"

        result = parse_multilang_value(value, languages)

        assert result == {"ru": "A | B", "uk": "А | Б"}

    def test_plain_string_all_same(self):
        """Plain string without pipe should apply to all languages."""
        languages = ["ru", "uk", "en"]
        value = "Заголовок"

        result = parse_multilang_value(value, languages)

        assert result == {"ru": "Заголовок", "uk": "Заголовок", "en": "Заголовок"}

    def test_two_languages(self):
        """Should work with 2-language projects."""
        languages = ["ru", "uk"]
        value = "Отчет | Звіт"

        result = parse_multilang_value(value, languages)

        assert result == {"ru": "Отчет", "uk": "Звіт"}


class TestNormalizeMultilang:
    """Tests for normalize_multilang function."""

    def test_dict_format_nested(self):
        """Nested dict format should convert to flat."""
        config = {
            "name": "Test",
            "title": {"ru": "Тест", "uk": "Тест"}
        }

        result = normalize_multilang(config, languages=["ru", "uk", "en"])

        assert result["title_ru"] == "Тест"
        assert result["title_uk"] == "Тест"
        assert "title" not in result

    def test_array_format(self):
        """Array format should convert to flat."""
        config = {
            "name": "Test",
            "title": ["Тест RU", "Тест UK"]
        }

        result = normalize_multilang(config, languages=["ru", "uk", "en"])

        assert result["title_ru"] == "Тест RU"
        assert result["title_uk"] == "Тест UK"
        assert result["title_en"] == "Тест RU"  # Fallback to first
        assert "title" not in result

    def test_pipe_format(self):
        """Pipe format should convert to flat."""
        config = {
            "name": "Test",
            "title": "Тест RU | Тест UK | Test EN"
        }

        result = normalize_multilang(config, languages=["ru", "uk", "en"])

        assert result["title_ru"] == "Тест RU"
        assert result["title_uk"] == "Тест UK"
        assert result["title_en"] == "Test EN"
        assert "title" not in result

    def test_plain_string(self):
        """Plain string should apply to all languages."""
        config = {
            "name": "Test",
            "title": "Same"
        }

        result = normalize_multilang(config, languages=["ru", "uk"])

        assert result["title_ru"] == "Same"
        assert result["title_uk"] == "Same"
        assert "title" not in result

    def test_flat_format_unchanged(self):
        """Already flat format should not be modified."""
        config = {
            "name": "Test",
            "title_ru": "Existing RU",
            "title_uk": "Existing UK"
        }

        result = normalize_multilang(config, languages=["ru", "uk", "en"])

        assert result["title_ru"] == "Existing RU"
        assert result["title_uk"] == "Existing UK"

    def test_multiple_fields(self):
        """Should normalize multiple multilang fields."""
        config = {
            "name": "Test",
            "synonym": "Синоним | Синонім",
            "title": ["Заголовок RU", "Заголовок UK"],
            "tooltip": {"ru": "Подсказка", "uk": "Підказка"}
        }

        result = normalize_multilang(config, languages=["ru", "uk"])

        assert result["synonym_ru"] == "Синоним"
        assert result["synonym_uk"] == "Синонім"
        assert result["title_ru"] == "Заголовок RU"
        assert result["title_uk"] == "Заголовок UK"
        assert result["tooltip_ru"] == "Подсказка"
        assert result["tooltip_uk"] == "Підказка"

    def test_default_languages(self):
        """Should use default languages when not specified."""
        config = {
            "name": "Test",
            "title": ["A", "B", "C"]
        }

        result = normalize_multilang(config)

        assert result["title_ru"] == "A"
        assert result["title_uk"] == "B"
        assert result["title_en"] == "C"

    def test_backward_compatibility(self):
        """Old dict format should still work."""
        config = {
            "name": "Test",
            "synonym": {"ru": "Тест", "uk": "Тест", "en": "Test"}
        }

        result = normalize_multilang(config)

        assert result["synonym_ru"] == "Тест"
        assert result["synonym_uk"] == "Тест"
        assert result["synonym_en"] == "Test"
        assert "synonym" not in result


class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_empty_array(self):
        """Empty array should return empty strings."""
        languages = ["ru", "uk"]
        value = []

        result = parse_multilang_value(value, languages)

        assert result == {"ru": "", "uk": ""}

    def test_string_with_single_pipe_at_end(self):
        """String ending with | should handle correctly."""
        languages = ["ru", "uk"]
        value = "Test |"

        result = parse_multilang_value(value, languages)

        # "Test |" splits to ["Test", ""] - second is empty string
        assert result["ru"] == "Test"
        assert result["uk"] == ""

    def test_only_escaped_pipes(self):
        """String with only escaped pipes should be treated as plain."""
        languages = ["ru", "uk"]
        value = r"A \| B \| C"

        result = parse_multilang_value(value, languages)

        # No unescaped pipes, so treated as plain string
        assert result["ru"] == "A | B | C"
        assert result["uk"] == "A | B | C"
