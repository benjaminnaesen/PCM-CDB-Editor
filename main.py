import tkinter as tk
from editor_gui import CDBEditor

if __name__ == "__main__":
    root = tk.Tk()
    app = CDBEditor(root)
    root.mainloop()