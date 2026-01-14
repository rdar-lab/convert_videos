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

import logging
import logging.handlers
import subprocess
import sys
from pathlib import Path

import configuration_manager
import subprocess_utils

logger = logging.getLogger(__name__)

# Set a basic handler for the root logger if none exists (fallback)
if not logging.root.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def get_codec(file_path, dependency_config=None):
    """Get the video codec of a file using ffprobe.

    Args:
        file_path: Path to the video file
        dependency_config: Optional dict with 'ffprobe' key specifying path to ffprobe.
                          Path should already be resolved by load_config() for PyInstaller bundles.
    """
    if dependency_config is None:
        dependency_config = {}

    ffprobe_path = dependency_config.get('ffprobe', 'ffprobe')

    command_args = [ffprobe_path, '-v', 'error', '-select_streams', 'v:0',
                    '-show_entries', 'stream=codec_name',
                    '-of', 'default=noprint_wrappers=1:nokey=1', str(file_path)]

    try:
        result = subprocess_utils.run_command(command_args, check=True)
        return result.stdout.strip()
    except Exception as e:
        logger.error(f"Error getting codec for {file_path}: {e}")
        return None


def get_duration(file_path, dependency_config=None):
    """Get the duration of a video file in seconds.

    Args:
        file_path: Path to the video file
        dependency_config: Optional dict with 'ffprobe' key specifying path to ffprobe.
                          Path should already be resolved by load_config() for PyInstaller bundles.
    """
    if dependency_config is None:
        dependency_config = {}

    ffprobe_path = dependency_config.get('ffprobe', 'ffprobe')

    try:
        result = subprocess_utils.run_command(
            [ffprobe_path, '-v', 'error',
             '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', str(file_path)],
            check=True
        )
        duration_str = result.stdout.strip()
        if duration_str:
            return int(float(duration_str))
        return 0
    except Exception as e:
        logger.error(f"Error getting duration for {file_path}: {e}")
        return 0


def find_eligible_files(target_dir, min_size_bytes=None, dependency_config=None):
    """Find all video files >= min_size_bytes that are not H.265 encoded.

    Args:
        target_dir: Directory to scan for video files
        min_size_bytes: Minimum file size threshold in bytes (default: 1GB)
        dependency_config: Optional dict with dependency paths
    """
    video_extensions = ['.mp4', '.mkv', '.mov', '.avi']
    if min_size_bytes is None:
        min_size_bytes = configuration_manager.DEFAULT_MIN_FILE_SIZE_BYTES

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

                # Skip files marked as already processed originals
                # Check for .orig.* pattern (e.g., video.orig.mp4)
                if '.orig.' in file_path.name:
                    continue

                # Check file size
                file_size = file_path.stat().st_size
                if file_size < min_size_bytes:
                    continue

                # Check codec
                codec = get_codec(file_path, dependency_config)
                if codec != 'hevc':
                    eligible_files.append((file_size, file_path))
            except OSError:
                logger.exception(f"Error processing {file_path}")

    # Sort by size (largest first)
    eligible_files.sort(reverse=True, key=lambda x: x[0])
    return [f[1] for f in eligible_files]


def convert_file(input_path, dry_run=False, preserve_original=False, output_config=None, dependency_config=None, progress_callback=None, cancellation_check=None):
    """Convert a video file using HandBrakeCLI with a configurable encoder.

    By default, uses an H.265 (HEVC) encoder, but the encoder, container
    format, preset, and quality can be customized via the output_config
    parameter (e.g., CPU x265 or GPU-accelerated nvenc_hevc).

    Args:
        input_path: Path to input video file
        dry_run: If True, only simulate conversion
        preserve_original: If True, keep original file after conversion
        output_config: Dict with output settings (format, encoder, preset, quality)
        dependency_config: Dict with dependency paths (handbrake, ffprobe)
        progress_callback: Optional callback function(percentage: float) for progress updates
        cancellation_check: Optional callback function() -> bool to check if operation should be cancelled
    """
    input_path = Path(input_path)

    # Default output configuration
    if output_config is None:
        output_config = {
            'format': 'mkv',
            'encoder': 'x265_10bit',
            'preset': 'medium',
            'quality': 24
        }

    # Default dependency configuration
    if dependency_config is None:
        dependency_config = {}

    handbrake_path = dependency_config.get('handbrake', 'HandBrakeCLI')

    output_format = output_config.get('format', 'mkv')
    encoder_type = output_config.get('encoder', 'x265_10bit')
    encoder_preset = output_config.get('preset', 'medium')
    quality = output_config.get('quality', 24)

    # Avoid collisions with existing output or temp files
    base_name = f"{input_path.stem}.converted"
    output_path = input_path.with_name(f"{base_name}.{output_format}")
    temp_output = output_path.with_suffix(f'.{output_format}.temp')

    if output_path.exists() or temp_output.exists():
        counter = 1
        while True:
            output_path = input_path.with_name(
                f"{base_name}.{counter}.{output_format}")
            temp_output = output_path.with_suffix(f'.{output_format}.temp')
            if not output_path.exists() and not temp_output.exists():
                break
            counter += 1

    logger.info(f"Starting conversion: {input_path}")
    logger.info(
        f"Encoder: {encoder_type}, Preset: {encoder_preset}, Quality: {quality}, Format: {output_format}")

    if dry_run:
        logger.info(f"[Dry Run] Would convert: {input_path} -> {output_path}")
        return True

    try:
        # Build HandBrakeCLI command based on encoder type
        cmd = [
            handbrake_path,
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
        # Helper function to choose between progress-aware and regular subprocess calls
        def run_subprocess(cmd_args, **extra_kwargs):
            if progress_callback or cancellation_check:
                return subprocess_utils.run_command_with_progress(
                    cmd_args,
                    progress_callback=progress_callback,
                    cancellation_check=cancellation_check,
                    **extra_kwargs
                )
            else:
                return subprocess_utils.run_command(cmd_args, check=True, **extra_kwargs)

        if sys.platform == 'win32':
            # Windows: Use BELOW_NORMAL_PRIORITY_CLASS (0x00004000)
            BELOW_NORMAL_PRIORITY_CLASS = 0x00004000
            run_subprocess(cmd, creationflags=BELOW_NORMAL_PRIORITY_CLASS)
        else:
            # Linux/Unix: Try to use nice if available, otherwise run without it
            try:
                command_args = ['nice', '-n', '10'] + cmd
                run_subprocess(command_args)
            except FileNotFoundError:
                # nice not available, run without it
                run_subprocess(cmd)

        # Validate and finalize
        return validate_and_finalize(input_path, temp_output, output_path, preserve_original, dependency_config)

    except subprocess.CalledProcessError as e:
        logger.error(f"Conversion failed for {input_path}: {e}")
        if temp_output.exists():
            try:
                temp_output.unlink()
            except OSError as cleanup_error:
                logger.error(
                    f"Failed to cleanup temp file {temp_output}: {cleanup_error}")
        return False


def validate_and_finalize(input_path, temp_output, final_output, preserve_original=False, dependency_config=None):
    """Validate the conversion and finalize the output.

    Args:
        input_path: Path to original input file
        temp_output: Path to temporary output file
        final_output: Path to final output file
        preserve_original: If True, keep original file
        dependency_config: Dict with dependency paths
    """
    src_duration = get_duration(input_path, dependency_config)
    out_duration = get_duration(temp_output, dependency_config)

    if src_duration == 0 or out_duration == 0:
        logger.error(
            f"❌ Could not determine duration: src={src_duration} vs out={out_duration}")
        if temp_output.exists():
            try:
                temp_output.unlink()
            except OSError as cleanup_error:
                logger.error(
                    f"Failed to cleanup temp file {temp_output}: {cleanup_error}")
        return False

    diff = abs(src_duration - out_duration)
    if diff <= 1:
        # Success - move temp to final and optionally remove/rename original
        temp_output.rename(final_output)
        if not preserve_original:
            input_path.unlink()
            logger.info(f"✅ Successfully converted: {final_output}")
        else:
            # Rename original to .orig.<ext> to mark it as processed
            # This prevents reprocessing the same file
            original_ext = input_path.suffix  # e.g., ".mp4"
            # e.g., "video.orig.mp4"
            orig_name = f"{input_path.stem}.orig{original_ext}"
            orig_path = input_path.with_name(orig_name)

            # Handle name collisions
            counter = 1
            while orig_path.exists():
                orig_name = f"{input_path.stem}.orig.{counter}{original_ext}"
                orig_path = input_path.with_name(orig_name)
                counter += 1

            try:
                input_path.rename(orig_path)
                logger.info(
                    f"✅ Successfully converted (original renamed to {orig_path.name}): {final_output}")
            except OSError as e:
                logger.error(
                    f"Failed to rename original file to {orig_path}: {repr(e)}")
                logger.info(
                    f"✅ Successfully converted (original preserved): {final_output}")
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
                failed_path = input_path.with_suffix(
                    f"{input_path.suffix}.fail_{counter}")

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
