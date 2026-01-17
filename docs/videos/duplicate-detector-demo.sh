#!/bin/bash
# Duplicate Detector Demo Script - Shows example usage
# This script demonstrates the duplicate detection feature

set -e

echo "==================================================================="
echo "  Video Duplicate Detection Demonstration"
echo "==================================================================="
echo ""
echo "This tool uses perceptual hashing to find duplicate videos."
echo ""

# Help command
echo "$ python3 duplicate_detector.py --help"
echo ""
cat << 'EOF'
usage: duplicate_detector.py [-h] [--max-distance MAX_DISTANCE]
                             [--thumbnails-dir THUMBNAILS_DIR]
                             directory

Video duplicate detector using perceptual hashing

positional arguments:
  directory             Directory to scan for duplicate videos

optional arguments:
  --max-distance MAX_DISTANCE
                        Maximum hamming distance to consider duplicates
                        (default: 5, range: 0-64)
  --thumbnails-dir THUMBNAILS_DIR
                        Directory to save comparison thumbnails
EOF
echo ""
echo "-------------------------------------------------------------------"
echo ""

# Show sample directory
echo "$ ls -lh /path/to/videos/"
echo ""
echo "total 12G"
echo "-rw-r--r-- 1 user user 1.8G Jan 14 09:15 movie_original.mp4"
echo "-rw-r--r-- 1 user user 1.8G Jan 14 09:20 movie_copy.mp4"
echo "-rw-r--r-- 1 user user 1.9G Jan 14 09:25 movie_reencoded.mp4"
echo "-rw-r--r-- 1 user user 2.1G Jan 14 10:30 vacation_2023.mov"
echo "-rw-r--r-- 1 user user 2.3G Jan 14 11:00 vacation_backup.mov"
echo "-rw-r--r-- 1 user user 2.4G Jan 14 12:15 different_movie.avi"
echo ""
echo "-------------------------------------------------------------------"
echo ""

# Run duplicate detection
echo "$ python3 duplicate_detector.py --max-distance 10 \\"
echo "    --thumbnails-dir /tmp/thumbnails /path/to/videos/"
echo ""
sleep 0.5
echo "2024-01-17 10:35:00 - INFO - Starting duplicate detection"
echo "2024-01-17 10:35:00 - INFO - Scanning directory: /path/to/videos/"
echo "2024-01-17 10:35:01 - INFO - Found 6 video files"
echo ""
echo "2024-01-17 10:35:01 - INFO - Processing: movie_original.mp4"
echo "2024-01-17 10:35:02 - INFO -   Extracting frame... Done"
echo "2024-01-17 10:35:02 - INFO -   Computing hash... Done"
echo ""
echo "2024-01-17 10:35:03 - INFO - Processing: movie_copy.mp4"
echo "2024-01-17 10:35:04 - INFO -   Extracting frame... Done"
echo "2024-01-17 10:35:04 - INFO -   Computing hash... Done"
echo "2024-01-17 10:35:04 - INFO -   ⚠️  Possible duplicate detected!"
echo ""
echo "2024-01-17 10:35:05 - INFO - Processing: movie_reencoded.mp4"
echo "2024-01-17 10:35:06 - INFO -   Extracting frame... Done"
echo "2024-01-17 10:35:06 - INFO -   Computing hash... Done"
echo "2024-01-17 10:35:06 - INFO -   ⚠️  Possible duplicate detected!"
echo ""
sleep 0.5
echo "2024-01-17 10:35:07 - INFO - Processing: vacation_2023.mov"
echo "2024-01-17 10:35:08 - INFO -   Extracting frame... Done"
echo "2024-01-17 10:35:08 - INFO -   Computing hash... Done"
echo ""
echo "2024-01-17 10:35:09 - INFO - Processing: vacation_backup.mov"
echo "2024-01-17 10:35:10 - INFO -   Extracting frame... Done"
echo "2024-01-17 10:35:10 - INFO -   Computing hash... Done"
echo "2024-01-17 10:35:10 - INFO -   ⚠️  Possible duplicate detected!"
echo ""
echo "2024-01-17 10:35:11 - INFO - Processing: different_movie.avi"
echo "2024-01-17 10:35:12 - INFO -   Extracting frame... Done"
echo "2024-01-17 10:35:12 - INFO -   Computing hash... Done"
echo ""
echo "-------------------------------------------------------------------"
echo ""
echo "2024-01-17 10:35:12 - INFO - Scan complete!"
echo ""
echo "==================================================================="
echo "  DUPLICATE GROUPS FOUND: 2"
echo "==================================================================="
echo ""
echo "Group 1: Movie duplicates (Max distance: 3)"
echo "  - /path/to/videos/movie_original.mp4 (1.8 GB)"
echo "  - /path/to/videos/movie_copy.mp4 (1.8 GB)"
echo "  - /path/to/videos/movie_reencoded.mp4 (1.9 GB)"
echo "  Hamming distances: 0-3 bits difference"
echo "  Thumbnails saved: /tmp/thumbnails/comparison_*.jpg"
echo ""
echo "Group 2: Vacation duplicates (Max distance: 2)"
echo "  - /path/to/videos/vacation_2023.mov (2.1 GB)"
echo "  - /path/to/videos/vacation_backup.mov (2.3 GB)"
echo "  Hamming distances: 0-2 bits difference"
echo "  Thumbnails saved: /tmp/thumbnails/comparison_*.jpg"
echo ""
echo "-------------------------------------------------------------------"
echo ""
echo "💾 Potential space savings: 5.9 GB"
echo ""
echo "To review the duplicates visually:"
echo "  $ ls -lh /tmp/thumbnails/"
echo ""
echo "==================================================================="
