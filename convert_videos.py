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
import yaml
import re


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# Constants
SUPPORTED_ENCODERS = ['x265', 'x265_10bit', 'nvenc_hevc']
SIZE_MULTIPLIERS = {
    'B': 1,
    'KB': 1024,
    'MB': 1024 ** 2,
    'GB': 1024 ** 3
}
DEFAULT_MIN_FILE_SIZE_BYTES = 1024 ** 3  # 1GB
FILE_SIZE_PATTERN = re.compile(r'^(\d+(?:\.\d+)?)\s*(GB|MB|KB|B)?$')


def validate_encoder(encoder_type):
    """Validate that the encoder type is supported."""
    if encoder_type not in SUPPORTED_ENCODERS:
        return False
    return True


def parse_file_size(size_str):
    """Parse file size string (e.g., '1GB', '500MB') to bytes."""
    if isinstance(size_str, int):
        if size_str < 0:
            raise ValueError(f"File size must be non-negative: {size_str}")
        return size_str
    
    size_str = str(size_str).strip().upper()
    
    # Match number and optional unit
    match = FILE_SIZE_PATTERN.match(size_str)
    if not match:
        raise ValueError(f"Invalid file size format: {size_str}")
    
    number = float(match.group(1))
    unit = match.group(2) or 'B'
    
    return int(number * SIZE_MULTIPLIERS[unit])


def load_config(config_path=None):
    """Load configuration from YAML file."""
    default_config = {
        'directory': None,
        'min_file_size': '1GB',
        'output': {
            'format': 'mkv',
            'encoder': 'x265_10bit',
            'preset': 'medium',
            'quality': 24
        },
        'preserve_original': False,
        'loop': False,
        'dry_run': False
    }
    
    if config_path is None:
        # Look for config.yaml in current directory
        config_path = Path('config.yaml')
    else:
        config_path = Path(config_path)
    
    if not config_path.exists():
        logger.debug(f"Config file not found: {config_path}, using defaults")
        return default_config
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            user_config = yaml.safe_load(f)
            # Handle None, False, or other falsy/invalid values
            if not isinstance(user_config, dict):
                user_config = {}
        
        # Merge with defaults
        config = {**default_config, **user_config}
        
        # Merge output settings if present
        if 'output' in user_config and user_config['output'] is not None:
            config['output'] = {**default_config['output'], **user_config['output']}
        
        logger.info(f"Loaded configuration from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Error loading config file {config_path}: {e}")
        return default_config


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


def find_eligible_files(target_dir, min_size_bytes=None):
    """Find all video files >= min_size_bytes that are not H.265 encoded."""
    video_extensions = ['.mp4', '.mkv', '.mov', '.avi']
    if min_size_bytes is None:
        min_size_bytes = DEFAULT_MIN_FILE_SIZE_BYTES
    
    eligible_files = []
    target_path = Path(target_dir)
    
    logger.info(f"Scanning directory: {target_dir}")
    logger.info(f"Minimum file size: {min_size_bytes / (1024**3):.2f} GB")
    
    for ext in video_extensions:
        for file_path in target_path.rglob(f'*{ext}'):
            try:
                # Skip files marked as failed conversions
                # Check for .fail suffix (e.g., video.mp4.fail, video.mp4.fail_1)
                if file_path.suffix == '.fail' or '.fail_' in file_path.name:
                    continue
                
                # Check file size
                file_size = file_path.stat().st_size
                if file_size < min_size_bytes:
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


def convert_file(input_path, dry_run=False, preserve_original=False, output_config=None):
    """Convert a video file to H.265 using HandBrakeCLI."""
    input_path = Path(input_path)
    
    # Default output configuration
    if output_config is None:
        output_config = {
            'format': 'mkv',
            'encoder': 'x265_10bit',
            'preset': 'medium',
            'quality': 24
        }
    
    output_format = output_config.get('format', 'mkv')
    encoder_type = output_config.get('encoder', 'x265_10bit')
    encoder_preset = output_config.get('preset', 'medium')
    quality = output_config.get('quality', 24)
    
    # Validate encoder type early
    if not validate_encoder(encoder_type):
        logger.error(f"Unsupported encoder type: {encoder_type}. Supported: {', '.join(SUPPORTED_ENCODERS)}")
        return False
    
    # Avoid collisions with existing output or temp files
    base_name = f"{input_path.stem} - New"
    output_path = input_path.with_name(f"{base_name}.{output_format}")
    temp_output = output_path.with_suffix(f'.{output_format}.temp')
    
    if output_path.exists() or temp_output.exists():
        counter = 1
        while True:
            output_path = input_path.with_name(f"{base_name} ({counter}).{output_format}")
            temp_output = output_path.with_suffix(f'.{output_format}.temp')
            if not output_path.exists() and not temp_output.exists():
                break
            counter += 1
    
    logger.info(f"Starting conversion: {input_path}")
    logger.info(f"Encoder: {encoder_type}, Preset: {encoder_preset}, Quality: {quality}, Format: {output_format}")
    
    if dry_run:
        logger.info(f"[Dry Run] Would convert: {input_path} -> {output_path}")
        return True
    
    try:
        # Build HandBrakeCLI command based on encoder type
        cmd = [
            'HandBrakeCLI',
            '-i', str(input_path),
            '-o', str(temp_output),
            '-f', output_format,
            '--all-audio',
            '--aencoder', 'copy',
            '--all-subtitles'
        ]
        
        # Configure encoder based on type
        if encoder_type == 'nvenc_hevc':
            # NVIDIA GPU acceleration
            cmd.extend([
                '-e', 'nvenc_h265',
                '--encoder-preset', encoder_preset,
                '-q', str(quality)
            ])
        elif encoder_type == 'x265_10bit':
            # x265 with 10-bit color depth
            cmd.extend([
                '-e', 'x265',
                '--encoder-preset', encoder_preset,
                '--encoder-profile', 'main10',
                '-q', str(quality)
            ])
        elif encoder_type == 'x265':
            # Standard x265 encoding (8-bit)
            cmd.extend([
                '-e', 'x265',
                '--encoder-preset', encoder_preset,
                '-q', str(quality)
            ])
        
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
  python convert_videos.py --config config.yaml
        """
    )
    parser.add_argument('directory', 
                       nargs='?',  # Optional to allow config-only usage
                       help='Directory to scan for video files')
    parser.add_argument('--config',
                       help='Path to configuration file (default: config.yaml)')
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
    
    # Load configuration file
    config = load_config(args.config)
    
    # Command line arguments override config file settings
    target_directory = args.directory or config.get('directory')
    dry_run = args.dry_run or config.get('dry_run', False)
    loop_mode = args.loop or config.get('loop', False)
    preserve_original = args.preserve_original or config.get('preserve_original', False)
    
    # Check for environment variable override
    preserve_original = preserve_original or os.getenv("VIDEO_CONVERTER_PRESERVE_ORIGINAL", "").lower() in ("1", "true", "yes")
    
    # Parse min file size from config
    try:
        min_file_size = parse_file_size(config.get('min_file_size', '1GB'))
    except ValueError as e:
        logger.error(f"Invalid min_file_size in config: {e}")
        sys.exit(1)
    
    # Get output configuration
    output_config = config.get('output', {})
    
    # Validate encoder type early
    encoder_type = output_config.get('encoder', 'x265_10bit')
    if not validate_encoder(encoder_type):
        logger.error(f"Unsupported encoder type in config: '{encoder_type}'. Supported encoders: {', '.join(SUPPORTED_ENCODERS)}")
        sys.exit(1)
    
    # Validate directory
    if not target_directory:
        logger.error("Error: No directory specified. Provide via command line or config file.")
        parser.print_help()
        sys.exit(1)
    
    if not os.path.isdir(target_directory):
        logger.error(f"Error: '{target_directory}' is not a valid directory.")
        sys.exit(1)
    
    # Check dependencies
    check_dependencies()
    
    # Main processing loop
    while True:
        logger.info(f"Starting scan in {target_directory}")
        
        files = find_eligible_files(target_directory, min_file_size)
        
        if not files:
            logger.info("No eligible files found.")
        else:
            logger.info(f"Files to convert ({len(files)}):")
            for file in files:
                logger.info(f"  {file}")
            
            for file in files:
                convert_file(file, dry_run=dry_run, preserve_original=preserve_original, 
                           output_config=output_config)
        
        if not loop_mode:
            break
        
        logger.info("Waiting 1 hour before next scan...")
        time.sleep(3600)


if __name__ == '__main__':
    main()
