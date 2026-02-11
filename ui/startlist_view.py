"""
Startlist generator view.

Full-frame view for converting saved HTML startlists from FirstCycling
or ProCyclingStats into PCM-compatible XML files.  Supports loading
team/cyclist data from CSV database folders or from an opened CDB file.
"""

import gc
import os
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

import core.converter as converter
from core.startlist import StartlistDatabase, StartlistParser, PCMXmlWriter
from ui.ui_utils import run_async

# databases/ folder next to main.py
DATABASES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'databases',
)


class StartlistView:
    """Full-frame startlist generator with database selector."""

    def __init__(self, parent_frame, root, go_home):
        """
        Args:
            parent_frame: tk.Frame to build the view inside
            root: The tk.Tk root window (for dialogs / update_idletasks)
            go_home: Callback to return to the home screen
        """
        self.frame = parent_frame
        self.root = root
        self.go_home = go_home
        self.parser = StartlistParser()
        self.writer = PCMXmlWriter()
        self.db = None
        self.temp_path = None

        self._build_ui()
        self._load_selected_db()

    def _build_ui(self):
        # Toolbar
        toolbar = tk.Frame(self.frame, pady=10, bg="#f0f0f0")
        toolbar.pack(side=tk.TOP, fill=tk.X)

        tk.Button(
            toolbar, text="Home", command=self._on_home, width=10,
        ).pack(side=tk.LEFT, padx=5)

        # Content area
        content = tk.Frame(self.frame, padx=16, pady=12)
        content.pack(fill='both', expand=True)

        # Database section
        db_frame = tk.LabelFrame(content, text="Database", padx=8, pady=8)
        db_frame.pack(fill='x', pady=(0, 8))
        db_row = tk.Frame(db_frame)
        db_row.pack(fill='x')

        tk.Label(db_row, text="Select database:").pack(side='left')

        # Scan databases/ folder for subfolders
        self._db_names = []
        if os.path.isdir(DATABASES_DIR):
            self._db_names = sorted(
                d for d in os.listdir(DATABASES_DIR)
                if os.path.isdir(os.path.join(DATABASES_DIR, d))
            )

        self.db_var = tk.StringVar()
        self.db_combo = ttk.Combobox(
            db_row, textvariable=self.db_var, values=self._db_names,
            state='readonly', width=30,
        )
        self.db_combo.pack(side='left', padx=(6, 0))
        self.db_combo.bind('<<ComboboxSelected>>', lambda e: self._load_selected_db())

        if self._db_names:
            self.db_combo.current(0)

        tk.Label(db_row, text="or").pack(side='left', padx=8)
        tk.Button(
            db_row, text="Open CDB...", command=self._load_cdb,
        ).pack(side='left')

        self.db_status = tk.Label(
            db_frame, text="", fg="#888", font=("Segoe UI", 9), anchor='w',
        )
        self.db_status.pack(fill='x', pady=(4, 0))

        # HTML file input
        file_frame = tk.LabelFrame(content, text="HTML startlist file",
                                   padx=8, pady=8)
        file_frame.pack(fill='x', pady=(0, 8))
        row = tk.Frame(file_frame)
        row.pack(fill='x')

        self.file_var = tk.StringVar()
        tk.Entry(row, textvariable=self.file_var, width=60).pack(
            side='left', fill='x', expand=True)
        tk.Button(row, text="Browse...", command=self._browse_file).pack(
            side='left', padx=(6, 0))

        # Output file
        out_frame = tk.LabelFrame(content, text="Output XML file",
                                  padx=8, pady=8)
        out_frame.pack(fill='x', pady=(0, 8))
        out_row = tk.Frame(out_frame)
        out_row.pack(fill='x')

        self.out_var = tk.StringVar(value="startlist.xml")
        tk.Entry(out_row, textvariable=self.out_var, width=60).pack(
            side='left', fill='x', expand=True)
        tk.Button(out_row, text="Save as...",
                  command=self._browse_output).pack(side='left', padx=(6, 0))

        # Convert button
        btn_frame = tk.Frame(content)
        btn_frame.pack(fill='x', pady=(0, 8))
        tk.Button(
            btn_frame, text="Convert", command=self._convert,
            bg="#4a90d9", fg="white", width=14,
        ).pack(side='left')

        # Progress bar
        self.progress_var = tk.DoubleVar()
        ttk.Progressbar(
            content, variable=self.progress_var, maximum=100,
        ).pack(fill='x', pady=(0, 4))

        # Log area
        tk.Label(content, text="Log:", font=("Segoe UI", 9)).pack(anchor='w')
        self.log_widget = scrolledtext.ScrolledText(
            content, height=14, state='disabled',
            font=("Consolas", 9), bg="#1e1e1e", fg="#cccccc",
        )
        self.log_widget.pack(fill='both', expand=True, pady=(2, 0))

        # Status bar
        self.status = tk.Label(
            self.frame, text="Ready", bd=1, relief="sunken", anchor="w",
        )
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

    # -- Database loading ---------------------------------------------------

    def _load_selected_db(self):
        """Load database from the selected CSV folder."""
        name = self.db_var.get()
        if not name:
            self.db = None
            self.db_status.config(text="No database selected")
            return

        db_path = os.path.join(DATABASES_DIR, name)
        self.db = StartlistDatabase.from_csv_folder(db_path)

        if self.db.loaded:
            msg = (f"Database '{name}' loaded: {len(self.db.teams)} teams, "
                   f"{len(self.db.cyclists)} cyclists")
            self.db_status.config(text=msg, fg="#333")
            self._log(msg)
        else:
            self.db_status.config(
                text=f"WARNING: '{name}' missing CSV files", fg="#c00")
            self._log(f"WARNING: Database '{name}' missing CSV files.")

    def _load_cdb(self):
        """Load database from a CDB file (converted to SQLite)."""
        path = filedialog.askopenfilename(
            filetypes=[("CDB files", "*.cdb")],
        )
        if not path:
            return

        def task():
            gc.collect()
            return converter.export_cdb_to_sqlite(path)

        def on_success(temp_path):
            self.temp_path = temp_path
            self.db = StartlistDatabase.from_sqlite(temp_path)
            # Clear dropdown selection to show CDB is active
            self.db_combo.set('')
            if self.db.loaded:
                msg = (f"CDB loaded: {len(self.db.teams)} teams, "
                       f"{len(self.db.cyclists)} cyclists")
                self.db_status.config(text=msg, fg="#333")
                self._log(msg)
                self.status.config(text=f"Loaded: {path}")
            else:
                self.db_status.config(
                    text="WARNING: DYN_team or DYN_cyclist tables missing",
                    fg="#c00")
                self._log("WARNING: DYN_team or DYN_cyclist tables missing. "
                          "ID matching unavailable.")

        run_async(self.root, task, on_success, "Loading CDB...")

    # -- Navigation ---------------------------------------------------------

    def _on_home(self):
        self.temp_path = None
        self.db = None
        gc.collect()
        self.go_home()

    # -- Logging helpers ----------------------------------------------------

    def _log(self, msg):
        self.log_widget.config(state='normal')
        self.log_widget.insert('end', msg + "\n")
        self.log_widget.see('end')
        self.log_widget.config(state='disabled')
        self.root.update_idletasks()

    def _clear_log(self):
        self.log_widget.config(state='normal')
        self.log_widget.delete('1.0', 'end')
        self.log_widget.config(state='disabled')
        self.progress_var.set(0)

    def _update_progress(self, current, total):
        self.progress_var.set((current / total) * 100 if total else 0)
        self.root.update_idletasks()

    # -- File dialogs -------------------------------------------------------

    def _browse_file(self):
        path = filedialog.askopenfilename(
            title="Select HTML startlist file",
            filetypes=[("HTML files", "*.html *.htm"), ("All files", "*.*")],
        )
        if path:
            self.file_var.set(path)

    def _browse_output(self):
        path = filedialog.asksaveasfilename(
            title="Save startlist XML as",
            defaultextension=".xml",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")],
        )
        if path:
            self.out_var.set(path)

    # -- Conversion ---------------------------------------------------------

    def _convert(self):
        filepath = self.file_var.get().strip()
        if not filepath:
            messagebox.showwarning("No file",
                                   "Please select an HTML file first.")
            return

        output = self.out_var.get().strip() or 'startlist.xml'

        self._clear_log()
        self._log(f"Reading: {filepath}")

        data = self.parser.parse_file(filepath)

        if data:
            total_teams = len(data)
            total_riders = sum(len(r) for r in data.values())
            self._log(f"Parsed {total_teams} teams, {total_riders} riders")
            self._log("Matching IDs...")

            db = self.db if self.db and self.db.loaded else None
            self.writer.write(
                data, output, db=db, log=self._log,
                on_progress=self._update_progress,
            )
            self.progress_var.set(100)
            self._log(f"\nSaved to: {output}")
            self.status.config(
                text=f"Saved {output}  --  {total_teams} teams, "
                     f"{total_riders} riders"
            )
            messagebox.showinfo(
                "Success",
                f"Startlist saved to {output}\n\n"
                f"Teams: {total_teams}\nRiders: {total_riders}",
            )
        else:
            self.progress_var.set(0)
            self.status.config(text="Error: no data parsed")
            self._log("ERROR: Could not parse any startlist data "
                      "from the input.")
            messagebox.showerror(
                "Error",
                "Could not parse any startlist data.\n"
                "Make sure the file contains a valid startlist.",
            )
