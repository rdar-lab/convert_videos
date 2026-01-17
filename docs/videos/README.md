# Demo Videos

This directory contains demonstration videos for the convert_videos project.

## Required Videos

1. **cli-demo.gif** or **cli-demo.mp4** - Demonstration of CLI usage
2. **gui-demo.gif** or **gui-demo.mp4** - Demonstration of GUI usage
3. **duplicate-detector-demo.gif** or **duplicate-detector-demo.mp4** - Demonstration of duplicate detection

## Recording Instructions

Please see [RECORDING_GUIDE.md](../RECORDING_GUIDE.md) for detailed instructions on how to create these demonstration videos.

## File Requirements

- **Format**: GIF or MP4 (H.264/H.265 codec)
- **Maximum size**: 10MB per file (for GitHub web interface)
- **Resolution**: 1280x720 or 1920x1080
- **Duration**: 30-90 seconds

## Current Status

- [ ] cli-demo (CLI usage demonstration)
- [ ] gui-demo (GUI usage demonstration)
- [ ] duplicate-detector-demo (Duplicate detection demonstration)

## Using Git LFS

If video files are larger than 10MB, consider using Git LFS:

```bash
# Install Git LFS
git lfs install

# Track video files
git lfs track "*.mp4"
git lfs track "*.gif"

# Add .gitattributes
git add .gitattributes

# Add and commit videos
git add docs/videos/*.mp4
git commit -m "Add demo videos"
```
