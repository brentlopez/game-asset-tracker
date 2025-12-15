#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Asset Scraper - Platform-Agnostic GUI

A unified GUI launcher for scraping metadata from various asset marketplaces.
Platforms are discovered via platforms.json and loaded dynamically.
"""
import tkinter as tk
from tkinter import ttk, messagebox
import json
import sys
import importlib
from pathlib import Path


class AssetScraperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Asset Scraper")
        self.root.geometry("900x750")
        
        # Load platform manifest
        self.platforms = self._load_platforms()
        self.current_platform = None
        self.current_module = None
        
        # Shared state for GUI modules
        self.tk_vars = {}
        
        self._setup_ui()
        
        # Load first enabled platform by default
        if self.platforms:
            self._switch_platform(self.platforms[0]["id"])
    
    def _load_platforms(self):
        """Load platform manifest from platforms.json"""
        manifest_path = Path(__file__).parent / "platforms.json"
        
        if not manifest_path.exists():
            messagebox.showerror("Error", f"Platform manifest not found: {manifest_path}")
            sys.exit(1)
        
        try:
            with open(manifest_path, 'r') as f:
                data = json.load(f)
                platforms = [p for p in data.get("platforms", []) if p.get("enabled", True)]
                
                if not platforms:
                    messagebox.showerror("Error", "No enabled platforms found in manifest")
                    sys.exit(1)
                
                return platforms
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load platform manifest: {e}")
            sys.exit(1)
    
    def _setup_ui(self):
        """Create the main UI layout"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Header with platform selector
        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        header_frame.columnconfigure(0, weight=1)
        
        ttk.Label(header_frame, text="Platform:", font=("", 10, "bold")).grid(row=0, column=1, padx=(10, 5))
        
        self.platform_var = tk.StringVar()
        platform_selector = ttk.Combobox(
            header_frame,
            textvariable=self.platform_var,
            values=[p["name"] for p in self.platforms],
            state="readonly",
            width=20
        )
        platform_selector.grid(row=0, column=2, sticky=tk.E)
        platform_selector.bind("<<ComboboxSelected>>", self._on_platform_changed)
        
        # Tab notebook
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Create tab frames
        self.setup_tab = ttk.Frame(self.notebook, padding="10")
        self.scraping_tab = ttk.Frame(self.notebook, padding="10")
        self.postprocess_tab = ttk.Frame(self.notebook, padding="10")
        
        self.notebook.add(self.setup_tab, text="Setup")
        self.notebook.add(self.scraping_tab, text="Scraping")
        self.notebook.add(self.postprocess_tab, text="Post-Processing")
        
        # Configure tab grid weights
        for tab in [self.setup_tab, self.scraping_tab, self.postprocess_tab]:
            tab.columnconfigure(0, weight=1)
            # Note: rowconfigure is handled by each platform's GUI module
    
    def _on_platform_changed(self, event=None):
        """Handle platform selection change"""
        platform_name = self.platform_var.get()
        platform = next((p for p in self.platforms if p["name"] == platform_name), None)
        
        if platform:
            self._switch_platform(platform["id"])
    
    def _switch_platform(self, platform_id):
        """Switch to a different platform"""
        platform = next((p for p in self.platforms if p["id"] == platform_id), None)
        
        if not platform:
            messagebox.showerror("Error", f"Platform not found: {platform_id}")
            return
        
        # Update selector
        self.platform_var.set(platform["name"])
        
        # Load platform module
        try:
            module_path = platform["gui_module"]
            module = importlib.import_module(module_path)
            
            # Verify module has required functions
            required_funcs = ["create_setup_tab", "create_scraping_tab", "create_postprocessing_tab"]
            for func_name in required_funcs:
                if not hasattr(module, func_name):
                    raise AttributeError(f"Module {module_path} missing required function: {func_name}")
            
            self.current_platform = platform
            self.current_module = module
            
            # Clear existing tab content
            self._clear_tab_content()
            
            # Render new tab content
            self._render_tabs()
            
        except ImportError as e:
            messagebox.showerror("Error", f"Failed to load platform module '{platform['gui_module']}': {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Error loading platform: {e}")
    
    def _clear_tab_content(self):
        """Clear all widgets from tabs"""
        for tab in [self.setup_tab, self.scraping_tab, self.postprocess_tab]:
            for widget in tab.winfo_children():
                widget.destroy()
    
    def _render_tabs(self):
        """Render tab content using current platform module"""
        if not self.current_module:
            return
        
        try:
            # Call platform module functions to render tabs
            self.current_module.create_setup_tab(self.setup_tab, self.tk_vars)
            self.current_module.create_scraping_tab(self.scraping_tab, self.tk_vars)
            self.current_module.create_postprocessing_tab(self.postprocess_tab, self.tk_vars)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to render tabs: {e}")


def main():
    root = tk.Tk()
    app = AssetScraperGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
