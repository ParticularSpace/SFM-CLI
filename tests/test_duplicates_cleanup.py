import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import main


class DuplicateCleanupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        (self.folder / 'report.pdf').write_text('same')
        (self.folder / 'report (1).pdf').write_text('same')
        (self.folder / 'report (2).pdf').write_text('same')

    def test_keeps_original(self):
        groups = main.duplicate_groups(self.folder)
        self.assertEqual(len(groups), 1)
        self.assertEqual(sorted(groups[0], key=main.duplicate_sort_key)[0].name, 'report.pdf')

    def test_cancel_keeps_everything(self):
        groups = main.duplicate_groups(self.folder)
        with patch.dict('sys.modules', {'send2trash': SimpleNamespace(send2trash=lambda x: None)}):
            with patch('builtins.input', return_value='no'), contextlib.redirect_stdout(io.StringIO()):
                main.trash_duplicates(groups)
        self.assertEqual(len(list(self.folder.iterdir())), 3)

    def test_confirm_trashes_only_extras(self):
        groups = main.duplicate_groups(self.folder)
        sent = []
        fake = SimpleNamespace(send2trash=lambda x: sent.append(Path(x).name))
        with patch.dict('sys.modules', {'send2trash': fake}):
            with patch('builtins.input', return_value='DELETE'), contextlib.redirect_stdout(io.StringIO()):
                main.trash_duplicates(groups)
        self.assertEqual(set(sent), {'report (1).pdf', 'report (2).pdf'})

    def test_changed_file_is_skipped(self):
        groups = main.duplicate_groups(self.folder)
        (self.folder / 'report (1).pdf').write_text('changed')
        sent = []
        fake = SimpleNamespace(send2trash=lambda x: sent.append(Path(x).name))
        with patch.dict('sys.modules', {'send2trash': fake}):
            with patch('builtins.input', return_value='DELETE'), contextlib.redirect_stdout(io.StringIO()):
                main.trash_duplicates(groups)
        self.assertEqual(sent, ['report (2).pdf'])


if __name__ == '__main__':
    unittest.main()
