#!/bin/bash
set -e

DRY_RUN=false

# Parse and remove --dry-run from arguments
ARGS=()
for arg in "$@"; do
    if [[ "$arg" == "--dry-run" ]]; then
        DRY_RUN=true
    else
        ARGS+=("$arg")
    fi
done

# Now safely get the directory
TARGET_DIR=${ARGS[0]:-/data}

# Build command with appropriate flags using array
CMD_ARGS=('python3' '/usr/local/bin/convert_videos.py')

# Always run in background mode for Docker (no GUI)
CMD_ARGS+=('--background')

if $DRY_RUN; then
    echo "Running in dry-run mode: no actual conversion will be done."
    CMD_ARGS+=('--dry-run')
fi

# Always run in loop mode for Docker
CMD_ARGS+=('--loop')
CMD_ARGS+=("$TARGET_DIR")

# Execute the command
exec "${CMD_ARGS[@]}"
