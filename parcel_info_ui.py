"""Interior-point picking and selected-field editing of existing MDB attributes."""
import queue
import threading
from pathlib import Path
from parcel_info import pick_parcel, update_attributes, editable_columns
from topology_workflow import validate_parcel_context

LABELS={'ToBD':'Tờ bản đồ','TCT':'Số thửa','TenChu':'Tên chủ sử dụng','DiaChi':'Địa chỉ chủ sử dụng',
        'DiaChiThuaDatChiTiet':'Địa chỉ thửa đất','Xudong':'Xứ đồng','LRD':'Loại đất (LRD)','MaLD':'Mã loại đất'}

# Only the user-requested cadastral fields belong in this dialog. Extra MDB columns stay untouched.
FORM_FIELDS={
 'ToBD':('Tờ BĐ',('ToBD',)), 'TCT':('Số thửa',('TCT',)),
 'temporary':('Số tạm',('ThuaTam','SoTam','SHTam')), 'DienTich':('Diện tích',('DienTich',)),
 'residential':('Đất ở',('dtThocu','DTDatO','DienTichDatO')),
 'legal_area':('DT pháp lý',('DTPhapLy','DienTichPhapLy')),
 'land':('MĐSD',('LRD','MaLD')), 'subject':('ĐTSD',('DTSD','KyHieuDTSD')),
 'parcel_address':('Địa chỉ thửa đất',('DiaChiThuaDatChiTiet','Xudong')),
 'TenChu':('Tên chủ SD',('TenChu',)), 'birth':('Năm sinh',('NamSinh','NamSinhChu','NamSinhChuSD')),
 'gender':('Giới tính',('GioiTinh','GioiTinhChu')),
 'identity':('Căn cước CD',('CCCD','SoCCCD','SoCMT','CMND','SoCMND')),
 'issue_date':('Ngày cấp',('NgayCap','NgayCapCCCD','NgayCapCMND')),
 'issue_place':('Nơi cấp',('NoiCap','NoiCapCCCD','NoiCapCMND')),
 'DiaChi':('Địa chỉ chủ SD',('DiaChi',)),
 'spouse':('Tên vợ/chồng',('TenVC','TenVoChong')),
 'spouse_birth':('Năm sinh',('NamSinhVC','NamSinhVoChong')),
 'spouse_gender':('Giới tính',('GioiTinhVC','GioiTinhVoChong')),
 'spouse_identity':('Căn cước CD',('CCCDVC','SoCMTVC','CMNDVC','SoCMNDVC')),
 'spouse_date':('Ngày cấp',('NgayCapVC','NgayCapCMNDVC')),
 'spouse_place':('Nơi cấp',('NoiCapVC','NoiCapCMNDVC')),
 'note':('Ghi chú',('GhiChu',))}
AREA_FIELDS={'DienTich','residential','legal_area'}
CHECK_FIELDS={'ToBD','TCT','temporary','residential','legal_area','land','subject','parcel_address','TenChu','DiaChi','note'}


def form_bindings(connected,row):
    available={c['name'].casefold():c['name'] for c in connected.get('columns',[])}
    result={}
    for key,(_,aliases) in FORM_FIELDS.items():
        names=[available[a.casefold()] for a in aliases if a.casefold() in available]
        if names:result[key]=next((n for n in names if row.get(n) not in (None,'')),names[0])
    return result


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
        dialog.title('SonMap+ — Sửa thông tin thửa');dialog.geometry('510x610+40+30');dialog.resizable(False,False)
        dialog.protocol('WM_DELETE_WINDOW',self.close)
        self.header=tk.StringVar(master=dialog,value='Chưa chọn thửa')
        self._vars={k:tk.StringVar(master=dialog) for k in FORM_FIELDS}
        self._enabled={k:tk.BooleanVar(master=dialog,value=False) for k in FORM_FIELDS}
        self._widgets={};self._checks={};self._writable=set();self._present=set()
        self.values={};self.enabled={};self.entries=[];self.checks=[]
        tabs=ttk.Notebook(dialog);tabs.pack(fill='both',expand=True,padx=7,pady=6)
        body=ttk.Frame(tabs);tabs.add(body,text='Thông tin thửa')
        def field(parent,key,row,col=0,wide=False):
            label=FORM_FIELDS[key][0]
            if key not in CHECK_FIELDS:ttk.Label(parent,text=label).grid(row=row,column=col,sticky='w',padx=4,pady=2)
            else:
                check=ttk.Checkbutton(parent,text=label,variable=self._enabled[key])
                check.grid(row=row,column=col,sticky='w',padx=4,pady=2);self._checks[key]=check
            entry=ttk.Entry(parent,textvariable=self._vars[key],width=11)
            entry.grid(row=row,column=col+1,columnspan=3 if wide else 1,sticky='ew',padx=4,pady=2)
            self._widgets[key]=entry
            self._vars[key].trace_add('write',lambda *_,k=key:None if self.loading or k not in self._writable else self._enabled[k].set(True))
        top=ttk.Frame(body);top.pack(fill='x',padx=3,pady=4)
        top.columnconfigure(1,weight=1);top.columnconfigure(3,weight=1)
        for row,pair in enumerate((('ToBD','TCT'),('temporary','DienTich'),('residential','legal_area'))):
            for col,key in zip((0,2),pair):field(top,key,row,col)
        land=ttk.Frame(body);land.pack(fill='x',padx=3,pady=3);land.columnconfigure(1,weight=1)
        for row,key in enumerate(('land','subject','parcel_address')):field(land,key,row)
        def person(keys):
            box=ttk.Frame(body);box.pack(fill='x',padx=3,pady=3)
            ttk.Separator(box).grid(row=0,column=0,columnspan=4,sticky='ew',pady=(0,4))
            box.columnconfigure(1,weight=1);box.columnconfigure(3,weight=1)
            name,birth,gender,identity,date,place=keys
            field(box,name,1,wide=True)
            field(box,birth,2);field(box,gender,2,2)
            field(box,identity,3);field(box,date,3,2)
            field(box,place,4,wide=True)
            return box
        owner=person(('TenChu','birth','gender','identity','issue_date','issue_place'))
        field(owner,'DiaChi',5,wide=True)
        spouse=person(('spouse','spouse_birth','spouse_gender','spouse_identity','spouse_date','spouse_place'))
        field(spouse,'note',5,wide=True)
        self.status=tk.StringVar(master=dialog,value='Bấm con trỏ hoặc Chọn, rồi nhấp bên trong thửa trên DGN.')
        ttk.Label(dialog,textvariable=self.status,wraplength=490).pack(fill='x',padx=10,pady=3)
        self.zoom=tk.BooleanVar(master=dialog,value=False)
        ttk.Checkbutton(dialog,text='Zoom đến tâm thửa khi pick bên trong',variable=self.zoom).pack(anchor='w',padx=10,pady=3)
        ttk.Separator(dialog).pack(fill='x',padx=8,pady=3)
        buttons=ttk.Frame(dialog);buttons.pack(fill='x',padx=10,pady=(5,10))
        self.clear_button=ttk.Button(buttons,text='Bỏ chọn tất cả',command=self.clear_checks);self.clear_button.pack(side='left')
        self.pick_button=ttk.Button(buttons,text='↖',width=3,command=self.repick);self.pick_button.pack(side='left',padx=10)
        self.choose_button=ttk.Button(buttons,text='Chọn',command=self.repick);self.choose_button.pack(side='left',expand=True,fill='x')
        self.save_button=ttk.Button(buttons,text='Lưu',command=self.save);self.save_button.pack(side='right',padx=(10,0))
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
        from app import format_area
        self.loading=True;self.selection=selection;row=selection['row']
        self.header.set(f"Tờ {row['ToBD']} | Thửa {row.get('TCT') or 'Chờ số'} | Diện tích {format_area(row['DienTich'])} m²")
        bindings=form_bindings(selection['connected'],row)
        self._present=set(bindings)
        editable={c['name'] for c in editable_columns(selection['connected'])}
        self.values={};self.enabled={};self._writable=set();self.original_display={}
        for key in FORM_FIELDS:
            name=bindings.get(key);value=row.get(name) if name else None
            shown='' if value in (None,'') else format_area(value) if key in AREA_FIELDS else str(value)
            self._vars[key].set(shown);self._enabled[key].set(False)
            if name in editable:
                self._writable.add(key);self.values[name]=self._vars[key];self.enabled[name]=self._enabled[key]
                self.original_display[name]=shown
        self.status.set('Chọn các thuộc tính cần lưu.')
        self.loading=False;self.set_editable(True)

    def set_editable(self,enabled):
        if not self.dialog or not self.dialog.winfo_exists():return
        writable=enabled and bool(self.selection)
        for key,widget in self._widgets.items():
            widget.configure(state='normal' if writable and key in self._writable else 'readonly' if enabled and self.selection and key in self._present else 'disabled')
        for key,check in self._checks.items():check.configure(state='normal' if writable and key in self._writable else 'disabled')
        self.save_button.configure(state='normal' if writable else 'disabled')
        self.clear_button.configure(state='normal' if writable else 'disabled')
        for button in (self.pick_button,self.choose_button):button.configure(state='normal' if enabled else 'disabled')

    def save(self):
        if self.busy or not self.selection:return
        changes={k:self.values[k].get() for k,v in self.enabled.items() if v.get()}
        if not changes:self.status.set('Chọn ít nhất một thuộc tính cần lưu.');return
        selected=self.selection
        changes={k:selected['row'].get(k) if self.values[k].get()==self.original_display[k] else v for k,v in changes.items()}
        self.status.set('Đang lưu thông tin thửa…')
        def done(result):
            connected=result['connected'];row=next(r for r in connected['rows'] if r['ID']==selected['row']['ID'])
            self.load_selection({**selected,'connected':connected,'row':row});self.on_saved(connected)
            self.last_backup=result['backup'];self.status.set('Không có giá trị thay đổi.' if result['status']=='unchanged' else 'Đã lưu thông tin thửa.')
        def work():
            validate_parcel_context(selected)
            return update_attributes(selected['connected']['path'],selected['connected']['sha256'],selected['row']['ID'],changes)
        self.run(work,done)
