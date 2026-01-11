# convert_videos

Automatically convert any videos in a specific folder to H.265 (HEVC).
This tool will keep monitoring for new files in the folder (or any sub-folder within it), and if a video is more than 1GB and not already H.265, it will automatically convert it.

Benefits:
1. Hardware-accelerated playback support
2. Significant storage savings (typically 40-60% smaller files)
3. Works on Windows, Linux, and macOS

## Installation & Usage

### Windows (Without Docker)

See **[WINDOWS_INSTALL.md](WINDOWS_INSTALL.md)** for detailed Windows installation instructions.

**Quick Start:**
```cmd
# Install dependencies: Python 3, FFmpeg, HandBrakeCLI
# Then run:
python convert_videos.py "C:\Path\To\Videos"

# Or run continuously:
python convert_videos.py --loop "C:\Path\To\Videos"

# Dry run to see what would be converted:
python convert_videos.py --dry-run "C:\Path\To\Videos"
```

### Linux/macOS (Without Docker)

**Install dependencies:**
```bash
# Ubuntu/Debian
sudo apt-get install python3 ffmpeg handbrake-cli

# macOS (using Homebrew)
brew install python3 ffmpeg handbrake
```

**Run the script:**
```bash
python3 convert_videos.py /path/to/videos

# Or run continuously:
python3 convert_videos.py --loop /path/to/videos
```

### Docker (Linux)

**Build the Docker image:**
```bash
docker build -t rdxmaster/convert_videos:latest .
```

**Run the container:**
```bash
docker run \
	-d \
	--name convert_videos \
	-v [FOLDER]:/data \
	--restart unless-stopped \
	--cap-add=SYS_NICE \
	rdxmaster/convert_videos
```

## Dependencies

- **Python 3.8+** (for the Python script)
- **FFmpeg** (provides `ffprobe` for video analysis)
- **HandBrakeCLI** (for video conversion)

## What It Does

1. Scans the specified directory and all subdirectories
2. Finds video files (MP4, MKV, MOV, AVI) that are 1GB or larger
3. Checks if they're already encoded with H.265 (HEVC)
4. Converts non-HEVC videos to H.265 using optimal settings
5. Validates the conversion by comparing video durations
6. Removes the original file if conversion is successful

## File Naming

- Converted files: `[Original Name] - New.mkv`
- Failed conversions: `[Original Name].[ext].fail`
