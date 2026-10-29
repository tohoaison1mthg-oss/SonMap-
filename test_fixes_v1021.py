import copy
import unittest
from unittest.mock import patch
from test_topology import project,line,rect
from topology import export_rows,BLOCKING
from app import geometry_rings,parcel_polygon
from database_topology import reconcile
from parcel_info import locate_parcel,select_record


class CriticalFixTests(unittest.TestCase):
    def test_endpoint_attaches_to_edge_and_closes_region(self):
        p=project([line(rect(x=0,y=0)),line([(5,.005),(5,10)])],snap=True,label_levels={})
        self.assertEqual(len(p['parcels']),2)
        self.assertFalse(any(i['code'] in BLOCKING for i in p['issues']))
        self.assertEqual(len(export_rows(p,allow_unnumbered=True)),2)

    def test_snap_does_not_bridge_real_gap_beyond_tolerance(self):
        p=project([line([(0,.02),(0,10),(10,10),(10,0),(0,0)])],snap=True,label_levels={})
        self.assertTrue(any(i['code'] in BLOCKING for i in p['issues']))

    def test_holes_pick_and_reconcile_keep_records_and_binary(self):
        p=project([line(rect(x=0,y=0)),line(rect(x=2,y=2,w=2,h=2))],label_levels={})
        for i,r in enumerate(p['parcels']):r.update(TCT=i+1,TenChu='Chủ mới '+str(i))
        rows=export_rows(p)
        self.assertEqual(locate_parcel(rows,(3,3))['DienTich'],4)
        self.assertEqual(locate_parcel(rows,(8,8))['DienTich'],96)
        d=reconcile(p,rows)
        self.assertFalse(d['insert_rows'] or d['update_rows'] or d['delete_ids'])
        self.assertEqual(d['final_rows'],rows)
        hole=next(r for r in rows if parcel_polygon(r).area==96)
        self.assertEqual(len(geometry_rings(hole['Geometry'])),2)
        with self.assertRaises(ValueError):geometry_rings(hole['Geometry'][:-4])

    def test_list_selection_uses_id_even_with_duplicate_numbers(self):
        rows=[dict(ID=1,TCT=10,TenChu='A'),dict(ID=2,TCT=10,TenChu='B')]
        connected=dict(path='test.mdb',sha256='hash',rows=rows)
        with patch('parcel_info.inspect_database',return_value=connected),patch('topology_workflow.validate_parcel_context'):
            s=select_record('test.dgn','test.mdb',2)
        self.assertEqual(s['row']['TenChu'],'B')

