import sqlite3

class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path

    def get_table_list(self):
        """Returns a list of all tables in the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
            return [r[0] for r in cursor.fetchall()]

    def fetch_data(self, table_name, search_term=None):
        """Fetches columns and rows, with optional searching across all columns."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info([{table_name}])")
            cols = [c[1] for c in cursor.fetchall()]

            if search_term:
                # CAST to text allows searching across numeric and string columns
                where_clauses = [f"CAST([{col}] AS TEXT) LIKE ?" for col in cols]
                sql = f"SELECT * FROM [{table_name}] WHERE {' OR '.join(where_clauses)}"
                params = [f"%{search_term}%"] * len(cols)
                cursor.execute(sql, params)
            else:
                cursor.execute(f"SELECT * FROM [{table_name}]")
            
            return cols, cursor.fetchall()

    def update_cell(self, table, column, value, pk_col, pk_val):
        """Updates a single cell in the database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(f"UPDATE [{table}] SET [{column}]=? WHERE [{pk_col}]=?", (value, pk_val))
            conn.commit()