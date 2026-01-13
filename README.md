# convert_videos

Automatically convert any videos in a specific folder to H.265 (HEVC).
This tool will keep monitoring for new files in the folder (or any sub-folder within it), and if a video is more than 1GB and not already H.265, it will automatically convert it.

Benefits:
1. Hardware-accelerated playback support
2. Significant storage savings (typically 40-60% smaller files)
3. Works on Windows, Linux, and macOS
4. Configurable via YAML configuration file or command line arguments
5. **NEW**: Headed mode with GUI for easy configuration and monitoring

## Modes of Operation

### Headed Mode (GUI) - NEW!

Run with a graphical user interface for easy configuration and monitoring:

```bash
python convert_videos.py --headed
```

The GUI provides:
- **Configuration Editor**: Edit all settings with validation and save to config file
- **Configuration Validation**: Real-time validation with error messages
- **File Queue**: See all files waiting to be processed
- **Live Progress**: Monitor current file being processed with progress indicator
- **Results Dashboard**: View completed conversions with success/failure status, error messages, and space savings

**Note**: Headed mode runs directly on your system (not in Docker) and requires a display.

### Background Mode (CLI)

Run as a command-line tool or service (Docker/loop mode):

```bash
# Single run
python convert_videos.py /path/to/videos

# Continuous monitoring (scans every hour)
python convert_videos.py --loop /path/to/videos

# Docker mode (runs in background)
docker run -d -v /path/to/videos:/data rdxmaster/convert_videos
```

## Configuration

You can configure the tool using a YAML configuration file. Copy `config.yaml.example` to `config.yaml` and customize:

```yaml
# Directory to scan for video files
directory: "/path/to/videos"

# Minimum file size threshold (supports human-readable formats)
min_file_size: "1GB"  # Can be "500MB", "2GB", etc.

# Output format and encoder settings
output:
  format: "mkv"  # Output container: mkv or mp4
  encoder: "x265_10bit"  # Options: x265, x265_10bit, nvenc_hevc
  preset: "medium"  # Speed vs quality tradeoff
  quality: 24  # Lower = better quality, larger file (range: 0-51)

# Other options
preserve_original: false  # Keep original files after conversion
loop: false  # Run continuously (scan every hour)
dry_run: false  # Show what would be converted without converting
```

### Encoder Options

- **x265**: Standard H.265 8-bit encoding (CPU)
- **x265_10bit**: H.265 10-bit encoding (CPU, better quality) - **Default**
- **nvenc_hevc**: NVIDIA GPU-accelerated H.265 encoding (requires NVIDIA GPU with NVENC support)

### Using Configuration File

```bash
# Use config.yaml in current directory
python convert_videos.py

# Specify a custom config file
python convert_videos.py --config /path/to/config.yaml

# Command line arguments override config file settings
python convert_videos.py --config config.yaml --dry-run /custom/path
```

## Installation & Usage

### Windows (Without Docker)

See **[WINDOWS_INSTALL.md](WINDOWS_INSTALL.md)** for detailed Windows installation instructions.

**Quick Start:**
```cmd
# Install dependencies: Python 3, FFmpeg, HandBrakeCLI
# Install Python dependencies:
pip install -r requirements.txt

# Run with GUI (headed mode):
python convert_videos.py --headed

# Or run from command line:
python convert_videos.py "C:\Path\To\Videos"

# Or run continuously:
python convert_videos.py --loop "C:\Path\To\Videos"

# Dry run to see what would be converted:
python convert_videos.py --dry-run "C:\Path\To\Videos"

# Keep original files after conversion:
python convert_videos.py --preserve-original "C:\Path\To\Videos"

# Use a configuration file:
python convert_videos.py --config config.yaml
```

### Linux/macOS (Without Docker)

**Install dependencies:**
```bash
# Ubuntu/Debian
sudo apt-get install python3 python3-pip python3-tk ffmpeg handbrake-cli

# Install Python dependencies
pip3 install -r requirements.txt

# macOS (using Homebrew)
brew install python3 ffmpeg handbrake python-tk
pip3 install -r requirements.txt
```

**Run the script:**
```bash
# Run with GUI (headed mode):
python3 convert_videos.py --headed

# Or run from command line:
python3 convert_videos.py /path/to/videos

# Or run continuously:
python3 convert_videos.py --loop /path/to/videos

# Keep original files after conversion:
python3 convert_videos.py --preserve-original /path/to/videos
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
3. Skips files marked as `.fail` (failed previous conversions)
4. Checks if they're already encoded with H.265 (HEVC)
5. Converts non-HEVC videos to H.265 using optimal settings
6. Preserves all audio tracks and subtitles from the original file
7. Validates the conversion by comparing video durations
8. Removes the original file if conversion is successful (unless `--preserve-original` is used)

## File Naming

- Converted files: `[Original Name] - New.mkv` (or with counter if collision: `[Original Name] - New (1).mkv`)
- Failed conversions: `[Original Name].[ext].fail` (or with counter: `[Original Name].[ext].fail_1`)

## Advanced Options

### Preserve Original Files

By default, original files are deleted after successful conversion. To keep them:

**Command line flag:**
```bash
python convert_videos.py --preserve-original /path/to/videos
```

**Environment variable:**
```bash
export VIDEO_CONVERTER_PRESERVE_ORIGINAL=true
python convert_videos.py /path/to/videos
```

## Development & Testing

This project includes comprehensive unit tests and continuous integration.

### Running Tests

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest test_convert_videos.py -v

# Run tests with coverage
pytest test_convert_videos.py --cov=convert_videos --cov-report=term-missing
```

See [TESTING.md](TESTING.md) for detailed testing documentation.

### Continuous Integration

Tests are automatically run via GitHub Actions on:
- Push to main/master/develop branches
- Pull requests to these branches
- Using Ubuntu Latest with Python 3.11
