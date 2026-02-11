# PCM CDB Editor

A desktop GUI application for editing Pro Cycling Manager (PCM) game database files. This tool allows you to view and modify CDB files used by the PCM game series by converting them to SQLite format for editing.

## Features

- **CDB File Support**: Open and edit .cdb files from Pro Cycling Manager games
- **Table Browser**: Browse all database tables with a searchable sidebar
- **Favorites System**: Star frequently-used tables for quick access with drag-and-drop reordering
- **Smart Editing**:
  - Double-click cells to edit
  - Lookup Mode: Display human-readable names for foreign key relationships
  - Keyboard navigation (Tab, Arrow keys)
- **Undo/Redo**: Full undo/redo support for all cell edits (Ctrl+Z / Ctrl+Y)
- **Search & Filter**: Real-time search across table contents
- **Sorting**: Click column headers to sort (ascending/descending)
- **CSV Operations**:
  - Export individual tables to CSV
  - Import CSV data back into tables
  - Export/Import all tables at once
- **Column Management**: Show/hide columns with saveable presets
- **Row Operations**: Duplicate or delete rows via right-click context menu
- **Session Persistence**: Remembers your window size, favorites, recent files, and settings
- **Pagination**: Efficiently handles large tables with lazy loading

## Requirements

- **Python**: 3.10 or higher
- **Operating System**: Windows (required for SQLiteExporter.exe)
- **Python Modules**: Standard library only (tkinter, sqlite3, csv, json, os, subprocess, shutil, tempfile, threading)

### Linux/Mac Note
The SQLiteExporter.exe tool is Windows-only. This application is designed for Windows users.

## Installation

1. **Clone or Download** this repository
2. **Ensure Python 3.10+** is installed:
   ```bash
   python --version
   ```
3. **Verify tkinter** is available (usually included with Python on Windows):
   ```bash
   python -m tkinter
   ```
   A small window should appear if tkinter is properly installed.

4. **No additional packages needed!** This project uses only Python's standard library.

## Usage

### Starting the Application

```bash
python main.py
```

### Workflow

1. **Open a CDB File**: Click "Open CDB" or select from recent files
2. **Browse Tables**: Use the sidebar to navigate tables (search or filter)
3. **Add Favorites**: Right-click tables to favorite them for quick access
4. **Edit Data**: Double-click cells to edit values
5. **Enable Lookup Mode**: Toggle to see human-readable names for foreign keys (e.g., team names instead of IDs)
6. **Save Changes**: Click "Save As..." to export your modified database back to .cdb format

### Keyboard Shortcuts

- **Ctrl+Z**: Undo last edit
- **Ctrl+Y**: Redo
- **Tab**: Move to next cell while editing
- **Shift+Tab**: Move to previous cell while editing
- **Enter**: Confirm edit
- **Escape**: Cancel edit

### File Formats

- **.cdb**: Pro Cycling Manager database file (proprietary format)
- **.sqlite**: SQLite database (used internally for editing)
- **.csv**: Comma-separated values (for data import/export)

The application automatically handles conversion between CDB and SQLite formats using the bundled SQLiteExporter.exe tool.

## Project Structure

```
PCM-CDB-Editor/
├── main.py                 # Application entry point
├── core/                   # Business logic
│   ├── db_manager.py       # Database operations and queries
│   ├── app_state.py        # Application state and settings management
│   ├── converter.py        # CDB ↔ SQLite conversion
│   └── csv_io.py           # CSV import/export functionality
├── ui/                     # User interface components
│   ├── editor_gui.py       # Main application window
│   ├── sidebar.py          # Table list and favorites sidebar
│   ├── table_view.py       # Table data display and editing
│   ├── welcome_screen.py   # Welcome screen with recent files
│   └── ui_utils.py         # UI utilities (async operations)
├── SQLiteExporter/         # External conversion tool
│   └── SQLiteExporter.exe  # CDB ↔ SQLite converter (Windows)
├── tests/                  # Unit tests
│   ├── test_app_state.py   # AppState tests
│   ├── test_db_manager.py  # DatabaseManager tests
│   └── ...
├── session_config.json     # User preferences (auto-generated)
├── requirements.txt        # Dependencies documentation
└── README.md               # This file
```

## Configuration

The application automatically creates `session_config.json` to store:
- Window size and maximized state
- Favorite tables
- Recent file paths
- Last opened directory
- Lookup mode preference

This file is gitignored and will be created on first run. See `session_config.example.json` for the structure.

## Testing

Run the test suite using Python's built-in unittest framework:

```bash
# Run all tests
python -m unittest discover tests

# Run specific test module
python -m unittest tests.test_app_state
```

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Maintain the "standard library only" philosophy (no external pip packages)
2. Follow existing code style and patterns
3. Test changes on actual PCM CDB files
4. Add tests for new functionality
5. Update documentation for new features

## Known Limitations

- **Windows Only**: Requires SQLiteExporter.exe which is Windows-specific
- **CDB Format**: Supports PCM game CDB files only (not other database formats)
- **Large Files**: Very large databases may take time to convert and load

## Troubleshooting

**Issue: "Module tkinter not found"**
- Solution: Tkinter is included with Python on Windows. Reinstall Python ensuring "tcl/tk and IDLE" is selected.

**Issue: "SQLiteExporter.exe not found"**
- Solution: Ensure the `SQLiteExporter/` folder is in the same directory as `main.py`

**Issue: CDB file won't open**
- Solution: Ensure the file is a valid PCM CDB file and not corrupted

## Credits

- **SQLiteExporter**: External tool for CDB/SQLite conversion (see SQLiteExporter/Readme.pdf)
- Developed for the Pro Cycling Manager modding community

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**⚠️ Important:** Always backup your .cdb files before editing! While this tool has undo/redo support, it's always safer to keep backups of your game files.

**🎮 Happy modding!**
