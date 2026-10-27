import copy
import unittest
from topology import export_rows
from database_topology import reconcile, scope_splits
from test_topology import project,line,rect,text


def old_rows():
    p=project([line(rect(x=0,y=0))],[text('12',5,5,13)],label_levels={'TCT':'13'})
    p['parcels'][0].update(ID=20,ToBD=89,TenChu='Original owner',LRD='LUC')
    return export_rows(p)


class DatabaseTopologyTests(unittest.TestCase):
    def test_scope_split_ignores_only_errors_outside_complete_parent(self):
        new=project([line(rect(x=0,y=0)),line([(5,0),(5,10)]),line([(50,50),(51,51)])],label_levels={})
        scoped=scope_splits(new,old_rows())
        self.assertEqual(len(scoped['parcels']),2)
        self.assertEqual(scoped['issues'],[])
        self.assertTrue(any(i['code']=='DANGLE' for i in scoped['excluded_issues']))
        self.assertEqual(reconcile(scoped,old_rows())['after_count'],2)
        self.assertNotIn('scope_rings',new)

    def test_scope_split_rejects_error_inside_parent(self):
        new=project([line(rect(x=0,y=0)),line([(5,0),(5,10)]),line([(1,1),(2,2)])],label_levels={})
        with self.assertRaisesRegex(ValueError,'phạm vi'):scope_splits(new,old_rows())

    def test_scope_split_requires_complete_parent_and_supported_geometry(self):
        new=project([line(rect(x=0,y=0,w=5)),line([(2,0),(2,10)])],label_levels={})
        with self.assertRaises(ValueError):scope_splits(new,old_rows())
        new=project([line(rect(x=0,y=0)),line([(5,0),(5,10)])],label_levels={})
        new['issues'].append({'code':'UNSUPPORTED'})
        with self.assertRaises(ValueError):scope_splits(new,old_rows())

    def test_world_coordinate_roundoff_preserves_unchanged_ids_including_zero(self):
        from app import geometry
        old=old_rows()
        ring=[(x+600000,y+1000000) for x,y in geometry(old[0]['Geometry'])]
        ring.append(ring[0])
        p=project([line(ring)],[text('12',600005,1000005,13)],label_levels={'TCT':'13'})
        old=export_rows(p);old[0]['ID']=0
        shifted=[(x+1.5e-8,y) for x,y in ring]
        new=project([line(shifted)],label_levels={})
        result=reconcile(new,old)
        self.assertEqual(result['delete_ids'],[])
        self.assertEqual(result['insert_rows'],[])
        self.assertEqual(result['final_rows'][0]['ID'],0)
        self.assertEqual(result['final_rows'][0]['TCT'],12)

    def test_roundoff_allowance_does_not_hide_real_partial_coverage(self):
        new=project([line(rect(x=.00001,y=0,w=9.99999))],label_levels={})
        with self.assertRaisesRegex(ValueError,'một phần'):reconcile(new,old_rows())

    def test_line_on_level_10_splits_one_mdb_parcel_into_two(self):
        old=old_rows()
        new=project([line(rect(x=0,y=0)),line([(5,0),(5,10)],level=10)],label_levels={})
        self.assertEqual(len(new['parcels']),2)
        result=reconcile(new,old)
        self.assertEqual((result['before_count'],result['after_count']),(1,2))
        self.assertEqual(result['delete_ids'],[20])
        self.assertEqual({r['ID'] for r in result['insert_rows']},{21,22})
        self.assertEqual(result['unnumbered'],2)
        self.assertEqual(sum(r['DienTich'] for r in result['final_rows']),100)
        self.assertTrue(all(r['ToBD']==89 and r['TenChu']=='Original owner' for r in result['final_rows']))
        self.assertEqual(result['splits'][0]['old_id'],20)

    def test_existing_and_outside_parcels_keep_ids_and_attributes(self):
        old=old_rows()
        outside=copy.deepcopy(old[0]);outside['ID']=30;outside['TCT']=13
        other=project([line(rect(x=50,y=0))],[text('13',55,5,13)])
        outside['Geometry']=export_rows(other)[0]['Geometry'];old.append(outside)
        new=project([line(rect(x=0,y=0))],label_levels={})
        result=reconcile(new,old)
        self.assertEqual(result['after_count'],2)
        self.assertEqual(result['delete_ids'],[])
        self.assertEqual(result['insert_rows'],[])
        self.assertEqual(result['project']['parcels'][0]['ID'],20)
        self.assertEqual(result['project']['parcels'][0]['TCT'],12)
        self.assertIn(outside,result['final_rows'])

    def test_partial_old_parcel_coverage_refuses_deletion(self):
        new=project([line(rect(x=0,y=0,w=5))],label_levels={})
        with self.assertRaisesRegex(ValueError,'một phần'):reconcile(new,old_rows())

    def test_unclosed_divider_cannot_be_written_to_database(self):
        new=project([line(rect(x=0,y=0)),line([(5,.01),(5,9.99)])],label_levels={})
        self.assertEqual(len(new['parcels']),1)
        with self.assertRaises(ValueError):reconcile(new,old_rows())

    def test_original_inputs_not_mutated(self):
        old=old_rows();before=copy.deepcopy(old)
        new=project([line(rect(x=0,y=0)),line([(5,0),(5,10)])],label_levels={});original=copy.deepcopy(new)
        reconcile(new,old)
        self.assertEqual(old,before);self.assertEqual(new,original)

    def test_unassigned_official_numbers_block_export_but_not_topology_storage(self):
        new=project([line(rect(x=0,y=0))],label_levels={})
        self.assertIsNone(export_rows(new,allow_unnumbered=True)[0]['TCT'])
        with self.assertRaises(ValueError):export_rows(new)

if __name__=='__main__':unittest.main()

class DirectUpdateTests(unittest.TestCase):
    def fixture(self,folder):
        import topology_workflow as flow
        from pathlib import Path
        from topology import save_project
        root=Path(folder);source=root/'sheet.dgn';source.write_bytes(b'old-dgn')
        mdb=root/'sheet.mdb';mdb.write_bytes(b'old-mdb')
        working=root/'copy.dgn';working.write_bytes(b'old-dgn')
        p=project([line(rect(x=0,y=0)),line([(5,0),(5,10)])],label_levels={})
        p.update(source={'path':str(source),'sha256':flow.digest(source)},working_dgn=str(working),working_sha256=flow.digest(working))
        path=root/'project.json';save_project(path,p)
        old=old_rows();delta=reconcile(p,old)
        return path,source,mdb,old,delta

    def test_direct_update_keeps_filenames_backs_up_and_returns_new_records(self):
        import topology_workflow as flow
        import tempfile,shutil
        from pathlib import Path
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            path,source,mdb,old,delta=self.fixture(directory)
            def execute(script,*args):
                if script=='update_mdb_topology.ps1':Path(args[args.index('-MdbPath')+1]).write_bytes(b'new-mdb')
                elif args[args.index('-Action')+1]=='ApplyDrawing':source.write_bytes(b'new-dgn')
            def inspect(target):
                target=Path(target)
                return {'path':str(target),'sha256':flow.digest(target),'rows':old if target.read_bytes()==b'old-mdb' else delta['final_rows'],'count':1 if target.read_bytes()==b'old-mdb' else 2}
            with patch.object(flow,'powershell',side_effect=execute),patch.object(flow,'inspect_database',side_effect=inspect):result=flow.apply_current(path,mdb)
            self.assertEqual(result['after_count'],2)
            self.assertEqual(source.read_bytes(),b'new-dgn');self.assertEqual(mdb.read_bytes(),b'new-mdb')
            backup=Path(result['backup'])
            self.assertEqual((backup/'sheet.dgn').read_bytes(),b'old-dgn')
            self.assertEqual((backup/'sheet.mdb').read_bytes(),b'old-mdb')

    def test_locked_mdb_restores_dgn_and_keeps_old_database(self):
        import topology_workflow as flow
        import tempfile,shutil,os
        from pathlib import Path
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            path,source,mdb,old,delta=self.fixture(directory)
            actions=[]
            def execute(script,*args):
                if script=='update_mdb_topology.ps1':Path(args[args.index('-MdbPath')+1]).write_bytes(b'new-mdb');return
                action=args[args.index('-Action')+1];actions.append(action)
                if action=='ApplyDrawing':source.write_bytes(b'new-dgn')
                if action=='RestoreActive':shutil.copyfile(args[args.index('-InputPath')+1],source)
            def inspect(target):
                target=Path(target);rows=old if target.read_bytes()==b'old-mdb' else delta['final_rows']
                return {'path':str(target),'sha256':flow.digest(target),'rows':rows,'count':len(rows)}
            real_replace=os.replace
            def locked(src,dst):
                if str(src).endswith('.mdb'):raise PermissionError('locked')
                return real_replace(src,dst)
            with patch.object(flow,'powershell',side_effect=execute),patch.object(flow,'inspect_database',side_effect=inspect),patch.object(flow.os,'replace',side_effect=locked):
                with self.assertRaisesRegex(RuntimeError,'bị khóa'):flow.apply_current(path,mdb)
            self.assertEqual(actions,['ApplyDrawing','RestoreActive'])
            self.assertEqual(source.read_bytes(),b'old-dgn');self.assertEqual(mdb.read_bytes(),b'old-mdb')
