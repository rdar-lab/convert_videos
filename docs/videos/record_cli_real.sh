#!/bin/bash
# Real CLI recording script
cd /home/runner/work/convert_videos/convert_videos

echo "=== Video Converter CLI Demo ==="
echo ""
sleep 1

echo "$ python3 convert_videos_cli.py --help"
sleep 0.5
python3 convert_videos_cli.py --help
sleep 2

echo ""
echo "$ ls -lh /tmp/test_videos/"
sleep 0.5
ls -lh /tmp/test_videos/
sleep 2

echo ""
echo "$ python3 convert_videos_cli.py --dry-run /tmp/test_videos/"
sleep 0.5
python3 convert_videos_cli.py --dry-run /tmp/test_videos/ 2>&1 || true
sleep 3

echo ""
echo "Demo complete!"
