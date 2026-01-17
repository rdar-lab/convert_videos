# Recording Guide for Demo Videos

This guide explains how to create the demonstration videos for the convert_videos project.

## Overview

Three videos need to be created to showcase the main features:
1. **CLI Usage** - Command-line interface demonstration
2. **GUI Usage** - Graphical user interface demonstration
3. **Duplicate Detection** - Duplicate video detection feature

## Video Requirements

- **Format**: MP4 (H.264 or H.265 codec for GitHub compatibility)
- **Resolution**: 1920x1080 or 1280x720 (HD quality)
- **Duration**: 30-90 seconds per video
- **File size**: Keep under 10MB per video (use compression if needed)
- **Frame rate**: 30fps or 60fps
- **Audio**: Optional, but consider adding brief narration or text overlays

## Recording Tools

### For CLI (Terminal Recording)
- **asciinema** (https://asciinema.org/) - Terminal session recorder
  - Can be converted to GIF or video
  - `asciinema rec demo.cast`
  - Convert to GIF: `asciicast2gif demo.cast demo.gif`
- **ttyrec/ttygif** - Alternative terminal recorder
- **OBS Studio** - Screen capture for terminal window

### For GUI
- **OBS Studio** (https://obsproject.com/) - Free, open-source screen recorder
- **QuickTime Player** (macOS) - Built-in screen recording
- **Windows Game Bar** (Windows) - Win+G shortcut
- **SimpleScreenRecorder** (Linux)
- **peek** (Linux) - Simple GIF recorder

## Video 1: CLI Usage Demo

**Filename**: `cli-demo.mp4` or `cli-demo.gif`

**What to show**:
1. **Start with clean terminal**
   ```bash
   # Show help
   python3 convert_videos_cli.py --help
   ```

2. **Show file structure**
   ```bash
   # List some sample videos
   ls -lh /path/to/videos/
   ```

3. **Run conversion with dry-run**
   ```bash
   python3 convert_videos_cli.py --dry-run /path/to/videos/
   ```

4. **Show actual conversion (or use config file)**
   ```bash
   # Option 1: Direct command
   python3 convert_videos_cli.py /path/to/videos/
   
   # Option 2: With config
   python3 convert_videos_cli.py --config config.yaml
   ```

5. **Show log output and progress**
   - Let it run for a few seconds to show progress
   - Display the log file contents

6. **Show results**
   ```bash
   # Show converted files
   ls -lh /path/to/videos/
   # Compare file sizes
   ```

**Tips**:
- Use sample videos that convert quickly (small files)
- Speed up the video during the actual conversion process
- Add text overlays explaining each step
- Show the before/after file sizes

## Video 2: GUI Usage Demo

**Filename**: `gui-demo.mp4` or `gui-demo.gif`

**What to show**:
1. **Launch the GUI**
   ```bash
   python3 convert_videos_gui.py
   ```

2. **Configuration Tab**
   - Show the configuration editor
   - Edit a few settings (directory, min file size, encoder)
   - Demonstrate validation (try invalid input)
   - Save configuration

3. **File Queue Tab**
   - Show the list of files waiting to be processed
   - Highlight different columns (file name, size, codec, status)

4. **Live Progress Tab**
   - Start a conversion
   - Show the progress bar
   - Display current file being processed

5. **Results Dashboard Tab**
   - Show completed conversions
   - Display success/failure status
   - Show space savings statistics
   - Highlight error messages if any

**Tips**:
- Use smaller test videos for quick demonstration
- Keep mouse movements smooth and deliberate
- Pause briefly on each tab to let viewers see details
- Show both successful and maybe one failed conversion
- Consider adding cursor highlights or annotations

## Video 3: Duplicate Detection Demo

**Filename**: `duplicate-detector-demo.mp4` or `duplicate-detector-demo.gif`

**What to show**:
1. **Setup: Create test directory with duplicates**
   - Show a folder with some video files
   - Include obvious duplicates (same file, different names)
   - Include similar videos that are near-duplicates

2. **Run duplicate detector with help**
   ```bash
   python3 duplicate_detector.py --help
   ```

3. **Run duplicate detection**
   ```bash
   python3 duplicate_detector.py /path/to/videos/
   ```

4. **Show the detection process**
   - Display progress as it scans files
   - Show hash calculations
   - Display when duplicates are found

5. **Show results**
   - List the duplicate groups
   - Show the hamming distances
   - Display thumbnails if generated
   - Show the side-by-side comparison images

6. **Optional: Show with different threshold**
   ```bash
   python3 duplicate_detector.py --max-distance 10 /path/to/videos/
   ```

**Tips**:
- Prepare test videos beforehand (actual duplicates and near-duplicates)
- Show the thumbnail comparisons clearly
- Highlight the hamming distance values
- Demonstrate how the threshold affects results
- Consider showing the generated thumbnails in an image viewer

## Post-Recording Steps

1. **Compress videos** if needed:
   ```bash
   ffmpeg -i input.mp4 -vcodec libx264 -crf 28 output.mp4
   ```

2. **Convert to GIF** (optional, for smaller embeds):
   ```bash
   ffmpeg -i input.mp4 -vf "fps=10,scale=800:-1:flags=lanczos" output.gif
   ```

3. **Upload to repository**:
   - Place in `docs/videos/` or `assets/` directory
   - Keep files under 10MB if possible
   - Use Git LFS for larger files if needed

4. **Test GitHub rendering**:
   - Verify videos play correctly on GitHub
   - Check that embeds display properly in README

## Embedding in README

Videos will be embedded at the top of README.md using:

```markdown
## Demo Videos

### CLI Usage
![CLI Demo](docs/videos/cli-demo.gif)

### GUI Usage
![GUI Demo](docs/videos/gui-demo.gif)

### Duplicate Detection
![Duplicate Detection Demo](docs/videos/duplicate-detector-demo.gif)
```

Or for MP4 files:
```html
<video src="docs/videos/cli-demo.mp4" controls></video>
```

## Notes

- GitHub has a 10MB limit for files in web interface, 100MB for command line
- Consider using GIF for better inline preview support
- MP4 provides better quality and smaller file size
- Can also host on external services (YouTube, etc.) and link
