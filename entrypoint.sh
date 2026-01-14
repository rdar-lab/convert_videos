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

# Check if config.yaml exists in the target directory
if [[ -f "${TARGET_DIR}/config.yaml" ]]; then
    echo "Using config file: ${TARGET_DIR}/config.yaml"
    CMD_ARGS+=('--config' "${TARGET_DIR}/config.yaml")
else
    # Always run in loop mode for Docker when no config
    CMD_ARGS+=('--loop')
    CMD_ARGS+=("$TARGET_DIR")
fi

# Execute the command
exec "${CMD_ARGS[@]}"
