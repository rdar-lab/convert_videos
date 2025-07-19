#!/bin/bash

INPUT_DIR="$1"
OUTPUT_HASHES="video_hashes.txt"
rm -f "$OUTPUT_HASHES"

source venv/bin/activate

find -L "$INPUT_DIR" -type f \( -iname "*.mp4" -o -iname "*.mkv" -o -iname "*.mov" -o -iname "*.avi" \) -print0 > filelist.txt

while IFS= read -r -d '' file <&3; do
    echo "Processing: $file" >&2

    # Get video duration in seconds
    DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$file")

    if [[ -z "$DURATION" || "$DURATION" == "N/A" ]]; then
        echo "ERR: Could not determine duration for: $file" >&2
        continue
    fi

    # echo "Duration: $DURATION" >&2
    MIDPOINT=$(awk "BEGIN {print $DURATION/2}")

    # Extract middle frame
    ffmpeg -ss "$MIDPOINT" -i "$file" -vframes 1 -q:v 2 -f image2 temp.jpg -y > /dev/null 2>&1
    # echo "Frame extracted. Calculating hash" >&2

    if [ -f temp.jpg ]; then
        HASH=$(python3 -c "import imagehash, PIL.Image; print(imagehash.phash(PIL.Image.open('temp.jpg')))")
        echo ">> $HASH | $file" >&2
        echo "$HASH | $file" >> "$OUTPUT_HASHES"
        rm temp.jpg
    else
       echo "ERR: Failed to extract frame: $file" >&2
    fi
done 3< filelist.txt

rm filelist.txt
