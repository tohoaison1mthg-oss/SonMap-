"""Tk interaction checks; Windows/Jet I/O is explicitly mocked."""
import copy
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from test_topology import project, line, rect, text
from topology import save_project
from topology_ui import TopologyWorkspace


@unittest.skipUnless(os.environ.get('DISPLAY') or os.name=='nt','Requires a Tk display')
class DialogTests(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        self.root=tk.Tk();self.root.withdraw()
        self.errors=[];self.infos=[];self.connected=[]
        self.stack=[]
        for name,output in [('showerror',self.errors),('showinfo',self.infos)]:
            p=patch('tkinter.messagebox.'+name,side_effect=lambda *a,_out=output,**k:_out.append(a))
            self.stack.append(p);p.start()
        self.workspace=TopologyWorkspace(self.root,'source.dgn',on_database=self.connected.append)
        self.temporary=tempfile.TemporaryDirectory();self.path=Path(self.temporary.name)/'project.json'
        self.data=project([line(rect(x=0,y=0))],[text('12',5,5,13)])
        self.data.update(source={'path':'source.dgn'},working_sha256='fixture',working_dgn='copy.dgn')
        save_project(self.path,self.data)

    def tearDown(self):
        self.root.destroy()
        for p in self.stack:p.stop()
        self.temporary.cleanup()

    def pump(self):
        deadline=time.monotonic()+4
        while self.workspace.busy and time.monotonic()<deadline:
            self.root.update();time.sleep(.01)
        self.root.update()
        self.assertFalse(self.workspace.busy)
        self.assertEqual(self.errors,[])

    def widgets(self,parent):
        result=[]
        for child in parent.winfo_children():result.append(child);result.extend(self.widgets(child))
        return result

    def button(self,parent,label):
        from tkinter import ttk
        return next(w for w in self.widgets(parent) if isinstance(w,ttk.Button) and w.cget('text')==label)

    def test_main_actions_open_separate_compact_dialogs(self):
        from tkinter import ttk
        main=self.workspace.main()
        for label,key in [('Sửa lỗi','clean'),('Tạo topology','topology'),('Kết nối CSDL','database')]:
            self.button(main,label).invoke();self.root.update()
            win=self.workspace.windows[key]
            self.assertLessEqual(win.winfo_width(),650)
            self.assertLessEqual(win.winfo_reqheight(),win.winfo_height())
            if key in ('clean','topology'):
                self.assertEqual(len(next(w for w in self.widgets(win) if isinstance(w,ttk.Notebook)).tabs()),1)
        self.assertNotEqual(self.workspace.windows['clean'],self.workspace.windows['topology'])

    def test_clean_and_topology_dispatch_different_drawing_operations(self):
        self.workspace.in_place.set(False)
        for kind,expected in [('clean',False),('topology',True)]:
            with patch('topology_ui.prepare',return_value=(self.path,copy.deepcopy(self.data))),patch('topology_ui.drawing_project',return_value='result.dgn') as write:
                self.workspace.process(kind);self.pump()
                write.assert_called_once_with(self.path,topology=expected)

    def test_database_read_and_create_connect_after_success(self):
        self.workspace.database_dialog();win=self.workspace.windows['database']
        result={'path':'chosen.mdb','count':0,'rows':[],'sha256':'fixture'}
        with patch('tkinter.filedialog.askopenfilename',return_value='chosen.mdb'),patch('topology_ui.inspect_database',return_value=result):
            self.button(win,'Đọc / kết nối MDB…').invoke();self.pump()
        with patch('tkinter.filedialog.asksaveasfilename',return_value='new.mdb'),patch('topology_ui.create_database',return_value={**result,'path':'new.mdb'}):
            self.button(win,'Tạo MDB mới…').invoke();self.pump()
        self.assertEqual([r['path'] for r in self.connected],['chosen.mdb','new.mdb'])

    def test_parcel_edit_saves_only_checked_fields(self):
        from tkinter import ttk
        self.workspace.project=copy.deepcopy(self.data);self.workspace.path=self.path
        self.workspace.parcels();win=self.workspace.windows['parcels']
        table=self.workspace.parcel_table;table.selection_set('0');self.root.update()
        form=next(w for w in self.widgets(win) if isinstance(w,ttk.LabelFrame))
        entries={int(w.grid_info()['row']):w for w in form.winfo_children() if isinstance(w,ttk.Entry)}
        for row,value in [(3,'New owner'),(4,'Ignore this address')]:entries[row].delete(0,'end');entries[row].insert(0,value)
        check=next(w for w in form.winfo_children() if isinstance(w,ttk.Checkbutton) and w.cget('text')=='Xứ đồng')
        check.invoke()
        self.button(win,'Lưu').invoke();self.root.update()
        saved=json.loads(self.path.read_text())['parcels'][0]
        self.assertEqual(saved['TenChu'],'New owner')
        self.assertEqual(saved['Xudong'],'')
        self.assertIn('TenChu',saved['manual_fields']);self.assertNotIn('Xudong',saved['manual_fields'])
        self.assertEqual(self.errors,[])

    def test_changing_dgn_invalidates_previous_parcels(self):
        self.workspace.project=copy.deepcopy(self.data);self.workspace.path=self.path
        self.workspace.parcels();self.root.update()
        self.workspace.source.set('other.dgn');self.root.update()
        self.assertIsNone(self.workspace.project)
        self.assertEqual(self.workspace.parcel_table.get_children(),())

    def test_clear_markers_works_after_manual_edit_without_reusing_old_analysis(self):
        self.workspace.project=copy.deepcopy(self.data);self.workspace.path=self.path
        with patch('topology_ui.clear_error_markers') as clear:
            self.workspace.clear_markers();self.pump()
        clear.assert_called_once_with('source.dgn')
        self.assertIsNone(self.workspace.project);self.assertIsNone(self.workspace.path)
        self.assertIn('kiểm tra lại',self.workspace.status.get())

    def test_auto_hide_is_default_for_both_processing_dialogs(self):
        self.workspace.clean();self.workspace.topology();self.root.update()
        self.assertTrue(self.workspace.options()['auto_hide'])
        for key in ('clean','topology'):
            self.button(self.workspace.windows[key],'Xóa dấu lỗi')
            self.button(self.workspace.windows[key],'Hiện lại lớp')

    def test_parcel_area_display_has_one_decimal_without_rounding_project(self):
        self.workspace.project=copy.deepcopy(self.data);self.workspace.path=self.path
        self.workspace.project['parcels'][0]['DienTich']=568.74321
        self.workspace.parcels();self.root.update()
        self.assertEqual(self.workspace.parcel_table.item('0','values')[3],'568,7')
        self.assertEqual(self.workspace.project['parcels'][0]['DienTich'],568.74321)
        self.assertIn('568,7 m²',self.workspace.report_detail({'area_m2':568.74321}))

    def test_default_direct_topology_updates_connected_mdb(self):
        self.workspace.current_mdb='current.mdb'
        result={'project':copy.deepcopy(self.data),'connected':{'path':'current.mdb','count':2,'rows':[],'sha256':'fixture'},'before_count':1,'after_count':2,'splits':[{}],'unnumbered':2,'backup':'backup'}
        with patch('topology_ui.prepare',return_value=(self.path,copy.deepcopy(self.data))),patch('topology_ui.apply_current',return_value=result) as update:
            self.workspace.process('topology');self.pump()
            update.assert_called_once_with(self.path,'current.mdb',clean_only=False)
        self.assertEqual(len(self.connected),1)
        self.assertIn('1 → 2',self.workspace.status.get())
