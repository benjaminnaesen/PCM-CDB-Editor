import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import gc, os, sys
from db_manager import DatabaseManager
from app_state import AppState
import converter
from welcome_screen import WelcomeScreen

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
        self.all_tables, self.active_editor = [], None
        self.sort_state = {"column": None, "reverse": False}
        self.sidebar_even, self.sidebar_odd, self.fav_color = "#e8e8e8", "#fdfdfd", "#fff9c4"

        self._setup_ui()
        self._create_menus()
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
        tk.Button(toolbar, text="Save As...", command=self.save_as_cdb, width=10).pack(side=tk.LEFT, padx=5)
        self.undo_btn = tk.Button(toolbar, text="↶ Undo", command=self.undo, state="disabled")
        self.undo_btn.pack(side=tk.LEFT, padx=5)
        self.redo_btn = tk.Button(toolbar, text="↷ Redo", command=self.redo, state="disabled")
        self.redo_btn.pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.load_table_data())
        self._create_search_box(toolbar, self.search_var, 40).pack(side=tk.RIGHT, padx=15)
        self.lookup_var = tk.BooleanVar(value=self.state.settings.get("lookup_mode", False))
        tk.Checkbutton(toolbar, text="Lookup Mode", variable=self.lookup_var, command=self.load_table_data).pack(side=tk.RIGHT, padx=5)

        self.pw = tk.PanedWindow(self.editor_frame, orient=tk.HORIZONTAL, sashwidth=4, bg="#ccc")
        self.pw.pack(expand=True, fill=tk.BOTH)

        sidebar_container = tk.Frame(self.pw, bg="#e1e1e1")
        self.pw.add(sidebar_container)
        tk.Label(sidebar_container, text=" ⭐ FAVORITES", anchor="w", bg="#ffd700", font=("SegoeUI", 8, "bold")).pack(fill=tk.X)
        self.fav_lb = tk.Listbox(sidebar_container, height=6, relief="flat", bg=self.fav_color, highlightthickness=0)
        self.fav_lb.pack(fill=tk.X, padx=2, pady=2)
        self.fav_lb.bind("<<ListboxSelect>>", lambda e: self.on_sidebar_select(self.fav_lb))
        self.fav_lb.bind("<Button-3>", lambda e: self.show_sidebar_menu(e, self.fav_lb))

        tk.Label(sidebar_container, text=" 📂 TABLES", anchor="w", bg="#444", fg="white", font=("SegoeUI", 8, "bold")).pack(fill=tk.X, pady=(5,0))
        self.filter_var = tk.StringVar()
        self.filter_var.trace_add("write", self.filter_sidebar)
        self._create_search_box(sidebar_container, self.filter_var, 20).pack(fill=tk.X, padx=2, pady=5)
        self.sidebar = tk.Listbox(sidebar_container, width=35, relief="flat", highlightthickness=0)
        self.sidebar.pack(expand=True, fill=tk.BOTH)
        self.sidebar.bind("<<ListboxSelect>>", lambda e: self.on_sidebar_select(self.sidebar))
        self.sidebar.bind("<Button-3>", lambda e: self.show_sidebar_menu(e, self.sidebar))

        self.table_frame = tk.Frame(self.pw)
        self.pw.add(self.table_frame)
        self.tree = ttk.Treeview(self.table_frame, show="headings", selectmode="browse")
        self.tree.tag_configure('oddrow', background="#f4f4f4"); self.tree.tag_configure('evenrow', background="#ffffff")
        vsb = ttk.Scrollbar(self.table_frame, command=self.tree.yview); hsb = ttk.Scrollbar(self.table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky='nsew'); vsb.grid(row=0, column=1, sticky='ns'); hsb.grid(row=1, column=0, sticky='ew')
        self.table_frame.grid_columnconfigure(0, weight=1); self.table_frame.grid_rowconfigure(0, weight=1)

        self.status = tk.Label(self.editor_frame, text="Ready", bd=1, relief="sunken", anchor="w")
        self.status.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.bind("<Double-1>", self.on_double_click); self.tree.bind("<Button-3>", self.show_context_menu)
        self.show_welcome_screen()

    def show_welcome_screen(self):
        self.editor_frame.pack_forget()
        self.welcome_screen.show()

    def sort_column(self, col, reverse):
        items = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        try: items.sort(key=lambda t: float(t[0]), reverse=reverse)
        except ValueError: items.sort(reverse=reverse)
        for index, (val, k) in enumerate(items):
            self.tree.move(k, '', index)
            self.tree.item(k, tags=('evenrow' if index % 2 == 0 else 'oddrow'))
        self.sort_state = {"column": col, "reverse": reverse}
        for column in self.tree["columns"]:
            prefix = ("▼ " if reverse else "▲ ") if column == col else ""
            self.tree.heading(column, text=prefix + column, command=lambda _c=column: self.sort_column(_c, not reverse))

    def load_table_data(self):
        if not self.current_table or not self.db: return
        columns, row_data = self.db.fetch_data(self.current_table, self.search_var.get(), self.lookup_var.get())
        self.tree["columns"] = columns; self.sort_state = {"column": None, "reverse": False}
        for col in columns:
            self.tree.heading(col, text=col, command=lambda _c=col: self.sort_column(_c, False))
            self.tree.column(col, width=140, stretch=False)
        self.tree.delete(*self.tree.get_children())
        for index, row in enumerate(row_data): self.tree.insert("", "end", values=row, tags=('evenrow' if index%2==0 else 'oddrow'))

    def undo(self):
        action = self.state.undo()
        if action: self.db.update_cell(action["table"], action["column"], action["old"], self.tree["columns"][0], action["pk"]); self.load_table_data()
        self._update_btns()

    def redo(self):
        action = self.state.redo()
        if action: self.db.update_cell(action["table"], action["column"], action["new"], self.tree["columns"][0], action["pk"]); self.load_table_data()
        self._update_btns()

    def _update_btns(self):
        self.undo_btn.config(state="normal" if self.state.undo_stack else "disabled")
        self.redo_btn.config(state="normal" if self.state.redo_stack else "disabled")

    def on_double_click(self, event):
        item = self.tree.identify_row(event.y)
        col_id = self.tree.identify_column(event.x)
        self.edit_cell(item, col_id)

    def edit_cell(self, item, col_id):
        if not item or not col_id: return
        index = int(col_id.replace('#', '')) - 1
        if index == 0: return  # Do not edit primary key

        if self.active_editor: self.active_editor.destroy()

        col_name = self.tree["columns"][index]
        if self.lookup_var.get() and col_name.startswith("fkID"): return
        values = self.tree.item(item, "values")
        pk_val, old_val = values[0], values[index]

        x, y, w, h = self.tree.bbox(item, col_id)
        self.tree.see(item)

        self.active_editor = tk.Entry(self.table_frame, relief="flat")
        self.active_editor.place(x=x, y=y, width=w, height=h)
        self.active_editor.insert(0, old_val)
        self.active_editor.select_range(0, tk.END)
        self.active_editor.focus_set()

        def commit(reload_data=True):
            if not self.active_editor: return
            new_val = self.active_editor.get()
            editor, self.active_editor = self.active_editor, None
            editor.destroy()

            if str(new_val) != str(old_val):
                self.state.push_undo(self.current_table, col_name, old_val, new_val, pk_val)
                self.db.update_cell(self.current_table, col_name, new_val, self.tree["columns"][0], pk_val)
                self._update_btns()
                if reload_data: self.load_table_data()
                else:
                    new_values = list(values); new_values[index] = new_val
                    self.tree.item(item, values=tuple(new_values))

        def navigate(event):
            commit(reload_data=False)
            next_item, next_col_index = item, index
            if event.keysym == 'Tab':
                if event.state & 1:  # Shift-Tab
                    if index > 1: next_col_index -= 1
                    elif (p := self.tree.prev(item)): next_item, next_col_index = p, len(self.tree['columns']) - 1
                else:  # Tab
                    if index < len(self.tree['columns']) - 1: next_col_index += 1
                    elif (n := self.tree.next(item)): next_item, next_col_index = n, 1
            elif event.keysym == 'Up' and (p := self.tree.prev(item)): next_item = p
            elif event.keysym == 'Down' and (n := self.tree.next(item)): next_item = n
            self.tree.selection_set(next_item); self.edit_cell(next_item, f"#{next_col_index + 1}")
            return "break"

        self.active_editor.bind("<Return>", lambda e: commit())
        self.active_editor.bind("<FocusOut>", lambda e: commit())
        self.active_editor.bind("<Escape>", lambda e: (self.active_editor.destroy(), setattr(self, 'active_editor', None)))
        self.active_editor.bind("<Tab>", navigate)
        self.active_editor.bind("<Up>", navigate)
        self.active_editor.bind("<Down>", navigate)

    def _create_menus(self):
        self.sidebar_menu = tk.Menu(self.root, tearoff=0)
        self.row_menu = tk.Menu(self.root, tearoff=0)
        self.row_menu.add_command(label="Duplicate Row", command=self.duplicate_row)
        self.row_menu.add_command(label="Delete Row", command=self.delete_row)

    def load_cdb(self, path=None):
        if not path: path = filedialog.askopenfilename(initialdir=self.state.settings.get("last_path",""), filetypes=[("CDB files", "*.cdb")])
        if not path: return
        try:
            self.temp_path = converter.export_cdb_to_sqlite(path)
            self.db = DatabaseManager(self.temp_path); self.all_tables = self.db.get_table_list()
            self.filter_sidebar(); self.refresh_fav_ui(); self.state.settings["last_path"] = os.path.dirname(path)
            if self.fav_lb.size() > 0:
                self.fav_lb.selection_set(0)
                self.on_sidebar_select(self.fav_lb)
            self.state.add_recent(path)
            self.welcome_screen.hide()
            self.editor_frame.pack(fill=tk.BOTH, expand=True)
            self.status.config(text=f"Loaded: {path}")
        except Exception as e: messagebox.showerror("Error", str(e))

    def _create_search_box(self, parent, var, width):
        frame = tk.Frame(parent, bg="white", highlightbackground="#ccc", highlightthickness=1)
        tk.Entry(frame, textvariable=var, width=width, relief="flat").pack(side="left", padx=5, fill="x", expand=True)
        tk.Button(frame, text="✕", command=lambda: var.set(""), relief="flat", bg="white", bd=0).pack(side="right")
        return frame

    def show_sidebar_menu(self, event, widget):
        widget.selection_clear(0, "end"); index = widget.nearest(event.y); widget.selection_set(index)
        table_name = widget.get(index); self.sidebar_menu.delete(0, "end")
        if table_name in self.state.favorites: self.sidebar_menu.add_command(label="❌ Remove Favorite", command=self.remove_favorite)
        else: self.sidebar_menu.add_command(label="⭐ Add Favorite", command=self.add_favorite)
        self.sidebar_menu.post(event.x_root, event.y_root)

    def add_favorite(self):
        selection = self.sidebar.curselection()
        if selection:
            name = self.sidebar.get(selection[0])
            if name not in self.state.favorites: self.state.favorites.append(name); self.refresh_fav_ui()

    def remove_favorite(self):
        sel_fav, sel_sidebar = self.fav_lb.curselection(), self.sidebar.curselection()
        name = self.fav_lb.get(sel_fav[0]) if sel_fav else self.sidebar.get(sel_sidebar[0]) if sel_sidebar else None
        if name in self.state.favorites: self.state.favorites.remove(name); self.refresh_fav_ui()

    def refresh_fav_ui(self):
        self.fav_lb.delete(0, "end")
        for table in sorted([f for f in self.state.favorites if f in self.all_tables]): self.fav_lb.insert("end", table)

    def on_sidebar_select(self, widget):
        selection = widget.curselection()
        if selection: self.current_table = widget.get(selection[0]); self.load_table_data()

    def filter_sidebar(self, *args):
        term = self.filter_var.get().lower(); self.sidebar.delete(0, "end")
        for index, table in enumerate([t for t in self.all_tables if term in t.lower()]):
            self.sidebar.insert("end", table); self.sidebar.itemconfig(index, {'bg': self.sidebar_even if index%2==0 else self.sidebar_odd})

    def duplicate_row(self):
        selection = self.tree.selection()
        if not selection: return
        row_values, tree_index = list(self.tree.item(selection[0], "values")), self.tree.index(selection[0])
        try:
            columns, _ = self.db.fetch_data(self.current_table); row_values[0] = self.db.get_max_id(self.current_table, columns[0])
            self.db.insert_row(self.current_table, columns, row_values)
            tag = 'evenrow' if (tree_index + 1) % 2 == 0 else 'oddrow'
            new_item = self.tree.insert("", tree_index + 1, values=row_values, tags=(tag,))
            self.tree.selection_set(new_item); self.tree.see(new_item)
        except Exception as e: messagebox.showerror("Error", str(e))

    def delete_row(self):
        selection = self.tree.selection()
        if selection and messagebox.askyesno("Confirm", "Delete?"):
            self.db.delete_row(self.current_table, self.tree["columns"][0], self.tree.item(selection[0], "values")[0]); self.load_table_data()

    def save_as_cdb(self):
        path = filedialog.asksaveasfilename(defaultextension=".cdb", filetypes=[("CDB files", "*.cdb")])
        if path: gc.collect(); converter.import_sqlite_to_cdb(self.temp_path, path); messagebox.showinfo("Saved", "Success")

    def show_context_menu(self, event):
        row_id = self.tree.identify_row(event.y)
        if row_id: self.tree.selection_set(row_id); self.row_menu.post(event.x_root, event.y_root)

    def on_close(self):
        is_maximized = False
        try: is_maximized = self.root.state() == 'zoomed' if sys.platform.startswith('win') else self.root.attributes('-zoomed')
        except: pass
        self.state.save_settings(self.normal_geometry, is_maximized, self.lookup_var.get()); self.root.destroy()