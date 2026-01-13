#!/usr/bin/env python3
"""
Unit tests for convert_videos_gui.py
"""

import unittest
import tempfile
import os
from pathlib import Path

# Import the GUI module (but don't run GUI components)
try:
    from convert_videos_gui import ConversionResult, DuplicateResult, VideoConverterGUI, DUPLICATE_DETECTION_AVAILABLE
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


@unittest.skipIf(not GUI_AVAILABLE, "GUI module not available (tkinter missing)")
class TestDuplicateResult(unittest.TestCase):
    """Test DuplicateResult class."""
    
    def test_duplicate_result_creation(self):
        """Test creating a duplicate result."""
        files = ["/path/to/video1.mp4", "/path/to/video2.mp4"]
        result = DuplicateResult(
            hash_value="abc123",
            files=files,
            hamming_distance=3,
            thumbnail_path="/path/to/thumb.jpg"
        )
        
        self.assertEqual(result.hash_value, "abc123")
        self.assertEqual(result.files, files)
        self.assertEqual(result.hamming_distance, 3)
        self.assertEqual(result.thumbnail_path, "/path/to/thumb.jpg")
    
    def test_duplicate_result_without_thumbnail(self):
        """Test creating a duplicate result without thumbnail."""
        files = ["/path/to/video1.mp4", "/path/to/video2.mp4", "/path/to/video3.mp4"]
        result = DuplicateResult(
            hash_value="def456",
            files=files,
            hamming_distance=5,
            thumbnail_path=None
        )
        
        self.assertEqual(result.hash_value, "def456")
        self.assertEqual(len(result.files), 3)
        self.assertEqual(result.hamming_distance, 5)
        self.assertIsNone(result.thumbnail_path)


@unittest.skipIf(not GUI_AVAILABLE or not DUPLICATE_DETECTION_AVAILABLE, 
                 "GUI or duplicate detection not available")
class TestDuplicateDetectionHelpers(unittest.TestCase):
    """Test duplicate detection helper methods."""
    
    def setUp(self):
        """Set up test fixtures."""
        import tkinter as tk
        self.root = tk.Tk()
        self.root.withdraw()  # Hide window
        try:
            from convert_videos_gui import VideoConverterGUI
            self.gui = VideoConverterGUI(self.root)
        except Exception as e:
            self.skipTest(f"Cannot initialize GUI: {e}")
    
    def tearDown(self):
        """Clean up test fixtures."""
        try:
            self.root.destroy()
        except Exception:
            pass
    
    def test_hamming_distance_identical(self):
        """Test hamming distance for identical hashes."""
        distance = self.gui._hamming_distance("abc123", "abc123")
        self.assertEqual(distance, 0)
    
    def test_hamming_distance_different(self):
        """Test hamming distance for different hashes."""
        # These hashes differ in specific bits
        distance = self.gui._hamming_distance("0000", "0001")
        self.assertGreater(distance, 0)
    
    def test_hamming_distance_invalid_input(self):
        """Test hamming distance with invalid input."""
        distance = self.gui._hamming_distance(None, "abc123")
        self.assertEqual(distance, 999)  # Should return large distance on error
    
    def test_create_comparison_thumbnail(self):
        """Test creating comparison thumbnail."""
        # Create two temporary test images
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("PIL not available")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test images
            img1_path = os.path.join(tmpdir, "img1.jpg")
            img2_path = os.path.join(tmpdir, "img2.jpg")
            
            img1 = Image.new('RGB', (100, 100), color='red')
            img2 = Image.new('RGB', (100, 100), color='blue')
            
            img1.save(img1_path)
            img2.save(img2_path)
            
            # Create comparison thumbnail
            result_path = self.gui._create_comparison_thumbnail([img1_path, img2_path])
            
            # Verify result
            if result_path:
                self.assertTrue(os.path.exists(result_path))
                # Clean up
                if os.path.exists(result_path):
                    os.unlink(result_path)
    
    def test_create_comparison_thumbnail_with_invalid_files(self):
        """Test creating comparison thumbnail with invalid files."""
        result_path = self.gui._create_comparison_thumbnail(["/nonexistent1.jpg", "/nonexistent2.jpg"])
        self.assertIsNone(result_path)


if __name__ == '__main__':
    unittest.main()
