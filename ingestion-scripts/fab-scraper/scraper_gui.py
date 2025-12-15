#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI for Fab Metadata Scraper

Provides a graphical interface for scrape_fab_metadata.py with:
- Checkbox toggles for boolean flags
- Text inputs for parameters with values
- File/folder selection dialogs
- Real-time progress display
- Log output viewer
"""
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import subprocess
import threading
import sys
import json
from pathlib import Path
import queue


class ScraperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Fab Metadata Tools")
        self.root.geometry("900x750")
        
        # Queue for thread-safe log updates
        self.log_queue = queue.Queue()
        
        # Process tracking
        self.process = None
        self.is_running = False
        self.total_urls = 0
        self.scraped_count = 0
        
        # Script paths
        self.script_path = Path(__file__).parent / "scrape_fab_metadata.py"
        self.converter_path = Path(__file__).parent / "convert_html_to_markdown.py"
        
        self._setup_ui()
        self._start_log_updater()
    
    def _setup_ui(self):
        """Create the UI layout with tabs"""
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)
        
        # Create notebook (tabs)
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Create tab frames
        scraping_tab = ttk.Frame(notebook, padding="10")
        postprocess_tab = ttk.Frame(notebook, padding="10")
        
        notebook.add(scraping_tab, text="Scraping")
        notebook.add(postprocess_tab, text="Post-Processing")
        
        # Setup each tab
        self._setup_scraping_tab(scraping_tab)
        self._setup_postprocess_tab(postprocess_tab)
    
    def _setup_scraping_tab(self, parent):
        """Setup the scraping tab UI"""
        # Configure grid weights for the tab
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(4, weight=1)  # Log area gets extra space
        
        # === SECTION 1: Boolean Flags ===
        flags_frame = ttk.LabelFrame(parent, text="Options", padding="10")
        flags_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N), pady=(0, 10))
        
        # Boolean flag variables
        self.headless_var = tk.BooleanVar(value=False)
        self.clear_cache_var = tk.BooleanVar(value=False)
        self.test_scroll_var = tk.BooleanVar(value=False)
        self.skip_library_var = tk.BooleanVar(value=False)
        self.skip_captcha_var = tk.BooleanVar(value=False)
        self.force_rescrape_var = tk.BooleanVar(value=False)
        self.new_browser_var = tk.BooleanVar(value=False)
        self.block_heavy_var = tk.BooleanVar(value=True)
        self.reuse_browser_var = tk.BooleanVar(value=True)
        self.randomize_ua_var = tk.BooleanVar(value=True)
        self.auth_on_listings_var = tk.BooleanVar(value=False)
        self.captcha_retry_var = tk.BooleanVar(value=True)
        self.measure_bytes_var = tk.BooleanVar(value=False)
        
        # Create checkboxes in a grid
        ttk.Checkbutton(flags_frame, text="Headless mode", variable=self.headless_var).grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Checkbutton(flags_frame, text="Clear cache before scraping", variable=self.clear_cache_var).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Checkbutton(flags_frame, text="Test scroll only (no scraping)", variable=self.test_scroll_var).grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Checkbutton(flags_frame, text="Skip library scrape (use URL file)", variable=self.skip_library_var).grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Checkbutton(flags_frame, text="Skip pages with captchas", variable=self.skip_captcha_var).grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Checkbutton(flags_frame, text="Force rescrape all URLs", variable=self.force_rescrape_var).grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Checkbutton(flags_frame, text="New browser per page (avoid captchas)", variable=self.new_browser_var).grid(row=3, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
        ttk.Checkbutton(flags_frame, text="Reuse one browser per worker (new context per URL)", variable=self.reuse_browser_var).grid(row=4, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
        ttk.Checkbutton(flags_frame, text="Randomize UA + viewport per context", variable=self.randomize_ua_var).grid(row=5, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
        ttk.Checkbutton(flags_frame, text="Use auth on listing pages (normally off)", variable=self.auth_on_listings_var).grid(row=6, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
        ttk.Checkbutton(flags_frame, text="Captcha backoff + retry once", variable=self.captcha_retry_var).grid(row=7, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
        ttk.Checkbutton(flags_frame, text="Block heavy resources (images/media/fonts/analytics)", variable=self.block_heavy_var).grid(row=8, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
        ttk.Checkbutton(flags_frame, text="Measure bytes (write JSONL report)", variable=self.measure_bytes_var).grid(row=9, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
        
        # === SECTION 2: Parameters with Values ===
        params_frame = ttk.LabelFrame(parent, text="Parameters", padding="10")
        params_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N), pady=(0, 10))
        params_frame.columnconfigure(1, weight=1)
        
        # Parameter variables
        self.max_scrolls_var = tk.StringVar(value="50")
        self.scroll_step_var = tk.StringVar(value="1200")
        self.scroll_steps_var = tk.StringVar(value="8")
        self.parallel_var = tk.StringVar(value="1")
        self.out_file_var = tk.StringVar(value="fab_metadata.json")
        self.url_file_var = tk.StringVar(value="fab_library_urls.json")
        # cadence
        self.sleep_min_var = tk.StringVar(value="300")
        self.sleep_max_var = tk.StringVar(value="800")
        self.burst_size_var = tk.StringVar(value="5")
        self.burst_sleep_var = tk.StringVar(value="3000")
        # proxies
        self.proxy_file_var = tk.StringVar(value="")
        # measure bytes
        self.measure_report_var = tk.StringVar(value="fab_bandwidth_report.jsonl")
        
        # Create labeled inputs
        row = 0
        ttk.Label(params_frame, text="Max scrolls:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(params_frame, textvariable=self.max_scrolls_var, width=15).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        
        row += 1
        ttk.Label(params_frame, text="Scroll step (px):").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(params_frame, textvariable=self.scroll_step_var, width=15).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        
        row += 1
        ttk.Label(params_frame, text="Scroll steps per round:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(params_frame, textvariable=self.scroll_steps_var, width=15).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        
        row += 1
        ttk.Label(params_frame, text="Parallel workers (1=sequential):").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        parallel_frame = ttk.Frame(params_frame)
        parallel_frame.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(parallel_frame, textvariable=self.parallel_var, width=10).pack(side=tk.LEFT)
        ttk.Label(parallel_frame, text="(2-10 recommended)", foreground="gray").pack(side=tk.LEFT, padx=(5, 0))
        
        row += 1
        ttk.Label(params_frame, text="Output file:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        out_frame = ttk.Frame(params_frame)
        out_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        out_frame.columnconfigure(0, weight=1)
        ttk.Entry(out_frame, textvariable=self.out_file_var).grid(row=0, column=0, sticky=(tk.W, tk.E))
        ttk.Button(out_frame, text="Browse", command=self._browse_output_file, width=8).grid(row=0, column=1, padx=(5, 0))
        
        row += 1
        ttk.Label(params_frame, text="URL file (for --skip-library-scrape):").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        url_frame = ttk.Frame(params_frame)
        url_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        url_frame.columnconfigure(0, weight=1)
        ttk.Entry(url_frame, textvariable=self.url_file_var).grid(row=0, column=0, sticky=(tk.W, tk.E))
        ttk.Button(url_frame, text="Browse", command=self._browse_url_file, width=8).grid(row=0, column=1, padx=(5, 0))
        
        # Proxy list file
        row += 1
        ttk.Label(params_frame, text="Proxy list file (one URL per line):").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        proxy_frame = ttk.Frame(params_frame)
        proxy_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        proxy_frame.columnconfigure(0, weight=1)
        ttk.Entry(proxy_frame, textvariable=self.proxy_file_var).grid(row=0, column=0, sticky=(tk.W, tk.E))
        ttk.Button(proxy_frame, text="Browse", command=self._browse_proxy_file, width=8).grid(row=0, column=1, padx=(5, 0))
        
        # Measure report path
        row += 1
        ttk.Label(params_frame, text="Measure report (JSONL):").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        meas_frame = ttk.Frame(params_frame)
        meas_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        meas_frame.columnconfigure(0, weight=1)
        ttk.Entry(meas_frame, textvariable=self.measure_report_var).grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        # Cadence inputs
        row += 1
        ttk.Label(params_frame, text="Sleep min (ms):").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(params_frame, textvariable=self.sleep_min_var, width=10).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        row += 1
        ttk.Label(params_frame, text="Sleep max (ms):").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(params_frame, textvariable=self.sleep_max_var, width=10).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        row += 1
        ttk.Label(params_frame, text="Burst size:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(params_frame, textvariable=self.burst_size_var, width=10).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        row += 1
        ttk.Label(params_frame, text="Burst sleep (ms):").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(params_frame, textvariable=self.burst_sleep_var, width=10).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
        
        # === SECTION 3: Control Buttons ===
        control_frame = ttk.Frame(parent)
        control_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.start_button = ttk.Button(control_frame, text="Start Scraping", command=self._start_scraping)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(control_frame, text="Stop", command=self._stop_scraping, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        self.clear_log_button = ttk.Button(control_frame, text="Clear Log", command=self._clear_log)
        self.clear_log_button.pack(side=tk.LEFT, padx=5)
        
        # Status label
        self.status_label = ttk.Label(control_frame, text="Ready", foreground="green")
        self.status_label.pack(side=tk.LEFT, padx=20)
        
        # === SECTION 4: Progress Bar ===
        progress_frame = ttk.LabelFrame(parent, text="Progress", padding="10")
        progress_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        progress_frame.columnconfigure(0, weight=1)
        
        # Progress bar
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100, mode='determinate')
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Progress label
        self.progress_label = ttk.Label(progress_frame, text="0 / 0 pages scraped")
        self.progress_label.grid(row=1, column=0, sticky=tk.W, padx=5)
        
        # === SECTION 5: Log Output ===
        log_frame = ttk.LabelFrame(parent, text="Log Output", padding="10")
        log_frame.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # Scrolled text for log output
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=20, state=tk.DISABLED)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure text tags for colored output
        self.log_text.tag_config("error", foreground="red")
        self.log_text.tag_config("warning", foreground="orange")
        self.log_text.tag_config("success", foreground="green")
        self.log_text.tag_config("info", foreground="blue")
    
    def _setup_postprocess_tab(self, parent):
        """Setup the post-processing tab UI"""
        # Configure grid weights
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(3, weight=1)  # Log area gets extra space
        
        # === SECTION 1: File Selection ===
        file_frame = ttk.LabelFrame(parent, text="Input/Output Files", padding="10")
        file_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N), pady=(0, 10))
        file_frame.columnconfigure(1, weight=1)
        
        # Input file
        ttk.Label(file_frame, text="Input JSON file:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.convert_input_var = tk.StringVar(value="fab_metadata.json")
        input_frame = ttk.Frame(file_frame)
        input_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        input_frame.columnconfigure(0, weight=1)
        ttk.Entry(input_frame, textvariable=self.convert_input_var).grid(row=0, column=0, sticky=(tk.W, tk.E))
        ttk.Button(input_frame, text="Browse", command=self._browse_convert_input, width=8).grid(row=0, column=1, padx=(5, 0))
        
        # Output file
        ttk.Label(file_frame, text="Output JSON file:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.convert_output_var = tk.StringVar(value="")
        output_frame = ttk.Frame(file_frame)
        output_frame.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        output_frame.columnconfigure(0, weight=1)
        ttk.Entry(output_frame, textvariable=self.convert_output_var).grid(row=0, column=0, sticky=(tk.W, tk.E))
        ttk.Button(output_frame, text="Browse", command=self._browse_convert_output, width=8).grid(row=0, column=1, padx=(5, 0))
        ttk.Label(file_frame, text="(Leave empty to overwrite input file)", foreground="gray").grid(row=2, column=1, sticky=tk.W, padx=5)
        
        # === SECTION 2: Options ===
        options_frame = ttk.LabelFrame(parent, text="Conversion Options", padding="10")
        options_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N), pady=(0, 10))
        
        # Workers
        ttk.Label(options_frame, text="Parallel workers:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.convert_workers_var = tk.StringVar(value="4")
        worker_frame = ttk.Frame(options_frame)
        worker_frame.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(worker_frame, textvariable=self.convert_workers_var, width=10).pack(side=tk.LEFT)
        ttk.Label(worker_frame, text="(More workers = faster conversion)", foreground="gray").pack(side=tk.LEFT, padx=(5, 0))
        
        # === SECTION 3: Control Buttons ===
        control_frame = ttk.Frame(parent)
        control_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.convert_button = ttk.Button(control_frame, text="Convert to Markdown", command=self._start_conversion)
        self.convert_button.pack(side=tk.LEFT, padx=5)
        
        self.convert_clear_button = ttk.Button(control_frame, text="Clear Log", command=self._clear_convert_log)
        self.convert_clear_button.pack(side=tk.LEFT, padx=5)
        
        # Status label
        self.convert_status_label = ttk.Label(control_frame, text="Ready", foreground="green")
        self.convert_status_label.pack(side=tk.LEFT, padx=20)
        
        # === SECTION 4: Log Output ===
        log_frame = ttk.LabelFrame(parent, text="Conversion Log", padding="10")
        log_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # Scrolled text for log output
        self.convert_log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=20, state=tk.DISABLED)
        self.convert_log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure text tags for colored output
        self.convert_log_text.tag_config("error", foreground="red")
        self.convert_log_text.tag_config("warning", foreground="orange")
        self.convert_log_text.tag_config("success", foreground="green")
        self.convert_log_text.tag_config("info", foreground="blue")
    
    def _browse_output_file(self):
        """Open file dialog for output file selection"""
        filename = filedialog.asksaveasfilename(
            title="Select output file",
            initialdir=Path(__file__).parent,
            initialfile=self.out_file_var.get(),
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            self.out_file_var.set(Path(filename).name)  # Store just the filename
    
    def _browse_url_file(self):
        """Open file dialog for URL file selection"""
        filename = filedialog.askopenfilename(
            title="Select URL file",
            initialdir=Path(__file__).parent,
            initialfile=self.url_file_var.get(),
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            self.url_file_var.set(Path(filename).name)  # Store just the filename
    
    def _browse_proxy_file(self):
        filename = filedialog.askopenfilename(
            title="Select proxy list file",
            initialdir=Path(__file__).parent,
            filetypes=[("Text files", "*.txt *.list"), ("All files", "*.*")]
        )
        if filename:
            self.proxy_file_var.set(Path(filename).name)
    
    def _browse_convert_input(self):
        """Open file dialog for conversion input file"""
        filename = filedialog.askopenfilename(
            title="Select input JSON file",
            initialdir=Path(__file__).parent,
            initialfile=self.convert_input_var.get(),
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            self.convert_input_var.set(Path(filename).name)
    
    def _browse_convert_output(self):
        """Open file dialog for conversion output file"""
        filename = filedialog.asksaveasfilename(
            title="Select output JSON file",
            initialdir=Path(__file__).parent,
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            self.convert_output_var.set(Path(filename).name)
    
    def _build_command(self):
        """Build the command line arguments from GUI inputs"""
        cmd = [sys.executable, str(self.script_path)]
        
        # Add boolean flags
        if self.headless_var.get():
            cmd.append("--headless")
        if self.clear_cache_var.get():
            cmd.append("--clear-cache")
        if self.test_scroll_var.get():
            cmd.append("--test-scroll")
        if self.skip_library_var.get():
            cmd.append("--skip-library-scrape")
        if self.skip_captcha_var.get():
            cmd.append("--skip-on-captcha")
        if self.force_rescrape_var.get():
            cmd.append("--force-rescrape")
        if self.new_browser_var.get():
            cmd.append("--new-browser-per-page")
        if self.block_heavy_var.get():
            cmd.append("--block-heavy")
        if self.reuse_browser_var.get():
            cmd.append("--reuse-browser")
        if self.randomize_ua_var.get():
            cmd.append("--randomize-ua")
        if self.auth_on_listings_var.get():
            cmd.append("--auth-on-listings")
        if self.captcha_retry_var.get():
            cmd.append("--captcha-retry")
        # measurement
        if self.measure_bytes_var.get():
            cmd.append("--measure-bytes")
            if self.measure_report_var.get().strip():
                cmd.extend(["--measure-report", self.measure_report_var.get().strip()])
        # cadence
        cmd.extend(["--sleep-min-ms", self.sleep_min_var.get()])
        cmd.extend(["--sleep-max-ms", self.sleep_max_var.get()])
        cmd.extend(["--burst-size", self.burst_size_var.get()])
        cmd.extend(["--burst-sleep-ms", self.burst_sleep_var.get()])
        if self.proxy_file_var.get().strip():
            cmd.extend(["--proxy-list", self.proxy_file_var.get().strip()])
        
        # Add parameters with values
        cmd.extend(["--max-scrolls", self.max_scrolls_var.get()])
        cmd.extend(["--scroll-step", self.scroll_step_var.get()])
        cmd.extend(["--scroll-steps", self.scroll_steps_var.get()])
        cmd.extend(["--parallel", self.parallel_var.get()])
        cmd.extend(["--out", self.out_file_var.get()])
        cmd.extend(["--use-url-file", self.url_file_var.get()])
        
        # Always add progress-newlines for GUI parsing
        cmd.append("--progress-newlines")
        
        # Add progress file for reliable GUI monitoring
        self.progress_file_path = self.script_path.parent / ".scraper_progress.json"
        cmd.extend(["--progress-file", str(self.progress_file_path)])
        
        return cmd
    
    def _log(self, message, tag=None):
        """Add message to log queue (thread-safe)"""
        self.log_queue.put((message, tag))
    
    def _update_log_from_queue(self):
        """Process queued log messages and update UI"""
        try:
            while True:
                message, tag = self.log_queue.get_nowait()
                self.log_text.config(state=tk.NORMAL)
                if tag:
                    self.log_text.insert(tk.END, message + "\n", tag)
                else:
                    self.log_text.insert(tk.END, message + "\n")
                self.log_text.see(tk.END)
                self.log_text.config(state=tk.DISABLED)
        except queue.Empty:
            pass
        
        # Schedule next check
        self.root.after(100, self._update_log_from_queue)
    
    def _start_log_updater(self):
        """Start the periodic log updater"""
        self.root.after(100, self._update_log_from_queue)
    
    def _monitor_progress_file(self):
        """Monitor progress file for updates"""
        if self.is_running and hasattr(self, 'progress_file_path'):
            try:
                if self.progress_file_path.exists():
                    with open(self.progress_file_path, 'r') as f:
                        data = json.load(f)
                        current = data.get('current', 0)
                        total = data.get('total', 0)
                        if total > 0:
                            self.total_urls = total
                            self.scraped_count = current
                            self._update_progress(current, total)
            except:
                pass  # Silently ignore errors reading progress file
        
        # Schedule next check
        if self.is_running:
            self.root.after(200, self._monitor_progress_file)
    
    def _clear_log(self):
        """Clear the log text area"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def _clear_convert_log(self):
        """Clear the conversion log text area"""
        self.convert_log_text.config(state=tk.NORMAL)
        self.convert_log_text.delete(1.0, tk.END)
        self.convert_log_text.config(state=tk.DISABLED)
    
    def _start_scraping(self):
        """Start the scraping process in a background thread"""
        if self.is_running:
            return
        
        # Validate inputs
        try:
            int(self.max_scrolls_var.get())
            int(self.scroll_step_var.get())
            int(self.scroll_steps_var.get())
            parallel = int(self.parallel_var.get())
            if parallel < 1:
                raise ValueError("Parallel workers must be >= 1")
            if parallel > 20:
                self._log("Warning: More than 20 parallel workers may cause issues", "warning")
            # cadence
            int(self.sleep_min_var.get())
            int(self.sleep_max_var.get())
            int(self.burst_size_var.get())
            int(self.burst_sleep_var.get())
        except ValueError as e:
            self._log(f"Error: {e}", "error")
            return
        
        # Check if script exists
        if not self.script_path.exists():
            self._log(f"Error: Script not found at {self.script_path}", "error")
            return
        
        # Update UI state
        self.is_running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.status_label.config(text="Running...", foreground="orange")
        
        # Build command
        cmd = self._build_command()
        self._log("Starting scraper with command:", "info")
        self._log(" ".join(cmd), "info")
        self._log("-" * 80)
        
        # Start progress file monitoring
        self.root.after(200, self._monitor_progress_file)
        
        # Start scraping in background thread
        thread = threading.Thread(target=self._run_scraping, args=(cmd,), daemon=True)
        thread.start()
    
    def _run_scraping(self, cmd):
        """Run the scraping process and capture output"""
        import select
        
        try:
            # Reset progress
            self.total_urls = 0
            self.scraped_count = 0
            self._update_progress(0, 0)
            
            # Start process with stdout/stderr capture
            # Use preexec_fn to create new process group for clean shutdown
            import os
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                cwd=self.script_path.parent,
                universal_newlines=True,
                preexec_fn=os.setsid  # Create new process group
            )
            
            # Use select for non-blocking I/O on Unix-like systems
            import os
            import fcntl
            
            # Set stdout and stderr to non-blocking
            for stream in [self.process.stdout, self.process.stderr]:
                if stream:
                    fd = stream.fileno()
                    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
                    fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
            
            # Read output in real-time
            while True:
                # Check if process has finished
                if self.process.poll() is not None:
                    break
                
                # Use select to check for available data
                readable = []
                if self.process.stdout:
                    readable.append(self.process.stdout)
                if self.process.stderr:
                    readable.append(self.process.stderr)
                
                ready, _, _ = select.select(readable, [], [], 0.1)
                
                for stream in ready:
                    try:
                        line = stream.readline()
                        if line:
                            line = line.rstrip()
                            if stream == self.process.stderr:
                                self._process_stderr_line(line)
                            else:
                                self._process_stdout_line(line)
                    except:
                        pass
            
            # Read any remaining output
            if self.process.stdout:
                try:
                    remaining_out = self.process.stdout.read()
                    if remaining_out:
                        for line in remaining_out.splitlines():
                            self._process_stdout_line(line)
                except:
                    pass
            
            if self.process.stderr:
                try:
                    remaining_err = self.process.stderr.read()
                    if remaining_err:
                        for line in remaining_err.splitlines():
                            self._process_stderr_line(line)
                except:
                    pass
            
            # Check exit code
            exit_code = self.process.returncode
            if exit_code == 0:
                self._log("-" * 80)
                self._log("Scraping completed successfully!", "success")
                self._update_status("Completed", "green")
            else:
                self._log("-" * 80)
                self._log(f"Scraping failed with exit code {exit_code}", "error")
                self._update_status("Failed", "red")
        
        except Exception as e:
            self._log(f"Error running scraper: {e}", "error")
            self._update_status("Error", "red")
        
        finally:
            self._cleanup_process()
    
    def _stop_scraping(self):
        """Stop the running scraping process and all child processes"""
        if self.process and self.process.poll() is None:
            self._log("Stopping scraper and all worker processes...", "warning")
            
            # Get the process group ID
            import os
            import signal
            
            try:
                # First, try to terminate gracefully
                # Send SIGTERM to the entire process group
                pgid = os.getpgid(self.process.pid)
                self._log(f"Terminating process group {pgid}...", "info")
                os.killpg(pgid, signal.SIGTERM)
                
                # Wait a bit for graceful shutdown
                try:
                    self.process.wait(timeout=3)
                    self._log("Scraper terminated gracefully", "warning")
                except subprocess.TimeoutExpired:
                    # Force kill if still running
                    self._log("Force killing process group...", "error")
                    try:
                        os.killpg(pgid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass  # Process group already gone
                    
                    # Also kill the main process if still alive
                    try:
                        self.process.kill()
                    except:
                        pass
                    
                    self._log("Scraper force killed", "error")
                
            except (ProcessLookupError, PermissionError) as e:
                # Process already gone or we don't have permission
                self._log(f"Process cleanup: {e}", "warning")
                try:
                    self.process.kill()
                except:
                    pass
            
            # Also kill any orphaned chromium processes
            try:
                import subprocess as sp
                sp.run(["pkill", "-9", "chromium"], 
                       capture_output=True, 
                       timeout=2)
                self._log("Cleaned up browser processes", "info")
            except:
                pass
            
            self._update_status("Stopped", "orange")
        
        self._cleanup_process()
    
    def _cleanup_process(self):
        """Clean up after process finishes"""
        self.is_running = False
        self.process = None
        
        # Clean up progress file
        if hasattr(self, 'progress_file_path'):
            try:
                if self.progress_file_path.exists():
                    self.progress_file_path.unlink()
            except:
                pass
        
        self.root.after(0, lambda: self.start_button.config(state=tk.NORMAL))
        self.root.after(0, lambda: self.stop_button.config(state=tk.DISABLED))
    
    def _update_status(self, text, color):
        """Update status label (thread-safe)"""
        self.root.after(0, lambda: self.status_label.config(text=text, foreground=color))
    
    def _process_stdout_line(self, line):
        """Process a line from stdout"""
        self._log(line)
    
    def _process_stderr_line(self, line):
        """Process a line from stderr and update progress"""
        # Classify stderr messages
        err_lower = line.lower()
        
        # Extract progress info from scraping messages
        # Pattern: "Scraping 5/100: https://..."
        if "scraping" in err_lower and "/" in line:
            try:
                import re
                match = re.search(r'scraping\s+(\d+)/(\d+)', line, re.IGNORECASE)
                if match:
                    current = int(match.group(1))
                    total = int(match.group(2))
                    self.total_urls = total
                    self.scraped_count = current
                    self._update_progress(current, total)
            except:
                pass
        
        # Extract parallel completion info
        # Pattern: "Progress: 5/100 (50.0%) completed" or "Saved progress: 5/100 completed"
        if ("progress" in err_lower or "saved progress" in err_lower) and "completed" in err_lower:
            try:
                import re
                # Try new format first: "Progress: 5/100 (50.0%) completed"
                match = re.search(r'progress:\s*(\d+)/(\d+)', line, re.IGNORECASE)
                if not match:
                    # Fallback to old format: "Saved progress: 5/100 completed"
                    match = re.search(r'saved progress:\s*(\d+)/(\d+)', line, re.IGNORECASE)
                if match:
                    current = int(match.group(1))
                    total = int(match.group(2))
                    self.total_urls = total
                    self.scraped_count = current
                    self._update_progress(current, total)
            except Exception as e:
                # Debug: log parsing errors
                self._log(f"Progress parse error: {e} for line: {line}", "warning")
        
        # Extract URL collection info
        # Pattern: "Collected 42 unique listing URLs."
        if "collected" in err_lower and "url" in err_lower:
            try:
                import re
                match = re.search(r'collected\s+(\d+)\s+unique', line, re.IGNORECASE)
                if match:
                    total = int(match.group(1))
                    self.total_urls = total
                    self._update_progress(0, total)
            except:
                pass
        
        # Log with appropriate color
        if "error" in err_lower:
            self._log(line, "error")
        elif "warning" in err_lower:
            self._log(line, "warning")
        elif "captcha" in err_lower:
            self._log(line, "warning")
        else:
            self._log(line)
    
    def _update_progress(self, current, total):
        """Update progress bar and label (thread-safe)"""
        def update():
            if total > 0:
                percentage = (current / total) * 100
                self.progress_var.set(percentage)
                self.progress_label.config(text=f"{current} / {total} pages scraped")
            else:
                self.progress_var.set(0)
                self.progress_label.config(text=f"{current} / {total} pages scraped")
        
        self.root.after(0, update)
    
    def _log_convert(self, message, tag=None):
        """Add message to conversion log (thread-safe)"""
        def update():
            self.convert_log_text.config(state=tk.NORMAL)
            if tag:
                self.convert_log_text.insert(tk.END, message + "\n", tag)
            else:
                self.convert_log_text.insert(tk.END, message + "\n")
            self.convert_log_text.see(tk.END)
            self.convert_log_text.config(state=tk.DISABLED)
        
        self.root.after(0, update)
    
    def _update_convert_status(self, text, color):
        """Update conversion status label (thread-safe)"""
        self.root.after(0, lambda: self.convert_status_label.config(text=text, foreground=color))
    
    def _start_conversion(self):
        """Start the HTML to Markdown conversion process"""
        # Validate inputs
        try:
            workers = int(self.convert_workers_var.get())
            if workers < 1:
                raise ValueError("Workers must be >= 1")
        except ValueError as e:
            self._log_convert(f"Error: {e}", "error")
            return
        
        input_file = Path(self.script_path.parent) / self.convert_input_var.get()
        if not input_file.exists():
            self._log_convert(f"Error: Input file not found: {input_file}", "error")
            return
        
        # Check if converter script exists
        if not self.converter_path.exists():
            self._log_convert(f"Error: Converter script not found at {self.converter_path}", "error")
            return
        
        # Update UI state
        self.convert_button.config(state=tk.DISABLED)
        self._update_convert_status("Running...", "orange")
        
        # Build command
        cmd = [sys.executable, str(self.converter_path), str(input_file)]
        
        # Add output file if specified
        output_file_name = self.convert_output_var.get().strip()
        if output_file_name:
            output_file = Path(self.script_path.parent) / output_file_name
            cmd.extend(["-o", str(output_file)])
        
        # Add workers
        cmd.extend(["-w", str(workers)])
        
        self._log_convert("Starting conversion with command:", "info")
        self._log_convert(" ".join(cmd), "info")
        self._log_convert("-" * 80)
        
        # Start conversion in background thread
        thread = threading.Thread(target=self._run_conversion, args=(cmd,), daemon=True)
        thread.start()
    
    def _run_conversion(self, cmd):
        """Run the conversion process and capture output"""
        try:
            # Start process with stdout/stderr capture
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                cwd=self.script_path.parent,
                universal_newlines=True
            )
            
            # Read output in real-time
            while True:
                # Check if process has finished
                if process.poll() is not None:
                    break
                
                # Read stderr (where progress messages go)
                if process.stderr:
                    line = process.stderr.readline()
                    if line:
                        self._log_convert(line.rstrip())
            
            # Read any remaining output
            if process.stderr:
                remaining_err = process.stderr.read()
                if remaining_err:
                    for line in remaining_err.splitlines():
                        self._log_convert(line)
            
            if process.stdout:
                remaining_out = process.stdout.read()
                if remaining_out:
                    for line in remaining_out.splitlines():
                        self._log_convert(line)
            
            # Check exit code
            exit_code = process.returncode
            if exit_code == 0:
                self._log_convert("-" * 80)
                self._log_convert("Conversion completed successfully!", "success")
                self._update_convert_status("Completed", "green")
            else:
                self._log_convert("-" * 80)
                self._log_convert(f"Conversion failed with exit code {exit_code}", "error")
                self._update_convert_status("Failed", "red")
        
        except Exception as e:
            self._log_convert(f"Error running converter: {e}", "error")
            self._update_convert_status("Error", "red")
        
        finally:
            self.root.after(0, lambda: self.convert_button.config(state=tk.NORMAL))


def main():
    root = tk.Tk()
    app = ScraperGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
