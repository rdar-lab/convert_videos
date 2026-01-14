#!/usr/bin/env python3
"""
Configuration manager
"""


import logging
import logging.handlers
import re
from pathlib import Path

import yaml

import dependencies_utils

# Constants
SUPPORTED_ENCODERS = ['x265', 'x265_10bit', 'nvenc_hevc']
SUPPORTED_FORMATS = ['mkv', 'mp4']
# x265 CPU encoder presets
X265_PRESETS = ['ultrafast', 'superfast', 'veryfast',
                'faster', 'fast', 'medium', 'slow', 'slower', 'veryslow']
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
FILE_SIZE_PATTERN = re.compile(
    r'^(\d+(?:\.\d+)?)\s*(GB|MB|KB|B)?$', re.IGNORECASE)

logger = logging.getLogger(__name__)


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


def prepare_default_config():
    return {
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
            'ffprobe': 'ffprobe',
            'ffmpeg': 'ffmpeg'
        },
        'logging': {
            'log_file': None  # None means default to temp directory
        },
        'remove_original_files': False,
        'loop': False,
        'dry_run': False
    }


def post_process_configuration(config, args):
    # Resolve dependency paths after loading configuration
    # This checks for bundled executables in PyInstaller bundles and resolves paths
    config['dependencies']['handbrake'] = dependencies_utils.find_dependency_path(
        'HandBrakeCLI',
        config['dependencies'].get('handbrake')
    )
    config['dependencies']['ffprobe'] = dependencies_utils.find_dependency_path(
        'ffprobe',
        config['dependencies'].get('ffprobe')
    )
    config['dependencies']['ffmpeg'] = dependencies_utils.find_dependency_path(
        'ffmpeg',
        config['dependencies'].get('ffmpeg')
    )

    # Reconfigure logging if config file specifies a different path
    # Priority: CLI arg > env var > config file > default
    log_file_path = args.log_file if args else None
    if not log_file_path:
        # Check environment variable
        log_file_path = os.environ.get('VIDEO_CONVERTER_LOG_FILE')
    if not log_file_path:
        # Check config file
        log_config = config.get('logging', {})
        if isinstance(log_config, dict):
            log_file_path = log_config.get('log_file')

    if 'logging' not in config:
        config['logging'] = {}
    config['logging']['log_file'] = log_file_path

    output_config = config.get('output', {})
    output_format = output_config.get('format', 'mkv')
    encoder_type = output_config.get('encoder', 'x265_10bit')
    encoder_preset = output_config.get('preset', 'medium')
    quality = output_config.get('quality', 24)

    validation_issues = []

    # Validate output format
    if not validate_format(output_format):
        validation_issues.append(
            f"Unsupported output format: {output_format}. Supported: {', '.join(SUPPORTED_FORMATS)}")

    # Validate encoder type
    if not validate_encoder(encoder_type):
        validation_issues.append(
            f"Unsupported encoder type: {encoder_type}. Supported: {', '.join(SUPPORTED_ENCODERS)}")

    # Validate encoder preset
    if not validate_preset(encoder_preset):
        validation_issues.append(
            f"Unsupported encoder preset: {encoder_preset}. Supported: {', '.join(SUPPORTED_PRESETS)}")

    # Validate quality parameter
    if not validate_quality(quality):
        validation_issues.append(
            f"Invalid quality value: {quality!r}. Must be an integer between 0 and 51.")

    # Map preset to encoder-specific preset
    effective_preset = map_preset_for_encoder(
        encoder_preset, encoder_type)

    if effective_preset != encoder_preset:
        logger.info(
            f"Mapped preset '{encoder_preset}' to '{effective_preset}' for encoder '{encoder_type}'")
        encoder_preset = effective_preset

    if 'output' not in config:
        config['output'] = {}
    config['output']['format'] = output_format
    config['output']['encoder'] = encoder_type
    config['output']['preset'] = encoder_preset
    config['output']['quality'] = quality


    config['directory'] = args.directory if args and args.directory else config.get('directory')
   
    # Validate directory
    if not config['directory']:
        validation_issues.append(
            "Error: No directory specified. Provide via command line or config file.")
    elif not os.path.isdir(config['directory']):
        validation_issues.append(
            f"Error: '{config['directory']}' is not a valid directory.")

    config['dry_run'] = args.dry_run if args and args.dry_run else config.get('dry_run', False)
    config['loop'] = args.loop if args and args.loop else config.get('loop', False)
    config['remove_original_files'] = config.get('remove_original_files', False)
    if args and args.remove_original_files:
        config['remove_original_files'] = True

    # Parse and validate min file size
    try:
        min_file_size = parse_file_size(config.get('min_file_size', '1GB'))
        config['min_file_size'] = min_file_size
    except ValueError as e:
        validation_issues.append(f"Invalid min_file_size in config: {e}")

    return config, validation_issues


def load_config(config_path=None, args=None):
    """Load configuration from YAML file.

    After loading, resolves dependency paths to check for bundled executables
    in PyInstaller bundles. This ensures all consumers of the config receive
    properly resolved paths.
    """
    default_config = prepare_default_config()

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
                    config['output'] = {
                        **default_config['output'], **user_config['output']}
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
                    config['dependencies'] = {
                        **default_config['dependencies'], **user_config['dependencies']}
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
                    config['logging'] = {
                        **default_config['logging'], **user_config['logging']}
                else:
                    # Invalid logging type; fall back to defaults to avoid runtime errors
                    config['logging'] = default_config['logging']

            logger.info(f"Loaded configuration from {config_path}")
        except (OSError, IOError, yaml.YAMLError) as e:
            logger.error(f"Error loading config file {config_path}: {e}")

            # Call prepare_default_config again to get a fresh default configuration
            config = prepare_default_config()

    return post_process_configuration(config, args)
