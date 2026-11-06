import unittest
from unittest.mock import patch
from parcel_actions import record_index
from parcel_info import pick_parcel
from test_database_topology import old_rows

class ParcelActionTests(unittest.TestCase):
    def test_duplicate_numbers_resolve_by_record_id(self):
        rows=[{'ID':20,'TCT':50},{'ID':21,'TCT':50}]
        self.assertEqual(record_index(rows,21),1)
        with self.assertRaises(ValueError):record_index(rows,99)
        with self.assertRaises(ValueError):record_index(rows+[rows[1]],21)

    def test_dgn_pick_returns_exact_record_without_exporting(self):
        rows=old_rows()
        connected={'path':'fixture.mdb','sha256':'same','rows':rows}
        with patch('parcel_info.inspect_database',return_value=connected),patch('parcel_info.digest',return_value='same'),patch('cad_bridge.request',return_value='{"point":[5,5],"model":"Default"}') as request:
            result=pick_parcel('fixture.dgn','fixture.mdb')
        self.assertEqual(result['row']['ID'],20)
        self.assertEqual(result['model'],'Default')
        self.assertEqual(request.call_args.args[0],'pick')

    def test_cancel_or_changed_mdb_never_selects_stale_record(self):
        with patch('parcel_info.inspect_database',return_value={'path':'fixture.mdb','sha256':'before','rows':old_rows()}),patch('cad_bridge.request',return_value='{"cancelled":true}'):
            self.assertIsNone(pick_parcel('fixture.dgn','fixture.mdb'))
        with patch('parcel_info.inspect_database',return_value={'path':'fixture.mdb','sha256':'before','rows':old_rows()}),patch('cad_bridge.request',return_value='{"point":[5,5]}'),patch('parcel_info.digest',return_value='after'):
            with self.assertRaisesRegex(ValueError,'MDB đã đổi'):pick_parcel('fixture.dgn','fixture.mdb')
