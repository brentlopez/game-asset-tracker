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
from pathlib import Path
import queue


class ScraperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Fab Metadata Scraper GUI")
        self.root.geometry("900x750")
        
        # Queue for thread-safe log updates
        self.log_queue = queue.Queue()
        
        # Process tracking
        self.process = None
        self.is_running = False
        self.total_urls = 0
        self.scraped_count = 0
        
        # Script path
        self.script_path = Path(__file__).parent / "scrape_fab_metadata.py"
        
        self._setup_ui()
        self._start_log_updater()
    
    def _setup_ui(self):
        """Create the UI layout"""
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)  # Log area gets extra space
        
        # === SECTION 1: Boolean Flags ===
        flags_frame = ttk.LabelFrame(main_frame, text="Options", padding="10")
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
        
        # Create checkboxes in a grid
        ttk.Checkbutton(flags_frame, text="Headless mode", variable=self.headless_var).grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Checkbutton(flags_frame, text="Clear cache before scraping", variable=self.clear_cache_var).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Checkbutton(flags_frame, text="Test scroll only (no scraping)", variable=self.test_scroll_var).grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Checkbutton(flags_frame, text="Skip library scrape (use URL file)", variable=self.skip_library_var).grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Checkbutton(flags_frame, text="Skip pages with captchas", variable=self.skip_captcha_var).grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Checkbutton(flags_frame, text="Force rescrape all URLs", variable=self.force_rescrape_var).grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        ttk.Checkbutton(flags_frame, text="New browser per page (avoid captchas)", variable=self.new_browser_var).grid(row=3, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
        ttk.Checkbutton(flags_frame, text="Block heavy resources (images/media/fonts/analytics)", variable=self.block_heavy_var).grid(row=4, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
        
        # === SECTION 2: Parameters with Values ===
        params_frame = ttk.LabelFrame(main_frame, text="Parameters", padding="10")
        params_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N), pady=(0, 10))
        params_frame.columnconfigure(1, weight=1)
        
        # Parameter variables
        self.max_scrolls_var = tk.StringVar(value="50")
        self.scroll_step_var = tk.StringVar(value="1200")
        self.scroll_steps_var = tk.StringVar(value="8")
        self.parallel_var = tk.StringVar(value="1")
        self.out_file_var = tk.StringVar(value="fab_metadata.json")
        self.url_file_var = tk.StringVar(value="fab_library_urls.json")
        
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
        
        # === SECTION 3: Control Buttons ===
        control_frame = ttk.Frame(main_frame)
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
        progress_frame = ttk.LabelFrame(main_frame, text="Progress", padding="10")
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
        log_frame = ttk.LabelFrame(main_frame, text="Log Output", padding="10")
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
        
        # Add parameters with values
        cmd.extend(["--max-scrolls", self.max_scrolls_var.get()])
        cmd.extend(["--scroll-step", self.scroll_step_var.get()])
        cmd.extend(["--scroll-steps", self.scroll_steps_var.get()])
        cmd.extend(["--parallel", self.parallel_var.get()])
        cmd.extend(["--out", self.out_file_var.get()])
        cmd.extend(["--use-url-file", self.url_file_var.get()])
        
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
    
    def _clear_log(self):
        """Clear the log text area"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
    
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
        # Pattern: "Saved progress: 5/100 completed"
        if "saved progress" in err_lower and "completed" in err_lower:
            try:
                import re
                match = re.search(r'saved progress:\s*(\d+)/(\d+)\s*completed', line, re.IGNORECASE)
                if match:
                    current = int(match.group(1))
                    total = int(match.group(2))
                    self.total_urls = total
                    self.scraped_count = current
                    self._update_progress(current, total)
            except:
                pass
        
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


def main():
    root = tk.Tk()
    app = ScraperGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
