import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from parcel_info import locate_parcel, update_owner, parcel_number
from test_database_topology import old_rows


class ParcelInfoTests(unittest.TestCase):
    def test_number_edit_is_optional_positive_integer(self):
        self.assertIsNone(parcel_number(''))
        self.assertEqual(parcel_number(' 10 '),10)
        for value in ('0','-1','1.5','1e2','2147483648',True):
            with self.assertRaises(ValueError):parcel_number(value)

    def test_duplicate_parcel_number_still_selects_unique_geometry_and_id(self):
        from test_topology import project,line,rect
        from topology import export_rows
        other=export_rows(project([line(rect(x=20,y=0))]),allow_unnumbered=True)[0]
        other.update(ID=21,TCT=12)
        rows=old_rows()+[other]
        self.assertEqual(locate_parcel(rows,[25,5])['ID'],21)
        self.assertEqual(locate_parcel(rows,[5,5])['ID'],20)
    def test_interior_point_finds_id_even_when_number_pending(self):
        rows=old_rows();rows[0].update(ID=0,TCT=None)
        result=locate_parcel(rows,[5,5])
        self.assertEqual(result['ID'],0)
        self.assertIsNone(result['TCT'])
        self.assertIsNot(result,rows[0])

    def test_border_outside_and_overlap_never_guess_a_record(self):
        rows=old_rows()
        for point in ([0,5],[50,50],[float('nan'),0]):
            with self.assertRaises(ValueError):locate_parcel(rows,point)
        other=copy.deepcopy(rows[0]);other['ID']=21
        with self.assertRaisesRegex(ValueError,'chồng lấn'):locate_parcel(rows+[other],[5,5])
        with self.assertRaisesRegex(ValueError,'ID trùng'):locate_parcel(rows+[dict(rows[0],Geometry='')],[5,5])

    def test_changed_database_is_not_backed_up_or_written(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'test.mdb';path.write_bytes(b'unchanged')
            with patch('parcel_info.inspect_database',return_value={'sha256':'new','rows':old_rows()}),patch('parcel_info.powershell') as io:
                with self.assertRaisesRegex(ValueError,'đã đổi'):update_owner(path,'old',20,'Tên mới','Địa chỉ')
                io.assert_not_called()
            self.assertFalse((Path(folder)/'SonMap_backups').exists())
            self.assertEqual(path.read_bytes(),b'unchanged')

    def test_invalid_fields_or_id_never_write(self):
        with patch('parcel_info.inspect_database',return_value={'sha256':'same','rows':old_rows()}),patch('parcel_info.powershell') as io:
            for value in ('x'*256,'nul\x00name'):
                with self.assertRaises(ValueError):update_owner('test.mdb','same',20,value,'')
            with self.assertRaises(ValueError):update_owner('test.mdb','same',999,'Name','')
            io.assert_not_called()
