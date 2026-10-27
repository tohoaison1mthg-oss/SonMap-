import copy
import os
import time
import unittest
from unittest.mock import patch
from parcel_info_ui import ParcelInfoController
from test_database_topology import old_rows
from test_cad_upgrade import columns


@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'Requires Tk display')
class OwnerDialogTests(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        self.root=tk.Tk();self.root.withdraw();self.saved=[];self.busy=[]
        self.controller=ParcelInfoController(self.root,self.busy.append,self.saved.append)
        self.context=patch('parcel_info_ui.validate_parcel_context');self.context.start()
        self.selection={'source':'test.dgn','row':old_rows()[0],
                        'connected':{'path':'test.mdb','sha256':'before','rows':old_rows(),'count':1,'columns':columns()}}

    def tearDown(self):self.context.stop();self.root.destroy()

    def wait(self):
        end=time.monotonic()+3
        while self.controller.busy and time.monotonic()<end:
            self.root.update();time.sleep(.01)
        self.assertFalse(self.controller.busy)

    def test_save_uses_exact_record_and_refreshes_hash_for_next_save(self):
        c=self.controller;c.show(copy.deepcopy(self.selection))
        c.values['TenChu'].set('Nguyễn Văn Mới');c.values['DiaChi'].set('Địa chỉ mới');c.values['TCT'].set('99')
        connected={**self.selection['connected'],'sha256':'after','rows':[dict(old_rows()[0],TCT=99,TenChu='Nguyễn Văn Mới',DiaChi='Địa chỉ mới')]}
        with patch('parcel_info_ui.update_attributes',return_value={'connected':connected,'backup':'backup','status':'attributes_updated'}) as write:
            c.save();self.wait()
            write.assert_called_once_with('test.mdb','before',20,{'TCT':'99','TenChu':'Nguyễn Văn Mới','DiaChi':'Địa chỉ mới'})
            self.assertEqual(self.saved,[connected])
            self.assertIn('Thửa 99',c.header.get())
            self.assertEqual(c.values['TCT'].get(),'99')
            c.values['DiaChi'].set('Địa chỉ lần hai')
            c.save();self.wait()
            self.assertEqual(write.call_args.args[1],'after')
        self.assertEqual(self.busy,[True,False,True,False])

    def test_failed_save_restores_button_without_reporting_success(self):
        c=self.controller;c.show(copy.deepcopy(self.selection))
        c.values['TenChu'].set('Thử lỗi')
        with patch('parcel_info_ui.update_attributes',side_effect=ValueError('stale MDB')),patch('tkinter.messagebox.showerror') as error:
            c.save();self.wait()
            self.assertTrue(error.called)
            self.assertEqual(self.saved,[])
            self.assertEqual(str(c.save_button.cget('state')),'normal')

    def test_cancelled_repick_disables_save_of_previous_parcel(self):
        c=self.controller;c.show(copy.deepcopy(self.selection))
        with patch('parcel_info_ui.pick_parcel',return_value=None):c.repick();self.wait()
        self.assertIsNone(c.selection)
        self.assertEqual(str(c.save_button.cget('state')),'disabled')
        self.assertEqual(self.saved,[])

    def test_changed_active_dgn_blocks_save_before_database_write(self):
        c=self.controller;c.show(copy.deepcopy(self.selection));c.values['TenChu'].set('Changed')
        with patch('parcel_info_ui.validate_parcel_context',side_effect=ValueError('Active DGN changed')),patch('parcel_info_ui.update_attributes') as write,patch('tkinter.messagebox.showerror'):
            c.save();self.wait();write.assert_not_called()
        self.assertEqual(self.saved,[])

    def test_form_hides_technical_columns_and_formats_all_areas_once(self):
        selection=copy.deepcopy(self.selection)
        selection['row'].update(DienTich=568.74321,DTPhapLy=123.4567,TamX=900,ExtraInt=99)
        selection['connected']['columns']+= [dict(name='TamX',type='System.Double',size=8,nullable=True),dict(name='ExtraInt',type='System.Int32',size=4,nullable=True)]
        c=self.controller;c.show(selection)
        self.assertEqual(c._vars['DienTich'].get(),'568,7')
        self.assertEqual(c.values['DTPhapLy'].get(),'123,5')
        for name in ('TamX','ExtraInt','ID','Geometry','DienTich'):self.assertNotIn(name,c.values)
        self.assertEqual(c.selection['row']['DienTich'],568.74321)

    def test_unchanged_selected_area_keeps_full_precision_on_save(self):
        selection=copy.deepcopy(self.selection);selection['row']['DTPhapLy']=123.4567
        c=self.controller;c.show(selection);c.enabled['DTPhapLy'].set(True)
        with patch('parcel_info_ui.update_attributes',return_value={'connected':selection['connected'],'backup':'','status':'unchanged'}) as write:
            c.save();self.wait()
            self.assertEqual(write.call_args.args[3],{'DTPhapLy':123.4567})
