"""
CDB ↔ SQLite conversion utilities using SQLiteExporter.exe.

This module wraps the external SQLiteExporter tool to convert between
Pro Cycling Manager's proprietary CDB format and SQLite databases.
"""

import os, subprocess, shutil, tempfile

TOOL_PATH = os.path.join("SQLiteExporter", "SQLiteExporter.exe")

def export_cdb_to_sqlite(cdb_path):
    """
    Convert CDB file to SQLite database in temp directory.

    Args:
        cdb_path (str): Path to source .cdb file

    Returns:
        str: Path to temporary SQLite database file

    Raises:
        subprocess.CalledProcessError: If SQLiteExporter fails
        FileNotFoundError: If SQLiteExporter.exe not found

    Side Effects:
        - Runs SQLiteExporter.exe subprocess
        - Creates temporary SQLite file in system temp directory
        - Removes existing temp file if present

    Notes:
        The SQLite file is created in a temporary location to avoid
        cluttering the user's working directory.
    """
    abs_cdb_path = os.path.abspath(cdb_path)
    temp_sqlite = os.path.join(tempfile.gettempdir(), "pcm_working_db.sqlite")
    local_sqlite = abs_cdb_path.replace(".cdb", ".sqlite")
    subprocess.run([TOOL_PATH, "-a", "-export", abs_cdb_path], check=True)
    if os.path.exists(temp_sqlite): os.remove(temp_sqlite)
    shutil.move(local_sqlite, temp_sqlite)
    return temp_sqlite

def import_sqlite_to_cdb(temp_sqlite, target_cdb_path):
    """
    Convert SQLite database back to CDB format.

    Args:
        temp_sqlite (str): Path to source SQLite database
        target_cdb_path (str): Path where .cdb file should be created

    Raises:
        subprocess.CalledProcessError: If SQLiteExporter fails

    Side Effects:
        - Creates intermediate .sqlite file next to target .cdb
        - Runs SQLiteExporter.exe subprocess
        - Deletes intermediate .sqlite file after conversion

    Notes:
        SQLiteExporter requires the .sqlite file to be in the same directory
        as the target .cdb file, hence the copy operation.
    """
    target_base = os.path.splitext(os.path.abspath(target_cdb_path))[0]
    target_sqlite = target_base + ".sqlite"
    shutil.copy2(temp_sqlite, target_sqlite)
    subprocess.run([TOOL_PATH, "-a", "-import", target_base], check=True)
    if os.path.exists(target_sqlite): os.remove(target_sqlite)