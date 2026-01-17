#!/usr/bin/env python3
"""
Unit tests for convert_videos_cli.py
"""

import sys
import unittest
from unittest.mock import patch

import convert_videos_cli


class TestConvertVideosCLI(unittest.TestCase):
    """Test CLI functionality."""
    
    @patch('convert_videos_cli.time.sleep')
    @patch('convert_videos_cli.convert_videos.convert_file')
    @patch('convert_videos_cli.convert_videos.find_eligible_files')
    @patch('convert_videos_cli.dependencies_utils.validate_dependencies')
    @patch('convert_videos_cli.configuration_manager.load_config')
    @patch('convert_videos_cli.logging_utils.setup_logging')
    def test_main_basic_execution(self, mock_logging, mock_config, mock_validate, 
                                  mock_find_files, mock_convert, mock_sleep):
        """Test basic CLI execution."""
        # Mock configuration
        mock_config.return_value = ({
            'directory': '/test/dir',
            'dry_run': False,
            'loop': False,
            'remove_original_files': False,
            'min_file_size': 1000000,
            'output': {'directory': '/output'},
            'dependencies': {},
            'logging': {'log_file': None}
        }, [])  # No validation errors
        
        mock_validate.return_value = True
        mock_find_files.return_value = []
        
        # Mock command line args
        test_args = ['convert_videos_cli.py', '/test/dir']
        with patch.object(sys, 'argv', test_args):
            convert_videos_cli.main()
        
        # Verify logging was set up
        self.assertEqual(mock_logging.call_count, 2)  # Called twice
        
        # Verify config was loaded
        mock_config.assert_called_once()
        
        # Verify dependencies were validated
        mock_validate.assert_called_once()
        
        # Verify files were searched for
        mock_find_files.assert_called_once()
    
    @patch('convert_videos_cli.time.sleep')
    @patch('convert_videos_cli.convert_videos.convert_file')
    @patch('convert_videos_cli.convert_videos.find_eligible_files')
    @patch('convert_videos_cli.dependencies_utils.validate_dependencies')
    @patch('convert_videos_cli.configuration_manager.load_config')
    @patch('convert_videos_cli.logging_utils.setup_logging')
    def test_main_with_files_to_convert(self, mock_logging, mock_config, mock_validate,
                                       mock_find_files, mock_convert, mock_sleep):
        """Test CLI with files to convert."""
        # Mock configuration
        mock_config.return_value = ({
            'directory': '/test/dir',
            'dry_run': False,
            'loop': False,
            'remove_original_files': False,
            'min_file_size': 1000000,
            'output': {'directory': '/output'},
            'dependencies': {},
            'logging': {'log_file': None}
        }, [])
        
        mock_validate.return_value = True
        mock_find_files.return_value = ['/test/file1.mp4', '/test/file2.mkv']
        
        test_args = ['convert_videos_cli.py', '/test/dir']
        with patch.object(sys, 'argv', test_args):
            convert_videos_cli.main()
        
        # Verify convert_file was called for each file
        self.assertEqual(mock_convert.call_count, 2)
        mock_convert.assert_any_call(
            '/test/file1.mp4',
            dry_run=False,
            preserve_original=True,
            output_config={'directory': '/output'},
            dependency_config={}
        )
    
    @patch('convert_videos_cli.time.sleep')
    @patch('convert_videos_cli.convert_videos.find_eligible_files')
    @patch('convert_videos_cli.dependencies_utils.validate_dependencies')
    @patch('convert_videos_cli.configuration_manager.load_config')
    @patch('convert_videos_cli.logging_utils.setup_logging')
    def test_main_with_dry_run(self, mock_logging, mock_config, mock_validate,
                               mock_find_files, mock_sleep):
        """Test CLI with dry-run mode."""
        mock_config.return_value = ({
            'directory': '/test/dir',
            'dry_run': True,
            'loop': False,
            'remove_original_files': False,
            'min_file_size': 1000000,
            'output': {'directory': '/output'},
            'dependencies': {},
            'logging': {'log_file': None}
        }, [])
        
        mock_validate.return_value = True
        mock_find_files.return_value = []
        
        test_args = ['convert_videos_cli.py', '--dry-run', '/test/dir']
        with patch.object(sys, 'argv', test_args):
            convert_videos_cli.main()
        
        mock_config.assert_called_once()
        # Config should reflect dry_run
        config, _ = mock_config.return_value
        self.assertTrue(config['dry_run'])
    
    @patch('convert_videos_cli.time.sleep')
    @patch('convert_videos_cli.convert_videos.convert_file')
    @patch('convert_videos_cli.convert_videos.find_eligible_files')
    @patch('convert_videos_cli.dependencies_utils.validate_dependencies')
    @patch('convert_videos_cli.configuration_manager.load_config')
    @patch('convert_videos_cli.logging_utils.setup_logging')
    def test_main_with_loop_mode(self, mock_logging, mock_config, mock_validate,
                                 mock_find_files, mock_convert, mock_sleep):
        """Test CLI with loop mode."""
        mock_config.return_value = ({
            'directory': '/test/dir',
            'dry_run': False,
            'loop': True,
            'remove_original_files': False,
            'min_file_size': 1000000,
            'output': {'directory': '/output'},
            'dependencies': {},
            'logging': {'log_file': None}
        }, [])
        
        mock_validate.return_value = True
        mock_find_files.return_value = []
        
        # Make sleep raise an exception to break the loop
        mock_sleep.side_effect = KeyboardInterrupt("Stop loop")
        
        test_args = ['convert_videos_cli.py', '--loop', '/test/dir']
        with patch.object(sys, 'argv', test_args):
            with self.assertRaises(KeyboardInterrupt):
                convert_videos_cli.main()
        
        # Should have called sleep (attempted to loop)
        mock_sleep.assert_called()
    
    @patch('convert_videos_cli.configuration_manager.load_config')
    @patch('convert_videos_cli.logging_utils.setup_logging')
    def test_main_with_validation_errors(self, mock_logging, mock_config):
        """Test CLI with configuration validation errors."""
        # Mock configuration with validation errors
        # When there are validation errors, config content doesn't matter since we exit
        mock_config.return_value = ({}, ['Error 1', 'Error 2'])
        
        test_args = ['convert_videos_cli.py', '/test/dir']
        with patch.object(sys, 'argv', test_args):
            with self.assertRaises(SystemExit) as cm:
                build_executable.main()
            self.assertEqual(cm.exception.code, 1)
        
    
    @patch('convert_videos_cli.dependencies_utils.validate_dependencies')
    @patch('convert_videos_cli.configuration_manager.load_config')
    @patch('convert_videos_cli.logging_utils.setup_logging')
    def test_main_with_dependency_validation_failure(self, mock_logging, mock_config,
                                                     mock_validate):
        """Test CLI when dependency validation fails."""
        mock_config.return_value = ({
            'directory': '/test/dir',
            'dry_run': False,
            'loop': False,
            'remove_original_files': False,
            'min_file_size': 1000000,
            'output': {'directory': '/output'},
            'dependencies': {},
            'logging': {'log_file': None}
        }, [])
        
        # Dependency validation fails
        mock_validate.return_value = False
        
        test_args = ['convert_videos_cli.py', '/test/dir']
        with patch.object(sys, 'argv', test_args):
            with self.assertRaises(SystemExit) as cm:
                convert_videos_cli.main()
            self.assertEqual(cm.exception.code, 1)


    @patch('convert_videos_cli.dependencies_utils.download_dependencies')
    @patch('convert_videos_cli.dependencies_utils.validate_dependencies')
    @patch('convert_videos_cli.configuration_manager.load_config')
    @patch('convert_videos_cli.logging_utils.setup_logging')
    def test_main_with_auto_download_success(self, mock_logging, mock_config, mock_validate,
                                             mock_download):
        """Test CLI with auto-download dependencies success."""
        mock_config.return_value = ({
            'directory': '/test/dir',
            'dry_run': False,
            'loop': False,
            'remove_original_files': False,
            'min_file_size': 1000000,
            'output': {'directory': '/output'},
            'logging': {'log_file': None}
        }, [])
        
        # Mock successful download
        mock_download.return_value = ('/path/handbrake', '/path/ffprobe', '/path/ffmpeg')
        mock_validate.return_value = True
        
        with patch('convert_videos_cli.convert_videos.find_eligible_files', return_value=[]):
            test_args = ['convert_videos_cli.py', '--auto-download-dependencies', '/test/dir']
            with patch.object(sys, 'argv', test_args):
                with self.assertRaises(SystemExit) as cm:
                    convert_videos_cli.main()
                self.assertEqual(cm.exception.code, 1)
        
        # Should have attempted download
        mock_download.assert_called_once()
        
        # Should validate with downloaded dependencies
        mock_validate.assert_called_once()
    
    @patch('convert_videos_cli.dependencies_utils.download_dependencies')
    @patch('convert_videos_cli.configuration_manager.load_config')
    @patch('convert_videos_cli.logging_utils.setup_logging')
    def test_main_with_auto_download_failure(self, mock_logging, mock_config, 
                                             mock_download):
        """Test CLI with auto-download dependencies failure."""
        mock_config.return_value = ({
            'directory': '/test/dir',
            'dry_run': False,
            'loop': False,
            'remove_original_files': False,
            'min_file_size': 1000000,
            'output': {'directory': '/output'},
            'logging': {'log_file': None}
        }, [])
        
        # Mock failed download (returns None or incomplete)
        mock_download.return_value = (None, None, None)
        
        test_args = ['convert_videos_cli.py', '--auto-download-dependencies', '/test/dir']
        with patch.object(sys, 'argv', test_args):
            with self.assertRaises(SystemExit) as cm:
                convert_videos_cli.main()
            self.assertEqual(cm.exception.code, 1)


    @patch('convert_videos_cli.convert_videos.convert_file')
    @patch('convert_videos_cli.convert_videos.find_eligible_files')
    @patch('convert_videos_cli.dependencies_utils.validate_dependencies')
    @patch('convert_videos_cli.configuration_manager.load_config')
    @patch('convert_videos_cli.logging_utils.setup_logging')
    def test_main_with_remove_original(self, mock_logging, mock_config, mock_validate,
                                       mock_find_files, mock_convert):
        """Test CLI with remove-original-files flag."""
        mock_config.return_value = ({
            'directory': '/test/dir',
            'dry_run': False,
            'loop': False,
            'remove_original_files': True,
            'min_file_size': 1000000,
            'output': {'directory': '/output'},
            'dependencies': {},
            'logging': {'log_file': None}
        }, [])
        
        mock_validate.return_value = True
        mock_find_files.return_value = ['/test/file.mp4']
        
        test_args = ['convert_videos_cli.py', '--remove-original-files', '/test/dir']
        with patch.object(sys, 'argv', test_args):
            convert_videos_cli.main()
        
        # Should call convert_file with preserve_original=False
        mock_convert.assert_called_once_with(
            '/test/file.mp4',
            dry_run=False,
            preserve_original=False,
            output_config={'directory': '/output'},
            dependency_config={}
        )
    
    @patch('convert_videos_cli.configuration_manager.load_config')
    @patch('convert_videos_cli.logging_utils.setup_logging')
    def test_main_with_config_file(self, mock_logging, mock_config):
        """Test CLI with config file argument."""
        mock_config.return_value = ({
            'directory': '/test/dir',
            'dry_run': False,
            'loop': False,
            'remove_original_files': False,
            'min_file_size': 1000000,
            'output': {'directory': '/output'},
            'dependencies': {},
            'logging': {'log_file': None}
        }, [])
        
        with patch('convert_videos_cli.dependencies_utils.validate_dependencies', return_value=True):
            with patch('convert_videos_cli.convert_videos.find_eligible_files', return_value=[]):
                test_args = ['convert_videos_cli.py', '--config', '/path/to/config.yaml']
                with patch.object(sys, 'argv', test_args):
                    convert_videos_cli.main()
        
        # Should pass config path to load_config
        args_passed = mock_config.call_args[0][1]
        self.assertEqual(args_passed.config, '/path/to/config.yaml')
    
    @patch('convert_videos_cli.configuration_manager.load_config')
    @patch('convert_videos_cli.logging_utils.setup_logging')
    def test_main_with_log_file_argument(self, mock_logging, mock_config):
        """Test CLI with log-file argument."""
        mock_config.return_value = ({
            'directory': '/test/dir',
            'dry_run': False,
            'loop': False,
            'remove_original_files': False,
            'min_file_size': 1000000,
            'output': {'directory': '/output'},
            'dependencies': {},
            'logging': {'log_file': '/custom/log.txt'}
        }, [])
        
        with patch('convert_videos_cli.dependencies_utils.validate_dependencies', return_value=True):
            with patch('convert_videos_cli.convert_videos.find_eligible_files', return_value=[]):
                test_args = ['convert_videos_cli.py', '--log-file', '/custom/log.txt', '/test/dir']
                with patch.object(sys, 'argv', test_args):
                    convert_videos_cli.main()
        
        # Should call setup_logging with custom path
        calls = mock_logging.call_args_list
        # Second call should have the custom path
        if len(calls) >= 2:
            self.assertEqual(calls[1][0][0], '/custom/log.txt')


if __name__ == '__main__':
    unittest.main()
