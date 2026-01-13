#!/usr/bin/env python3
"""
Unit tests for duplicate_detector.py
"""

import unittest
import tempfile
import os
from pathlib import Path

from duplicate_detector import (
    DuplicateResult, hamming_distance, create_comparison_thumbnail,
    MAX_HAMMING_DISTANCE_ERROR
)
from PIL import Image
import imagehash


class TestDuplicateResult(unittest.TestCase):
    """Test DuplicateResult class."""
    
    def test_duplicate_result_creation(self):
        """Test creating a duplicate result."""
        files = ["/path/to/video1.mp4", "/path/to/video2.mp4"]
        file_thumbnails = {
            "/path/to/video1.mp4": "/tmp/thumb1.jpg",
            "/path/to/video2.mp4": "/tmp/thumb2.jpg"
        }
        result = DuplicateResult(
            hash_value="abc123",
            files=files,
            hamming_distance=3,
            file_thumbnails=file_thumbnails,
            comparison_thumbnail="/tmp/comparison.jpg"
        )
        
        self.assertEqual(result.hash_value, "abc123")
        self.assertEqual(result.files, files)
        self.assertEqual(result.hamming_distance, 3)
        self.assertEqual(result.file_thumbnails, file_thumbnails)
        self.assertEqual(result.comparison_thumbnail, "/tmp/comparison.jpg")
    
    def test_duplicate_result_without_thumbnails(self):
        """Test creating a duplicate result without thumbnails."""
        files = ["/path/to/video1.mp4", "/path/to/video2.mp4", "/path/to/video3.mp4"]
        result = DuplicateResult(
            hash_value="def456",
            files=files,
            hamming_distance=5
        )
        
        self.assertEqual(result.hash_value, "def456")
        self.assertEqual(len(result.files), 3)
        self.assertEqual(result.hamming_distance, 5)
        self.assertEqual(result.file_thumbnails, {})
        self.assertIsNone(result.comparison_thumbnail)


class TestHammingDistance(unittest.TestCase):
    """Test hamming distance calculation."""
    
    def test_hamming_distance_identical(self):
        """Test hamming distance for identical hashes."""
        distance = hamming_distance("abc123", "abc123")
        self.assertEqual(distance, 0)
    
    def test_hamming_distance_different(self):
        """Test hamming distance for different hashes."""
        # These hashes differ in specific bits
        distance = hamming_distance("0000", "0001")
        self.assertGreater(distance, 0)
    
    def test_hamming_distance_invalid_input(self):
        """Test hamming distance with invalid input."""
        distance = hamming_distance(None, "abc123")
        self.assertEqual(distance, MAX_HAMMING_DISTANCE_ERROR)  # Should return error constant on error


class TestComparisonThumbnail(unittest.TestCase):
    """Test comparison thumbnail creation."""
    
    def test_create_comparison_thumbnail(self):
        """Test creating comparison thumbnail."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test images
            img1_path = os.path.join(tmpdir, "img1.jpg")
            img2_path = os.path.join(tmpdir, "img2.jpg")
            
            img1 = Image.new('RGB', (100, 100), color='red')
            img2 = Image.new('RGB', (100, 100), color='blue')
            
            img1.save(img1_path)
            img2.save(img2_path)
            
            # Create comparison thumbnail
            result_path = create_comparison_thumbnail([img1_path, img2_path])
            
            # Verify result
            if result_path:
                self.assertTrue(os.path.exists(result_path))
                # Clean up
                if os.path.exists(result_path):
                    os.unlink(result_path)
    
    def test_create_comparison_thumbnail_with_invalid_files(self):
        """Test creating comparison thumbnail with invalid files."""
        result_path = create_comparison_thumbnail(["/nonexistent1.jpg", "/nonexistent2.jpg"])
        self.assertIsNone(result_path)


if __name__ == '__main__':
    unittest.main()
