import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import app
from installer.package_update import ROOT, build, release_version


class ReleaseTests(unittest.TestCase):
    def test_window_title_uses_single_version_source(self):
        self.assertEqual(app.APP_TITLE,'SonMap+ V'+release_version())
        source=(ROOT/'app.py').read_text(encoding='utf-8')
        self.assertIn('win.title(APP_TITLE)',source)
        self.assertIn('FindWindowW(None,APP_TITLE)',source)

    def test_installer_contains_verified_source_and_no_private_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            path=build(directory)
            self.assertEqual(path.name,'SonMapPlus_V'+release_version().replace('.','_')+'_Update.zip')
            with zipfile.ZipFile(path) as outer:
                self.assertEqual(set(outer.namelist()),{'Cai_dat.cmd','Cai_dat.ps1','payload.zip','HUONG_DAN.txt','Kiem_tra_V8i.cmd','Kiem_tra_quet_DGN.cmd'})
                with zipfile.ZipFile(io.BytesIO(outer.read('payload.zip'))) as payload:
                    self.assertEqual(payload.read('VERSION').decode().strip(),release_version())
                    for required in ('dgn_view.ps1','update_parcel_attributes.ps1'):
                        self.assertIn(required,payload.namelist())
                    for required in ['installer/restore.ps1','installer/restore.cmd','CHANGELOG.md','AGENTS.md','check_connection.ps1','python_probe.py','python_setup.ps1','dgn_scan.ps1','test_scan_v8i.ps1','dgn_interop.ps1','test_dgn_interop.ps1','parcel_info.py','parcel_info_ui.py','pick_dgn_point.ps1','update_parcel_owner.ps1']:
                        self.assertIn(required,payload.namelist())
                    entries=json.loads(payload.read('MANIFEST.json'))
                    self.assertEqual(set(payload.namelist()),{entry['file'] for entry in entries}|{'MANIFEST.json'})
                    for entry in entries:self.assertEqual(hashlib.sha256(payload.read(entry['file'])).hexdigest(),entry['sha256'])
                    for name in payload.namelist():
                        self.assertNotIn(name.split('/')[0],('data','assets','runtime','exports','.git','.venv-topology'))
                        self.assertFalse(name.lower().endswith(('.mdb','.dgn','.mvba','.dll')))
            # A release artifact is immutable; don't silently reuse a versioned file name.
            with self.assertRaises(FileExistsError):build(directory)

if __name__=='__main__':unittest.main()
