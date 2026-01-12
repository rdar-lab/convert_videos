#!/bin/bash
set -e

DRY_RUN=false

# Parse arguments for --dry-run flag
for arg in "$@"; do
    if [[ "$arg" == "--dry-run" ]]; then
        DRY_RUN=true
    fi
done

# Directory to process - default is /data or first argument if not --dry-run
TARGET_DIR=${1:-/data}

# Build command with appropriate flags
CMD="python3 /usr/local/bin/convert_videos.py"

if $DRY_RUN; then
    echo "Running in dry-run mode: no actual conversion will be done."
    CMD="$CMD --dry-run"
fi

# Always run in loop mode for Docker
CMD="$CMD --loop $TARGET_DIR"

# Execute the command
exec $CMD
