#!/usr/bin/env python3
"""
Unit tests for convert_videos_gui.py
"""

import unittest
from pathlib import Path

# Import the GUI module (but don't run GUI components)
try:
    from convert_videos_gui import ConversionResult, VideoConverterGUI
    GUI_AVAILABLE = True
except ImportError:
    # tkinter might not be available in headless environments
    GUI_AVAILABLE = False


@unittest.skipIf(not GUI_AVAILABLE, "GUI module not available (tkinter missing)")
class TestConversionResult(unittest.TestCase):
    """Test ConversionResult class."""
    
    def test_successful_conversion(self):
        """Test result for successful conversion."""
        result = ConversionResult(
            file_path="/path/to/video.mp4",
            success=True,
            error_message=None,
            original_size=1000000000,  # 1GB
            new_size=600000000  # 600MB
        )
        
        self.assertEqual(result.file_path, "/path/to/video.mp4")
        self.assertTrue(result.success)
        self.assertIsNone(result.error_message)
        self.assertEqual(result.original_size, 1000000000)
        self.assertEqual(result.new_size, 600000000)
        self.assertEqual(result.space_saved, 400000000)
        self.assertAlmostEqual(result.space_saved_percent, 40.0, places=1)
    
    def test_failed_conversion(self):
        """Test result for failed conversion."""
        result = ConversionResult(
            file_path="/path/to/video.mp4",
            success=False,
            error_message="Conversion failed",
            original_size=1000000000,
            new_size=0
        )
        
        self.assertEqual(result.file_path, "/path/to/video.mp4")
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "Conversion failed")
        self.assertEqual(result.space_saved, 0)
        self.assertEqual(result.space_saved_percent, 0)
    
    def test_zero_original_size(self):
        """Test result with zero original size."""
        result = ConversionResult(
            file_path="/path/to/video.mp4",
            success=True,
            error_message=None,
            original_size=0,
            new_size=0
        )
        
        self.assertEqual(result.space_saved, 0)
        self.assertEqual(result.space_saved_percent, 0)


@unittest.skipIf(not GUI_AVAILABLE, "GUI module not available (tkinter missing)")
class TestVideoConverterGUIHelpers(unittest.TestCase):
    """Test VideoConverterGUI helper methods."""
    
    def test_format_size_bytes(self):
        """Test formatting bytes."""
        self.assertEqual(VideoConverterGUI.format_size(0), "0 B")
        self.assertEqual(VideoConverterGUI.format_size(100), "100.00 B")
        self.assertEqual(VideoConverterGUI.format_size(999), "999.00 B")
    
    def test_format_size_kilobytes(self):
        """Test formatting kilobytes."""
        self.assertEqual(VideoConverterGUI.format_size(1024), "1.00 KB")
        self.assertEqual(VideoConverterGUI.format_size(1536), "1.50 KB")
        self.assertEqual(VideoConverterGUI.format_size(2048), "2.00 KB")
    
    def test_format_size_megabytes(self):
        """Test formatting megabytes."""
        self.assertEqual(VideoConverterGUI.format_size(1024 ** 2), "1.00 MB")
        self.assertEqual(VideoConverterGUI.format_size(int(1.5 * 1024 ** 2)), "1.50 MB")
        self.assertEqual(VideoConverterGUI.format_size(1024 ** 2 * 100), "100.00 MB")
    
    def test_format_size_gigabytes(self):
        """Test formatting gigabytes."""
        self.assertEqual(VideoConverterGUI.format_size(1024 ** 3), "1.00 GB")
        self.assertEqual(VideoConverterGUI.format_size(int(2.5 * 1024 ** 3)), "2.50 GB")
        self.assertEqual(VideoConverterGUI.format_size(1024 ** 3 * 10), "10.00 GB")
    
    def test_format_size_terabytes(self):
        """Test formatting terabytes."""
        self.assertEqual(VideoConverterGUI.format_size(1024 ** 4), "1.00 TB")
        self.assertEqual(VideoConverterGUI.format_size(int(1.5 * 1024 ** 4)), "1.50 TB")


if __name__ == '__main__':
    unittest.main()
