#!/bin/bash
# Create a video demonstrating the GUI features

cd /tmp

# Create text descriptions
cat > gui_intro.txt << 'EOF'
Video Converter GUI Demo

The GUI provides an easy-to-use
interface for video conversion with
four main tabs:

1. Configuration
2. File Queue
3. Live Progress  
4. Results Dashboard

Let's explore each tab...
EOF

cat > gui_config.txt << 'EOF'
Tab 1: Configuration

• Set video directory to scan
• Configure minimum file size
• Choose encoder (x265, x265_10bit, nvenc)
• Adjust quality settings (0-51)
• Select output format (MKV/MP4)
• Enable/disable options
• Save/Load configuration files
EOF

cat > gui_queue.txt << 'EOF'
Tab 2: File Queue

Shows all videos waiting to be processed:

• File names and paths
• Current file sizes
• Current video codec
• Processing status
• Skip files already in HEVC format

Start processing with one click!
EOF

cat > gui_progress.txt << 'EOF'
Tab 3: Live Progress

Monitor current conversion:

• Currently processing file
• Progress bar (0-100%)
• Encoding speed (fps)
• Estimated time remaining
• Pause/Cancel options

Real-time updates during encoding!
EOF

cat > gui_results.txt << 'EOF'
Tab 4: Results Dashboard

View completed conversions:

• Success/Failure status
• Original vs new file sizes
• Space savings percentage
• Processing time
• Error messages for failures

Export reports & retry failed files!
EOF

# Create images from text using ImageMagick
for file in gui_intro.txt gui_config.txt gui_queue.txt gui_progress.txt gui_results.txt; do
    base=$(basename "$file" .txt)
    convert -size 1280x720 xc:black \
        -font DejaVu-Sans -pointsize 36 -fill white \
        -gravity center -annotate +0+0 "$(cat $file)" \
        "${base}.png"
done

# Create video from images with timing
ffmpeg -y -loop 1 -t 3 -i gui_intro.png \
    -loop 1 -t 4 -i gui_config.png \
    -loop 1 -t 4 -i gui_queue.png \
    -loop 1 -t 4 -i gui_progress.png \
    -loop 1 -t 4 -i gui_results.png \
    -filter_complex "[0:v][1:v][2:v][3:v][4:v]concat=n=5:v=1[outv]" \
    -map "[outv]" -pix_fmt yuv420p -c:v libx264 -crf 23 -r 30 \
    /home/runner/work/convert_videos/convert_videos/docs/videos/gui-demo-real.mp4

echo "GUI video created!"
