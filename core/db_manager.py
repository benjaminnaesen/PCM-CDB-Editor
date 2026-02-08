import sqlite3

class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.schema_cache = {}
        self.table_map_cache = None

    def get_table_list(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
            return [row[0] for row in cursor.fetchall()]

    def fetch_data(self, table_name, search_term=None, lookup=False, limit=None, offset=0, sort_col=None, sort_reverse=False):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if table_name in self.schema_cache: columns = self.schema_cache[table_name]
            else:
                cursor.execute(f"PRAGMA table_info([{table_name}])")
                columns = [col[1] for col in cursor.fetchall()]
                self.schema_cache[table_name] = columns
            
            select_fields = [f"[{c}]" for c in columns]
            if lookup:
                if not self.table_map_cache:
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    self.table_map_cache = {r[0].upper(): r[0] for r in cursor.fetchall()}
                for i, col in enumerate(columns):
                    if col.startswith("fkID") and len(col) > 4:
                        suffix = col[4:]
                        target_table = None
                        for candidate in [f"DYN_{suffix}", f"STA_{suffix}", f"GAM_{suffix}", suffix]:
                            if candidate.upper() in self.table_map_cache:
                                target_table = self.table_map_cache[candidate.upper()]; break
                        if target_table:
                            try:
                                cursor.execute(f"PRAGMA table_info([{target_table}])")
                                target_info = cursor.fetchall()
                                target_cols = [c[1] for c in target_info]
                                target_pk = next((c[1] for c in target_info if c[5] > 0), target_cols[0] if target_cols else "ID")
                                target_col = next((c for c in ["gene_sz_name", "name", "szName", "sz_name"] if c in target_cols), None)
                                if not target_col and len(target_cols) > 1: target_col = target_cols[1]
                                if target_col:
                                    select_fields[i] = f"(SELECT [{target_col}] FROM [{target_table}] WHERE [{target_table}].[{target_pk}] = [{table_name}].[{col}])"
                            except: pass

            query_cols = ", ".join(select_fields)
            sql = f"SELECT {query_cols} FROM [{table_name}]"
            params = []

            if search_term:
                where_clause = " OR ".join([f"CAST([{col}] AS TEXT) LIKE ?" for col in columns])
                sql += f" WHERE {where_clause}"
                params = [f"%{search_term}%"] * len(columns)
            
            if sort_col:
                sql += f" ORDER BY [{sort_col}] {'DESC' if sort_reverse else 'ASC'}"
            
            if limit is not None:
                sql += f" LIMIT {limit} OFFSET {offset}"

            cursor.execute(sql, params)
            return columns, cursor.fetchall()

    def get_row_count(self, table_name, search_term=None):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if search_term:
                cursor.execute(f"PRAGMA table_info([{table_name}])")
                columns = [col[1] for col in cursor.fetchall()]
                where_clause = " OR ".join([f"CAST([{col}] AS TEXT) LIKE ?" for col in columns])
                cursor.execute(f"SELECT COUNT(*) FROM [{table_name}] WHERE {where_clause}", [f"%{search_term}%"] * len(columns))
            else:
                cursor.execute(f"SELECT COUNT(*) FROM [{table_name}]")
            return cursor.fetchone()[0]

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

    def get_fk_options(self, fk_column):
        if not fk_column.startswith("fkID") or len(fk_column) <= 4: return None
        suffix = fk_column[4:]
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if not self.table_map_cache:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                self.table_map_cache = {r[0].upper(): r[0] for r in cursor.fetchall()}
            
            target_table = None
            for candidate in [f"DYN_{suffix}", f"STA_{suffix}", f"GAM_{suffix}", suffix]:
                if candidate.upper() in self.table_map_cache:
                    target_table = self.table_map_cache[candidate.upper()]; break
            
            if not target_table: return None

            try:
                cursor.execute(f"PRAGMA table_info([{target_table}])")
                target_info = cursor.fetchall()
                target_cols = [c[1] for c in target_info]
                target_pk = next((c[1] for c in target_info if c[5] > 0), target_cols[0] if target_cols else "ID")
                target_col = next((c for c in ["gene_sz_name", "name", "szName", "sz_name"] if c in target_cols), None)
                if not target_col and len(target_cols) > 1: target_col = target_cols[1]
                
                if target_col:
                    cursor.execute(f"SELECT [{target_col}], [{target_pk}] FROM [{target_table}] ORDER BY [{target_col}]")
                    return {str(row[0]): row[1] for row in cursor.fetchall() if row[0] is not None}
            except: pass
        return None