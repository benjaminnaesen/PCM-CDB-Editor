"""
PCM Database Tools - Main entry point.

A desktop application bundling modding tools for Pro Cycling Manager,
including a database editor and startlist generator.
"""

__version__ = "1.1.0"

import tkinter as tk
from ui.editor_gui import PCMDatabaseTools

if __name__ == "__main__":
    root = tk.Tk()
    app = PCMDatabaseTools(root)
    root.mainloop()
