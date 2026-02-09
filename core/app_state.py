import json, os

class AppState:
    """
    Manages application state including settings, favorites, and undo/redo history.

    Persists user preferences to JSON file and maintains undo/redo stacks for edits.
    """

    def __init__(self, settings_file):
        """
        Initialize application state from settings file.

        Args:
            settings_file (str): Path to JSON settings file

        Notes:
            Creates default settings if file doesn't exist.
        """
        self.settings_file = settings_file
        self.undo_stack = []
        self.redo_stack = []
        self.settings = self.load_settings()
        self.favorites = self.settings.get("favorites", [])
        self.recents = self.settings.get("recents", [])
        self.column_widths = self.settings.get("column_widths", {})

    def load_settings(self):
        """
        Load settings from JSON file or return defaults.

        Returns:
            dict: Settings dictionary with keys: favorites, window_size,
                  last_path, is_maximized, lookup_mode, recents

        Notes:
            Returns default settings if file doesn't exist or is invalid.
        """
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r") as file:
                    return json.load(file)
            except: pass
        return {"favorites": [], "window_size": "1200x800", "last_path": "", "is_maximized": False, "lookup_mode": False, "recents": []}

    def save_settings(self, window_geometry, is_maximized, lookup_mode):
        """
        Persist current application settings to JSON file.

        Args:
            window_geometry (str): Window size and position (e.g., "1200x800+100+50")
            is_maximized (bool): Whether window is maximized
            lookup_mode (bool): Whether lookup mode is enabled

        Side Effects:
            Writes to self.settings_file with current favorites, recents, and provided params
        """
        self.settings["favorites"] = self.favorites
        self.settings["recents"] = self.recents
        self.settings["column_widths"] = self.column_widths
        self.settings["window_size"] = window_geometry
        self.settings["is_maximized"] = is_maximized
        self.settings["lookup_mode"] = lookup_mode
        with open(self.settings_file, "w") as file:
            json.dump(self.settings, file, indent=4)

    def add_recent(self, path):
        """
        Add file path to recent files list (maximum 10 entries).

        Args:
            path (str): File path to add

        Side Effects:
            - Removes duplicate if path already exists
            - Inserts path at the beginning (most recent first)
            - Truncates list to 10 most recent files

        Notes:
            Most recently added files appear first in the list.
        """
        if path in self.recents: self.recents.remove(path)
        self.recents.insert(0, path)
        self.recents = self.recents[:10]

    def push_undo(self, table, col, old, new, pk):
        """
        Add an edit action to the undo stack.

        Args:
            table (str): Table name where edit occurred
            col (str): Column name that was edited
            old: Previous value before edit
            new: New value after edit
            pk: Primary key value identifying the row

        Side Effects:
            Clears redo stack (new edits invalidate redo history)
        """
        self.undo_stack.append({"table": table, "column": col, "old": old, "new": new, "pk": pk})
        self.redo_stack.clear()

    def undo(self):
        """
        Pop the most recent action from undo stack and add to redo stack.

        Returns:
            dict or None: Action dictionary with keys (table, column, old, new, pk)
                         or None if undo stack is empty
        """
        if not self.undo_stack: return None
        action = self.undo_stack.pop()
        self.redo_stack.append(action)
        return action

    def redo(self):
        """
        Pop the most recent action from redo stack and add back to undo stack.

        Returns:
            dict or None: Action dictionary with keys (table, column, old, new, pk)
                         or None if redo stack is empty
        """
        if not self.redo_stack: return None
        action = self.redo_stack.pop()
        self.undo_stack.append(action)
        return action

    def get_column_widths(self, table_name):
        """
        Get saved column widths for a specific table.

        Args:
            table_name (str): Name of the table

        Returns:
            dict or None: Dictionary mapping column names to widths, or None if not saved
        """
        return self.column_widths.get(table_name)

    def set_column_widths(self, table_name, widths):
        """
        Save column widths for a specific table.

        Args:
            table_name (str): Name of the table
            widths (dict): Dictionary mapping column names to widths
        """
        self.column_widths[table_name] = widths