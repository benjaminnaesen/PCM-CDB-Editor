import os, subprocess, shutil, tempfile

TOOL_PATH = os.path.join("SQLiteExporter", "SQLiteExporter.exe")

def export_cdb_to_sqlite(cdb_path):
    abs_cdb = os.path.abspath(cdb_path)
    temp_sqlite = os.path.join(tempfile.gettempdir(), "pcm_working_db.sqlite")
    local_sqlite = abs_cdb.replace(".cdb", ".sqlite")
    subprocess.run([TOOL_PATH, "-a", "-export", abs_cdb], check=True)
    if os.path.exists(temp_sqlite): os.remove(temp_sqlite)
    shutil.move(local_sqlite, temp_sqlite)
    return temp_sqlite

def import_sqlite_to_cdb(temp_sqlite, target_cdb_path):
    target_base = os.path.splitext(os.path.abspath(target_cdb_path))[0]
    target_sqlite = target_base + ".sqlite"
    shutil.copy2(temp_sqlite, target_sqlite)
    subprocess.run([TOOL_PATH, "-a", "-import", target_base], check=True)
    if os.path.exists(target_sqlite): os.remove(target_sqlite)