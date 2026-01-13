# Windows Installation Guide

This guide will help you set up and run the video converter on Windows without Docker.

## Prerequisites

You need to install the following dependencies:

### 1. Python 3.8 or higher

1. Download Python from [python.org](https://www.python.org/downloads/)
2. During installation, make sure to check "Add Python to PATH"
3. **For GUI mode**: Tkinter is included with Python on Windows by default
4. Verify installation by opening Command Prompt or PowerShell and running:
   ```cmd
   python --version
   ```

### 2. FFmpeg

FFmpeg provides `ffprobe`, which is used to analyze video files.

**Option A: Using Chocolatey (Recommended)**
```cmd
choco install ffmpeg
```

**Option B: Manual Installation**
1. Download FFmpeg from [ffmpeg.org](https://ffmpeg.org/download.html#build-windows)
2. Choose a Windows build (e.g., from gyan.dev or BtbN)
3. Extract the ZIP file to a folder (e.g., `C:\ffmpeg`)
4. Add the `bin` folder to your PATH:
   - Open "Environment Variables" in Windows Settings
   - Edit the "Path" variable under "System variables"
   - Add `C:\ffmpeg\bin` (or wherever you extracted it)
5. Verify installation:
   ```cmd
   ffmpeg -version
   ffprobe -version
   ```

### 3. HandBrake CLI

HandBrakeCLI is used to convert video files to H.265.

**Option A: Using Chocolatey**
```cmd
choco install handbrake-cli
```

**Option B: Manual Installation**
1. Download HandBrake CLI from [handbrake.fr](https://handbrake.fr/downloads.php)
2. Download the "Command Line Version" for Windows
3. Extract the ZIP file to a folder (e.g., `C:\HandBrake`)
4. Add the folder to your PATH (same process as FFmpeg)
5. Verify installation:
   ```cmd
   HandBrakeCLI --version
   ```

## Installation

1. Clone or download this repository:
   ```cmd
   git clone https://github.com/rdar-lab/convert_videos.git
   cd convert_videos
   ```

2. (Optional) Create a virtual environment:
   ```cmd
   python -m venv venv
   venv\Scripts\activate
   ```

3. The script uses only Python standard library, but you can verify with:
   ```cmd
   pip install -r requirements.txt
   ```

## Usage

### GUI Mode (Headed Mode) - Recommended for Desktop Use

Run the application with a graphical user interface:
```cmd
python convert_videos.py --headed
```

The GUI provides:
- Easy configuration editing with validation
- Visual queue of files to process
- Real-time progress monitoring
- Results dashboard showing space savings and conversion status

**Note**: GUI mode requires a display and does not run in Docker.

### Basic Usage (Command Line)

Convert videos in a specific folder:
```cmd
python convert_videos.py "C:\Path\To\Your\Videos"
```

### Dry Run Mode

See what would be converted without actually converting:
```cmd
python convert_videos.py --dry-run "C:\Path\To\Your\Videos"
```

### Continuous Monitoring

Run in a loop that checks for new files every hour:
```cmd
python convert_videos.py --loop "C:\Path\To\Your\Videos"
```

### Preserve Original Files

Keep original files after successful conversion (default is to remove them):
```cmd
python convert_videos.py --preserve-original "C:\Path\To\Your\Videos"
```

Or set an environment variable:
```cmd
set VIDEO_CONVERTER_PRESERVE_ORIGINAL=true
python convert_videos.py "C:\Path\To\Your\Videos"
```

### Using PowerShell

In PowerShell, you can use forward slashes or backslashes:
```powershell
python convert_videos.py "C:/Path/To/Your/Videos"
```

## What It Does

The script will:
1. Scan the specified directory and all subdirectories
2. Find video files (MP4, MKV, MOV, AVI) that are 1GB or larger
3. Skip files marked as `.fail` (from previous failed conversions)
4. Check if they're already encoded with H.265 (HEVC)
5. Convert non-HEVC videos to H.265 using HandBrakeCLI
6. Preserve all audio tracks and subtitles from the original file
7. Validate the conversion by comparing video durations
8. Remove the original file if conversion is successful (unless `--preserve-original` is used)
9. Mark the original file as `.fail` if there's a duration mismatch

## Running as a Background Task

### Option 1: Using Task Scheduler

1. Open Task Scheduler
2. Create a new task
3. Set the trigger (e.g., at startup or at specific intervals)
4. Set the action to run:
   ```
   Program: python
   Arguments: convert_videos.py --loop "C:\Path\To\Your\Videos"
   Start in: C:\path\to\convert_videos
   ```

### Option 2: Using NSSM (Non-Sucking Service Manager)

1. Download NSSM from [nssm.cc](https://nssm.cc/)
2. Install the service:
   ```cmd
   nssm install ConvertVideos "C:\Path\To\Python\python.exe" "C:\path\to\convert_videos\convert_videos.py" --loop "C:\Videos"
   ```
3. Start the service:
   ```cmd
   nssm start ConvertVideos
   ```

## Troubleshooting

### "python is not recognized"
- Make sure Python is added to PATH
- Try using `py` instead of `python`

### "ffprobe is not recognized" or "HandBrakeCLI is not recognized"
- Verify the tools are installed and in your PATH
- Restart your terminal after adding to PATH

### Script says "Missing dependencies"
- Run `ffprobe --version` and `HandBrakeCLI --version` to verify installation
- Make sure both are accessible from the command line

### Permission Errors
- Run Command Prompt or PowerShell as Administrator
- Check that you have write permissions to the video directory

## Performance Considerations

- The script runs HandBrakeCLI with lower priority to avoid impacting system performance
- Conversion can be CPU-intensive and may take several hours per video
- It's recommended to run this on a machine that can be left running overnight

## Notes

- Original files are deleted only after successful conversion (unless `--preserve-original` flag is used)
- If conversion fails (duration mismatch), the original is renamed to `.fail` (or `.fail_1`, `.fail_2`, etc. to avoid collisions)
- The converted file is saved as `[original name] - New.mkv` (or with counter if collision)
- Only files 1GB or larger are processed
- Files with `.fail` in the name are automatically skipped to prevent re-processing
- All audio tracks and subtitles from the original file are preserved
