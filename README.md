# PCM Database Tools

A desktop application bundling modding tools for Pro Cycling Manager (PCM), including a database editor and startlist generator.

## Features

### Database Editor

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
- **Row Operations**: Multi-select, duplicate, or delete rows via right-click context menu
- **Session Persistence**: Remembers window size, favorites, recent files, and settings
- **Pagination**: Efficiently handles large tables with lazy loading

### Startlist Generator

- **HTML Parsing**: Convert saved startlist pages from FirstCycling or ProCyclingStats into PCM-compatible XML
- **Database Matching**: Match rider/team names to PCM database IDs using CSV databases or an opened CDB file
- **Progress Tracking**: Real-time log output and progress bar during conversion

## Requirements

- **Python**: 3.10 or higher
- **Operating System**: Windows (required for SQLiteExporter.exe)
- **Dependencies**: Install with pip (see below)

## Installation

1. **Clone or Download** this repository
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Verify tkinter** is available (usually included with Python on Windows):
   ```bash
   python -m tkinter
   ```

## Usage

### Starting the Application

```bash
python main.py
```

The home screen presents two tools: **Database Editor** and **Startlist Generator**, plus a list of recently opened CDB files.

### Database Editor Workflow

1. **Open a CDB File**: Click the Database Editor tile or select a recent file
2. **Browse Tables**: Use the sidebar to navigate tables (search or filter)
3. **Add Favorites**: Right-click tables to favorite them for quick access
4. **Edit Data**: Double-click cells to edit values
5. **Enable Lookup Mode**: Toggle to see human-readable names for foreign keys (e.g., team names instead of IDs)
6. **Save Changes**: Click "Save As..." to export your modified database back to .cdb format

### Startlist Generator Workflow

1. Click the **Startlist Generator** tile from the home screen
2. **Select a database**: Choose a CSV database folder or open a CDB file for rider/team ID matching
3. **Browse** for an HTML startlist file saved from FirstCycling or ProCyclingStats
4. **Set output path** for the XML file
5. Click **Convert** to generate the PCM-compatible startlist XML

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
- **.xml**: PCM startlist format (output of Startlist Generator)

The application automatically handles conversion between CDB and SQLite formats using the bundled SQLiteExporter.exe tool.

## Project Structure

```
PCM-Database-Tools/
├── main.py                          # Application entry point
├── core/                            # Business logic
│   ├── db_manager.py                # Database operations and queries
│   ├── app_state.py                 # Application state and settings
│   ├── constants.py                 # Shared constants
│   ├── converter.py                 # CDB ↔ SQLite conversion
│   ├── csv_io.py                    # CSV import/export
│   └── startlist.py                 # Startlist parsing, matching, and XML writing
├── ui/                              # User interface components
│   ├── editor_gui.py                # Main application window and menu
│   ├── welcome_screen.py            # Home screen with tool tiles
│   ├── sidebar.py                   # Table list and favorites sidebar
│   ├── table_view.py                # Table data display and editing
│   ├── column_manager_dialog.py     # Column visibility and presets dialog
│   ├── startlist_view.py            # Startlist generator view
│   └── ui_utils.py                  # Tooltips and async task helpers
├── databases/                       # CSV database folders for startlist matching
├── SQLiteExporter/                  # External conversion tool
│   └── SQLiteExporter.exe           # CDB ↔ SQLite converter (Windows)
├── tests/                           # Unit tests
│   ├── test_app_state.py            # AppState tests
│   ├── test_db_manager.py           # DatabaseManager tests
│   └── ...
├── requirements.txt                 # Python dependencies
├── session_config.json              # User preferences (auto-generated)
└── README.md
```

## Configuration

The application automatically creates `session_config.json` to store:
- Window size and maximized state
- Favorite tables
- Recent file paths
- Last opened directory
- Lookup mode preference

This file is gitignored and will be created on first run.

## Testing

```bash
# Run all tests
python -m unittest discover tests

# Run a specific test module
python -m unittest tests.test_app_state
```

## Contributing

1. Follow existing code style and patterns
2. Test changes on actual PCM CDB files
3. Add tests for new functionality
4. Update documentation for new features

## Known Limitations

- **Windows Only**: Requires SQLiteExporter.exe which is Windows-specific
- **CDB Format**: Supports PCM game CDB files only
- **Large Files**: Very large databases may take time to convert and load

## Troubleshooting

**"Module tkinter not found"**
Tkinter is included with Python on Windows. Reinstall Python ensuring "tcl/tk and IDLE" is selected.

**"SQLiteExporter.exe not found"**
Ensure the `SQLiteExporter/` folder is in the same directory as `main.py`.

**CDB file won't open**
Ensure the file is a valid PCM CDB file and not corrupted.

## Credits

- **SQLiteExporter**: External tool for CDB/SQLite conversion (see SQLiteExporter/Readme.pdf)
- Developed for the Pro Cycling Manager modding community

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Always backup your .cdb files before editing!** While this tool has undo/redo support, it's always safer to keep backups of your game files.
