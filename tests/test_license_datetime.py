"""
Unit tests for license.py datetime handling (v2.68.1)

Tests for:
- _parse_iso_datetime() helper function
- Token expiry validation
- Grace period calculation
- Timezone handling (offset-naive vs offset-aware)

These tests ensure Python 3.10-3.14 compatibility for datetime operations.
"""

import pytest
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock


# ============================================================================
# Test Setup - Import license module functions directly
# ============================================================================

# We need to import the helper function directly to test it
# The module has side effects on import, so we patch them
@pytest.fixture
def license_module():
    """Import license module with mocked side effects."""
    # Patch the license manager getter to avoid network calls
    with patch.dict('sys.modules', {'cryptography': MagicMock()}):
        # Add path for import
        sys.path.insert(0, str(Path(__file__).parent.parent / "1c_processor_generator" / "pro"))

        # Import the function we're testing
        try:
            from license import _parse_iso_datetime
            yield _parse_iso_datetime
        except ImportError:
            pytest.skip("license module not available in test environment")
        finally:
            sys.path.pop(0)


# ============================================================================
# Test _parse_iso_datetime()
# ============================================================================

class TestParseIsoDatetime:
    """Tests for _parse_iso_datetime() helper function."""

    def test_parse_z_suffix(self, license_module):
        """Test parsing ISO datetime with Z suffix."""
        _parse_iso_datetime = license_module

        result = _parse_iso_datetime("2025-03-15T12:00:00Z")

        assert result.tzinfo is not None
        assert result.year == 2025
        assert result.month == 3
        assert result.day == 15
        assert result.hour == 12

    def test_parse_explicit_offset(self, license_module):
        """Test parsing ISO datetime with explicit +00:00 offset."""
        _parse_iso_datetime = license_module

        result = _parse_iso_datetime("2025-03-15T12:00:00+00:00")

        assert result.tzinfo is not None
        assert result.year == 2025

    def test_parse_positive_offset(self, license_module):
        """Test parsing ISO datetime with positive offset (+03:00)."""
        _parse_iso_datetime = license_module

        result = _parse_iso_datetime("2025-03-15T15:00:00+03:00")

        assert result.tzinfo is not None
        # Offset should be preserved
        assert result.hour == 15

    def test_parse_negative_offset(self, license_module):
        """Test parsing ISO datetime with negative offset (-05:00)."""
        _parse_iso_datetime = license_module

        result = _parse_iso_datetime("2025-03-15T07:00:00-05:00")

        assert result.tzinfo is not None
        assert result.hour == 7

    def test_naive_becomes_utc(self, license_module):
        """Test that naive datetime (without timezone) becomes UTC-aware."""
        _parse_iso_datetime = license_module

        result = _parse_iso_datetime("2025-03-15T12:00:00")

        assert result.tzinfo == timezone.utc
        assert result.year == 2025

    def test_empty_string_raises(self, license_module):
        """Test that empty string raises ValueError."""
        _parse_iso_datetime = license_module

        with pytest.raises(ValueError, match="Empty datetime string"):
            _parse_iso_datetime("")

    def test_none_raises(self, license_module):
        """Test that None raises ValueError."""
        _parse_iso_datetime = license_module

        with pytest.raises((ValueError, TypeError)):
            _parse_iso_datetime(None)


# ============================================================================
# Test Datetime Comparisons (Integration-style tests)
# ============================================================================

class TestDatetimeComparisons:
    """Tests for datetime comparison scenarios that caused the original bug."""

    def test_z_suffix_vs_now_utc(self, license_module):
        """
        Test that Z-suffixed datetime can be compared with datetime.now(timezone.utc).

        This was the original bug: comparing offset-aware (from API) with offset-naive.
        """
        _parse_iso_datetime = license_module

        # Simulate expiry date from API (with Z suffix)
        future_date = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat().replace('+00:00', 'Z')
        expires = _parse_iso_datetime(future_date)
        now = datetime.now(timezone.utc)

        # This comparison should NOT raise TypeError
        assert expires > now  # Future date is greater

    def test_z_suffix_vs_now_utc_expired(self, license_module):
        """Test comparing expired Z-suffixed datetime with now."""
        _parse_iso_datetime = license_module

        # Simulate past expiry date
        past_date = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat().replace('+00:00', 'Z')
        expires = _parse_iso_datetime(past_date)
        now = datetime.now(timezone.utc)

        # This comparison should NOT raise TypeError
        assert expires < now  # Past date is less

    def test_datetime_subtraction(self, license_module):
        """Test that subtraction works for grace period calculation."""
        _parse_iso_datetime = license_module

        # Simulate last_online_verify from 5 days ago
        five_days_ago = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        last_verify = _parse_iso_datetime(five_days_ago)
        now = datetime.now(timezone.utc)

        # Subtraction should work without TypeError
        days_offline = (now - last_verify).days
        assert days_offline >= 4  # At least 4-5 days

    def test_future_check_for_time_manipulation(self, license_module):
        """Test time manipulation detection (last_verify in future)."""
        _parse_iso_datetime = license_module

        # Simulate last_verify in future (suspicious)
        future_verify = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        last_verify = _parse_iso_datetime(future_verify)
        now = datetime.now(timezone.utc)

        # Check if in future (should NOT raise TypeError)
        is_future = last_verify > now + timedelta(hours=1)
        assert is_future is True


# ============================================================================
# Test Edge Cases
# ============================================================================

class TestDatetimeEdgeCases:
    """Tests for edge cases in datetime handling."""

    def test_microseconds_preserved(self, license_module):
        """Test that microseconds are preserved in parsing."""
        _parse_iso_datetime = license_module

        result = _parse_iso_datetime("2025-03-15T12:00:00.123456Z")

        assert result.microsecond == 123456

    def test_different_timezone_offsets(self, license_module):
        """Test various timezone offsets."""
        _parse_iso_datetime = license_module

        test_cases = [
            "2025-03-15T12:00:00+00:00",
            "2025-03-15T12:00:00+02:00",
            "2025-03-15T12:00:00-07:00",
            "2025-03-15T12:00:00+05:30",  # India
            "2025-03-15T12:00:00+09:00",  # Japan
        ]

        for dt_str in test_cases:
            result = _parse_iso_datetime(dt_str)
            assert result.tzinfo is not None, f"Failed for: {dt_str}"

    def test_iso_format_roundtrip(self, license_module):
        """Test that parsed datetime can be converted back to ISO."""
        _parse_iso_datetime = license_module

        original = "2025-03-15T12:00:00Z"
        parsed = _parse_iso_datetime(original)

        # Should be convertible back to ISO
        iso_back = parsed.isoformat()
        assert "2025-03-15" in iso_back
        assert "12:00:00" in iso_back


# ============================================================================
# Test Python Version Compatibility
# ============================================================================

class TestPythonVersionCompatibility:
    """Tests to ensure compatibility across Python versions."""

    def test_z_suffix_handling_all_formats(self, license_module):
        """
        Test Z suffix handling across all common API response formats.

        Python < 3.11 doesn't support 'Z' natively in fromisoformat().
        Our helper should handle it correctly.
        """
        _parse_iso_datetime = license_module

        # Common formats from various APIs
        formats = [
            "2025-03-15T12:00:00Z",
            "2025-03-15T12:00:00.000Z",
            "2025-03-15T12:00:00.123456Z",
        ]

        for fmt in formats:
            result = _parse_iso_datetime(fmt)
            assert result.tzinfo is not None, f"Z suffix not handled for: {fmt}"
            # Should be comparable with now
            _ = result > datetime.now(timezone.utc)  # Should not raise

    def test_comparison_never_raises_typeerror(self, license_module):
        """
        Ensure that comparison between parsed datetime and now never raises.

        This is the core fix for Python 3.14 compatibility issue.
        """
        _parse_iso_datetime = license_module

        test_datetimes = [
            "2025-03-15T12:00:00Z",
            "2025-03-15T12:00:00+00:00",
            "2025-03-15T12:00:00",  # Naive
            "2025-03-15T12:00:00.000000Z",
            "2025-03-15T12:00:00.000000+00:00",
        ]

        now = datetime.now(timezone.utc)

        for dt_str in test_datetimes:
            try:
                parsed = _parse_iso_datetime(dt_str)
                # All these should work without TypeError
                _ = parsed > now
                _ = parsed < now
                _ = parsed >= now
                _ = parsed <= now
                _ = parsed == now
                _ = (now - parsed).days
            except TypeError as e:
                pytest.fail(f"TypeError raised for '{dt_str}': {e}")
