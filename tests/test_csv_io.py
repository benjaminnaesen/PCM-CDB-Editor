"""
Unit tests for core.csv_io module.

Run with: python -m unittest tests.test_csv_io
"""

import unittest
import os
import tempfile
import sqlite3
import csv
from core.csv_io import export_table, import_table_from_csv, export_to_csv, import_from_csv


class TestCsvIO(unittest.TestCase):
    """Test suite for CSV import/export functions."""

    def setUp(self):
        """Create temporary database and CSV files for testing."""
        # Create temp database
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
        cursor.execute("INSERT INTO test_table VALUES (3, 'Item3', 300)")
        conn.commit()
        conn.close()

        # Create temp directory for CSV files
        self.csv_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        if os.path.exists(self.db_file.name):
            try:
                os.remove(self.db_file.name)
            except PermissionError:
                pass
        if os.path.exists(self.csv_dir):
            shutil.rmtree(self.csv_dir, ignore_errors=True)

    def test_export_table(self):
        """Test exporting a single table to CSV."""
        csv_path = os.path.join(self.csv_dir, "export_test.csv")
        export_table(self.db_file.name, "test_table", csv_path)

        # Verify file exists
        self.assertTrue(os.path.exists(csv_path))

        # Verify CSV content
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)

        # Check headers
        self.assertEqual(rows[0], ['id', 'name', 'value'])

        # Check data rows
        self.assertEqual(len(rows), 4)  # 1 header + 3 data rows
        self.assertEqual(rows[1], ['1', 'Item1', '100'])
        self.assertEqual(rows[2], ['2', 'Item2', '200'])
        self.assertEqual(rows[3], ['3', 'Item3', '300'])

    def test_import_table_from_csv(self):
        """Test importing CSV data into existing table."""
        # Create CSV file
        csv_path = os.path.join(self.csv_dir, "import_test.csv")
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'name', 'value'])
            writer.writerow([10, 'ImportedItem1', 1000])
            writer.writerow([20, 'ImportedItem2', 2000])

        # Import CSV (replaces all existing data)
        import_table_from_csv(self.db_file.name, "test_table", csv_path)

        # Verify data was replaced
        conn = sqlite3.connect(self.db_file.name)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM test_table ORDER BY id")
        rows = cursor.fetchall()
        conn.close()

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0], (10, 'ImportedItem1', 1000))
        self.assertEqual(rows[1], (20, 'ImportedItem2', 2000))

    def test_export_to_csv_all_tables(self):
        """Test exporting all tables to CSV folder."""
        # Add another table
        conn = sqlite3.connect(self.db_file.name)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE another_table (id INTEGER, data TEXT)")
        cursor.execute("INSERT INTO another_table VALUES (1, 'data1')")
        conn.commit()
        conn.close()

        # Export all tables
        export_to_csv(self.db_file.name, self.csv_dir)

        # Verify files exist
        self.assertTrue(os.path.exists(os.path.join(self.csv_dir, "test_table.csv")))
        self.assertTrue(os.path.exists(os.path.join(self.csv_dir, "another_table.csv")))

        # Verify test_table.csv content
        with open(os.path.join(self.csv_dir, "test_table.csv"), 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        self.assertEqual(len(rows), 4)  # 1 header + 3 data rows

    def test_import_from_csv_folder(self):
        """Test importing multiple CSV files from folder."""
        # Create CSV files
        with open(os.path.join(self.csv_dir, "test_table.csv"), 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'name', 'value'])
            writer.writerow([99, 'NewItem', 9900])

        # Import all CSVs
        import_from_csv(self.db_file.name, self.csv_dir)

        # Verify data was imported
        conn = sqlite3.connect(self.db_file.name)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM test_table")
        rows = cursor.fetchall()
        conn.close()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0], (99, 'NewItem', 9900))

    def test_csv_utf8_encoding(self):
        """Test CSV export/import with UTF-8 characters."""
        # Add row with UTF-8 characters
        conn = sqlite3.connect(self.db_file.name)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO test_table VALUES (4, 'Café ☕', 400)")
        conn.commit()
        conn.close()

        # Export
        csv_path = os.path.join(self.csv_dir, "utf8_test.csv")
        export_table(self.db_file.name, "test_table", csv_path)

        # Import to new table
        conn = sqlite3.connect(self.db_file.name)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE import_test (id INTEGER, name TEXT, value INTEGER)")
        conn.commit()
        conn.close()

        import_table_from_csv(self.db_file.name, "import_test", csv_path)

        # Verify UTF-8 preserved
        conn = sqlite3.connect(self.db_file.name)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM import_test WHERE id=4")
        result = cursor.fetchone()
        conn.close()

        self.assertEqual(result[0], 'Café ☕')

    def test_import_empty_csv(self):
        """Test importing CSV with only headers (no data rows)."""
        csv_path = os.path.join(self.csv_dir, "empty.csv")
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'name', 'value'])

        # Should clear table but not error
        import_table_from_csv(self.db_file.name, "test_table", csv_path)

        # Verify table is empty
        conn = sqlite3.connect(self.db_file.name)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM test_table")
        count = cursor.fetchone()[0]
        conn.close()

        self.assertEqual(count, 0)


if __name__ == '__main__':
    unittest.main()
