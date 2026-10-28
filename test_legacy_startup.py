import hashlib
import json
import os
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch

from legacy_startup import MARKER, repair, restore

OLD = b"from pathlib import Path\ndef gui(win):\n    win.title('SonMap+ V10.3')\nPath(__file__).with_suffix('.ran').touch()\n"


class LegacyStartupTests(unittest.TestCase):
    def test_direct_vba_and_legacy_launcher_both_forward_to_installed_app(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            legacy = base / 'ThanhTanApp'
            installed = base / 'SonMapPlus' / 'App'
            legacy.mkdir()
            (installed / '.venv-topology' / 'Scripts').mkdir(parents=True)
            (installed / 'VERSION').write_text('10.15')
            (installed / 'launch.py').touch()
            python = installed / '.venv-topology' / 'Scripts' / 'pythonw.exe'
            python.touch()
            (legacy / 'app.py').write_bytes(OLD)
            (legacy / 'launch.py').write_text("import runpy\nfrom pathlib import Path\nrunpy.run_path(str(Path(__file__).parent / 'app.py'), run_name='__main__')")
            backup = repair(legacy)
            self.assertEqual((backup / 'app.py').read_bytes(), OLD)
            for entry in ('app.py', 'launch.py'):
                with self.subTest(entry=entry), patch.dict(os.environ, LOCALAPPDATA=folder), patch('subprocess.Popen') as spawn:
                    with self.assertRaises(SystemExit) as caught:
                        runpy.run_path(str(legacy / entry), run_name='__main__')
                    self.assertEqual(caught.exception.code, 0)
                    self.assertEqual(spawn.call_args.args[0], [str(python), str(installed / 'launch.py')])
                    self.assertEqual(spawn.call_args.kwargs['cwd'], str(installed))
            self.assertFalse((legacy / 'app.ran').exists())
            self.assertIsNone(repair(legacy))
            redirected = (legacy / 'app.py').read_bytes()
            undo = restore(legacy, backup)
            self.assertEqual((legacy / 'app.py').read_bytes(), OLD)
            self.assertEqual((undo / 'app.py').read_bytes(), redirected)
            restore(legacy, undo)
            self.assertEqual((legacy / 'app.py').read_bytes(), redirected)

    def test_no_installed_app_keeps_old_launch_working_and_preserves_private_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / 'ThanhTanApp'
            root.mkdir()
            (root / 'app.py').write_bytes(OLD)
            for name in ('settings.json', 'user.mdb', 'user.dgn'):
                (root / name).write_bytes(b'unchanged private data')
            repair(root)
            with patch.dict(os.environ, LOCALAPPDATA=folder), patch('subprocess.Popen') as spawn:
                runpy.run_path(str(root / 'app.py'), run_name='__main__')
                spawn.assert_not_called()
            self.assertTrue((root / 'app.ran').exists())
            for name in ('settings.json', 'user.mdb', 'user.dgn'):
                self.assertEqual((root / name).read_bytes(), b'unchanged private data')

    def test_unknown_or_modern_app_is_untouched_and_damaged_backup_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'app.py').write_bytes(b'print("modern app")')
            self.assertIsNone(repair(root))
            self.assertEqual((root / 'app.py').read_bytes(), b'print("modern app")')
            (root / 'app.py').write_bytes(OLD)
            backup = repair(root)
            (backup / 'app.py').write_bytes(b'corrupt')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                restore(root, backup)
            self.assertTrue((root / 'app.py').read_text(encoding='utf-8-sig').startswith(MARKER))
