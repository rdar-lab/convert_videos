#!/usr/bin/env python3
"""
Unit tests for logging_utils.py
"""

import logging
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import logging_utils


class TestSetupLogging(unittest.TestCase):
    """Test logging setup functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Clear any existing handlers
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
    
    def tearDown(self):
        """Clean up after tests."""
        # Clear handlers again and close file handles to avoid Windows file locking issues
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            handler.close()
            root_logger.removeHandler(handler)
        root_logger.handlers.clear()
    
    def test_setup_logging_default_path(self):
        """Test logging setup with default temp directory path."""
        log_path = logging_utils.setup_logging()
        
        # Should return a path in temp directory
        self.assertIsNotNone(log_path)
        self.assertIn(tempfile.gettempdir(), log_path)
        self.assertIn('convert_videos.log', log_path)
        
        # Should have handlers set up
        root_logger = logging.getLogger()
        self.assertGreater(len(root_logger.handlers), 0)
        
        # Should have both console and file handlers
        handler_types = [type(h).__name__ for h in root_logger.handlers]
        self.assertIn('StreamHandler', handler_types)
        self.assertIn('RotatingFileHandler', handler_types)
    
    def test_setup_logging_custom_path(self):
        """Test logging setup with custom log file path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            custom_log_path = os.path.join(temp_dir, 'custom.log')
            log_path = logging_utils.setup_logging(custom_log_path)
            
            self.assertEqual(log_path, custom_log_path)
            self.assertTrue(os.path.exists(custom_log_path))
            
            # Close handlers to release file locks (Windows compatibility)
            root_logger = logging.getLogger()
            for handler in root_logger.handlers[:]:
                handler.close()
                root_logger.removeHandler(handler)
    
    def test_setup_logging_creates_directory(self):
        """Test that logging setup creates missing directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            nested_path = os.path.join(temp_dir, 'subdir', 'logs', 'app.log')
            log_path = logging_utils.setup_logging(nested_path)
            
            self.assertEqual(log_path, nested_path)
            self.assertTrue(os.path.exists(nested_path))
            self.assertTrue(os.path.isdir(os.path.dirname(nested_path)))
            
            # Close handlers to release file locks (Windows compatibility)
            root_logger = logging.getLogger()
            for handler in root_logger.handlers[:]:
                handler.close()
                root_logger.removeHandler(handler)
    
    def test_setup_logging_invalid_path_fallback(self):
        """Test fallback to temp directory when log path is invalid."""
        # Use an invalid path that doesn't exist on any platform
        # Windows: uses drive letters, Unix: uses /
        import sys
        if sys.platform == 'win32':
            invalid_path = 'Z:\\impossible\\nonexistent\\path\\test.log'
        else:
            invalid_path = '/root/impossible/path/test.log'
        
        with patch('sys.stderr', new=MagicMock()):
            log_path = logging_utils.setup_logging(invalid_path)
        
        # Should fall back to temp directory or None
        if log_path:
            self.assertIn(tempfile.gettempdir(), log_path)
    
    def test_setup_logging_console_only(self):
        """Test logging works with console only when file creation fails."""
        # Mock Path.mkdir to always raise PermissionError
        with patch('logging_utils.Path.mkdir', side_effect=PermissionError("No permission")):
            with patch('sys.stderr', new=MagicMock()):
                logging_utils.setup_logging('/invalid/path.log')
        
        # Should return None for console-only mode
        # But logging should still work
        root_logger = logging.getLogger()
        self.assertGreater(len(root_logger.handlers), 0)
    
    def test_setup_logging_clears_existing_handlers(self):
        """Test that setup_logging clears existing handlers."""
        # Add a dummy handler
        root_logger = logging.getLogger()
        dummy_handler = logging.StreamHandler()
        root_logger.addHandler(dummy_handler)
        
        initial_count = len(root_logger.handlers)
        self.assertGreater(initial_count, 0)
        
        # Setup logging should clear and recreate handlers
        logging_utils.setup_logging()
        
        # Should have new handlers, old one should be gone
        self.assertNotIn(dummy_handler, root_logger.handlers)
    
    def test_setup_logging_formatter(self):
        """Test that handlers have correct formatter."""
        logging_utils.setup_logging()
        
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            formatter = handler.formatter
            self.assertIsNotNone(formatter)
            # Check formatter has expected format elements
            self.assertIn('%(asctime)s', formatter._fmt)
            self.assertIn('%(levelname)s', formatter._fmt)
            self.assertIn('%(message)s', formatter._fmt)
    
    def test_setup_logging_level(self):
        """Test that logging level is set correctly."""
        logging_utils.setup_logging()
        
        root_logger = logging.getLogger()
        self.assertEqual(root_logger.level, logging.INFO)
        
        for handler in root_logger.handlers:
            self.assertEqual(handler.level, logging.INFO)
    
    def test_setup_logging_file_handler_rotation(self):
        """Test that file handler has rotation configured."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = os.path.join(temp_dir, 'test.log')
            logging_utils.setup_logging(log_path)
            
            root_logger = logging.getLogger()
            
            # Find the RotatingFileHandler
            file_handler = None
            for handler in root_logger.handlers:
                if isinstance(handler, logging.handlers.RotatingFileHandler):
                    file_handler = handler
                    break
            
            self.assertIsNotNone(file_handler)
            # Check rotation settings (10MB max, 5 backups)
            self.assertEqual(file_handler.maxBytes, 10 * 1024 * 1024)
            self.assertEqual(file_handler.backupCount, 5)
            
            # Close handlers to release file locks (Windows compatibility)
            for handler in root_logger.handlers[:]:
                handler.close()
                root_logger.removeHandler(handler)
    
    def test_setup_logging_writes_to_file(self):
        """Test that logging actually writes to the file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = os.path.join(temp_dir, 'test.log')
            logging_utils.setup_logging(log_path)
            
            # Write a test log message
            logger = logging.getLogger()
            test_message = "Test log message 12345"
            logger.info(test_message)
            
            # Flush handlers
            for handler in logger.handlers:
                handler.flush()
            
            # Check file contains the message
            self.assertTrue(os.path.exists(log_path))
            with open(log_path, 'r') as f:
                content = f.read()
                self.assertIn(test_message, content)
            
            # Close handlers to release file locks (Windows compatibility)
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)
    
    def test_setup_logging_file_permission_error(self):
        """Test handling of permission errors when creating log file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = os.path.join(temp_dir, 'test.log')
            
            # First create the directory
            logging_utils.setup_logging(log_path)
            
            # Now mock the RotatingFileHandler to raise PermissionError
            with patch('logging_utils.logging.handlers.RotatingFileHandler', 
                      side_effect=PermissionError("Permission denied")):
                with patch('sys.stderr', new=MagicMock()):
                    logging_utils.setup_logging(log_path)
            
            # Should return None and still have console handler
            root_logger = logging.getLogger()
            self.assertGreater(len(root_logger.handlers), 0)


if __name__ == '__main__':
    unittest.main()
