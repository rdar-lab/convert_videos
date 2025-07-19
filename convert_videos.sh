#!/bin/bash
set -euo pipefail
trap 'log "❌ Script failed at line $LINENO with exit code $?"' ERR

LOG_TAG="convert_h265"

LOG_FILE="/var/log/convert_files.log"
DRY_RUN=false
TARGET_DIR=""

# Parse arguments
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=true
    shift
fi

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 [--dry-run] <directory>"
    exit 1
fi

TARGET_DIR="$1"

if [[ ! -d "$TARGET_DIR" ]]; then
    log "Error: '$TARGET_DIR' is not a valid directory."
    exit 1
fi

# Redirect all stdout and stderr to logger
# exec > >(tee >(logger -t "$LOG_TAG")) 2>&1


log() {
    echo "$(date +'%Y-%m-%d %H:%M:%S') - $*" >&2
}

# Find all non-H.265 video files >= 1GB
find_eligible_files() {
    find -L "$TARGET_DIR" -type f -size +1G \( -iname "*.mp4" -o -iname "*.mkv" -o -iname "*.mov" -o -iname "*.avi" \) | while read -r file; do
    # log "Checking file $file"
    codec=$(ffprobe -v error -select_streams v:0 -show_entries stream=codec_name \
            -of default=noprint_wrappers=1:nokey=1 "$file")
    # log "File codec is %codec"
        if [[ "$codec" != "hevc" ]]; then
            size=$(stat -c "%s" "$file")
        # log "File size is $size"
            echo "$size|$file"
        fi
    done | sort -nr | cut -d'|' -f2
}

# Run HandBrake conversion with nice
convert_file() {
    local input="$1"
    local output="${input%.*} - New.mkv"
    local temp_output="${output}.temp"

    log "Starting conversion: $input"
    
    if $DRY_RUN; then
        log "[Dry Run] Would convert: $input -> $output"
        return 0
    fi

    nice -n 10 HandBrakeCLI -i "$input" -o "$temp_output" \
        -e x265 --encoder-preset medium --encoder-profile main10 \
        -q 24 -f mkv --audio 1 --aencoder copy --format av_mkv

    validate_and_finalize "$input" "$temp_output" "$output"
}

abs() {
    local n="$1"
    echo $(( n < 0 ? -n : n ))
}

get_duration() {
    local file="$1"
    local duration

    duration=$(ffprobe -v error -select_streams v:0 -show_entries format=duration \
        -of default=noprint_wrappers=1:nokey=1 "$file" 2>/dev/null | cut -d'.' -f1)

    echo "${duration:-0}"
}


# Validate that source and temp output durations match
validate_and_finalize() {
    local input="$1"
    local temp_output="$2"
    local final_output="$3"
    
    local src_duration=$(get_duration "$input")
    local out_duration=$(get_duration "$temp_output")
    
    if [[ "$src_duration" -eq 0 || "$out_duration" -eq 0 ]]; then
      log "❌ Could not determine duration for one of the files: src=$src_duration vs out=$out_duration"
      # rm -f "$temp_output"
      exit 1
    fi
    
    local diff=$(abs $((src_duration - out_duration)))
    if (( diff <= 1 )); then
        mv "$temp_output" "$final_output"
        rm -f "$input"
        log "✅ Successfully converted: $final_output"
    else
        # rm -f "$temp_output"
        log "❌ Duration mismatch: src=$src_duration vs out=$out_duration for file $input"
        exit 1
    fi
}

# Main loop
main() {
    log "Starting scan in $TARGET_DIR"

    mapfile -t files < <(find_eligible_files)

    if [[ ${#files[@]} -eq 0 ]]; then
        log "No eligible files found."
        exit 0
    fi
    
    log "Files to convert:"
    for file in "${files[@]}"; do
        log "$file"
    done

    for file in "${files[@]}"; do
        convert_file "$file"
    done
}

main "$@"
