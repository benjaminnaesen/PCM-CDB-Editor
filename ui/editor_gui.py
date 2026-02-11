"""
Main application window and controller.

Coordinates all UI components, manages file operations,
and handles application lifecycle.
"""

import tkinter as tk
from tkinter import filedialog, ttk, messagebox, simpledialog
import gc, os, sys
from core.db_manager import DatabaseManager
from core.app_state import AppState
from core.constants import SEARCH_DEBOUNCE_DELAY
import core.converter as converter
import core.csv_io as csv_io
from ui.welcome_screen import WelcomeScreen
from ui.ui_utils import run_async
from ui.sidebar import Sidebar
from ui.table_view import TableView
from ui.column_manager_dialog import ColumnManagerDialog

class CDBEditor:
    """
    Main application controller for PCM CDB Editor.

    Manages:
        - Welcome screen and editor frame switching
        - CDB file loading/saving via SQLiteExporter
        - Menu and toolbar actions
        - Undo/redo coordination
        - Search with debouncing
        - Lookup mode toggle
        - CSV import/export operations
        - Application settings persistence
    """

    def __init__(self, root):
        """
        Initialize main application window.

        Args:
            root: Tkinter root window
        """
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
        self.search_timer = None

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

        # Career submenu
        self.career_menu = tk.Menu(self.tools_menu, tearoff=0)
        self.career_menu.add_command(label="Change team budget...", command=self.change_team_budget)
        self.tools_menu.add_cascade(label="Career", menu=self.career_menu)

        # Export submenu
        self.export_menu = tk.Menu(self.tools_menu, tearoff=0)
        self.export_menu.add_command(label="Export table to CSV...", command=self.export_csv)
        self.export_menu.add_command(label="Import table from CSV...", command=self.import_csv_table)
        self.export_menu.add_separator()
        self.export_menu.add_command(label="Export all tables to folder...", command=self.export_all_csv)
        self.export_menu.add_command(label="Import all tables from folder...", command=self.import_all_csv)
        self.tools_menu.add_cascade(label="Export", menu=self.export_menu)

        self.tools_btn.config(menu=self.tools_menu)

        self.undo_btn = tk.Button(toolbar, text="↶ Undo", command=self.undo, state="disabled")
        self.undo_btn.pack(side=tk.LEFT, padx=5)
        self.redo_btn = tk.Button(toolbar, text="↷ Redo", command=self.redo, state="disabled")
        self.redo_btn.pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="Add Row", command=lambda: self.table_view.add_row(), width=12).pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="Remove Row", command=lambda: self.table_view.delete_row(), width=12).pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="Clear Table", command=self.clear_table, width=12).pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self.on_search)
        self._create_search_box(toolbar, self.search_var, 40).pack(side=tk.RIGHT, padx=15)
        self.lookup_var = tk.BooleanVar(value=self.state.settings.get("lookup_mode", False))
        self.lookup_btn = tk.Button(toolbar, text="Lookup: ON" if self.lookup_var.get() else "Lookup: OFF", command=self.toggle_lookup, width=12)
        self.lookup_btn.pack(side=tk.RIGHT, padx=5)
        tk.Button(toolbar, text="Columns", command=self.open_column_manager, width=10).pack(side=tk.RIGHT, padx=5)
        self.tools_btn.pack(side=tk.RIGHT, padx=5)

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
        # Cancel previous search timer if user is still typing
        if self.search_timer:
            self.root.after_cancel(self.search_timer)

        # Schedule new search after delay
        self.search_timer = self.root.after(SEARCH_DEBOUNCE_DELAY, self._execute_search)

    def _execute_search(self):
        self.table_view.set_search_term(self.search_var.get())
        self.search_timer = None

    def toggle_lookup(self):
        new_state = not self.lookup_var.get()
        self.lookup_var.set(new_state)
        self.lookup_btn.config(text="Lookup: ON" if new_state else "Lookup: OFF")
        self.table_view.set_lookup_mode(new_state)

    def on_data_change(self):
        self.unsaved_changes = True
        self._update_btns()

    def undo(self):
        action = self.state.undo()
        if not action: return
        
        if action.get("type") == "row_op":
            self._handle_row_op(action, is_undo=True)
        else:
            self.db.update_cell(action["table"], action["column"], action["old"], self.table_view.tree["columns"][0], action["pk"])
            self.unsaved_changes = True; self.table_view.load_table_data()
        self._update_btns()

    def redo(self):
        action = self.state.redo()
        if not action: return
        
        if action.get("type") == "row_op":
            self._handle_row_op(action, is_undo=False)
        else:
            self.db.update_cell(action["table"], action["column"], action["new"], self.table_view.tree["columns"][0], action["pk"])
            self.unsaved_changes = True; self.table_view.load_table_data()
        self._update_btns()

    def _handle_row_op(self, action, is_undo):
        table = action["table"]
        mode = action["mode"]
        rows = action["rows"]
        pk_col = action["pk_col"]
        columns = action["columns"]

        # Determine effective operation
        # Undo Insert -> Delete | Redo Insert -> Insert
        # Undo Delete -> Insert | Redo Delete -> Delete
        effective_op = "delete" if (mode == "insert" and is_undo) or (mode == "delete" and not is_undo) else "insert"

        try:
            if effective_op == "delete":
                self.db.delete_rows(table, pk_col, [r["pk"] for r in rows])
            else:
                for r in rows:
                    self.db.insert_row(table, columns, r["data"])

            self.unsaved_changes = True
            self.table_view.load_table_data()
        except Exception as e:
            operation = "undo" if is_undo else "redo"
            messagebox.showerror("Error", f"Failed to {operation} operation: {str(e)}")

    def _update_btns(self):
        self.undo_btn.config(state="normal" if self.state.undo_stack else "disabled")
        self.redo_btn.config(state="normal" if self.state.redo_stack else "disabled")

    def close_cdb(self):
        if self.unsaved_changes:
            if not messagebox.askyesno("Unsaved Changes", "You have unsaved changes. Are you sure you want to close?"): return
        self.db = None; self.current_table = None; self.unsaved_changes = False
        self.table_view.set_db(None)
        self.tools_menu.entryconfig("Career", state="disabled")
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
            self.table_view.set_db(self.db)
            self.table_view.set_lookup_mode(self.lookup_var.get())
            self.sidebar.select_first_favorite()
            self.state.add_recent(path)
            self._update_career_menu_state()
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
            def on_complete(_):
                self.unsaved_changes = False
                self.status.config(text=f"Saved: {path}")
            run_async(self.root, task, on_complete, "Saving CDB...")

    def export_csv(self):
        if not self.db: return
        if not self.table_view.current_table: return messagebox.showwarning("Warning", "No table selected.")

        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")], initialfile=f"{self.table_view.current_table}.csv")
        if path:
            table_name = self.table_view.current_table
            run_async(self.root, lambda: csv_io.export_table(self.temp_path, table_name, path),
                     lambda _: self.status.config(text=f"Exported table '{table_name}' to CSV"),
                     "Exporting CSV...")

    def import_csv_table(self):
        if not self.db: return
        if not self.table_view.current_table: return messagebox.showwarning("Warning", "No table selected.")

        path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if path:
            if not messagebox.askyesno("Confirm Import", f"This will overwrite data in '{self.table_view.current_table}' with data from the CSV. Continue?"): return

            table_name = self.table_view.current_table
            def on_complete(_):
                self.unsaved_changes = True
                self.table_view.load_table_data()
                self.status.config(text=f"Imported CSV data into table '{table_name}'")
            run_async(self.root, lambda: csv_io.import_table_from_csv(self.temp_path, table_name, path), on_complete, "Importing CSV...")

    def export_all_csv(self):
        if not self.db: return

        folder = filedialog.askdirectory(title="Select folder to export all tables")
        if folder:
            run_async(self.root, lambda: csv_io.export_to_csv(self.temp_path, folder),
                     lambda _: self.status.config(text=f"Successfully exported all tables to folder"),
                     "Exporting all tables...")

    def import_all_csv(self):
        if not self.db: return

        folder = filedialog.askdirectory(title="Select folder containing CSV files")
        if folder:
            if not messagebox.askyesno("Confirm Import",
                                      "This will overwrite data in ALL matching tables with data from CSV files in the selected folder. Continue?"):
                return

            def on_complete(_):
                self.unsaved_changes = True
                if self.table_view.current_table:
                    self.table_view.load_table_data()
                self.status.config(text=f"Successfully imported all matching tables from folder")

            run_async(self.root, lambda: csv_io.import_from_csv(self.temp_path, folder), on_complete, "Importing all tables...")

    def _update_career_menu_state(self):
        """Enable or disable Career menu based on GAM_career_data table existence."""
        if self.db and "GAM_career_data" in self.all_tables:
            self.tools_menu.entryconfig("Career", state="normal")
        else:
            self.tools_menu.entryconfig("Career", state="disabled")

    def change_team_budget(self):
        """Open dialog to change team budget from GAM_career_data table."""
        if not self.db:
            return

        try:
            # Fetch current budget value for UID = 1 using direct SQL
            import sqlite3
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()

                # Get table schema
                cursor.execute("PRAGMA table_info([GAM_career_data])")
                columns = [col[1] for col in cursor.fetchall()]

                if "value" not in columns:
                    messagebox.showerror("Error", "Column 'value' not found in GAM_career_data table")
                    return

                # Fetch the row with UID = 1
                cursor.execute("SELECT value FROM [GAM_career_data] WHERE UID = 1")
                row = cursor.fetchone()

                if not row:
                    messagebox.showerror("Error", "No career data found (UID = 1 not found in GAM_career_data)")
                    return

                current_value = row[0]

            # Open input dialog
            new_value = simpledialog.askinteger(
                "Change Team Budget",
                "Enter new team budget:",
                initialvalue=current_value,
                minvalue=0,
                parent=self.root
            )

            if new_value is not None:  # User clicked OK (not Cancel)
                # Update the database
                self.db.update_cell("GAM_career_data", "value", new_value, "UID", 1)
                self.unsaved_changes = True

                # Refresh table if it's currently displayed
                if self.table_view.current_table == "GAM_career_data":
                    self.table_view.load_table_data()

                self.status.config(text=f"Team budget updated to {new_value}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to update budget: {str(e)}")

    def open_column_manager(self):
        """Open the column manager dialog."""
        if not self.db or not self.table_view.current_table:
            messagebox.showwarning("No Table", "Please select a table first.")
            return
        ColumnManagerDialog(self.root, self.table_view, self.state)

    def clear_table(self):
        """Clear all rows from the current table."""
        if not self.db or not self.table_view.current_table:
            messagebox.showwarning("No Table", "Please select a table first.")
            return

        try:
            table_name = self.table_view.current_table
            total_rows = self.db.get_row_count(table_name)

            if total_rows == 0:
                messagebox.showinfo("Empty Table", "This table is already empty.")
                return

            if not messagebox.askyesno("Confirm Clear Table",
                                      f"This will delete ALL {total_rows} rows from '{table_name}'.\n\nThis action can be undone.\n\nContinue?"):
                return

            # Get all columns and primary key
            columns = self.db.get_columns(table_name)
            pk_col = columns[0]

            # Fetch ALL rows for undo (no limit)
            _, all_rows = self.db.fetch_data(table_name, limit=None)

            # Capture data for undo
            deleted_rows = []
            for row in all_rows:
                pk = row[0]
                data = list(self.db.get_row_data(table_name, pk_col, pk))
                if data:
                    deleted_rows.append({"pk": pk, "data": data})

            # Delete all rows
            pk_vals = [row[0] for row in all_rows]
            self.db.delete_rows(table_name, pk_col, pk_vals)

            # Push undo action
            if deleted_rows:
                action = {
                    "type": "row_op",
                    "mode": "delete",
                    "table": table_name,
                    "pk_col": pk_col,
                    "columns": columns,
                    "rows": deleted_rows
                }
                self.state.push_action(action)

            self.unsaved_changes = True
            self.table_view.load_table_data()
            self._update_btns()
            self.status.config(text=f"Cleared {len(deleted_rows)} rows from '{table_name}'")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to clear table: {str(e)}")

    def on_close(self):
        if self.unsaved_changes:
            if not messagebox.askyesno("Unsaved Changes", "You have unsaved changes. Are you sure you want to exit?"): return
        is_maximized = False
        try: is_maximized = self.root.state() == 'zoomed' if sys.platform.startswith('win') else self.root.attributes('-zoomed')
        except: pass
        self.state.save_settings(self.normal_geometry, is_maximized, self.lookup_var.get()); self.root.destroy()