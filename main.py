"""
PCM CDB Editor - Main entry point.

A desktop application for editing Pro Cycling Manager game database files.
"""

__version__ = "1.0.0"

import tkinter as tk
from ui.editor_gui import CDBEditor

if __name__ == "__main__":
    root = tk.Tk()
    app = CDBEditor(root)
    root.mainloop()