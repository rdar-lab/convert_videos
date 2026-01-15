#!/usr/bin/env python3
"""
Unit tests for convert_videos_gui.py
"""

import unittest
from unittest.mock import patch, MagicMock

# Import the GUI module (but don't run GUI components)
try:
    from convert_videos_gui import ConversionResult, VideoConverterGUI
    GUI_AVAILABLE = True
except ImportError:
    # tkinter might not be available in headless environments
    GUI_AVAILABLE = False


@unittest.skipIf(not GUI_AVAILABLE, "GUI module not available (tkinter missing)")
class TestConversionResult(unittest.TestCase):
    """Test ConversionResult class."""
    
    def test_successful_conversion(self):
        """Test result for successful conversion."""
        result = ConversionResult(
            file_path="/path/to/video.mp4",
            success=True,
            error_message=None,
            original_size=1000000000,  # 1GB
            new_size=600000000  # 600MB
        )
        
        self.assertEqual(result.file_path, "/path/to/video.mp4")
        self.assertTrue(result.success)
        self.assertIsNone(result.error_message)
        self.assertEqual(result.original_size, 1000000000)
        self.assertEqual(result.new_size, 600000000)
        self.assertEqual(result.space_saved, 400000000)
        self.assertAlmostEqual(result.space_saved_percent, 40.0, places=1)
    
    def test_failed_conversion(self):
        """Test result for failed conversion."""
        result = ConversionResult(
            file_path="/path/to/video.mp4",
            success=False,
            error_message="Conversion failed",
            original_size=1000000000,
            new_size=0
        )
        
        self.assertEqual(result.file_path, "/path/to/video.mp4")
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "Conversion failed")
        self.assertEqual(result.space_saved, 0)
        self.assertEqual(result.space_saved_percent, 0)
    
    def test_zero_original_size(self):
        """Test result with zero original size."""
        result = ConversionResult(
            file_path="/path/to/video.mp4",
            success=True,
            error_message=None,
            original_size=0,
            new_size=0
        )
        
        self.assertEqual(result.space_saved, 0)
        self.assertEqual(result.space_saved_percent, 0)
    
    def test_larger_output_file(self):
        """Test when output file is larger than input."""
        result = ConversionResult(
            file_path="/path/to/video.mp4",
            success=True,
            error_message=None,
            original_size=500000000,
            new_size=700000000  # Larger
        )
        
        # Space saved should be negative
        self.assertEqual(result.space_saved, -200000000)
        self.assertLess(result.space_saved_percent, 0)


@unittest.skipIf(not GUI_AVAILABLE, "GUI module not available (tkinter missing)")
class TestVideoConverterGUIHelpers(unittest.TestCase):
    """Test VideoConverterGUI helper methods."""
    
    def test_format_size_bytes(self):
        """Test formatting bytes."""
        self.assertEqual(VideoConverterGUI.format_size(0), "0 B")
        self.assertEqual(VideoConverterGUI.format_size(100), "100.00 B")
        self.assertEqual(VideoConverterGUI.format_size(999), "999.00 B")
    
    def test_format_size_kilobytes(self):
        """Test formatting kilobytes."""
        self.assertEqual(VideoConverterGUI.format_size(1024), "1.00 KB")
        self.assertEqual(VideoConverterGUI.format_size(1536), "1.50 KB")
        self.assertEqual(VideoConverterGUI.format_size(2048), "2.00 KB")
    
    def test_format_size_megabytes(self):
        """Test formatting megabytes."""
        self.assertEqual(VideoConverterGUI.format_size(1024 ** 2), "1.00 MB")
        self.assertEqual(VideoConverterGUI.format_size(int(1.5 * 1024 ** 2)), "1.50 MB")
        self.assertEqual(VideoConverterGUI.format_size(1024 ** 2 * 100), "100.00 MB")
    
    def test_format_size_gigabytes(self):
        """Test formatting gigabytes."""
        self.assertEqual(VideoConverterGUI.format_size(1024 ** 3), "1.00 GB")
        self.assertEqual(VideoConverterGUI.format_size(int(2.5 * 1024 ** 3)), "2.50 GB")
        self.assertEqual(VideoConverterGUI.format_size(1024 ** 3 * 10), "10.00 GB")
    
    def test_format_size_terabytes(self):
        """Test formatting terabytes."""
        self.assertEqual(VideoConverterGUI.format_size(1024 ** 4), "1.00 TB")
        self.assertEqual(VideoConverterGUI.format_size(int(1.5 * 1024 ** 4)), "1.50 TB")
    
    def test_format_size_negative(self):
        """Test formatting negative sizes."""
        # Should handle gracefully
        result = VideoConverterGUI.format_size(-1024)
        self.assertIn("-", result)


@unittest.skipIf(not GUI_AVAILABLE, "GUI module not available (tkinter missing)")
class TestVideoConverterGUIInit(unittest.TestCase):
    """Test VideoConverterGUI initialization."""
    
    @patch('convert_videos_gui.configuration_manager.load_config')
    @patch('convert_videos_gui.tk.Tk')
    def test_gui_initialization(self, mock_tk, mock_load_config):
        """Test GUI initializes with proper structure."""
        # Mock config
        mock_config = {
            'dependencies': {
                'handbrake': '/usr/bin/HandBrakeCLI',
                'ffprobe': '/usr/bin/ffprobe',
                'ffmpeg': '/usr/bin/ffmpeg'
            },
            'directory': '/test/dir',
            'min_file_size': 1000000,
            'output': {'directory': '/output', 'format': 'mkv'},
            'dry_run': False,
            'loop': False,
            'remove_original_files': False
        }
        mock_load_config.return_value = (mock_config, [])
        
        # Mock root
        mock_root = MagicMock()
        
        # Create a custom create_ui that sets up necessary attributes
        def mock_create_ui(self):
            self.notebook = MagicMock()
        
        # Create GUI instance
        with patch.object(VideoConverterGUI, 'create_ui', mock_create_ui):
            with patch.object(VideoConverterGUI, 'update_progress'):
                with patch.object(VideoConverterGUI, 'update_duplicate_progress'):
                    gui = VideoConverterGUI(mock_root)
        
        # Verify initialization
        self.assertEqual(gui.root, mock_root)
        self.assertIsNotNone(gui.config)
        self.assertEqual(gui.file_queue, [])
        self.assertFalse(gui.is_running)
        self.assertFalse(gui.stop_requested)


@unittest.skipIf(not GUI_AVAILABLE, "GUI module not available (tkinter missing)")
class TestVideoConverterGUIMethods(unittest.TestCase):
    """Test VideoConverterGUI methods."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock configuration
        mock_config = {
            'dependencies': {
                'handbrake': '/usr/bin/HandBrakeCLI',
                'ffprobe': '/usr/bin/ffprobe',
                'ffmpeg': '/usr/bin/ffmpeg'
            },
            'directory': '/test/dir',
            'min_file_size': 1000000,
            'output': {'directory': '/output', 'format': 'mkv'},
            'dry_run': False,
            'loop': False,
            'remove_original_files': False
        }
        
        # Create a custom create_ui that sets up necessary attributes
        def mock_create_ui(self):
            self.notebook = MagicMock()
        
        with patch('convert_videos_gui.configuration_manager.load_config', return_value=(mock_config, [])):
            with patch('convert_videos_gui.tk.Tk'):
                with patch.object(VideoConverterGUI, 'create_ui', mock_create_ui):
                    with patch.object(VideoConverterGUI, 'update_progress'):
                        with patch.object(VideoConverterGUI, 'update_duplicate_progress'):
                            mock_root = MagicMock()
                            self.gui = VideoConverterGUI(mock_root)
    
    def test_stop_processing(self):
        """Test stopping processing."""
        self.gui.is_running = True
        self.gui.stop_requested = False
        
        # Mock necessary UI elements
        self.gui.stop_button = MagicMock()
        self.gui.start_button = MagicMock()
        
        self.gui.stop_processing()
        
        self.assertTrue(self.gui.stop_requested)
    
    def test_clear_results(self):
        """Test clearing results."""
        self.gui.conversion_results = [
            ConversionResult("/test1.mp4", True),
            ConversionResult("/test2.mp4", False, "Error")
        ]
        
        # Mock the results tree
        self.gui.results_tree = MagicMock()
        self.gui.summary_label = MagicMock()
        
        self.gui.clear_results()
        
        self.assertEqual(len(self.gui.conversion_results), 0)
    
    def test_scan_files(self):
        """Test scanning for files."""
        # Mock directory_var
        self.gui.directory_var = MagicMock()
        self.gui.directory_var.get.return_value = '/test/dir'
        
        # Mock other dependencies
        self.gui.file_tree = MagicMock()
        self.gui.min_file_size_var = MagicMock()
        self.gui.min_file_size_var.get.return_value = '100'
        
        with patch('convert_videos_gui.convert_videos.find_eligible_files', return_value=['/test/file.mp4']):
            self.gui.scan_files()
        
        self.assertEqual(len(self.gui.file_queue), 1)
    
    @patch('convert_videos_gui.messagebox')
    def test_validate_config_valid(self, mock_messagebox):
        """Test validating valid configuration."""
        # Mock necessary UI elements
        self.gui.dir_entry = MagicMock()
        self.gui.dir_entry.get.return_value = '/test/dir'
        
        with patch('convert_videos_gui.dependencies_utils.validate_dependencies', return_value=True):
            result = self.gui.validate_config()
        
        self.assertTrue(result)
    
    @patch('convert_videos_gui.messagebox')
    def test_validate_config_invalid(self, mock_messagebox):
        """Test validating invalid configuration."""
        # Mock necessary UI elements
        self.gui.dir_entry = MagicMock()
        self.gui.dir_entry.get.return_value = ''
        
        with patch('convert_videos_gui.dependencies_utils.validate_dependencies', return_value=False):
            result = self.gui.validate_config()
        
        self.assertFalse(result)
        # Should show error message
        mock_messagebox.showerror.assert_called_once()
    
    def test_progress_callback(self):
        """Test progress callback."""
        # Mock progress label
        self.gui.progress_label = MagicMock()
        self.gui.status_label = MagicMock()
        
        # Put progress in queue
        self.gui.progress_queue.put(('progress', 50.0))
        
        # Mock the root after to avoid actual tk scheduling
        with patch.object(self.gui.root, 'after'):
            # Update should read from queue
            self.gui.update_progress()
    
    def test_generate_config(self):
        """Test generating config from UI."""
        # Mock all the UI elements needed
        self.gui.directory_var = MagicMock()
        self.gui.directory_var.get.return_value = '/test/dir'
        self.gui.dry_run_var = MagicMock()
        self.gui.dry_run_var.get.return_value = False
        self.gui.loop_var = MagicMock()
        self.gui.loop_var.get.return_value = False
        self.gui.remove_original_var = MagicMock()
        self.gui.remove_original_var.get.return_value = False
        self.gui.min_file_size_var = MagicMock()
        self.gui.min_file_size_var.get.return_value = '100'
        self.gui.output_directory_var = MagicMock()
        self.gui.output_directory_var.get.return_value = ''
        self.gui.output_format_var = MagicMock()
        self.gui.output_format_var.get.return_value = 'mkv'
        self.gui.encoder_type_var = MagicMock()
        self.gui.encoder_type_var.get.return_value = 'x265'
        self.gui.encoder_preset_var = MagicMock()
        self.gui.encoder_preset_var.get.return_value = 'medium'
        self.gui.quality_var = MagicMock()
        self.gui.quality_var.get.return_value = '22'
        self.gui.handbrake_var = MagicMock()
        self.gui.handbrake_var.get.return_value = ''
        self.gui.ffprobe_var = MagicMock()
        self.gui.ffprobe_var.get.return_value = ''
        self.gui.ffmpeg_var = MagicMock()
        self.gui.ffmpeg_var.get.return_value = ''
        self.gui.log_file_var = MagicMock()
        self.gui.log_file_var.get.return_value = ''
        
        config = self.gui.generate_config()
        
        self.assertIsNotNone(config)
        self.assertEqual(config['directory'], '/test/dir')
    
    def test_browse_directory(self):
        """Test browsing for directory."""
        # Mock directory entry
        self.gui.directory_var = MagicMock()
        
        with patch('convert_videos_gui.filedialog.askdirectory', return_value='/new/path'):
            self.gui.browse_directory()
        
        self.gui.directory_var.set.assert_called_with('/new/path')


if __name__ == '__main__':
    unittest.main()
