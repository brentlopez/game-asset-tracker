#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fab Platform GUI Module

Provides Setup, Scraping, and Post-Processing tabs for the Fab (Epic) marketplace scraper.
This module is dynamically loaded by the main asset_scraper.py application.
"""
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import subprocess
import threading
import sys
import json
from pathlib import Path
import queue
import select
import os
import fcntl
import re


# Module-level state (shared across functions)
_state = {
    "log_queue": None,
    "process": None,
    "is_running": False,
    "total_urls": 0,
    "scraped_count": 0,
    "script_path": Path(__file__).parent / "scraping" / "scrape_fab_metadata.py",
    "converter_path": Path(__file__).parent / "post_processing" / "convert_html_to_markdown.py",
    "auth_script_path": Path(__file__).parent / "setup" / "generate_fab_auth.py",
    "auth_file_path": Path(__file__).parent / "setup" / "auth.json",
    "root": None
}


def create_setup_tab(parent, tk_vars):
    """Render Setup tab content for Fab authentication"""
    parent.columnconfigure(0, weight=1)
    parent.rowconfigure(2, weight=1)
    
    # Header
    header_frame = ttk.LabelFrame(parent, text="Fab Authentication Setup", padding="10")
    header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N), pady=(0, 10))
    header_frame.columnconfigure(0, weight=1)
    
    ttk.Label(header_frame, text="Before scraping, you need to authenticate with Fab.com.").grid(row=0, column=0, sticky=tk.W, pady=5)
    ttk.Label(header_frame, text="This will launch a browser where you can log in. Your session will be saved.").grid(row=1, column=0, sticky=tk.W, pady=5)
    
    # Auth status
    status_frame = ttk.LabelFrame(parent, text="Authentication Status", padding="10")
    status_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N), pady=(0, 10))
    
    auth_exists = _state["auth_file_path"].exists()
    status_text = "✓ auth.json found" if auth_exists else "✗ auth.json not found"
    status_color = "green" if auth_exists else "red"
    
    tk_vars["auth_status_label"] = ttk.Label(status_frame, text=status_text, foreground=status_color, font=("", 10, "bold"))
    tk_vars["auth_status_label"].grid(row=0, column=0, sticky=tk.W, pady=5)
    
    if auth_exists:
        ttk.Label(status_frame, text=f"Location: {_state['auth_file_path']}", foreground="gray").grid(row=1, column=0, sticky=tk.W, pady=2)
    
    # Actions
    action_frame = ttk.Frame(status_frame)
    action_frame.grid(row=2, column=0, sticky=tk.W, pady=(10, 0))
    
    ttk.Button(action_frame, text="Generate Authentication", 
               command=lambda: _run_auth_script(tk_vars)).pack(side=tk.LEFT, padx=(0, 5))
    
    if auth_exists:
        ttk.Button(action_frame, text="Delete auth.json", 
                   command=lambda: _delete_auth_file(tk_vars)).pack(side=tk.LEFT, padx=5)
    
    # Log output
    log_frame = ttk.LabelFrame(parent, text="Setup Log", padding="10")
    log_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 0))
    log_frame.columnconfigure(0, weight=1)
    log_frame.rowconfigure(0, weight=1)
    
    tk_vars["setup_log"] = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=15, state=tk.DISABLED)
    tk_vars["setup_log"].grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    tk_vars["setup_log"].tag_config("error", foreground="red")
    tk_vars["setup_log"].tag_config("success", foreground="green")
    tk_vars["setup_log"].tag_config("info", foreground="blue")


def _run_auth_script(tk_vars):
    """Run the authentication script"""
    def log_message(msg, tag=None):
        log = tk_vars.get("setup_log")
        if log:
            log.config(state=tk.NORMAL)
            if tag:
                log.insert(tk.END, msg + "\n", tag)
            else:
                log.insert(tk.END, msg + "\n")
            log.see(tk.END)
            log.config(state=tk.DISABLED)
    
    log_message("Starting authentication script...", "info")
    log_message(f"Running: {_state['auth_script_path']}", "info")
    
    def run():
        try:
            result = subprocess.run(
                [sys.executable, str(_state["auth_script_path"])],
                capture_output=True,
                text=True,
                cwd=_state["auth_script_path"].parent
            )
            
            if result.stdout:
                log_message(result.stdout)
            if result.stderr:
                log_message(result.stderr)
            
            if result.returncode == 0:
                log_message("Authentication completed successfully!", "success")
                _refresh_auth_status(tk_vars)
            else:
                log_message(f"Authentication failed with exit code {result.returncode}", "error")
        except Exception as e:
            log_message(f"Error running authentication: {e}", "error")
    
    thread = threading.Thread(target=run, daemon=True)
    thread.start()


def _delete_auth_file(tk_vars):
    """Delete the auth.json file"""
    if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete auth.json?"):
        try:
            _state["auth_file_path"].unlink()
            messagebox.showinfo("Success", "auth.json deleted")
            _refresh_auth_status(tk_vars)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete auth.json: {e}")


def _refresh_auth_status(tk_vars):
    """Refresh authentication status display"""
    auth_exists = _state["auth_file_path"].exists()
    status_text = "✓ auth.json found" if auth_exists else "✗ auth.json not found"
    status_color = "green" if auth_exists else "red"
    
    label = tk_vars.get("auth_status_label")
    if label:
        label.config(text=status_text, foreground=status_color)


def create_scraping_tab(parent, tk_vars):
    """Render Scraping tab content for Fab metadata scraping"""
    _state["root"] = parent.winfo_toplevel()
    _state["log_queue"] = queue.Queue()
    
    # Create a canvas with scrollbar for the entire tab
    canvas = tk.Canvas(parent, highlightthickness=0, bd=0)
    scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)
    
    def _on_frame_configure(event):
        # Update scroll region
        canvas.configure(scrollregion=canvas.bbox("all"))
        # Check if scrolling is needed
        bbox = canvas.bbox("all")
        if bbox:
            content_height = bbox[3] - bbox[1]
            canvas_height = canvas.winfo_height()
            # Only show scrollbar if content exceeds canvas height
            if content_height > canvas_height:
                scrollbar.pack(side="right", fill="y")
            else:
                scrollbar.pack_forget()
    
    scrollable_frame.bind("<Configure>", _on_frame_configure)
    
    canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    
    # Make the scrollable frame fill the canvas width
    def _configure_canvas(event):
        canvas.itemconfig(canvas_window, width=event.width)
    canvas.bind("<Configure>", _configure_canvas)
    
    # Pack canvas and scrollbar
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    # Enable mousewheel scrolling (only if scrollable)
    def _on_mousewheel(event):
        # Check if content is scrollable
        bbox = canvas.bbox("all")
        if bbox:
            content_height = bbox[3] - bbox[1]
            canvas_height = canvas.winfo_height()
            if content_height > canvas_height:
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
                return "break"
        return "break"
    
    def _on_mousewheel_mac(event):
        # Check if content is scrollable
        bbox = canvas.bbox("all")
        if bbox:
            content_height = bbox[3] - bbox[1]
            canvas_height = canvas.winfo_height()
            if content_height > canvas_height:
                canvas.yview_scroll(int(-1*event.delta), "units")
                return "break"
        return "break"
    
    def _bind_mousewheel(widget):
        """Recursively bind mousewheel to widget and all children"""
        # Skip text widgets that have their own scrolling
        if isinstance(widget, (scrolledtext.ScrolledText, tk.Text)):
            return
        
        try:
            if sys.platform == "darwin":
                widget.bind("<MouseWheel>", _on_mousewheel_mac)
            else:
                widget.bind("<MouseWheel>", _on_mousewheel)
                widget.bind("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
                widget.bind("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))
        except tk.TclError:
            pass  # Some widgets can't be bound
        
        try:
            for child in widget.winfo_children():
                _bind_mousewheel(child)
        except tk.TclError:
            pass
    
    # Bind to canvas
    if sys.platform == "darwin":
        canvas.bind("<MouseWheel>", _on_mousewheel_mac)
    else:
        canvas.bind("<MouseWheel>", _on_mousewheel)
        canvas.bind("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
        canvas.bind("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))
    
    # Configure scrollable_frame layout
    scrollable_frame.columnconfigure(0, weight=1)
    
    # Initialize variables
    _init_scraping_vars(tk_vars)
    
    # Build UI sections with collapsible frames
    row = 0
    _create_collapsible_section(scrollable_frame, tk_vars, "Options", 
                                lambda parent: _create_scraping_options_content(parent, tk_vars), 
                                row, expanded=True)
    row += 1
    _create_collapsible_section(scrollable_frame, tk_vars, "Parameters", 
                                lambda parent: _create_scraping_parameters_content(parent, tk_vars), 
                                row, expanded=False)
    row += 1
    _create_scraping_controls(scrollable_frame, tk_vars, row)
    row += 1
    _create_collapsible_section(scrollable_frame, tk_vars, "Progress", 
                                lambda parent: _create_scraping_progress_content(parent, tk_vars), 
                                row, expanded=True)
    row += 1
    _create_collapsible_section(scrollable_frame, tk_vars, "Console", 
                                lambda parent: _create_scraping_log_content(parent, tk_vars), 
                                row, expanded=True)
    
    # Bind mousewheel to all widgets after they're created
    _bind_mousewheel(scrollable_frame)
    
    # Start log updater
    _start_log_updater(tk_vars)


def _init_scraping_vars(tk_vars):
    """Initialize scraping tab variables"""
    # Boolean flags
    tk_vars["headless"] = tk.BooleanVar(value=False)
    tk_vars["clear_cache"] = tk.BooleanVar(value=False)
    tk_vars["test_scroll"] = tk.BooleanVar(value=False)
    tk_vars["skip_library"] = tk.BooleanVar(value=False)
    tk_vars["skip_captcha"] = tk.BooleanVar(value=False)
    tk_vars["force_rescrape"] = tk.BooleanVar(value=False)
    tk_vars["new_browser"] = tk.BooleanVar(value=False)
    tk_vars["block_heavy"] = tk.BooleanVar(value=True)
    tk_vars["reuse_browser"] = tk.BooleanVar(value=True)
    tk_vars["randomize_ua"] = tk.BooleanVar(value=True)
    tk_vars["auth_on_listings"] = tk.BooleanVar(value=False)
    tk_vars["captcha_retry"] = tk.BooleanVar(value=True)
    tk_vars["measure_bytes"] = tk.BooleanVar(value=False)
    tk_vars["fetch_manifests"] = tk.BooleanVar(value=False)
    
    # Parameters
    tk_vars["max_scrolls"] = tk.StringVar(value="50")
    tk_vars["scroll_step"] = tk.StringVar(value="1200")
    tk_vars["scroll_steps"] = tk.StringVar(value="8")
    tk_vars["parallel"] = tk.StringVar(value="1")
    tk_vars["out_file"] = tk.StringVar(value="output/fab_metadata.json")
    tk_vars["url_file"] = tk.StringVar(value="setup/fab_library_urls.json")
    tk_vars["sleep_min"] = tk.StringVar(value="300")
    tk_vars["sleep_max"] = tk.StringVar(value="800")
    tk_vars["burst_size"] = tk.StringVar(value="5")
    tk_vars["burst_sleep"] = tk.StringVar(value="3000")
    tk_vars["proxy_file"] = tk.StringVar(value="")
    tk_vars["measure_report"] = tk.StringVar(value="output/fab_bandwidth_report.jsonl")
    
    # Progress
    tk_vars["progress"] = tk.DoubleVar(value=0)


def _create_collapsible_section(parent, tk_vars, title, content_builder, row, expanded=True):
    """Create a collapsible section with expand/collapse functionality"""
    # Container frame
    container = ttk.Frame(parent)
    container.grid(row=row, column=0, sticky=(tk.W, tk.E, tk.N), pady=(0, 0))
    container.columnconfigure(0, weight=1)
    
    # Top separator
    ttk.Separator(container, orient="horizontal").grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
    
    # Header frame with clickable area
    header_frame = ttk.Frame(container, cursor="hand2")
    header_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
    header_frame.columnconfigure(1, weight=1)
    
    # Store collapse state
    collapse_var = tk.BooleanVar(value=not expanded)
    
    # Toggle function
    def toggle(event=None):
        if collapse_var.get():
            # Expand
            content_frame.grid()
            arrow_label.config(text="▼")
            collapse_var.set(False)
        else:
            # Collapse
            content_frame.grid_remove()
            arrow_label.config(text="▶")
            collapse_var.set(True)
    
    # Arrow icon (small, clickable)
    arrow_label = ttk.Label(header_frame, text="▼" if expanded else "▶", 
                           font=("", 9), cursor="hand2")
    arrow_label.grid(row=0, column=0, padx=(5, 5))
    arrow_label.bind("<Button-1>", toggle)
    
    # Title label (also clickable)
    title_label = ttk.Label(header_frame, text=title, font=("", 10, "bold"), cursor="hand2")
    title_label.grid(row=0, column=1, sticky=tk.W)
    title_label.bind("<Button-1>", toggle)
    
    # Make entire header frame clickable
    header_frame.bind("<Button-1>", toggle)
    
    # Content frame (without border)
    content_frame = ttk.Frame(container, padding="10")
    content_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N), padx=(10, 0))
    content_frame.columnconfigure(0, weight=1)
    
    # Build content
    content_builder(content_frame)
    
    # Initially hide if not expanded
    if not expanded:
        content_frame.grid_remove()
    
    # Bottom separator (subtle)
    ttk.Separator(container, orient="horizontal").grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(5, 10))


def _create_scraping_options_content(parent, tk_vars):
    """Create scraping options content"""
    parent.columnconfigure(0, weight=1)
    parent.columnconfigure(1, weight=1)
    
    ttk.Checkbutton(parent, text="Headless mode", variable=tk_vars["headless"]).grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
    ttk.Checkbutton(parent, text="Clear cache before scraping", variable=tk_vars["clear_cache"]).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
    ttk.Checkbutton(parent, text="Test scroll only (no scraping)", variable=tk_vars["test_scroll"]).grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
    ttk.Checkbutton(parent, text="Skip library scrape (use URL file)", variable=tk_vars["skip_library"]).grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
    ttk.Checkbutton(parent, text="Skip pages with captchas", variable=tk_vars["skip_captcha"]).grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
    ttk.Checkbutton(parent, text="Force rescrape all URLs", variable=tk_vars["force_rescrape"]).grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
    ttk.Checkbutton(parent, text="New browser per page (avoid captchas)", variable=tk_vars["new_browser"]).grid(row=3, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
    ttk.Checkbutton(parent, text="Reuse one browser per worker (new context per URL)", variable=tk_vars["reuse_browser"]).grid(row=4, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
    ttk.Checkbutton(parent, text="Randomize UA + viewport per context", variable=tk_vars["randomize_ua"]).grid(row=5, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
    ttk.Checkbutton(parent, text="Use auth on listing pages (normally off)", variable=tk_vars["auth_on_listings"]).grid(row=6, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
    ttk.Checkbutton(parent, text="Captcha backoff + retry once", variable=tk_vars["captcha_retry"]).grid(row=7, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
    ttk.Checkbutton(parent, text="Block heavy resources (images/media/fonts/analytics)", variable=tk_vars["block_heavy"]).grid(row=8, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
    ttk.Checkbutton(parent, text="Measure bytes (write JSONL report)", variable=tk_vars["measure_bytes"]).grid(row=9, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
    ttk.Checkbutton(parent, text="Fetch FAB manifests (bypasses CAPTCHA)", variable=tk_vars["fetch_manifests"]).grid(row=10, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)


def _create_scraping_parameters_content(parent, tk_vars):
    """Create scraping parameters content"""
    parent.columnconfigure(1, weight=1)
    
    row = 0
    ttk.Label(parent, text="Max scrolls:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
    ttk.Entry(parent, textvariable=tk_vars["max_scrolls"], width=15).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
    
    row += 1
    ttk.Label(parent, text="Scroll step (px):").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
    ttk.Entry(parent, textvariable=tk_vars["scroll_step"], width=15).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
    
    row += 1
    ttk.Label(parent, text="Scroll steps per round:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
    ttk.Entry(parent, textvariable=tk_vars["scroll_steps"], width=15).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
    
    row += 1
    ttk.Label(parent, text="Parallel workers (1=sequential):").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
    parallel_frame = ttk.Frame(parent)
    parallel_frame.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
    ttk.Entry(parallel_frame, textvariable=tk_vars["parallel"], width=10).pack(side=tk.LEFT)
    ttk.Label(parallel_frame, text="(2-10 recommended)", foreground="gray").pack(side=tk.LEFT, padx=(5, 0))
    
    row += 1
    ttk.Label(parent, text="Output file:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
    out_frame = ttk.Frame(parent)
    out_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
    out_frame.columnconfigure(0, weight=1)
    ttk.Entry(out_frame, textvariable=tk_vars["out_file"]).grid(row=0, column=0, sticky=(tk.W, tk.E))
    ttk.Button(out_frame, text="Browse", command=lambda: _browse_output_file(tk_vars), width=8).grid(row=0, column=1, padx=(5, 0))
    
    row += 1
    ttk.Label(parent, text="URL file (for --skip-library-scrape):").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
    url_frame = ttk.Frame(parent)
    url_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
    url_frame.columnconfigure(0, weight=1)
    ttk.Entry(url_frame, textvariable=tk_vars["url_file"]).grid(row=0, column=0, sticky=(tk.W, tk.E))
    ttk.Button(url_frame, text="Browse", command=lambda: _browse_url_file(tk_vars), width=8).grid(row=0, column=1, padx=(5, 0))
    
    row += 1
    ttk.Label(parent, text="Proxy list file:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
    proxy_frame = ttk.Frame(parent)
    proxy_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
    proxy_frame.columnconfigure(0, weight=1)
    ttk.Entry(proxy_frame, textvariable=tk_vars["proxy_file"]).grid(row=0, column=0, sticky=(tk.W, tk.E))
    ttk.Button(proxy_frame, text="Browse", command=lambda: _browse_proxy_file(tk_vars), width=8).grid(row=0, column=1, padx=(5, 0))
    
    row += 1
    ttk.Label(parent, text="Measure report (JSONL):").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
    meas_frame = ttk.Frame(parent)
    meas_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
    meas_frame.columnconfigure(0, weight=1)
    ttk.Entry(meas_frame, textvariable=tk_vars["measure_report"]).grid(row=0, column=0, sticky=(tk.W, tk.E))
    
    # Cadence
    row += 1
    ttk.Label(parent, text="Sleep min (ms):").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
    ttk.Entry(parent, textvariable=tk_vars["sleep_min"], width=10).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
    row += 1
    ttk.Label(parent, text="Sleep max (ms):").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
    ttk.Entry(parent, textvariable=tk_vars["sleep_max"], width=10).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
    row += 1
    ttk.Label(parent, text="Burst size:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
    ttk.Entry(parent, textvariable=tk_vars["burst_size"], width=10).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
    row += 1
    ttk.Label(parent, text="Burst sleep (ms):").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
    ttk.Entry(parent, textvariable=tk_vars["burst_sleep"], width=10).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)


def _create_scraping_controls(parent, tk_vars, row):
    """Create scraping control buttons"""
    control_frame = ttk.Frame(parent)
    control_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
    
    tk_vars["start_button"] = ttk.Button(control_frame, text="Start Scraping", command=lambda: _start_scraping(tk_vars))
    tk_vars["start_button"].pack(side=tk.LEFT, padx=5)
    
    tk_vars["stop_button"] = ttk.Button(control_frame, text="Stop", command=lambda: _stop_scraping(tk_vars), state=tk.DISABLED)
    tk_vars["stop_button"].pack(side=tk.LEFT, padx=5)
    
    ttk.Button(control_frame, text="Clear Log", command=lambda: _clear_log(tk_vars)).pack(side=tk.LEFT, padx=5)
    
    tk_vars["status_label"] = ttk.Label(control_frame, text="Ready", foreground="green")
    tk_vars["status_label"].pack(side=tk.LEFT, padx=20)


def _create_scraping_progress_content(parent, tk_vars):
    """Create progress bar content"""
    parent.columnconfigure(0, weight=1)
    
    tk_vars["progress_bar"] = ttk.Progressbar(parent, variable=tk_vars["progress"], maximum=100, mode='determinate')
    tk_vars["progress_bar"].grid(row=0, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
    
    tk_vars["progress_label"] = ttk.Label(parent, text="0 / 0 pages scraped")
    tk_vars["progress_label"].grid(row=1, column=0, sticky=tk.W, padx=5)


def _create_scraping_log_content(parent, tk_vars):
    """Create log output content"""
    parent.columnconfigure(0, weight=1)
    parent.rowconfigure(0, weight=1)
    
    tk_vars["log_text"] = scrolledtext.ScrolledText(parent, wrap=tk.WORD, height=20, state=tk.DISABLED)
    tk_vars["log_text"].grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    tk_vars["log_text"].tag_config("error", foreground="red")
    tk_vars["log_text"].tag_config("warning", foreground="orange")
    tk_vars["log_text"].tag_config("success", foreground="green")
    tk_vars["log_text"].tag_config("info", foreground="blue")


def _browse_output_file(tk_vars):
    """Browse for output file"""
    # Allow selecting existing file or entering new filename
    filename = filedialog.askopenfilename(
        title="Select output file (or cancel to create new)",
        initialdir=Path(__file__).parent / "output",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
    )
    if filename:
        # Store absolute path so script can find it regardless of working directory
        tk_vars["out_file"].set(str(Path(filename).resolve()))
    else:
        # If cancelled, offer save dialog to create new file
        filename = filedialog.asksaveasfilename(
            title="Create new output file",
            initialdir=Path(__file__).parent / "output",
            initialfile="fab_metadata.json",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            tk_vars["out_file"].set(str(Path(filename).resolve()))


def _browse_url_file(tk_vars):
    """Browse for URL file"""
    filename = filedialog.askopenfilename(
        title="Select URL file",
        initialdir=Path(__file__).parent,
        initialfile=tk_vars["url_file"].get(),
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
    )
    if filename:
        # Store absolute path so script can find it regardless of working directory
        tk_vars["url_file"].set(str(Path(filename).resolve()))


def _browse_proxy_file(tk_vars):
    """Browse for proxy file"""
    filename = filedialog.askopenfilename(
        title="Select proxy list file",
        initialdir=Path(__file__).parent,
        filetypes=[("Text files", "*.txt *.list"), ("All files", "*.*")]
    )
    if filename:
        # Store absolute path so script can find it regardless of working directory
        tk_vars["proxy_file"].set(str(Path(filename).resolve()))


def _start_scraping(tk_vars):
    """Start the scraping process"""
    if _state["is_running"]:
        return
    
    # Validate inputs
    try:
        int(tk_vars["max_scrolls"].get())
        int(tk_vars["scroll_step"].get())
        int(tk_vars["scroll_steps"].get())
        parallel = int(tk_vars["parallel"].get())
        if parallel < 1:
            raise ValueError("Parallel workers must be >= 1")
        if parallel > 20:
            _log("Warning: More than 20 parallel workers may cause issues", "warning", tk_vars)
        int(tk_vars["sleep_min"].get())
        int(tk_vars["sleep_max"].get())
        int(tk_vars["burst_size"].get())
        int(tk_vars["burst_sleep"].get())
    except ValueError as e:
        _log(f"Error: {e}", "error", tk_vars)
        return
    
    # Check if script exists
    if not _state["script_path"].exists():
        _log(f"Error: Script not found at {_state['script_path']}", "error", tk_vars)
        return
    
    # Update UI state
    _state["is_running"] = True
    tk_vars["start_button"].config(state=tk.DISABLED)
    tk_vars["stop_button"].config(state=tk.NORMAL)
    tk_vars["status_label"].config(text="Running...", foreground="orange")
    
    # Build command
    cmd = _build_command(tk_vars)
    _log("Starting scraper with command:", "info", tk_vars)
    _log(" ".join(cmd), "info", tk_vars)
    _log("-" * 80, None, tk_vars)
    
    # Start progress file monitoring
    _state["root"].after(200, lambda: _monitor_progress_file(tk_vars))
    
    # Start scraping in background thread
    thread = threading.Thread(target=_run_scraping, args=(cmd, tk_vars), daemon=True)
    thread.start()


def _build_command(tk_vars):
    """Build the scraping command"""
    cmd = [sys.executable, str(_state["script_path"])]
    
    # Add boolean flags
    if tk_vars["headless"].get():
        cmd.append("--headless")
    if tk_vars["clear_cache"].get():
        cmd.append("--clear-cache")
    if tk_vars["test_scroll"].get():
        cmd.append("--test-scroll")
    if tk_vars["skip_library"].get():
        cmd.append("--skip-library-scrape")
    if tk_vars["skip_captcha"].get():
        cmd.append("--skip-on-captcha")
    if tk_vars["force_rescrape"].get():
        cmd.append("--force-rescrape")
    if tk_vars["new_browser"].get():
        cmd.append("--new-browser-per-page")
    if tk_vars["block_heavy"].get():
        cmd.append("--block-heavy")
    if tk_vars["reuse_browser"].get():
        cmd.append("--reuse-browser")
    if tk_vars["randomize_ua"].get():
        cmd.append("--randomize-ua")
    if tk_vars["auth_on_listings"].get():
        cmd.append("--auth-on-listings")
    if tk_vars["captcha_retry"].get():
        cmd.append("--captcha-retry")
    if tk_vars["measure_bytes"].get():
        cmd.append("--measure-bytes")
        if tk_vars["measure_report"].get().strip():
            cmd.extend(["--measure-report", tk_vars["measure_report"].get().strip()])
    if tk_vars["fetch_manifests"].get():
        cmd.append("--fetch-manifests")
    
    # Add parameters
    cmd.extend(["--sleep-min-ms", tk_vars["sleep_min"].get()])
    cmd.extend(["--sleep-max-ms", tk_vars["sleep_max"].get()])
    cmd.extend(["--burst-size", tk_vars["burst_size"].get()])
    cmd.extend(["--burst-sleep-ms", tk_vars["burst_sleep"].get()])
    if tk_vars["proxy_file"].get().strip():
        cmd.extend(["--proxy-list", tk_vars["proxy_file"].get().strip()])
    
    cmd.extend(["--max-scrolls", tk_vars["max_scrolls"].get()])
    cmd.extend(["--scroll-step", tk_vars["scroll_step"].get()])
    cmd.extend(["--scroll-steps", tk_vars["scroll_steps"].get()])
    cmd.extend(["--parallel", tk_vars["parallel"].get()])
    cmd.extend(["--out", tk_vars["out_file"].get()])
    cmd.extend(["--use-url-file", tk_vars["url_file"].get()])
    
    cmd.append("--progress-newlines")
    
    # Add progress file
    _state["progress_file_path"] = _state["script_path"].parent / ".scraper_progress.json"
    cmd.extend(["--progress-file", str(_state["progress_file_path"])])
    
    return cmd


def _run_scraping(cmd, tk_vars):
    """Run the scraping process"""
    try:
        _state["total_urls"] = 0
        _state["scraped_count"] = 0
        _update_progress(0, 0, tk_vars)
        
        _state["process"] = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=_state["script_path"].parent,
            universal_newlines=True,
            preexec_fn=os.setsid
        )
        
        # Set non-blocking I/O
        for stream in [_state["process"].stdout, _state["process"].stderr]:
            if stream:
                fd = stream.fileno()
                flags = fcntl.fcntl(fd, fcntl.F_GETFL)
                fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
        
        # Read output in real-time
        while True:
            if _state["process"].poll() is not None:
                break
            
            readable = []
            if _state["process"].stdout:
                readable.append(_state["process"].stdout)
            if _state["process"].stderr:
                readable.append(_state["process"].stderr)
            
            ready, _, _ = select.select(readable, [], [], 0.1)
            
            for stream in ready:
                try:
                    line = stream.readline()
                    if line:
                        line = line.rstrip()
                        if stream == _state["process"].stderr:
                            _process_stderr_line(line, tk_vars)
                        else:
                            _log(line, None, tk_vars)
                except:
                    pass
        
        # Read remaining output
        if _state["process"].stdout:
            try:
                remaining = _state["process"].stdout.read()
                if remaining:
                    for line in remaining.splitlines():
                        _log(line, None, tk_vars)
            except:
                pass
        
        if _state["process"].stderr:
            try:
                remaining = _state["process"].stderr.read()
                if remaining:
                    for line in remaining.splitlines():
                        _process_stderr_line(line, tk_vars)
            except:
                pass
        
        # Check exit code
        exit_code = _state["process"].returncode
        if exit_code == 0:
            _log("-" * 80, None, tk_vars)
            _log("Scraping completed successfully!", "success", tk_vars)
            _update_status("Completed", "green", tk_vars)
        else:
            _log("-" * 80, None, tk_vars)
            _log(f"Scraping failed with exit code {exit_code}", "error", tk_vars)
            _update_status("Failed", "red", tk_vars)
    
    except Exception as e:
        _log(f"Error running scraper: {e}", "error", tk_vars)
        _update_status("Error", "red", tk_vars)
    
    finally:
        _cleanup_process(tk_vars)


def _stop_scraping(tk_vars):
    """Stop the scraping process"""
    if _state["process"] and _state["process"].poll() is None:
        _log("Stopping scraper...", "warning", tk_vars)
        
        try:
            import signal
            pgid = os.getpgid(_state["process"].pid)
            _log(f"Terminating process group {pgid}...", "info", tk_vars)
            os.killpg(pgid, signal.SIGTERM)
            
            try:
                _state["process"].wait(timeout=3)
                _log("Scraper terminated gracefully", "warning", tk_vars)
            except subprocess.TimeoutExpired:
                _log("Force killing process group...", "error", tk_vars)
                try:
                    os.killpg(pgid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                
                try:
                    _state["process"].kill()
                except:
                    pass
                
                _log("Scraper force killed", "error", tk_vars)
        
        except (ProcessLookupError, PermissionError) as e:
            _log(f"Process cleanup: {e}", "warning", tk_vars)
            try:
                _state["process"].kill()
            except:
                pass
        
        # Clean up browser processes
        try:
            subprocess.run(["pkill", "-9", "chromium"], capture_output=True, timeout=2)
            _log("Cleaned up browser processes", "info", tk_vars)
        except:
            pass
        
        _update_status("Stopped", "orange", tk_vars)
    
    _cleanup_process(tk_vars)


def _cleanup_process(tk_vars):
    """Clean up after process finishes"""
    _state["is_running"] = False
    _state["process"] = None
    
    if "progress_file_path" in _state:
        try:
            if _state["progress_file_path"].exists():
                _state["progress_file_path"].unlink()
        except:
            pass
    
    _state["root"].after(0, lambda: tk_vars["start_button"].config(state=tk.NORMAL))
    _state["root"].after(0, lambda: tk_vars["stop_button"].config(state=tk.DISABLED))


def _monitor_progress_file(tk_vars):
    """Monitor progress file for updates"""
    if _state["is_running"] and "progress_file_path" in _state:
        try:
            if _state["progress_file_path"].exists():
                with open(_state["progress_file_path"], 'r') as f:
                    data = json.load(f)
                    current = data.get('current', 0)
                    total = data.get('total', 0)
                    if total > 0:
                        _state["total_urls"] = total
                        _state["scraped_count"] = current
                        _update_progress(current, total, tk_vars)
        except:
            pass
    
    if _state["is_running"]:
        _state["root"].after(200, lambda: _monitor_progress_file(tk_vars))


def _process_stderr_line(line, tk_vars):
    """Process stderr line and update progress"""
    err_lower = line.lower()
    
    # Extract progress info
    if "scraping" in err_lower and "/" in line:
        try:
            match = re.search(r'scraping\s+(\d+)/(\d+)', line, re.IGNORECASE)
            if match:
                current = int(match.group(1))
                total = int(match.group(2))
                _state["total_urls"] = total
                _state["scraped_count"] = current
                _update_progress(current, total, tk_vars)
        except:
            pass
    
    if ("progress" in err_lower or "saved progress" in err_lower) and "completed" in err_lower:
        try:
            match = re.search(r'progress:\s*(\d+)/(\d+)', line, re.IGNORECASE)
            if not match:
                match = re.search(r'saved progress:\s*(\d+)/(\d+)', line, re.IGNORECASE)
            if match:
                current = int(match.group(1))
                total = int(match.group(2))
                _state["total_urls"] = total
                _state["scraped_count"] = current
                _update_progress(current, total, tk_vars)
        except Exception as e:
            _log(f"Progress parse error: {e} for line: {line}", "warning", tk_vars)
    
    if "collected" in err_lower and "url" in err_lower:
        try:
            match = re.search(r'collected\s+(\d+)\s+unique', line, re.IGNORECASE)
            if match:
                total = int(match.group(1))
                _state["total_urls"] = total
                _update_progress(0, total, tk_vars)
        except:
            pass
    
    # Log with appropriate color
    if "error" in err_lower:
        _log(line, "error", tk_vars)
    elif "warning" in err_lower:
        _log(line, "warning", tk_vars)
    elif "captcha" in err_lower:
        _log(line, "warning", tk_vars)
    else:
        _log(line, None, tk_vars)


def _update_progress(current, total, tk_vars):
    """Update progress bar"""
    def update():
        if total > 0:
            percentage = (current / total) * 100
            tk_vars["progress"].set(percentage)
            tk_vars["progress_label"].config(text=f"{current} / {total} pages scraped")
        else:
            tk_vars["progress"].set(0)
            tk_vars["progress_label"].config(text=f"{current} / {total} pages scraped")
    
    _state["root"].after(0, update)


def _update_status(text, color, tk_vars):
    """Update status label"""
    _state["root"].after(0, lambda: tk_vars["status_label"].config(text=text, foreground=color))


def _log(message, tag, tk_vars):
    """Add message to log queue"""
    _state["log_queue"].put((message, tag))


def _update_log_from_queue(tk_vars):
    """Process queued log messages"""
    try:
        while True:
            message, tag = _state["log_queue"].get_nowait()
            log = tk_vars.get("log_text")
            if log:
                log.config(state=tk.NORMAL)
                if tag:
                    log.insert(tk.END, message + "\n", tag)
                else:
                    log.insert(tk.END, message + "\n")
                log.see(tk.END)
                log.config(state=tk.DISABLED)
    except queue.Empty:
        pass
    
    _state["root"].after(100, lambda: _update_log_from_queue(tk_vars))


def _start_log_updater(tk_vars):
    """Start the periodic log updater"""
    _state["root"].after(100, lambda: _update_log_from_queue(tk_vars))


def _clear_log(tk_vars):
    """Clear the log text area"""
    log = tk_vars.get("log_text")
    if log:
        log.config(state=tk.NORMAL)
        log.delete(1.0, tk.END)
        log.config(state=tk.DISABLED)


def create_postprocessing_tab(parent, tk_vars):
    """Render Post-Processing tab content for HTML to Markdown conversion"""
    parent.columnconfigure(0, weight=1)
    parent.columnconfigure(1, weight=1)
    parent.rowconfigure(3, weight=1)
    
    # Initialize preview state
    tk_vars["preview_visible"] = False
    tk_vars["preview_assets"] = []  # List of (title, fab_id) tuples
    
    # File Selection
    file_frame = ttk.LabelFrame(parent, text="Input/Output Files", padding="10")
    file_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N), pady=(0, 10))
    file_frame.columnconfigure(1, weight=1)
    
    tk_vars["convert_input"] = tk.StringVar(value="output/fab_metadata.json")
    tk_vars["convert_output"] = tk.StringVar(value="")
    
    ttk.Label(file_frame, text="Input JSON file:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
    input_frame = ttk.Frame(file_frame)
    input_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
    input_frame.columnconfigure(0, weight=1)
    ttk.Entry(input_frame, textvariable=tk_vars["convert_input"]).grid(row=0, column=0, sticky=(tk.W, tk.E))
    ttk.Button(input_frame, text="Browse", command=lambda: _browse_convert_input(tk_vars), width=8).grid(row=0, column=1, padx=(5, 0))
    
    ttk.Label(file_frame, text="Output JSON file:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
    output_frame = ttk.Frame(file_frame)
    output_frame.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
    output_frame.columnconfigure(0, weight=1)
    ttk.Entry(output_frame, textvariable=tk_vars["convert_output"]).grid(row=0, column=0, sticky=(tk.W, tk.E))
    ttk.Button(output_frame, text="Browse", command=lambda: _browse_convert_output(tk_vars), width=8).grid(row=0, column=1, padx=(5, 0))
    ttk.Label(file_frame, text="(Leave empty to overwrite input file)", foreground="gray").grid(row=2, column=1, sticky=tk.W, padx=5)
    
    # Options
    options_frame = ttk.LabelFrame(parent, text="Conversion Options", padding="10")
    options_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N), pady=(0, 10))
    
    tk_vars["convert_workers"] = tk.StringVar(value="4")
    ttk.Label(options_frame, text="Parallel workers:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
    worker_frame = ttk.Frame(options_frame)
    worker_frame.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
    ttk.Entry(worker_frame, textvariable=tk_vars["convert_workers"], width=10).pack(side=tk.LEFT)
    ttk.Label(worker_frame, text="(More workers = faster conversion)", foreground="gray").pack(side=tk.LEFT, padx=(5, 0))
    
    # Control Buttons
    control_frame = ttk.Frame(parent)
    control_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
    
    tk_vars["convert_button"] = ttk.Button(control_frame, text="Convert to Markdown", command=lambda: _start_conversion(tk_vars))
    tk_vars["convert_button"].pack(side=tk.LEFT, padx=5)
    
    ttk.Button(control_frame, text="Clear Log", command=lambda: _clear_convert_log(tk_vars)).pack(side=tk.LEFT, padx=5)
    
    tk_vars["convert_status_label"] = ttk.Label(control_frame, text="Ready", foreground="green")
    tk_vars["convert_status_label"].pack(side=tk.LEFT, padx=20)
    
    # Preview controls (right side of control frame)
    preview_control_frame = ttk.Frame(control_frame)
    preview_control_frame.pack(side=tk.RIGHT, padx=5)
    
    ttk.Label(preview_control_frame, text="Select an Asset:").pack(side=tk.LEFT, padx=(0, 5))
    
    tk_vars["preview_dropdown"] = ttk.Combobox(preview_control_frame, state="readonly", width=30)
    tk_vars["preview_dropdown"].pack(side=tk.LEFT, padx=(0, 5))
    tk_vars["preview_dropdown"].set("")
    tk_vars["preview_dropdown"]["values"] = []
    tk_vars["preview_dropdown"].bind("<<ComboboxSelected>>", lambda e: _on_asset_selected(tk_vars))
    
    tk_vars["preview_button"] = ttk.Button(preview_control_frame, text="Show Preview", 
                                           command=lambda: _toggle_preview(tk_vars), state=tk.DISABLED)
    tk_vars["preview_button"].pack(side=tk.LEFT, padx=(0, 5))
    
    # Log Output
    log_frame = ttk.LabelFrame(parent, text="Conversion Log", padding="10")
    log_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 0))
    log_frame.columnconfigure(0, weight=1)
    log_frame.rowconfigure(0, weight=1)
    
    tk_vars["convert_log"] = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=20, state=tk.DISABLED)
    tk_vars["convert_log"].grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    tk_vars["convert_log"].tag_config("error", foreground="red")
    tk_vars["convert_log"].tag_config("warning", foreground="orange")
    tk_vars["convert_log"].tag_config("success", foreground="green")
    tk_vars["convert_log"].tag_config("info", foreground="blue")
    
    # Preview Column (full height, initially hidden)
    preview_frame = ttk.LabelFrame(parent, text="Markdown Preview", padding="10")
    preview_frame.grid(row=0, column=1, rowspan=4, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(10, 0))
    preview_frame.columnconfigure(0, weight=1)
    preview_frame.rowconfigure(0, weight=1)
    
    tk_vars["preview_text"] = scrolledtext.ScrolledText(preview_frame, wrap=tk.WORD, height=20, 
                                                        state=tk.DISABLED, width=60)
    tk_vars["preview_text"].grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    # Configure text tags for markdown formatting
    tk_vars["preview_text"].tag_config("h1", font=("", 16, "bold"), spacing3=10)
    tk_vars["preview_text"].tag_config("h2", font=("", 14, "bold"), spacing3=8)
    tk_vars["preview_text"].tag_config("h3", font=("", 12, "bold"), spacing3=6)
    tk_vars["preview_text"].tag_config("bold", font=("", 10, "bold"))
    tk_vars["preview_text"].tag_config("italic", font=("", 10, "italic"))
    tk_vars["preview_text"].tag_config("code", font=("Courier", 10), background="#f0f0f0")
    tk_vars["preview_text"].tag_config("link", foreground="blue", underline=1)
    tk_vars["preview_text"].tag_config("list", lmargin1=20, lmargin2=20)
    
    # Initially hide preview frame
    preview_frame.grid_remove()
    tk_vars["preview_frame"] = preview_frame
    
    # Try to populate dropdown from existing file
    _try_populate_from_existing_file(tk_vars)


def _browse_convert_input(tk_vars):
    """Browse for conversion input file"""
    filename = filedialog.askopenfilename(
        title="Select input JSON file",
        initialdir=Path(__file__).parent / "output",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
    )
    if filename:
        # Store absolute path so script can find it regardless of working directory
        tk_vars["convert_input"].set(str(Path(filename).resolve()))
        # Try to populate dropdown from selected file
        _try_populate_from_existing_file(tk_vars)


def _browse_convert_output(tk_vars):
    """Browse for conversion output file"""
    # Allow selecting existing file or entering new filename
    filename = filedialog.askopenfilename(
        title="Select output file (or cancel to create new)",
        initialdir=Path(__file__).parent / "output",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
    )
    if filename:
        # Store absolute path so script can find it regardless of working directory
        tk_vars["convert_output"].set(str(Path(filename).resolve()))
        # Try to populate dropdown from selected file if it exists
        _try_populate_from_existing_file(tk_vars)
    else:
        # If cancelled, offer save dialog to create new file
        filename = filedialog.asksaveasfilename(
            title="Create new output file",
            initialdir=Path(__file__).parent / "output",
            initialfile="fab_metadata_converted.json",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            tk_vars["convert_output"].set(str(Path(filename).resolve()))
            _try_populate_from_existing_file(tk_vars)


def _start_conversion(tk_vars):
    """Start the HTML to Markdown conversion process"""
    try:
        workers = int(tk_vars["convert_workers"].get())
        if workers < 1:
            raise ValueError("Workers must be >= 1")
    except ValueError as e:
        _log_convert(f"Error: {e}", "error", tk_vars)
        return
    
    # Handle both absolute and relative paths for input file
    input_file_str = tk_vars["convert_input"].get()
    input_file = Path(input_file_str)
    if not input_file.is_absolute():
        input_file = Path(__file__).parent / input_file_str
    
    if not input_file.exists():
        _log_convert(f"Error: Input file not found: {input_file}", "error", tk_vars)
        return
    
    if not _state["converter_path"].exists():
        _log_convert(f"Error: Converter script not found at {_state['converter_path']}", "error", tk_vars)
        return
    
    tk_vars["convert_button"].config(state=tk.DISABLED)
    _update_convert_status("Running...", "orange", tk_vars)
    
    cmd = [sys.executable, str(_state["converter_path"]), str(input_file)]
    
    output_file_str = tk_vars["convert_output"].get().strip()
    if output_file_str:
        # Handle both absolute and relative paths for output file
        output_file = Path(output_file_str)
        if not output_file.is_absolute():
            output_file = Path(__file__).parent / output_file_str
        cmd.extend(["-o", str(output_file)])
    
    cmd.extend(["-w", str(workers)])
    
    _log_convert("Starting conversion with command:", "info", tk_vars)
    _log_convert(" ".join(cmd), "info", tk_vars)
    _log_convert("-" * 80, None, tk_vars)
    
    thread = threading.Thread(target=_run_conversion, args=(cmd, tk_vars), daemon=True)
    thread.start()


def _run_conversion(cmd, tk_vars):
    """Run the conversion process"""
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=Path(__file__).parent,
            universal_newlines=True
        )
        
        while True:
            if process.poll() is not None:
                break
            
            if process.stderr:
                line = process.stderr.readline()
                if line:
                    _log_convert(line.rstrip(), None, tk_vars)
        
        if process.stderr:
            remaining = process.stderr.read()
            if remaining:
                for line in remaining.splitlines():
                    _log_convert(line, None, tk_vars)
        
        if process.stdout:
            remaining = process.stdout.read()
            if remaining:
                for line in remaining.splitlines():
                    _log_convert(line, None, tk_vars)
        
        exit_code = process.returncode
        if exit_code == 0:
            _log_convert("-" * 80, None, tk_vars)
            _log_convert("Conversion completed successfully!", "success", tk_vars)
            _update_convert_status("Completed", "green", tk_vars)
            
            # Populate asset dropdown for preview
            output_file = tk_vars.get("convert_output", tk.StringVar()).get().strip()
            input_file = tk_vars.get("convert_input", tk.StringVar()).get()
            json_file = output_file if output_file else input_file
            _populate_asset_dropdown(tk_vars, json_file)
        else:
            _log_convert("-" * 80, None, tk_vars)
            _log_convert(f"Conversion failed with exit code {exit_code}", "error", tk_vars)
            _update_convert_status("Failed", "red", tk_vars)
    
    except Exception as e:
        _log_convert(f"Error running converter: {e}", "error", tk_vars)
        _update_convert_status("Error", "red", tk_vars)
    
    finally:
        _state["root"].after(0, lambda: tk_vars["convert_button"].config(state=tk.NORMAL))


def _log_convert(message, tag, tk_vars):
    """Add message to conversion log"""
    def update():
        log = tk_vars.get("convert_log")
        if log:
            log.config(state=tk.NORMAL)
            if tag:
                log.insert(tk.END, message + "\n", tag)
            else:
                log.insert(tk.END, message + "\n")
            log.see(tk.END)
            log.config(state=tk.DISABLED)
    
    _state["root"].after(0, update)


def _update_convert_status(text, color, tk_vars):
    """Update conversion status label"""
    _state["root"].after(0, lambda: tk_vars["convert_status_label"].config(text=text, foreground=color))


def _clear_convert_log(tk_vars):
    """Clear the conversion log text area"""
    log = tk_vars.get("convert_log")
    if log:
        log.config(state=tk.NORMAL)
        log.delete(1.0, tk.END)
        log.config(state=tk.DISABLED)


def _try_populate_from_existing_file(tk_vars):
    """Try to populate dropdown from existing file (output or input)"""
    output_file = tk_vars.get("convert_output", tk.StringVar()).get().strip()
    input_file = tk_vars.get("convert_input", tk.StringVar()).get()
    
    # Try output file first, then input file
    json_file = output_file if output_file else input_file
    
    if json_file:
        # Handle both absolute and relative paths
        json_path = Path(json_file)
        if not json_path.is_absolute():
            json_path = Path(__file__).parent / json_file
        
        if json_path.exists():
            # Check if file has markdown descriptions
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    assets = json.load(f)
                
                if isinstance(assets, list) and len(assets) > 0:
                    # Check if first asset has markdown (converted)
                    first_asset = assets[0]
                    if isinstance(first_asset, dict) and 'description' in first_asset:
                        description = first_asset.get('description', '')
                        # Check if description looks like markdown (has ## or # or **)
                        if any(marker in description for marker in ['##', '# ', '**', '- ']):
                            _populate_asset_dropdown(tk_vars, json_file)
            except:
                pass  # Silently fail, don't spam logs on tab load


def _populate_asset_dropdown(tk_vars, json_file_path):
    """Populate asset dropdown from JSON file"""
    try:
        # Handle both absolute and relative paths
        json_path = Path(json_file_path)
        if not json_path.is_absolute():
            json_path = Path(__file__).parent / json_file_path
        
        if not json_path.exists():
            _log_convert(f"Warning: Cannot populate preview - file not found: {json_path}", "warning", tk_vars)
            return
        
        with open(json_path, 'r', encoding='utf-8') as f:
            assets = json.load(f)
        
        if not isinstance(assets, list):
            _log_convert("Warning: Cannot populate preview - JSON is not an array", "warning", tk_vars)
            return
        
        # Extract titles and store asset data
        asset_titles = []
        tk_vars["preview_assets"] = []
        
        for asset in assets:
            if isinstance(asset, dict) and 'title' in asset:
                title = asset['title']
                fab_id = asset.get('fab_id', '')
                asset_titles.append(title)
                tk_vars["preview_assets"].append((title, fab_id, asset))
        
        if asset_titles:
            tk_vars["preview_dropdown"]["values"] = asset_titles
            _log_convert(f"Preview ready: Loaded {len(asset_titles)} assets", "success", tk_vars)
        else:
            _log_convert("Warning: No assets found in JSON file", "warning", tk_vars)
    
    except json.JSONDecodeError as e:
        _log_convert(f"Error: Invalid JSON in {json_file_path}: {e}", "error", tk_vars)
    except Exception as e:
        _log_convert(f"Error loading assets for preview: {e}", "error", tk_vars)


def _toggle_preview(tk_vars):
    """Toggle preview column visibility"""
    preview_frame = tk_vars.get("preview_frame")
    preview_button = tk_vars.get("preview_button")
    
    if not preview_frame or not preview_button:
        return
    
    if tk_vars["preview_visible"]:
        # Hide preview
        preview_frame.grid_remove()
        preview_button.config(text="Show Preview")
        tk_vars["preview_visible"] = False
    else:
        # Show preview
        preview_frame.grid()
        preview_button.config(text="Hide Preview")
        tk_vars["preview_visible"] = True
        
        # Render current selection if any
        _on_asset_selected(tk_vars)


def _on_asset_selected(tk_vars):
    """Handle asset selection from dropdown"""
    dropdown = tk_vars.get("preview_dropdown")
    preview_button = tk_vars.get("preview_button")
    
    if not dropdown:
        return
    
    selected_title = dropdown.get()
    
    if selected_title:
        # Enable preview button
        if preview_button:
            preview_button.config(state=tk.NORMAL)
        
        # Render preview if visible
        if tk_vars.get("preview_visible", False):
            _render_markdown_preview(tk_vars, selected_title)


def _render_markdown_preview(tk_vars, selected_title):
    """Render markdown preview for selected asset"""
    preview_text = tk_vars.get("preview_text")
    
    if not preview_text:
        return
    
    # Find asset data
    asset_data = None
    for title, fab_id, data in tk_vars.get("preview_assets", []):
        if title == selected_title:
            asset_data = data
            break
    
    if not asset_data:
        return
    
    # Clear preview
    preview_text.config(state=tk.NORMAL)
    preview_text.delete(1.0, tk.END)
    
    # Get markdown description
    description = asset_data.get('description', '')
    
    if not description:
        preview_text.insert(tk.END, "No description available for this asset.")
        preview_text.config(state=tk.DISABLED)
        return
    
    # Parse and format markdown
    _parse_and_format_markdown(preview_text, description)
    
    preview_text.config(state=tk.DISABLED)


def _parse_and_format_markdown(text_widget, markdown_text):
    """Parse markdown and insert formatted text into widget"""
    if not markdown_text:
        return
    
    lines = markdown_text.split('\n')
    
    for line in lines:
        # Skip empty lines
        if not line.strip():
            text_widget.insert(tk.END, '\n')
            continue
        
        # Headings
        if line.startswith('### '):
            text_widget.insert(tk.END, line[4:] + '\n', 'h3')
        elif line.startswith('## '):
            text_widget.insert(tk.END, line[3:] + '\n', 'h2')
        elif line.startswith('# '):
            text_widget.insert(tk.END, line[2:] + '\n', 'h1')
        # Lists
        elif line.strip().startswith(('- ', '* ', '1. ', '2. ', '3. ', '4. ', '5. ', '6. ', '7. ', '8. ', '9. ')):
            _format_inline_text(text_widget, line, 'list')
            text_widget.insert(tk.END, '\n')
        # Regular text
        else:
            _format_inline_text(text_widget, line, None)
            text_widget.insert(tk.END, '\n')


def _format_inline_text(text_widget, line, base_tag=None):
    """Format inline markdown (bold, italic, links, code)"""
    import re
    
    pos = 0
    
    # Pattern for inline formatting: **bold**, *italic*, `code`, [text](url)
    pattern = r'(\*\*.*?\*\*|\*.*?\*|`.*?`|\[.*?\]\(.*?\))'
    
    parts = re.split(pattern, line)
    
    for part in parts:
        if not part:
            continue
        
        tags = [base_tag] if base_tag else []
        
        # Bold
        if part.startswith('**') and part.endswith('**') and len(part) > 4:
            text_widget.insert(tk.END, part[2:-2], ('bold',) + tuple(tags) if tags else 'bold')
        # Italic
        elif part.startswith('*') and part.endswith('*') and len(part) > 2 and not part.startswith('**'):
            text_widget.insert(tk.END, part[1:-1], ('italic',) + tuple(tags) if tags else 'italic')
        # Code
        elif part.startswith('`') and part.endswith('`') and len(part) > 2:
            text_widget.insert(tk.END, part[1:-1], ('code',) + tuple(tags) if tags else 'code')
        # Links [text](url)
        elif part.startswith('[') and '](' in part and part.endswith(')'):
            match = re.match(r'\[(.+?)\]\((.+?)\)', part)
            if match:
                link_text, url = match.groups()
                text_widget.insert(tk.END, link_text, ('link',) + tuple(tags) if tags else 'link')
        # Plain text
        else:
            text_widget.insert(tk.END, part, tuple(tags) if tags else ())
