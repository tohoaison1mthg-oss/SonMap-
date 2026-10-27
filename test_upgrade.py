import base64, copy, json, struct, unittest
from pathlib import Path
import app
from quality import ring_issues, area, audit, matches, read_edits, merge_edits

class UpgradeTests(unittest.TestCase):
    def test_duplicate_temporary_numbers_block_export_before_files_are_written(self):
        import tempfile
        from topology import export_rows
        from test_topology import project,line,rect
        with tempfile.TemporaryDirectory() as folder:
            mdb=Path(folder)/'test.mdb';mdb.write_bytes(b'synthetic MDB')
            p=project([line(rect(x=0,y=0)),line([(5,0),(5,10)])],label_levels={})
            for row in p['parcels']:row['TCT']=10
            rows=export_rows(p,allow_duplicate_numbers=True)
            parcels,rejected=app.decode_mdb_rows(rows,str(mdb),app.sha(mdb))
            with self.assertRaisesRegex(ValueError,'số tạm'):
                app.prepare({'mdb':str(mdb)},parcels,rejected)
            self.assertEqual(list(Path(folder).iterdir()),[mdb])

    def test_valid_large_coordinates_and_orientation(self):
        p=[(500000,1000000),(500010,1000000),(500010,1000010),(500000,1000010)]
        self.assertEqual(ring_issues(p),[]);self.assertEqual(area(p),100)
        self.assertEqual(ring_issues(p[::-1]),[])
    def test_invalid_rings(self):
        for p in [[(0,0),(4,4),(0,3),(4,0)],[(0,0),(3,0),(1,0),(1,3),(0,3)],[(0,0),(2,0),(2,2),(0,0),(0,2)],[(0,0),(1,0),(2,0)],[(0,0),(float('nan'),1),(0,2)]]:
            with self.subTest(points=p):self.assertTrue(ring_issues(p))
    def test_decoder_blocks_self_intersection(self):
        p=[(0,0),(4,4),(0,3),(4,0),(0,0)]
        data=b'\0'+struct.pack('<III',3,1,len(p))+b''.join(struct.pack('<dd',*v) for v in p)
        with self.assertRaises(ValueError):app.geometry(base64.b64encode(data).decode())
    def test_search_does_not_confuse_number_and_id(self):
        p={'ToBD':18,'TCT':17,'ID':101,'TenChu':'Nguyễn Văn A'}
        self.assertTrue(matches(p,'18','17','101','NGUYỄN'))
        self.assertFalse(matches(p,number='1'));self.assertFalse(matches(p,record_id='17'))
    def test_scoped_overrides_preserve_legacy_and_other_source(self):
        old={'18/17/101':{'owner_override':'OLD'}};original=copy.deepcopy(old)
        self.assertEqual(read_edits(old,'sourceA'),{})
        p={'key':'18/17/101','owner_override':'NEW','points':[(0,0)]}
        saved=merge_edits(old,'sourceA',[p]);self.assertEqual(old,original)
        self.assertEqual(saved['legacy_unassigned'],old)
        self.assertEqual(read_edits(saved,'sourceB'),{})
        self.assertEqual(read_edits(saved,'sourceA')[p['key']],{'owner_override':'NEW'})
        merged=merge_edits(saved,'sourceB',[dict(p,owner_override='B')])
        self.assertEqual(read_edits(merged,'sourceA')[p['key']]['owner_override'],'NEW')
    def test_audit(self):
        p={'key':'18/17/1','ToBD':18,'TCT':17,'ID':1,'DienTich':90,'LRD':'LUC','points':[(0,0),(10,0),(10,10),(0,10)]}
        q=dict(p,key='18/17/2',ID=2)
        codes=[i['code'] for i in audit([p,q])]
        self.assertEqual(codes.count('DUP_NUMBER'),2);self.assertEqual(codes.count('AREA_DIFF'),2)

def real_report():
    raw=json.loads((Path(__file__).parent/'data/source.json').read_text(encoding='utf-8-sig'))
    accepted=[];rejected=[]
    for source in raw:
        row=dict(source);row['key']=f"{row['ToBD']}/{row['TCT']}/{row['ID']}"
        try:row['points']=app.geometry(row['Geometry']);accepted.append(row)
        except ValueError as exc:rejected.append({'key':row['key'],'reason':str(exc)})
    issues=audit(accepted,rejected)
    counts={code:sum(i['code']==code for i in issues) for code in sorted({i['code'] for i in issues})}
    report={'records':len(raw),'accepted':len(accepted),'rejected':len(rejected),'warnings':counts,'checks':'MDB geometry only; no DGN editing or VBA runtime validation'}
    (Path(__file__).parent/'UPGRADE_TEST_RESULTS.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True))

if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(UpgradeTests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():raise SystemExit(1)
    real_report()
