#!/usr/bin/env python3
"""
Unit tests for convert_videos.py
"""

import os
import unittest
from unittest.mock import patch, MagicMock
import tempfile
from pathlib import Path

# Import the module to test
import convert_videos


class TestGetCodec(unittest.TestCase):
    """Test codec detection functionality."""
    
    @patch('subprocess_utils.run_command')
    def test_get_codec_hevc(self, mock_run):
        """Test detecting HEVC codec."""
        mock_result = MagicMock()
        mock_result.stdout = "hevc"
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        codec = convert_videos.get_codec('/test/file.mp4')
        self.assertEqual(codec, "hevc")
        mock_run.assert_called_once()
    
    @patch('subprocess_utils.run_command')
    def test_get_codec_h264(self, mock_run):
        """Test detecting H.264 codec."""
        mock_result = MagicMock()
        mock_result.stdout = "h264"
        mock_run.return_value = mock_result
        
        codec = convert_videos.get_codec('/test/file.mp4')
        self.assertEqual(codec, "h264")
    
    @patch('subprocess_utils.run_command')
    def test_get_codec_error(self, mock_run):
        """Test handling error when getting codec."""
        mock_run.side_effect = Exception("Command failed")
        
        codec = convert_videos.get_codec('/test/file.mp4')
        self.assertIsNone(codec)


class TestGetDuration(unittest.TestCase):
    """Test video duration extraction."""
    
    @patch('subprocess_utils.run_command')
    def test_get_duration_valid(self, mock_run):
        """Test getting valid duration."""
        mock_result = MagicMock()
        mock_result.stdout = "123.45"
        mock_run.return_value = mock_result
        
        duration = convert_videos.get_duration('/test/file.mp4')
        self.assertEqual(duration, 123)
    
    @patch('subprocess_utils.run_command')
    def test_get_duration_integer(self, mock_run):
        """Test getting integer duration."""
        mock_result = MagicMock()
        mock_result.stdout = "100"
        mock_run.return_value = mock_result
        
        duration = convert_videos.get_duration('/test/file.mp4')
        self.assertEqual(duration, 100)
    
    @patch('subprocess_utils.run_command')
    def test_get_duration_empty(self, mock_run):
        """Test handling empty duration output."""
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_run.return_value = mock_result
        
        duration = convert_videos.get_duration('/test/file.mp4')
        self.assertEqual(duration, 0)
    
    @patch('subprocess_utils.run_command')
    def test_get_duration_error(self, mock_run):
        """Test handling error when getting duration."""
        mock_run.side_effect = Exception("Command failed")
        
        duration = convert_videos.get_duration('/test/file.mp4')
        self.assertEqual(duration, 0)


class TestFindEligibleFiles(unittest.TestCase):
    """Test finding eligible files for conversion."""
    
    @patch('convert_videos.get_codec')
    def test_find_eligible_files_filters_by_codec(self, mock_get_codec):
        """Test that HEVC files are filtered out."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            file1 = Path(temp_dir) / "test1.mp4"
            file2 = Path(temp_dir) / "test2.mp4"
            
            # Create files with minimum size
            file1.write_bytes(b'x' * (1024**3 + 1))  # > 1GB
            file2.write_bytes(b'x' * (1024**3 + 1))
            
            # Mock codec detection - one hevc, one h264
            def codec_side_effect(path, config=None):
                if 'test1' in str(path):
                    return 'hevc'
                return 'h264'
            
            mock_get_codec.side_effect = codec_side_effect
            
            eligible = convert_videos.find_eligible_files(temp_dir)
            
            # Only test2.mp4 (h264) should be eligible
            self.assertEqual(len(eligible), 1)
            self.assertIn('test2.mp4', str(eligible[0]))
    
    @patch('convert_videos.get_codec')
    def test_find_eligible_files_filters_by_size(self, mock_get_codec):
        """Test that files below minimum size are filtered out."""
        mock_get_codec.return_value = 'h264'
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create small and large files
            small_file = Path(temp_dir) / "small.mp4"
            large_file = Path(temp_dir) / "large.mp4"
            
            small_file.write_bytes(b'x' * 1000)  # Small file
            large_file.write_bytes(b'x' * (1024**3 + 1))  # > 1GB
            
            eligible = convert_videos.find_eligible_files(temp_dir)
            
            # Only large file should be eligible
            self.assertEqual(len(eligible), 1)
            self.assertIn('large.mp4', str(eligible[0]))
    
    @patch('convert_videos.get_codec')
    def test_find_eligible_files_sorts_by_size(self, mock_get_codec):
        """Test that files are sorted by size (largest first)."""
        mock_get_codec.return_value = 'h264'
        
        with tempfile.TemporaryDirectory() as temp_dir:
            file1 = Path(temp_dir) / "file1.mp4"
            file2 = Path(temp_dir) / "file2.mp4"
            file3 = Path(temp_dir) / "file3.mp4"
            
            # Create files with different sizes
            file1.write_bytes(b'x' * (1024**3 + 100))
            file2.write_bytes(b'x' * (1024**3 + 300))  # Largest
            file3.write_bytes(b'x' * (1024**3 + 200))
            
            eligible = convert_videos.find_eligible_files(temp_dir)
            
            # Should be sorted by size (largest first)
            self.assertEqual(len(eligible), 3)
            self.assertIn('file2', str(eligible[0]))  # Largest
            self.assertIn('file3', str(eligible[1]))
            self.assertIn('file1', str(eligible[2]))
    
    @patch('convert_videos.get_codec')
    def test_find_eligible_files_skips_failed(self, mock_get_codec):
        """Test that files with .fail extension are skipped."""
        mock_get_codec.return_value = 'h264'
        
        with tempfile.TemporaryDirectory() as temp_dir:
            normal_file = Path(temp_dir) / "normal.mp4"
            failed_file = Path(temp_dir) / "failed.mp4.fail"
            
            normal_file.write_bytes(b'x' * (1024**3 + 1))
            failed_file.write_bytes(b'x' * (1024**3 + 1))
            
            eligible = convert_videos.find_eligible_files(temp_dir)
            
            # Only normal file should be eligible
            self.assertEqual(len(eligible), 1)
            self.assertIn('normal.mp4', str(eligible[0]))


class TestValidateAndFinalize(unittest.TestCase):
    """Test validation and finalization of converted files."""
    
    @patch('convert_videos.get_duration')
    def test_validate_and_finalize_success(self, mock_get_duration):
        """Test successful validation and finalization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "input.mp4"
            temp_output = Path(temp_dir) / "output.mkv.temp"
            final_output = Path(temp_dir) / "output.mkv"
            
            input_file.write_bytes(b'input data')
            temp_output.write_bytes(b'output data')
            
            # Mock duration match
            mock_get_duration.return_value = 100
            
            result = convert_videos.validate_and_finalize(
                input_file, temp_output, final_output, preserve_original=False
            )
            
            self.assertTrue(result)
            self.assertTrue(final_output.exists())
            self.assertFalse(input_file.exists())  # Original removed
            self.assertFalse(temp_output.exists())
    
    @patch('convert_videos.get_duration')
    def test_validate_and_finalize_duration_mismatch(self, mock_get_duration):
        """Test handling duration mismatch."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "input.mp4"
            temp_output = Path(temp_dir) / "output.mkv.temp"
            final_output = Path(temp_dir) / "output.mkv"
            
            input_file.write_bytes(b'input data')
            temp_output.write_bytes(b'output data')
            
            # Mock duration mismatch
            def duration_side_effect(path, config=None):
                if 'input' in str(path):
                    return 100
                return 90  # Mismatch > 1 second
            
            mock_get_duration.side_effect = duration_side_effect
            
            result = convert_videos.validate_and_finalize(
                input_file, temp_output, final_output, preserve_original=False
            )
            
            self.assertFalse(result)
            self.assertTrue(final_output.exists())  # Output still created
            self.assertFalse(input_file.exists())  # Original renamed to .fail


class TestConvertFile(unittest.TestCase):
    """Test file conversion functionality."""
    
    def test_convert_file_dry_run(self):
        """Test dry run mode."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "test.mp4"
            input_file.write_bytes(b'test data')
            
            result = convert_videos.convert_file(input_file, dry_run=True)
            
            self.assertTrue(result)
            # No actual conversion should happen
            converted_files = list(Path(temp_dir).glob("*.converted.*"))
            self.assertEqual(len(converted_files), 0)
    
    def test_convert_file_with_progress_callback(self):
        """Test that progress callback is accepted."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "test.mp4"
            input_file.write_bytes(b'test data')
            
            progress_calls = []
            def progress_callback(percentage):
                progress_calls.append(percentage)
            
            result = convert_videos.convert_file(
                input_file,
                dry_run=True,
                progress_callback=progress_callback
            )
            
            self.assertTrue(result)
    
    def test_convert_file_with_cancellation_check(self):
        """Test that cancellation check is accepted."""
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "test.mp4"
            input_file.write_bytes(b'test data')
            
            def cancellation_check():
                return False
            
            result = convert_videos.convert_file(
                input_file,
                dry_run=True,
                cancellation_check=cancellation_check
            )
            
            self.assertTrue(result)


if __name__ == '__main__':
    unittest.main()
