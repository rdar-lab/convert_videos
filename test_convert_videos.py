#!/usr/bin/env python3
"""
Unit tests for convert_videos.py
"""

import unittest
from unittest.mock import patch, MagicMock
import tempfile
from pathlib import Path
import yaml

# Import the module to test
import convert_videos


class TestFileSizeParsing(unittest.TestCase):
    """Test file size parsing functionality."""
    
    def test_parse_file_size_bytes(self):
        """Test parsing file size in bytes."""
        self.assertEqual(convert_videos.parse_file_size("100"), 100)
        self.assertEqual(convert_videos.parse_file_size("100B"), 100)
        self.assertEqual(convert_videos.parse_file_size("100 B"), 100)
    
    def test_parse_file_size_kilobytes(self):
        """Test parsing file size in kilobytes."""
        self.assertEqual(convert_videos.parse_file_size("1KB"), 1024)
        self.assertEqual(convert_videos.parse_file_size("2 KB"), 2048)
        self.assertEqual(convert_videos.parse_file_size("1.5KB"), 1536)
    
    def test_parse_file_size_megabytes(self):
        """Test parsing file size in megabytes."""
        self.assertEqual(convert_videos.parse_file_size("1MB"), 1024 ** 2)
        self.assertEqual(convert_videos.parse_file_size("2 MB"), 2 * 1024 ** 2)
        self.assertEqual(convert_videos.parse_file_size("1.5MB"), int(1.5 * 1024 ** 2))
    
    def test_parse_file_size_gigabytes(self):
        """Test parsing file size in gigabytes."""
        self.assertEqual(convert_videos.parse_file_size("1GB"), 1024 ** 3)
        self.assertEqual(convert_videos.parse_file_size("2 GB"), 2 * 1024 ** 3)
        self.assertEqual(convert_videos.parse_file_size("0.5GB"), int(0.5 * 1024 ** 3))
    
    def test_parse_file_size_case_insensitive(self):
        """Test that parsing is case insensitive."""
        self.assertEqual(convert_videos.parse_file_size("1gb"), 1024 ** 3)
        self.assertEqual(convert_videos.parse_file_size("1Gb"), 1024 ** 3)
        self.assertEqual(convert_videos.parse_file_size("1gB"), 1024 ** 3)
    
    def test_parse_file_size_integer_input(self):
        """Test that integer input is handled correctly."""
        self.assertEqual(convert_videos.parse_file_size(1024), 1024)
        self.assertEqual(convert_videos.parse_file_size(0), 0)
    
    def test_parse_file_size_invalid_format(self):
        """Test that invalid formats raise ValueError."""
        with self.assertRaises(ValueError):
            convert_videos.parse_file_size("invalid")
        with self.assertRaises(ValueError):
            convert_videos.parse_file_size("1 2 GB")
        with self.assertRaises(ValueError):
            convert_videos.parse_file_size("GB")
    
    def test_parse_file_size_negative(self):
        """Test that negative values raise ValueError."""
        with self.assertRaises(ValueError):
            convert_videos.parse_file_size(-100)


class TestValidationFunctions(unittest.TestCase):
    """Test validation functions."""
    
    def test_validate_encoder(self):
        """Test encoder validation."""
        # Valid encoders
        self.assertTrue(convert_videos.validate_encoder('x265'))
        self.assertTrue(convert_videos.validate_encoder('x265_10bit'))
        self.assertTrue(convert_videos.validate_encoder('nvenc_hevc'))
        
        # Invalid encoders
        self.assertFalse(convert_videos.validate_encoder('invalid'))
        self.assertFalse(convert_videos.validate_encoder('h264'))
        self.assertFalse(convert_videos.validate_encoder(''))
    
    def test_validate_format(self):
        """Test format validation."""
        # Valid formats
        self.assertTrue(convert_videos.validate_format('mkv'))
        self.assertTrue(convert_videos.validate_format('mp4'))
        
        # Invalid formats
        self.assertFalse(convert_videos.validate_format('avi'))
        self.assertFalse(convert_videos.validate_format('mov'))
        self.assertFalse(convert_videos.validate_format(''))
    
    def test_validate_preset(self):
        """Test preset validation."""
        # Valid x265 presets
        for preset in ['ultrafast', 'superfast', 'veryfast', 'faster', 'fast', 'medium', 'slow', 'slower', 'veryslow']:
            self.assertTrue(convert_videos.validate_preset(preset))
        
        # Valid NVENC presets
        for preset in ['default', 'fast', 'medium', 'slow']:
            self.assertTrue(convert_videos.validate_preset(preset))
        
        # Invalid presets
        self.assertFalse(convert_videos.validate_preset('invalid'))
        self.assertFalse(convert_videos.validate_preset(''))
    
    def test_validate_quality(self):
        """Test quality validation."""
        # Valid quality values
        self.assertTrue(convert_videos.validate_quality(0))
        self.assertTrue(convert_videos.validate_quality(24))
        self.assertTrue(convert_videos.validate_quality(51))
        self.assertTrue(convert_videos.validate_quality('24'))
        
        # Invalid quality values
        self.assertFalse(convert_videos.validate_quality(-1))
        self.assertFalse(convert_videos.validate_quality(52))
        self.assertFalse(convert_videos.validate_quality('invalid'))
        self.assertFalse(convert_videos.validate_quality(None))


class TestPresetMapping(unittest.TestCase):
    """Test preset mapping for different encoders."""
    
    def test_x265_preset_mapping(self):
        """Test that x265 presets are passed through unchanged."""
        for preset in ['ultrafast', 'superfast', 'veryfast', 'faster', 'fast', 'medium', 'slow', 'slower', 'veryslow']:
            result = convert_videos.map_preset_for_encoder(preset, 'x265')
            self.assertEqual(result, preset)
    
    def test_x265_10bit_preset_mapping(self):
        """Test that x265_10bit presets are passed through unchanged."""
        for preset in ['ultrafast', 'superfast', 'veryfast', 'faster', 'fast', 'medium', 'slow', 'slower', 'veryslow']:
            result = convert_videos.map_preset_for_encoder(preset, 'x265_10bit')
            self.assertEqual(result, preset)
    
    def test_nvenc_preset_mapping_from_x265(self):
        """Test mapping x265 presets to NVENC equivalents."""
        # Fast presets should map to 'fast'
        for preset in ['ultrafast', 'superfast', 'veryfast', 'faster', 'fast']:
            result = convert_videos.map_preset_for_encoder(preset, 'nvenc_hevc')
            self.assertEqual(result, 'fast')
        
        # Medium preset should map to 'medium'
        self.assertEqual(convert_videos.map_preset_for_encoder('medium', 'nvenc_hevc'), 'medium')
        
        # Slow presets should map to 'slow'
        for preset in ['slow', 'slower', 'veryslow']:
            result = convert_videos.map_preset_for_encoder(preset, 'nvenc_hevc')
            self.assertEqual(result, 'slow')
    
    def test_nvenc_preset_passthrough(self):
        """Test that NVENC presets are passed through unchanged for NVENC encoder."""
        for preset in ['default', 'fast', 'medium', 'slow']:
            result = convert_videos.map_preset_for_encoder(preset, 'nvenc_hevc')
            self.assertEqual(result, preset)
    
    def test_x265_with_nvenc_preset(self):
        """Test mapping NVENC presets to x265 equivalents."""
        self.assertEqual(convert_videos.map_preset_for_encoder('default', 'x265'), 'medium')
        self.assertEqual(convert_videos.map_preset_for_encoder('fast', 'x265'), 'fast')
        self.assertEqual(convert_videos.map_preset_for_encoder('medium', 'x265'), 'medium')
        self.assertEqual(convert_videos.map_preset_for_encoder('slow', 'x265'), 'slow')


class TestConfigLoading(unittest.TestCase):
    """Test configuration file loading."""
    
    def test_load_config_file_not_found(self):
        """Test loading config when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / 'nonexistent.yaml'
            config = convert_videos.load_config(config_path)
            
            # Should return default config
            self.assertIsNotNone(config)
            self.assertEqual(config['min_file_size'], '1GB')
            self.assertEqual(config['output']['format'], 'mkv')
            self.assertEqual(config['output']['encoder'], 'x265_10bit')
    
    def test_load_config_valid_file(self):
        """Test loading a valid config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / 'config.yaml'
            config_data = {
                'directory': '/test/path',
                'min_file_size': '500MB',
                'output': {
                    'format': 'mp4',
                    'encoder': 'nvenc_hevc',
                    'preset': 'fast',
                    'quality': 20
                },
                'preserve_original': True,
                'loop': True,
                'dry_run': True
            }
            
            with open(config_path, 'w') as f:
                yaml.dump(config_data, f)
            
            config = convert_videos.load_config(config_path)
            
            self.assertEqual(config['directory'], '/test/path')
            self.assertEqual(config['min_file_size'], '500MB')
            self.assertEqual(config['output']['format'], 'mp4')
            self.assertEqual(config['output']['encoder'], 'nvenc_hevc')
            self.assertEqual(config['output']['preset'], 'fast')
            self.assertEqual(config['output']['quality'], 20)
            self.assertTrue(config['preserve_original'])
            self.assertTrue(config['loop'])
            self.assertTrue(config['dry_run'])
    
    def test_load_config_partial_output(self):
        """Test that partial output config merges with defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / 'config.yaml'
            config_data = {
                'directory': '/test/path',
                'output': {
                    'encoder': 'x265'
                }
            }
            
            with open(config_path, 'w') as f:
                yaml.dump(config_data, f)
            
            config = convert_videos.load_config(config_path)
            
            # Should have custom encoder
            self.assertEqual(config['output']['encoder'], 'x265')
            # But default format, preset, and quality
            self.assertEqual(config['output']['format'], 'mkv')
            self.assertEqual(config['output']['preset'], 'medium')
            self.assertEqual(config['output']['quality'], 24)
    
    def test_load_config_null_output(self):
        """Test that null output config restores defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / 'config.yaml'
            config_data = {
                'directory': '/test/path',
                'output': None
            }
            
            with open(config_path, 'w') as f:
                yaml.dump(config_data, f)
            
            config = convert_videos.load_config(config_path)
            
            # Should have default output config
            self.assertEqual(config['output']['format'], 'mkv')
            self.assertEqual(config['output']['encoder'], 'x265_10bit')
            self.assertEqual(config['output']['preset'], 'medium')
            self.assertEqual(config['output']['quality'], 24)
    
    def test_load_config_invalid_yaml(self):
        """Test handling of invalid YAML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / 'config.yaml'
            
            with open(config_path, 'w') as f:
                f.write("invalid: yaml: content:\n  - broken")
            
            config = convert_videos.load_config(config_path)
            
            # Should return default config on error
            self.assertEqual(config['min_file_size'], '1GB')
    
    def test_load_config_with_dependencies(self):
        """Test loading config with dependencies paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / 'config.yaml'
            config_data = {
                'directory': '/test/path',
                'dependencies': {
                    'handbrake': '/custom/path/HandBrakeCLI',
                    'ffprobe': '/custom/path/ffprobe'
                }
            }
            
            with open(config_path, 'w') as f:
                yaml.dump(config_data, f)
            
            config = convert_videos.load_config(config_path)
            
            self.assertEqual(config['dependencies']['handbrake'], '/custom/path/HandBrakeCLI')
            self.assertEqual(config['dependencies']['ffprobe'], '/custom/path/ffprobe')
    
    def test_load_config_partial_dependencies(self):
        """Test that partial dependencies config merges with defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / 'config.yaml'
            config_data = {
                'directory': '/test/path',
                'dependencies': {
                    'handbrake': '/custom/HandBrakeCLI'
                }
            }
            
            with open(config_path, 'w') as f:
                yaml.dump(config_data, f)
            
            config = convert_videos.load_config(config_path)
            
            # Should have custom handbrake path
            self.assertEqual(config['dependencies']['handbrake'], '/custom/HandBrakeCLI')
            # But default ffprobe
            self.assertEqual(config['dependencies']['ffprobe'], 'ffprobe')
    
    def test_load_config_null_dependencies(self):
        """Test that null dependencies config restores defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / 'config.yaml'
            config_data = {
                'directory': '/test/path',
                'dependencies': None
            }
            
            with open(config_path, 'w') as f:
                yaml.dump(config_data, f)
            
            config = convert_videos.load_config(config_path)
            
            # Should have default dependencies config
            self.assertEqual(config['dependencies']['handbrake'], 'HandBrakeCLI')
            self.assertEqual(config['dependencies']['ffprobe'], 'ffprobe')
    
    def test_load_config_invalid_dependencies_type(self):
        """Test that invalid dependencies type falls back to defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / 'config.yaml'
            config_data = {
                'directory': '/test/path',
                'dependencies': 'invalid_string'
            }
            
            with open(config_path, 'w') as f:
                yaml.dump(config_data, f)
            
            config = convert_videos.load_config(config_path)
            
            # Should fall back to default dependencies config
            self.assertEqual(config['dependencies']['handbrake'], 'HandBrakeCLI')
            self.assertEqual(config['dependencies']['ffprobe'], 'ffprobe')


class TestGetCodec(unittest.TestCase):
    """Test codec detection functionality."""
    
    @patch('convert_videos.subprocess.run')
    def test_get_codec_hevc(self, mock_run):
        """Test detecting HEVC codec."""
        mock_run.return_value = MagicMock(stdout='hevc\n', returncode=0)
        
        result = convert_videos.get_codec('/path/to/video.mp4')
        
        self.assertEqual(result, 'hevc')
        mock_run.assert_called_once()
    
    @patch('convert_videos.subprocess.run')
    def test_get_codec_h264(self, mock_run):
        """Test detecting H.264 codec."""
        mock_run.return_value = MagicMock(stdout='h264\n', returncode=0)
        
        result = convert_videos.get_codec('/path/to/video.mp4')
        
        self.assertEqual(result, 'h264')
    
    @patch('convert_videos.subprocess.run')
    def test_get_codec_error(self, mock_run):
        """Test handling error when getting codec."""
        from subprocess import CalledProcessError
        mock_run.side_effect = CalledProcessError(1, 'ffprobe')
        
        result = convert_videos.get_codec('/path/to/video.mp4')
        
        self.assertIsNone(result)


class TestGetDuration(unittest.TestCase):
    """Test video duration extraction."""
    
    @patch('convert_videos.subprocess.run')
    def test_get_duration_valid(self, mock_run):
        """Test getting valid duration."""
        mock_run.return_value = MagicMock(stdout='3600.5\n', returncode=0)
        
        result = convert_videos.get_duration('/path/to/video.mp4')
        
        self.assertEqual(result, 3600)
    
    @patch('convert_videos.subprocess.run')
    def test_get_duration_integer(self, mock_run):
        """Test getting integer duration."""
        mock_run.return_value = MagicMock(stdout='1800\n', returncode=0)
        
        result = convert_videos.get_duration('/path/to/video.mp4')
        
        self.assertEqual(result, 1800)
    
    @patch('convert_videos.subprocess.run')
    def test_get_duration_error(self, mock_run):
        """Test handling error when getting duration."""
        from subprocess import CalledProcessError
        mock_run.side_effect = CalledProcessError(1, 'ffprobe')
        
        result = convert_videos.get_duration('/path/to/video.mp4')
        
        self.assertEqual(result, 0)
    
    @patch('convert_videos.subprocess.run')
    def test_get_duration_empty(self, mock_run):
        """Test handling empty duration output."""
        mock_run.return_value = MagicMock(stdout='', returncode=0)
        
        result = convert_videos.get_duration('/path/to/video.mp4')
        
        self.assertEqual(result, 0)


class TestFindEligibleFiles(unittest.TestCase):
    """Test finding eligible files for conversion."""
    
    @patch('convert_videos.get_codec')
    def test_find_eligible_files_filters_by_size(self, mock_get_codec):
        """Test that files below minimum size are filtered out."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # Create test files (using smaller sizes for faster tests)
            small_file = tmpdir_path / 'small.mp4'
            large_file = tmpdir_path / 'large.mp4'
            
            small_file.write_bytes(b'x' * (500 * 1024))  # 500KB
            large_file.write_bytes(b'x' * (2 * 1024 * 1024))  # 2MB
            
            mock_get_codec.return_value = 'h264'
            
            result = convert_videos.find_eligible_files(tmpdir, min_size_bytes=1024 * 1024)  # 1MB threshold
            
            # Only large file should be returned
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].name, 'large.mp4')
    
    @patch('convert_videos.get_codec')
    def test_find_eligible_files_filters_by_codec(self, mock_get_codec):
        """Test that HEVC files are filtered out."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # Create test files (using smaller sizes for faster tests)
            h264_file = tmpdir_path / 'h264.mp4'
            hevc_file = tmpdir_path / 'hevc.mp4'
            
            h264_file.write_bytes(b'x' * (2 * 1024 * 1024))  # 2MB
            hevc_file.write_bytes(b'x' * (2 * 1024 * 1024))  # 2MB
            
            def codec_side_effect(path):
                if 'h264' in str(path):
                    return 'h264'
                return 'hevc'
            
            mock_get_codec.side_effect = codec_side_effect
            
            result = convert_videos.find_eligible_files(tmpdir, min_size_bytes=1024 * 1024)  # 1MB threshold
            
            # Only h264 file should be returned
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].name, 'h264.mp4')
    
    @patch('convert_videos.get_codec')
    def test_find_eligible_files_skips_failed(self, mock_get_codec):
        """Test that files with .fail extension are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # Create test files (using smaller sizes for faster tests)
            normal_file = tmpdir_path / 'normal.mp4'
            failed_file = tmpdir_path / 'failed.mp4.fail'
            failed_file_numbered = tmpdir_path / 'failed2.mp4.fail_1'
            
            normal_file.write_bytes(b'x' * (2 * 1024 * 1024))  # 2MB
            failed_file.write_bytes(b'x' * (2 * 1024 * 1024))  # 2MB
            failed_file_numbered.write_bytes(b'x' * (2 * 1024 * 1024))  # 2MB
            
            mock_get_codec.return_value = 'h264'
            
            result = convert_videos.find_eligible_files(tmpdir, min_size_bytes=1024 * 1024)  # 1MB threshold
            
            # Only normal file should be returned
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].name, 'normal.mp4')
    
    @patch('convert_videos.get_codec')
    def test_find_eligible_files_sorts_by_size(self, mock_get_codec):
        """Test that files are sorted by size (largest first)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # Create test files of different sizes (using smaller sizes for faster tests)
            small = tmpdir_path / 'small.mp4'
            medium = tmpdir_path / 'medium.mp4'
            large = tmpdir_path / 'large.mp4'
            
            small.write_bytes(b'x' * (1 * 1024 * 1024))   # 1MB
            medium.write_bytes(b'x' * (2 * 1024 * 1024))  # 2MB
            large.write_bytes(b'x' * (3 * 1024 * 1024))   # 3MB
            
            mock_get_codec.return_value = 'h264'
            
            result = convert_videos.find_eligible_files(tmpdir, min_size_bytes=1024 * 1024)  # 1MB threshold
            
            # Should be sorted largest first
            self.assertEqual(len(result), 3)
            self.assertEqual(result[0].name, 'large.mp4')
            self.assertEqual(result[1].name, 'medium.mp4')
            self.assertEqual(result[2].name, 'small.mp4')


class TestValidateAndFinalize(unittest.TestCase):
    """Test validation and finalization of converted files."""
    
    @patch('convert_videos.get_duration')
    def test_validate_and_finalize_success(self, mock_get_duration):
        """Test successful validation with matching durations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            input_file = tmpdir_path / 'input.mp4'
            temp_file = tmpdir_path / 'temp.mkv.temp'
            final_file = tmpdir_path / 'final.mkv'
            
            input_file.write_text('input')
            temp_file.write_text('temp')
            
            # Mock durations to be the same
            mock_get_duration.return_value = 3600
            
            result = convert_videos.validate_and_finalize(
                input_file, temp_file, final_file, preserve_original=False
            )
            
            self.assertTrue(result)
            self.assertFalse(input_file.exists())
            self.assertFalse(temp_file.exists())
            self.assertTrue(final_file.exists())
    
    @patch('convert_videos.get_duration')
    def test_validate_and_finalize_preserve_original(self, mock_get_duration):
        """Test successful validation with preserve_original=True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            input_file = tmpdir_path / 'input.mp4'
            temp_file = tmpdir_path / 'temp.mkv.temp'
            final_file = tmpdir_path / 'final.mkv'
            
            input_file.write_text('input')
            temp_file.write_text('temp')
            
            # Mock durations to be the same
            mock_get_duration.return_value = 3600
            
            result = convert_videos.validate_and_finalize(
                input_file, temp_file, final_file, preserve_original=True
            )
            
            self.assertTrue(result)
            self.assertTrue(input_file.exists())  # Original should still exist
            self.assertFalse(temp_file.exists())
            self.assertTrue(final_file.exists())
    
    @patch('convert_videos.get_duration')
    def test_validate_and_finalize_duration_mismatch(self, mock_get_duration):
        """Test validation failure with mismatched durations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            input_file = tmpdir_path / 'input.mp4'
            temp_file = tmpdir_path / 'temp.mkv.temp'
            final_file = tmpdir_path / 'final.mkv'
            
            input_file.write_text('input')
            temp_file.write_text('temp')
            
            # Mock durations to be different
            mock_get_duration.side_effect = [3600, 3500]
            
            result = convert_videos.validate_and_finalize(
                input_file, temp_file, final_file, preserve_original=False
            )
            
            self.assertFalse(result)
            self.assertFalse(input_file.exists())  # Original renamed to .fail
            self.assertFalse(temp_file.exists())
            self.assertTrue(final_file.exists())
            
            # Check for .fail file
            fail_files = list(tmpdir_path.glob('*.fail*'))
            self.assertEqual(len(fail_files), 1)
    
    @patch('convert_videos.get_duration')
    def test_validate_and_finalize_zero_duration(self, mock_get_duration):
        """Test validation failure when duration cannot be determined."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            input_file = tmpdir_path / 'input.mp4'
            temp_file = tmpdir_path / 'temp.mkv.temp'
            final_file = tmpdir_path / 'final.mkv'
            
            input_file.write_text('input')
            temp_file.write_text('temp')
            
            # Mock one duration to be zero
            mock_get_duration.side_effect = [3600, 0]
            
            result = convert_videos.validate_and_finalize(
                input_file, temp_file, final_file, preserve_original=False
            )
            
            self.assertFalse(result)
            self.assertTrue(input_file.exists())  # Original should still exist on error
            self.assertFalse(temp_file.exists())  # Temp should be cleaned up
            self.assertFalse(final_file.exists())


class TestConvertFile(unittest.TestCase):
    """Test convert_file function."""
    
    def test_convert_file_invalid_format(self):
        """Test that invalid output format returns False."""
        output_config = {
            'format': 'avi',  # Invalid
            'encoder': 'x265',
            'preset': 'medium',
            'quality': 24
        }
        
        result = convert_videos.convert_file(
            '/path/to/video.mp4',
            dry_run=False,
            preserve_original=False,
            output_config=output_config
        )
        
        self.assertFalse(result)
    
    def test_convert_file_invalid_encoder(self):
        """Test that invalid encoder returns False."""
        output_config = {
            'format': 'mkv',
            'encoder': 'invalid',  # Invalid
            'preset': 'medium',
            'quality': 24
        }
        
        result = convert_videos.convert_file(
            '/path/to/video.mp4',
            dry_run=False,
            preserve_original=False,
            output_config=output_config
        )
        
        self.assertFalse(result)
    
    def test_convert_file_invalid_preset(self):
        """Test that invalid preset returns False."""
        output_config = {
            'format': 'mkv',
            'encoder': 'x265',
            'preset': 'invalid',  # Invalid
            'quality': 24
        }
        
        result = convert_videos.convert_file(
            '/path/to/video.mp4',
            dry_run=False,
            preserve_original=False,
            output_config=output_config
        )
        
        self.assertFalse(result)
    
    def test_convert_file_invalid_quality(self):
        """Test that invalid quality returns False."""
        output_config = {
            'format': 'mkv',
            'encoder': 'x265',
            'preset': 'medium',
            'quality': 100  # Invalid (must be 0-51)
        }
        
        result = convert_videos.convert_file(
            '/path/to/video.mp4',
            dry_run=False,
            preserve_original=False,
            output_config=output_config
        )
        
        self.assertFalse(result)
    
    def test_convert_file_dry_run(self):
        """Test dry run mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            input_file = tmpdir_path / 'input.mp4'
            input_file.write_text('test')
            
            output_config = {
                'format': 'mkv',
                'encoder': 'x265',
                'preset': 'medium',
                'quality': 24
            }
            
            result = convert_videos.convert_file(
                input_file,
                dry_run=True,
                preserve_original=False,
                output_config=output_config
            )
            
            self.assertTrue(result)
            # No output file should be created in dry run
            self.assertEqual(len(list(tmpdir_path.glob('*.mkv'))), 0)


class TestCheckDependencies(unittest.TestCase):
    """Test dependency checking."""
    
    @patch('convert_videos.subprocess.run')
    @patch('convert_videos.sys.exit')
    def test_check_dependencies_missing(self, mock_exit, mock_run):
        """Test that missing dependencies trigger exit."""
        mock_run.side_effect = FileNotFoundError()
        
        convert_videos.check_dependencies()
        
        mock_exit.assert_called_once_with(1)
    
    @patch('convert_videos.subprocess.run')
    def test_check_dependencies_all_present(self, mock_run):
        """Test that all dependencies present doesn't exit."""
        mock_run.return_value = MagicMock(returncode=0)
        
        # Should not raise exception
        try:
            convert_videos.check_dependencies()
        except SystemExit:
            self.fail("check_dependencies raised SystemExit unexpectedly")
    
    @patch('convert_videos.subprocess.run')
    def test_check_dependencies_custom_paths(self, mock_run):
        """Test dependency checking with custom paths."""
        mock_run.return_value = MagicMock(returncode=0)
        
        custom_paths = {
            'handbrake': '/custom/HandBrakeCLI',
            'ffprobe': '/custom/ffprobe'
        }
        
        # Should not raise exception
        try:
            convert_videos.check_dependencies(custom_paths)
        except SystemExit:
            self.fail("check_dependencies raised SystemExit unexpectedly")
        
        # Verify custom paths were used
        calls = mock_run.call_args_list
        self.assertEqual(len(calls), 2)
        
        # Check that custom paths were used in the calls
        called_paths = []
        for call in calls:
            call_args = call[0]
            command = call_args[0]
            executable = command[0]
            called_paths.append(executable)
        
        self.assertIn('/custom/ffprobe', called_paths)
        self.assertIn('/custom/HandBrakeCLI', called_paths)
    
    @patch('convert_videos.subprocess.run')
    @patch('convert_videos.sys.exit')
    def test_check_dependencies_custom_paths_missing(self, mock_exit, mock_run):
        """Test that missing custom dependency paths trigger exit."""
        mock_run.side_effect = FileNotFoundError()
        
        custom_paths = {
            'handbrake': '/nonexistent/HandBrakeCLI',
            'ffprobe': '/nonexistent/ffprobe'
        }
        
        convert_videos.check_dependencies(custom_paths)
        
        mock_exit.assert_called_once_with(1)
    
    @patch('convert_videos.subprocess.run')
    def test_check_dependencies_partial_custom_paths(self, mock_run):
        """Test dependency checking with partial custom paths."""
        mock_run.return_value = MagicMock(returncode=0)
        
        custom_paths = {
            'handbrake': '/custom/HandBrakeCLI',
            # ffprobe will use default
        }
        
        # Should not raise exception
        try:
            convert_videos.check_dependencies(custom_paths)
        except SystemExit:
            self.fail("check_dependencies raised SystemExit unexpectedly")
        
        # Verify mixed paths were used
        calls = mock_run.call_args_list
        self.assertEqual(len(calls), 2)
        
        called_paths = []
        for call in calls:
            call_args = call[0]
            command = call_args[0]
            executable = command[0]
            called_paths.append(executable)
        
        self.assertIn('/custom/HandBrakeCLI', called_paths)
        self.assertIn('ffprobe', called_paths)


if __name__ == '__main__':
    unittest.main()
