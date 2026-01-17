#!/usr/bin/bash
set -e

# Build command with appropriate flags using array
# Use -u flag for unbuffered output so logs appear immediately in Docker
CMD_ARGS=('python3' '-u' 'duplicate_detector_runner.py')

# Add all the arguments that were passed to the script
CMD_ARGS+=("$@")

# Add thumbnails directory (default to /thumbs in Docker)
CMD_ARGS+=('--thumbnails-dir' '/thumbs')

# Execute the command
exec "${CMD_ARGS[@]}"