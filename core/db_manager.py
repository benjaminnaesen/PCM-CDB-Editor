import sqlite3

class DatabaseManager:
    """
    Manages SQLite database operations for PCM CDB files.

    Provides methods for querying, updating, and managing database tables
    with support for foreign key lookups and schema caching.
    """

    def __init__(self, db_path):
        """
        Initialize database manager with connection to SQLite database.

        Args:
            db_path (str): Path to the SQLite database file

        Notes:
            Initializes empty caches for schema and table mappings to improve
            query performance on repeated operations.
        """
        self.db_path = db_path
        self.schema_cache = {}
        self.table_map_cache = None

    def get_table_list(self):
        """
        Retrieve list of all user tables in the database.

        Returns:
            list[str]: Sorted list of table names

        Notes:
            Excludes SQLite system tables (sqlite_*).
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
            return [row[0] for row in cursor.fetchall()]

    def fetch_data(self, table_name, search_term=None, lookup=False, limit=None, offset=0, sort_col=None, sort_reverse=False):
        """
        Fetch data from a table with optional filtering, lookup, sorting, and pagination.

        Args:
            table_name (str): Name of the table to query
            search_term (str, optional): Search term to filter across all columns. Defaults to None.
            lookup (bool, optional): If True, resolve foreign keys to display names. Defaults to False.
            limit (int, optional): Maximum number of rows to return. Defaults to None (all rows).
            offset (int, optional): Number of rows to skip (for pagination). Defaults to 0.
            sort_col (str, optional): Column name to sort by. Defaults to None.
            sort_reverse (bool, optional): If True, sort descending. Defaults to False.

        Returns:
            tuple: (columns, rows) where columns is list[str] and rows is list[tuple]

        Notes:
            - When lookup=True, foreign key columns (fkID*) are replaced with
              subqueries that retrieve human-readable names from related tables.
            - Foreign key resolution follows naming conventions: fkIDSuffix looks for
              tables named DYN_Suffix, STA_Suffix, GAM_Suffix, or Suffix.
            - Target display columns are searched in order: gene_sz_name, name, szName, sz_name
            - Search term is case-insensitive and matches across all columns.
            - Schema and table mapping are cached for performance.
        """
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
        """
        Get total number of rows in a table, optionally filtered by search term.

        Args:
            table_name (str): Name of the table
            search_term (str, optional): Search term to filter across all columns. Defaults to None.

        Returns:
            int: Number of rows matching the criteria
        """
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
        """
        Get the next available ID value for a table (max + 1).

        Args:
            table (str): Table name
            id_column (str): Name of the ID column

        Returns:
            int: Next available ID (current maximum + 1, or 1 if table is empty)
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT MAX([{id_column}]) FROM [{table}]")
            result = cursor.fetchone()[0]
            return (int(result) if result is not None else 0) + 1

    def update_cell(self, table, column, value, pk_col, pk_val):
        """
        Update a single cell in the database.

        Args:
            table (str): Table name
            column (str): Column name to update
            value: New value to set
            pk_col (str): Primary key column name
            pk_val: Primary key value identifying the row

        Side Effects:
            Commits the change to the database immediately.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(f"UPDATE [{table}] SET [{column}]=? WHERE [{pk_col}]=?", (value, pk_val))
            conn.commit()

    def delete_row(self, table, pk_col, pk_val):
        """
        Delete a row from the database.

        Args:
            table (str): Table name
            pk_col (str): Primary key column name
            pk_val: Primary key value identifying the row to delete

        Side Effects:
            Commits the deletion to the database immediately.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(f"DELETE FROM [{table}] WHERE [{pk_col}]=?", (pk_val,))
            conn.commit()

    def insert_row(self, table, columns, values):
        """
        Insert a new row into the database.

        Args:
            table (str): Table name
            columns (list[str]): List of column names
            values (list): List of values corresponding to columns

        Side Effects:
            Commits the new row to the database immediately.

        Notes:
            The number and order of values must match the columns list.
        """
        with sqlite3.connect(self.db_path) as conn:
            placeholders = ", ".join(["?"] * len(values))
            col_names = ", ".join([f"[{c}]" for c in columns])
            conn.execute(f"INSERT INTO [{table}] ({col_names}) VALUES ({placeholders})", values)
            conn.commit()

    def get_fk_options(self, fk_column):
        """
        Get dropdown options for a foreign key column.

        Resolves the target table and retrieves {display_name: id} mappings
        for use in dropdown menus during editing.

        Args:
            fk_column (str): Foreign key column name (must start with 'fkID')

        Returns:
            dict or None: Dictionary mapping display names to IDs, or None if not a FK column

        Notes:
            - Follows same resolution logic as fetch_data lookup mode
            - Column naming: fkIDSuffix → searches for DYN_Suffix, STA_Suffix, GAM_Suffix, Suffix
            - Display column preference: gene_sz_name, name, szName, sz_name
            - Returns None if column is not a foreign key or target table not found
            - Results are cached in table_map_cache for performance
        """
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