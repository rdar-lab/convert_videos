#!/bin/bash
# CLI Demo Script - Shows example usage of convert_videos CLI
# This script demonstrates the commands and expected output

set -e

echo "==================================================================="
echo "  convert_videos CLI Demonstration"
echo "==================================================================="
echo ""
echo "This demonstration shows the typical workflow of using the CLI."
echo ""

# Help command
echo "$ python3 convert_videos_cli.py --help"
echo ""
cat << 'EOF'
usage: convert_videos_cli.py [-h] [--config CONFIG] [--dry-run] 
                             [--loop] [--min-file-size MIN_FILE_SIZE]
                             [--remove-original-files] [--log-file LOG_FILE]
                             [--encoder {x265,x265_10bit,nvenc_hevc}]
                             [--preset PRESET] [--quality QUALITY]
                             [--output-format {mkv,mp4}]
                             [directory]

Video converter - Automatically convert videos to H.265

positional arguments:
  directory            Directory to scan for videos

optional arguments:
  --config CONFIG      Path to YAML config file
  --dry-run           Show what would be converted without converting
  --loop              Run continuously (scan every hour)
  --min-file-size     Minimum file size threshold (e.g., "1GB", "500MB")
  --encoder           Encoder to use: x265, x265_10bit, nvenc_hevc
  --quality           Quality setting (0-51, lower = better)
  --remove-original-files  Remove original files after successful conversion
EOF
echo ""
echo "-------------------------------------------------------------------"
echo ""

# Show sample directory
echo "$ ls -lh /path/to/videos/"
echo ""
echo "total 8.5G"
echo "-rw-r--r-- 1 user user 2.1G Jan 15 10:23 movie1.mp4"
echo "-rw-r--r-- 1 user user 3.8G Jan 15 11:45 movie2.avi"
echo "-rw-r--r-- 1 user user 1.2G Jan 15 14:30 movie3.mkv"
echo "-rw-r--r-- 1 user user 1.5G Jan 15 16:00 series_s01e01.mp4"
echo ""
echo "-------------------------------------------------------------------"
echo ""

# Dry run
echo "$ python3 convert_videos_cli.py --dry-run /path/to/videos/"
echo ""
echo "2024-01-17 10:30:15 - INFO - Starting video converter (dry-run mode)"
echo "2024-01-17 10:30:15 - INFO - Scanning directory: /path/to/videos/"
echo "2024-01-17 10:30:16 - INFO - Found 4 video files"
echo "2024-01-17 10:30:16 - INFO - Analyzing: movie1.mp4 (2.1 GB)"
echo "2024-01-17 10:30:16 - INFO -   Codec: h264 → Would convert to HEVC"
echo "2024-01-17 10:30:17 - INFO - Analyzing: movie2.avi (3.8 GB)"
echo "2024-01-17 10:30:17 - INFO -   Codec: mpeg4 → Would convert to HEVC"
echo "2024-01-17 10:30:17 - INFO - Analyzing: movie3.mkv (1.2 GB)"
echo "2024-01-17 10:30:17 - INFO -   Codec: hevc → Already HEVC, skipping"
echo "2024-01-17 10:30:18 - INFO - Analyzing: series_s01e01.mp4 (1.5 GB)"
echo "2024-01-17 10:30:18 - INFO -   Codec: h264 → Would convert to HEVC"
echo ""
echo "Summary (dry-run):"
echo "  - Files to convert: 3"
echo "  - Files to skip: 1"
echo "  - Estimated space savings: 40-60%"
echo ""
echo "-------------------------------------------------------------------"
echo ""

# Actual conversion
echo "$ python3 convert_videos_cli.py /path/to/videos/"
echo ""
echo "2024-01-17 10:35:00 - INFO - Starting video converter"
echo "2024-01-17 10:35:00 - INFO - Scanning directory: /path/to/videos/"
echo "2024-01-17 10:35:01 - INFO - Found 3 files to convert"
echo ""
echo "2024-01-17 10:35:01 - INFO - Converting: movie1.mp4 (2.1 GB)"
echo "2024-01-17 10:35:01 - INFO - Running HandBrakeCLI..."
echo "Encoding: task 1 of 1, 5.23 % (21.45 fps, avg 21.45 fps, ETA 00h15m22s)"
echo "Encoding: task 1 of 1, 12.67 % (32.11 fps, avg 28.32 fps, ETA 00h12m18s)"
echo "Encoding: task 1 of 1, 25.34 % (35.89 fps, avg 31.56 fps, ETA 00h09m45s)"
sleep 1
echo "Encoding: task 1 of 1, 42.18 % (36.22 fps, avg 33.12 fps, ETA 00h06m33s)"
echo "Encoding: task 1 of 1, 68.92 % (37.45 fps, avg 34.87 fps, ETA 00h03m12s)"
echo "Encoding: task 1 of 1, 89.43 % (38.12 fps, avg 35.23 fps, ETA 00h01m05s)"
echo "Encoding: task 1 of 1, 100.00 % (38.45 fps, avg 35.67 fps)"
echo ""
echo "2024-01-17 10:50:23 - INFO - Conversion complete!"
echo "2024-01-17 10:50:23 - INFO - Output: movie1.converted.mkv (1.1 GB)"
echo "2024-01-17 10:50:23 - INFO - Space saved: 1.0 GB (47.6%)"
echo "2024-01-17 10:50:23 - INFO - Duration validation: PASS"
echo ""
echo "-------------------------------------------------------------------"
echo ""

# Show results
echo "$ ls -lh /path/to/videos/"
echo ""
echo "total 9.6G"
echo "-rw-r--r-- 1 user user 2.1G Jan 15 10:23 movie1.mp4"
echo "-rw-r--r-- 1 user user 1.1G Jan 17 10:50 movie1.converted.mkv  ← NEW"
echo "-rw-r--r-- 1 user user 3.8G Jan 15 11:45 movie2.avi"
echo "-rw-r--r-- 1 user user 1.2G Jan 15 14:30 movie3.mkv"
echo "-rw-r--r-- 1 user user 1.5G Jan 15 16:00 series_s01e01.mp4"
echo ""
echo "==================================================================="
echo "  Demonstration complete!"
echo "==================================================================="
