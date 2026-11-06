import os
import unittest
from unittest.mock import patch
import app

@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'Requires Tk')
class ExportUiTests(unittest.TestCase):
    def test_list_zoom_and_both_export_controls_fit_window(self):
        from tkinter import ttk
        def check(root):
            try:
                def widgets(parent):
                    result=[]
                    for child in parent.winfo_children():result.append(child);result.extend(widgets(child))
                    return result
                buttons={str(w.cget('text')):w for w in widgets(root) if isinstance(w,ttk.Button)}
                self.assertIn('Zoom đến thửa',buttons)
                self.assertNotIn('Trích lục → chọn DGN',buttons)
                for name in ('Trích lục','In GCN','Mẫu 03/CLBĐ'):self.assertIn(name,buttons)
                buttons['Danh sách thửa ▾'].invoke()
                buttons['Xuất hồ sơ ▾'].invoke()
                root.update_idletasks()
                self.assertLessEqual(root.winfo_reqwidth(),root.winfo_width())
                self.assertLessEqual(root.winfo_reqheight(),root.winfo_height())
            finally:root.destroy()
        with patch('tkinter.Tk.mainloop',check):app.gui()
