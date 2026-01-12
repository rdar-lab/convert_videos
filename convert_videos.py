#!/usr/bin/env python3
"""
Video conversion script to convert videos to H.265 (HEVC) codec.
Works on Windows, Linux, and macOS.

This script will:
1. Find all video files >= 1GB in the specified directory
2. Check if they are already encoded with H.265/HEVC
3. Convert non-HEVC videos using HandBrakeCLI
4. Validate the conversion by comparing durations
"""

import os
import sys
import subprocess
import argparse
import logging
from pathlib import Path
import time


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def check_dependencies():
    """Check if required dependencies are installed."""
    dependencies = ['ffprobe', 'HandBrakeCLI']
    missing = []
    
    for dep in dependencies:
        try:
            subprocess.run([dep, '--version'], 
                          stdout=subprocess.PIPE, 
                          stderr=subprocess.PIPE,
                          check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            missing.append(dep)
    
    if missing:
        logger.error(f"Missing dependencies: {', '.join(missing)}")
        logger.error("Please install the required dependencies. See WINDOWS_INSTALL.md or README.md for instructions.")
        sys.exit(1)


def get_codec(file_path):
    """Get the video codec of a file using ffprobe."""
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-select_streams', 'v:0', 
             '-show_entries', 'stream=codec_name',
             '-of', 'default=noprint_wrappers=1:nokey=1', str(file_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"Error getting codec for {file_path}: {e}")
        return None


def get_duration(file_path):
    """Get the duration of a video file in seconds."""
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error',
             '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', str(file_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        duration_str = result.stdout.strip()
        if duration_str:
            return int(float(duration_str))
        return 0
    except (subprocess.CalledProcessError, ValueError) as e:
        logger.error(f"Error getting duration for {file_path}: {e}")
        return 0


def find_eligible_files(target_dir):
    """Find all video files >= 1GB that are not H.265 encoded."""
    video_extensions = ['.mp4', '.mkv', '.mov', '.avi']
    min_size = 1 * 1024 * 1024 * 1024  # 1GB in bytes
    
    eligible_files = []
    target_path = Path(target_dir)
    
    logger.info(f"Scanning directory: {target_dir}")
    
    for ext in video_extensions:
        for file_path in target_path.rglob(f'*{ext}'):
            try:
                # Skip files marked as failed conversions
                # Check for .fail suffix (e.g., video.mp4.fail, video.mp4.fail_1)
                if file_path.suffix == '.fail' or '.fail_' in file_path.name:
                    continue
                
                # Check file size
                file_size = file_path.stat().st_size
                if file_size < min_size:
                    continue
                
                # Check codec
                codec = get_codec(file_path)
                if codec != 'hevc':
                    eligible_files.append((file_size, file_path))
            except OSError:
                logger.exception(f"Error processing {file_path}")
    
    # Sort by size (largest first)
    eligible_files.sort(reverse=True, key=lambda x: x[0])
    return [f[1] for f in eligible_files]


def convert_file(input_path, dry_run=False, preserve_original=False):
    """Convert a video file to H.265 using HandBrakeCLI."""
    input_path = Path(input_path)
    
    # Avoid collisions with existing output or temp files
    base_name = f"{input_path.stem} - New"
    output_path = input_path.with_name(f"{base_name}.mkv")
    temp_output = output_path.with_suffix('.mkv.temp')
    
    if output_path.exists() or temp_output.exists():
        counter = 1
        while True:
            output_path = input_path.with_name(f"{base_name} ({counter}).mkv")
            temp_output = output_path.with_suffix('.mkv.temp')
            if not output_path.exists() and not temp_output.exists():
                break
            counter += 1
    
    logger.info(f"Starting conversion: {input_path}")
    
    if dry_run:
        logger.info(f"[Dry Run] Would convert: {input_path} -> {output_path}")
        return True
    
    try:
        # Run HandBrakeCLI with appropriate settings
        cmd = [
            'HandBrakeCLI',
            '-i', str(input_path),
            '-o', str(temp_output),
            '-e', 'x265',
            '--encoder-preset', 'medium',
            '--encoder-profile', 'main10',
            '-q', '24',
            '-f', 'mkv',
            '--all-audio',
            '--aencoder', 'copy',
            '--all-subtitles'
        ]
        
        # Run with lower priority on Windows and Linux
        if sys.platform == 'win32':
            # Windows: Use BELOW_NORMAL_PRIORITY_CLASS (0x00004000)
            BELOW_NORMAL_PRIORITY_CLASS = 0x00004000
            subprocess.run(cmd, check=True, 
                          creationflags=BELOW_NORMAL_PRIORITY_CLASS)
        else:
            # Linux/Unix: Try to use nice if available, otherwise run without it
            try:
                subprocess.run(['nice', '-n', '10'] + cmd, check=True)
            except FileNotFoundError:
                # nice not available, run without it
                subprocess.run(cmd, check=True)
        
        # Validate and finalize
        return validate_and_finalize(input_path, temp_output, output_path, preserve_original)
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Conversion failed for {input_path}: {e}")
        if temp_output.exists():
            try:
                temp_output.unlink()
            except OSError as cleanup_error:
                logger.error(f"Failed to cleanup temp file {temp_output}: {cleanup_error}")
        return False


def validate_and_finalize(input_path, temp_output, final_output, preserve_original=False):
    """Validate the conversion and finalize the output."""
    src_duration = get_duration(input_path)
    out_duration = get_duration(temp_output)
    
    if src_duration == 0 or out_duration == 0:
        logger.error(f"❌ Could not determine duration: src={src_duration} vs out={out_duration}")
        if temp_output.exists():
            try:
                temp_output.unlink()
            except OSError as cleanup_error:
                logger.error(f"Failed to cleanup temp file {temp_output}: {cleanup_error}")
        return False
    
    diff = abs(src_duration - out_duration)
    if diff <= 1:
        # Success - move temp to final and optionally remove original
        temp_output.rename(final_output)
        if not preserve_original:
            input_path.unlink()
            logger.info(f"✅ Successfully converted: {final_output}")
        else:
            logger.info(f"✅ Successfully converted (original preserved): {final_output}")
        return True
    else:
        # Duration mismatch - keep both files but mark original as failed
        temp_output.rename(final_output)
        
        # Create unique .fail filename atomically to handle race conditions
        base_failed_path = input_path.with_suffix(input_path.suffix + '.fail')
        counter = 0
        while True:
            if counter == 0:
                failed_path = base_failed_path
            else:
                failed_path = input_path.with_suffix(f"{input_path.suffix}.fail_{counter}")
            
            try:
                input_path.rename(failed_path)
                logger.error(
                    f"❌ Duration mismatch: src={src_duration} vs out={out_duration} for file {input_path}"
                )
                break
            except FileExistsError:
                # Another process created this path; try the next suffix
                counter += 1
                continue
            except OSError as e:
                logger.error(
                    f"❌ Failed to rename original file '{input_path}' to '{failed_path}': "
                    f"{type(e).__name__}: {e}",
                    exc_info=True,
                )
                break
        
        return False


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Convert video files to H.265 (HEVC) codec',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python convert_videos.py /path/to/videos
  python convert_videos.py --dry-run C:\\Videos
  python convert_videos.py --loop /path/to/videos
        """
    )
    parser.add_argument('directory', 
                       help='Directory to scan for video files')
    parser.add_argument('--dry-run', 
                       action='store_true',
                       help='Show what would be converted without actually converting')
    parser.add_argument('--loop', 
                       action='store_true',
                       help='Run continuously, checking every hour')
    parser.add_argument('--preserve-original', 
                       action='store_true',
                       help='Keep original files after successful conversion (default: remove)')
    
    args = parser.parse_args()
    
    # Validate directory
    if not os.path.isdir(args.directory):
        logger.error(f"Error: '{args.directory}' is not a valid directory.")
        sys.exit(1)
    
    # Check dependencies
    check_dependencies()
    
    # Check for environment variable override
    preserve_original = args.preserve_original or os.getenv("VIDEO_CONVERTER_PRESERVE_ORIGINAL", "").lower() in ("1", "true", "yes")
    
    # Main processing loop
    while True:
        logger.info(f"Starting scan in {args.directory}")
        
        files = find_eligible_files(args.directory)
        
        if not files:
            logger.info("No eligible files found.")
        else:
            logger.info(f"Files to convert ({len(files)}):")
            for file in files:
                logger.info(f"  {file}")
            
            for file in files:
                convert_file(file, dry_run=args.dry_run, preserve_original=preserve_original)
        
        if not args.loop:
            break
        
        logger.info("Waiting 1 hour before next scan...")
        time.sleep(3600)


if __name__ == '__main__':
    main()
