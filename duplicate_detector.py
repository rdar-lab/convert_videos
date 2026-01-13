#!/usr/bin/env python3
"""
Video duplicate detection module using perceptual hashing.
"""

import os
import subprocess
import tempfile
import logging
from pathlib import Path

import imagehash
from PIL import Image

logger = logging.getLogger(__name__)

# Constants
MAX_HAMMING_DISTANCE_ERROR = 999  # Return value when hamming distance calculation fails


class DuplicateResult:
    """Represents a group of duplicate videos."""
    def __init__(self, hash_value, files, hamming_distance, file_thumbnails=None, comparison_thumbnail=None):
        self.hash_value = hash_value
        self.files = files  # List of file paths
        self.hamming_distance = hamming_distance  # Max distance within the group
        self.file_thumbnails = file_thumbnails or {}  # Dict mapping file path to thumbnail path
        self.comparison_thumbnail = comparison_thumbnail  # Path to side-by-side comparison thumbnail


def hamming_distance(hash1, hash2):
    """Calculate hamming distance between two hash strings.
    
    Args:
        hash1: First hash string
        hash2: Second hash string
        
    Returns:
        int: Number of differing bits, or MAX_HAMMING_DISTANCE_ERROR on error
    """
    try:
        return bin(int(str(hash1), 16) ^ int(str(hash2), 16)).count("1")
    except (ValueError, TypeError):
        return MAX_HAMMING_DISTANCE_ERROR  # Return large distance on error


def create_comparison_thumbnail(thumbnail_paths):
    """Create a side-by-side comparison thumbnail from two images.
    
    Args:
        thumbnail_paths: List of at least 2 image file paths
        
    Returns:
        str: Path to combined thumbnail, or None on error
    """
    try:
        img1 = Image.open(thumbnail_paths[0])
        img2 = Image.open(thumbnail_paths[1])
        
        # Resize to reasonable size
        max_height = 200
        img1.thumbnail((400, max_height))
        img2.thumbnail((400, max_height))
        
        # Create side-by-side image
        total_width = img1.width + img2.width
        max_height = max(img1.height, img2.height)
        
        combined = Image.new('RGB', (total_width, max_height))
        combined.paste(img1, (0, 0))
        combined.paste(img2, (img1.width, 0))
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_combined:
            combined.save(temp_combined, format='JPEG')
            return temp_combined.name
    
    except Exception as e:
        logger.error(f"Error creating comparison thumbnail: {repr(e)}")
        return None


def scan_for_duplicates(directory, max_distance, ffmpeg_path, ffprobe_path, progress_callback=None):
    """Scan directory for duplicate videos.
    
    Args:
        directory: Path to directory to scan
        max_distance: Maximum hamming distance for duplicates
        ffmpeg_path: Path to ffmpeg executable
        ffprobe_path: Path to ffprobe executable
        progress_callback: Optional callback function for progress updates
        
    Returns:
        list: List of DuplicateResult objects representing duplicate groups
        
    Raises:
        Exception: If scanning fails
    """
    # Find video files
    video_extensions = ('.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm')
    video_files = []
    
    if progress_callback:
        progress_callback('Finding video files...')
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(video_extensions):
                video_files.append(Path(root) / file)
    
    if not video_files:
        raise Exception('No video files found in directory')
    
    if progress_callback:
        progress_callback(f'Found {len(video_files)} videos. Extracting frames and calculating hashes...')
    
    # Extract middle frames and calculate hashes
    video_hashes = []
    # Create a temp directory for storing thumbnails
    temp_dir = Path(tempfile.mkdtemp(prefix='video_dup_'))
    
    for i, video_file in enumerate(video_files):
        try:
            # Get video duration
            duration_cmd = [
                ffprobe_path, '-v', 'error', '-show_entries', 
                'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1',
                str(video_file)
            ]
            result = subprocess.run(duration_cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0 or not result.stdout.strip():
                logger.warning(f"Could not determine duration for {video_file}")
                continue
            
            duration = float(result.stdout.strip())
            midpoint = duration / 2
            
            # Extract middle frame to temp directory with unique name
            temp_frame_path = temp_dir / f"{Path(video_file).stem}_{i}.jpg"
            
            extract_cmd = [
                ffmpeg_path, '-ss', str(midpoint), '-i', str(video_file),
                '-vframes', '1', '-q:v', '2', '-f', 'image2',
                str(temp_frame_path), '-y'
            ]
            subprocess.run(extract_cmd, capture_output=True, timeout=30, check=True)
            
            # Calculate perceptual hash
            if os.path.exists(temp_frame_path) and os.path.getsize(temp_frame_path) > 0:
                img = Image.open(temp_frame_path)
                hash_value = imagehash.phash(img)
                video_hashes.append((str(hash_value), video_file, str(temp_frame_path)))
            else:
                logger.warning(f"Failed to extract frame from {video_file}")
                if os.path.exists(temp_frame_path):
                    os.unlink(temp_frame_path)
            
            # Update progress
            if (i + 1) % 5 == 0 or i == len(video_files) - 1:
                if progress_callback:
                    progress_callback(f'Processing {i + 1}/{len(video_files)} videos...')
        
        except Exception as e:
            logger.error(f"Error processing {video_file}: {repr(e)}")
            continue
    
    if not video_hashes:
        raise Exception('No videos could be processed')
    
    if progress_callback:
        progress_callback(f'Comparing {len(video_hashes)} video hashes...')
    
    # Compare all pairs and find duplicates
    duplicate_groups = []
    processed_files = set()
    
    for i, (h1, f1, thumb1) in enumerate(video_hashes):
        if f1 in processed_files:
            continue
        
        group_files = [f1]
        group_thumbs = [thumb1]
        max_dist_in_group = 0
        
        for h2, f2, thumb2 in video_hashes[i+1:]:
            if f2 in processed_files:
                continue
            
            # Calculate hamming distance
            dist = hamming_distance(h1, h2)
            if dist <= max_distance:
                group_files.append(f2)
                group_thumbs.append(thumb2)
                max_dist_in_group = max(max_dist_in_group, dist)
                processed_files.add(f2)
        
        if len(group_files) > 1:
            # Create dict mapping files to their thumbnail paths
            file_thumbnails = {}
            for file, thumb in zip(group_files, group_thumbs):
                file_thumbnails[str(file)] = thumb
            
            # Create combined thumbnail if multiple files
            comparison_thumbnail = None
            try:
                if len(group_thumbs) >= 2:
                    comparison_thumbnail = create_comparison_thumbnail(group_thumbs[:2])
            except Exception as e:
                logger.error(f"Failed to create comparison thumbnail: {repr(e)}")
            
            duplicate_groups.append(DuplicateResult(
                hash_value=h1,
                files=group_files,
                hamming_distance=max_dist_in_group,
                file_thumbnails=file_thumbnails,
                comparison_thumbnail=comparison_thumbnail
            ))
            processed_files.add(f1)
    
    # Don't clean up temp files - they will be used by GUI
    # GUI is responsible for cleanup
    
    return duplicate_groups
