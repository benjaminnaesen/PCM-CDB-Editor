# CLAUDE.md — Development Context

## Project Overview

PCM Database Tools is a Tkinter desktop app for editing Pro Cycling Manager .cdb database files and generating startlist XML files. Windows-only (requires SQLiteExporter.exe).

## Architecture

**Core layer** (`core/`) — no UI imports:
- `db_manager.py` — `DatabaseManager` wraps SQLite; FK resolution via `fkID{Suffix}` → `DYN_/STA_/GAM_{Suffix}` naming convention; pagination with `LIMIT/OFFSET`; column/row caching
- `app_state.py` — `AppState` persists session to `session_config.json`; undo/redo stacks with `MAX_UNDO_STACK_SIZE` limit
- `converter.py` — shells out to `SQLiteExporter.exe` for CDB↔SQLite
- `csv_io.py` — CSV bulk import/export
- `startlist.py` — `StartlistParser` (BeautifulSoup), `StartlistDatabase`, `PCMXmlWriter`
- `constants.py` — all magic numbers (`PAGE_SIZE`, `DB_CHUNK_SIZE`, delays, limits)

**UI layer** (`ui/`) — Tkinter widgets:
- `editor_gui.py` — `PCMDatabaseTools` is the root window; manages frame navigation (home ↔ editor ↔ startlist) via `pack`/`pack_forget`
- `welcome_screen.py` — home screen with tool tiles and recent files
- `sidebar.py` — table list with search, favorites (drag-and-drop reorder), right-click context menu
- `table_view.py` — Treeview-based data grid; inline editing, sorting, pagination, column visibility, debounced search
- `column_manager_dialog.py` — column show/hide with presets
- `startlist_view.py` — startlist generator UI
- `ui_utils.py` — `ToolTip` widget, `run_async` (threaded task with progress dialog)

## Key Patterns

- FK columns use naming convention `fkID{Suffix}` mapping to tables `DYN_{Suffix}`, `STA_{Suffix}`, or `GAM_{Suffix}`
- Display columns for FK lookups are chosen by preference list: `gene_sz_name`, `name`, `szName`, `sz_name`, then first text column
- `run_async()` runs blocking operations in daemon threads with a modal progress dialog
- Pagination: `PAGE_SIZE` rows loaded initially, more on scroll via `load_more_data()`
- Search is debounced (`SEARCH_DEBOUNCE_DELAY` ms) and runs SQL `CAST(col AS TEXT) LIKE ?`

## Testing

```bash
python -m unittest discover tests
```

Tests use in-memory SQLite databases. No CDB files or GUI required for unit tests.

## Dependencies

- Python 3.10+
- `beautifulsoup4` (HTML startlist parsing)
- `tkinter` (included with Python on Windows)
- `SQLiteExporter.exe` (bundled in `SQLiteExporter/`)
