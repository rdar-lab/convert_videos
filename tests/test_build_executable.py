#!/usr/bin/env python3
"""
Unit tests for build_executable.py
"""

import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

import build_executable


class TestGetPlatform(unittest.TestCase):
    """Test platform detection."""
    
    @patch('build_executable.platform.system')
    def test_get_platform_macos(self, mock_system):
        """Test macOS platform detection."""
        mock_system.return_value = 'Darwin'
        result = build_executable.get_platform()
        self.assertEqual(result, 'macos')
    
    @patch('build_executable.platform.system')
    def test_get_platform_windows(self, mock_system):
        """Test Windows platform detection."""
        mock_system.return_value = 'Windows'
        result = build_executable.get_platform()
        self.assertEqual(result, 'windows')
    
    @patch('build_executable.platform.system')
    def test_get_platform_linux(self, mock_system):
        """Test Linux platform detection."""
        mock_system.return_value = 'Linux'
        result = build_executable.get_platform()
        self.assertEqual(result, 'linux')
    
    @patch('build_executable.platform.system')
    def test_get_platform_unsupported(self, mock_system):
        """Test unsupported platform raises error."""
        mock_system.return_value = 'FreeBSD'
        with self.assertRaises(RuntimeError) as context:
            build_executable.get_platform()
        self.assertIn('Unsupported platform', str(context.exception))


class TestInstallPyinstaller(unittest.TestCase):
    """Test PyInstaller installation."""
    
    def test_install_pyinstaller_already_installed(self):
        """Test when PyInstaller is already installed."""
        # Create a mock PyInstaller module
        mock_pyinstaller = MagicMock()
        mock_pyinstaller.__version__ = '5.0.0'
        
        with patch.dict('sys.modules', {'PyInstaller': mock_pyinstaller}):
            # Should not raise any errors
            build_executable.install_pyinstaller()
    
    @patch('build_executable.subprocess.check_call')
    @patch('builtins.__import__')
    def test_install_pyinstaller_not_installed(self, mock_import, mock_check_call):
        """Test installing PyInstaller when not present."""
        # Mock import to fail for PyInstaller
        def import_side_effect(name, *args, **kwargs):
            if name == 'PyInstaller':
                raise ImportError("No module named 'PyInstaller'")
            # For all other imports, use the real import
            return __import__(name, *args, **kwargs)
        
        mock_import.side_effect = import_side_effect
        
        build_executable.install_pyinstaller()
        
        # Should have called pip install
        mock_check_call.assert_called_once()
        call_args = mock_check_call.call_args[0][0]
        self.assertIn('pip', call_args)
        self.assertIn('install', call_args)
        self.assertIn('pyinstaller', call_args)


class TestCreateSpecFile(unittest.TestCase):
    """Test spec file creation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.binaries_data = {
            'handbrake': '/path/to/handbrake',
            'ffmpeg': {
                'ffmpeg': '/path/to/ffmpeg',
                'ffprobe': '/path/to/ffprobe'
            }
        }
    
    @patch('builtins.open', new_callable=mock_open)
    def test_create_spec_file_basic(self, mock_file):
        """Test basic spec file creation."""
        spec_file = build_executable.create_spec_file(
            'linux',
            self.binaries_data,
            script_name='test.py',
            exe_name='test_exe'
        )
        
        self.assertIn('test_exe.spec', str(spec_file))
        
        # Verify file was written
        mock_file.assert_called_once_with(spec_file, 'w')
        
        # Get the content that was written
        handle = mock_file()
        written_content = ''.join(call[0][0] for call in handle.write.call_args_list)
        
        # Check for essential elements
        self.assertIn('test.py', written_content)
        self.assertIn("name='test_exe'", written_content)
        self.assertIn('/path/to/handbrake', written_content)
        self.assertIn('/path/to/ffmpeg', written_content)
        self.assertIn('/path/to/ffprobe', written_content)
    
    @patch('builtins.open', new_callable=mock_open)
    def test_create_spec_file_console_true(self, mock_file):
        """Test spec file creation with console window."""
        build_executable.create_spec_file(
            'windows',
            self.binaries_data,
            console=True
        )
        
        handle = mock_file()
        written_content = ''.join(call[0][0] for call in handle.write.call_args_list)
        self.assertIn('console=True', written_content)
    
    @patch('builtins.open', new_callable=mock_open)
    def test_create_spec_file_console_false(self, mock_file):
        """Test spec file creation without console window."""
        build_executable.create_spec_file(
            'windows',
            self.binaries_data,
            console=False
        )
        
        handle = mock_file()
        written_content = ''.join(call[0][0] for call in handle.write.call_args_list)
        self.assertIn('console=False', written_content)
    
    @patch('builtins.open', new_callable=mock_open)
    def test_create_spec_file_no_binaries(self, mock_file):
        """Test spec file creation without binaries."""
        spec_file = build_executable.create_spec_file(
            'linux',
            {},
            script_name='test.py'
        )
        
        # Should still create spec file
        self.assertIsNotNone(spec_file)
    
    @patch('builtins.open', new_callable=mock_open)
    def test_create_spec_file_macos(self, mock_file):
        """Test spec file for macOS platform."""
        build_executable.create_spec_file(
            'macos',
            self.binaries_data
        )
        
        handle = mock_file()
        written_content = ''.join(call[0][0] for call in handle.write.call_args_list)
        # Should have icon configuration for macOS
        self.assertIn('icon=', written_content)


class TestBuildWithPyinstaller(unittest.TestCase):
    """Test PyInstaller build execution."""
    
    @patch('build_executable.subprocess.check_call')
    def test_build_with_pyinstaller_success(self, mock_check_call):
        """Test successful PyInstaller build."""
        result = build_executable.build_with_pyinstaller(Path('test.spec'))
        
        self.assertTrue(result)
        mock_check_call.assert_called_once()
        
        # Check command arguments
        call_args = mock_check_call.call_args[0][0]
        self.assertIn('PyInstaller', call_args)
        self.assertIn('--clean', call_args)
        self.assertIn('--noconfirm', call_args)
    
    @patch('build_executable.subprocess.check_call')
    def test_build_with_pyinstaller_failure(self, mock_check_call):
        """Test failed PyInstaller build."""
        import subprocess
        mock_check_call.side_effect = subprocess.CalledProcessError(1, ['pyinstaller'])
        
        result = build_executable.build_with_pyinstaller(Path('test.spec'))
        
        self.assertFalse(result)


class TestCreateDistributionPackage(unittest.TestCase):
    """Test distribution package creation."""
    
    @patch('build_executable.shutil.make_archive')
    @patch('build_executable.shutil.copy2')
    @patch('build_executable.Path')
    def test_create_distribution_package_windows(self, mock_path_class, mock_copy, mock_archive):
        """Test creating distribution package for Windows."""
        # Create mock Path instances
        mock_dist = MagicMock()
        mock_cli_exe = MagicMock()
        mock_gui_exe = MagicMock()
        mock_package_dir = MagicMock()
        
        # CLI exe exists
        mock_cli_exe.exists.return_value = True
        # GUI exe exists
        mock_gui_exe.exists.return_value = True
        
        # Mock Path() calls to return appropriate mocks
        def path_side_effect(arg):
            if arg == 'dist':
                return mock_dist
            return MagicMock()
        
        mock_path_class.side_effect = path_side_effect
        
        # Mock the / operator for Path
        mock_dist.__truediv__ = MagicMock(side_effect=lambda x: mock_cli_exe if 'cli' in x else 
                                          (mock_gui_exe if 'gui' in x else mock_package_dir))
        
        build_executable.create_distribution_package('windows')
        
        # Should create zip archive for Windows
        mock_archive.assert_called_once()
        call_args = mock_archive.call_args[0]
        self.assertIn('zip', call_args)
    
    @patch('build_executable.shutil.make_archive')
    @patch('build_executable.shutil.copy2')
    @patch('build_executable.Path')
    def test_create_distribution_package_linux(self, mock_path_class, mock_copy, mock_archive):
        """Test creating distribution package for Linux."""
        # Create mock Path instances
        mock_dist = MagicMock()
        mock_cli_exe = MagicMock()
        mock_package_dir = MagicMock()
        
        # CLI exe exists
        mock_cli_exe.exists.return_value = True
        
        # Mock Path() calls
        def path_side_effect(arg):
            if arg == 'dist':
                return mock_dist
            return MagicMock()
        
        mock_path_class.side_effect = path_side_effect
        
        # Mock the / operator
        mock_dist.__truediv__ = MagicMock(side_effect=lambda x: mock_cli_exe if 'cli' in x else mock_package_dir)
        
        build_executable.create_distribution_package('linux')
        
        # Should create tar.gz archive for Linux
        mock_archive.assert_called_once()
        call_args = mock_archive.call_args[0]
        self.assertIn('gztar', call_args)
    
    @patch('build_executable.Path.exists')
    def test_create_distribution_package_no_cli_exe(self, mock_exists):
        """Test error when CLI executable is missing."""
        mock_exists.return_value = False

        with self.assertRaises(SystemExit) as cm:        
            result = build_executable.create_distribution_package('linux')

        self.assertEqual(cm.exception.code, 1)
        mock_exit.assert_called_with(1)


class TestMain(unittest.TestCase):
    """Test main build function."""
    
    @patch('build_executable.create_distribution_package')
    @patch('build_executable.build_with_pyinstaller')
    @patch('build_executable.create_spec_file')
    @patch('build_executable.dependencies_utils.download_dependencies')
    @patch('build_executable.Path.mkdir')
    @patch('build_executable.install_pyinstaller')
    @patch('build_executable.get_platform')
    @patch('sys.argv', ['build_executable.py'])
    def test_main_success(self, mock_get_platform, mock_install, mock_mkdir,
                         mock_download, mock_create_spec, mock_build, mock_package):
        """Test successful build execution."""
        mock_get_platform.return_value = 'linux'
        mock_download.return_value = ('/handbrake', '/ffprobe', '/ffmpeg')
        mock_build.return_value = True
        
        build_executable.main()
        
        # Should install PyInstaller
        mock_install.assert_called_once()
        
        # Should download dependencies
        mock_download.assert_called_once()
        
        # Should create spec files (CLI and GUI)
        self.assertEqual(mock_create_spec.call_count, 2)
        
        # Should build both versions
        self.assertEqual(mock_build.call_count, 2)
        
        # Should create distribution package
        mock_package.assert_called_once()
    
    @patch('build_executable.dependencies_utils.download_dependencies')
    @patch('build_executable.Path.mkdir')
    @patch('build_executable.install_pyinstaller')
    @patch('build_executable.get_platform')
    @patch('sys.argv', ['build_executable.py'])
    def test_main_no_handbrake(self, mock_get_platform, mock_install, mock_mkdir,
                               mock_download):
        """Test failure when HandBrake is not available."""
        mock_get_platform.return_value = 'linux'
        mock_download.return_value = (None, '/ffprobe', '/ffmpeg')
        
        with self.assertRaises(SystemExit) as cm:
            build_executable.main()
        self.assertEqual(cm.exception.code, 1)
    
    @patch('build_executable.dependencies_utils.download_dependencies')
    @patch('build_executable.Path.mkdir')
    @patch('build_executable.install_pyinstaller')
    @patch('build_executable.get_platform')
    @patch('sys.argv', ['build_executable.py'])
    def test_main_no_ffmpeg(self, mock_get_platform, mock_install, mock_mkdir,
                           mock_download):
        """Test failure when ffmpeg is not available."""
        mock_get_platform.return_value = 'linux'
        mock_download.return_value = ('/handbrake', None, None)
        
        with self.assertRaises(SystemExit) as cm:
            build_executable.main()
        self.assertEqual(cm.exception.code, 1)
        
    
    @patch('build_executable.build_with_pyinstaller')
    @patch('build_executable.create_spec_file')
    @patch('build_executable.dependencies_utils.download_dependencies')
    @patch('build_executable.Path.mkdir')
    @patch('build_executable.install_pyinstaller')
    @patch('build_executable.get_platform')
    @patch('sys.argv', ['build_executable.py'])
    def test_main_cli_build_failure(self, mock_get_platform, mock_install, mock_mkdir,
                                    mock_download, mock_create_spec, mock_build):
        """Test failure when CLI build fails."""
        mock_get_platform.return_value = 'linux'
        mock_download.return_value = ('/handbrake', '/ffprobe', '/ffmpeg')
        mock_build.return_value = False  # Build fails
        
        with self.assertRaises(SystemExit) as cm:
            build_executable.main()
        self.assertEqual(cm.exception.code, 1)
    
    @patch('build_executable.create_distribution_package')
    @patch('build_executable.build_with_pyinstaller')
    @patch('build_executable.create_spec_file')
    @patch('build_executable.dependencies_utils.download_dependencies')
    @patch('build_executable.Path.mkdir')
    @patch('build_executable.install_pyinstaller')
    @patch('build_executable.get_platform')
    @patch('sys.argv', ['build_executable.py', '--platform', 'macos'])
    def test_main_with_platform_arg(self, mock_get_platform, mock_install, mock_mkdir,
                                    mock_download, mock_create_spec, mock_build, mock_package):
        """Test main with explicit platform argument."""
        mock_download.return_value = ('/handbrake', '/ffprobe', '/ffmpeg')
        mock_build.return_value = True
        
        build_executable.main()
        
        # Should not call get_platform since platform was specified
        mock_get_platform.assert_not_called()


if __name__ == '__main__':
    unittest.main()
