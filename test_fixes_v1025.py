import unittest
from topology_ui import drawing_sheet
from parcel_info_ui import form_bindings,FORM_FIELDS

class CadastralDefaultsTests(unittest.TestCase):
    def test_sheet_from_current_dgn_or_unambiguous_mdb(self):
        self.assertEqual(drawing_sheet('dc188.dgn'),'188')
        self.assertEqual(drawing_sheet('dc188.dgn',[{'ToBD':1}]),'188')
        self.assertEqual(drawing_sheet('DC00116.dgn'),'116')
        self.assertEqual(drawing_sheet('renamed.dgn',[{'ToBD':116},{'ToBD':116}]),'116')
        self.assertEqual(drawing_sheet('renamed.dgn',[{'ToBD':116},{'ToBD':188}]),'')
        self.assertEqual(drawing_sheet('unknown.dgn'),'')
    def test_temporary_number_stays_in_database_but_not_edit_form(self):
        row={'ToBD':188,'TCT':50,'ThuaTam':999}
        fields=form_bindings({'columns':[{'name':k} for k in row]},row)
        self.assertNotIn('temporary',FORM_FIELDS)
        self.assertNotIn('temporary',fields)
        self.assertEqual(row['ThuaTam'],999)
