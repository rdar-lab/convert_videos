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
- **Executable**: `dist/convert_videos` (or `convert_videos.exe` on Windows)
- **Package**: `dist/convert_videos-{platform}.tar.gz` (or `.zip` on Windows)

The package includes:
- The executable
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
2. Create a GitHub Release
3. Upload all platform packages as release assets

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

## Using the Portable Executable

Once built, the executable can be used standalone:

```bash
# Linux/macOS
./convert_videos

# Windows
convert_videos.exe

# With arguments
./convert_videos /path/to/videos
./convert_videos --config config.yaml
```

The executable supports all the same command-line options as the Python script.
