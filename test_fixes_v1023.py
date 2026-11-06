import ctypes
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from topology_workflow import check_database_replaceable

ROOT=Path(__file__).resolve().parent


@unittest.skipUnless(os.name=='nt','Windows permissions and workspace')
class StartupFixTests(unittest.TestCase):
    def test_access_denied_reports_mdb_and_does_not_modify_permissions(self):
        kernel=MagicMock()
        kernel.CreateFileW.return_value=ctypes.c_void_p(-1).value
        with patch('ctypes.WinDLL',return_value=kernel),patch('ctypes.get_last_error',return_value=5):
            with self.assertRaisesRegex(PermissionError,'Modify.*') as caught:
                check_database_replaceable(ROOT/'example.mdb')
        self.assertIn('example.mdb',str(caught.exception))
        kernel.CloseHandle.assert_not_called()

    def test_workspace_can_be_generated_without_bentley_admin_access(self):
        with tempfile.TemporaryDirectory(prefix='SonMap space ') as folder:
            command=[str(Path(os.environ['WINDIR'])/'System32/WindowsPowerShell/v1.0/powershell.exe'),
                     '-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'v8i_workspace.ps1'),'-Root',folder]
            first=subprocess.run(command,capture_output=True,text=True,check=True).stdout
            self.assertIn('-wuSonMap',first)
            self.assertIn('-wpSonMap',first)
            self.assertIn('-ws_USTN_USER=',first)
            ucf=Path(folder)/'workspace/Users/SonMap.ucf'
            pcf=Path(folder)/'workspace/Projects/SonMap.pcf'
            self.assertTrue(pcf.is_file())
            content=ucf.read_text()
            self.assertIn('MS_OPENV7 = 3',content)
            self.assertNotIn('MS_INIT',content)
            self.assertNotIn('MS_VBAAUTOLOADPROJECTS',content)
            self.assertEqual(subprocess.run(command,capture_output=True,text=True,check=True).stdout,first)
            self.assertEqual(ucf.read_text(),content)


if __name__=='__main__':unittest.main()
