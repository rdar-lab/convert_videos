#!/usr/bin/bash
set -e

# Populate ARGS array from script arguments
ARGS=("$@")

# Now safely get the directory
TARGET_DIR=${ARGS[0]:-/data}

# Build command with appropriate flags using array
# Use -u flag for unbuffered output so logs appear immediately in Docker
CMD_ARGS=('python3' '-u' 'duplicate_detector.py')

CMD_ARGS+=("$TARGET_DIR")

# Add thumbnails directory (default to /thumbs in Docker)
CMD_ARGS+=('--thumbnails-dir' '/thumbs')

# Execute the command
exec "${CMD_ARGS[@]}"