#!/usr/bin/env python3
"""
Unit tests for dependencies_utils module.
"""
import os
import platform
import shutil
import subprocess
import tarfile
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, call

import pytest

import dependencies_utils


class TestIsWithinDirectory:
    """Test the _is_within_directory path traversal prevention function."""

    def test_is_within_directory_valid_subdirectory(self, tmp_path):
        """Test that a valid subdirectory is recognized as within the parent."""
        parent_dir = tmp_path / "parent"
        parent_dir.mkdir()
        sub_dir = parent_dir / "subdir"
        sub_dir.mkdir()

        assert dependencies_utils._is_within_directory(str(parent_dir), str(sub_dir))

    def test_is_within_directory_valid_file_in_directory(self, tmp_path):
        """Test that a file within a directory is recognized."""
        parent_dir = tmp_path / "parent"
        parent_dir.mkdir()
        file_path = parent_dir / "file.txt"
        file_path.touch()

        assert dependencies_utils._is_within_directory(str(parent_dir), str(file_path))

    def test_is_within_directory_same_directory(self, tmp_path):
        """Test that a directory is considered within itself."""
        test_dir = tmp_path / "test"
        test_dir.mkdir()

        assert dependencies_utils._is_within_directory(str(test_dir), str(test_dir))

    def test_is_within_directory_path_traversal_attempt(self, tmp_path):
        """Test that path traversal attempts are detected and blocked."""
        parent_dir = tmp_path / "parent"
        parent_dir.mkdir()
        sibling_dir = tmp_path / "sibling"
        sibling_dir.mkdir()

        # Attempt to access sibling directory via path traversal
        traversal_path = parent_dir / ".." / "sibling"

        assert not dependencies_utils._is_within_directory(str(parent_dir), str(traversal_path))

    def test_is_within_directory_outside_directory(self, tmp_path):
        """Test that a path outside the directory is rejected."""
        dir1 = tmp_path / "dir1"
        dir1.mkdir()
        dir2 = tmp_path / "dir2"
        dir2.mkdir()

        assert not dependencies_utils._is_within_directory(str(dir1), str(dir2))

    def test_is_within_directory_partial_name_match(self, tmp_path):
        """Test that partial directory name matches don't cause false positives."""
        foo_dir = tmp_path / "foo"
        foo_dir.mkdir()
        foobar_dir = tmp_path / "foobar"
        foobar_dir.mkdir()

        assert not dependencies_utils._is_within_directory(str(foo_dir), str(foobar_dir))


class TestSafeExtractTar:
    """Test the _safe_extract_tar function for path traversal prevention."""

    def test_safe_extract_tar_valid_archive(self, tmp_path):
        """Test that a valid tar archive extracts successfully."""
        archive_dir = tmp_path / "archive"
        archive_dir.mkdir()
        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        # Create a valid tar archive
        archive_path = archive_dir / "test.tar.gz"
        test_file = archive_dir / "test.txt"
        test_file.write_text("test content")

        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(test_file, arcname="test.txt")

        # Extract the archive
        with tarfile.open(archive_path, "r:*") as tar:
            dependencies_utils._safe_extract_tar(tar, str(extract_dir))

        # Verify extraction
        extracted_file = extract_dir / "test.txt"
        assert extracted_file.exists()
        assert extracted_file.read_text() == "test content"

    def test_safe_extract_tar_path_traversal_attempt(self, tmp_path):
        """Test that path traversal in tar archives is detected and blocked."""
        archive_dir = tmp_path / "archive"
        archive_dir.mkdir()
        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        # Create a tar archive with path traversal
        archive_path = archive_dir / "malicious.tar.gz"
        test_file = archive_dir / "test.txt"
        test_file.write_text("malicious content")

        with tarfile.open(archive_path, "w:gz") as tar:
            # Add file with path traversal in the name
            tar.add(test_file, arcname="../../../etc/passwd")

        # Attempt to extract should raise RuntimeError
        with tarfile.open(archive_path, "r:*") as tar:
            with pytest.raises(RuntimeError, match="Attempted path traversal"):
                dependencies_utils._safe_extract_tar(tar, str(extract_dir))


class TestSafeExtractZip:
    """Test the _safe_extract_zip function for path traversal prevention."""

    def test_safe_extract_zip_valid_archive(self, tmp_path):
        """Test that a valid zip archive extracts successfully."""
        archive_dir = tmp_path / "archive"
        archive_dir.mkdir()
        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        # Create a valid zip archive
        archive_path = archive_dir / "test.zip"
        test_file = archive_dir / "test.txt"
        test_file.write_text("test content")

        with zipfile.ZipFile(archive_path, "w") as zip_ref:
            zip_ref.write(test_file, arcname="test.txt")

        # Extract the archive
        with zipfile.ZipFile(archive_path, "r") as zip_ref:
            dependencies_utils._safe_extract_zip(zip_ref, str(extract_dir))

        # Verify extraction
        extracted_file = extract_dir / "test.txt"
        assert extracted_file.exists()
        assert extracted_file.read_text() == "test content"

    def test_safe_extract_zip_path_traversal_attempt(self, tmp_path):
        """Test that path traversal in zip archives is detected and blocked."""
        archive_dir = tmp_path / "archive"
        archive_dir.mkdir()
        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        # Create a zip archive with path traversal
        archive_path = archive_dir / "malicious.zip"
        test_file = archive_dir / "test.txt"
        test_file.write_text("malicious content")

        with zipfile.ZipFile(archive_path, "w") as zip_ref:
            # Add file with path traversal in the name
            zip_ref.write(test_file, arcname="../../../etc/passwd")

        # Attempt to extract should raise RuntimeError
        with zipfile.ZipFile(archive_path, "r") as zip_ref:
            with pytest.raises(RuntimeError, match="Attempted path traversal"):
                dependencies_utils._safe_extract_zip(zip_ref, str(extract_dir))


class TestDownloadFile:
    """Test the download_file function."""

    @patch('dependencies_utils.shutil.copyfileobj')
    @patch('dependencies_utils.urllib.request.urlopen')
    def test_download_file_success(self, mock_urlopen, mock_copyfileobj, tmp_path):
        """Test successful file download."""
        dest_path = tmp_path / "downloaded.txt"

        # Mock the response context manager
        mock_response = MagicMock()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = dependencies_utils.download_file("http://example.com/file.txt", dest_path)

        assert result is True
        mock_urlopen.assert_called_once()
        mock_copyfileobj.assert_called_once()

    @patch('dependencies_utils.urllib.request.urlopen')
    def test_download_file_url_error(self, mock_urlopen, tmp_path):
        """Test download failure due to URL error."""
        dest_path = tmp_path / "downloaded.txt"

        # Mock URL error
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("Connection failed")

        result = dependencies_utils.download_file("http://example.com/file.txt", dest_path)

        assert result is False


class TestExtractArchive:
    """Test the extract_archive function."""

    def test_extract_archive_tar_gz(self, tmp_path):
        """Test extracting a tar.gz archive."""
        archive_dir = tmp_path / "archive"
        archive_dir.mkdir()
        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        # Create a tar.gz archive
        archive_path = archive_dir / "test.tar.gz"
        test_file = archive_dir / "test.txt"
        test_file.write_text("test content")

        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(test_file, arcname="test.txt")

        # Extract
        dependencies_utils.extract_archive(str(archive_path), str(extract_dir))

        # Verify
        extracted_file = extract_dir / "test.txt"
        assert extracted_file.exists()
        assert extracted_file.read_text() == "test content"

    def test_extract_archive_zip(self, tmp_path):
        """Test extracting a zip archive."""
        archive_dir = tmp_path / "archive"
        archive_dir.mkdir()
        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        # Create a zip archive
        archive_path = archive_dir / "test.zip"
        test_file = archive_dir / "test.txt"
        test_file.write_text("test content")

        with zipfile.ZipFile(archive_path, "w") as zip_ref:
            zip_ref.write(test_file, arcname="test.txt")

        # Extract
        dependencies_utils.extract_archive(str(archive_path), str(extract_dir))

        # Verify
        extracted_file = extract_dir / "test.txt"
        assert extracted_file.exists()
        assert extracted_file.read_text() == "test content"

    def test_extract_archive_unsupported_format(self, tmp_path):
        """Test that unsupported archive formats raise ValueError."""
        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        with pytest.raises(ValueError, match="Unsupported archive format"):
            dependencies_utils.extract_archive("/path/to/file.rar", str(extract_dir))

    def test_extract_archive_flatpak_not_supported(self, tmp_path):
        """Test that flatpak files raise ValueError with appropriate message."""
        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        with pytest.raises(ValueError, match="Flatpak files are not supported"):
            dependencies_utils.extract_archive("/path/to/file.flatpak", str(extract_dir))


@pytest.mark.skipif(platform.system() != 'Darwin', reason="DMG extraction only works on macOS")
class TestExtractDmg:
    """Test the extract_dmg function (macOS only)."""

    @patch('dependencies_utils.subprocess.run')
    @patch('dependencies_utils.tempfile.mkdtemp')
    def test_extract_dmg_success(self, mock_mkdtemp, mock_subprocess, tmp_path):
        """Test successful DMG extraction."""
        mount_point = tmp_path / "mount"
        mount_point.mkdir()
        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()

        # Create a test file in mount point
        test_file = mount_point / "test.txt"
        test_file.write_text("test content")

        mock_mkdtemp.return_value = str(mount_point)

        # Mock successful mount
        mount_result = Mock()
        mount_result.returncode = 0
        mount_result.stderr = ""

        # Mock successful unmount
        unmount_result = Mock()
        unmount_result.returncode = 0
        unmount_result.stderr = ""

        mock_subprocess.side_effect = [mount_result, unmount_result]

        # Extract
        dependencies_utils.extract_dmg("/path/to/test.dmg", str(extract_dir))

        # Verify file was copied
        extracted_file = extract_dir / "test.txt"
        assert extracted_file.exists()
        assert extracted_file.read_text() == "test content"

    @patch('dependencies_utils.subprocess.run')
    @patch('dependencies_utils.tempfile.mkdtemp')
    def test_extract_dmg_mount_failure(self, mock_mkdtemp, mock_subprocess, tmp_path):
        """Test DMG extraction when mount fails."""
        mount_point = tmp_path / "mount"
        mount_point.mkdir()

        mock_mkdtemp.return_value = str(mount_point)

        # Mock failed mount
        mount_result = Mock()
        mount_result.returncode = 1
        mount_result.stderr = "Mount failed"

        mock_subprocess.return_value = mount_result

        # Extract should raise RuntimeError
        with pytest.raises(RuntimeError, match="Failed to mount DMG"):
            dependencies_utils.extract_dmg("/path/to/test.dmg", str(tmp_path / "extract"))


class TestGetPlatform:
    """Test the get_platform function."""

    @patch('dependencies_utils.platform.system')
    def test_get_platform_darwin(self, mock_system):
        """Test platform detection for macOS."""
        mock_system.return_value = 'Darwin'
        assert dependencies_utils.get_platform() == 'macos'

    @patch('dependencies_utils.platform.system')
    def test_get_platform_windows(self, mock_system):
        """Test platform detection for Windows."""
        mock_system.return_value = 'Windows'
        assert dependencies_utils.get_platform() == 'windows'

    @patch('dependencies_utils.platform.system')
    def test_get_platform_linux(self, mock_system):
        """Test platform detection for Linux."""
        mock_system.return_value = 'Linux'
        assert dependencies_utils.get_platform() == 'linux'

    @patch('dependencies_utils.platform.system')
    def test_get_platform_unsupported(self, mock_system):
        """Test platform detection for unsupported OS."""
        mock_system.return_value = 'FreeBSD'
        with pytest.raises(RuntimeError, match="Unsupported platform"):
            dependencies_utils.get_platform()


class TestCheckSingleDependency:
    """Test the check_single_dependency function."""

    @patch('dependencies_utils.subprocess_utils.run_command')
    def test_check_single_dependency_valid(self, mock_run):
        """Test checking a valid dependency."""
        mock_run.return_value = None  # Successful execution

        valid, error = dependencies_utils.check_single_dependency("ffmpeg")

        assert valid is True
        assert error is None

    @patch('dependencies_utils.subprocess_utils.run_command')
    def test_check_single_dependency_not_found(self, mock_run):
        """Test checking a dependency that doesn't exist."""
        mock_run.side_effect = FileNotFoundError()

        valid, error = dependencies_utils.check_single_dependency("nonexistent")

        assert valid is False
        assert error == "not_found"

    @patch('dependencies_utils.subprocess_utils.run_command')
    def test_check_single_dependency_timeout(self, mock_run):
        """Test checking a dependency that times out."""
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 5)

        valid, error = dependencies_utils.check_single_dependency("slow_command")

        assert valid is False
        assert error == "timeout"

    @patch('dependencies_utils.subprocess_utils.run_command')
    def test_check_single_dependency_invalid(self, mock_run):
        """Test checking a dependency that exists but is invalid."""
        # First call with --version fails, second call with -version also fails
        mock_run.side_effect = [
            subprocess.CalledProcessError(1, "cmd"),
            subprocess.CalledProcessError(1, "cmd")
        ]

        valid, error = dependencies_utils.check_single_dependency("invalid_tool")

        assert valid is False
        assert error == "invalid"
