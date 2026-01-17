# Demo Videos

This directory contains demonstration videos for the convert_videos project.

## Current Videos

1. **cli-demo-real.gif** (1.2MB) - Real terminal recording of CLI usage
2. **gui-demo-real.gif** (228KB) - Visual demonstration of GUI features
3. **duplicate-detector-demo-real.gif** (1.1MB) - Real terminal recording of duplicate detection

## How These Were Created

### CLI and Duplicate Detector Demos

The CLI and duplicate detector demos were created using:
- `asciinema` to record actual terminal sessions running the real tools
- `agg` (asciinema GIF generator) to convert recordings to animated GIFs
- Real test video files for demonstration

### GUI Demo

The GUI demo was created using:
- Text descriptions of each GUI tab
- ImageMagick to generate slides from text
- FFmpeg to create a video slideshow
- FFmpeg palette optimization to convert to animated GIF

## File Requirements

- **Format**: GIF (animated)
- **CLI Demo**: 1.2MB - Shows actual terminal output
- **GUI Demo**: 228KB - Text-based slides showing GUI features
- **Duplicate Detector**: 1.1MB - Shows actual terminal output

## Regenerating Demos

To regenerate the demos:

```bash
# CLI Demo
cd docs/videos
asciinema rec -c "./record_cli_real.sh" cli-demo-real.cast
agg cli-demo-real.cast cli-demo-real.gif

# Duplicate Detector Demo
asciinema rec -c "./record_duplicate_real.sh" duplicate-detector-demo-real.cast
agg duplicate-detector-demo-real.cast duplicate-detector-demo-real.gif

# GUI Demo
bash create_gui_video.sh
```

## Notes

- All demos are actual recordings or demonstrations of the real tools
- The GIF format provides wide compatibility and auto-plays in GitHub
- Files are kept under GitHub's size limits
- Asciinema recordings (.cast files) are preserved for future regeneration

