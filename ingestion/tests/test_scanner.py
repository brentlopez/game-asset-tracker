"""Tests for scanner module."""

import tempfile
from pathlib import Path

import pytest

from game_asset_tracker_ingestion.scanner import (
    sanitize_filename,
    validate_path_safety,
    validate_url,
)


class TestSanitizeFilename:
    """Test filename sanitization."""

    def test_removes_dangerous_characters(self) -> None:
        """Test that dangerous characters are removed."""
        assert sanitize_filename("file<test>.txt") == "filetest.txt"
        assert sanitize_filename('file"test".txt') == "filetest.txt"
        assert sanitize_filename("file|test.txt") == "filetest.txt"

    def test_removes_path_separators(self) -> None:
        """Test that path separators are removed."""
        assert sanitize_filename("../../../etc/passwd") == "......etcpasswd"
        assert sanitize_filename("..\\..\\..\\windows\\system32") == "......windowssystem32"

    def test_safe_filenames_unchanged(self) -> None:
        """Test that safe filenames pass through unchanged."""
        assert sanitize_filename("normal_file.txt") == "normal_file.txt"
        assert sanitize_filename("file-name_123.png") == "file-name_123.png"


class TestValidatePathSafety:
    """Test path traversal prevention."""

    def test_allows_paths_within_base(self) -> None:
        """Test that paths within base directory are allowed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            safe_path = base / "subdir" / "file.txt"
            # Should not raise
            validate_path_safety(safe_path, base)

    def test_rejects_path_traversal(self) -> None:
        """Test that path traversal attempts are rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            # Create a path that tries to escape
            dangerous_path = base / ".." / ".." / "etc" / "passwd"

            with pytest.raises(ValueError, match="escapes base directory"):
                validate_path_safety(dangerous_path, base)

    def test_allows_symlinks_within_base(self) -> None:
        """Test that symlinks within base directory are allowed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            target = base / "target.txt"
            link = base / "link.txt"

            # Create target file and symlink
            target.touch()
            link.symlink_to(target)

            # Should not raise since link resolves within base
            validate_path_safety(link, base)


class TestValidateUrl:
    """Test URL validation."""

    def test_allows_http_https(self) -> None:
        """Test that http and https URLs are allowed."""
        # Should not raise
        validate_url("http://example.com")
        validate_url("https://example.com/path")

    def test_allows_empty_string(self) -> None:
        """Test that empty string is allowed."""
        validate_url("")  # Should not raise

    def test_rejects_dangerous_schemes(self) -> None:
        """Test that dangerous schemes are rejected."""
        with pytest.raises(ValueError, match="Invalid URL scheme"):
            validate_url("javascript:alert('xss')")

        with pytest.raises(ValueError, match="Invalid URL scheme"):
            validate_url("file:///etc/passwd")

        with pytest.raises(ValueError, match="Invalid URL scheme"):
            validate_url("data:text/html,<script>alert('xss')</script>")

    def test_allows_relative_paths(self) -> None:
        """Test that relative file paths are allowed."""
        # These have no scheme, so should be allowed
        validate_url("../license.txt")
        validate_url("docs/license.md")
