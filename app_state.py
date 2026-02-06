import json, os

class AppState:
    def __init__(self, settings_file):
        self.settings_file = settings_file
        self.undo_stack = []
        self.redo_stack = []
        self.settings = self.load_settings()
        self.favorites = self.settings.get("favorites", [])

    def load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r") as file:
                    return json.load(file)
            except: pass
        return {"favorites": [], "window_size": "1200x800", "last_path": "", "is_maximized": False}

    def save_settings(self, window_geometry, is_maximized):
        self.settings["favorites"] = self.favorites
        self.settings["window_size"] = window_geometry
        self.settings["is_maximized"] = is_maximized
        with open(self.settings_file, "w") as file:
            json.dump(self.settings, file, indent=4)

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