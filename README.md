# convert_videos

Automatically convert any videos in a specific folder to H.265 (HEVC).
This tool will keep monitoring for new files in the folder (or any sub-folder within it), and if a video is more than 1GB and not already H.265, it will automatically convert it.

Benefits:
1. Hardware-accelerated playback support
2. Significant storage savings (typically 40-60% smaller files)
3. Works on Windows, Linux, and macOS
4. Configurable via YAML configuration file or command line arguments
5. **Default GUI mode** for easy configuration and monitoring

## Modes of Operation

### Headed Mode (GUI) - **DEFAULT**

The default mode launches a graphical user interface when no arguments are provided:

```bash
# Launch GUI (default - no arguments)
python convert_videos.py

# Or explicitly with --gui flag
python convert_videos.py --gui
```

The GUI provides:
- **Configuration Editor**: Edit all settings with validation and save to config file
- **Configuration Validation**: Real-time validation with error messages
- **File Queue**: See all files waiting to be processed
- **Live Progress**: Monitor current file being processed with progress indicator
- **Results Dashboard**: View completed conversions with success/failure status, error messages, and space savings

**Note**: GUI mode requires a display and tkinter. For headless/server use or when using config files, see Background Mode below.

### Background Mode (CLI)

Background mode is used when providing arguments (directory, config, flags) or explicitly with `--background`:

```bash
# Run with config file (background mode)
python convert_videos.py --config config.yaml

# Single run with directory
python convert_videos.py /path/to/videos

# With --background flag explicitly
python convert_videos.py --background /path/to/videos

# Continuous monitoring (scans every hour)
python convert_videos.py --background --loop /path/to/videos

# Docker mode (automatically runs in background)
docker run -d -v /path/to/videos:/data rdxmaster/convert_videos
```

## Configuration

You can configure the tool using a YAML configuration file. Copy `config.yaml.example` to `config.yaml` and customize:

```yaml
# Directory to scan for video files
directory: "/path/to/videos"

# Minimum file size threshold (supports human-readable formats)
min_file_size: "1GB"  # Can be "500MB", "2GB", etc.

# Logging configuration
logging:
  log_file: "/path/to/convert_videos.log"  # Optional: defaults to temp directory

# Output format and encoder settings
output:
  format: "mkv"  # Output container: mkv or mp4
  encoder: "x265_10bit"  # Options: x265, x265_10bit, nvenc_hevc
  preset: "medium"  # Speed vs quality tradeoff
  quality: 24  # Lower = better quality, larger file (range: 0-51)

# Other options
remove_original_files: false  # Remove original files after conversion (default: false, preserves originals)
loop: false  # Run continuously (scan every hour)
dry_run: false  # Show what would be converted without converting
```

### Logging

The tool creates a log file that captures all important events, including:
- All commands executed (HandBrakeCLI, ffprobe, etc.)
- Command output (stdout and stderr)
- Exit status codes
- Conversion progress and results

**Log file location priority:**
1. Command line argument: `--log-file /path/to/logfile.log`
2. Environment variable: `VIDEO_CONVERTER_LOG_FILE=/path/to/logfile.log`
3. Configuration file: `logging.log_file` setting
4. Default: System temp directory (e.g., `/tmp/convert_videos.log`)

**Examples:**

```bash
# Use custom log file via command line
python convert_videos.py --log-file /var/log/convert_videos.log /path/to/videos

# Use custom log file via environment variable
export VIDEO_CONVERTER_LOG_FILE=/var/log/convert_videos.log
python convert_videos.py /path/to/videos

# Use custom log file via config file
# (Set logging.log_file in config.yaml)
python convert_videos.py --config config.yaml
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

### Portable Executable (Recommended for Easy Setup)

Pre-built portable executables are available for Windows, Linux, and macOS from the [Releases page](https://github.com/rdar-lab/convert_videos/releases).

**Benefits:**
- No need to install Python, FFmpeg, or HandBrakeCLI
- All dependencies bundled in a single executable
- Works out of the box on any system

**Download and run:**
1. Download the appropriate package for your platform from [Releases](https://github.com/rdar-lab/convert_videos/releases)
2. Extract the archive
3. Run the executable:
   - Linux/macOS: `./convert_videos`
   - Windows: `convert_videos.exe`

The portable executable supports all the same options as the Python script.

**Building from source:** See [BUILD.md](BUILD.md) for instructions on building your own portable executable.

### Windows (Without Docker)

See **[WINDOWS_INSTALL.md](WINDOWS_INSTALL.md)** for detailed Windows installation instructions.

**Quick Start:**
```cmd
# Install dependencies: Python 3, FFmpeg, HandBrakeCLI
# Install Python dependencies:
pip install -r requirements.txt

# Run with GUI (default - no arguments):
python convert_videos.py

# Or run with directory (background mode):
python convert_videos.py "C:\Path\To\Videos"

# Run with config file (background mode):
python convert_videos.py --config config.yaml

# Run continuously:
python convert_videos.py --loop "C:\Path\To\Videos"

# Dry run to see what would be converted:
python convert_videos.py --dry-run "C:\Path\To\Videos"

# Remove original files after conversion:
python convert_videos.py --remove-original-files "C:\Path\To\Videos"

# Explicitly use background mode:
python convert_videos.py --background "C:\Path\To\Videos"
```

### Linux/macOS (Without Docker)

**Install dependencies:**
```bash
# Ubuntu/Debian
sudo apt-get install python3 python3-pip ffmpeg handbrake-cli

# Install Python dependencies
pip3 install -r requirements.txt

# macOS (using Homebrew)
brew install python3 ffmpeg handbrake
pip3 install -r requirements.txt
```

**Run the script:**
```bash
# Run with GUI (default - no arguments):
python3 convert_videos.py

# Run with directory (background mode):
python3 convert_videos.py /path/to/videos

# Run with config file (background mode):
python3 convert_videos.py --config config.yaml

# Run continuously:
python3 convert_videos.py --loop /path/to/videos

# Remove original files after conversion:
python3 convert_videos.py --remove-original-files /path/to/videos

# Explicitly use background mode:
python3 convert_videos.py --background /path/to/videos
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
8. By default, preserves the original file (unless `remove_original_files: true` in config)

## File Naming

- Converted files: `[Original Name].converted.mkv` (or with counter if collision: `[Original Name].converted.1.mkv`)
- Failed conversions: `[Original Name].[ext].fail` (or with counter: `[Original Name].[ext].fail_1`)

## Advanced Options

### Remove Original Files After Conversion

By default, original files are preserved after successful conversion. To remove them:

**Configuration file:**
```yaml
remove_original_files: true
```

**Command line flag:**
```bash
python convert_videos.py --remove-original-files /path/to/videos
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
