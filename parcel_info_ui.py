"""Interior-point picking and selected-field editing of existing MDB attributes."""
import queue
import threading
from pathlib import Path
from parcel_info import pick_parcel, update_attributes, editable_columns
from topology_workflow import validate_parcel_context

LABELS={'ToBD':'Tờ bản đồ','TCT':'Số thửa','TenChu':'Tên chủ sử dụng','DiaChi':'Địa chỉ chủ sử dụng',
        'DiaChiThuaDatChiTiet':'Địa chỉ thửa đất','Xudong':'Xứ đồng','LRD':'Loại đất (LRD)','MaLD':'Mã loại đất'}


class ParcelInfoController:
    def __init__(self,parent,set_busy,on_saved,on_status=lambda text:None):
        self.parent=parent;self.set_busy=set_busy;self.on_saved=on_saved;self.on_status=on_status
        self.busy=False;self.dialog=None;self.selection=None;self.source='';self.mdb='';self.loading=False

    def run(self,work,done,restore=False):
        from tkinter import messagebox
        self.busy=True;self.set_busy(True);result=queue.Queue();self.set_editable(False)
        def worker():
            try:result.put((True,work()))
            except Exception as exc:result.put((False,str(exc)))
        def poll():
            try:ok,value=result.get_nowait()
            except queue.Empty:self.parent.after(100,poll);return
            self.busy=False;self.set_busy(False)
            if restore:
                self.parent.deiconify()
                if self.dialog and self.dialog.winfo_exists():self.dialog.deiconify();self.dialog.lift()
            self.set_editable(True)
            try:
                if not ok:raise ValueError(value)
                done(value)
            except Exception as exc:
                self.status.set('Chưa hoàn tất. Pick lại thửa nếu MDB đã thay đổi.')
                messagebox.showerror('Thông tin thửa',str(exc),parent=self.dialog or self.parent)
        threading.Thread(target=worker,daemon=True).start();self.parent.after(100,poll)

    def start(self,source,mdb):
        from tkinter import messagebox
        if self.busy:return
        if not source or not mdb or not Path(mdb).is_file():
            messagebox.showinfo('Thông tin thửa','Mở DGN và kết nối MDB trước.',parent=self.parent);return
        if self.dialog and self.dialog.winfo_exists():self.dialog.lift();return
        self.source=str(source);self.mdb=str(mdb);self.selection=None;self.show(None)

    def show(self,selection):
        import tkinter as tk
        from tkinter import ttk
        self.selection=selection
        if selection:self.source=selection['source'];self.mdb=selection['connected']['path']
        dialog=tk.Toplevel(self.parent);self.dialog=dialog
        dialog.title('SonMap+ — Thông tin thửa');dialog.geometry('650x540+40+40');dialog.minsize(600,450)
        dialog.protocol('WM_DELETE_WINDOW',self.close)
        self.header=tk.StringVar(master=dialog,value='Bấm nút con trỏ, rồi nhấp bên trong thửa trên DGN.')
        ttk.Label(dialog,textvariable=self.header,wraplength=610).pack(anchor='w',padx=14,pady=(12,6))
        self.notebook=ttk.Notebook(dialog);self.notebook.pack(fill='both',expand=True,padx=12,pady=6)
        form=ttk.Frame(self.notebook);self.notebook.add(form,text='Thông tin thửa')
        self.canvas=tk.Canvas(form,highlightthickness=0)
        scroll=ttk.Scrollbar(form,orient='vertical',command=self.canvas.yview)
        scroll.pack(side='right',fill='y');self.canvas.pack(side='left',fill='both',expand=True)
        self.canvas.configure(yscrollcommand=scroll.set)
        self.fields=ttk.Frame(self.canvas);item=self.canvas.create_window((0,0),window=self.fields,anchor='nw')
        self.fields.bind('<Configure>',lambda e:self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>',lambda e:self.canvas.itemconfigure(item,width=e.width))
        dialog.bind('<MouseWheel>',lambda e:self.canvas.yview_scroll(-int(e.delta/120),'units'))
        all_fields=ttk.Frame(self.notebook);self.notebook.add(all_fields,text='Toàn bộ thuộc tính')
        self.attributes=ttk.Treeview(all_fields,columns=('field','value'),show='headings')
        self.attributes.heading('field',text='Thuộc tính');self.attributes.heading('value',text='Giá trị')
        self.attributes.column('field',width=200);self.attributes.column('value',width=430)
        all_scroll=ttk.Scrollbar(all_fields,orient='vertical',command=self.attributes.yview)
        all_scroll.pack(side='right',fill='y');self.attributes.configure(yscrollcommand=all_scroll.set)
        self.attributes.pack(fill='both',expand=True)
        self.status=tk.StringVar(master=dialog,value='Chọn thửa để nạp thông tin.')
        ttk.Label(dialog,textvariable=self.status,wraplength=610).pack(fill='x',padx=14,pady=6)
        self.zoom=tk.BooleanVar(master=dialog,value=False)
        ttk.Checkbutton(dialog,text='Zoom đến thửa sau khi pick',variable=self.zoom).pack(anchor='w',padx=14)
        buttons=ttk.Frame(dialog);buttons.pack(fill='x',padx=14,pady=12)
        self.clear_button=ttk.Button(buttons,text='Bỏ chọn tất cả',command=self.clear_checks);self.clear_button.pack(side='left')
        self.pick_button=ttk.Button(buttons,text='↖  Pick trong thửa',command=self.repick);self.pick_button.pack(side='left',padx=8)
        ttk.Button(buttons,text='Đóng',command=self.close).pack(side='right')
        self.save_button=ttk.Button(buttons,text='Lưu',command=self.save);self.save_button.pack(side='right',padx=8)
        self.entries=[];self.checks=[];self.values={};self.enabled={}
        if selection:self.load_selection(selection)
        self.set_editable(True);dialog.lift()

    def discard(self):
        from tkinter import messagebox
        return not any(v.get() for v in self.enabled.values()) or messagebox.askyesno('Thông tin chưa lưu','Bỏ các chỉnh sửa chưa lưu để tiếp tục?',parent=self.dialog)

    def close(self):
        if not self.busy and self.discard():self.dialog.destroy();self.selection=None

    def clear_checks(self):
        if not self.busy:
            for var in self.enabled.values():var.set(False)

    def repick(self):
        if self.busy or not self.discard():return
        self.selection=None;self.clear_checks();self.set_editable(False)
        self.header.set('Nhấp bên trong thửa trên DGN; chuột phải để hủy.')
        self.dialog.withdraw();self.parent.iconify()
        def selected(result):
            if result:
                self.load_selection(result)
                if self.zoom.get():
                    from topology_workflow import focus_parcel
                    self.run(lambda:focus_parcel(result),lambda _:self.dialog.lift())
            else:
                self.header.set('Đã hủy chọn thửa. Bấm con trỏ để chọn lại.')
                self.status.set('Chưa chọn thửa để lưu.');self.set_editable(True)
        self.run(lambda:pick_parcel(self.source,self.mdb),selected,restore=True)

    def load_selection(self,selection):
        import tkinter as tk
        from tkinter import ttk
        from app import format_area
        self.loading=True;self.selection=selection;row=selection['row']
        self.header.set(f"Tờ {row['ToBD']}  |  Thửa {row.get('TCT') or 'Chờ số'}  |  Diện tích {format_area(row['DienTich'])} m²")
        for child in self.fields.winfo_children():child.destroy()
        self.values={};self.enabled={};self.entries=[];self.checks=[]
        for index,column in enumerate(editable_columns(selection['connected'])):
            name=column['name'];value=row.get(name)
            var=tk.StringVar(master=self.dialog,value='' if value is None else str(value))
            enabled=tk.BooleanVar(master=self.dialog,value=False)
            self.values[name]=var;self.enabled[name]=enabled
            check=ttk.Checkbutton(self.fields,text=LABELS.get(name,name),variable=enabled)
            check.grid(row=index,column=0,sticky='w',padx=6,pady=7);self.checks.append(check)
            entry=ttk.Entry(self.fields,textvariable=var);entry.grid(row=index,column=1,sticky='ew',padx=6,pady=7);self.entries.append(entry)
            var.trace_add('write',lambda *_, flag=enabled:None if self.loading else flag.set(True))
        self.fields.columnconfigure(1,weight=1);self.attributes.delete(*self.attributes.get_children())
        for name,value in row.items():
            shown='Hình học ranh thửa (chỉ đọc)' if name=='Geometry' else '' if value is None else str(value)
            self.attributes.insert('','end',values=(LABELS.get(name,name),shown))
        self.status.set('Chỉ ghi trường được đánh dấu. Để trống để xóa nội dung; diện tích hình học chỉ đọc.')
        self.loading=False;self.set_editable(True)

    def set_editable(self,enabled):
        if not self.dialog or not self.dialog.winfo_exists():return
        writable=enabled and bool(self.selection)
        for widget in self.entries+self.checks:widget.configure(state='normal' if writable else 'disabled')
        self.save_button.configure(state='normal' if writable else 'disabled')
        self.clear_button.configure(state='normal' if writable else 'disabled')
        self.pick_button.configure(state='normal' if enabled else 'disabled')

    def save(self):
        if self.busy or not self.selection:return
        changes={k:self.values[k].get() for k,v in self.enabled.items() if v.get()}
        if not changes:self.status.set('Chọn ít nhất một thuộc tính cần lưu.');return
        selected=self.selection;self.status.set('Đang sao lưu và kiểm tra các trường đã chọn…')
        def done(result):
            connected=result['connected'];row=next(r for r in connected['rows'] if r['ID']==selected['row']['ID'])
            self.load_selection({**selected,'connected':connected,'row':row});self.on_saved(connected)
            self.status.set('Không có giá trị thay đổi.' if result['status']=='unchanged' else 'Đã lưu. Sao lưu: '+result['backup'])
        def work():
            validate_parcel_context(selected)
            return update_attributes(selected['connected']['path'],selected['connected']['sha256'],selected['row']['ID'],changes)
        self.run(work,done)
