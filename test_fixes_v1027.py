import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from parcel_actions import reference_context

class ExportContextTests(unittest.TestCase):
    def test_reference_recovers_original_source_after_active_dgn_becomes_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'data').mkdir()
            source=root/'source.dgn';target=root/'output.dgn'
            source.write_bytes(b'source');target.write_bytes(b'output')
            (root/'data/runtime.txt').write_text(str(source)+'\nfixture.mdb',encoding='utf-16')
            (root/'data/result.txt').write_text('OK\t116/7/5\t'+str(target),encoding='utf-16')
            result=reference_context(root,str(target),str(target))
            self.assertEqual(result,{'source':str(source),'target':str(target)})
            (root/'data/result.txt').write_text('ERROR\t116/7/5\tfailed',encoding='utf-16')
            with self.assertRaises(ValueError):reference_context(root,str(target),str(target))

class NativeTopologyTests(unittest.TestCase):
    def test_native_write_commits_verified_mdb_without_replaying_legacy_write(self):
        from test_database_topology import DirectUpdateTests
        import topology_workflow as flow
        with tempfile.TemporaryDirectory() as folder:
            path,source,mdb,old,delta=DirectUpdateTests().fixture(folder)
            project=json.loads(path.read_text());project['native_write']=True;flow.save_project(path,project)
            def execute(script,*args):
                self.assertEqual(script,'update_mdb_topology.ps1')
                Path(args[args.index('-MdbPath')+1]).write_bytes(b'new-mdb')
            def inspect(target):
                target=Path(target);rows=old if target.read_bytes()==b'old-mdb' else delta['final_rows']
                return {'path':str(target),'sha256':flow.digest(target),'rows':rows,'count':len(rows)}
            def native(action,path,**kwargs):
                self.assertEqual(action,'topology');source.write_bytes(b'new-dgn')
            with patch.object(flow,'powershell',side_effect=execute),patch.object(flow,'inspect_database',side_effect=inspect),patch('cad_bridge.request',side_effect=native) as request:
                result=flow.apply_current(path,mdb)
            self.assertEqual(request.call_count,1)
            self.assertEqual(result['after_count'],2)
            self.assertEqual(mdb.read_bytes(),b'new-mdb')
            self.assertIn('dgn_write_seconds',result['timing'])

    def test_native_failure_restores_dgn_and_keeps_original_mdb(self):
        from test_database_topology import DirectUpdateTests
        import topology_workflow as flow
        with tempfile.TemporaryDirectory() as folder:
            path,source,mdb,old,delta=DirectUpdateTests().fixture(folder)
            project=json.loads(path.read_text());project['native_write']=True;flow.save_project(path,project)
            def execute(script,*args):
                if script=='update_mdb_topology.ps1':Path(args[args.index('-MdbPath')+1]).write_bytes(b'new-mdb')
                else:
                    self.assertEqual(args[args.index('-Action')+1],'RestoreActive');source.write_bytes(b'old-dgn')
            def inspect(target):
                target=Path(target);rows=old if target.read_bytes()==b'old-mdb' else delta['final_rows']
                return {'path':str(target),'sha256':flow.digest(target),'rows':rows,'count':len(rows)}
            def native(*args,**kwargs):source.write_bytes(b'partial-dgn');raise RuntimeError('native failed')
            with patch.object(flow,'powershell',side_effect=execute),patch.object(flow,'inspect_database',side_effect=inspect),patch('cad_bridge.request',side_effect=native) as request:
                with self.assertRaisesRegex(RuntimeError,'native failed'):flow.apply_current(path,mdb)
            self.assertEqual(request.call_count,1)
            self.assertEqual(source.read_bytes(),b'old-dgn');self.assertEqual(mdb.read_bytes(),b'old-mdb')
