#!/usr/bin/env python3
"""
Unit tests for convert_videos_gui.py
"""

import unittest
from unittest.mock import Mock

# Import the GUI module (but don't run GUI components)
try:
    from convert_videos_gui import (
        ConversionResult, VideoConverterGUI, parse_duplicate_directories,
        resolve_duplicate_file_path, grid_treeview_with_scrollbars
    )
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

    def test_grid_treeview_places_horizontal_scrollbar_below_table(self):
        """Treeview and scrollbars share a resizeable grid layout."""
        tree_frame = Mock()
        tree = Mock()
        vertical_scrollbar = Mock()
        horizontal_scrollbar = Mock()

        grid_treeview_with_scrollbars(
            tree_frame, tree, vertical_scrollbar, horizontal_scrollbar
        )

        tree_frame.grid_rowconfigure.assert_called_once_with(0, weight=1)
        tree_frame.grid_columnconfigure.assert_called_once_with(0, weight=1)
        tree.grid.assert_called_once_with(row=0, column=0, sticky='nsew')
        vertical_scrollbar.grid.assert_called_once_with(
            row=0, column=1, sticky='ns'
        )
        horizontal_scrollbar.grid.assert_called_once_with(
            row=1, column=0, sticky='ew'
        )

    def test_parse_duplicate_directories(self):
        """Test parsing multiple GUI directory selections."""
        self.assertEqual(
            parse_duplicate_directories("/local/videos; D:/shared/videos"),
            ["/local/videos", "D:/shared/videos"]
        )

    def test_resolve_duplicate_file_path_with_same_filename(self):
        """Test same filenames in different directories resolve exactly."""
        files = [
            "/local/videos/movie.mp4",
            "/shared/videos/movie.mp4"
        ]
        self.assertEqual(
            resolve_duplicate_file_path(
                files, "/shared/videos/movie.mp4", "movie.mp4"
            ),
            "/shared/videos/movie.mp4"
        )

    def test_resolve_duplicate_file_path_rejects_ambiguous_fallback(self):
        """Test basename fallback does not choose one of same-name files."""
        files = [
            "/local/videos/movie.mp4",
            "/shared/videos/movie.mp4"
        ]
        self.assertIsNone(
            resolve_duplicate_file_path(files, "unknown-row", "movie.mp4")
        )

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

    def test_format_duration(self):
        """Test formatting movie durations."""
        self.assertEqual(VideoConverterGUI.format_duration(65), "01:05")
        self.assertEqual(VideoConverterGUI.format_duration(3665), "1:01:05")
        self.assertEqual(VideoConverterGUI.format_duration(None), "Unknown")
        self.assertEqual(VideoConverterGUI.format_size(int(1.5 * 1024 ** 4)), "1.50 TB")


if __name__ == '__main__':
    unittest.main()
