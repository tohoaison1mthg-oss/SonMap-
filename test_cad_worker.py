"""Real PowerShell transport tests; no DGN or MDB access."""
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from cad_worker import CadWorker


@unittest.skipUnless(os.name=='nt', 'Windows PowerShell bridge')
class WorkerTests(unittest.TestCase):
    def test_reuse_exit_errors_unicode_and_no_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            shutil.copyfile(Path(__file__).with_name('cad_worker.ps1'),root/'cad_worker.ps1')
            (root/'sample.ps1').write_text('''param([string]$Value,[int]$Code=0)
if(-not ('SonMapWorkerTestCounter' -as [type])){Add-Type 'public class SonMapWorkerTestCounter {public static int Count=0;}'}
[SonMapWorkerTestCounter]::Count++
[Console]::Write('raw:')
Write-Output ($Value+':'+[SonMapWorkerTestCounter]::Count)
exit $Code
''',encoding='utf-8-sig')
            (root/'throw.ps1').write_text("throw 'expected failure'",encoding='utf-8-sig')
            worker=CadWorker(root)
            try:
                ok,output=worker.run('sample.ps1',['-Value','Nguyễn Văn Đặng'])
                self.assertTrue(ok);self.assertIn('Nguyễn Văn Đặng:1',output)
                pid=worker.process.pid
                ok,output=worker.run('sample.ps1',['-Value','next','-Code','7'])
                self.assertFalse(ok);self.assertIn('next:2',output)
                ok,output=worker.run('throw.ps1',[])
                self.assertFalse(ok);self.assertIn('expected failure',output)
                ok,output=worker.run('sample.ps1',['-Value','after'])
                self.assertTrue(ok);self.assertIn('after:3',output)
                self.assertEqual(worker.process.pid,pid)
                ok,_=worker.run('../sample.ps1',[])
                self.assertFalse(ok)
            finally:
                worker.close()

    def test_transport_failure_is_not_replayed(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            shutil.copyfile(Path(__file__).with_name('cad_worker.ps1'),root/'cad_worker.ps1')
            (root/'crash.ps1').write_text("Add-Content -LiteralPath (Join-Path $PSScriptRoot 'calls.txt') -Value 'once'; [Environment]::Exit(9)",encoding='utf-8-sig')
            worker=CadWorker(root)
            try:
                with self.assertRaisesRegex(RuntimeError,'không được tự chạy lại'):
                    worker.run('crash.ps1',[],timeout=10)
                self.assertEqual((root/'calls.txt').read_text().splitlines(),['once'])
            finally:
                worker.close()
