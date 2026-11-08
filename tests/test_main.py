import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import main


class SFMCLITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)

    def test_category(self):
        self.assertEqual(main.file_category(Path("test.PDF")), "Documents")
        self.assertEqual(main.file_category(Path("unknown.xyz")), "Other")

    def test_organize_moves_file(self):
        original = self.folder / "report.pdf"
        original.write_text("example")
        with patch("builtins.input", return_value="YES"), contextlib.redirect_stdout(io.StringIO()):
            main.organize_files(self.folder)
        self.assertFalse(original.exists())
        self.assertTrue((self.folder / "Documents" / "report.pdf").exists())

    def test_cancel_does_not_move(self):
        original = self.folder / "report.pdf"
        original.write_text("example")
        with patch("builtins.input", return_value="no"), contextlib.redirect_stdout(io.StringIO()):
            main.organize_files(self.folder)
        self.assertTrue(original.exists())
        self.assertFalse((self.folder / "Documents" / "report.pdf").exists())

    def test_existing_name_is_not_overwritten(self):
        (self.folder / "Documents").mkdir()
        (self.folder / "Documents" / "report.pdf").write_text("old")
        (self.folder / "report.pdf").write_text("new")
        with patch("builtins.input", return_value="YES"), contextlib.redirect_stdout(io.StringIO()):
            main.organize_files(self.folder)
        self.assertEqual((self.folder / "Documents" / "report.pdf").read_text(), "old")
        self.assertEqual((self.folder / "Documents" / "report (1).pdf").read_text(), "new")

    def test_duplicates(self):
        (self.folder / "a.txt").write_text("same")
        (self.folder / "b.txt").write_text("same")
        output = io.StringIO()
        with patch("builtins.input", return_value="0"), contextlib.redirect_stdout(output):
            main.find_duplicates(self.folder)
        self.assertIn("Group 1", output.getvalue())


    def test_organize_shows_confirmation(self):
        (self.folder / "sample.pdf").write_text("sample")
        output = io.StringIO()
        with patch("builtins.input", return_value="YES"), contextlib.redirect_stdout(output):
            main.organize_files(self.folder)
        self.assertIn("[RESULT] Organization finished: 1 of 1 files moved.", output.getvalue())

    def test_duplicate_scan_shows_confirmation(self):
        (self.folder / "one.txt").write_text("same")
        (self.folder / "two.txt").write_text("same")
        output = io.StringIO()
        with patch("builtins.input", return_value="0"), contextlib.redirect_stdout(output):
            main.find_duplicates(self.folder)
        self.assertIn("[RESULT] Duplicate scan complete: 1 duplicate group(s) found.", output.getvalue())


if __name__ == "__main__":
    unittest.main()
