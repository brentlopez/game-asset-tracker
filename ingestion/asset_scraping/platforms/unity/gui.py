#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unity Platform GUI Module

Provides Setup, Scraping, and Post-Processing tabs for the Unity Asset Store scraper.
This module is dynamically loaded by the main asset_scraper.py application.
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import subprocess
import threading
import sys
from pathlib import Path


# Module-level state (shared across functions)
_state = {
    "process": None,
    "is_running": False,
    "script_path": Path(__file__).parent / "scraping" / "scrape_unity_metadata.py",
    "auth_script_path": Path(__file__).parent / "setup" / "generate_unity_auth.py",
    "auth_file_path": Path(__file__).parent / "setup" / "auth.json",
    "root": None
}


def create_setup_tab(parent, tk_vars):
    """Render Setup tab content for Unity authentication"""
    parent.columnconfigure(0, weight=1)
    parent.rowconfigure(2, weight=1)
    
    # Header
    header_frame = ttk.LabelFrame(parent, text="Unity Asset Store Authentication", padding="10")
    header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N), pady=(0, 10))
    header_frame.columnconfigure(0, weight=1)
    
    ttk.Label(header_frame, text="Before scraping, you need to authenticate with Unity Asset Store.").grid(row=0, column=0, sticky=tk.W, pady=5)
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
    """Render Scraping tab content for Unity metadata scraping"""
    _state["root"] = parent.winfo_toplevel()
    
    parent.columnconfigure(0, weight=1)
    parent.rowconfigure(3, weight=1)
    
    # Instructions
    instructions_frame = ttk.LabelFrame(parent, text="Instructions", padding="10")
    instructions_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N), pady=(0, 10))
    instructions_frame.columnconfigure(0, weight=1)
    
    ttk.Label(instructions_frame, text="This will scrape metadata from all assets in your Unity Asset Store library.").grid(row=0, column=0, sticky=tk.W, pady=2)
    ttk.Label(instructions_frame, text="Make sure you've authenticated in the Setup tab before scraping.").grid(row=1, column=0, sticky=tk.W, pady=2)
    ttk.Label(instructions_frame, text="⚠ This may take several minutes for large libraries.", foreground="orange", font=("", 9, "bold")).grid(row=2, column=0, sticky=tk.W, pady=(10, 2))
    
    # Options
    options_frame = ttk.LabelFrame(parent, text="Options", padding="10")
    options_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N), pady=(0, 10))
    
    tk_vars["headless"] = tk.BooleanVar(value=False)
    tk_vars["output_file"] = tk.StringVar(value="output/unity_metadata.json")
    
    ttk.Checkbutton(options_frame, text="Headless mode (browser runs in background)", variable=tk_vars["headless"]).grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
    
    ttk.Label(options_frame, text="Output file:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
    ttk.Entry(options_frame, textvariable=tk_vars["output_file"], width=40).grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
    
    # Control Buttons
    control_frame = ttk.Frame(parent)
    control_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
    
    tk_vars["start_button"] = ttk.Button(control_frame, text="Start Scraping", command=lambda: _start_scraping(tk_vars))
    tk_vars["start_button"].pack(side=tk.LEFT, padx=5)
    
    tk_vars["stop_button"] = ttk.Button(control_frame, text="Stop", command=lambda: _stop_scraping(tk_vars), state=tk.DISABLED)
    tk_vars["stop_button"].pack(side=tk.LEFT, padx=5)
    
    ttk.Button(control_frame, text="Clear Log", command=lambda: _clear_log(tk_vars)).pack(side=tk.LEFT, padx=5)
    
    tk_vars["status_label"] = ttk.Label(control_frame, text="Ready", foreground="green")
    tk_vars["status_label"].pack(side=tk.LEFT, padx=20)
    
    # Log Output
    log_frame = ttk.LabelFrame(parent, text="Log Output", padding="10")
    log_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 0))
    log_frame.columnconfigure(0, weight=1)
    log_frame.rowconfigure(0, weight=1)
    
    tk_vars["log_text"] = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=20, state=tk.DISABLED)
    tk_vars["log_text"].grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    tk_vars["log_text"].tag_config("error", foreground="red")
    tk_vars["log_text"].tag_config("warning", foreground="orange")
    tk_vars["log_text"].tag_config("success", foreground="green")
    tk_vars["log_text"].tag_config("info", foreground="blue")


def _start_scraping(tk_vars):
    """Start the scraping process"""
    if _state["is_running"]:
        return
    
    # Check if auth exists
    if not _state["auth_file_path"].exists():
        _log("Error: auth.json not found. Please authenticate in the Setup tab first.", "error", tk_vars)
        messagebox.showerror("Authentication Required", "Please authenticate in the Setup tab before scraping.")
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
    cmd = [sys.executable, str(_state["script_path"])]
    if tk_vars["headless"].get():
        cmd.append("--headless")
    cmd.extend(["--output", tk_vars["output_file"].get()])
    
    _log("Starting Unity scraper with command:", "info", tk_vars)
    _log(" ".join(cmd), "info", tk_vars)
    _log("-" * 80, None, tk_vars)
    
    # Start scraping in background thread
    thread = threading.Thread(target=_run_scraping, args=(cmd, tk_vars), daemon=True)
    thread.start()


def _run_scraping(cmd, tk_vars):
    """Run the scraping process"""
    try:
        _state["process"] = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=_state["script_path"].parent,
            universal_newlines=True
        )
        
        # Read output in real-time
        while True:
            if _state["process"].poll() is not None:
                break
            
            if _state["process"].stderr:
                line = _state["process"].stderr.readline()
                if line:
                    _log(line.rstrip(), None, tk_vars)
            
            if _state["process"].stdout:
                line = _state["process"].stdout.readline()
                if line:
                    _log(line.rstrip(), None, tk_vars)
        
        # Read remaining output
        if _state["process"].stderr:
            remaining = _state["process"].stderr.read()
            if remaining:
                for line in remaining.splitlines():
                    _log(line, None, tk_vars)
        
        if _state["process"].stdout:
            remaining = _state["process"].stdout.read()
            if remaining:
                for line in remaining.splitlines():
                    _log(line, None, tk_vars)
        
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
            _state["process"].terminate()
            try:
                _state["process"].wait(timeout=3)
                _log("Scraper terminated gracefully", "warning", tk_vars)
            except subprocess.TimeoutExpired:
                _log("Force killing scraper...", "error", tk_vars)
                _state["process"].kill()
                _log("Scraper force killed", "error", tk_vars)
        except Exception as e:
            _log(f"Error stopping scraper: {e}", "error", tk_vars)
        
        _update_status("Stopped", "orange", tk_vars)
    
    _cleanup_process(tk_vars)


def _cleanup_process(tk_vars):
    """Clean up after process finishes"""
    _state["is_running"] = False
    _state["process"] = None
    
    _state["root"].after(0, lambda: tk_vars["start_button"].config(state=tk.NORMAL))
    _state["root"].after(0, lambda: tk_vars["stop_button"].config(state=tk.DISABLED))


def _update_status(text, color, tk_vars):
    """Update status label"""
    _state["root"].after(0, lambda: tk_vars["status_label"].config(text=text, foreground=color))


def _log(message, tag, tk_vars):
    """Add message to log"""
    def update():
        log = tk_vars.get("log_text")
        if log:
            log.config(state=tk.NORMAL)
            if tag:
                log.insert(tk.END, message + "\n", tag)
            else:
                log.insert(tk.END, message + "\n")
            log.see(tk.END)
            log.config(state=tk.DISABLED)
    
    _state["root"].after(0, update)


def _clear_log(tk_vars):
    """Clear the log text area"""
    log = tk_vars.get("log_text")
    if log:
        log.config(state=tk.NORMAL)
        log.delete(1.0, tk.END)
        log.config(state=tk.DISABLED)


def create_postprocessing_tab(parent, tk_vars):
    """Render Post-Processing tab content for Unity"""
    parent.columnconfigure(0, weight=1)
    parent.rowconfigure(0, weight=1)
    
    # Placeholder content
    placeholder_frame = ttk.LabelFrame(parent, text="Post-Processing", padding="20")
    placeholder_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    placeholder_frame.columnconfigure(0, weight=1)
    placeholder_frame.rowconfigure(0, weight=1)
    
    info_frame = ttk.Frame(placeholder_frame)
    info_frame.grid(row=0, column=0)
    
    ttk.Label(info_frame, text="Post-Processing", font=("", 14, "bold")).pack(pady=(0, 20))
    ttk.Label(info_frame, text="Post-processing features for Unity Asset Store metadata").pack(pady=5)
    ttk.Label(info_frame, text="are not yet implemented.", foreground="gray").pack(pady=5)
    ttk.Label(info_frame, text="").pack(pady=10)
    ttk.Label(info_frame, text="Future features may include:", font=("", 10, "bold")).pack(pady=(20, 10))
    ttk.Label(info_frame, text="• HTML to Markdown conversion", foreground="gray").pack(anchor=tk.W, padx=50)
    ttk.Label(info_frame, text="• Metadata enrichment", foreground="gray").pack(anchor=tk.W, padx=50)
    ttk.Label(info_frame, text="• Data validation", foreground="gray").pack(anchor=tk.W, padx=50)
