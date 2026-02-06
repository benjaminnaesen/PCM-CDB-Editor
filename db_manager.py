import sqlite3

class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path

    def get_table_list(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
            return [row[0] for row in cursor.fetchall()]

    def fetch_data(self, table_name, search_term=None):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info([{table_name}])")
            columns = [col[1] for col in cursor.fetchall()]
            if search_term:
                where_clause = " OR ".join([f"CAST([{col}] AS TEXT) LIKE ?" for col in columns])
                cursor.execute(f"SELECT * FROM [{table_name}] WHERE {where_clause}", [f"%{search_term}%"] * len(columns))
            else:
                cursor.execute(f"SELECT * FROM [{table_name}]")
            return columns, cursor.fetchall()

    def get_max_id(self, table, id_column):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT MAX([{id_column}]) FROM [{table}]")
            result = cursor.fetchone()[0]
            return (int(result) if result is not None else 0) + 1

    def update_cell(self, table, column, value, pk_col, pk_val):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(f"UPDATE [{table}] SET [{column}]=? WHERE [{pk_col}]=?", (value, pk_val))
            conn.commit()

    def delete_row(self, table, pk_col, pk_val):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(f"DELETE FROM [{table}] WHERE [{pk_col}]=?", (pk_val,))
            conn.commit()

    def insert_row(self, table, columns, values):
        with sqlite3.connect(self.db_path) as conn:
            placeholders = ", ".join(["?"] * len(values))
            col_names = ", ".join([f"[{c}]" for c in columns])
            conn.execute(f"INSERT INTO [{table}] ({col_names}) VALUES ({placeholders})", values)
            conn.commit()