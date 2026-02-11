"""
Unit tests for core.converter module.

Run with: python -m unittest tests.test_converter

Note: Tests use mocked subprocess calls to avoid dependency on SQLiteExporter.exe
"""

import unittest
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock
import core.converter as converter


class TestConverter(unittest.TestCase):
    """Test suite for converter functions with mocked external tool."""

    def setUp(self):
        """Create temporary files for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.cdb_path = os.path.join(self.temp_dir, "test.cdb")
        self.sqlite_path = os.path.join(self.temp_dir, "test.sqlite")

        # Create dummy CDB file
        with open(self.cdb_path, 'w') as f:
            f.write("dummy cdb content")

    def tearDown(self):
        """Clean up temporary files."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('core.converter.subprocess.run')
    @patch('core.converter.os.path.exists')
    @patch('core.converter.os.remove')
    @patch('core.converter.shutil.move')
    def test_export_cdb_to_sqlite_success(self, mock_move, mock_remove, mock_exists, mock_run):
        """Test successful CDB to SQLite conversion."""
        # Mock TOOL_PATH and temp file exist
        mock_exists.return_value = True

        # Mock subprocess success
        mock_run.return_value = MagicMock(returncode=0)

        # Call function
        result = converter.export_cdb_to_sqlite(self.cdb_path)

        # Verify subprocess was called with correct args
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        self.assertIn("-export", args)
        self.assertIn(os.path.abspath(self.cdb_path), args)

        # Verify file move was attempted
        mock_move.assert_called_once()

        # Verify return value
        self.assertIn("pcm_working_db.sqlite", result)

    @patch('core.converter.subprocess.run')
    @patch('core.converter.os.path.exists')
    def test_export_cdb_to_sqlite_tool_not_found(self, mock_exists, mock_run):
        """Test export fails when SQLiteExporter.exe not found."""
        # Mock TOOL_PATH doesn't exist
        mock_exists.return_value = False

        # Should raise FileNotFoundError
        with self.assertRaises(FileNotFoundError) as context:
            converter.export_cdb_to_sqlite(self.cdb_path)

        self.assertIn("SQLiteExporter tool not found", str(context.exception))

    @patch('core.converter.subprocess.run')
    @patch('core.converter.os.path.exists')
    @patch('core.converter.os.remove')
    @patch('core.converter.shutil.copy2')
    def test_import_sqlite_to_cdb_success(self, mock_copy, mock_remove, mock_exists, mock_run):
        """Test successful SQLite to CDB conversion."""
        # Create temp sqlite file
        with open(self.sqlite_path, 'w') as f:
            f.write("dummy sqlite content")

        target_cdb = os.path.join(self.temp_dir, "output.cdb")

        # Mock subprocess success
        mock_run.return_value = MagicMock(returncode=0)
        mock_exists.return_value = True

        # Call function
        converter.import_sqlite_to_cdb(self.sqlite_path, target_cdb)

        # Verify subprocess was called
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        self.assertIn("-import", args)

        # Verify file copy was attempted
        mock_copy.assert_called_once()

    @patch('core.converter.subprocess.run')
    @patch('core.converter.os.path.exists')
    def test_export_subprocess_failure(self, mock_exists, mock_run):
        """Test export handles subprocess errors."""
        mock_exists.return_value = True

        # Mock subprocess failure
        from subprocess import CalledProcessError
        mock_run.side_effect = CalledProcessError(1, 'cmd')

        # Should raise CalledProcessError
        with self.assertRaises(CalledProcessError):
            converter.export_cdb_to_sqlite(self.cdb_path)

    def test_tool_path_configuration(self):
        """Test that TOOL_PATH is configured correctly."""
        # Verify TOOL_PATH exists in module
        self.assertTrue(hasattr(converter, 'TOOL_PATH'))
        self.assertIn("SQLiteExporter.exe", converter.TOOL_PATH)


if __name__ == '__main__':
    unittest.main()
