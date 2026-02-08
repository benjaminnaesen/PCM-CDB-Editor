import tkinter as tk
from tkinter import ttk, messagebox

class TableView:
    def __init__(self, parent, app_state, on_change_callback):
        self.parent = parent
        self.state = app_state
        self.on_change = on_change_callback
        
        self.db = None
        self.current_table = None
        self.search_term = ""
        self.lookup_mode = False
        
        self.active_editor = None
        self.editing_data = {}
        self.sort_state = {"column": None, "reverse": False}
        self.page_size = 50
        self.offset, self.total_rows, self.loading_data = 0, 0, False
        
        self._setup_ui()
        self._create_menu()

    def _setup_ui(self):
        self.tree = ttk.Treeview(self.parent, show="headings", selectmode="browse")
        self.tree.tag_configure('oddrow', background="#f4f4f4"); self.tree.tag_configure('evenrow', background="#ffffff")
        self.vsb = ttk.Scrollbar(self.parent, command=self.tree.yview); hsb = ttk.Scrollbar(self.parent, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=self.on_tree_scroll, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky='nsew'); self.vsb.grid(row=0, column=1, sticky='ns'); hsb.grid(row=1, column=0, sticky='ew')
        self.parent.grid_columnconfigure(0, weight=1); self.parent.grid_rowconfigure(0, weight=1)
        
        self.tree.bind("<Double-1>", self.on_double_click); self.tree.bind("<Button-3>", self.show_context_menu)
        self.tree.bind("<ButtonRelease-1>", self.on_single_click)
        self.tree.bind("<Button-1>", self.on_tree_click)

    def _create_menu(self):
        self.row_menu = tk.Menu(self.parent, tearoff=0)
        self.row_menu.add_command(label="Duplicate Row", command=self.duplicate_row)
        self.row_menu.add_command(label="Delete Row", command=self.delete_row)

    def set_db(self, db):
        self.db = db
        self.current_table = None
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = []

    def set_table(self, table_name):
        self.current_table = table_name
        self.sort_state = {"column": None, "reverse": False}
        self.load_table_data()

    def set_search_term(self, term):
        self.search_term = term
        self.load_table_data()

    def set_lookup_mode(self, enabled):
        self.lookup_mode = enabled
        self.load_table_data()

    def on_tree_scroll(self, first, last):
        self.vsb.set(first, last)
        if float(last) > 0.95: self.load_more_data()

    def sort_column(self, col, reverse):
        self.sort_state = {"column": col, "reverse": reverse}
        self.load_table_data()

    def load_table_data(self):
        if self.active_editor: self.cancel_edit()
        if not self.current_table or not self.db: return
        self.tree.grid_remove()
        self.offset = 0
        self.total_rows = self.db.get_row_count(self.current_table, self.search_term)
        columns, row_data = self.db.fetch_data(self.current_table, self.search_term, self.lookup_mode, self.page_size, 0, self.sort_state["column"], self.sort_state["reverse"])
        self.offset += len(row_data)

        self.tree["columns"] = columns
        for col in columns:
            prefix = ("▼ " if self.sort_state["reverse"] else "▲ ") if col == self.sort_state["column"] else ""
            self.tree.heading(col, text=prefix + col, command=lambda _c=col: self.sort_column(_c, not self.sort_state["reverse"] if _c == self.sort_state["column"] else False))
            self.tree.column(col, width=140, stretch=False)
        self.tree.delete(*self.tree.get_children())
        for index, row in enumerate(row_data): self.tree.insert("", "end", values=row, tags=('evenrow' if index%2==0 else 'oddrow'))
        self.tree.grid()

    def load_more_data(self):
        if not self.current_table or self.loading_data or self.offset >= self.total_rows: return
        self.loading_data = True
        _, row_data = self.db.fetch_data(self.current_table, self.search_term, self.lookup_mode, self.page_size, self.offset, self.sort_state["column"], self.sort_state["reverse"])
        start_idx = self.offset
        for index, row in enumerate(row_data):
            self.tree.insert("", "end", values=row, tags=('evenrow' if (start_idx + index)%2==0 else 'oddrow'))
        self.offset += len(row_data)
        self.loading_data = False

    def on_double_click(self, event):
        item, col_id = self.tree.identify_row(event.y), self.tree.identify_column(event.x)
        self.edit_cell(item, col_id)

    def on_single_click(self, event):
        if not self.lookup_mode: return
        try: region = self.tree.identify_region(event.x, event.y)
        except: region = self.tree.identify("region", event.x, event.y)
        if region == "cell":
            col_id, item = self.tree.identify_column(event.x), self.tree.identify_row(event.y)
            if col_id and item:
                index = int(col_id.replace('#', '')) - 1
                if index >= 0 and self.tree["columns"][index].startswith("fkID"): self.edit_cell(item, col_id)

    def on_tree_click(self, event):
        if self.active_editor: self.commit_editor()

    def cancel_edit(self, event=None):
        if self.active_editor: self.active_editor.destroy(); self.active_editor = None; self.editing_data = {}

    def commit_editor(self, event=None, reload_data=True):
        if not self.active_editor: return
        new_val, editor = self.active_editor.get(), self.active_editor
        self.active_editor = None; data = self.editing_data; self.editing_data = {}; editor.destroy()
        col_name, pk_val, old_val, fk_options = data['col_name'], data['pk_val'], data['old_val'], data['fk_options']
        db_val, undo_old_val = new_val, old_val
        if fk_options:
            if new_val in fk_options: db_val = fk_options[new_val]
            else: return 
            undo_old_val = fk_options.get(old_val, old_val)
        if str(new_val) != str(old_val):
            self.state.push_undo(self.current_table, col_name, undo_old_val, db_val, pk_val)
            self.on_change(); self.db.update_cell(self.current_table, col_name, db_val, self.tree["columns"][0], pk_val)
            if reload_data: self.load_table_data()
            else:
                new_values = list(data['values']); new_values[data['index']] = new_val
                self.tree.item(data['item'], values=tuple(new_values))

    def on_editor_navigate(self, event):
        if not self.editing_data: return
        item, index = self.editing_data['item'], self.editing_data['index']
        self.commit_editor(reload_data=False)
        next_item, next_col_index = item, index
        if event.keysym == 'Tab':
            if event.state & 1:
                if index > 1: next_col_index -= 1
                elif (p := self.tree.prev(item)): next_item, next_col_index = p, len(self.tree['columns']) - 1
            else:
                if index < len(self.tree['columns']) - 1: next_col_index += 1
                elif (n := self.tree.next(item)): next_item, next_col_index = n, 1
        elif event.keysym == 'Up' and (p := self.tree.prev(item)): next_item = p
        elif event.keysym == 'Down' and (n := self.tree.next(item)): next_item = n
        self.tree.selection_set(next_item); self.edit_cell(next_item, f"#{next_col_index + 1}"); return "break"

    def edit_cell(self, item, col_id):
        if not item or not col_id: return
        index = int(col_id.replace('#', '')) - 1
        if index == 0: return
        if self.active_editor: self.commit_editor()
        col_name, values = self.tree["columns"][index], self.tree.item(item, "values")
        pk_val, old_val = values[0], values[index]
        fk_options = self.db.get_fk_options(col_name) if(self.lookup_mode and col_name.startswith("fkID")) else None
        x, y, w, h = self.tree.bbox(item, col_id); self.tree.see(item)
        self.active_editor = ttk.Combobox(self.parent, values=list(fk_options.keys())) if fk_options else tk.Entry(self.parent, relief="flat")
        self.active_editor.place(x=x, y=y, width=w, height=h); self.active_editor.insert(0, old_val)
        if not isinstance(self.active_editor, ttk.Combobox): self.active_editor.select_range(0, tk.END)
        self.active_editor.focus_set()
        self.editing_data = {'col_name': col_name, 'pk_val': pk_val, 'old_val': old_val, 'fk_options': fk_options, 'item': item, 'index': index, 'values': values}
        for k, v in {"<Return>": lambda e: self.commit_editor(), "<FocusOut>": lambda e: self.commit_editor(), "<Escape>": self.cancel_edit, "<Tab>": self.on_editor_navigate, "<Up>": self.on_editor_navigate, "<Down>": self.on_editor_navigate}.items(): self.active_editor.bind(k, v)

    def duplicate_row(self):
        selection = self.tree.selection()
        if not selection: return
        row_values, tree_index = list(self.tree.item(selection[0], "values")), self.tree.index(selection[0])
        try:
            columns, _ = self.db.fetch_data(self.current_table); row_values[0] = self.db.get_max_id(self.current_table, columns[0])
            self.db.insert_row(self.current_table, columns, row_values); self.on_change()
            tag = 'evenrow' if (tree_index + 1) % 2 == 0 else 'oddrow'
            new_item = self.tree.insert("", tree_index + 1, values=row_values, tags=(tag,))
            self.tree.selection_set(new_item); self.tree.see(new_item)
        except Exception as e: messagebox.showerror("Error", str(e))

    def delete_row(self):
        selection = self.tree.selection()
        if selection and messagebox.askyesno("Confirm", "Delete?"):
            self.db.delete_row(self.current_table, self.tree["columns"][0], self.tree.item(selection[0], "values")[0])
            self.on_change(); self.load_table_data()

    def show_context_menu(self, event):
        row_id = self.tree.identify_row(event.y)
        if row_id: self.tree.selection_set(row_id); self.row_menu.post(event.x_root, event.y_root)