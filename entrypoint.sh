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

if $DRY_RUN; then
    echo "Running in dry-run mode: no actual conversion will be done."
fi

while true; do
    if $DRY_RUN; then
        /usr/local/bin/convert_videos.sh --dry-run "$TARGET_DIR"
    else
        /usr/local/bin/convert_videos.sh "$TARGET_DIR"
    fi
    sleep 3600
done
