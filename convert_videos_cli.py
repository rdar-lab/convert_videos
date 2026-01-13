#!/usr/bin/env python3
"""
CLI-only entry point for convert_videos that always runs in background mode.
This is used for the standalone CLI executable to prevent GUI from launching.
"""

import sys

# Explicitly reject GUI mode in the CLI-only entry point
if '--gui' in sys.argv:
    sys.stderr.write(
        "Error: The --gui flag is not supported in the CLI executable. "
        "It always runs in background mode.\n"
        "Use convert_videos_gui executable for GUI mode.\n"
    )
    sys.exit(1)

# Force background mode by injecting --background flag if not already present
if '--background' not in sys.argv:
    # Insert --background after the script name
    sys.argv.insert(1, '--background')

# Import and run the main script
import convert_videos

if __name__ == '__main__':
    convert_videos.main()
