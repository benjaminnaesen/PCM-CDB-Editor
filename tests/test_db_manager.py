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

    # TODO: Add tests for search functionality
    # TODO: Add tests for pagination (limit/offset)
    # TODO: Add tests for sorting
    # TODO: Add tests for FK lookups (requires more complex test database)


if __name__ == '__main__':
    unittest.main()
