# Building Portable Executables

This document explains how to build standalone executable packages for convert_videos that include all dependencies.

## Quick Start

Build for your current platform:
```bash
python build_executable.py
```

Build for a specific platform:
```bash
python build_executable.py --platform linux
python build_executable.py --platform windows
python build_executable.py --platform macos
```

## What Gets Bundled

The executable package includes:
- Python interpreter
- All Python dependencies (PyYAML, tkinter)
- HandBrakeCLI (if available or manually provided)
- FFmpeg/FFprobe binaries (if available or manually provided)

## Requirements

- Python 3.8 or higher
- PyInstaller (automatically installed if missing)

### Platform-Specific Requirements

**Linux:**
- System packages: `ffmpeg`, `handbrake-cli`
- Install: `sudo apt-get install ffmpeg handbrake-cli`

**Windows:**
- FFmpeg: Download from https://www.gyan.dev/ffmpeg/builds/
- HandBrake CLI: Download from https://handbrake.fr/downloads.php
- Or use Chocolatey: `choco install ffmpeg handbrake-cli`

**macOS:**
- Homebrew packages: `ffmpeg`, `handbrake`
- Install: `brew install ffmpeg handbrake`

## Build Options

### Skip Downloading External Binaries

If you want to rely on system-installed tools:
```bash
python build_executable.py --skip-download
```

### Provide Custom Binary Paths

Bundle specific versions of external tools:
```bash
python build_executable.py \
  --handbrake-path /path/to/HandBrakeCLI \
  --ffmpeg-path /path/to/ffmpeg \
  --ffprobe-path /path/to/ffprobe
```

## Output

After successful build, you'll find:
- **CLI Executable**: `dist/convert_videos_cli` (or `convert_videos_cli.exe` on Windows)
- **GUI Executable**: `dist/convert_videos_gui` (or `convert_videos_gui.exe` on Windows)
- **Package**: `dist/convert_videos-{platform}.tar.gz` (or `.zip` on Windows)

The package includes:
- Both executables (CLI and GUI)
- README.md
- BUILD.md
- LICENSE
- config.yaml.example

### Executable Differences

- **CLI Executable (`convert_videos_cli`)**: 
  - Runs with a console window
  - Always runs in background mode (never launches GUI)
  - Suitable for command-line usage, scripts, and background tasks
  - Supports all command-line arguments
  
- **GUI Executable (`convert_videos_gui`)**:
  - Runs without a console window for a clean experience
  - Launches the graphical user interface
  - Automatically detects and displays bundled dependencies (HandBrakeCLI, ffprobe, ffmpeg)

## GitHub Actions

Automated builds are configured via `.github/workflows/build-release.yml`.

### Triggering a Release

Create and push a version tag:
```bash
git tag v1.0.0
git push origin v1.0.0
```

This will:
1. Build executables for Linux, Windows, and macOS
2. Build and push Docker image to DockerHub (if secrets are configured)
3. Create a GitHub Release
4. Upload all platform packages as release assets

### Docker Image Publishing

The workflow automatically builds and publishes Docker images to DockerHub when:
- A version tag is pushed (e.g., `v1.0.0`)
- DockerHub secrets are configured

**Required Secrets:**
- `DOCKERHUB_USERNAME` - Your DockerHub username
- `DOCKERHUB_TOKEN` - Your DockerHub access token

**Tags Created:**
- `{username}/convert_videos:{version}` - Specific version (e.g., `v1.0.0`)
- `{username}/convert_videos:latest` - Latest release

If the secrets are not configured, the Docker build step is skipped, and only executables are built.

### Manual Trigger

You can also trigger the workflow manually from the GitHub Actions tab.

## Troubleshooting

### Missing tkinter

If PyInstaller can't find tkinter:
- **Linux**: Install `python3-tk`
- **Windows**: Reinstall Python with tkinter enabled
- **macOS**: tkinter should be included with Python

### Missing External Tools

If HandBrakeCLI or ffmpeg aren't found:
1. Install them on your system
2. Use `--skip-download` to rely on system installation
3. Or provide explicit paths with `--handbrake-path`, `--ffmpeg-path`, `--ffprobe-path`

### Large Executable Size

The executable will be large (100-300 MB) because it includes:
- Python interpreter
- All libraries
- External tools (HandBrakeCLI, ffmpeg)

This is expected for a truly portable executable.

## Using the Portable Executables

Once built, the executables can be used standalone:

### GUI Mode (Recommended for Interactive Use)

```bash
# Linux/macOS
./convert_videos_gui

# Windows
convert_videos_gui.exe
```

The GUI executable:
- Launches without a console window
- Automatically detects bundled dependencies (HandBrakeCLI, ffprobe, ffmpeg)
- Shows full paths to bundled dependencies in the Configuration tab
- Provides visual configuration, progress monitoring, and results

### CLI Mode (For Automation and Scripts)

```bash
# Linux/macOS
./convert_videos_cli

# Windows
convert_videos_cli.exe

# With arguments
./convert_videos_cli /path/to/videos
./convert_videos_cli --config config.yaml
./convert_videos_cli --loop /path/to/videos
```

The CLI executable:
- Runs with a console window for output
- Always runs in background mode (never launches GUI)
- Supports all command-line options
- Suitable for scripts, Docker, and automated tasks
- Automatically uses bundled dependencies when available
