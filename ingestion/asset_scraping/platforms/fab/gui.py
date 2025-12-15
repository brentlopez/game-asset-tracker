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
    
    parent.columnconfigure(0, weight=1)
    parent.rowconfigure(4, weight=1)
    
    # Initialize variables
    _init_scraping_vars(tk_vars)
    
    # Build UI sections
    _create_scraping_options(parent, tk_vars)
    _create_scraping_parameters(parent, tk_vars)
    _create_scraping_controls(parent, tk_vars)
    _create_scraping_progress(parent, tk_vars)
    _create_scraping_log(parent, tk_vars)
    
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


def _create_scraping_options(parent, tk_vars):
    """Create scraping options section"""
    flags_frame = ttk.LabelFrame(parent, text="Options", padding="10")
    flags_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N), pady=(0, 10))
    flags_frame.columnconfigure(0, weight=1)
    flags_frame.columnconfigure(1, weight=1)
    
    ttk.Checkbutton(flags_frame, text="Headless mode", variable=tk_vars["headless"]).grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
    ttk.Checkbutton(flags_frame, text="Clear cache before scraping", variable=tk_vars["clear_cache"]).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
    ttk.Checkbutton(flags_frame, text="Test scroll only (no scraping)", variable=tk_vars["test_scroll"]).grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
    ttk.Checkbutton(flags_frame, text="Skip library scrape (use URL file)", variable=tk_vars["skip_library"]).grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
    ttk.Checkbutton(flags_frame, text="Skip pages with captchas", variable=tk_vars["skip_captcha"]).grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
    ttk.Checkbutton(flags_frame, text="Force rescrape all URLs", variable=tk_vars["force_rescrape"]).grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
    ttk.Checkbutton(flags_frame, text="New browser per page (avoid captchas)", variable=tk_vars["new_browser"]).grid(row=3, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
    ttk.Checkbutton(flags_frame, text="Reuse one browser per worker (new context per URL)", variable=tk_vars["reuse_browser"]).grid(row=4, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
    ttk.Checkbutton(flags_frame, text="Randomize UA + viewport per context", variable=tk_vars["randomize_ua"]).grid(row=5, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
    ttk.Checkbutton(flags_frame, text="Use auth on listing pages (normally off)", variable=tk_vars["auth_on_listings"]).grid(row=6, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
    ttk.Checkbutton(flags_frame, text="Captcha backoff + retry once", variable=tk_vars["captcha_retry"]).grid(row=7, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
    ttk.Checkbutton(flags_frame, text="Block heavy resources (images/media/fonts/analytics)", variable=tk_vars["block_heavy"]).grid(row=8, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
    ttk.Checkbutton(flags_frame, text="Measure bytes (write JSONL report)", variable=tk_vars["measure_bytes"]).grid(row=9, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)


def _create_scraping_parameters(parent, tk_vars):
    """Create scraping parameters section"""
    params_frame = ttk.LabelFrame(parent, text="Parameters", padding="10")
    params_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N), pady=(0, 10))
    params_frame.columnconfigure(1, weight=1)
    
    row = 0
    ttk.Label(params_frame, text="Max scrolls:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
    ttk.Entry(params_frame, textvariable=tk_vars["max_scrolls"], width=15).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
    
    row += 1
    ttk.Label(params_frame, text="Scroll step (px):").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
    ttk.Entry(params_frame, textvariable=tk_vars["scroll_step"], width=15).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
    
    row += 1
    ttk.Label(params_frame, text="Scroll steps per round:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
    ttk.Entry(params_frame, textvariable=tk_vars["scroll_steps"], width=15).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
    
    row += 1
    ttk.Label(params_frame, text="Parallel workers (1=sequential):").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
    parallel_frame = ttk.Frame(params_frame)
    parallel_frame.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
    ttk.Entry(parallel_frame, textvariable=tk_vars["parallel"], width=10).pack(side=tk.LEFT)
    ttk.Label(parallel_frame, text="(2-10 recommended)", foreground="gray").pack(side=tk.LEFT, padx=(5, 0))
    
    row += 1
    ttk.Label(params_frame, text="Output file:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
    out_frame = ttk.Frame(params_frame)
    out_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
    out_frame.columnconfigure(0, weight=1)
    ttk.Entry(out_frame, textvariable=tk_vars["out_file"]).grid(row=0, column=0, sticky=(tk.W, tk.E))
    ttk.Button(out_frame, text="Browse", command=lambda: _browse_output_file(tk_vars), width=8).grid(row=0, column=1, padx=(5, 0))
    
    row += 1
    ttk.Label(params_frame, text="URL file (for --skip-library-scrape):").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
    url_frame = ttk.Frame(params_frame)
    url_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
    url_frame.columnconfigure(0, weight=1)
    ttk.Entry(url_frame, textvariable=tk_vars["url_file"]).grid(row=0, column=0, sticky=(tk.W, tk.E))
    ttk.Button(url_frame, text="Browse", command=lambda: _browse_url_file(tk_vars), width=8).grid(row=0, column=1, padx=(5, 0))
    
    row += 1
    ttk.Label(params_frame, text="Proxy list file:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
    proxy_frame = ttk.Frame(params_frame)
    proxy_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
    proxy_frame.columnconfigure(0, weight=1)
    ttk.Entry(proxy_frame, textvariable=tk_vars["proxy_file"]).grid(row=0, column=0, sticky=(tk.W, tk.E))
    ttk.Button(proxy_frame, text="Browse", command=lambda: _browse_proxy_file(tk_vars), width=8).grid(row=0, column=1, padx=(5, 0))
    
    row += 1
    ttk.Label(params_frame, text="Measure report (JSONL):").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
    meas_frame = ttk.Frame(params_frame)
    meas_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
    meas_frame.columnconfigure(0, weight=1)
    ttk.Entry(meas_frame, textvariable=tk_vars["measure_report"]).grid(row=0, column=0, sticky=(tk.W, tk.E))
    
    # Cadence
    row += 1
    ttk.Label(params_frame, text="Sleep min (ms):").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
    ttk.Entry(params_frame, textvariable=tk_vars["sleep_min"], width=10).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
    row += 1
    ttk.Label(params_frame, text="Sleep max (ms):").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
    ttk.Entry(params_frame, textvariable=tk_vars["sleep_max"], width=10).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
    row += 1
    ttk.Label(params_frame, text="Burst size:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
    ttk.Entry(params_frame, textvariable=tk_vars["burst_size"], width=10).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
    row += 1
    ttk.Label(params_frame, text="Burst sleep (ms):").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
    ttk.Entry(params_frame, textvariable=tk_vars["burst_sleep"], width=10).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)


def _create_scraping_controls(parent, tk_vars):
    """Create scraping control buttons"""
    control_frame = ttk.Frame(parent)
    control_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
    
    tk_vars["start_button"] = ttk.Button(control_frame, text="Start Scraping", command=lambda: _start_scraping(tk_vars))
    tk_vars["start_button"].pack(side=tk.LEFT, padx=5)
    
    tk_vars["stop_button"] = ttk.Button(control_frame, text="Stop", command=lambda: _stop_scraping(tk_vars), state=tk.DISABLED)
    tk_vars["stop_button"].pack(side=tk.LEFT, padx=5)
    
    ttk.Button(control_frame, text="Clear Log", command=lambda: _clear_log(tk_vars)).pack(side=tk.LEFT, padx=5)
    
    tk_vars["status_label"] = ttk.Label(control_frame, text="Ready", foreground="green")
    tk_vars["status_label"].pack(side=tk.LEFT, padx=20)


def _create_scraping_progress(parent, tk_vars):
    """Create progress bar section"""
    progress_frame = ttk.LabelFrame(parent, text="Progress", padding="10")
    progress_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
    progress_frame.columnconfigure(0, weight=1)
    
    tk_vars["progress_bar"] = ttk.Progressbar(progress_frame, variable=tk_vars["progress"], maximum=100, mode='determinate')
    tk_vars["progress_bar"].grid(row=0, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
    
    tk_vars["progress_label"] = ttk.Label(progress_frame, text="0 / 0 pages scraped")
    tk_vars["progress_label"].grid(row=1, column=0, sticky=tk.W, padx=5)


def _create_scraping_log(parent, tk_vars):
    """Create log output section"""
    log_frame = ttk.LabelFrame(parent, text="Log Output", padding="10")
    log_frame.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 0))
    log_frame.columnconfigure(0, weight=1)
    log_frame.rowconfigure(0, weight=1)
    
    tk_vars["log_text"] = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=20, state=tk.DISABLED)
    tk_vars["log_text"].grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    tk_vars["log_text"].tag_config("error", foreground="red")
    tk_vars["log_text"].tag_config("warning", foreground="orange")
    tk_vars["log_text"].tag_config("success", foreground="green")
    tk_vars["log_text"].tag_config("info", foreground="blue")


def _browse_output_file(tk_vars):
    """Browse for output file"""
    filename = filedialog.asksaveasfilename(
        title="Select output file",
        initialdir=Path(__file__).parent,
        initialfile=tk_vars["out_file"].get(),
        defaultextension=".json",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
    )
    if filename:
        tk_vars["out_file"].set(Path(filename).name)


def _browse_url_file(tk_vars):
    """Browse for URL file"""
    filename = filedialog.askopenfilename(
        title="Select URL file",
        initialdir=Path(__file__).parent,
        initialfile=tk_vars["url_file"].get(),
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
    )
    if filename:
        tk_vars["url_file"].set(Path(filename).name)


def _browse_proxy_file(tk_vars):
    """Browse for proxy file"""
    filename = filedialog.askopenfilename(
        title="Select proxy list file",
        initialdir=Path(__file__).parent,
        filetypes=[("Text files", "*.txt *.list"), ("All files", "*.*")]
    )
    if filename:
        tk_vars["proxy_file"].set(Path(filename).name)


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
    parent.rowconfigure(3, weight=1)
    
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


def _browse_convert_input(tk_vars):
    """Browse for conversion input file"""
    filename = filedialog.askopenfilename(
        title="Select input JSON file",
        initialdir=Path(__file__).parent,
        initialfile=tk_vars["convert_input"].get(),
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
    )
    if filename:
        tk_vars["convert_input"].set(Path(filename).name)


def _browse_convert_output(tk_vars):
    """Browse for conversion output file"""
    filename = filedialog.asksaveasfilename(
        title="Select output JSON file",
        initialdir=Path(__file__).parent,
        defaultextension=".json",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
    )
    if filename:
        tk_vars["convert_output"].set(Path(filename).name)


def _start_conversion(tk_vars):
    """Start the HTML to Markdown conversion process"""
    try:
        workers = int(tk_vars["convert_workers"].get())
        if workers < 1:
            raise ValueError("Workers must be >= 1")
    except ValueError as e:
        _log_convert(f"Error: {e}", "error", tk_vars)
        return
    
    input_file = Path(__file__).parent / tk_vars["convert_input"].get()
    if not input_file.exists():
        _log_convert(f"Error: Input file not found: {input_file}", "error", tk_vars)
        return
    
    if not _state["converter_path"].exists():
        _log_convert(f"Error: Converter script not found at {_state['converter_path']}", "error", tk_vars)
        return
    
    tk_vars["convert_button"].config(state=tk.DISABLED)
    _update_convert_status("Running...", "orange", tk_vars)
    
    cmd = [sys.executable, str(_state["converter_path"]), str(input_file)]
    
    output_file_name = tk_vars["convert_output"].get().strip()
    if output_file_name:
        output_file = Path(__file__).parent / output_file_name
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
