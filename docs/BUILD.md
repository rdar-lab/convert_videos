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

- Python 3.11 or higher
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

The build script automatically downloads HandBrakeCLI and FFmpeg binaries:
```bash
python build_executable.py
```

The build will **fail** if downloads are unsuccessful, ensuring fully functional executables.

Optionally specify the target platform (defaults to auto-detect):
```bash
python build_executable.py --platform linux
python build_executable.py --platform windows
python build_executable.py --platform macos
```

## Output

After successful build, you'll find:
- **CLI Executable**: `dist/convert_videos_cli` (or `convert_videos_cli.exe` on Windows)
- **Duplicate Detector Executable**: `dist/duplicate_detector` (or `duplicate_detector.exe` on Windows)
- **GUI Executable**: `dist/convert_videos_gui` (or `convert_videos_gui.exe` on Windows)
- **Package**: `dist/convert_videos-{platform}.tar.gz` (or `.zip` on Windows)

The package includes:
- All executables (CLI, GUI and Duplicate Detector)
- README.md
- LICENSE
- config.yaml.example

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
- `{username}/duplicate_detector:{version}` - Specific version (e.g., `v1.0.0`)
- `{username}/duplicate_detector:latest` - Latest release

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