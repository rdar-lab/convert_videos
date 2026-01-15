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
        
        subprocess_utils.run_command(
            ['test_command'],
            progress_callback=progress_callback,
            progress_pattern=r'Progress: ([0-9.]+)%'
        )
        
        self.assertEqual(len(progress_updates), 3)
        self.assertIn(30.0, progress_updates)
        self.assertIn(60.0, progress_updates)
        self.assertIn(90.0, progress_updates)
    
    @patch('subprocess_utils.subprocess.run')
    def test_run_command_with_timeout(self, mock_run):
        """Test command with timeout parameter."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        subprocess_utils.run_command(['test'], timeout=30)
        
        # Verify timeout was passed
        call_kwargs = mock_run.call_args[1]
        self.assertEqual(call_kwargs['timeout'], 30)
    
    @patch('subprocess_utils.subprocess.Popen')
    def test_run_command_progress_exception_handling(self, mock_popen):
        """Test that progress extraction exceptions are handled."""
        mock_process = MagicMock()
        mock_process.stdout = ['Invalid progress line\n', 'Encoding: 50.0 % complete\n']
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process
        
        progress_updates = []
        def progress_callback(percentage):
            progress_updates.append(percentage)
        
        subprocess_utils.run_command(
            ['test_command'],
            progress_callback=progress_callback
        )
        
        # Should handle invalid line gracefully and still capture valid progress
        self.assertEqual(len(progress_updates), 1)
        self.assertIn(50.0, progress_updates)
    
    @patch('subprocess_utils.subprocess.Popen')
    def test_run_command_process_kill_on_timeout(self, mock_popen):
        """Test that process is killed if termination times out."""
        mock_process = MagicMock()
        mock_process.stdout = ['Line 1\n']
        mock_process.wait.side_effect = [subprocess.TimeoutExpired(['cmd'], 5), None]
        mock_popen.return_value = mock_process
        
        def cancel_immediately():
            return True
        
        with self.assertRaises(InterruptedError):
            subprocess_utils.run_command(
                ['test_command'],
                cancellation_check=cancel_immediately
            )
        
        # Should call terminate, then kill after timeout
        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()
    
    @patch('subprocess_utils.subprocess.run')
    def test_run_command_without_check(self, mock_run):
        """Test command that fails but check=False."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "error"
        mock_run.return_value = mock_result
        
        result = subprocess_utils.run_command(['false'], check=False)
        
        # Should not raise exception
        self.assertEqual(result.returncode, 1)
    
    @patch('subprocess_utils.sys.platform', 'win32')
    @patch('subprocess_utils.sys.frozen', True, create=True)
    @patch('subprocess_utils.subprocess.run')
    def test_run_command_windows_frozen_app(self, mock_run):
        """Test Windows frozen app includes CREATE_NO_WINDOW flag."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        subprocess_utils.run_command(['test'])
        
        # Verify CREATE_NO_WINDOW flag was set
        call_kwargs = mock_run.call_args[1]
        self.assertIn('creationflags', call_kwargs)
        # Should have CREATE_NO_WINDOW flag (0x08000000)
        self.assertTrue(call_kwargs['creationflags'] & 0x08000000)
    
    @patch('subprocess_utils.subprocess.run')
    def test_run_command_captures_text(self, mock_run):
        """Test that command output is captured as text."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "text output"
        mock_run.return_value = mock_result
        
        subprocess_utils.run_command(['test'])
        
        # Verify text mode was set
        call_kwargs = mock_run.call_args[1]
        self.assertTrue(call_kwargs.get('text') or call_kwargs.get('universal_newlines'))
    
    @patch('subprocess_utils.subprocess.Popen')
    def test_run_command_collects_output_lines(self, mock_popen):
        """Test that output lines are collected during progress monitoring."""
        mock_process = MagicMock()
        mock_process.stdout = ['Line 1\n', 'Line 2\n', 'Line 3\n']
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process
        
        def progress_callback(pct):
            pass
        
        result = subprocess_utils.run_command(
            ['test'],
            progress_callback=progress_callback
        )
        
        # Should have captured all output
        self.assertEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()

