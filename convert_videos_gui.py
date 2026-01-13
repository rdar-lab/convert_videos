#!/usr/bin/env python3
"""
GUI for convert_videos - Headed mode with configuration editor, queue management, and results display.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import queue
import yaml
from pathlib import Path
import logging
import os

import convert_videos


logger = logging.getLogger(__name__)

# Constants
PROGRESS_UPDATE_INTERVAL_MS = 100  # Milliseconds between progress updates
MAX_OUTPUT_FILE_ATTEMPTS = 100  # Maximum number of attempts to find unique output filename


class ConversionResult:
    """Represents the result of a video conversion."""
    def __init__(self, file_path, success, error_message=None, original_size=0, new_size=0):
        self.file_path = file_path
        self.success = success
        self.error_message = error_message
        self.original_size = original_size
        self.new_size = new_size
        self.space_saved = original_size - new_size if success else 0
        self.space_saved_percent = (self.space_saved / original_size * 100) if original_size > 0 else 0


class VideoConverterGUI:
    """Main GUI application for video converter."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Video Converter - H.265 (HEVC)")
        self.root.geometry("1000x700")
        
        # Configuration
        self.config = convert_videos.load_config()
        self.config_file_path = Path('config.yaml')
        
        # Queue and results
        self.file_queue = []
        self.current_file = None
        self.conversion_results = []
        self.is_running = False
        self.stop_requested = False
        
        # Thread communication
        self.progress_queue = queue.Queue()
        self.conversion_thread = None
        
        # Create UI
        self.create_ui()
        
        # Start progress update loop
        self.update_progress()
        
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
        
    def create_config_tab(self):
        """Create the configuration editor tab."""
        # Main container with scrollbar
        canvas = tk.Canvas(self.config_tab)
        scrollbar = ttk.Scrollbar(self.config_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Directory selection
        dir_frame = ttk.LabelFrame(scrollable_frame, text="Directory Settings", padding=10)
        dir_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(dir_frame, text="Target Directory:").grid(row=0, column=0, sticky='w', pady=5)
        self.dir_entry = ttk.Entry(dir_frame, width=50)
        self.dir_entry.grid(row=0, column=1, padx=5, pady=5)
        # Default to current working directory if no directory in config
        default_dir = self.config.get('directory') or os.getcwd()
        self.dir_entry.insert(0, default_dir)
        ttk.Button(dir_frame, text="Browse...", command=self.browse_directory).grid(row=0, column=2, pady=5)
        
        ttk.Label(dir_frame, text="Min File Size:").grid(row=1, column=0, sticky='w', pady=5)
        self.min_size_entry = ttk.Entry(dir_frame, width=20)
        self.min_size_entry.grid(row=1, column=1, sticky='w', padx=5, pady=5)
        self.min_size_entry.insert(0, str(self.config.get('min_file_size') or '1GB'))
        ttk.Label(dir_frame, text="(e.g., 1GB, 500MB)").grid(row=1, column=2, sticky='w')
        
        # Output settings
        output_frame = ttk.LabelFrame(scrollable_frame, text="Output Settings", padding=10)
        output_frame.pack(fill='x', padx=10, pady=5)
        
        output_config = self.config.get('output', {})
        
        ttk.Label(output_frame, text="Format:").grid(row=0, column=0, sticky='w', pady=5)
        self.format_var = tk.StringVar(value=output_config.get('format', 'mkv'))
        format_combo = ttk.Combobox(output_frame, textvariable=self.format_var, 
                                    values=list(convert_videos.SUPPORTED_FORMATS), state='readonly', width=18)
        format_combo.grid(row=0, column=1, sticky='w', padx=5, pady=5)
        
        ttk.Label(output_frame, text="Encoder:").grid(row=1, column=0, sticky='w', pady=5)
        self.encoder_var = tk.StringVar(value=output_config.get('encoder', 'x265_10bit'))
        encoder_combo = ttk.Combobox(output_frame, textvariable=self.encoder_var,
                                     values=list(convert_videos.SUPPORTED_ENCODERS), state='readonly', width=18)
        encoder_combo.grid(row=1, column=1, sticky='w', padx=5, pady=5)
        
        ttk.Label(output_frame, text="Preset:").grid(row=2, column=0, sticky='w', pady=5)
        self.preset_var = tk.StringVar(value=output_config.get('preset', 'medium'))
        preset_combo = ttk.Combobox(output_frame, textvariable=self.preset_var,
                                    values=list(convert_videos.SUPPORTED_PRESETS), state='readonly', width=18)
        preset_combo.grid(row=2, column=1, sticky='w', padx=5, pady=5)
        
        ttk.Label(output_frame, text="Quality:").grid(row=3, column=0, sticky='w', pady=5)
        self.quality_entry = ttk.Entry(output_frame, width=20)
        self.quality_entry.grid(row=3, column=1, sticky='w', padx=5, pady=5)
        self.quality_entry.insert(0, str(output_config.get('quality') or 24))
        ttk.Label(output_frame, text="(0-51, lower=better)").grid(row=3, column=2, sticky='w')
        
        # Dependencies settings
        deps_frame = ttk.LabelFrame(scrollable_frame, text="Dependencies (Optional)", padding=10)
        deps_frame.pack(fill='x', padx=10, pady=5)
        
        dependency_config = self.config.get('dependencies', {})
        
        ttk.Label(deps_frame, text="HandBrakeCLI:").grid(row=0, column=0, sticky='w', pady=5)
        self.handbrake_entry = ttk.Entry(deps_frame, width=40)
        self.handbrake_entry.grid(row=0, column=1, padx=5, pady=5)
        self.handbrake_entry.insert(0, dependency_config.get('handbrake') or 'HandBrakeCLI')
        ttk.Button(deps_frame, text="Browse...", command=self.browse_handbrake).grid(row=0, column=2, pady=5)
        
        ttk.Label(deps_frame, text="ffprobe:").grid(row=1, column=0, sticky='w', pady=5)
        self.ffprobe_entry = ttk.Entry(deps_frame, width=40)
        self.ffprobe_entry.grid(row=1, column=1, padx=5, pady=5)
        self.ffprobe_entry.insert(0, dependency_config.get('ffprobe') or 'ffprobe')
        ttk.Button(deps_frame, text="Browse...", command=self.browse_ffprobe).grid(row=1, column=2, pady=5)
        
        # Other options
        options_frame = ttk.LabelFrame(scrollable_frame, text="Other Options", padding=10)
        options_frame.pack(fill='x', padx=10, pady=5)
        
        self.remove_original_var = tk.BooleanVar(value=self.config.get('remove_original_files', False))
        ttk.Checkbutton(options_frame, text="Remove Original Files After Conversion", 
                       variable=self.remove_original_var).pack(anchor='w', pady=2)
        
        self.dry_run_var = tk.BooleanVar(value=self.config.get('dry_run', False))
        ttk.Checkbutton(options_frame, text="Dry Run (simulate only)",
                       variable=self.dry_run_var).pack(anchor='w', pady=2)
        
        # Validation status
        self.validation_frame = ttk.Frame(scrollable_frame)
        self.validation_frame.pack(fill='x', padx=10, pady=5)
        
        self.validation_label = ttk.Label(self.validation_frame, text="", foreground="blue")
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
        queue_frame = ttk.LabelFrame(self.processing_tab, text="File Queue", padding=10)
        queue_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Queue listbox with scrollbar
        queue_scroll = ttk.Scrollbar(queue_frame, orient='vertical')
        self.queue_listbox = tk.Listbox(queue_frame, yscrollcommand=queue_scroll.set, height=10)
        queue_scroll.config(command=self.queue_listbox.yview)
        self.queue_listbox.pack(side='left', fill='both', expand=True)
        queue_scroll.pack(side='right', fill='y')
        
        # Current file section
        current_frame = ttk.LabelFrame(self.processing_tab, text="Currently Processing", padding=10)
        current_frame.pack(fill='x', padx=10, pady=5)
        
        self.current_file_label = ttk.Label(current_frame, text="No file being processed", wraplength=900)
        self.current_file_label.pack(fill='x', pady=5)
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(current_frame, mode='indeterminate')
        self.progress_bar.pack(fill='x', pady=5)
        
        self.progress_label = ttk.Label(current_frame, text="")
        self.progress_label.pack(fill='x', pady=2)
        
        # Control buttons
        button_frame = ttk.Frame(self.processing_tab)
        button_frame.pack(fill='x', padx=10, pady=10)
        
        self.scan_button = ttk.Button(button_frame, text="Scan for Files", command=self.scan_files)
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
        columns = ('Status', 'Original Size', 'New Size', 'Space Saved', 'Error')
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
        self.summary_label = ttk.Label(self.results_tab, text="No conversions completed yet")
        self.summary_label.pack(fill='x', padx=10, pady=5)
        
        # Clear button
        ttk.Button(self.results_tab, text="Clear Results", 
                  command=self.clear_results).pack(pady=5)
        
    def browse_directory(self):
        """Open directory browser."""
        directory = filedialog.askdirectory(initialdir=self.dir_entry.get())
        if directory:
            self.dir_entry.delete(0, tk.END)
            self.dir_entry.insert(0, directory)
    
    def browse_handbrake(self):
        """Open file browser for HandBrakeCLI executable."""
        file_path = filedialog.askopenfilename(
            title="Select HandBrakeCLI executable",
            filetypes=[("Executable files", "*.exe"), ("All files", "*.*")]
        )
        if file_path:
            self.handbrake_entry.delete(0, tk.END)
            self.handbrake_entry.insert(0, file_path)
    
    def browse_ffprobe(self):
        """Open file browser for ffprobe executable."""
        file_path = filedialog.askopenfilename(
            title="Select ffprobe executable",
            filetypes=[("Executable files", "*.exe"), ("All files", "*.*")]
        )
        if file_path:
            self.ffprobe_entry.delete(0, tk.END)
            self.ffprobe_entry.insert(0, file_path)
            
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
            convert_videos.parse_file_size(min_size)
        except ValueError as e:
            errors.append(f"Invalid min file size: {e}")
        
        # Validate format
        if not convert_videos.validate_format(self.format_var.get()):
            errors.append(f"Invalid format: {self.format_var.get()}")
        
        # Validate encoder
        if not convert_videos.validate_encoder(self.encoder_var.get()):
            errors.append(f"Invalid encoder: {self.encoder_var.get()}")
        
        # Validate preset
        if not convert_videos.validate_preset(self.preset_var.get()):
            errors.append(f"Invalid preset: {self.preset_var.get()}")
        
        # Validate quality
        try:
            quality = int(self.quality_entry.get().strip())
            if not convert_videos.validate_quality(quality):
                errors.append(f"Quality must be between 0 and 51")
        except ValueError:
            errors.append("Quality must be an integer")
        
        # Validate dependencies
        handbrake_path = self.handbrake_entry.get().strip()
        ffprobe_path = self.ffprobe_entry.get().strip()
        
        if handbrake_path:
            if not convert_videos.check_single_dependency(handbrake_path):
                errors.append(f"HandBrakeCLI not found: {handbrake_path}")
        
        if ffprobe_path:
            if not convert_videos.check_single_dependency(ffprobe_path):
                errors.append(f"ffprobe not found: {ffprobe_path}")
        
        # Display results
        if errors:
            self.validation_label.config(text="❌ Validation failed", foreground="red")
            messagebox.showerror("Validation Errors", "\n".join(errors))
            return False
        else:
            self.validation_label.config(text="✅ Configuration is valid", foreground="green")
            return True
            
    def save_config(self):
        """Save the current configuration to file."""
        if not self.validate_config():
            return
        
        # Ask user where to save the file
        file_path = filedialog.asksaveasfilename(
            defaultextension=".yaml",
            filetypes=[("YAML files", "*.yaml"), ("All files", "*.*")],
            initialfile="config.yaml",
            title="Save Configuration"
        )
        
        if not file_path:
            return  # User cancelled
        
        config = {
            'directory': self.dir_entry.get().strip(),
            'min_file_size': self.min_size_entry.get().strip(),
            'output': {
                'format': self.format_var.get(),
                'encoder': self.encoder_var.get(),
                'preset': self.preset_var.get(),
                'quality': int(self.quality_entry.get().strip())
            },
            'dependencies': {
                'handbrake': self.handbrake_entry.get().strip(),
                'ffprobe': self.ffprobe_entry.get().strip()
            },
            'remove_original_files': self.remove_original_var.get(),
            'dry_run': self.dry_run_var.get(),
            'loop': False  # GUI mode doesn't use loop
        }
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            
            self.config = config
            self.config_file_path = Path(file_path)
            messagebox.showinfo("Success", f"Configuration saved to {file_path}")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save configuration: {e}")
            
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
            self.config = convert_videos.load_config(file_path)
            self.config_file_path = Path(file_path)
            self.update_config_ui()
            messagebox.showinfo("Success", f"Configuration loaded from {file_path}")
        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load configuration: {e}")
            
    def update_config_ui(self):
        """Update UI fields with current config."""
        self.dir_entry.delete(0, tk.END)
        # Default to current working directory if no directory in config
        default_dir = self.config.get('directory') or os.getcwd()
        self.dir_entry.insert(0, default_dir)
        
        self.min_size_entry.delete(0, tk.END)
        self.min_size_entry.insert(0, str(self.config.get('min_file_size') or '1GB'))
        
        output_config = self.config.get('output', {})
        self.format_var.set(output_config.get('format', 'mkv'))
        self.encoder_var.set(output_config.get('encoder', 'x265_10bit'))
        self.preset_var.set(output_config.get('preset', 'medium'))
        
        self.quality_entry.delete(0, tk.END)
        self.quality_entry.insert(0, str(output_config.get('quality') or 24))
        
        dependency_config = self.config.get('dependencies', {})
        self.handbrake_entry.delete(0, tk.END)
        self.handbrake_entry.insert(0, dependency_config.get('handbrake') or 'HandBrakeCLI')
        
        self.ffprobe_entry.delete(0, tk.END)
        self.ffprobe_entry.insert(0, dependency_config.get('ffprobe') or 'ffprobe')
        
        self.remove_original_var.set(self.config.get('remove_original_files', False))
        self.dry_run_var.set(self.config.get('dry_run', False))
        
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
            convert_videos.parse_file_size(min_size)
        except ValueError as e:
            errors.append(f"Invalid min file size: {e}")
        
        if errors:
            self.validation_label.config(text="❌ Validation failed", foreground="red")
            messagebox.showerror("Validation Errors", "\n".join(errors))
            return
        
        self.scan_button.config(state='disabled')
        self.validation_label.config(text="Scanning directory...", foreground="blue")
        
        def scan_thread():
            try:
                directory = self.dir_entry.get().strip()
                min_size = convert_videos.parse_file_size(self.min_size_entry.get().strip())
                dependency_config = self.config.get('dependencies', {})
                
                files = convert_videos.find_eligible_files(directory, min_size, dependency_config)
                
                self.progress_queue.put(('scan_complete', files))
            except Exception as e:
                self.progress_queue.put(('scan_error', str(e)))
        
        threading.Thread(target=scan_thread, daemon=True).start()
        
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
            messagebox.showerror("Configuration Error", f"Invalid configuration: {e}")
            self.reset_ui_state()
            return
        
        def processing_thread():
            for file_path in list(self.file_queue):  # Create a copy to avoid modification issues
                if self.stop_requested:
                    self.progress_queue.put(('stopped', None))
                    break
                
                self.progress_queue.put(('start_file', str(file_path)))
                
                try:
                    # Get original size
                    original_size = file_path.stat().st_size
                    
                    # Convert file
                    success = convert_videos.convert_file(
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
                        output_path = file_path.with_name(f"{base_name}.{output_format}")
                        if not output_path.exists():
                            # Try with counter
                            counter = 1
                            while counter < MAX_OUTPUT_FILE_ATTEMPTS:
                                output_path = file_path.with_name(f"{base_name}.{counter}.{output_format}")
                                if output_path.exists():
                                    break
                                counter += 1
                        if output_path.exists():
                            new_size = output_path.stat().st_size
                    
                    result = ConversionResult(
                        file_path=str(file_path),
                        success=success,
                        error_message=None if success else "Conversion failed",
                        original_size=original_size,
                        new_size=new_size
                    )
                    
                except Exception as e:
                    result = ConversionResult(
                        file_path=str(file_path),
                        success=False,
                        error_message=str(e),
                        original_size=file_path.stat().st_size if file_path.exists() else 0,
                        new_size=0
                    )
                
                self.progress_queue.put(('file_complete', result))
            
            if not self.stop_requested:
                self.progress_queue.put(('all_complete', None))
        
        self.conversion_thread = threading.Thread(target=processing_thread, daemon=True)
        self.conversion_thread.start()
        self.progress_bar.start()
        
    def stop_processing(self):
        """Stop the current processing."""
        self.stop_requested = True
        self.stop_button.config(state='disabled')
        
    def reset_ui_state(self):
        """Reset UI to idle state."""
        self.is_running = False
        self.start_button.config(state='normal' if self.file_queue else 'disabled')
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
                    self.start_button.config(state='normal' if self.file_queue else 'disabled')
                    self.scan_button.config(state='normal')
                    
                elif msg_type == 'scan_error':
                    self.validation_label.config(text=f"❌ Scan error: {data}", foreground="red")
                    self.scan_button.config(state='normal')
                    messagebox.showerror("Scan Error", f"Failed to scan directory: {data}")
                    
                elif msg_type == 'start_file':
                    self.current_file = data
                    self.current_file_label.config(text=f"Processing: {data}")
                    self.progress_label.config(text="Converting...")
                    
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
                    messagebox.showinfo("Complete", "All files have been processed!")
                    self.notebook.select(self.results_tab)
                    
                elif msg_type == 'stopped':
                    self.reset_ui_state()
                    messagebox.showinfo("Stopped", "Processing stopped by user")
                    
        except queue.Empty:
            pass
        
        # Schedule next update
        self.root.after(PROGRESS_UPDATE_INTERVAL_MS, self.update_progress)
        
    def add_result_to_tree(self, result):
        """Add a conversion result to the results tree."""
        status = "✅ Success" if result.success else "❌ Failed"
        original_size_str = self.format_size(result.original_size)
        new_size_str = self.format_size(result.new_size) if result.success else "N/A"
        
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
        total_saved = sum(r.space_saved for r in self.conversion_results if r.success)
        
        summary = f"Total: {total} | Success: {successful} | Failed: {failed} | Space Saved: {self.format_size(total_saved)}"
        self.summary_label.config(text=summary)
        
    def clear_results(self):
        """Clear the results list."""
        if messagebox.askyesno("Clear Results", "Are you sure you want to clear all results?"):
            self.conversion_results.clear()
            self.results_tree.delete(*self.results_tree.get_children())
            self.summary_label.config(text="No conversions completed yet")
            
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
    app = VideoConverterGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
