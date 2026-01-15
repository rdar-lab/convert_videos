#!/usr/bin/bash
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
# Use -u flag for unbuffered output so logs appear immediately in Docker
CMD_ARGS=('python3' '-u' '-m' 'src.convert_videos_cli')

if $DRY_RUN; then
    echo "Running in dry-run mode: no actual conversion will be done."
    CMD_ARGS+=('--dry-run')
fi

# Check if config.yaml exists in a separate config directory
if [[ -f "/config/config.yaml" ]]; then
    echo "Using config file: /config/config.yaml"
    CMD_ARGS+=('--config' '/config/config.yaml')
else
    # Always run in loop mode for Docker when no config
    CMD_ARGS+=('--loop')
    CMD_ARGS+=("$TARGET_DIR")
fi

# Execute the command
exec "${CMD_ARGS[@]}"
