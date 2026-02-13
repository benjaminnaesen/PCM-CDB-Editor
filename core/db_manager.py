"""
Manages SQLite database operations for PCM CDB files.

Provides methods for querying, updating, and managing database tables
with support for foreign key lookups and schema caching.
"""

import sqlite3

from core.constants import DB_CHUNK_SIZE

# Preferred display columns when resolving foreign keys (tried in order)
_FK_DISPLAY_COLUMNS = ["gene_sz_name", "name", "szName", "sz_name"]


class DatabaseManager:
    """
    Manages SQLite database operations for PCM CDB files.

    Provides methods for querying, updating, and managing database tables
    with support for foreign key lookups and schema caching.
    """

    def __init__(self, db_path):
        """
        Initialize database manager with persistent connection.

        Args:
            db_path (str): Path to the SQLite database file
        """
        self.db_path = db_path
        self.schema_cache = {}
        self.table_map_cache = None
        self._fk_options_cache = {}
        self.conn = sqlite3.connect(db_path)

    def close(self):
        """Close the persistent database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    # ------------------------------------------------------------------
    # Table / column metadata
    # ------------------------------------------------------------------

    def get_table_list(self):
        """
        Retrieve list of all user tables in the database.

        Returns:
            list[str]: Sorted list of table names

        Notes:
            Excludes SQLite system tables (sqlite_*).
        """
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name"
        )
        return [row[0] for row in cursor.fetchall()]

    def get_columns(self, table_name):
        """
        Fast retrieval of column names for a table using cache.

        Args:
            table_name (str): Name of the table

        Returns:
            list[str]: List of column names

        Notes:
            Uses schema_cache for performance. This method is optimized
            for UI operations that only need column metadata without data.
        """
        if table_name in self.schema_cache:
            return self.schema_cache[table_name]

        cursor = self.conn.cursor()
        cursor.execute(f"PRAGMA table_info([{table_name}])")
        columns = [col[1] for col in cursor.fetchall()]
        self.schema_cache[table_name] = columns
        return columns

    # ------------------------------------------------------------------
    # Foreign key resolution helpers
    # ------------------------------------------------------------------

    def _ensure_table_map(self, cursor):
        """Populate table_map_cache if not already loaded."""
        if not self.table_map_cache:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            self.table_map_cache = {r[0].upper(): r[0] for r in cursor.fetchall()}

    def _resolve_fk_target(self, suffix):
        """Resolve a foreign key suffix to its target table name.

        Searches for tables matching DYN_Suffix, STA_Suffix, GAM_Suffix,
        or the raw Suffix.

        Args:
            suffix (str): The part of the FK column name after 'fkID'

        Returns:
            str or None: The actual table name if found
        """
        for candidate in [f"DYN_{suffix}", f"STA_{suffix}", f"GAM_{suffix}", suffix]:
            if candidate.upper() in self.table_map_cache:
                return self.table_map_cache[candidate.upper()]
        return None

    def _resolve_fk_display(self, cursor, target_table):
        """Get primary key and display column for a FK target table.

        Args:
            cursor: SQLite cursor
            target_table (str): Name of the target table

        Returns:
            tuple: (primary_key_col, display_col) or (None, None)
        """
        cursor.execute(f"PRAGMA table_info([{target_table}])")
        target_info = cursor.fetchall()
        target_cols = [c[1] for c in target_info]

        target_pk = next(
            (c[1] for c in target_info if c[5] > 0),
            target_cols[0] if target_cols else "ID",
        )
        target_col = next(
            (c for c in _FK_DISPLAY_COLUMNS if c in target_cols),
            None,
        )
        if not target_col and len(target_cols) > 1:
            target_col = target_cols[1]

        return (target_pk, target_col) if target_col else (None, None)

    # ------------------------------------------------------------------
    # Search helper
    # ------------------------------------------------------------------

    @staticmethod
    def _build_search_clause(search_fields, search_term):
        """Build a WHERE clause for searching across all columns.

        Args:
            search_fields (list[str]): SQL expressions to search (e.g.
                ``["[table].[col]", "[_fk1].[name]"]``).
            search_term (str): Term to search for

        Returns:
            tuple: (where_sql, params)
        """
        where_sql = " OR ".join(
            f"CAST({field} AS TEXT) LIKE ?" for field in search_fields
        )
        params = [f"%{search_term}%"] * len(search_fields)
        return where_sql, params

    def _build_lookup_joins(self, cursor, table_name, columns):
        """Build SELECT fields and JOINs for FK lookup mode.

        Returns:
            tuple: (select_fields, joins) where select_fields[i] is the
            SQL expression for column i and joins is a list of JOIN clauses.
        """
        self._ensure_table_map(cursor)
        select_fields = [f"[{table_name}].[{c}]" for c in columns]
        joins = []
        for i, col in enumerate(columns):
            if col.startswith("fkID") and len(col) > 4:
                target_table = self._resolve_fk_target(col[4:])
                if target_table:
                    try:
                        pk, display = self._resolve_fk_display(cursor, target_table)
                        if display:
                            alias = f"_fk{i}"
                            select_fields[i] = f"[{alias}].[{display}]"
                            joins.append(
                                f"LEFT JOIN [{target_table}] [{alias}] "
                                f"ON [{alias}].[{pk}] = [{table_name}].[{col}]"
                            )
                    except Exception:
                        pass
        return select_fields, joins

    # ------------------------------------------------------------------
    # Data fetching
    # ------------------------------------------------------------------

    def fetch_data(self, table_name, search_term=None, lookup=False,
                   limit=None, offset=0, sort_col=None, sort_reverse=False):
        """
        Fetch data from a table with optional filtering, lookup, sorting, and pagination.

        Args:
            table_name (str): Name of the table to query
            search_term (str, optional): Search term to filter across all columns.
            lookup (bool, optional): If True, resolve foreign keys to display names.
            limit (int, optional): Maximum number of rows to return.
            offset (int, optional): Number of rows to skip (for pagination).
            sort_col (str, optional): Column name to sort by.
            sort_reverse (bool, optional): If True, sort descending.

        Returns:
            tuple: (columns, rows) where columns is list[str] and rows is list[tuple]
        """
        cursor = self.conn.cursor()

        columns = self.get_columns(table_name)
        select_fields = [f"[{table_name}].[{c}]" for c in columns]
        joins = []

        if lookup:
            select_fields, joins = self._build_lookup_joins(
                cursor, table_name, columns)

        query_cols = ", ".join(select_fields)
        join_clause = " ".join(joins)
        sql = f"SELECT {query_cols} FROM [{table_name}] {join_clause}"
        params = []

        if search_term:
            where_sql, params = self._build_search_clause(
                select_fields, search_term)
            sql += f" WHERE {where_sql}"

        if sort_col:
            sql += f" ORDER BY [{table_name}].[{sort_col}] {'DESC' if sort_reverse else 'ASC'}"

        if limit is not None:
            sql += f" LIMIT {limit} OFFSET {offset}"

        cursor.execute(sql, params)
        return columns, cursor.fetchall()

    def get_row_count(self, table_name, search_term=None, lookup=False):
        """
        Get total number of rows in a table, optionally filtered by search term.

        Args:
            table_name (str): Name of the table
            search_term (str, optional): Search term to filter across all columns.
            lookup (bool, optional): If True, search FK display values too.

        Returns:
            int: Number of rows matching the criteria
        """
        cursor = self.conn.cursor()
        if search_term:
            columns = self.get_columns(table_name)
            search_fields = [f"[{table_name}].[{c}]" for c in columns]
            joins = []
            if lookup:
                search_fields, joins = self._build_lookup_joins(
                    cursor, table_name, columns)
            join_clause = " ".join(joins)
            where_sql, params = self._build_search_clause(
                search_fields, search_term)
            cursor.execute(
                f"SELECT COUNT(*) FROM [{table_name}] {join_clause} WHERE {where_sql}",
                params,
            )
        else:
            cursor.execute(f"SELECT COUNT(*) FROM [{table_name}]")
        return cursor.fetchone()[0]

    # ------------------------------------------------------------------
    # Single-row operations
    # ------------------------------------------------------------------

    def get_max_id(self, table, id_column):
        """
        Get the next available ID value for a table (max + 1).

        Args:
            table (str): Table name
            id_column (str): Name of the ID column

        Returns:
            int: Next available ID (current maximum + 1, or 1 if table is empty)
        """
        cursor = self.conn.cursor()
        cursor.execute(f"SELECT MAX([{id_column}]) FROM [{table}]")
        result = cursor.fetchone()[0]
        return (int(result) if result is not None else 0) + 1

    def get_row_data(self, table, pk_col, pk_val):
        """
        Get full row data for a specific primary key.

        Args:
            table (str): Table name
            pk_col (str): Primary key column name
            pk_val: Primary key value

        Returns:
            tuple: Row values
        """
        cursor = self.conn.cursor()
        cursor.execute(f"SELECT * FROM [{table}] WHERE [{pk_col}]=?", (pk_val,))
        return cursor.fetchone()

    def get_rows_data(self, table, pk_col, pk_vals):
        """
        Fetch multiple rows by primary key values in a single query.

        Args:
            table (str): Table name
            pk_col (str): Primary key column name
            pk_vals (list): List of primary key values to fetch

        Returns:
            dict: Mapping of pk_val -> tuple of row values
        """
        result = {}
        for i in range(0, len(pk_vals), DB_CHUNK_SIZE):
            chunk = pk_vals[i:i + DB_CHUNK_SIZE]
            placeholders = ", ".join(["?"] * len(chunk))
            cursor = self.conn.cursor()
            cursor.execute(
                f"SELECT * FROM [{table}] WHERE [{pk_col}] IN ({placeholders})",
                chunk,
            )
            for row in cursor.fetchall():
                result[row[0]] = row
        return result

    def update_cell(self, table, column, value, pk_col, pk_val):
        """
        Update a single cell in the database.

        Args:
            table (str): Table name
            column (str): Column name to update
            value: New value to set
            pk_col (str): Primary key column name
            pk_val: Primary key value identifying the row
        """
        self.conn.execute(
            f"UPDATE [{table}] SET [{column}]=? WHERE [{pk_col}]=?",
            (value, pk_val),
        )
        self.conn.commit()
        self._fk_options_cache.clear()

    def delete_row(self, table, pk_col, pk_val):
        """
        Delete a row from the database.

        Args:
            table (str): Table name
            pk_col (str): Primary key column name
            pk_val: Primary key value identifying the row to delete
        """
        self.conn.execute(f"DELETE FROM [{table}] WHERE [{pk_col}]=?", (pk_val,))
        self.conn.commit()
        self._fk_options_cache.clear()

    def delete_rows(self, table, pk_col, pk_vals):
        """
        Delete multiple rows from the database.

        Args:
            table (str): Table name
            pk_col (str): Primary key column name
            pk_vals (list): List of primary key values to delete
        """
        for i in range(0, len(pk_vals), DB_CHUNK_SIZE):
            chunk = pk_vals[i:i + DB_CHUNK_SIZE]
            placeholders = ", ".join(["?"] * len(chunk))
            self.conn.execute(
                f"DELETE FROM [{table}] WHERE [{pk_col}] IN ({placeholders})",
                chunk,
            )
        self.conn.commit()
        self._fk_options_cache.clear()

    def insert_row(self, table, columns, values):
        """
        Insert a new row into the database.

        Args:
            table (str): Table name
            columns (list[str]): List of column names
            values (list): List of values corresponding to columns
        """
        placeholders = ", ".join(["?"] * len(values))
        col_names = ", ".join(f"[{c}]" for c in columns)
        self.conn.execute(
            f"INSERT INTO [{table}] ({col_names}) VALUES ({placeholders})",
            values,
        )
        self.conn.commit()
        self._fk_options_cache.clear()

    # ------------------------------------------------------------------
    # Foreign key dropdown options
    # ------------------------------------------------------------------

    def invalidate_fk_cache(self, fk_column=None):
        """Clear FK options cache, optionally for a specific column only."""
        if fk_column:
            self._fk_options_cache.pop(fk_column, None)
        else:
            self._fk_options_cache.clear()

    def get_fk_options(self, fk_column):
        """
        Get dropdown options for a foreign key column.

        Args:
            fk_column (str): Foreign key column name (must start with 'fkID')

        Returns:
            dict or None: Dictionary mapping display names to IDs
        """
        if not fk_column.startswith("fkID") or len(fk_column) <= 4:
            return None

        if fk_column in self._fk_options_cache:
            return self._fk_options_cache[fk_column]

        cursor = self.conn.cursor()
        self._ensure_table_map(cursor)

        target_table = self._resolve_fk_target(fk_column[4:])
        if not target_table:
            return None

        try:
            pk, display = self._resolve_fk_display(cursor, target_table)
            if display:
                cursor.execute(
                    f"SELECT [{display}], [{pk}] FROM [{target_table}] "
                    f"ORDER BY [{display}]"
                )
                result = {
                    str(row[0]): row[1]
                    for row in cursor.fetchall()
                    if row[0] is not None
                }
                self._fk_options_cache[fk_column] = result
                return result
        except Exception:
            pass

        return None
