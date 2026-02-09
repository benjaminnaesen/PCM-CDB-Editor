"""
Unit tests for core.app_state module.

Run with: python -m unittest tests.test_app_state
"""

import unittest
import os
import json
import tempfile
from core.app_state import AppState


class TestAppState(unittest.TestCase):
    """Test suite for AppState class."""

    def setUp(self):
        """Create temporary settings file for testing."""
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        self.temp_file.close()
        self.state = AppState(self.temp_file.name)

    def tearDown(self):
        """Clean up temporary file."""
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)

    def test_load_default_settings(self):
        """Test that default settings are loaded when file doesn't exist."""
        self.assertEqual(self.state.favorites, [])
        self.assertEqual(self.state.recents, [])
        self.assertIn("window_size", self.state.settings)

    def test_save_and_load_settings(self):
        """Test saving and reloading settings."""
        self.state.favorites = ["DYN_team", "DYN_cyclist"]
        self.state.save_settings("1200x800", False, True)

        # Create new instance to test persistence
        state2 = AppState(self.temp_file.name)
        self.assertEqual(state2.favorites, ["DYN_team", "DYN_cyclist"])
        self.assertEqual(state2.settings["window_size"], "1200x800")
        self.assertTrue(state2.settings["lookup_mode"])

    def test_add_recent(self):
        """Test adding recent files with limit of 10."""
        # Add 12 files
        for i in range(12):
            self.state.add_recent(f"file{i}.cdb")

        # Should only keep 10 most recent
        self.assertEqual(len(self.state.recents), 10)
        # Most recent should be first
        self.assertEqual(self.state.recents[0], "file11.cdb")

    def test_undo_redo(self):
        """Test undo/redo stack operations."""
        # Push an action
        self.state.push_undo("DYN_team", "name", "Old Name", "New Name", 1)

        # Undo should return the action
        action = self.state.undo()
        self.assertIsNotNone(action)
        self.assertEqual(action["old"], "Old Name")
        self.assertEqual(action["new"], "New Name")

        # Redo should return it again
        action = self.state.redo()
        self.assertIsNotNone(action)
        self.assertEqual(action["new"], "New Name")

    def test_push_undo_clears_redo(self):
        """Test that new edits clear redo stack."""
        self.state.push_undo("table", "col", "old1", "new1", 1)
        self.state.undo()

        # Redo stack should have one item
        self.assertEqual(len(self.state.redo_stack), 1)

        # New edit should clear redo
        self.state.push_undo("table", "col", "old2", "new2", 1)
        self.assertEqual(len(self.state.redo_stack), 0)


if __name__ == '__main__':
    unittest.main()
