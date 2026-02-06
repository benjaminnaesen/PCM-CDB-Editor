import os
import subprocess
import shutil
import tempfile

TOOL_PATH = os.path.join("SQLiteExporter", "SQLiteExporter.exe")

def export_cdb_to_sqlite(cdb_path):
    """Converts a CDB to SQLite and moves it to a temp working directory."""
    abs_cdb = os.path.abspath(cdb_path)
    temp_sqlite = os.path.join(tempfile.gettempdir(), "pcm_working_db.sqlite")
    
    # SQLiteExporter creates a .sqlite file in the source directory
    local_sqlite = abs_cdb.replace(".cdb", ".sqlite")
    
    subprocess.run([TOOL_PATH, "-a", "-export", abs_cdb], check=True)
    
    if os.path.exists(temp_sqlite): os.remove(temp_sqlite)
    shutil.move(local_sqlite, temp_sqlite)
    return temp_sqlite

def import_sqlite_to_cdb(temp_sqlite, target_cdb_path):
    """Converts the working SQLite back into a CDB file."""
    target_base = os.path.splitext(os.path.abspath(target_cdb_path))[0]
    target_sqlite = target_base + ".sqlite"
    
    shutil.copy2(temp_sqlite, target_sqlite)
    subprocess.run([TOOL_PATH, "-a", "-import", target_base], check=True)
    
    if os.path.exists(target_sqlite):
        os.remove(target_sqlite)