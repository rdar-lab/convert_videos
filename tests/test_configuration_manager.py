#!/usr/bin/env python3
"""
Unit tests for configuration_manager.py
"""

import os
import unittest
import tempfile
import yaml

# Import the module to test
import configuration_manager


class TestFileSizeParsing(unittest.TestCase):
    """Test file size parsing functionality."""
    
    def test_parse_file_size_bytes(self):
        """Test parsing file size in bytes."""
        self.assertEqual(configuration_manager.parse_file_size("100"), 100)
        self.assertEqual(configuration_manager.parse_file_size("100B"), 100)
        self.assertEqual(configuration_manager.parse_file_size("100 B"), 100)
    
    def test_parse_file_size_kilobytes(self):
        """Test parsing file size in kilobytes."""
        self.assertEqual(configuration_manager.parse_file_size("1KB"), 1024)
        self.assertEqual(configuration_manager.parse_file_size("2 KB"), 2048)
        self.assertEqual(configuration_manager.parse_file_size("1.5KB"), 1536)
    
    def test_parse_file_size_megabytes(self):
        """Test parsing file size in megabytes."""
        self.assertEqual(configuration_manager.parse_file_size("1MB"), 1024 ** 2)
        self.assertEqual(configuration_manager.parse_file_size("2 MB"), 2 * 1024 ** 2)
        self.assertEqual(configuration_manager.parse_file_size("1.5MB"), int(1.5 * 1024 ** 2))
    
    def test_parse_file_size_gigabytes(self):
        """Test parsing file size in gigabytes."""
        self.assertEqual(configuration_manager.parse_file_size("1GB"), 1024 ** 3)
        self.assertEqual(configuration_manager.parse_file_size("2 GB"), 2 * 1024 ** 3)
        self.assertEqual(configuration_manager.parse_file_size("0.5GB"), int(0.5 * 1024 ** 3))
    
    def test_parse_file_size_case_insensitive(self):
        """Test that parsing is case insensitive."""
        self.assertEqual(configuration_manager.parse_file_size("1gb"), 1024 ** 3)
        self.assertEqual(configuration_manager.parse_file_size("1Gb"), 1024 ** 3)
        self.assertEqual(configuration_manager.parse_file_size("1gB"), 1024 ** 3)
    
    def test_parse_file_size_integer_input(self):
        """Test that integer input is handled correctly."""
        self.assertEqual(configuration_manager.parse_file_size(1024), 1024)
        self.assertEqual(configuration_manager.parse_file_size(0), 0)
    
    def test_parse_file_size_invalid_format(self):
        """Test that invalid formats raise ValueError."""
        with self.assertRaises(ValueError):
            configuration_manager.parse_file_size("invalid")
        
        # Multiple spaces or numbers should fail
        with self.assertRaises(ValueError):
            configuration_manager.parse_file_size("1 2 GB")
    
    def test_parse_file_size_negative(self):
        """Test that negative values raise ValueError."""
        with self.assertRaises(ValueError):
            configuration_manager.parse_file_size("-1GB")


class TestValidationFunctions(unittest.TestCase):
    """Test validation functions."""
    
    def test_validate_encoder(self):
        """Test encoder validation."""
        # Valid encoders
        self.assertTrue(configuration_manager.validate_encoder('x265'))
        self.assertTrue(configuration_manager.validate_encoder('x265_10bit'))
        self.assertTrue(configuration_manager.validate_encoder('nvenc_hevc'))
        
        # Invalid encoders
        self.assertFalse(configuration_manager.validate_encoder('invalid'))
        self.assertFalse(configuration_manager.validate_encoder('h264'))
        self.assertFalse(configuration_manager.validate_encoder(''))
    
    def test_validate_format(self):
        """Test format validation."""
        # Valid formats
        self.assertTrue(configuration_manager.validate_format('mkv'))
        self.assertTrue(configuration_manager.validate_format('mp4'))
        
        # Invalid formats
        self.assertFalse(configuration_manager.validate_format('m4v'))
        self.assertFalse(configuration_manager.validate_format('invalid'))
        self.assertFalse(configuration_manager.validate_format('avi'))
        self.assertFalse(configuration_manager.validate_format(''))
    
    def test_validate_preset(self):
        """Test preset validation."""
        # Valid presets (x265)
        self.assertTrue(configuration_manager.validate_preset('ultrafast'))
        self.assertTrue(configuration_manager.validate_preset('medium'))
        self.assertTrue(configuration_manager.validate_preset('veryslow'))
        
        # Valid presets (NVENC)
        self.assertTrue(configuration_manager.validate_preset('fast'))
        self.assertTrue(configuration_manager.validate_preset('slow'))
        
        # Invalid presets
        self.assertFalse(configuration_manager.validate_preset('invalid'))
        self.assertFalse(configuration_manager.validate_preset(''))
    
    def test_validate_quality(self):
        """Test quality validation."""
        # Valid quality values
        self.assertTrue(configuration_manager.validate_quality(0))
        self.assertTrue(configuration_manager.validate_quality(24))
        self.assertTrue(configuration_manager.validate_quality(51))
        
        # Invalid quality values
        self.assertFalse(configuration_manager.validate_quality(-1))
        self.assertFalse(configuration_manager.validate_quality(52))
        self.assertFalse(configuration_manager.validate_quality(100))


class TestPresetMapping(unittest.TestCase):
    """Test preset mapping for different encoders."""
    
    def test_x265_preset_mapping(self):
        """Test that x265 presets are passed through unchanged."""
        for preset in ['ultrafast', 'superfast', 'veryfast', 'faster', 'fast', 'medium', 'slow', 'slower', 'veryslow']:
            self.assertEqual(
                configuration_manager.map_preset_for_encoder(preset, 'x265'),
                preset
            )
    
    def test_x265_10bit_preset_mapping(self):
        """Test that x265_10bit presets are passed through unchanged."""
        for preset in ['ultrafast', 'medium', 'veryslow']:
            self.assertEqual(
                configuration_manager.map_preset_for_encoder(preset, 'x265_10bit'),
                preset
            )
    
    def test_nvenc_preset_mapping_from_x265(self):
        """Test mapping x265 presets to NVENC equivalents."""
        # x265 -> NVENC mapping
        self.assertEqual(
            configuration_manager.map_preset_for_encoder('ultrafast', 'nvenc_hevc'),
            'fast'
        )
        self.assertEqual(
            configuration_manager.map_preset_for_encoder('medium', 'nvenc_hevc'),
            'medium'
        )
        self.assertEqual(
            configuration_manager.map_preset_for_encoder('veryslow', 'nvenc_hevc'),
            'slow'
        )
    
    def test_nvenc_preset_passthrough(self):
        """Test that NVENC presets are passed through unchanged for NVENC encoder."""
        for preset in ['fast', 'medium', 'slow']:
            self.assertEqual(
                configuration_manager.map_preset_for_encoder(preset, 'nvenc_hevc'),
                preset
            )
    
    def test_x265_with_nvenc_preset(self):
        """Test that NVENC presets work with x265 encoder."""
        # NVENC presets are also valid for x265, so they pass through
        for preset in ['fast', 'medium', 'slow']:
            # These are valid for both, so they should pass through
            result = configuration_manager.map_preset_for_encoder(preset, 'x265')
            self.assertIn(result, ['ultrafast', 'superfast', 'veryfast', 'faster', 'fast', 'medium', 'slow', 'slower', 'veryslow'])


class TestConfigLoading(unittest.TestCase):
    """Test configuration file loading."""
    
    def test_load_config_file_not_found(self):
        """Test loading config when file doesn't exist."""
        # Should return default config with validation errors
        with tempfile.TemporaryDirectory() as temp_dir:
            non_existent_file = os.path.join(temp_dir, 'nonexistent.yaml')
            config, errors = configuration_manager.load_config(non_existent_file)
            
            # Should have default values
            self.assertIsNotNone(config.get('output'))
            self.assertIsNotNone(config.get('dependencies'))
            
            # Should have an error about missing file
            self.assertTrue(len(errors) > 0)
    
    def test_load_config_valid_file(self):
        """Test loading a valid config file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_data = {
                'directory': '/test/path',
                'min_file_size': '2GB',
                'output': {
                    'format': 'mp4',
                    'encoder': 'nvenc_hevc',
                    'preset': 'fast',
                    'quality': 20
                }
            }
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            config, errors = configuration_manager.load_config(config_path)
            
            # Should load config successfully
            self.assertEqual(config['directory'], '/test/path')
            # min_file_size gets parsed to bytes
            self.assertEqual(config['min_file_size'], 2 * 1024**3)
            self.assertEqual(config['output']['format'], 'mp4')
            self.assertEqual(config['output']['encoder'], 'nvenc_hevc')
            
            # May have warnings but no blocking errors
            # (e.g., directory doesn't exist is a warning)
        finally:
            os.unlink(config_path)
    
    def test_load_config_partial_output(self):
        """Test that partial output config merges with defaults."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_data = {
                'output': {
                    'format': 'mp4',
                    # Missing encoder, preset, quality
                }
            }
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            config, errors = configuration_manager.load_config(config_path)
            
            # Should merge with defaults
            self.assertEqual(config['output']['format'], 'mp4')
            self.assertIn('encoder', config['output'])
            self.assertIn('preset', config['output'])
            self.assertIn('quality', config['output'])
        finally:
            os.unlink(config_path)
    
    def test_load_config_null_output(self):
        """Test that null output config restores defaults."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_data = {
                'output': None
            }
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            config, errors = configuration_manager.load_config(config_path)
            
            # Should have default output config
            self.assertIsNotNone(config['output'])
            self.assertIn('format', config['output'])
            self.assertIn('encoder', config['output'])
        finally:
            os.unlink(config_path)
    
    def test_load_config_invalid_yaml(self):
        """Test handling of invalid YAML file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [\n")
            config_path = f.name
        
        try:
            config, errors = configuration_manager.load_config(config_path)
            
            # Should return default config
            self.assertIsNotNone(config.get('output'))
            
            # Should have error about invalid YAML
            self.assertTrue(len(errors) > 0)
        finally:
            os.unlink(config_path)
    
    def test_load_config_with_dependencies(self):
        """Test loading config with dependencies paths."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_data = {
                'dependencies': {
                    'handbrake': '/usr/local/bin/HandBrakeCLI',
                    'ffprobe': '/usr/bin/ffprobe'
                }
            }
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            config, errors = configuration_manager.load_config(config_path)
            
            # Should load dependencies
            self.assertEqual(config['dependencies']['handbrake'], '/usr/local/bin/HandBrakeCLI')
            self.assertEqual(config['dependencies']['ffprobe'], '/usr/bin/ffprobe')
        finally:
            os.unlink(config_path)
    
    def test_load_config_partial_dependencies(self):
        """Test that partial dependencies config merges with defaults."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_data = {
                'dependencies': {
                    'handbrake': '/custom/HandBrakeCLI'
                    # Missing ffprobe, ffmpeg
                }
            }
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            config, errors = configuration_manager.load_config(config_path)
            
            # Should merge with defaults
            self.assertEqual(config['dependencies']['handbrake'], '/custom/HandBrakeCLI')
            self.assertIn('ffprobe', config['dependencies'])
            self.assertIn('ffmpeg', config['dependencies'])
        finally:
            os.unlink(config_path)
    
    def test_load_config_null_dependencies(self):
        """Test that null dependencies config restores defaults."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_data = {
                'dependencies': None
            }
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            config, errors = configuration_manager.load_config(config_path)
            
            # Should have default dependencies
            self.assertIsNotNone(config['dependencies'])
            self.assertIn('handbrake', config['dependencies'])
            self.assertIn('ffprobe', config['dependencies'])
        finally:
            os.unlink(config_path)
    
    def test_load_config_invalid_dependencies_type(self):
        """Test that invalid dependencies type falls back to defaults."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_data = {
                'dependencies': 'not a dict'
            }
            yaml.dump(config_data, f)
            config_path = f.name
        
        try:
            config, errors = configuration_manager.load_config(config_path)
            
            # Should use defaults for dependencies
            self.assertIsInstance(config['dependencies'], dict)
            self.assertIn('handbrake', config['dependencies'])
        finally:
            os.unlink(config_path)


if __name__ == '__main__':
    unittest.main()
