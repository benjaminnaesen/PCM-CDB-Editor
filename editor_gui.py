import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import gc
from db_manager import DatabaseManager
import converter

class CDBEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("PCM CDB Editor")
        self.root.geometry("1200x800")
        
        self.db = None
        self.temp_path = None
        self.current_table = None
        self.all_tables = []
        self.active_editor = None

        self.sidebar_even = "#e8e8e8"
        self.sidebar_odd = "#fdfdfd"

        self._setup_ui()
        self._create_context_menu()

    def _create_context_menu(self):
        self.menu = tk.Menu(self.root, tearoff=0)
        self.menu.add_command(label="Duplicate Row", command=self.duplicate_row)
        self.menu.add_command(label="Delete Row", command=self.delete_row)

    def _create_search_box(self, parent, variable, width):
        frame = tk.Frame(parent, bg="white", highlightbackground="#ccc", highlightthickness=1)
        entry = tk.Entry(frame, textvariable=variable, width=width, relief=tk.FLAT, borderwidth=0)
        entry.pack(side=tk.LEFT, padx=5, pady=2, fill=tk.X, expand=True)
        tk.Button(frame, text="✕", command=lambda: variable.set(""), 
                  relief=tk.FLAT, bg="white", fg="gray", font=("Arial", 8, "bold"), bd=0).pack(side=tk.RIGHT, padx=2)
        return frame

    def _setup_ui(self):
        style = ttk.Style()
        style.configure("Treeview", rowheight=25)

        toolbar = tk.Frame(self.root, pady=10, bg="#f0f0f0")
        toolbar.pack(side=tk.TOP, fill=tk.X)
        
        tk.Button(toolbar, text="Open CDB", command=self.load_cdb, width=12).pack(side=tk.LEFT, padx=10)
        tk.Button(toolbar, text="Save As...", command=self.save_as_cdb, width=12).pack(side=tk.LEFT, padx=10)

        self.data_search_var = tk.StringVar()
        self.data_search_var.trace_add("write", lambda *args: self.load_table_data())
        self._create_search_box(toolbar, self.data_search_var, 40).pack(side=tk.RIGHT, padx=15)

        self.pw = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashwidth=4, bg="#ccc")
        self.pw.pack(expand=True, fill=tk.BOTH)

        sidebar_container = tk.Frame(self.pw, bg="#e1e1e1")
        self.pw.add(sidebar_container)
        self.table_filter_var = tk.StringVar()
        self.table_filter_var.trace_add("write", self.filter_sidebar)
        self._create_search_box(sidebar_container, self.table_filter_var, 20).pack(fill=tk.X, padx=2, pady=2)

        self.sidebar = tk.Listbox(sidebar_container, width=35, relief=tk.FLAT, borderwidth=0, selectbackground="#0078d7", highlightthickness=0, activestyle='none')
        self.sidebar.pack(expand=True, fill=tk.BOTH)
        self.sidebar.bind("<<ListboxSelect>>", self.on_table_select)

        self.table_frame = tk.Frame(self.pw)
        self.pw.add(self.table_frame)

        self.tree = ttk.Treeview(self.table_frame, show="headings", selectmode="browse")
        self.tree.tag_configure('oddrow', background="#f4f4f4")
        self.tree.tag_configure('evenrow', background="#ffffff")
        
        self.vsb = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.tree.yview)
        self.hsb = ttk.Scrollbar(self.table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=self.vsb.set, xscrollcommand=self.hsb.set)
        self.tree.grid(row=0, column=0, sticky='nsew')
        self.vsb.grid(row=0, column=1, sticky='ns')
        self.hsb.grid(row=1, column=0, sticky='ew')
        
        self.table_frame.grid_columnconfigure(0, weight=1)
        self.table_frame.grid_rowconfigure(0, weight=1)

        self.status = tk.Label(self.root, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W, padx=10)
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Button-3>", self.show_context_menu)

    def load_table_data(self):
        if not self.current_table or not self.db: return
        if self.active_editor: self.active_editor.destroy()
        
        cols, rows = self.db.fetch_data(self.current_table, self.data_search_var.get())
        
        self.tree["columns"] = cols
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=140, stretch=False)
        
        self.tree.delete(*self.tree.get_children())
        for i, row in enumerate(rows):
            tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            self.tree.insert("", "end", values=row, tags=(tag,))

    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.menu.post(event.x_root, event.y_root)

    def on_double_click(self, event):
        item = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        if not item or not column: return
        
        col_idx = int(column[1:]) - 1
        col_name = self.tree["columns"][col_idx]
        vals = self.tree.item(item, "values")
        pk_val = vals[0]
        
        x, y, w, h = self.tree.bbox(item, column)
        self.active_editor = tk.Entry(self.table_frame, relief=tk.FLAT)
        self.active_editor.insert(0, vals[col_idx])
        self.active_editor.place(x=x, y=y, width=w, height=h)
        self.active_editor.focus_set()

        def commit(e=None):
            if not self.active_editor: return
            new_val = self.active_editor.get()
            self.db.update_cell(self.current_table, col_name, new_val, self.tree["columns"][0], pk_val)
            self.active_editor.destroy()
            self.active_editor = None
            self.load_table_data()

        self.active_editor.bind("<Return>", commit)
        self.active_editor.bind("<FocusOut>", lambda e: self.active_editor.destroy() if self.active_editor else None)

    def duplicate_row(self):
        selected = self.tree.selection()
        if not selected: return
        
        item = selected[0]
        vals = list(self.tree.item(item, "values"))
        current_index = self.tree.index(item)
        
        try:
            cols, _ = self.db.fetch_data(self.current_table)
            pk_col = cols[0]
            
            # GET NEW UNIQUE ID
            new_id = self.db.get_max_id(self.current_table, pk_col)
            vals[0] = new_id
            
            self.db.insert_row(self.current_table, cols, vals)
            
            target_index = current_index + 1
            tag = 'evenrow' if target_index % 2 == 0 else 'oddrow'
            new_item = self.tree.insert("", target_index, values=vals, tags=(tag,))
            
            self.tree.selection_set(new_item)
            self.tree.see(new_item)
            
        except Exception as e:
            messagebox.showerror("Error", f"Duplicate failed: {e}")

    def delete_row(self):
        selected = self.tree.selection()
        if not selected: return
        if not messagebox.askyesno("Confirm", "Delete row?"): return
        vals = self.tree.item(selected[0], "values")
        try:
            # Uses the unique ID at vals[0]
            self.db.delete_row(self.current_table, self.tree["columns"][0], vals[0])
            self.load_table_data()
        except Exception as e:
            messagebox.showerror("Error", f"Delete failed: {e}")

    def load_cdb(self, path=None):
        if not path:
            path = filedialog.askopenfilename(filetypes=[("CDB files", "*.cdb")])
        if not path: return
        try:
            self.temp_path = converter.export_cdb_to_sqlite(path)
            self.db = DatabaseManager(self.temp_path)
            self.all_tables = self.db.get_table_list()
            self.filter_sidebar()
            self.status.config(text=f"Loaded: {path}")
        except Exception as e:
            messagebox.showerror("Error", f"Load failed: {e}")

    def filter_sidebar(self, *args):
        search_term = self.table_filter_var.get().lower()
        self.sidebar.delete(0, tk.END)
        filtered = [t for t in self.all_tables if search_term in t.lower()]
        for i, table in enumerate(filtered):
            self.sidebar.insert(tk.END, table)
            self.sidebar.itemconfig(i, {'bg': self.sidebar_even if i % 2 == 0 else self.sidebar_odd})

    def on_table_select(self, e):
        selection = self.sidebar.curselection()
        if not selection: return
        self.current_table = self.sidebar.get(selection[0])
        self.load_table_data()

    def save_as_cdb(self):
        if not self.temp_path: return
        target = filedialog.asksaveasfilename(defaultextension=".cdb", filetypes=[("CDB files", "*.cdb")])
        if not target: return
        try:
            gc.collect()
            converter.import_sqlite_to_cdb(self.temp_path, target)
            messagebox.showinfo("Success", "CDB saved successfully.")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed: {e}")