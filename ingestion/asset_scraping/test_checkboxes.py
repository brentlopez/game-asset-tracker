#!/usr/bin/env python3
"""Test script to verify checkbox rendering"""
import tkinter as tk
from tkinter import ttk

def test_checkboxes():
    root = tk.Tk()
    root.title("Checkbox Test")
    root.geometry("900x750")
    
    frame = ttk.Frame(root, padding="10")
    frame.pack(fill=tk.BOTH, expand=True)
    
    # Create Options section (simulating the fab gui)
    flags_frame = ttk.LabelFrame(frame, text="Options", padding="10")
    flags_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N), pady=(0, 10))
    flags_frame.columnconfigure(0, weight=1)
    flags_frame.columnconfigure(1, weight=1)
    
    # Create BooleanVars
    var1 = tk.BooleanVar(value=False)
    var2 = tk.BooleanVar(value=True)
    
    # Create checkboxes
    ttk.Checkbutton(flags_frame, text="Headless mode", variable=var1).grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
    ttk.Checkbutton(flags_frame, text="Clear cache", variable=var2).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
    ttk.Checkbutton(flags_frame, text="Test option 3", variable=var1).grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
    ttk.Checkbutton(flags_frame, text="Test option 4", variable=var2).grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
    
    # Add a label below to confirm layout
    ttk.Label(frame, text="If you see this and the checkboxes above, everything works!").grid(row=1, column=0, sticky=tk.W, pady=10)
    
    root.mainloop()

if __name__ == "__main__":
    test_checkboxes()
