import csv
import os
import sqlite3

def export_to_csv(db_path, output_folder):
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
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        with open(csv_path, "r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f); headers = next(reader, None)
            if not headers: return
            cursor.execute(f"DELETE FROM [{table_name}]")
            cursor.executemany(f"INSERT INTO [{table_name}] ({', '.join([f'[{h}]' for h in headers])}) VALUES ({', '.join(['?']*len(headers))})", reader)
        conn.commit()

def import_from_csv(db_path, input_folder):
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