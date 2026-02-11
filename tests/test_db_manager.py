"""
Unit tests for core.db_manager module.

Run with: python -m unittest tests.test_db_manager
"""

import unittest
import sqlite3
import tempfile
import os
from core.db_manager import DatabaseManager


class TestDatabaseManager(unittest.TestCase):
    """Test suite for DatabaseManager class."""

    def setUp(self):
        """Create temporary SQLite database for testing."""
        self.db_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sqlite')
        self.db_file.close()

        # Create test database with sample data
        conn = sqlite3.connect(self.db_file.name)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                name TEXT,
                value INTEGER
            )
        """)
        cursor.execute("INSERT INTO test_table VALUES (1, 'Item1', 100)")
        cursor.execute("INSERT INTO test_table VALUES (2, 'Item2', 200)")
        conn.commit()
        conn.close()

        self.db = DatabaseManager(self.db_file.name)

    def tearDown(self):
        """Clean up temporary database file."""
        # Remove reference to DatabaseManager to close connections
        self.db = None
        # Small delay to ensure Windows releases the file lock
        import time
        time.sleep(0.1)
        if os.path.exists(self.db_file.name):
            try:
                os.remove(self.db_file.name)
            except PermissionError:
                # On Windows, file might still be locked - ignore for cleanup
                pass

    def test_get_table_list(self):
        """Test retrieving table list."""
        tables = self.db.get_table_list()
        self.assertIn("test_table", tables)
        # Should not include system tables
        self.assertNotIn("sqlite_master", tables)

    def test_fetch_data(self):
        """Test fetching table data."""
        columns, rows = self.db.fetch_data("test_table")
        self.assertEqual(columns, ["id", "name", "value"])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0], (1, 'Item1', 100))

    def test_get_row_count(self):
        """Test counting rows in table."""
        count = self.db.get_row_count("test_table")
        self.assertEqual(count, 2)

    def test_update_cell(self):
        """Test updating a cell value."""
        self.db.update_cell("test_table", "name", "Updated", "id", 1)
        columns, rows = self.db.fetch_data("test_table")
        self.assertEqual(rows[0][1], "Updated")

    def test_delete_row(self):
        """Test deleting a row."""
        self.db.delete_row("test_table", "id", 1)
        count = self.db.get_row_count("test_table")
        self.assertEqual(count, 1)

    def test_insert_row(self):
        """Test inserting a new row."""
        self.db.insert_row("test_table", ["id", "name", "value"], [3, "Item3", 300])
        count = self.db.get_row_count("test_table")
        self.assertEqual(count, 3)

    def test_get_columns(self):
        """Test fast column retrieval using cache."""
        columns = self.db.get_columns("test_table")
        self.assertEqual(columns, ["id", "name", "value"])
        # Second call should use cache
        columns2 = self.db.get_columns("test_table")
        self.assertEqual(columns, columns2)

    def test_search_functionality(self):
        """Test search across all columns."""
        # Search for "Item1" should return 1 row
        columns, rows = self.db.fetch_data("test_table", search_term="Item1")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1], "Item1")

        # Search for "100" should return 1 row
        columns, rows = self.db.fetch_data("test_table", search_term="100")
        self.assertEqual(len(rows), 1)

        # Search for "Item" should return 2 rows
        columns, rows = self.db.fetch_data("test_table", search_term="Item")
        self.assertEqual(len(rows), 2)

        # Search for non-existent should return 0 rows
        columns, rows = self.db.fetch_data("test_table", search_term="NonExistent")
        self.assertEqual(len(rows), 0)

    def test_pagination(self):
        """Test pagination with limit and offset."""
        # Add more rows for pagination testing
        self.db.insert_row("test_table", ["id", "name", "value"], [3, "Item3", 300])
        self.db.insert_row("test_table", ["id", "name", "value"], [4, "Item4", 400])
        self.db.insert_row("test_table", ["id", "name", "value"], [5, "Item5", 500])

        # Test limit
        columns, rows = self.db.fetch_data("test_table", limit=2)
        self.assertEqual(len(rows), 2)

        # Test offset
        columns, rows = self.db.fetch_data("test_table", limit=2, offset=2)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][0], 3)  # Should start at ID 3

        # Test offset beyond data
        columns, rows = self.db.fetch_data("test_table", limit=2, offset=10)
        self.assertEqual(len(rows), 0)

    def test_sorting(self):
        """Test sorting by column."""
        # Sort by name ascending
        columns, rows = self.db.fetch_data("test_table", sort_col="name", sort_reverse=False)
        self.assertEqual(rows[0][1], "Item1")
        self.assertEqual(rows[1][1], "Item2")

        # Sort by name descending
        columns, rows = self.db.fetch_data("test_table", sort_col="name", sort_reverse=True)
        self.assertEqual(rows[0][1], "Item2")
        self.assertEqual(rows[1][1], "Item1")

        # Sort by value ascending
        columns, rows = self.db.fetch_data("test_table", sort_col="value", sort_reverse=False)
        self.assertEqual(rows[0][2], 100)
        self.assertEqual(rows[1][2], 200)

    def test_delete_rows_bulk(self):
        """Test bulk deletion of multiple rows."""
        # Add more rows
        self.db.insert_row("test_table", ["id", "name", "value"], [3, "Item3", 300])

        # Delete multiple rows
        self.db.delete_rows("test_table", "id", [1, 3])
        count = self.db.get_row_count("test_table")
        self.assertEqual(count, 1)

        # Verify remaining row
        columns, rows = self.db.fetch_data("test_table")
        self.assertEqual(rows[0][0], 2)

    def test_get_max_id(self):
        """Test getting next available ID."""
        max_id = self.db.get_max_id("test_table", "id")
        self.assertEqual(max_id, 3)  # Should be max(1,2) + 1

        # Test with empty table
        self.db.delete_rows("test_table", "id", [1, 2])
        max_id = self.db.get_max_id("test_table", "id")
        self.assertEqual(max_id, 1)  # Should be 1 for empty table

    def test_get_row_data(self):
        """Test fetching specific row by primary key."""
        row = self.db.get_row_data("test_table", "id", 1)
        self.assertEqual(row, (1, 'Item1', 100))

        # Test non-existent row
        row = self.db.get_row_data("test_table", "id", 999)
        self.assertIsNone(row)

    def test_get_row_count_with_search(self):
        """Test row count with search filter."""
        # Count with search
        count = self.db.get_row_count("test_table", search_term="Item1")
        self.assertEqual(count, 1)

        count = self.db.get_row_count("test_table", search_term="Item")
        self.assertEqual(count, 2)

        count = self.db.get_row_count("test_table", search_term="NonExistent")
        self.assertEqual(count, 0)

    def test_fk_lookup_no_fk_column(self):
        """Test FK lookup options returns None for non-FK columns."""
        options = self.db.get_fk_options("name")
        self.assertIsNone(options)

        options = self.db.get_fk_options("value")
        self.assertIsNone(options)


if __name__ == '__main__':
    unittest.main()
