#!/usr/bin/env python3
"""
Unit tests for subprocess_utils.py
"""

import unittest
from unittest.mock import patch, MagicMock
import subprocess

# Import the module to test
import subprocess_utils


class TestRunCommand(unittest.TestCase):
    """Test run_command functionality."""
    
    @patch('subprocess_utils.subprocess.run')
    def test_run_command_simple(self, mock_run):
        """Test simple command execution without progress."""
        # Mock successful command execution
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "test output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        result = subprocess_utils.run_command(['echo', 'test'], check=True)
        
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "test output")
        mock_run.assert_called_once()
    
    @patch('subprocess_utils.subprocess.Popen')
    def test_run_command_with_progress_callback(self, mock_popen):
        """Test command execution with progress callback."""
        # Mock process that outputs progress
        mock_process = MagicMock()
        mock_process.stdout = ['Encoding: task 1, 25.0 % complete\n', 
                               'Encoding: task 1, 50.0 % complete\n',
                               'Encoding: task 1, 100.0 % complete\n']
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process
        
        progress_updates = []
        def progress_callback(percentage):
            progress_updates.append(percentage)
        
        result = subprocess_utils.run_command(
            ['test_command'],
            progress_callback=progress_callback
        )
        
        self.assertEqual(result.returncode, 0)
        self.assertEqual(len(progress_updates), 3)
        self.assertIn(25.0, progress_updates)
        self.assertIn(50.0, progress_updates)
        self.assertIn(100.0, progress_updates)
    
    @patch('subprocess_utils.subprocess.Popen')
    def test_run_command_with_cancellation(self, mock_popen):
        """Test command execution with cancellation."""
        # Mock process
        mock_process = MagicMock()
        mock_process.stdout = ['Line 1\n', 'Line 2\n']
        mock_process.wait.return_value = 0
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process
        
        call_count = [0]
        def cancellation_check():
            call_count[0] += 1
            return call_count[0] > 1  # Cancel after second line
        
        with self.assertRaises(InterruptedError):
            subprocess_utils.run_command(
                ['test_command'],
                cancellation_check=cancellation_check
            )
        
        # Should have terminated the process
        mock_process.terminate.assert_called_once()
    
    @patch('subprocess_utils.subprocess.run')
    def test_run_command_with_error(self, mock_run):
        """Test command that returns error code."""
        # Mock failed command execution
        mock_run.side_effect = subprocess.CalledProcessError(
            1, ['false'], output="error output", stderr="error details"
        )
        
        with self.assertRaises(subprocess.CalledProcessError):
            subprocess_utils.run_command(['false'], check=True)
    
    @patch('subprocess_utils.subprocess.Popen')
    def test_run_command_custom_progress_pattern(self, mock_popen):
        """Test custom progress pattern."""
        # Mock process with different progress format
        mock_process = MagicMock()
        mock_process.stdout = ['Progress: 30%\n', 'Progress: 60%\n', 'Progress: 90%\n']
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process
        
        progress_updates = []
        def progress_callback(percentage):
            progress_updates.append(percentage)
        
        result = subprocess_utils.run_command(
            ['test_command'],
            progress_callback=progress_callback,
            progress_pattern=r'Progress: ([0-9.]+)%'
        )
        
        self.assertEqual(len(progress_updates), 3)
        self.assertIn(30.0, progress_updates)
        self.assertIn(60.0, progress_updates)
        self.assertIn(90.0, progress_updates)


if __name__ == '__main__':
    unittest.main()
