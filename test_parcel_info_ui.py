import copy
import os
import time
import unittest
from unittest.mock import patch
from parcel_info_ui import ParcelInfoController
from test_database_topology import old_rows


@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'Requires Tk display')
class OwnerDialogTests(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        self.root=tk.Tk();self.root.withdraw();self.saved=[];self.busy=[]
        self.controller=ParcelInfoController(self.root,self.busy.append,self.saved.append)
        self.selection={'source':'test.dgn','row':old_rows()[0],
                        'connected':{'path':'test.mdb','sha256':'before','rows':old_rows(),'count':1}}

    def tearDown(self):self.root.destroy()

    def wait(self):
        end=time.monotonic()+3
        while self.controller.busy and time.monotonic()<end:
            self.root.update();time.sleep(.01)
        self.assertFalse(self.controller.busy)

    def test_save_uses_exact_record_and_refreshes_hash_for_next_save(self):
        c=self.controller;c.show(copy.deepcopy(self.selection))
        c.owner.set('Nguyễn Văn Mới');c.address.set('Địa chỉ mới');c.number.set('99')
        connected={**self.selection['connected'],'sha256':'after','rows':[dict(old_rows()[0],TCT=99,TenChu='Nguyễn Văn Mới',DiaChi='Địa chỉ mới')]}
        with patch('parcel_info_ui.update_owner',return_value={'connected':connected,'backup':'backup'}) as write:
            c.save();self.wait()
            write.assert_called_once_with('test.mdb','before',20,'Nguyễn Văn Mới','Địa chỉ mới',number='99')
            self.assertEqual(self.saved,[connected])
            self.assertIn('Thửa 99',c.header.get())
            self.assertEqual(c.number.get(),'99')
            c.save();self.wait()
            self.assertEqual(write.call_args.args[1],'after')
        self.assertEqual(self.busy,[True,False,True,False])

    def test_failed_save_restores_button_without_reporting_success(self):
        c=self.controller;c.show(copy.deepcopy(self.selection))
        with patch('parcel_info_ui.update_owner',side_effect=ValueError('stale MDB')),patch('tkinter.messagebox.showerror') as error:
            c.save();self.wait()
            self.assertTrue(error.called)
            self.assertEqual(self.saved,[])
            self.assertEqual(str(c.save_button.cget('state')),'normal')
