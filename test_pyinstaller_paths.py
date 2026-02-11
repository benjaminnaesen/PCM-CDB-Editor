"""
Test script to verify PyInstaller path resolution.
Run this after building with PyInstaller to verify paths are correct.
"""

import sys
import os

print("=== PyInstaller Path Diagnostic ===")
print(f"sys.frozen: {getattr(sys, 'frozen', False)}")
print(f"sys.executable: {sys.executable}")
if hasattr(sys, '_MEIPASS'):
    print(f"sys._MEIPASS: {sys._MEIPASS}")
else:
    print("sys._MEIPASS: NOT SET")

# Simulate the BASE_PATH logic from converter.py
if getattr(sys, 'frozen', False):
    base_dir = os.path.dirname(sys.executable)
    internal_path = os.path.join(base_dir, "_internal")
    BASE_PATH = internal_path if os.path.exists(internal_path) else base_dir
    print(f"\nbase_dir: {base_dir}")
    print(f"_internal exists: {os.path.exists(internal_path)}")
    print(f"BASE_PATH (frozen): {BASE_PATH}")
else:
    BASE_PATH = os.path.dirname(os.path.abspath(__file__))
    print(f"\nBASE_PATH (source): {BASE_PATH}")

TOOL_PATH = os.path.join(BASE_PATH, "SQLiteExporter", "SQLiteExporter.exe")
print(f"TOOL_PATH: {TOOL_PATH}")
print(f"TOOL_PATH exists: {os.path.exists(TOOL_PATH)}")

# List contents of BASE_PATH
print(f"\nContents of BASE_PATH:")
if os.path.exists(BASE_PATH):
    for item in os.listdir(BASE_PATH):
        item_path = os.path.join(BASE_PATH, item)
        item_type = "DIR" if os.path.isdir(item_path) else "FILE"
        print(f"  [{item_type}] {item}")

        # If SQLiteExporter folder found, list its contents
        if item == "SQLiteExporter" and os.path.isdir(item_path):
            print(f"\n  Contents of SQLiteExporter/:")
            for subitem in os.listdir(item_path):
                print(f"    - {subitem}")
else:
    print(f"  BASE_PATH does not exist!")

print("\n=== End Diagnostic ===")
