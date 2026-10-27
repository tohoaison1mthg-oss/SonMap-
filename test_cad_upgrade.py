import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from topology import build, BLOCKING
from test_topology import OPTIONS, line, rect
from test_database_topology import old_rows
from parcel_info import attribute_values, update_attributes
from topology_workflow import digest


def columns():
    return [dict(name=k,type=t,size=255,nullable=True) for k,t in
            [('ToBD','System.Int32'),('TCT','System.Int32'),('TenChu','System.String'),
             ('DiaChi','System.String'),('LRD','System.String'),('GhiChu','System.String'),
             ('DienTich','System.Double'),('Geometry','System.Byte[]'),('ID','System.Int32'),
             ('DTPhapLy','System.Double')]]


class RepairTests(unittest.TestCase):
    def test_crossings_create_real_nodes_and_keep_each_level_and_style(self):
        elements=[dict(line([(0,5),(10,5)],10),color=3,weight=2,line_style='0'),
                  dict(line([(5,0),(5,10)],23),color=4,weight=1,line_style='2')]
        p=build({'elements':elements},dict(OPTIONS,boundary_levels='10,23'))
        self.assertEqual(len(p['noded_lines']),4)
        for row in p['noded_lines']:
            self.assertIn([5,5],row['points'])
            self.assertEqual((row['color'],row['weight'],row['line_style']),
                             (3,2,'0') if row['level']==10 else (4,1,'2'))
        self.assertTrue(any(i['code']=='INTERSECTION_NODE' for i in p['issues']))

    def test_excess_and_missing_edges_are_reported_and_retained(self):
        elements=[line(rect(x=0,y=0)),line([(10,5),(12,5)]),line([(20,0),(30,0),(30,10),(20,10)])]
        p=build({'elements':elements},OPTIONS)
        self.assertEqual(len(p['parcels']),1)
        self.assertTrue(any(i['code'] in ('CUT_EDGE','DANGLE') for i in p['issues']))
        self.assertTrue(any([12,5] in r['points'] for r in p['noded_lines']))
        self.assertTrue(any([20,0] in r['points'] for r in p['noded_lines']))
        self.assertEqual(elements[1]['points'],[(10,5),(12,5)])


class AttributeTests(unittest.TestCase):
    def test_selected_fields_validate_types_and_allow_clearing(self):
        connected={'columns':columns()}
        self.assertEqual(attribute_values(connected,{'TCT':'','GhiChu':'','DTPhapLy':'12,5'}),
                         {'TCT':None,'GhiChu':'','DTPhapLy':12.5})
        for changes in ({'Geometry':'x'},{'ID':'2'},{'DienTich':'9'},{'ToBD':''},{'TenChu':'x'*256},
                        {'DTPhapLy':'NaN'},{'DTPhapLy':'1,000.1'},{'Unknown':'x'}):
            with self.assertRaises(ValueError):attribute_values(connected,changes)

    def test_staged_edit_verifies_other_parcels_before_replacing(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'test.mdb';target.write_bytes(b'old')
            rows=old_rows()+[dict(old_rows()[0],ID=21)]
            for row in rows:row['GhiChu']='old'
            expected=copy.deepcopy(rows);expected[0]['GhiChu']=''
            before={'path':str(target),'rows':rows,'sha256':digest(target),'columns':columns()}
            def inspect(path):
                return dict(before,path=str(path),rows=copy.deepcopy(expected if Path(path).read_bytes()==b'new' else rows),sha256=digest(path))
            def execute(script,*args):
                self.assertEqual(script,'update_parcel_attributes.ps1')
                plan=json.loads(Path(args[args.index('-PlanPath')+1]).read_text(encoding='utf-8'))
                self.assertEqual(plan['changes'],{'GhiChu':''})
                Path(args[args.index('-MdbPath')+1]).write_bytes(b'new')
            with patch('parcel_info.inspect_database',side_effect=inspect),patch('parcel_info.powershell',side_effect=execute):
                result=update_attributes(target,before['sha256'],20,{'GhiChu':''})
            self.assertEqual(result['connected']['rows'],expected)
            self.assertEqual((Path(result['backup'])/'test.mdb').read_bytes(),b'old')

    def test_failed_readback_keeps_original_file(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'test.mdb';target.write_bytes(b'old')
            connected={'rows':old_rows(),'sha256':digest(target),'columns':columns()}
            with patch('parcel_info.inspect_database',return_value=connected),patch('parcel_info.powershell'):
                with self.assertRaisesRegex(RuntimeError,'không khớp'):
                    update_attributes(target,connected['sha256'],20,{'TenChu':'new'})
            self.assertEqual(target.read_bytes(),b'old')
