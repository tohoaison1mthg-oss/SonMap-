"""Synthetic CAD cases, independent of proprietary DGN/MDB fixtures."""
import copy
import tempfile
import unittest
from pathlib import Path

from topology import build, export_rows, save_project, BLOCKING
from topology_workflow import validate_options

OPTIONS = dict(boundary_levels='10', sheet=89, metres_per_unit=1,
               short_length=.001, min_area=.3, near_distance=.1, snap_tolerance=.01,
               snap=False, centre_level=11, centre_color=3, centre_height=1,
               chord_tolerance=.001, label_levels={'TCT':'13','LRD':'14'})


def line(points, level=10):
    return dict(kind='line', level=level, points=points)


def rect(x=500000,y=1000000,w=10,h=10):
    return [(x,y),(x+w,y),(x+w,y+h),(x,y+h),(x,y)]


def text(value,x,y,level):
    return dict(text=value,point=(x,y),level=level)


def project(elements, texts=(), **options):
    return build(dict(elements=elements,texts=texts,model='Default',unit='m'),{**OPTIONS,**options})


class TopologyTests(unittest.TestCase):
    def test_ignore_tiny_spur_keeps_coordinates_and_real_open_end(self):
        elements=[line(rect(x=0,y=0)),line([(10,10),(10.0000002,10)]),line([(0,0),(-2,0)])]
        strict=project(elements,label_levels={},ignore_tolerance=0)
        relaxed=project(elements,label_levels={},ignore_tolerance=.001)
        self.assertEqual(strict['noded_lines'],relaxed['noded_lines'])
        self.assertEqual(strict['parcels'],relaxed['parcels'])
        self.assertTrue(any(i['code']=='DANGLE' for i in relaxed['ignored_issues']))
        self.assertTrue(any(i['code']=='DANGLE' and i['point']==(-2.,0.) for i in relaxed['issues']))
        with self.assertRaises(ValueError):export_rows(relaxed)

    def test_ignored_small_gap_does_not_allow_export_of_missing_region(self):
        elements=[line(rect(x=20,y=0)),line([(0,.0001),(0,10),(10,10),(10,0),(0,0)])]
        relaxed=project(elements,label_levels={},ignore_tolerance=.001)
        self.assertEqual(len(relaxed['parcels']),1)
        self.assertTrue(any(i['code']=='DANGLE' for i in relaxed['ignored_issues']))
        with self.assertRaises(ValueError):export_rows(relaxed)
        relaxed['issues']=[i for i in relaxed['issues'] if i['code'] not in BLOCKING]
        with self.assertRaisesRegex(ValueError,'khép vùng'):export_rows(relaxed)
        strict=project(elements,label_levels={},ignore_tolerance=0)
        self.assertTrue(any(i['code']=='DANGLE' for i in strict['issues']))

    def test_shared_boundary_nodes_and_assigns_separate_parcels(self):
        p=project([line(rect(w=20)),line([(500010,1000000),(500010,1000010)])],
                  [text('12',500005,1000005,13),text('13',500015,1000005,13),
                   text('ODT+CLN',500005,1000004,14),text('LUC',500015,1000004,14)])
        self.assertEqual(len(p['parcels']),2)
        self.assertEqual(sorted(r['DienTich'] for r in p['parcels']),[100,100])
        self.assertEqual({r['TCT'] for r in p['parcels']},{12,13})
        self.assertFalse(any(i['code'] in BLOCKING for i in p['issues']))
        from shapely.geometry import Polygon,Point
        for r in p['parcels']:self.assertTrue(Polygon(r['points']).contains(Point(r['centre'])))
        from app import geometry
        from quality import area
        rows=export_rows(p)
        self.assertEqual([area(geometry(r['Geometry'])) for r in rows],[100,100])
        self.assertTrue(all(min(x for x,y in geometry(r['Geometry']))>=500000 for r in rows))

    def test_reversed_duplicate_and_partial_overlap_do_not_create_extra_parcels(self):
        p=project([line(rect()),line(list(reversed(rect()))),line([(500002,1000000),(500008,1000000)])],label_levels={})
        self.assertEqual(len(p['parcels']),1)
        self.assertEqual(p['parcels'][0]['DienTich'],100)
        self.assertEqual(sum(i['code']=='DUPLICATE_REMOVED' for i in p['issues']),4)

    def test_open_gap_blocks_export_until_explicit_pair_snap(self):
        points=[(0,.005),(0,10),(10,10),(10,0),(0,0)]
        raw=project([line(points)],label_levels={})
        self.assertTrue(any(i['code'] in BLOCKING for i in raw['issues']))
        with self.assertRaises(ValueError):export_rows(raw)
        fixed=project([line(points)],snap=True,label_levels={})
        self.assertEqual(len(fixed['parcels']),1)
        self.assertTrue(any(i['code']=='SNAPPED_ENDPOINT' for i in fixed['issues']))
        self.assertFalse(any(i['code'] in BLOCKING for i in fixed['issues']))

    def test_bounded_group_of_nearby_nodes_is_snapped(self):
        p=project([line([(0,0),(10,0)]),line([(.005,0),(10,10)]),line([(0,.005),(0,10)])],snap=True,label_levels={})
        moved=[i for i in p['issues'] if i['code']=='SNAPPED_ENDPOINT']
        self.assertTrue(moved)
        self.assertTrue(all(i['displacement_m']<=.01 for i in moved))

    def test_crossing_lines_are_split_into_faces(self):
        p=project([line(rect(x=0,y=0)),line([(0,0),(10,10)]),line([(0,10),(10,0)])],label_levels={})
        self.assertEqual(len(p['parcels']),4)
        self.assertEqual([r['DienTich'] for r in p['parcels']],[25]*4)

    def test_text_on_shared_edge_never_assigns_to_both(self):
        p=project([line(rect(x=0,y=0)),line([(5,0),(5,10)])],[text('12',5,5,13)])
        self.assertEqual([r['TCT'] for r in p['parcels']],[None,None])
        self.assertEqual(sum(i['code']=='LABEL_AMBIGUOUS' for i in p['issues']),2)

    def test_multiple_owner_labels_require_manual_choice(self):
        p=project([line(rect(x=0,y=0))],[text('A',2,2,15),text('B',3,3,15)],label_levels={'TenChu':'15'})
        self.assertEqual(p['parcels'][0]['TenChu'],'')
        self.assertTrue(any(i['code']=='LABEL_AMBIGUOUS' for i in p['issues']))

    def test_nested_rings_roundtrip_with_correct_net_area(self):
        p=project([line(rect(x=0,y=0)),line(rect(x=2,y=2,w=2,h=2))],label_levels={})
        self.assertFalse(any(i['code'] in BLOCKING for i in p['issues']))
        from app import parcel_polygon
        rows=export_rows(p,allow_unnumbered=True)
        self.assertEqual(sorted(parcel_polygon(r).area for r in rows),[4,96])

    def test_dangle_does_not_get_silently_removed(self):
        p=project([line(rect(x=0,y=0)),line([(0,0),(-2,0)])],label_levels={})
        self.assertEqual(len(p['parcels']),1)
        self.assertTrue(any(i['code'] in ('DANGLE','CUT_EDGE') for i in p['issues']))
        with self.assertRaises(ValueError):export_rows(p)

    def test_unsupported_boundary_is_not_ignored(self):
        p=project([line(rect()),dict(kind='unsupported-type-16',level=10)],label_levels={})
        with self.assertRaises(ValueError):export_rows(p)

    def test_unselected_layer_does_not_form_parcel(self):
        p=project([line(rect()),line(rect(x=0,y=0),level=12)],label_levels={})
        self.assertEqual(len(p['parcels']),1)

    def test_empty_and_nonfinite_inputs_rejected(self):
        with self.assertRaises(ValueError):project([])
        with self.assertRaises(ValueError):project([line([(0,0),(float('nan'),1)])])
        with self.assertRaises(ValueError):project([line(rect())],snap_tolerance='nan')
        with self.assertRaises(ValueError):project([line(rect())],boundary_levels='0')

    def test_missing_duplicate_numbers_and_wrong_units_block_mdb(self):
        p=project([line(rect(x=0,y=0)),line([(5,0),(5,10)])],label_levels={})
        with self.assertRaises(ValueError):export_rows(p)
        for r in p['parcels']:r['TCT']=1
        with self.assertRaises(ValueError):export_rows(p)
        p['parcels'][1]['TCT']=2
        self.assertEqual(len(export_rows(p)),2)
        p['options']['metres_per_unit']=.001
        with self.assertRaises(ValueError):export_rows(p)

    def test_small_area_report_and_metric_conversion(self):
        p=project([line(rect(x=0,y=0,w=100,h=100))],metres_per_unit=.001,label_levels={})
        self.assertAlmostEqual(p['parcels'][0]['DienTich'],.01)
        self.assertTrue(any(i['code']=='SMALL_PARCEL' for i in p['issues']))

    def test_input_not_mutated_and_review_roundtrips(self):
        snapshot=dict(elements=[line(rect())],texts=[])
        before=copy.deepcopy(snapshot)
        p=build(snapshot,OPTIONS)
        self.assertEqual(snapshot,before)
        import json
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'project.json'
            save_project(path,p)
            loaded=json.loads(path.read_text(encoding='utf-8'))
            save_project(path,loaded)
            self.assertEqual(len(loaded['parcels']),1)

    def test_separate_centre_layer_and_valid_colour_required(self):
        with self.assertRaises(ValueError):validate_options({**OPTIONS,'centre_level':10})
        with self.assertRaises(ValueError):validate_options({**OPTIONS,'centre_color':256})

    def test_missing_mdb_allowed_for_discovery_but_export_still_requires_it(self):
        from workflow import drawing_paths
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'sheet.dgn';path.write_bytes(b'placeholder')
            self.assertEqual(drawing_paths(path,directory,require_mdb=False)['mdb'],str(path.with_suffix('.mdb')))
            with self.assertRaises(FileNotFoundError):drawing_paths(path,directory)


class TopologySafetyTests(unittest.TestCase):
    def valid(self):
        return project([line(rect(x=0,y=0))],[text('12',5,5,13)])

    def test_area_and_centre_tampering_cannot_be_exported(self):
        p=self.valid();p['parcels'][0]['DienTich']=101
        with self.assertRaises(ValueError):export_rows(p)
        p=self.valid();p['parcels'][0]['centre']=[20,20]
        with self.assertRaises(ValueError):export_rows(p)

    def test_oversized_text_and_non_integer_numbers_block_export(self):
        p=self.valid();p['parcels'][0]['TenChu']='a'*256
        with self.assertRaises(ValueError):export_rows(p)
        p=self.valid();p['parcels'][0]['TCT']=1.5
        with self.assertRaises(ValueError):export_rows(p)

    def test_joining_line_strings_keeps_same_polygon(self):
        p=project([line(rect())],label_levels={},join_lines=True)
        self.assertEqual(len(p['cleaned_lines']),1)
        self.assertEqual(len(p['parcels']),1)
        self.assertEqual(p['parcels'][0]['DienTich'],100)

    def test_snap_works_even_if_near_warning_radius_is_smaller(self):
        p=project([line([(0,.005),(0,10),(10,10),(10,0),(0,0)])],snap=True,near_distance=.001,label_levels={})
        self.assertEqual(len(p['parcels']),1)
        self.assertTrue(any(i['code']=='SNAPPED_ENDPOINT' for i in p['issues']))

    def test_changed_source_blocks_before_any_external_write(self):
        import topology_workflow as flow
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'source.dgn';source.write_bytes(b'original')
            working=root/'copy.dgn';working.write_bytes(b'original')
            p=self.valid();p['options'].update(error_level=60,error_color=3,error_radius=.01)
            p.update(source={'path':str(source),'sha256':flow.digest(source)},working_dgn=str(working),working_sha256=flow.digest(working))
            path=root/'project.json';save_project(path,p)
            source.write_bytes(b'changed')
            with patch.object(flow,'powershell') as execute:
                with self.assertRaises(ValueError):flow.export_project(path)
                execute.assert_not_called()
            self.assertEqual(list(root.glob('result_*')),[])

    def test_existing_mdb_not_used_or_overwritten(self):
        # A project always targets a new result directory, even when the source has an MDB.
        import topology_workflow as flow
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'source.dgn';source.write_bytes(b'original')
            existing=source.with_suffix('.mdb');existing.write_bytes(b'keep original database')
            working=root/'copy.dgn';working.write_bytes(b'original')
            p=self.valid();p['options'].update(error_level=60,error_color=3,error_radius=.01)
            p.update(source={'path':str(source),'sha256':flow.digest(source)},working_dgn=str(working),working_sha256=flow.digest(working))
            path=root/'project.json';save_project(path,p)
            def fail(script,*args):
                output=Path(args[args.index('-OutputPath')+1])
                self.assertNotEqual(output,existing)
                self.assertTrue(output.parent.name.startswith('result_'))
                raise RuntimeError('simulated Jet unavailable')
            with patch.object(flow,'powershell',side_effect=fail):
                with self.assertRaises(RuntimeError):flow.export_project(path)
            self.assertEqual(existing.read_bytes(),b'keep original database')
            self.assertFalse(list(root.glob('result_*/receipt.json')))



class DatabaseWorkflowTests(unittest.TestCase):
    def test_existing_database_is_not_overwritten(self):
        import topology_workflow as flow
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'old.mdb';path.write_bytes(b'keep')
            with patch.object(flow,'powershell') as execute:
                with self.assertRaises(ValueError):flow.create_database(path)
                execute.assert_not_called()
            self.assertEqual(path.read_bytes(),b'keep')

    def test_read_database_uses_verified_snapshot(self):
        import json
        import topology_workflow as flow
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'old.mdb';path.write_bytes(b'original')
            def read(script,*args):
                source=Path(args[args.index('-MdbPath')+1]);output=Path(args[args.index('-JsonPath')+1])
                self.assertNotEqual(source,path);self.assertEqual(source.read_bytes(),b'original')
                output.write_text('[]')
            with patch.object(flow,'powershell',side_effect=read):result=flow.inspect_database(path)
            self.assertEqual(result['count'],0)
            self.assertEqual(path.read_bytes(),b'original')
            self.assertEqual(result['sha256'],flow.digest(path))

    def test_gan_nhan_preserves_manual_edits(self):
        import json
        import topology_workflow as flow
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);working=root/'source.dgn';working.write_bytes(b'fixture')
            snapshot={'elements':[line(rect(x=0,y=0))],'texts':[text('12',5,5,13),text('Drawing owner',4,4,15)]}
            (root/'snapshot.json').write_text(json.dumps(snapshot))
            p=build(snapshot,OPTIONS);p.update(working_dgn=str(working),working_sha256=flow.digest(working),source={'path':str(working),'sha256':flow.digest(working)},references_excluded=0,status='review')
            p['parcels'][0].update(TenChu='Edited owner',manual_fields=['TenChu'])
            path=root/'project.json';save_project(path,p)
            new=flow.assign_labels(path,{'TCT':'13','TenChu':'15'})
            self.assertEqual(new['parcels'][0]['TenChu'],'Edited owner')
            self.assertEqual(new['parcels'][0]['TCT'],12)

    def test_com_error_retains_stage_and_full_log(self):
        import json
        import topology_workflow as flow
        from unittest.mock import patch
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as directory:
            error={'stage':'select-model: Default','message':'Value does not fall within expected range.','line':75}
            with patch.object(flow,'ROOT',Path(directory)),patch.object(flow,'os',SimpleNamespace(name='nt',environ={})),patch('cad_worker.worker.run',return_value=(False,json.dumps(error))):
                with self.assertRaisesRegex(RuntimeError,'select-model: Default'):flow.powershell('dgn_topology.ps1')
            self.assertIn(error['message'],(Path(directory)/'data/dgn-topology-last.log').read_text())




class EmptyDatabaseTests(unittest.TestCase):
    def test_empty_database_can_connect_without_fake_parcels(self):
        from app import decode_mdb_rows
        self.assertEqual(decode_mdb_rows([], 'empty.mdb', 'fixture', allow_empty=True),([],[]))
        with self.assertRaises(ValueError):decode_mdb_rows([], 'empty.mdb', 'fixture')



class ModelIdentityTests(unittest.TestCase):
    def test_default_model_role_survives_snapshot_and_project_serialization(self):
        import json
        snapshot={'elements':[line(rect())],'texts':[],'model':'Default','model_is_default':True}
        p=build(snapshot,OPTIONS)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'project.json';save_project(path,p)
            loaded=json.loads(path.read_text())
        self.assertIs(loaded['model_is_default'],True)
        self.assertEqual(loaded['model'],'Default')

if __name__=='__main__':unittest.main()
