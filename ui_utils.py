import tkinter as tk

class ToolTip:
    def __init__(self, widget, text):
        self.widget, self.text, self.tip_window = widget, text, None
        self.widget.bind("<Enter>", self.show_tip); self.widget.bind("<Leave>", self.hide_tip)
    def show_tip(self, event=None):
        if self.tip_window or not self.text: return
        x, y = self.widget.winfo_rootx() + 20, self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tip_window = tw = tk.Toplevel(self.widget); tw.wm_overrideredirect(True); tw.wm_geometry(f"+{x}+{y}")
        tk.Label(tw, text=self.text, justify=tk.LEFT, bg="#ffffe0", relief=tk.SOLID, bd=1, font=("tahoma", "8", "normal")).pack(ipadx=1)
    def hide_tip(self, event=None):
        if self.tip_window: self.tip_window.destroy(); self.tip_window = None