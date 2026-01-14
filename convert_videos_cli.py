#!/usr/bin/env python3
"""
CLI-only entry point for convert_videos that always runs in background mode.
This is used for the standalone CLI executable to prevent GUI from launching.
"""

import sys
import convert_videos

import argparse
import logging
import logging.handlers
import os
import sys
import time
from pathlib import Path

import configuration_manager
import dependencies_utils
import logging_utils

logger = logging.getLogger(__name__)


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Convert video files to H.265 (HEVC) codec',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python convert_videos.py --config config.yaml     # Run with config (background mode)
  python convert_videos.py /path/to/videos
  python convert_videos.py --dry-run C:\\Videos
  python convert_videos.py --loop /path/to/videos
        """
    )
    parser.add_argument('directory',
                        nargs='?',  # Optional to allow config-only usage
                        help='Directory to scan for video files (optional; can be set in config file or GUI)')
    parser.add_argument('--config',
                        help='Path to configuration file (default: config.yaml)')
    parser.add_argument('--dry-run',
                        action='store_true',
                        help='Show what would be converted without actually converting')
    parser.add_argument('--loop',
                        action='store_true',
                        help='Run continuously, checking every hour')
    parser.add_argument('--remove-original-files',
                        action='store_true',
                        help='Remove original files after successful conversion (default: keep originals)')
    parser.add_argument('--auto-download-dependencies',
                        action='store_true',
                        help='Automatically download dependencies if not found (HandBrakeCLI, ffprobe)')
    parser.add_argument('--log-file',
                        help='Path to log file (default: temp directory, can be set via VIDEO_CONVERTER_LOG_FILE env var)')

    args = parser.parse_args()

    # First we init logging - first log of init will go to temp location
    logging_utils.setup_logging()

    # Load configuration file
    config, validation_errors = configuration_manager.load_config(
        args.config, args)

    # In case there are validation errors. Print them and return
    if validation_errors:
        for err in validation_errors:
            logger.error(err)
        parser.print_help()
        sys.exit(1)

    logging_utils.setup_logging(config['logging']['log_file'])

    # Command line arguments override config file settings
    target_directory = config['directory']
    dry_run = config['dry_run']
    loop_mode = config['loop']

    # Get remove_original_files config
    remove_original = config['remove_original_files']
    preserve_original = not remove_original

    # Get dependency paths configuration
    dependency_config = config.get('dependencies', {})

    min_file_size = config['min_file_size']

    output_config = config['output']

    # Auto-download dependencies if requested
    if args.auto_download_dependencies:
        logger.info("Auto-downloading dependencies...")
        deps_dir = Path(os.getcwd()) / "dependencies"

        handbrake_path, ffprobe_path, ffmpeg_path = dependencies_utils.download_dependencies(
            deps_dir)

        if handbrake_path and ffprobe_path and ffmpeg_path:
            # Update dependency config with downloaded paths
            if 'dependencies' not in config:
                config['dependencies'] = {}
            config['dependencies']['handbrake'] = handbrake_path
            config['dependencies']['ffprobe'] = ffprobe_path
            config['dependencies']['ffmpeg'] = ffmpeg_path
            dependency_config = config['dependencies']
            logger.info(
                f"Dependencies downloaded: HandBrakeCLI={handbrake_path}, ffprobe={ffprobe_path}, ffmpeg_path={ffmpeg_path}")
        else:
            logger.error(
                "Failed to download dependencies. Please install manually.")
            sys.exit(1)

    # Check dependencies
    if not dependencies_utils.validate_dependencies(dependency_config):
        sys.exit(1)

    # Main processing loop
    while True:
        logger.info(f"Starting scan in {target_directory}")

        files = convert_videos.find_eligible_files(
            target_directory, min_file_size, dependency_config)

        if not files:
            logger.info("No eligible files found.")
        else:
            logger.info(f"Files to convert ({len(files)}):")
            for file in files:
                logger.info(f"  {file}")

            for file in files:
                convert_videos.convert_file(file, dry_run=dry_run, preserve_original=preserve_original,
                                            output_config=output_config, dependency_config=dependency_config)

        if not loop_mode:
            break

        logger.info("Waiting 1 hour before next scan...")
        time.sleep(3600)


if __name__ == '__main__':
    main()
