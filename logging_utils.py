#!/usr/bin/env python3
"""
Manage logging
"""

import logging
import logging.handlers
import os
import sys
import tempfile
from pathlib import Path


def setup_logging(log_file_path=None):
    """Setup logging with both console and file output.

    Args:
        log_file_path: Path to log file. If None, defaults to temp directory.

    Returns:
        str: Path to the log file being used

    Note:
        Priority for log file path is handled by main():
        1. Command line argument (--log-file)
        2. Environment variable (VIDEO_CONVERTER_LOG_FILE)
        3. Configuration file (logging.log_file)
        4. Default (temp directory)

        This function receives the final resolved path or None (for default).
    """
    # Use provided path or default to temp directory
    if log_file_path is None:
        temp_dir = tempfile.gettempdir()
        log_file_path = os.path.join(temp_dir, 'convert_videos.log')

    # Ensure log directory exists with error handling
    try:
        log_file = Path(log_file_path)
        log_file.parent.mkdir(parents=True, exist_ok=True)
    except (OSError, PermissionError) as e:
        # Fall back to temp directory if we can't create the specified path
        print(
            f"Warning: Cannot create log directory at {log_file_path}: {e}", file=sys.stderr)
        print(f"Falling back to temp directory", file=sys.stderr)
        temp_dir = tempfile.gettempdir()
        log_file_path = os.path.join(temp_dir, 'convert_videos.log')
        log_file = Path(log_file_path)
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError) as e2:
            print(
                f"Error: Cannot create log directory in temp: {e2}", file=sys.stderr)
            print(f"Logging to console only", file=sys.stderr)
            log_file_path = None  # Signal to skip file handler

    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler with rotation (10MB max, keep 5 backups)
    # Only add if we have a valid log path
    if log_file_path:
        try:
            file_handler = logging.handlers.RotatingFileHandler(
                log_file_path,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

            # Use root logger after setup is complete
            root_logger.info(f"Logging to file: {log_file_path}")
        except (OSError, PermissionError) as e:
            root_logger.warning(
                f"Cannot create log file at {log_file_path}: {e}")
            root_logger.warning("Logging to console only")
            log_file_path = None
    else:
        root_logger.info("Logging to console only (file logging unavailable)")

    return str(log_file_path) if log_file_path else None
