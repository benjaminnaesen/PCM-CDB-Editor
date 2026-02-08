import json, os

class AppState:
    def __init__(self, settings_file):
        self.settings_file = settings_file
        self.undo_stack = []
        self.redo_stack = []
        self.settings = self.load_settings()
        self.favorites = self.settings.get("favorites", [])
        self.recents = self.settings.get("recents", [])

    def load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r") as file:
                    return json.load(file)
            except: pass
        return {"favorites": [], "window_size": "1200x800", "last_path": "", "is_maximized": False, "lookup_mode": False, "recents": []}

    def save_settings(self, window_geometry, is_maximized, lookup_mode):
        self.settings["favorites"] = self.favorites
        self.settings["recents"] = self.recents
        self.settings["window_size"] = window_geometry
        self.settings["is_maximized"] = is_maximized
        self.settings["lookup_mode"] = lookup_mode
        with open(self.settings_file, "w") as file:
            json.dump(self.settings, file, indent=4)

    def add_recent(self, path):
        if path in self.recents: self.recents.remove(path)
        self.recents.insert(0, path)
        self.recents = self.recents[:10]

    def push_undo(self, table, col, old, new, pk):
        self.undo_stack.append({"table": table, "column": col, "old": old, "new": new, "pk": pk})
        self.redo_stack.clear()

    def undo(self):
        if not self.undo_stack: return None
        action = self.undo_stack.pop()
        self.redo_stack.append(action)
        return action

    def redo(self):
        if not self.redo_stack: return None
        action = self.redo_stack.pop()
        self.undo_stack.append(action)
        return action