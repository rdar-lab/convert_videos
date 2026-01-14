#!/usr/bin/env python3
"""
GUI for convert_videos - Headed mode with configuration editor, queue management, and results display.
"""

import logging
import os
import platform
import queue
import re
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import yaml
from PIL import Image, ImageTk

import configuration_manager
import convert_videos
import duplicate_detector
import dependencies_utils

logger = logging.getLogger(__name__)

# Constants
PROGRESS_UPDATE_INTERVAL_MS = 100  # Milliseconds between progress updates
# Maximum number of attempts to find unique output filename
MAX_OUTPUT_FILE_ATTEMPTS = 100


class ConversionResult:
    """Represents the result of a video conversion."""

    def __init__(self, file_path, success, error_message=None, original_size=0, new_size=0):
        self.file_path = file_path
        self.success = success
        self.error_message = error_message
        self.original_size = original_size
        self.new_size = new_size
        self.space_saved = original_size - new_size if success else 0
        self.space_saved_percent = (
            self.space_saved / original_size * 100) if original_size > 0 else 0


class VideoConverterGUI:
    """Main GUI application for video converter."""

    def __init__(self, root):
        self.root = root
        self.root.title("Video Converter - H.265 (HEVC)")
        self.root.geometry("1000x700")

        # Configuration
        config, _ = configuration_manager.load_config()

        self.config_file_path = Path('config.yaml')

        # Log bundled dependency paths for debugging
        # Note: These logs go to the log file (not console) and are useful for troubleshooting
        # standalone executables where bundled dependencies should be auto-detected
        deps = self.config.get('dependencies', {})
        logger.info(
            f"GUI initialized with HandBrakeCLI path: {deps.get('handbrake')}")
        logger.info(
            f"GUI initialized with ffprobe path: {deps.get('ffprobe')}")
        logger.info(f"GUI initialized with ffmpeg path: {deps.get('ffmpeg')}")

        # Queue and results
        self.file_queue = []
        self.current_file = None
        self.conversion_results = []
        self.is_running = False
        self.stop_requested = False

        # Duplicate detection state
        self.duplicate_results = []
        self.duplicate_scan_running = False
        # Separate queue for duplicate detection
        self.duplicate_progress_queue = queue.Queue()
        self.thumbnail_tooltip = None  # For showing thumbnail on hover
        self.thumbnail_images = {}  # Keep references to prevent garbage collection

        # Thread communication
        self.progress_queue = queue.Queue()
        self.conversion_thread = None

        # Create UI
        self.create_ui()

        # Bind tab switch event to regenerate config
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        # Start progress update loops
        self.update_progress()
        self.update_duplicate_progress()

    def create_ui(self):
        """Create the main UI with tabs."""
        # Create notebook (tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)

        # Configuration Tab
        self.config_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.config_tab, text="Configuration")
        self.create_config_tab()

        # Processing Tab
        self.processing_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.processing_tab, text="Processing")
        self.create_processing_tab()

        # Results Tab
        self.results_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.results_tab, text="Results")
        self.create_results_tab()

        # Detect Duplicates Tab
        self.duplicates_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.duplicates_tab, text="Detect Duplicates")
        self.create_duplicates_tab()

    def create_config_tab(self):
        """Create the configuration editor tab."""
        # Main container with scrollbar
        canvas = tk.Canvas(self.config_tab)
        scrollbar = ttk.Scrollbar(
            self.config_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Directory selection
        dir_frame = ttk.LabelFrame(
            scrollable_frame, text="Directory Settings", padding=10)
        dir_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(dir_frame, text="Target Directory:").grid(
            row=0, column=0, sticky='w', pady=5)
        self.dir_entry = ttk.Entry(dir_frame, width=50)
        self.dir_entry.grid(row=0, column=1, padx=5, pady=5)
        # Default to current working directory if no directory in config
        default_dir = self.config.get('directory') or os.getcwd()
        self.dir_entry.insert(0, default_dir)
        ttk.Button(dir_frame, text="Browse...", command=self.browse_directory).grid(
            row=0, column=2, pady=5)

        ttk.Label(dir_frame, text="Min File Size:").grid(
            row=1, column=0, sticky='w', pady=5)
        self.min_size_entry = ttk.Entry(dir_frame, width=20)
        self.min_size_entry.grid(row=1, column=1, sticky='w', padx=5, pady=5)
        self.min_size_entry.insert(
            0, str(self.config.get('min_file_size') or '1GB'))
        ttk.Label(dir_frame, text="(e.g., 1GB, 500MB)").grid(
            row=1, column=2, sticky='w')

        # Output settings
        output_frame = ttk.LabelFrame(
            scrollable_frame, text="Output Settings", padding=10)
        output_frame.pack(fill='x', padx=10, pady=5)

        output_config = self.config.get('output', {})

        ttk.Label(output_frame, text="Format:").grid(
            row=0, column=0, sticky='w', pady=5)
        self.format_var = tk.StringVar(
            value=output_config.get('format', 'mkv'))
        format_combo = ttk.Combobox(output_frame, textvariable=self.format_var,
                                    values=list(configuration_manager.SUPPORTED_FORMATS), state='readonly', width=18)
        format_combo.grid(row=0, column=1, sticky='w', padx=5, pady=5)

        ttk.Label(output_frame, text="Encoder:").grid(
            row=1, column=0, sticky='w', pady=5)
        self.encoder_var = tk.StringVar(
            value=output_config.get('encoder', 'x265_10bit'))
        encoder_combo = ttk.Combobox(output_frame, textvariable=self.encoder_var,
                                     values=list(configuration_manager.SUPPORTED_ENCODERS), state='readonly', width=18)
        encoder_combo.grid(row=1, column=1, sticky='w', padx=5, pady=5)

        ttk.Label(output_frame, text="Preset:").grid(
            row=2, column=0, sticky='w', pady=5)
        self.preset_var = tk.StringVar(
            value=output_config.get('preset', 'medium'))
        preset_combo = ttk.Combobox(output_frame, textvariable=self.preset_var,
                                    values=list(configuration_manager.SUPPORTED_PRESETS), state='readonly', width=18)
        preset_combo.grid(row=2, column=1, sticky='w', padx=5, pady=5)

        ttk.Label(output_frame, text="Quality:").grid(
            row=3, column=0, sticky='w', pady=5)
        self.quality_entry = ttk.Entry(output_frame, width=20)
        self.quality_entry.grid(row=3, column=1, sticky='w', padx=5, pady=5)
        self.quality_entry.insert(0, str(output_config.get('quality') or 24))
        ttk.Label(output_frame, text="(0-51, lower=better)").grid(row=3,
                                                                  column=2, sticky='w')

        # Dependencies settings
        deps_frame = ttk.LabelFrame(
            scrollable_frame, text="Dependencies (Optional)", padding=10)
        deps_frame.pack(fill='x', padx=10, pady=5)

        dependency_config = self.config.get('dependencies', {})

        ttk.Label(deps_frame, text="HandBrakeCLI:").grid(
            row=0, column=0, sticky='w', pady=5)
        self.handbrake_entry = ttk.Entry(deps_frame, width=60)
        self.handbrake_entry.grid(row=0, column=1, padx=5, pady=5)
        self.handbrake_entry.insert(
            0, dependency_config.get('handbrake') or 'HandBrakeCLI')
        ttk.Button(deps_frame, text="Browse...", command=self.browse_handbrake).grid(
            row=0, column=2, pady=5)

        ttk.Label(deps_frame, text="ffprobe:").grid(
            row=1, column=0, sticky='w', pady=5)
        self.ffprobe_entry = ttk.Entry(deps_frame, width=60)
        self.ffprobe_entry.grid(row=1, column=1, padx=5, pady=5)
        self.ffprobe_entry.insert(
            0, dependency_config.get('ffprobe') or 'ffprobe')
        ttk.Button(deps_frame, text="Browse...", command=self.browse_ffprobe).grid(
            row=1, column=2, pady=5)

        ttk.Label(deps_frame, text="ffmpeg:").grid(
            row=2, column=0, sticky='w', pady=5)
        self.ffmpeg_entry = ttk.Entry(deps_frame, width=60)
        self.ffmpeg_entry.grid(row=2, column=1, padx=5, pady=5)
        self.ffmpeg_entry.insert(
            0, dependency_config.get('ffmpeg') or 'ffmpeg')
        ttk.Button(deps_frame, text="Browse...", command=self.browse_ffmpeg).grid(
            row=2, column=2, pady=5)

        # Download dependencies button
        ttk.Button(deps_frame, text="Download Dependencies",
                   command=self.download_dependencies).grid(row=3, column=1, pady=10, sticky='w')

        # Other options
        options_frame = ttk.LabelFrame(
            scrollable_frame, text="Other Options", padding=10)
        options_frame.pack(fill='x', padx=10, pady=5)

        self.remove_original_var = tk.BooleanVar(
            value=self.config.get('remove_original_files', False))
        ttk.Checkbutton(options_frame, text="Remove Original Files After Conversion",
                        variable=self.remove_original_var).pack(anchor='w', pady=2)

        self.dry_run_var = tk.BooleanVar(
            value=self.config.get('dry_run', False))
        ttk.Checkbutton(options_frame, text="Dry Run (simulate only)",
                        variable=self.dry_run_var).pack(anchor='w', pady=2)

        # Validation status
        self.validation_frame = ttk.Frame(scrollable_frame)
        self.validation_frame.pack(fill='x', padx=10, pady=5)

        self.validation_label = ttk.Label(
            self.validation_frame, text="", foreground="blue")
        self.validation_label.pack(side='left', padx=5)

        # Buttons
        button_frame = ttk.Frame(scrollable_frame)
        button_frame.pack(fill='x', padx=10, pady=10)

        ttk.Button(button_frame, text="Validate Configuration",
                   command=self.validate_config).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Save Configuration",
                   command=self.save_config).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Load Configuration",
                   command=self.load_config_file).pack(side='left', padx=5)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def create_processing_tab(self):
        """Create the processing tab with queue, current file, and progress."""
        # Queue section
        queue_frame = ttk.LabelFrame(
            self.processing_tab, text="File Queue", padding=10)
        queue_frame.pack(fill='both', expand=True, padx=10, pady=5)

        # Queue listbox with scrollbar
        queue_scroll = ttk.Scrollbar(queue_frame, orient='vertical')
        self.queue_listbox = tk.Listbox(
            queue_frame, yscrollcommand=queue_scroll.set, height=10)
        queue_scroll.config(command=self.queue_listbox.yview)
        self.queue_listbox.pack(side='left', fill='both', expand=True)
        queue_scroll.pack(side='right', fill='y')

        # Current file section
        current_frame = ttk.LabelFrame(
            self.processing_tab, text="Currently Processing", padding=10)
        current_frame.pack(fill='x', padx=10, pady=5)

        self.current_file_label = ttk.Label(
            current_frame, text="No file being processed", wraplength=900)
        self.current_file_label.pack(fill='x', pady=5)

        # Progress bar
        self.progress_bar = ttk.Progressbar(
            current_frame, mode='determinate', maximum=100)
        self.progress_bar.pack(fill='x', pady=5)

        self.progress_label = ttk.Label(current_frame, text="")
        self.progress_label.pack(fill='x', pady=2)

        # Control buttons
        button_frame = ttk.Frame(self.processing_tab)
        button_frame.pack(fill='x', padx=10, pady=10)

        self.scan_button = ttk.Button(
            button_frame, text="Scan for Files", command=self.scan_files)
        self.scan_button.pack(side='left', padx=5)

        self.start_button = ttk.Button(button_frame, text="Start Processing",
                                       command=self.start_processing, state='disabled')
        self.start_button.pack(side='left', padx=5)

        self.stop_button = ttk.Button(button_frame, text="Stop",
                                      command=self.stop_processing, state='disabled')
        self.stop_button.pack(side='left', padx=5)

    def create_results_tab(self):
        """Create the results tab with finished conversions."""
        # Results tree
        tree_frame = ttk.Frame(self.results_tab)
        tree_frame.pack(fill='both', expand=True, padx=10, pady=5)

        # Scrollbars
        tree_scroll_y = ttk.Scrollbar(tree_frame, orient='vertical')
        tree_scroll_x = ttk.Scrollbar(tree_frame, orient='horizontal')

        # Create treeview
        columns = ('Status', 'Original Size',
                   'New Size', 'Space Saved', 'Error')
        self.results_tree = ttk.Treeview(tree_frame, columns=columns, show='tree headings',
                                         yscrollcommand=tree_scroll_y.set,
                                         xscrollcommand=tree_scroll_x.set)

        tree_scroll_y.config(command=self.results_tree.yview)
        tree_scroll_x.config(command=self.results_tree.xview)

        # Configure columns
        self.results_tree.heading('#0', text='File')
        self.results_tree.heading('Status', text='Status')
        self.results_tree.heading('Original Size', text='Original Size')
        self.results_tree.heading('New Size', text='New Size')
        self.results_tree.heading('Space Saved', text='Space Saved')
        self.results_tree.heading('Error', text='Error Message')

        self.results_tree.column('#0', width=300, minwidth=200)
        self.results_tree.column('Status', width=100, minwidth=80)
        self.results_tree.column('Original Size', width=120, minwidth=100)
        self.results_tree.column('New Size', width=120, minwidth=100)
        self.results_tree.column('Space Saved', width=150, minwidth=120)
        self.results_tree.column('Error', width=200, minwidth=150)

        # Pack
        self.results_tree.pack(side='left', fill='both', expand=True)
        tree_scroll_y.pack(side='right', fill='y')
        tree_scroll_x.pack(side='bottom', fill='x')

        # Summary label
        self.summary_label = ttk.Label(
            self.results_tab, text="No conversions completed yet")
        self.summary_label.pack(fill='x', padx=10, pady=5)

        # Clear button
        ttk.Button(self.results_tab, text="Clear Results",
                   command=self.clear_results).pack(pady=5)

    def create_duplicates_tab(self):
        """Create the duplicate detection tab."""
        # Directory selection
        dir_frame = ttk.LabelFrame(
            self.duplicates_tab, text="Scan Settings", padding=10)
        dir_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(dir_frame, text="Directory to Scan:").grid(
            row=0, column=0, sticky='w', pady=5)
        self.dup_dir_entry = ttk.Entry(dir_frame, width=50)
        self.dup_dir_entry.grid(row=0, column=1, padx=5, pady=5)
        default_dir = self.config.get('directory') or os.getcwd()
        self.dup_dir_entry.insert(0, default_dir)
        ttk.Button(dir_frame, text="Browse...", command=self.browse_duplicate_directory).grid(
            row=0, column=2, pady=5)

        ttk.Label(dir_frame, text="Max Hamming Distance:").grid(
            row=1, column=0, sticky='w', pady=5)
        self.hamming_distance_entry = ttk.Entry(dir_frame, width=10)
        self.hamming_distance_entry.grid(
            row=1, column=1, sticky='w', padx=5, pady=5)
        self.hamming_distance_entry.insert(0, "5")
        ttk.Label(dir_frame, text="(Lower = more similar, recommended: 5)").grid(
            row=1, column=2, sticky='w')

        # Control buttons
        button_frame = ttk.Frame(self.duplicates_tab)
        button_frame.pack(fill='x', padx=10, pady=5)

        self.scan_duplicates_button = ttk.Button(button_frame, text="Scan for Duplicates",
                                                 command=self.scan_for_duplicates)
        self.scan_duplicates_button.pack(side='left', padx=5)

        self.clear_duplicates_button = ttk.Button(button_frame, text="Clear Results",
                                                  command=self.clear_duplicate_results)
        self.clear_duplicates_button.pack(side='left', padx=5)

        # Status label
        self.dup_status_label = ttk.Label(
            self.duplicates_tab, text="Ready to scan", foreground="blue")
        self.dup_status_label.pack(fill='x', padx=10, pady=5)

        # Progress bar
        self.dup_progress_bar = ttk.Progressbar(
            self.duplicates_tab, mode='indeterminate')
        self.dup_progress_bar.pack(fill='x', padx=10, pady=5)

        # Results tree
        tree_frame = ttk.Frame(self.duplicates_tab)
        tree_frame.pack(fill='both', expand=True, padx=10, pady=5)

        # Scrollbars
        tree_scroll_y = ttk.Scrollbar(tree_frame, orient='vertical')
        tree_scroll_x = ttk.Scrollbar(tree_frame, orient='horizontal')

        # Create treeview
        columns = ('Distance', 'Files', 'Thumbnail')
        self.duplicates_tree = ttk.Treeview(tree_frame, columns=columns, show='tree headings',
                                            yscrollcommand=tree_scroll_y.set,
                                            xscrollcommand=tree_scroll_x.set)

        tree_scroll_y.config(command=self.duplicates_tree.yview)
        tree_scroll_x.config(command=self.duplicates_tree.xview)

        # Configure columns
        self.duplicates_tree.heading('#0', text='Group / File')
        self.duplicates_tree.heading('Distance', text='Hamming Distance')
        self.duplicates_tree.heading('Files', text='File Count')
        self.duplicates_tree.heading('Thumbnail', text='Thumbnail Path')

        self.duplicates_tree.column('#0', width=200, minwidth=150)
        self.duplicates_tree.column('Distance', width=120, minwidth=100)
        self.duplicates_tree.column('Files', width=100, minwidth=80)
        self.duplicates_tree.column('Thumbnail', width=300, minwidth=200)

        # Pack
        self.duplicates_tree.pack(side='left', fill='both', expand=True)
        tree_scroll_y.pack(side='right', fill='y')
        tree_scroll_x.pack(side='bottom', fill='x')

        # Bind mouse events for thumbnail tooltips
        self.duplicates_tree.bind('<Motion>', self.show_thumbnail_tooltip)
        self.duplicates_tree.bind('<Leave>', self.hide_thumbnail_tooltip)

        # Bind right-click for context menu
        self.duplicates_tree.bind(
            '<Button-3>', self.show_file_context_menu)  # Right-click
        # Middle-click on macOS
        self.duplicates_tree.bind('<Button-2>', self.show_file_context_menu)

        # Summary label
        self.dup_summary_label = ttk.Label(
            self.duplicates_tab, text="No duplicates found yet")
        self.dup_summary_label.pack(fill='x', padx=10, pady=5)

    def browse_duplicate_directory(self):
        """Open directory browser for duplicate detection."""
        try:
            directory = filedialog.askdirectory(
                initialdir=self.dup_dir_entry.get())
            if directory:
                self.dup_dir_entry.delete(0, tk.END)
                self.dup_dir_entry.insert(0, directory)
        except Exception as e:
            logger.error(f"Browse directory error: {repr(e)}")
            messagebox.showerror(
                "Browse Error", f"Failed to browse directory:\n{repr(e)}")

    def browse_directory(self):
        """Open directory browser."""
        try:
            directory = filedialog.askdirectory(
                initialdir=self.dir_entry.get())
            if directory:
                self.dir_entry.delete(0, tk.END)
                self.dir_entry.insert(0, directory)
        except Exception as e:
            logger.error(f"Browse directory error: {repr(e)}")
            messagebox.showerror(
                "Browse Error", f"Failed to browse directory:\n{repr(e)}")

    def browse_handbrake(self):
        """Open file browser for HandBrakeCLI executable."""
        try:
            file_path = filedialog.askopenfilename(
                title="Select HandBrakeCLI executable",
                filetypes=[("Executable files", "*.exe"), ("All files", "*.*")]
            )
            if file_path:
                self.handbrake_entry.delete(0, tk.END)
                self.handbrake_entry.insert(0, file_path)
        except Exception as e:
            logger.error(f"Browse HandBrakeCLI error: {repr(e)}")
            messagebox.showerror(
                "Browse Error", f"Failed to browse for HandBrakeCLI:\n{repr(e)}")

    def browse_ffprobe(self):
        """Open file browser for ffprobe executable."""
        try:
            file_path = filedialog.askopenfilename(
                title="Select ffprobe executable",
                filetypes=[("Executable files", "*.exe"), ("All files", "*.*")]
            )
            if file_path:
                self.ffprobe_entry.delete(0, tk.END)
                self.ffprobe_entry.insert(0, file_path)
        except Exception as e:
            logger.error(f"Browse ffprobe error: {repr(e)}")
            messagebox.showerror(
                "Browse Error", f"Failed to browse for ffprobe:\n{repr(e)}")

    def browse_ffmpeg(self):
        """Open file browser for ffmpeg executable."""
        try:
            file_path = filedialog.askopenfilename(
                title="Select ffmpeg executable",
                filetypes=[("Executable files", "*.exe"), ("All files", "*.*")]
            )
            if file_path:
                self.ffmpeg_entry.delete(0, tk.END)
                self.ffmpeg_entry.insert(0, file_path)
        except Exception as e:
            logger.error(f"Browse ffmpeg error: {repr(e)}")
            messagebox.showerror(
                "Browse Error", f"Failed to browse for ffmpeg:\n{repr(e)}")

    def download_dependencies(self):
        """Download HandBrakeCLI and ffprobe to ./dependencies directory."""
        # Confirm with user
        result = messagebox.askyesno(
            "Download Dependencies",
            "This will download HandBrakeCLI and ffmpeg (includes ffprobe) to ./dependencies directory.\n\n"
            "Download sizes:\n"
            "- HandBrakeCLI: ~20-30 MB\n"
            "- ffmpeg: ~50-80 MB\n\n"
            "Continue?"
        )

        if not result:
            return

        # Run download in background thread
        def download_thread():
            def progress_callback(message):
                """Callback to report progress to GUI."""
                self.progress_queue.put(('download_status', message))

            try:
                # Call centralized download function
                handbrake_path, ffprobe_path, ffmpeg_path = dependencies_utils.download_dependencies(
                    progress_callback)

                if handbrake_path and ffprobe_path and ffmpeg_path:
                    self.progress_queue.put(
                        ('download_complete', (handbrake_path, ffprobe_path, ffmpeg_path)))
                else:
                    self.progress_queue.put(
                        ('download_error', "Download failed. Check logs for details."))

            except Exception as e:
                logger.error(f"Download dependencies error: {repr(e)}")
                self.progress_queue.put(('download_error', repr(e)))

        threading.Thread(target=download_thread, daemon=True).start()

    def validate_config(self):
        """Validate the current configuration."""
        errors = []

        # Validate directory
        directory = self.dir_entry.get().strip()
        if not directory:
            errors.append("Directory is required")
        elif not os.path.isdir(directory):
            errors.append(f"Directory does not exist: {directory}")

        # Validate min file size
        try:
            min_size = self.min_size_entry.get().strip()
            configuration_manager.parse_file_size(min_size)
        except ValueError as e:
            errors.append(f"Invalid min file size: {e}")

        # Validate format
        if not configuration_manager.validate_format(self.format_var.get()):
            errors.append(f"Invalid format: {self.format_var.get()}")

        # Validate encoder
        if not configuration_manager.validate_encoder(self.encoder_var.get()):
            errors.append(f"Invalid encoder: {self.encoder_var.get()}")

        # Validate preset
        if not configuration_manager.validate_preset(self.preset_var.get()):
            errors.append(f"Invalid preset: {self.preset_var.get()}")

        # Validate quality
        try:
            quality = int(self.quality_entry.get().strip())
            if not configuration_manager.validate_quality(quality):
                errors.append(f"Quality must be between 0 and 51")
        except ValueError:
            errors.append("Quality must be an integer")

        # Validate dependencies
        handbrake_path = self.handbrake_entry.get().strip()
        ffprobe_path = self.ffprobe_entry.get().strip()
        ffmpeg_path = self.ffmpeg_entry.get().strip()

        if handbrake_path:
            success, error_type = configuration_manager.check_single_dependency(
                handbrake_path)
            if not success:
                if error_type == "not_found":
                    errors.append(f"HandBrakeCLI not found: {handbrake_path}")
                elif error_type == "invalid":
                    errors.append(
                        f"HandBrakeCLI exists but is not a valid executable: {handbrake_path}")
                elif error_type == "timeout":
                    errors.append(f"HandBrakeCLI timed out: {handbrake_path}")

        if ffprobe_path:
            success, error_type = configuration_manager.check_single_dependency(
                ffprobe_path)
            if not success:
                if error_type == "not_found":
                    errors.append(f"ffprobe not found: {ffprobe_path}")
                elif error_type == "invalid":
                    errors.append(
                        f"ffprobe exists but is not a valid executable: {ffprobe_path}")
                elif error_type == "timeout":
                    errors.append(f"ffprobe timed out: {ffprobe_path}")

        if ffmpeg_path:
            success, error_type = configuration_manager.check_single_dependency(
                ffmpeg_path)
            if not success:
                if error_type == "not_found":
                    errors.append(f"ffmpeg not found: {ffmpeg_path}")
                elif error_type == "invalid":
                    errors.append(
                        f"ffmpeg exists but is not a valid executable: {ffmpeg_path}")
                elif error_type == "timeout":
                    errors.append(f"ffmpeg timed out: {ffmpeg_path}")

        # Display results
        if errors:
            self.validation_label.config(
                text="❌ Validation failed", foreground="red")
            messagebox.showerror("Validation Errors", "\n".join(errors))
            return False
        else:
            self.validation_label.config(
                text="✅ Configuration is valid", foreground="green")
            self.config = self.generate_config()
            return True

    def generate_config(self):
        config = {
            'directory': self.dir_entry.get().strip(),
            'min_file_size': self.min_size_entry.get().strip(),
            'output': {
                'format': self.format_var.get(),
                'encoder': self.encoder_var.get(),
                'preset': self.preset_var.get(),
                'quality': self._parse_quality()
            },
            'dependencies': {
                'handbrake': self.handbrake_entry.get().strip(),
                'ffprobe': self.ffprobe_entry.get().strip(),
                'ffmpeg': self.ffmpeg_entry.get().strip()
            },
            'remove_original_files': self.remove_original_var.get(),
            'dry_run': self.dry_run_var.get(),
            'loop': False  # GUI mode doesn't use loop
        }
        return config

    def _parse_quality(self):
        """Parse quality value from entry, returning default if invalid."""
        try:
            return int(self.quality_entry.get().strip())
        except (ValueError, AttributeError):
            logger.warning("Invalid quality value, using default 24")
            return 24

    def on_tab_changed(self, event):
        """Handle tab switch event - regenerate config from UI."""
        try:
            self.config = self.generate_config()
        except Exception as e:
            logger.error(f"Failed to generate config on tab switch: {repr(e)}")

    def save_config(self):
        """Save the current configuration to file."""
        # Validate silently first
        is_valid = self.validate_config()
        if not is_valid:
            return

        config = self.generate_config()

        # Ask user where to save the file
        file_path = filedialog.asksaveasfilename(
            defaultextension=".yaml",
            filetypes=[("YAML files", "*.yaml"), ("All files", "*.*")],
            initialfile="config.yaml",
            title="Save Configuration"
        )

        if not file_path:
            return  # User cancelled

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)

            self.config = config
            self.config_file_path = Path(file_path)
            messagebox.showinfo(
                "Success", f"Configuration saved to {file_path}")
        except Exception as e:
            logger.error(f"Failed to save configuration: {repr(e)}")
            messagebox.showerror(
                "Save Error", f"Failed to save configuration:\n{repr(e)}")

    def load_config_file(self):
        """Load configuration from a file."""
        file_path = filedialog.askopenfilename(
            title="Select Configuration File",
            filetypes=[("YAML files", "*.yaml *.yml"), ("All files", "*.*")],
            initialdir="."
        )

        if not file_path:
            return

        try:
            config, validation_errors = configuration_manager.load_config(file_path)
            if len(validation_errors) > 0:
                logger.error(f"Failed to load configuration: {validation_errors}")
                messagebox.showerror(
                    "Load Error", f"Failed to load configuration:\n{validation_errors}")
            else:
                self.config = config
                self.config_file_path = Path(file_path)
                self.update_config_ui()
                messagebox.showinfo(
                    "Success", f"Configuration loaded from {file_path}")
        except Exception as e:
            logger.error(f"Failed to load configuration: {repr(e)}")
            messagebox.showerror(
                "Load Error", f"Failed to load configuration:\n{repr(e)}")

    def update_config_ui(self):
        """Update UI fields with current config."""
        try:
            self.dir_entry.delete(0, tk.END)
            # Default to current working directory if no directory in config
            default_dir = self.config.get('directory') or os.getcwd()
            self.dir_entry.insert(0, default_dir)

            self.min_size_entry.delete(0, tk.END)
            self.min_size_entry.insert(
                0, str(self.config.get('min_file_size') or '1GB'))

            output_config = self.config.get('output', {})
            self.format_var.set(output_config.get('format', 'mkv'))
            self.encoder_var.set(output_config.get('encoder', 'x265_10bit'))
            self.preset_var.set(output_config.get('preset', 'medium'))

            self.quality_entry.delete(0, tk.END)
            self.quality_entry.insert(
                0, str(output_config.get('quality') or 24))

            dependency_config = self.config.get('dependencies', {})
            self.handbrake_entry.delete(0, tk.END)
            self.handbrake_entry.insert(
                0, dependency_config.get('handbrake') or 'HandBrakeCLI')

            self.ffprobe_entry.delete(0, tk.END)
            self.ffprobe_entry.insert(
                0, dependency_config.get('ffprobe') or 'ffprobe')

            self.ffmpeg_entry.delete(0, tk.END)
            self.ffmpeg_entry.insert(
                0, dependency_config.get('ffmpeg') or 'ffmpeg')

            self.remove_original_var.set(
                self.config.get('remove_original_files', False))
            self.dry_run_var.set(self.config.get('dry_run', False))
        except Exception as e:
            logger.error(f"Failed to update UI with config: {repr(e)}")
            messagebox.showerror(
                "UI Update Error", f"Failed to update interface:\n{repr(e)}")

    def scan_files(self):
        """Scan directory for eligible files."""
        # Validate without showing popup
        errors = []

        # Validate directory
        directory = self.dir_entry.get().strip()
        if not directory:
            errors.append("Directory is required")
        elif not os.path.isdir(directory):
            errors.append(f"Directory does not exist: {directory}")

        # Validate min file size
        try:
            min_size = self.min_size_entry.get().strip()
            configuration_manager.parse_file_size(min_size)
        except ValueError as e:
            errors.append(f"Invalid min file size: {e}")

        if errors:
            self.validation_label.config(
                text="❌ Validation failed", foreground="red")
            messagebox.showerror("Validation Errors", "\n".join(errors))
            return

        self.scan_button.config(state='disabled')
        self.validation_label.config(
            text="Scanning directory...", foreground="blue")

        def scan_thread():
            try:
                directory = self.dir_entry.get().strip()
                min_size = configuration_manager.parse_file_size(
                    self.min_size_entry.get().strip())
                dependency_config = self.config.get('dependencies', {})

                files = convert_videos.find_eligible_files(
                    directory, min_size, dependency_config)

                self.progress_queue.put(('scan_complete', files))
            except Exception as e:
                logger.error(f"Scan error: {repr(e)}")
                self.progress_queue.put(('scan_error', repr(e)))

        threading.Thread(target=scan_thread, daemon=True).start()

    def convert_file_with_progress(self, input_path, dry_run, preserve_original, output_config, dependency_config):
        """Convert a file while reporting progress to the GUI.

        This now delegates to convert_videos.convert_file with progress callbacks.
        """
        from pathlib import Path

        input_path = Path(input_path)

        if dry_run:
            logger.info(f"[Dry Run] Would convert: {input_path}")
            return True

        # Create progress callback that communicates with GUI
        def progress_callback(percentage):
            self.progress_queue.put(('progress', percentage))

        # Create cancellation check
        def cancellation_check():
            return self.stop_requested

        try:
            # Use convert_videos.convert_file with progress callbacks
            success = convert_videos.convert_file(
                input_path=input_path,
                dry_run=dry_run,
                preserve_original=preserve_original,
                output_config=output_config,
                dependency_config=dependency_config,
                progress_callback=progress_callback,
                cancellation_check=cancellation_check
            )
            return success

        except Exception as e:
            # Check if this was a cancellation
            if self.stop_requested or "cancelled" in str(e).lower():
                logger.info(f"Conversion cancelled for {input_path}")
                return False
            logger.error(f"Conversion error: {repr(e)}")
            return False

    def start_processing(self):
        """Start processing the file queue."""
        if not self.file_queue:
            messagebox.showwarning("No Files", "No files in queue to process")
            return

        self.is_running = True
        self.stop_requested = False
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.scan_button.config(state='disabled')

        # Get config
        try:
            output_config = {
                'format': self.format_var.get(),
                'encoder': self.encoder_var.get(),
                'preset': self.preset_var.get(),
                'quality': int(self.quality_entry.get().strip())
            }
            remove_original = self.remove_original_var.get()
            # Convert to preserve_original for backward compatibility with convert_file function
            preserve_original = not remove_original
            dry_run = self.dry_run_var.get()
            dependency_config = {
                'handbrake': self.handbrake_entry.get().strip(),
                'ffprobe': self.ffprobe_entry.get().strip()
            }
        except Exception as e:
            logger.error(f"Configuration error: {repr(e)}")
            messagebox.showerror("Configuration Error",
                                 f"Invalid configuration:\n{repr(e)}")
            self.reset_ui_state()
            return

        def processing_thread():
            # Create a copy to avoid modification issues
            for file_path in list(self.file_queue):
                if self.stop_requested:
                    self.progress_queue.put(('stopped', None))
                    break

                self.progress_queue.put(('start_file', str(file_path)))

                try:
                    # Get original size
                    original_size = file_path.stat().st_size

                    # Convert file with progress tracking
                    success = self.convert_file_with_progress(
                        file_path,
                        dry_run=dry_run,
                        preserve_original=preserve_original,
                        output_config=output_config,
                        dependency_config=dependency_config
                    )

                    # Get new size (if not dry run and successful)
                    new_size = 0
                    if success and not dry_run:
                        # Find the newly created file with .converted naming
                        base_name = f"{file_path.stem}.converted"
                        output_format = output_config['format']
                        output_path = file_path.with_name(
                            f"{base_name}.{output_format}")
                        if not output_path.exists():
                            # Try with counter
                            counter = 1
                            while counter < MAX_OUTPUT_FILE_ATTEMPTS:
                                output_path = file_path.with_name(
                                    f"{base_name}.{counter}.{output_format}")
                                if output_path.exists():
                                    break
                                counter += 1
                        if output_path.exists():
                            new_size = output_path.stat().st_size
                        else:
                            logger.warning(
                                "Converted file for '%s' not found after %d attempts using base name '%s' "
                                "and format '%s'.",
                                file_path,
                                MAX_OUTPUT_FILE_ATTEMPTS,
                                base_name,
                                output_format,
                            )

                    result = ConversionResult(
                        file_path=str(file_path),
                        success=success,
                        error_message=None if success else "Conversion failed",
                        original_size=original_size,
                        new_size=new_size
                    )

                except Exception as e:
                    logger.error(f"File conversion error: {repr(e)}")
                    result = ConversionResult(
                        file_path=str(file_path),
                        success=False,
                        error_message=repr(e),
                        original_size=file_path.stat().st_size if file_path.exists() else 0,
                        new_size=0
                    )

                self.progress_queue.put(('file_complete', result))

            if not self.stop_requested:
                self.progress_queue.put(('all_complete', None))

        self.conversion_thread = threading.Thread(
            target=processing_thread, daemon=True)
        self.conversion_thread.start()

    def stop_processing(self):
        """Stop the current processing."""
        self.stop_requested = True
        self.stop_button.config(state='disabled')
        logger.info("Stop requested by user")

    def reset_ui_state(self):
        """Reset UI to idle state."""
        self.is_running = False
        self.start_button.config(
            state='normal' if self.file_queue else 'disabled')
        self.stop_button.config(state='disabled')
        self.scan_button.config(state='normal')
        self.progress_bar.stop()
        self.current_file = None
        self.current_file_label.config(text="No file being processed")
        self.progress_label.config(text="")

    def update_progress(self):
        """Process messages from the conversion thread."""
        try:
            while True:
                msg_type, data = self.progress_queue.get_nowait()

                if msg_type == 'scan_complete':
                    self.file_queue = data
                    self.queue_listbox.delete(0, tk.END)
                    for f in self.file_queue:
                        self.queue_listbox.insert(tk.END, str(f))

                    self.validation_label.config(
                        text=f"✅ Found {len(self.file_queue)} files to convert",
                        foreground="green"
                    )
                    self.start_button.config(
                        state='normal' if self.file_queue else 'disabled')
                    self.scan_button.config(state='normal')

                elif msg_type == 'scan_error':
                    self.validation_label.config(
                        text=f"❌ Scan error: {data}", foreground="red")
                    self.scan_button.config(state='normal')
                    messagebox.showerror(
                        "Scan Error", f"Failed to scan directory: {data}")

                elif msg_type == 'start_file':
                    self.current_file = data
                    self.current_file_label.config(text=f"Processing: {data}")
                    self.progress_label.config(text="Converting... 0%")
                    # Stop indeterminate mode and reset to 0
                    self.progress_bar.stop()
                    self.progress_bar['value'] = 0

                elif msg_type == 'progress':
                    # Update progress bar with actual percentage
                    percentage = data
                    self.progress_bar['value'] = percentage
                    self.progress_label.config(
                        text=f"Converting... {percentage:.1f}%")

                elif msg_type == 'file_complete':
                    result = data
                    self.conversion_results.append(result)

                    # Remove from queue
                    if self.file_queue:
                        self.file_queue.pop(0)
                        self.queue_listbox.delete(0)

                    # Add to results
                    self.add_result_to_tree(result)

                elif msg_type == 'all_complete':
                    self.reset_ui_state()
                    messagebox.showinfo(
                        "Complete", "All files have been processed!")
                    self.notebook.select(self.results_tab)

                elif msg_type == 'stopped':
                    self.reset_ui_state()
                    messagebox.showinfo(
                        "Stopped", "Processing stopped by user")

                elif msg_type == 'download_status':
                    self.validation_label.config(text=data, foreground="blue")

                elif msg_type == 'download_complete':
                    handbrake_path, ffprobe_path, ffmpeg_path = data
                    # Update the entry fields
                    self.handbrake_entry.delete(0, tk.END)
                    self.handbrake_entry.insert(0, handbrake_path)
                    self.ffprobe_entry.delete(0, tk.END)
                    self.ffprobe_entry.insert(0, ffprobe_path)
                    self.ffmpeg_entry.delete(0, tk.END)
                    self.ffmpeg_entry.insert(0, ffmpeg_path)
                    self.validation_label.config(
                        text="✅ Dependencies downloaded successfully!", foreground="green")
                    messagebox.showinfo("Success",
                                        f"Dependencies downloaded successfully!\n\n"
                                        f"HandBrakeCLI: {handbrake_path}\n"
                                        f"ffprobe: {ffprobe_path}\n"
                                        f"ffmpeg: {ffmpeg_path}\n\n"
                                        f"The paths have been updated in the configuration.")

                elif msg_type == 'download_error':
                    self.validation_label.config(
                        text="❌ Download failed", foreground="red")
                    messagebox.showerror(
                        "Download Error", f"Failed to download dependencies:\n\n{data}")

        except queue.Empty:
            pass

        # Schedule next update
        self.root.after(PROGRESS_UPDATE_INTERVAL_MS, self.update_progress)

    def update_duplicate_progress(self):
        """Process messages from the duplicate detection thread."""
        try:
            while True:
                msg_type, data = self.duplicate_progress_queue.get_nowait()

                if msg_type == 'dup_status':
                    self.dup_status_label.config(text=data, foreground="blue")

                elif msg_type == 'dup_complete':
                    duplicate_groups = data
                    self.duplicate_results = duplicate_groups
                    self.duplicates_tree.delete(
                        *self.duplicates_tree.get_children())

                    for i, group in enumerate(duplicate_groups):
                        # Show comparison thumbnail path for group if available
                        group_thumb = group.comparison_thumbnail if group.comparison_thumbnail else ''
                        group_id = self.duplicates_tree.insert('', 'end',
                                                               text=f'Group {i+1}',
                                                               values=(group.hamming_distance, len(group.files), group_thumb))

                        # Add files as children with their individual thumbnail paths
                        for file_path in group.files:
                            file_name = str(Path(file_path).name)
                            thumbnail_path = group.file_thumbnails.get(
                                str(file_path), '')
                            self.duplicates_tree.insert(group_id, 'end',
                                                        text=file_name,
                                                        values=('', '', thumbnail_path))

                    self.dup_progress_bar.stop()
                    self.dup_status_label.config(
                        text=f"✅ Found {len(duplicate_groups)} duplicate groups",
                        foreground="green"
                    )
                    self.dup_summary_label.config(
                        text=f"Total Groups: {len(duplicate_groups)} | "
                        f"Total Duplicate Files: {sum(len(g.files) for g in duplicate_groups)}"
                    )
                    self.duplicate_scan_running = False
                    self.scan_duplicates_button.config(state='normal')

                    if duplicate_groups:
                        messagebox.showinfo("Scan Complete",
                                            f"Found {len(duplicate_groups)} groups of duplicate videos")
                    else:
                        messagebox.showinfo(
                            "Scan Complete", "No duplicates found")

                elif msg_type == 'dup_error':
                    self.dup_progress_bar.stop()
                    self.dup_status_label.config(
                        text=f"❌ Error: {data}", foreground="red")
                    self.duplicate_scan_running = False
                    self.scan_duplicates_button.config(state='normal')
                    messagebox.showerror(
                        "Scan Error", f"Failed to scan for duplicates:\n\n{data}")

        except queue.Empty:
            pass

        # Schedule next update
        self.root.after(PROGRESS_UPDATE_INTERVAL_MS,
                        self.update_duplicate_progress)

    def add_result_to_tree(self, result):
        """Add a conversion result to the results tree."""
        status = "✅ Success" if result.success else "❌ Failed"
        original_size_str = self.format_size(result.original_size)
        new_size_str = self.format_size(
            result.new_size) if result.success else "N/A"

        if result.success and result.space_saved > 0:
            space_saved_str = f"{self.format_size(result.space_saved)} ({result.space_saved_percent:.1f}%)"
        else:
            space_saved_str = "N/A"

        error_str = result.error_message if result.error_message else ""

        self.results_tree.insert('', 'end', text=Path(result.file_path).name,
                                 values=(status, original_size_str, new_size_str, space_saved_str, error_str))

        # Update summary
        self.update_summary()

    def update_summary(self):
        """Update the results summary."""
        total = len(self.conversion_results)
        successful = sum(1 for r in self.conversion_results if r.success)
        failed = total - successful
        total_saved = sum(
            r.space_saved for r in self.conversion_results if r.success)

        summary = f"Total: {total} | Success: {successful} | Failed: {failed} | Space Saved: {self.format_size(total_saved)}"
        self.summary_label.config(text=summary)

    def clear_results(self):
        """Clear the results list."""
        try:
            if messagebox.askyesno("Clear Results", "Are you sure you want to clear all results?"):
                self.conversion_results.clear()
                self.results_tree.delete(*self.results_tree.get_children())
                self.summary_label.config(text="No conversions completed yet")
        except Exception as e:
            logger.error(f"Clear results error: {repr(e)}")
            messagebox.showerror(
                "Clear Error", f"Failed to clear results:\n{repr(e)}")

    def scan_for_duplicates(self):
        """Scan directory for duplicate videos."""
        directory = self.dup_dir_entry.get().strip()
        if not directory or not os.path.isdir(directory):
            messagebox.showerror("Invalid Directory",
                                 "Please select a valid directory to scan")
            return

        try:
            max_distance = int(self.hamming_distance_entry.get().strip())
            if max_distance < 0:
                raise ValueError("Distance must be non-negative")
        except ValueError as e:
            messagebox.showerror("Invalid Distance",
                                 f"Please enter a valid hamming distance: {e}")
            return

        self.duplicate_scan_running = True
        self.scan_duplicates_button.config(state='disabled')
        self.dup_status_label.config(
            text="Scanning for videos...", foreground="blue")
        self.dup_progress_bar.start()

        def scan_thread():
            try:
                # Get dependency paths
                dependency_config = self.config.get('dependencies', {})
                ffprobe_path = dependencies_utils.find_dependency_path(
                    'ffprobe', dependency_config.get('ffprobe'))
                if not ffprobe_path:
                    ffprobe_path = 'ffprobe'

                ffmpeg_path = dependencies_utils.find_dependency_path(
                    'ffmpeg', dependency_config.get('ffmpeg'))
                if not ffmpeg_path:
                    ffmpeg_path = 'ffmpeg'

                # Progress callback
                def progress_callback(message):
                    self.duplicate_progress_queue.put(('dup_status', message))

                # Run duplicate detection
                duplicate_groups = duplicate_detector.scan_for_duplicates(
                    directory=directory,
                    max_distance=max_distance,
                    ffmpeg_path=ffmpeg_path,
                    ffprobe_path=ffprobe_path,
                    progress_callback=progress_callback
                )

                self.duplicate_progress_queue.put(
                    ('dup_complete', duplicate_groups))

            except Exception as e:
                logger.error(f"Duplicate scan error: {repr(e)}")
                self.duplicate_progress_queue.put(('dup_error', repr(e)))

        threading.Thread(target=scan_thread, daemon=True).start()

    def clear_duplicate_results(self):
        """Clear duplicate detection results."""
        try:
            if messagebox.askyesno("Clear Results", "Are you sure you want to clear duplicate results?"):
                # Track temp directories to clean up
                temp_dirs = set()

                # Clean up thumbnail files
                for result in self.duplicate_results:
                    # Clean up comparison thumbnail
                    if result.comparison_thumbnail and os.path.exists(result.comparison_thumbnail):
                        try:
                            os.unlink(result.comparison_thumbnail)
                        except Exception:
                            # Best-effort cleanup; file may already be deleted
                            pass

                    # Clean up individual file thumbnails
                    for file_path, thumb_path in result.file_thumbnails.items():
                        if thumb_path and os.path.exists(thumb_path):
                            try:
                                os.unlink(thumb_path)
                                # Track the parent directory for cleanup
                                temp_dirs.add(Path(thumb_path).parent)
                            except Exception:
                                # Best-effort cleanup; file may already be deleted
                                pass

                # Try to remove temp directories after all files are deleted
                for temp_dir in temp_dirs:
                    try:
                        if temp_dir.exists() and temp_dir.name.startswith('video_dup_'):
                            temp_dir.rmdir()
                    except Exception:
                        # Directory may not be empty or may be in use
                        pass

                # Clear the thumbnail image cache
                self.thumbnail_images.clear()

                self.duplicate_results.clear()
                self.duplicates_tree.delete(
                    *self.duplicates_tree.get_children())
                self.dup_summary_label.config(text="No duplicates found yet")
        except Exception as e:
            logger.error(f"Clear duplicate results error: {repr(e)}")
            messagebox.showerror(
                "Clear Error", f"Failed to clear results:\n{repr(e)}")

    def show_thumbnail_tooltip(self, event):
        """Show thumbnail image tooltip on mouse hover."""
        try:
            # Get the item and column under the mouse
            item = self.duplicates_tree.identify_row(event.y)
            column = self.duplicates_tree.identify_column(event.x)

            if not item or column != '#3':  # Only show for Thumbnail column
                self.hide_thumbnail_tooltip(None)
                return

            # Get the thumbnail path from the cell
            values = self.duplicates_tree.item(item, 'values')
            if not values or len(values) < 3 or not values[2]:
                self.hide_thumbnail_tooltip(None)
                return

            thumbnail_path = values[2]

            # Check if file exists
            if not os.path.exists(thumbnail_path):
                self.hide_thumbnail_tooltip(None)
                return

            # If tooltip already showing this image, don't recreate
            if self.thumbnail_tooltip and hasattr(self.thumbnail_tooltip, 'current_path'):
                if self.thumbnail_tooltip.current_path == thumbnail_path:
                    return

            # Hide existing tooltip
            self.hide_thumbnail_tooltip(None)

            # Create new tooltip window
            self.thumbnail_tooltip = tk.Toplevel(self.root)
            self.thumbnail_tooltip.wm_overrideredirect(True)
            self.thumbnail_tooltip.current_path = thumbnail_path

            # Load and display image
            img = Image.open(thumbnail_path)
            # Resize if too large
            max_size = (400, 300)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)

            # Convert to PhotoImage and keep reference
            photo = ImageTk.PhotoImage(img)
            self.thumbnail_images[thumbnail_path] = photo

            # Create label with image
            label = tk.Label(self.thumbnail_tooltip, image=photo,
                             borderwidth=2, relief='solid')
            label.pack()

            # Position tooltip near mouse
            x = event.x_root + 10
            y = event.y_root + 10
            self.thumbnail_tooltip.wm_geometry(f"+{x}+{y}")

        except Exception as e:
            logger.error(f"Error showing thumbnail tooltip: {repr(e)}")
            self.hide_thumbnail_tooltip(None)

    def hide_thumbnail_tooltip(self, event):
        """Hide thumbnail tooltip."""
        if self.thumbnail_tooltip:
            try:
                self.thumbnail_tooltip.destroy()
            except Exception:
                # Tooltip may have already been destroyed
                pass
            self.thumbnail_tooltip = None

    def show_file_context_menu(self, event):
        """Show context menu for file operations."""
        try:
            # Get the item under the cursor
            item = self.duplicates_tree.identify_row(event.y)
            if not item:
                return

            # Check if this is a file (child item, not group)
            parent = self.duplicates_tree.parent(item)
            if not parent:  # This is a group, not a file
                return

            # Get the file name from the item
            file_name = self.duplicates_tree.item(item, 'text')

            # Find the full file path from the duplicate group that this item belongs to
            file_path = None

            # Determine which duplicate group this parent item represents
            group_items = self.duplicates_tree.get_children('')
            try:
                group_index = group_items.index(parent)
            except ValueError:
                return

            # Ensure the index is within the range of available duplicate results
            if group_index < 0 or group_index >= len(self.duplicate_results):
                return

            group = self.duplicate_results[group_index]
            for fpath in group.files:
                if Path(fpath).name == file_name:
                    file_path = fpath
                    break

            if not file_path:
                return

            # Select the item
            self.duplicates_tree.selection_set(item)

            # Create context menu
            context_menu = tk.Menu(self.root, tearoff=0)
            context_menu.add_command(
                label="Play Video",
                command=lambda: self.play_video_file(file_path)
            )
            context_menu.add_command(
                label="Browse Folder",
                command=lambda: self.browse_to_file(file_path)
            )
            context_menu.add_separator()
            context_menu.add_command(
                label="Delete this file...",
                command=lambda: self.delete_duplicate_file(item, file_path)
            )

            # Show menu at cursor position
            context_menu.tk_popup(event.x_root, event.y_root)

        except Exception as e:
            logger.error(f"Error showing context menu: {repr(e)}")
        finally:
            # Clean up menu if it was created
            if "context_menu" in locals():
                try:
                    context_menu.grab_release()
                except Exception:
                    # Best-effort cleanup; grab may have already been released
                    pass

    def delete_duplicate_file(self, tree_item, file_path):
        """Delete a duplicate file after confirmation."""
        try:
            # Show confirmation dialog with full path
            result = messagebox.askyesno(
                "Delete File",
                f"Are you sure you want to delete this file?\n\n{file_path}\n\n"
                f"This action cannot be undone!",
                icon='warning'
            )

            if not result:
                return

            # Delete the file
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Deleted file: {file_path}")

                # Get parent reference BEFORE deleting the tree item
                parent = self.duplicates_tree.parent(tree_item)

                # Remove from tree view
                self.duplicates_tree.delete(tree_item)

                # Update the parent group's file count
                if parent:
                    # Get remaining children
                    children = self.duplicates_tree.get_children(parent)
                    file_count = len(children)

                    # Update parent values
                    values = self.duplicates_tree.item(parent, 'values')
                    if values:
                        self.duplicates_tree.item(parent, values=(
                            values[0], file_count, values[2]))

                    # If only one file left in group, it's not a duplicate anymore
                    if file_count <= 1:
                        self.duplicates_tree.delete(parent)

                # Update duplicate_results
                for group in self.duplicate_results[:]:
                    if str(file_path) in [str(f) for f in group.files]:
                        group.files = [
                            f for f in group.files if str(f) != str(file_path)]
                        # Remove thumbnail entry
                        if str(file_path) in group.file_thumbnails:
                            del group.file_thumbnails[str(file_path)]
                        # Remove group if only one file left
                        if len(group.files) <= 1:
                            self.duplicate_results.remove(group)
                        break

                # Update summary
                self.dup_summary_label.config(
                    text=f"Total Groups: {len(self.duplicate_results)} | "
                    f"Total Duplicate Files: {sum(len(g.files) for g in self.duplicate_results)}"
                )

                messagebox.showinfo(
                    "File Deleted", f"Successfully deleted:\n{file_path}")
            else:
                messagebox.showerror(
                    "File Not Found", f"File does not exist:\n{file_path}")

        except PermissionError:
            logger.error(f"Permission denied deleting file: {file_path}")
            messagebox.showerror("Permission Denied",
                                 f"Cannot delete file (permission denied):\n{file_path}")
        except Exception as e:
            logger.error(f"Error deleting file: {repr(e)}")
            messagebox.showerror("Delete Error",
                                 f"Failed to delete file:\n{file_path}\n\nError: {repr(e)}")

    def play_video_file(self, file_path):
        """Open video file with system default video player."""
        try:
            if not os.path.exists(file_path):
                messagebox.showerror(
                    "File Not Found", f"File does not exist:\n{file_path}")
                return

            system = platform.system()
            if system == 'Windows':
                # Windows: use os.startfile
                os.startfile(file_path)
            elif system == 'Darwin':
                # macOS: use open command
                subprocess.Popen(['open', file_path])
            else:
                # Linux: use xdg-open
                subprocess.Popen(['xdg-open', file_path])

            logger.info(f"Opened video file: {file_path}")

        except Exception as e:
            logger.error(f"Error opening video file: {repr(e)}")
            messagebox.showerror("Open Error",
                                 f"Failed to open video file:\n{file_path}\n\nError: {repr(e)}")

    def browse_to_file(self, file_path):
        """Open file explorer and highlight the file."""
        try:
            if not os.path.exists(file_path):
                messagebox.showerror(
                    "File Not Found", f"File does not exist:\n{file_path}")
                return

            system = platform.system()
            if system == 'Windows':
                # Windows: use explorer with /select parameter to highlight the file
                subprocess.Popen(
                    ['explorer', '/select,', os.path.normpath(file_path)])
            elif system == 'Darwin':
                # macOS: use open -R to reveal in Finder
                subprocess.Popen(['open', '-R', file_path])
            else:
                # Linux: open the parent directory (highlighting not universally supported)
                # Try to use file managers that support selection
                parent_dir = os.path.dirname(file_path)
                try:
                    # Try nautilus (GNOME) with --select
                    subprocess.Popen(['nautilus', '--select', file_path])
                except FileNotFoundError:
                    try:
                        # Try dolphin (KDE) with --select
                        subprocess.Popen(['dolphin', '--select', file_path])
                    except FileNotFoundError:
                        # Fallback: just open the directory
                        subprocess.Popen(['xdg-open', parent_dir])

            logger.info(f"Opened folder for file: {file_path}")

        except Exception as e:
            logger.error(f"Error opening folder: {repr(e)}")
            messagebox.showerror("Browse Error",
                                 f"Failed to open folder:\n{file_path}\n\nError: {repr(e)}")

    @staticmethod
    def format_size(size_bytes):
        """Format bytes as human-readable size."""
        if size_bytes == 0:
            return "0 B"

        units = ['B', 'KB', 'MB', 'GB', 'TB']
        unit_index = 0
        size = float(size_bytes)

        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1

        return f"{size:.2f} {units[unit_index]}"


def main():
    """Run the GUI application."""
    root = tk.Tk()
    VideoConverterGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
