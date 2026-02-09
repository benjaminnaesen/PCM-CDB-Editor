"""
CSV import/export functionality for database tables.

Provides utilities to export individual tables or entire databases to CSV
and import CSV data back into existing tables.
"""

import csv
import os
import sqlite3

def export_to_csv(db_path, output_folder):
    """
    Export all tables from database to individual CSV files.

    Args:
        db_path (str): Path to SQLite database
        output_folder (str): Destination directory for CSV files

    Side Effects:
        - Creates output_folder if it doesn't exist
        - Creates one CSV file per table named {table_name}.csv
        - CSV files are UTF-8 encoded with headers

    Notes:
        System tables (sqlite_*) are excluded from export.
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [row[0] for row in cursor.fetchall()]
        
        for table in tables:
            cursor.execute(f"SELECT * FROM [{table}]")
            rows = cursor.fetchall()
            headers = [description[0] for description in cursor.description]
            
            csv_path = os.path.join(output_folder, f"{table}.csv")
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                writer.writerows(rows)

def export_table(db_path, table_name, output_path):
    """
    Export a single table to CSV file.

    Args:
        db_path (str): Path to SQLite database
        table_name (str): Name of table to export
        output_path (str): Destination CSV file path

    Side Effects:
        Creates CSV file with headers and all rows from the table

    Notes:
        CSV is encoded as UTF-8 with standard comma delimiter.
    """
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM [{table_name}]")
        rows = cursor.fetchall()
        headers = [description[0] for description in cursor.description]
        
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)

def import_table_from_csv(db_path, table_name, csv_path):
    """
    Import CSV data into existing table (replaces all existing data).

    Args:
        db_path (str): Path to SQLite database
        table_name (str): Name of target table
        csv_path (str): Source CSV file path

    Side Effects:
        - DELETES all existing rows from the table
        - Inserts all rows from CSV file
        - Commits changes to database

    Warnings:
        This operation is destructive and cannot be undone at the database level.
        Use application undo feature or backup before importing.

    Notes:
        - CSV first row must contain column names matching table schema
        - Column order in CSV must match table schema or be a subset
        - CSV is read as UTF-8 encoded
    """
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        with open(csv_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f); headers = next(reader, None)
            if not headers: return
            cursor.execute(f"DELETE FROM [{table_name}]")
            cursor.executemany(f"INSERT INTO [{table_name}] ({', '.join([f'[{h}]' for h in headers])}) VALUES ({', '.join(['?']*len(headers))})", reader)
        conn.commit()

def import_from_csv(db_path, input_folder):
    """
    Import CSV files from a folder into matching database tables.

    Args:
        db_path (str): Path to SQLite database
        input_folder (str): Directory containing CSV files

    Side Effects:
        - Deletes all existing data from each matched table
        - Imports CSV data into tables with matching names (case-insensitive)
        - Skips CSV files that don't match any table name
        - Commits all changes to database

    Warnings:
        This operation is destructive for all matched tables.

    Notes:
        - CSV filenames should match table names (e.g., DYN_team.csv → DYN_team table)
        - Matching is case-insensitive
        - Each CSV first row must contain column headers
    """
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = {row[0].lower(): row[0] for row in cursor.fetchall()}
        
        files = [f for f in os.listdir(input_folder) if f.lower().endswith(".csv")]
        
        for file in files:
            table_key = os.path.splitext(file)[0].lower()
            if table_key not in existing_tables: continue
            
            table_name = existing_tables[table_key]
            with open(os.path.join(input_folder, file), "r", newline="", encoding="utf-8") as f:
                reader = csv.reader(f); headers = next(reader, None)
                if not headers: continue
                cursor.execute(f"DELETE FROM [{table_name}]")
                cursor.executemany(f"INSERT INTO [{table_name}] ({', '.join([f'[{h}]' for h in headers])}) VALUES ({', '.join(['?']*len(headers))})", reader)
        conn.commit()