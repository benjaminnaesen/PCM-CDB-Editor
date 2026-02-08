import tkinter as tk
import os
from tkinter import messagebox
from ui.ui_utils import ToolTip

class WelcomeScreen:
    def __init__(self, root_frame, app_state, load_callback):
        self.frame = root_frame
        self.state = app_state
        self.load_callback = load_callback

    def show(self):
        for widget in self.frame.winfo_children(): widget.destroy()
        self.frame.pack(fill=tk.BOTH, expand=True)
        
        container = tk.Frame(self.frame, bg="white", padx=40, pady=40, relief="raised", bd=1)
        container.place(relx=0.5, rely=0.5, anchor="center")
        
        tk.Label(container, text="PCM CDB Editor", font=("Segoe UI", 24, "bold"), bg="white", fg="#333").pack(pady=(0, 20))
        tk.Button(container, text="Open CDB File", command=lambda: self.load_callback(), font=("Segoe UI", 12), bg="#007acc", fg="white", relief="flat", padx=20, pady=8, cursor="hand2").pack(pady=10, fill=tk.X)
        
        if self.state.recents:
            tk.Label(container, text="Recent Projects", font=("Segoe UI", 10, "bold"), bg="white", fg="#777", anchor="w").pack(fill=tk.X, pady=(20, 5))
            for path in self.state.recents:
                display = f"{os.path.basename(os.path.dirname(path))}/{os.path.basename(path)}" if os.path.dirname(path) else path
                btn = tk.Button(container, text=display, command=lambda p=path: self.load_recent(p), anchor="w", relief="flat", bg="#f9f9f9", fg="#333", padx=10, pady=5, cursor="hand2")
                btn.pack(fill=tk.X, pady=1); ToolTip(btn, path)

    def load_recent(self, path):
        if not os.path.exists(path):
            messagebox.showerror("Error", f"File not found:\n{path}")
            if path in self.state.recents:
                self.state.recents.remove(path)
                self.show()
            return
        self.load_callback(path)

    def hide(self):
        self.frame.pack_forget()