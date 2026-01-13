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
import logging.handlers
from pathlib import Path
import time
import yaml
import re
import platform
import urllib.request
import tarfile
import zipfile
import shutil
import tempfile


# Get logger for this module
# Note: Primary logging configuration is done via setup_logging() function called in main()
# Basic configuration is set here as fallback for early logging or library usage
logger = logging.getLogger(__name__)

# Set a basic handler for the root logger if none exists (fallback)
if not logging.root.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


# Constants
SUPPORTED_ENCODERS = ['x265', 'x265_10bit', 'nvenc_hevc']
SUPPORTED_FORMATS = ['mkv', 'mp4']
# x265 CPU encoder presets
X265_PRESETS = ['ultrafast', 'superfast', 'veryfast', 'faster', 'fast', 'medium', 'slow', 'slower', 'veryslow']
# NVENC GPU encoder presets (HandBrake-compatible)
NVENC_PRESETS = ['default', 'fast', 'medium', 'slow']
# All supported presets (combined)
SUPPORTED_PRESETS = X265_PRESETS + NVENC_PRESETS
SIZE_MULTIPLIERS = {
    'B': 1,
    'KB': 1024,
    'MB': 1024 ** 2,
    'GB': 1024 ** 3
}
DEFAULT_MIN_FILE_SIZE_BYTES = 1024 ** 3  # 1GB
FILE_SIZE_PATTERN = re.compile(r'^(\d+(?:\.\d+)?)\s*(GB|MB|KB|B)?$', re.IGNORECASE)


def get_bundled_path():
    """Get the path to the bundled resources directory when running as a PyInstaller executable.
    
    Returns:
        Path object pointing to the bundle directory, or None if not running as a bundle
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Running as a PyInstaller bundle
        return Path(sys._MEIPASS)
    return None


def find_dependency_path(dependency_name, config_path=None):
    """Find the path to a dependency executable.
    
    Searches in this order:
    1. If config_path is provided and is an absolute path that exists, use it directly
    2. If running as PyInstaller bundle, check sys._MEIPASS directory
    3. Use config_path if provided (for PATH resolution), otherwise use dependency_name
    
    Args:
        dependency_name: Name of the dependency (e.g., 'HandBrakeCLI', 'ffprobe')
        config_path: Optional path from configuration
    
    Returns:
        str: Path to the dependency executable
    """
    # If config provides an absolute path that exists, use it directly (highest priority)
    if config_path:
        config_path_obj = Path(config_path)
        if config_path_obj.is_absolute() and config_path_obj.exists():
            return str(config_path)
    
    # Check if running as PyInstaller bundle
    bundle_dir = get_bundled_path()
    if bundle_dir:
        # Look for dependency in bundle directory
        # Check for .exe extension on Windows
        if platform.system() == 'Windows':
            exe_name = dependency_name if dependency_name.endswith('.exe') else f'{dependency_name}.exe'
        else:
            exe_name = dependency_name
        
        bundled_path = bundle_dir / exe_name
        if bundled_path.exists():
            logger.debug(f"Found bundled dependency: {bundled_path}")
            return str(bundled_path)
    
    # Fall back to config_path if provided, otherwise use dependency_name
    # (will be resolved via PATH)
    return config_path if config_path else dependency_name


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
        print(f"Warning: Cannot create log directory at {log_file_path}: {e}", file=sys.stderr)
        print(f"Falling back to temp directory", file=sys.stderr)
        temp_dir = tempfile.gettempdir()
        log_file_path = os.path.join(temp_dir, 'convert_videos.log')
        log_file = Path(log_file_path)
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError) as e2:
            print(f"Error: Cannot create log directory in temp: {e2}", file=sys.stderr)
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
            root_logger.warning(f"Cannot create log file at {log_file_path}: {e}")
            root_logger.warning("Logging to console only")
            log_file_path = None
    else:
        root_logger.info("Logging to console only (file logging unavailable)")
    
    return str(log_file_path) if log_file_path else None


def run_command(command_args, **kwargs):
    """Run a subprocess command and log all details.
    
    Args:
        command_args: List of command arguments
        **kwargs: Additional arguments to pass to subprocess.run
                 Note: stdout and stderr will be set to PIPE for logging unless
                       explicitly set to None by the caller
    
    Returns:
        subprocess.CompletedProcess: Result of the command execution
    """
    # Maximum length for logged output to prevent huge log files
    MAX_OUTPUT_LENGTH = 2000
    
    logger.info(f"Running command: {' '.join(str(arg) for arg in command_args)}")
    
    # Capture output for logging unless explicitly disabled
    # Allow caller to explicitly set stdout/stderr to None if they don't want capture
    if 'stdout' not in kwargs:
        kwargs['stdout'] = subprocess.PIPE
    if 'stderr' not in kwargs:
        kwargs['stderr'] = subprocess.PIPE
    if 'text' not in kwargs:
        kwargs['text'] = True
    
    try:
        result = subprocess.run(command_args, **kwargs)
        
        # Log stdout if present and captured, with truncation for large output
        if result.stdout:
            stdout_stripped = result.stdout.strip()
            if len(stdout_stripped) > MAX_OUTPUT_LENGTH:
                logger.info(f"Command stdout (truncated to {MAX_OUTPUT_LENGTH} chars): {stdout_stripped[:MAX_OUTPUT_LENGTH]}... [output truncated, total length: {len(stdout_stripped)} chars]")
            else:
                logger.info(f"Command stdout: {stdout_stripped}")
        
        # Log stderr if present and captured, with truncation for large output
        if result.stderr:
            stderr_stripped = result.stderr.strip()
            if result.returncode == 0:
                # Some tools write normal output to stderr
                if len(stderr_stripped) > MAX_OUTPUT_LENGTH:
                    logger.info(f"Command stderr (truncated to {MAX_OUTPUT_LENGTH} chars): {stderr_stripped[:MAX_OUTPUT_LENGTH]}... [output truncated, total length: {len(stderr_stripped)} chars]")
                else:
                    logger.info(f"Command stderr: {stderr_stripped}")
            else:
                if len(stderr_stripped) > MAX_OUTPUT_LENGTH:
                    logger.error(f"Command stderr (truncated to {MAX_OUTPUT_LENGTH} chars): {stderr_stripped[:MAX_OUTPUT_LENGTH]}... [output truncated, total length: {len(stderr_stripped)} chars]")
                else:
                    logger.error(f"Command stderr: {stderr_stripped}")
        
        # Log exit code
        logger.info(f"Command exit code: {result.returncode}")
        
        return result
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with exit code {e.returncode}")
        if e.stdout:
            stdout_stripped = e.stdout.strip()
            if len(stdout_stripped) > MAX_OUTPUT_LENGTH:
                logger.error(f"Command stdout (truncated to {MAX_OUTPUT_LENGTH} chars): {stdout_stripped[:MAX_OUTPUT_LENGTH]}... [output truncated, total length: {len(stdout_stripped)} chars]")
            else:
                logger.error(f"Command stdout: {stdout_stripped}")
        if e.stderr:
            stderr_stripped = e.stderr.strip()
            if len(stderr_stripped) > MAX_OUTPUT_LENGTH:
                logger.error(f"Command stderr (truncated to {MAX_OUTPUT_LENGTH} chars): {stderr_stripped[:MAX_OUTPUT_LENGTH]}... [output truncated, total length: {len(stderr_stripped)} chars]")
            else:
                logger.error(f"Command stderr: {stderr_stripped}")
        raise
    except Exception as e:
        logger.error(f"Command execution error: {type(e).__name__}: {e}")
        raise


def validate_encoder(encoder_type):
    """Validate that the encoder type is supported."""
    return encoder_type in SUPPORTED_ENCODERS


def validate_format(format_type):
    """Validate that the output format is supported."""
    return format_type in SUPPORTED_FORMATS


def validate_preset(preset):
    """Validate that the encoder preset is supported."""
    return preset in SUPPORTED_PRESETS


def validate_quality(quality):
    """Validate that the quality value is in the valid range (0-51)."""
    try:
        quality_int = int(quality)
        return 0 <= quality_int <= 51
    except (TypeError, ValueError):
        return False


def map_preset_for_encoder(preset, encoder_type):
    """Map x265-style presets to encoder-specific presets when needed.
    
    For x265/x265_10bit: returns the preset as-is if valid
    For nvenc_hevc: maps x265 presets to NVENC equivalents, or returns NVENC preset as-is
    """
    if encoder_type in ['x265', 'x265_10bit']:
        # x265 encoders use their own preset names
        if preset in X265_PRESETS:
            return preset
        # If using an NVENC preset with x265, map to closest equivalent
        nvenc_to_x265_map = {
            'default': 'medium',
            'slow': 'slow',
            'medium': 'medium',
            'fast': 'fast'
        }
        return nvenc_to_x265_map.get(preset, 'medium')
    
    elif encoder_type == 'nvenc_hevc':
        # NVENC encoder: map x265 presets to NVENC equivalents
        if preset in NVENC_PRESETS:
            # Already an NVENC preset
            return preset
        
        # Map x265 presets to NVENC presets
        x265_to_nvenc_map = {
            'ultrafast': 'fast',
            'superfast': 'fast',
            'veryfast': 'fast',
            'faster': 'fast',
            'fast': 'fast',
            'medium': 'medium',
            'slow': 'slow',
            'slower': 'slow',
            'veryslow': 'slow'
        }
        return x265_to_nvenc_map.get(preset, 'medium')
    
    return preset



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
    """Load configuration from YAML file.
    
    After loading, resolves dependency paths to check for bundled executables
    in PyInstaller bundles. This ensures all consumers of the config receive
    properly resolved paths.
    """
    default_config = {
        'directory': None,
        'min_file_size': '1GB',
        'output': {
            'format': 'mkv',
            'encoder': 'x265_10bit',
            'preset': 'medium',
            'quality': 24
        },
        'dependencies': {
            'handbrake': 'HandBrakeCLI',
            'ffprobe': 'ffprobe'
        },
        'logging': {
            'log_file': None  # None means default to temp directory
        },
        'remove_original_files': False,
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
        config = default_config
    else:
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = yaml.safe_load(f)
                # Handle None, False, or other falsy/invalid values
                if not isinstance(user_config, dict):
                    user_config = {}
            
            # Merge with defaults
            config = {**default_config, **user_config}
            
            # Merge output settings if present, handling None and type safety
            if 'output' in user_config:
                if user_config['output'] is None:
                    # User explicitly set output: null; restore default nested output config
                    config['output'] = default_config['output']
                elif isinstance(user_config['output'], dict):
                    # Merge user-provided output settings into the default output config
                    config['output'] = {**default_config['output'], **user_config['output']}
                else:
                    # Invalid output type; fall back to defaults to avoid runtime errors
                    config['output'] = default_config['output']
            
            # Merge dependencies settings if present, handling None and type safety
            if 'dependencies' in user_config:
                if user_config['dependencies'] is None:
                    # User explicitly set dependencies: null; restore default dependencies config
                    config['dependencies'] = default_config['dependencies']
                elif isinstance(user_config['dependencies'], dict):
                    # Merge user-provided dependencies settings into the default dependencies config
                    config['dependencies'] = {**default_config['dependencies'], **user_config['dependencies']}
                else:
                    # Invalid dependencies type; fall back to defaults to avoid runtime errors
                    config['dependencies'] = default_config['dependencies']
            
            # Merge logging settings if present, handling None and type safety
            if 'logging' in user_config:
                if user_config['logging'] is None:
                    # User explicitly set logging: null; restore default logging config
                    config['logging'] = default_config['logging']
                elif isinstance(user_config['logging'], dict):
                    # Merge user-provided logging settings into the default logging config
                    config['logging'] = {**default_config['logging'], **user_config['logging']}
                else:
                    # Invalid logging type; fall back to defaults to avoid runtime errors
                    config['logging'] = default_config['logging']
            
            logger.info(f"Loaded configuration from {config_path}")
        except (OSError, IOError, yaml.YAMLError) as e:
            logger.error(f"Error loading config file {config_path}: {e}")
            config = default_config
    
    # Resolve dependency paths after loading configuration
    # This checks for bundled executables in PyInstaller bundles and resolves paths
    config['dependencies']['handbrake'] = find_dependency_path(
        'HandBrakeCLI', 
        config['dependencies'].get('handbrake')
    )
    config['dependencies']['ffprobe'] = find_dependency_path(
        'ffprobe',
        config['dependencies'].get('ffprobe')
    )
    
    return config


def check_dependencies(dependency_paths=None):
    """Check if required dependencies are installed.
    
    Args:
        dependency_paths: Optional dict with 'handbrake' and 'ffprobe' keys
                         specifying paths to executables. If None, uses default names.
                         
    Note:
        Paths should already be resolved by load_config() to handle PyInstaller bundles.
    """
    if dependency_paths is None:
        dependency_paths = {
            'handbrake': 'HandBrakeCLI',
            'ffprobe': 'ffprobe'
        }
    
    dependencies = {
        'ffprobe': dependency_paths.get('ffprobe', 'ffprobe'),
        'HandBrakeCLI': dependency_paths.get('handbrake', 'HandBrakeCLI')
    }
    missing = []
    
    for name, path in dependencies.items():
        try:
            command_args = [path, '--version']
            run_command(command_args, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            missing.append(f"{name} (path: {path})")
    
    if missing:
        logger.error(f"Missing dependencies: {', '.join(missing)}")
        logger.error("Please install the required dependencies. See WINDOWS_INSTALL.md or README.md for instructions.")
        sys.exit(1)


def check_single_dependency(command):
    """Check if a single dependency command is available.
    
    Args:
        command: Command name or path to check
        
    Returns:
        tuple: (success: bool, error_message: str or None)
               - (True, None) if command is valid
               - (False, "not_found") if command not found
               - (False, "invalid") if command exists but is not valid
               - (False, "timeout") if command timed out
    """
    # Try both --version (for HandBrakeCLI) and -version (for ffprobe/ffmpeg)
    for version_flag in ['--version', '-version']:
        try:
            command_args = [command, version_flag]
            run_command(command_args, check=True, timeout=5)
            return True, None
        except FileNotFoundError:
            return False, "not_found"
        except subprocess.CalledProcessError:
            # Try next version flag
            continue
        except subprocess.TimeoutExpired:
            return False, "timeout"
    
    # If both version flags failed, the executable exists but is invalid
    return False, "invalid"


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
        result = run_command(command_args, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
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
        result = run_command(
            [ffprobe_path, '-v', 'error',
             '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', str(file_path)],
            check=True
        )
        duration_str = result.stdout.strip()
        if duration_str:
            return int(float(duration_str))
        return 0
    except (subprocess.CalledProcessError, ValueError) as e:
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


def convert_file(input_path, dry_run=False, preserve_original=False, output_config=None, dependency_config=None):
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
    
    # Validate output format
    if not validate_format(output_format):
        logger.error(f"Unsupported output format: {output_format}. Supported: {', '.join(SUPPORTED_FORMATS)}")
        return False
    
    # Validate encoder type
    if not validate_encoder(encoder_type):
        logger.error(f"Unsupported encoder type: {encoder_type}. Supported: {', '.join(SUPPORTED_ENCODERS)}")
        return False
    
    # Validate encoder preset
    if not validate_preset(encoder_preset):
        logger.error(f"Unsupported encoder preset: {encoder_preset}. Supported: {', '.join(SUPPORTED_PRESETS)}")
        return False
    
    # Validate quality parameter
    if not validate_quality(quality):
        logger.error(f"Invalid quality value: {quality!r}. Must be an integer between 0 and 51.")
        return False
    
    # Map preset to encoder-specific preset
    effective_preset = map_preset_for_encoder(encoder_preset, encoder_type)
    if effective_preset != encoder_preset:
        logger.info(f"Mapped preset '{encoder_preset}' to '{effective_preset}' for encoder '{encoder_type}'")
    
    # Avoid collisions with existing output or temp files
    base_name = f"{input_path.stem}.converted"
    output_path = input_path.with_name(f"{base_name}.{output_format}")
    temp_output = output_path.with_suffix(f'.{output_format}.temp')
    
    if output_path.exists() or temp_output.exists():
        counter = 1
        while True:
            output_path = input_path.with_name(f"{base_name}.{counter}.{output_format}")
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
                '--encoder-preset', effective_preset,
                '-q', str(quality)
            ])
        elif encoder_type == 'x265_10bit':
            # x265 with 10-bit color depth
            cmd.extend([
                '-e', 'x265',
                '--encoder-preset', effective_preset,
                '--encoder-profile', 'main10',
                '-q', str(quality)
            ])
        elif encoder_type == 'x265':
            # Standard x265 encoding (8-bit)
            cmd.extend([
                '-e', 'x265',
                '--encoder-preset', effective_preset,
                '-q', str(quality)
            ])
        
        # Run with lower priority on Windows and Linux
        if sys.platform == 'win32':
            # Windows: Use BELOW_NORMAL_PRIORITY_CLASS (0x00004000)
            BELOW_NORMAL_PRIORITY_CLASS = 0x00004000
            run_command(cmd, check=True, creationflags=BELOW_NORMAL_PRIORITY_CLASS)
        else:
            # Linux/Unix: Try to use nice if available, otherwise run without it
            try:
                command_args = ['nice', '-n', '10'] + cmd
                run_command(command_args, check=True)
            except FileNotFoundError:
                # nice not available, run without it
                run_command(cmd, check=True)
        
        # Validate and finalize
        return validate_and_finalize(input_path, temp_output, output_path, preserve_original, dependency_config)
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Conversion failed for {input_path}: {e}")
        if temp_output.exists():
            try:
                temp_output.unlink()
            except OSError as cleanup_error:
                logger.error(f"Failed to cleanup temp file {temp_output}: {cleanup_error}")
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
        logger.error(f"❌ Could not determine duration: src={src_duration} vs out={out_duration}")
        if temp_output.exists():
            try:
                temp_output.unlink()
            except OSError as cleanup_error:
                logger.error(f"Failed to cleanup temp file {temp_output}: {cleanup_error}")
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
            orig_name = f"{input_path.stem}.orig{original_ext}"  # e.g., "video.orig.mp4"
            orig_path = input_path.with_name(orig_name)
            
            # Handle name collisions
            counter = 1
            while orig_path.exists():
                orig_name = f"{input_path.stem}.orig.{counter}{original_ext}"
                orig_path = input_path.with_name(orig_name)
                counter += 1
            
            try:
                input_path.rename(orig_path)
                logger.info(f"✅ Successfully converted (original renamed to {orig_path.name}): {final_output}")
            except OSError as e:
                logger.error(f"Failed to rename original file to {orig_path}: {repr(e)}")
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


def download_dependencies(progress_callback=None):
    """
    Download HandBrakeCLI and ffprobe to ./dependencies directory.
    
    Args:
        progress_callback: Optional callback function to report progress.
                          Called with status messages as strings.
    
    Returns:
        tuple: (handbrake_path, ffprobe_path) as strings, or (None, None) on failure
    """
    try:
        system = platform.system()
        machine = platform.machine().lower()
        
        # Create dependencies directory
        deps_dir = Path(os.getcwd()) / "dependencies"
        deps_dir.mkdir(exist_ok=True)
        
        if progress_callback:
            progress_callback("Detecting platform...")
        logger.info("Detecting platform...")
        
        # Determine executable names based on platform
        if system == "Windows":
            handbrake_exe = "HandBrakeCLI.exe"
            ffprobe_exe = "ffprobe.exe"
        else:
            handbrake_exe = "HandBrakeCLI"
            ffprobe_exe = "ffprobe"
        
        # Check if dependencies already exist
        handbrake_path = deps_dir / handbrake_exe
        ffprobe_path = deps_dir / ffprobe_exe
        
        if handbrake_path.exists() and ffprobe_path.exists():
            # Validate existing dependencies
            handbrake_valid, _ = check_single_dependency(str(handbrake_path))
            ffprobe_valid, _ = check_single_dependency(str(ffprobe_path))
            
            if handbrake_valid and ffprobe_valid:
                msg = "Dependencies already exist and are valid. Skipping download."
                if progress_callback:
                    progress_callback(msg)
                logger.info(msg)
                return (str(handbrake_path.resolve()), str(ffprobe_path.resolve()))
            else:
                msg = "Existing dependencies are invalid. Re-downloading..."
                if progress_callback:
                    progress_callback(msg)
                logger.info(msg)
        
        # Determine URLs based on platform
        if system == "Windows":
            handbrake_url = "https://github.com/HandBrake/HandBrake/releases/download/1.7.2/HandBrakeCLI-1.7.2-win-x86_64.zip"
            ffmpeg_url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
        elif system == "Darwin":  # macOS
            if "arm" in machine or "aarch64" in machine:
                handbrake_url = "https://github.com/HandBrake/HandBrake/releases/download/1.7.2/HandBrakeCLI-1.7.2-arm64.dmg"
            else:
                handbrake_url = "https://github.com/HandBrake/HandBrake/releases/download/1.7.2/HandBrakeCLI-1.7.2-x86_64.dmg"
            ffmpeg_url = "https://evermeet.cx/ffmpeg/ffmpeg-6.1.zip"
        elif system == "Linux":
            if "arm" in machine or "aarch64" in machine:
                handbrake_url = "https://github.com/HandBrake/HandBrake/releases/download/1.7.2/HandBrakeCLI-1.7.2-aarch64.flatpak"
                ffmpeg_url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-arm64-static.tar.xz"
            else:
                handbrake_url = "https://github.com/HandBrake/HandBrake/releases/download/1.7.2/HandBrakeCLI-1.7.2-x86_64.flatpak"
                ffmpeg_url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
        else:
            raise Exception(f"Unsupported platform: {system}")
        
        # Download HandBrakeCLI
        msg = f"Downloading HandBrakeCLI for {system}..."
        if progress_callback:
            progress_callback(msg)
        logger.info(msg)
        
        handbrake_archive = deps_dir / f"handbrake.{handbrake_url.split('.')[-1]}"
        
        try:
            urllib.request.urlretrieve(handbrake_url, handbrake_archive)
        except Exception as e:
            raise Exception(f"Failed to download HandBrakeCLI: {repr(e)}")
        
        # Extract HandBrakeCLI
        msg = "Extracting HandBrakeCLI..."
        if progress_callback:
            progress_callback(msg)
        logger.info(msg)
        
        try:
            if handbrake_archive.suffix == ".zip":
                with zipfile.ZipFile(handbrake_archive, 'r') as zip_ref:
                    zip_ref.extractall(deps_dir / "handbrake_temp")
                # Find HandBrakeCLI executable in extracted files
                handbrake_found = False
                for root, dirs, files in os.walk(deps_dir / "handbrake_temp"):
                    if handbrake_exe in files:
                        shutil.copy2(Path(root) / handbrake_exe, deps_dir / handbrake_exe)
                        handbrake_found = True
                        break
                if not handbrake_found:
                    raise Exception(f"Could not find {handbrake_exe} in downloaded archive")
                shutil.rmtree(deps_dir / "handbrake_temp")
            elif handbrake_archive.suffix in [".tar", ".xz", ".gz"]:
                with tarfile.open(handbrake_archive, 'r:*') as tar_ref:
                    tar_ref.extractall(deps_dir / "handbrake_temp")
                # Find HandBrakeCLI executable
                handbrake_found = False
                for root, dirs, files in os.walk(deps_dir / "handbrake_temp"):
                    if handbrake_exe in files:
                        shutil.copy2(Path(root) / handbrake_exe, deps_dir / handbrake_exe)
                        handbrake_found = True
                        break
                if not handbrake_found:
                    raise Exception(f"Could not find {handbrake_exe} in downloaded archive")
                temp_dir = deps_dir / "handbrake_temp"
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
            else:
                # For formats like .dmg or .flatpak, just inform user
                raise Exception(f"HandBrakeCLI format {handbrake_archive.suffix} requires manual installation on {system}")
        except Exception as e:
            logger.error(f"HandBrakeCLI extraction error: {repr(e)}")
            msg = f"HandBrakeCLI extraction failed: {repr(e)}"
            if progress_callback:
                progress_callback(msg)
            return (None, None)
        finally:
            if handbrake_archive.exists():
                handbrake_archive.unlink()
        
        # Download ffmpeg (includes ffprobe)
        msg = f"Downloading ffmpeg for {system}..."
        if progress_callback:
            progress_callback(msg)
        logger.info(msg)
        
        ffmpeg_archive = deps_dir / f"ffmpeg.{ffmpeg_url.split('.')[-1]}"
        
        try:
            urllib.request.urlretrieve(ffmpeg_url, ffmpeg_archive)
        except Exception as e:
            raise Exception(f"Failed to download ffmpeg: {repr(e)}")
        
        # Extract ffmpeg/ffprobe
        msg = "Extracting ffmpeg..."
        if progress_callback:
            progress_callback(msg)
        logger.info(msg)
        
        try:
            if ffmpeg_archive.suffix == ".zip":
                with zipfile.ZipFile(ffmpeg_archive, 'r') as zip_ref:
                    zip_ref.extractall(deps_dir / "ffmpeg_temp")
                # Find ffprobe executable (often in bin subdirectory)
                ffprobe_found = False
                for root, dirs, files in os.walk(deps_dir / "ffmpeg_temp"):
                    if ffprobe_exe in files:
                        shutil.copy2(Path(root) / ffprobe_exe, deps_dir / ffprobe_exe)
                        ffprobe_found = True
                        # Also copy ffmpeg if present
                        ffmpeg_exe = "ffmpeg.exe" if system == "Windows" else "ffmpeg"
                        if ffmpeg_exe in files:
                            shutil.copy2(Path(root) / ffmpeg_exe, deps_dir / ffmpeg_exe)
                        break
                if not ffprobe_found:
                    raise Exception(f"Could not find {ffprobe_exe} in downloaded archive")
                temp_dir = deps_dir / "ffmpeg_temp"
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
            elif ffmpeg_archive.suffix in [".tar", ".xz", ".gz"]:
                with tarfile.open(ffmpeg_archive, 'r:*') as tar_ref:
                    tar_ref.extractall(deps_dir / "ffmpeg_temp")
                # Find ffprobe executable (often in bin subdirectory)
                ffprobe_found = False
                for root, dirs, files in os.walk(deps_dir / "ffmpeg_temp"):
                    if ffprobe_exe in files:
                        shutil.copy2(Path(root) / ffprobe_exe, deps_dir / ffprobe_exe)
                        ffprobe_found = True
                        # Also copy ffmpeg if present
                        ffmpeg_exe = "ffmpeg.exe" if system == "Windows" else "ffmpeg"
                        if ffmpeg_exe in files:
                            shutil.copy2(Path(root) / ffmpeg_exe, deps_dir / ffmpeg_exe)
                        break
                if not ffprobe_found:
                    raise Exception(f"Could not find {ffprobe_exe} in downloaded archive")
                temp_dir = deps_dir / "ffmpeg_temp"
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
            else:
                raise Exception(f"ffmpeg format {ffmpeg_archive.suffix} not supported")
        except Exception as e:
            logger.error(f"ffmpeg extraction error: {repr(e)}")
            msg = f"ffmpeg extraction failed: {repr(e)}"
            if progress_callback:
                progress_callback(msg)
            return (None, None)
        finally:
            if ffmpeg_archive.exists():
                ffmpeg_archive.unlink()
        
        # Make executables executable on Unix-like systems
        if system in ["Linux", "Darwin"]:
            if handbrake_path.exists():
                os.chmod(handbrake_path, 0o755)
            if ffprobe_path.exists():
                os.chmod(ffprobe_path, 0o755)
        
        msg = f"Dependencies downloaded successfully to {deps_dir}"
        if progress_callback:
            progress_callback(msg)
        logger.info(msg)
        
        return (str(handbrake_path.resolve()), str(ffprobe_path.resolve()))
        
    except Exception as e:
        logger.error(f"Download dependencies error: {repr(e)}")
        msg = f"Failed to download dependencies: {repr(e)}"
        if progress_callback:
            progress_callback(msg)
        return (None, None)


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Convert video files to H.265 (HEVC) codec',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python convert_videos.py                          # Launch GUI (default)
  python convert_videos.py --gui                    # Launch GUI explicitly  
  python convert_videos.py --config config.yaml     # Run with config (background mode)
  python convert_videos.py --background /path/to/videos
  python convert_videos.py --background --dry-run C:\\Videos
  python convert_videos.py --background --loop /path/to/videos
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
    parser.add_argument('--background',
                       action='store_true',
                       help='Run in background mode (CLI, no GUI) - for Docker/service use')
    parser.add_argument('--gui',
                       action='store_true',
                       help='Run in GUI mode (default when no arguments provided)')
    parser.add_argument('--auto-download-dependencies',
                       action='store_true',
                       help='Automatically download dependencies if not found (HandBrakeCLI, ffprobe)')
    parser.add_argument('--log-file',
                       help='Path to log file (default: temp directory, can be set via VIDEO_CONVERTER_LOG_FILE env var)')
    
    args = parser.parse_args()
    
    # Determine whether to launch GUI or background mode
    # GUI mode if:
    # 1. --gui flag is explicitly provided, OR
    # 2. No arguments at all (len(sys.argv) == 1)
    # Background mode otherwise
    launch_gui = args.gui or (len(sys.argv) == 1 and not args.background)
    
    # Setup early logging to capture all events
    # Priority: CLI arg > env var > config file (loaded later) > default
    # We'll reconfigure logging after loading config if needed
    early_log_path = args.log_file or os.environ.get('VIDEO_CONVERTER_LOG_FILE')
    if early_log_path:
        setup_logging(early_log_path)
    
    if launch_gui and not args.background:
        # Launch GUI mode
        try:
            import convert_videos_gui
            convert_videos_gui.main()
        except ImportError as e:
            logger.error(f"Failed to import GUI module: {repr(e)}")
            logger.error("Make sure tkinter is installed")
            logger.error("To run in background mode, use: --background or provide arguments")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Failed to launch GUI: {repr(e)}")
            logger.error("To run in background mode, use: --background or provide arguments")
            sys.exit(1)
        return
    
    # Load configuration file
    config = load_config(args.config)
    
    # Reconfigure logging if config file specifies a different path
    # Priority: CLI arg > env var > config file > default
    log_file_path = args.log_file
    if not log_file_path:
        # Check environment variable
        log_file_path = os.environ.get('VIDEO_CONVERTER_LOG_FILE')
    if not log_file_path:
        # Check config file
        log_config = config.get('logging', {})
        if isinstance(log_config, dict):
            log_file_path = log_config.get('log_file')
    
    # Setup or reconfigure logging with final resolved path
    setup_logging(log_file_path)
    
    # Command line arguments override config file settings
    target_directory = args.directory or config.get('directory')
    dry_run = args.dry_run or config.get('dry_run', False)
    loop_mode = args.loop or config.get('loop', False)
    
    # Get remove_original_files config
    remove_original = config.get('remove_original_files', False)
    
    # Command line flag overrides config
    if args.remove_original_files:
        remove_original = True
    
    preserve_original = not remove_original
    
    # Get output configuration
    output_config = config.get('output', {})
    
    # Get dependency paths configuration
    dependency_config = config.get('dependencies', {})
    
    # ============================================
    # ALL CONFIGURATION VALIDATIONS START HERE
    # ============================================
    
    # Validate directory
    if not target_directory:
        logger.error("Error: No directory specified. Provide via command line or config file.")
        parser.print_help()
        sys.exit(1)
    
    if not os.path.isdir(target_directory):
        logger.error(f"Error: '{target_directory}' is not a valid directory.")
        sys.exit(1)
    
    # Parse and validate min file size
    try:
        min_file_size = parse_file_size(config.get('min_file_size', '1GB'))
    except ValueError as e:
        logger.error(f"Invalid min_file_size in config: {e}")
        sys.exit(1)
    
    # Validate output format
    output_format = output_config.get('format', 'mkv')
    if not validate_format(output_format):
        logger.error(f"Unsupported output format in config: '{output_format}'. Supported formats: {', '.join(SUPPORTED_FORMATS)}")
        sys.exit(1)
    
    # Validate encoder type
    encoder_type = output_config.get('encoder', 'x265_10bit')
    if not validate_encoder(encoder_type):
        logger.error(f"Unsupported encoder type in config: '{encoder_type}'. Supported encoders: {', '.join(SUPPORTED_ENCODERS)}")
        sys.exit(1)
    
    # Validate encoder preset
    encoder_preset = output_config.get('preset', 'medium')
    if not validate_preset(encoder_preset):
        logger.error(f"Unsupported encoder preset in config: '{encoder_preset}'. Supported presets: {', '.join(SUPPORTED_PRESETS)}")
        sys.exit(1)
    
    # Validate quality parameter
    quality = output_config.get('quality', 24)
    if not validate_quality(quality):
        logger.error(f"Invalid quality value in config: {quality!r}. Must be an integer between 0 and 51.")
        sys.exit(1)
    
    # Auto-download dependencies if requested
    if args.auto_download_dependencies:
        logger.info("Auto-downloading dependencies...")
        handbrake_path, ffprobe_path = download_dependencies()
        
        if handbrake_path and ffprobe_path:
            # Update dependency config with downloaded paths
            if 'dependencies' not in config:
                config['dependencies'] = {}
            config['dependencies']['handbrake'] = handbrake_path
            config['dependencies']['ffprobe'] = ffprobe_path
            dependency_config = config['dependencies']
            logger.info(f"Dependencies downloaded: HandBrakeCLI={handbrake_path}, ffprobe={ffprobe_path}")
        else:
            logger.error("Failed to download dependencies. Please install manually.")
            sys.exit(1)
    
    # Check dependencies
    check_dependencies(dependency_config)
    
    # ============================================
    # ALL CONFIGURATION VALIDATIONS COMPLETED
    # ============================================
    
    # Main processing loop
    while True:
        logger.info(f"Starting scan in {target_directory}")
        
        files = find_eligible_files(target_directory, min_file_size, dependency_config)
        
        if not files:
            logger.info("No eligible files found.")
        else:
            logger.info(f"Files to convert ({len(files)}):")
            for file in files:
                logger.info(f"  {file}")
            
            for file in files:
                convert_file(file, dry_run=dry_run, preserve_original=preserve_original, 
                           output_config=output_config, dependency_config=dependency_config)
        
        if not loop_mode:
            break
        
        logger.info("Waiting 1 hour before next scan...")
        time.sleep(3600)


if __name__ == '__main__':
    main()
