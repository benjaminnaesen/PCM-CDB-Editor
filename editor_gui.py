import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import gc, os
from db_manager import DatabaseManager
from app_state import AppState
import converter

class CDBEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("PCM CDB Editor")
        self.state = AppState("session_config.json")
        self.root.geometry(self.state.settings.get("window_size", "1200x800"))
        
        self.db = None
        self.temp_path = None
        self.current_table = None
        self.all_tables = []
        self.active_editor = None

        self.sidebar_even, self.sidebar_odd = "#e8e8e8", "#fdfdfd"
        self.fav_color = "#fff9c4"

        self._setup_ui()
        self._create_menus()
        self.root.bind("<Control-z>", lambda e: self.undo())
        self.root.bind("<Control-y>", lambda e: self.redo())
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _setup_ui(self):
        toolbar = tk.Frame(self.root, pady=10, bg="#f0f0f0")
        toolbar.pack(side=tk.TOP, fill=tk.X)
        
        tk.Button(toolbar, text="Open CDB", command=self.load_cdb, width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="Save As...", command=self.save_as_cdb, width=10).pack(side=tk.LEFT, padx=5)
        
        self.undo_btn = tk.Button(toolbar, text="↶ Undo", command=self.undo, state="disabled")
        self.undo_btn.pack(side=tk.LEFT, padx=5)
        self.redo_btn = tk.Button(toolbar, text="↷ Redo", command=self.redo, state="disabled")
        self.redo_btn.pack(side=tk.LEFT, padx=5)

        self.data_search_var = tk.StringVar()
        self.data_search_var.trace_add("write", lambda *args: self.load_table_data())
        self._create_search_box(toolbar, self.data_search_var, 40).pack(side=tk.RIGHT, padx=15)

        self.pw = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashwidth=4, bg="#ccc")
        self.pw.pack(expand=True, fill=tk.BOTH)

        # Sidebar
        s_cont = tk.Frame(self.pw, bg="#e1e1e1")
        self.pw.add(s_cont)
        tk.Label(s_cont, text=" ⭐ FAVORITES", anchor="w", bg="#ffd700", font=("SegoeUI", 8, "bold")).pack(fill=tk.X)
        self.fav_lb = tk.Listbox(s_cont, height=6, relief="flat", bg=self.fav_color, highlightthickness=0)
        self.fav_lb.pack(fill=tk.X, padx=2, pady=2)
        self.fav_lb.bind("<<ListboxSelect>>", lambda e: self.on_sidebar_select(self.fav_lb))
        self.fav_lb.bind("<Button-3>", lambda e: self.show_sidebar_menu(e, self.fav_lb))

        tk.Label(s_cont, text=" 📂 TABLES", anchor="w", bg="#444", fg="white", font=("SegoeUI", 8, "bold")).pack(fill=tk.X, pady=(5,0))
        self.table_filter_var = tk.StringVar()
        self.table_filter_var.trace_add("write", self.filter_sidebar)
        self._create_search_box(s_cont, self.table_filter_var, 20).pack(fill=tk.X, padx=2, pady=5)
        
        self.sidebar = tk.Listbox(s_cont, width=35, relief="flat", highlightthickness=0)
        self.sidebar.pack(expand=True, fill=tk.BOTH)
        self.sidebar.bind("<<ListboxSelect>>", lambda e: self.on_sidebar_select(self.sidebar))
        self.sidebar.bind("<Button-3>", lambda e: self.show_sidebar_menu(e, self.sidebar))

        # Table
        self.table_frame = tk.Frame(self.pw)
        self.pw.add(self.table_frame)
        self.tree = ttk.Treeview(self.table_frame, show="headings", selectmode="browse")
        self.tree.tag_configure('oddrow', background="#f4f4f4")
        self.tree.tag_configure('evenrow', background="#ffffff")
        vsb = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self.table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        self.table_frame.grid_columnconfigure(0, weight=1)
        self.table_frame.grid_rowconfigure(0, weight=1)

        self.status = tk.Label(self.root, text="Ready", bd=1, relief="sunken", anchor="w")
        self.status.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Button-3>", self.show_context_menu)

    def _create_menus(self):
        self.sidebar_menu = tk.Menu(self.root, tearoff=0)
        self.row_menu = tk.Menu(self.root, tearoff=0)
        self.row_menu.add_command(label="Duplicate Row", command=self.duplicate_row)
        self.row_menu.add_command(label="Delete Row", command=self.delete_row)

    def undo(self):
        act = self.state.undo()
        if act:
            self.db.update_cell(act["table"], act["column"], act["old"], self.tree["columns"][0], act["pk"])
            self.load_table_data()
        self._update_btns()

    def redo(self):
        act = self.state.redo()
        if act:
            self.db.update_cell(act["table"], act["column"], act["new"], self.tree["columns"][0], act["pk"])
            self.load_table_data()
        self._update_btns()

    def _update_btns(self):
        self.undo_btn.config(state="normal" if self.state.undo_stack else "disabled")
        self.redo_btn.config(state="normal" if self.state.redo_stack else "disabled")

    def on_double_click(self, event):
        item = self.tree.identify_row(event.y)
        col_id = self.tree.identify_column(event.x)
        if not item or not col_id: return
        idx = int(col_id[1:]) - 1
        col_name = self.tree["columns"][idx]
        vals = self.tree.item(item, "values")
        pk_val, old_val = vals[0], vals[idx]
        x, y, w, h = self.tree.bbox(item, col_id)
        self.active_editor = tk.Entry(self.table_frame, relief="flat")
        self.active_editor.insert(0, old_val)
        self.active_editor.place(x=x, y=y, width=w, height=h)
        self.active_editor.focus_set()

        def commit(e=None):
            if not self.active_editor: return
            new_val = self.active_editor.get()
            if str(new_val) != str(old_val):
                self.state.push_undo(self.current_table, col_name, old_val, new_val, pk_val)
                self.db.update_cell(self.current_table, col_name, new_val, self.tree["columns"][0], pk_val)
                self._update_btns()
            ent = self.active_editor; self.active_editor = None; ent.destroy()
            self.load_table_data()

        self.active_editor.bind("<Return>", commit)
        self.active_editor.bind("<FocusOut>", lambda e: commit())

    def load_cdb(self, path=None):
        if not path: path = filedialog.askopenfilename(initialdir=self.state.settings.get("last_path",""), filetypes=[("CDB files", "*.cdb")])
        if not path: return
        try:
            self.temp_path = converter.export_cdb_to_sqlite(path)
            self.db = DatabaseManager(self.temp_path)
            self.all_tables = self.db.get_table_list()
            self.filter_sidebar(); self.refresh_fav_ui()
            self.state.settings["last_path"] = os.path.dirname(path)
            self.status.config(text=f"Loaded: {path}")
        except Exception as e: messagebox.showerror("Error", str(e))

    def load_table_data(self):
        if not self.current_table or not self.db: return
        cols, rows = self.db.fetch_data(self.current_table, self.data_search_var.get())
        self.tree["columns"] = cols
        for c in cols: self.tree.heading(c, text=c); self.tree.column(c, width=140, stretch=False)
        self.tree.delete(*self.tree.get_children())
        for i, r in enumerate(rows): self.tree.insert("", "end", values=r, tags=('evenrow' if i%2==0 else 'oddrow'))

    def _create_search_box(self, parent, var, w):
        f = tk.Frame(parent, bg="white", highlightbackground="#ccc", highlightthickness=1)
        tk.Entry(f, textvariable=var, width=w, relief="flat").pack(side="left", padx=5, fill="x", expand=True)
        tk.Button(f, text="✕", command=lambda: var.set(""), relief="flat", bg="white", bd=0).pack(side="right")
        return f

    def show_sidebar_menu(self, event, widget):
        widget.selection_clear(0, "end"); idx = widget.nearest(event.y); widget.selection_set(idx)
        name = widget.get(idx); self.sidebar_menu.delete(0, "end")
        if name in self.state.favorites: self.sidebar_menu.add_command(label="❌ Remove Favorite", command=self.remove_favorite)
        else: self.sidebar_menu.add_command(label="⭐ Add Favorite", command=self.add_favorite)
        self.sidebar_menu.post(event.x_root, event.y_root)

    def add_favorite(self):
        sel = self.sidebar.curselection()
        if sel: 
            name = self.sidebar.get(sel[0])
            if name not in self.state.favorites: self.state.favorites.append(name); self.refresh_fav_ui()

    def remove_favorite(self):
        sel_f, sel_s = self.fav_lb.curselection(), self.sidebar.curselection()
        name = self.fav_lb.get(sel_f[0]) if sel_f else self.sidebar.get(sel_s[0]) if sel_s else None
        if name in self.state.favorites: self.state.favorites.remove(name); self.refresh_fav_ui()

    def refresh_fav_ui(self):
        self.fav_lb.delete(0, "end")
        for f in sorted([f for f in self.state.favorites if f in self.all_tables]): self.fav_lb.insert("end", f)

    def on_sidebar_select(self, w):
        sel = w.curselection()
        if sel: self.current_table = w.get(sel[0]); self.load_table_data()

    def filter_sidebar(self, *args):
        term = self.table_filter_var.get().lower()
        self.sidebar.delete(0, "end")
        for i, t in enumerate([t for t in self.all_tables if term in t.lower()]):
            self.sidebar.insert("end", t); self.sidebar.itemconfig(i, {'bg': self.sidebar_even if i%2==0 else self.sidebar_odd})

    def duplicate_row(self):
        sel = self.tree.selection()
        if not sel: return
        vals = list(self.tree.item(sel[0], "values"))
        try:
            cols, _ = self.db.fetch_data(self.current_table)
            vals[0] = self.db.get_max_id(self.current_table, cols[0])
            self.db.insert_row(self.current_table, cols, vals)
            self.load_table_data()
        except Exception as e: messagebox.showerror("Error", str(e))

    def delete_row(self):
        sel = self.tree.selection()
        if sel and messagebox.askyesno("Confirm", "Delete?"):
            self.db.delete_row(self.current_table, self.tree["columns"][0], self.tree.item(sel[0], "values")[0])
            self.load_table_data()

    def save_as_cdb(self):
        path = filedialog.asksaveasfilename(defaultextension=".cdb", filetypes=[("CDB files", "*.cdb")])
        if path: gc.collect(); converter.import_sqlite_to_cdb(self.temp_path, path); messagebox.showinfo("Saved", "Success")

    def show_context_menu(self, e):
        row = self.tree.identify_row(e.y)
        if row: self.tree.selection_set(row); self.row_menu.post(e.x_root, e.y_root)

    def on_close(self):
        self.state.save_settings(self.root.geometry())
        self.root.destroy()