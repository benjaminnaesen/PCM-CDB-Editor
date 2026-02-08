import tkinter as tk
from ui.editor_gui import CDBEditor

if __name__ == "__main__":
    root = tk.Tk()
    app = CDBEditor(root)
    root.mainloop()