#!/usr/bin/bash
set -e

# Build command with appropriate flags using array
# Use -u flag for unbuffered output so logs appear immediately in Docker
CMD_ARGS=('python3' '-u' 'convert_videos_cli_runner.py')

# Add all the arguments that were passed to the script
CMD_ARGS+=("$@")

# Check if config.yaml exists in a separate config directory
if [[ -f "/config/config.yaml" ]]; then
    echo "Using config file: /config/config.yaml"
    CMD_ARGS+=('--config' '/config/config.yaml')
else
    # Always run in loop mode for Docker when no config
    CMD_ARGS+=('--loop')
fi

# Execute the command
exec "${CMD_ARGS[@]}"
