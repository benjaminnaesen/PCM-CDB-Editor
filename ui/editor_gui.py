import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import gc, os, sys
from core.db_manager import DatabaseManager
from core.app_state import AppState
import core.converter as converter
import core.csv_io as csv_io
from ui.welcome_screen import WelcomeScreen
from ui.ui_utils import run_async
from ui.sidebar import Sidebar
from ui.table_view import TableView

class CDBEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("PCM CDB Editor")
        self.state = AppState("session_config.json")
        self.normal_geometry = self.state.settings.get("window_size", "1200x800")
        self.root.geometry(self.normal_geometry)
        
        if self.state.settings.get("is_maximized", False):
            try:
                if sys.platform.startswith('win'): self.root.state('zoomed')
                else: self.root.attributes('-zoomed', True)
            except: pass
        
        self.root.bind("<Configure>", self.track_window_size)
        self.db, self.temp_path, self.current_table = None, None, None
        self.unsaved_changes = False

        self._setup_ui()
        self.root.bind("<Control-z>", lambda e: self.undo())
        self.root.bind("<Control-y>", lambda e: self.redo())
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def track_window_size(self, event):
        try:
            is_maximized = self.root.state() == 'zoomed' if sys.platform.startswith('win') else self.root.attributes('-zoomed')
            if not is_maximized: self.normal_geometry = self.root.geometry()
        except: pass

    def _setup_ui(self):
        self.editor_frame = tk.Frame(self.root)
        self.welcome_frame = tk.Frame(self.root, bg="#f0f0f0")
        self.welcome_screen = WelcomeScreen(self.welcome_frame, self.state, self.load_cdb)

        toolbar = tk.Frame(self.editor_frame, pady=10, bg="#f0f0f0")
        toolbar.pack(side=tk.TOP, fill=tk.X)
        tk.Button(toolbar, text="Open CDB", command=self.load_cdb, width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="Close CDB", command=self.close_cdb, width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="Save As...", command=self.save_as_cdb, width=10).pack(side=tk.LEFT, padx=5)
        
        self.tools_btn = tk.Menubutton(toolbar, text="Tools", relief="raised", width=10)
        self.tools_menu = tk.Menu(self.tools_btn, tearoff=0)
        self.tools_menu.add_command(label="Export table to CSV...", command=self.export_csv)
        self.tools_menu.add_command(label="Import table from CSV...", command=self.import_csv_table)
        self.tools_btn.config(menu=self.tools_menu); self.tools_btn.pack(side=tk.LEFT, padx=5)

        self.undo_btn = tk.Button(toolbar, text="↶ Undo", command=self.undo, state="disabled")
        self.undo_btn.pack(side=tk.LEFT, padx=5)
        self.redo_btn = tk.Button(toolbar, text="↷ Redo", command=self.redo, state="disabled")
        self.redo_btn.pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self.on_search)
        self._create_search_box(toolbar, self.search_var, 40).pack(side=tk.RIGHT, padx=15)
        self.lookup_var = tk.BooleanVar(value=self.state.settings.get("lookup_mode", False))
        tk.Checkbutton(toolbar, text="Lookup Mode", variable=self.lookup_var, command=self.toggle_lookup).pack(side=tk.RIGHT, padx=5)

        self.pw = tk.PanedWindow(self.editor_frame, orient=tk.HORIZONTAL, sashwidth=4, bg="#ccc")
        self.pw.pack(expand=True, fill=tk.BOTH)

        sidebar_container = tk.Frame(self.pw, bg="#e1e1e1")
        self.pw.add(sidebar_container)
        self.sidebar = Sidebar(sidebar_container, self.state, self.on_table_select)

        self.table_frame = tk.Frame(self.pw)
        self.pw.add(self.table_frame)
        self.table_view = TableView(self.table_frame, self.state, self.on_data_change)
        
        self.status = tk.Label(self.editor_frame, text="Ready", bd=1, relief="sunken", anchor="w")
        self.status.pack(side=tk.BOTTOM, fill=tk.X)
        self.show_welcome_screen()

    def show_welcome_screen(self):
        self.editor_frame.pack_forget()
        self.welcome_screen.show()

    def on_search(self, *args):
        self.table_view.set_search_term(self.search_var.get())

    def toggle_lookup(self):
        self.table_view.set_lookup_mode(self.lookup_var.get())

    def on_data_change(self):
        self.unsaved_changes = True
        self._update_btns()

    def undo(self):
        action = self.state.undo()
        if action: 
            self.db.update_cell(action["table"], action["column"], action["old"], self.table_view.tree["columns"][0], action["pk"])
            self.unsaved_changes = True; self.table_view.load_table_data()
        self._update_btns()

    def redo(self):
        action = self.state.redo()
        if action: 
            self.db.update_cell(action["table"], action["column"], action["new"], self.table_view.tree["columns"][0], action["pk"])
            self.unsaved_changes = True; self.table_view.load_table_data()
        self._update_btns()

    def _update_btns(self):
        self.undo_btn.config(state="normal" if self.state.undo_stack else "disabled")
        self.redo_btn.config(state="normal" if self.state.redo_stack else "disabled")

    def close_cdb(self):
        if self.unsaved_changes:
            if not messagebox.askyesno("Unsaved Changes", "You have unsaved changes. Are you sure you want to close?"): return
        self.db = None; self.current_table = None; self.unsaved_changes = False
        self.table_view.set_db(None)
        gc.collect()
        self.editor_frame.pack_forget()
        self.welcome_screen.show()
        self.root.title("PCM CDB Editor")

    def load_cdb(self, path=None):
        if not path: path = filedialog.askopenfilename(initialdir=self.state.settings.get("last_path",""), filetypes=[("CDB files", "*.cdb")])
        if not path: return
        
        def task(): 
            gc.collect()
            return converter.export_cdb_to_sqlite(path)
        
        def on_success(temp_path):
            self.temp_path = temp_path
            self.db = DatabaseManager(self.temp_path); self.all_tables = self.db.get_table_list()
            self.sidebar.set_tables(self.all_tables); self.state.settings["last_path"] = os.path.dirname(path)
            self.sidebar.select_first_favorite()
            self.table_view.set_db(self.db)
            self.table_view.set_lookup_mode(self.lookup_var.get())
            self.state.add_recent(path)
            self.welcome_screen.hide()
            self.editor_frame.pack(fill=tk.BOTH, expand=True)
            self.status.config(text=f"Loaded: {path}")
            self.unsaved_changes = False

        run_async(self.root, task, on_success, "Opening CDB...")

    def _create_search_box(self, parent, var, width):
        frame = tk.Frame(parent, bg="white", highlightbackground="#ccc", highlightthickness=1)
        tk.Entry(frame, textvariable=var, width=width, relief="flat").pack(side="left", padx=5, fill="x", expand=True)
        tk.Button(frame, text="✕", command=lambda: var.set(""), relief="flat", bg="white", bd=0).pack(side="right")
        return frame

    def on_table_select(self, table_name):
        self.table_view.set_table(table_name)

    def save_as_cdb(self):
        path = filedialog.asksaveasfilename(defaultextension=".cdb", filetypes=[("CDB files", "*.cdb")])
        if path: 
            gc.collect()
            def task(): converter.import_sqlite_to_cdb(self.temp_path, path)
            run_async(self.root, task, lambda _: setattr(self, 'unsaved_changes', False), "Saving CDB...")

    def export_csv(self):
        if not self.db: return
        if not self.table_view.current_table: return messagebox.showwarning("Warning", "No table selected.")
        
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")], initialfile=f"{self.table_view.current_table}.csv")
        if path:
            run_async(self.root, lambda: csv_io.export_table(self.temp_path, self.table_view.current_table, path), lambda _: None, "Exporting CSV...")

    def import_csv_table(self):
        if not self.db: return
        if not self.table_view.current_table: return messagebox.showwarning("Warning", "No table selected.")
        
        path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if path:
            if not messagebox.askyesno("Confirm Import", f"This will overwrite data in '{self.table_view.current_table}' with data from the CSV. Continue?"): return
            
            def on_complete(_):
                self.unsaved_changes = True
                self.table_view.load_table_data()
            run_async(self.root, lambda: csv_io.import_table_from_csv(self.temp_path, self.table_view.current_table, path), on_complete, "Importing CSV...")

    def on_close(self):
        is_maximized = False
        try: is_maximized = self.root.state() == 'zoomed' if sys.platform.startswith('win') else self.root.attributes('-zoomed')
        except: pass
        self.state.save_settings(self.normal_geometry, is_maximized, self.lookup_var.get()); self.root.destroy()