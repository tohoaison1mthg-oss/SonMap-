"""Owner editor opened by a point picked in the active MicroStation drawing."""
import queue
import threading
from pathlib import Path
from parcel_info import pick_parcel, update_owner


class ParcelInfoController:
    def __init__(self,parent,set_busy,on_saved,on_status=lambda text:None):
        self.parent=parent;self.set_busy=set_busy;self.on_saved=on_saved
        self.busy=False;self.dialog=None
        self.on_status=on_status

    def run(self,work,done,restore=False):
        from tkinter import messagebox
        self.busy=True;self.set_busy(True);result=queue.Queue()
        def worker():
            try:result.put((True,work()))
            except Exception as exc:result.put((False,str(exc)))
        def poll():
            try:ok,value=result.get_nowait()
            except queue.Empty:self.parent.after(100,poll);return
            self.busy=False;self.set_busy(False)
            if restore:self.parent.deiconify();self.parent.lift()
            if ok:done(value)
            else:
                if self.dialog and self.dialog.winfo_exists():
                    self.set_editable(True);self.status.set('Chưa lưu. Kiểm tra thông báo rồi chọn lại thửa nếu MDB đã đổi.')
                else:self.on_status('Chưa chọn được thửa. Kiểm tra thông báo và thử lại.')
                messagebox.showerror('Thông tin thửa',value,parent=self.dialog if self.dialog and self.dialog.winfo_exists() else self.parent)
        threading.Thread(target=worker,daemon=True).start();self.parent.after(100,poll)

    def start(self,source,mdb):
        from tkinter import messagebox
        if self.busy:return
        if self.dialog and self.dialog.winfo_exists():self.dialog.lift();return
        if not source or not mdb or not Path(mdb).is_file():
            messagebox.showinfo('Thông tin thửa','Mở DGN và kết nối MDB trước.',parent=self.parent);return
        self.parent.iconify()
        def selected(result):
            if result:
                self.on_status('Đã chọn thửa. Sửa thông tin trong bảng rồi bấm Lưu vào MDB.')
                self.show(result)
            else:self.on_status('Đã hủy chọn thửa.')
        self.run(lambda:pick_parcel(source,mdb),selected,restore=True)

    def show(self,selection):
        import tkinter as tk
        from tkinter import ttk
        from app import format_area
        self.selection=selection;row=selection['row']
        dialog=tk.Toplevel(self.parent);self.dialog=dialog
        dialog.title('Thông tin thửa — cập nhật MDB');dialog.geometry('700x390');dialog.resizable(False,False)
        dialog.protocol('WM_DELETE_WINDOW',lambda:None if self.busy else dialog.destroy())
        self.metadata=lambda p:f"Tờ {p['ToBD']}  |  Thửa {p.get('TCT') or 'Chờ số'}  |  ID MDB {p['ID']}  |  Diện tích {format_area(p['DienTich'])} m²"
        self.header=tk.StringVar(master=dialog,value=self.metadata(row))
        ttk.Label(dialog,textvariable=self.header).pack(anchor='w',padx=14,pady=(12,6))
        ttk.Label(dialog,text='MDB: '+selection['connected']['path'],wraplength=665).pack(anchor='w',padx=14,pady=(0,10))
        fields=ttk.Frame(dialog);fields.pack(fill='x',padx=14)
        self.number=tk.StringVar(master=dialog,value='' if row.get('TCT') is None else str(row['TCT']))
        self.owner=tk.StringVar(master=dialog,value=row.get('TenChu') or '')
        self.address=tk.StringVar(master=dialog,value=row.get('DiaChi') or '')
        self.entries=[]
        for i,(label,var) in enumerate((('Số thửa',self.number),('Chủ sử dụng',self.owner),('Địa chỉ chủ sử dụng',self.address))):
            ttk.Label(fields,text=label).grid(row=i,column=0,sticky='w',padx=(0,10),pady=8)
            entry=ttk.Entry(fields,textvariable=var,width=65);entry.grid(row=i,column=1,sticky='ew',pady=8)
            self.entries.append(entry)
        fields.columnconfigure(1,weight=1)
        self.status=tk.StringVar(master=dialog,value='Các thửa tách có thể tạm cùng số cũ. Lưu theo ID MDB riêng, có sao lưu.')
        ttk.Label(dialog,textvariable=self.status,wraplength=665).pack(fill='x',padx=14,pady=12)
        buttons=ttk.Frame(dialog);buttons.pack(fill='x',padx=14,pady=8)
        ttk.Button(buttons,text='Đóng',command=lambda:None if self.busy else dialog.destroy()).pack(side='right')
        self.save_button=ttk.Button(buttons,text='Lưu vào MDB',command=self.save)
        self.save_button.pack(side='right',padx=8)
        dialog.lift();dialog.focus_force()

    def set_editable(self,enabled):
        for entry in self.entries:entry.configure(state='normal' if enabled else 'disabled')
        self.save_button.configure(state='normal' if enabled else 'disabled')

    def save(self):
        if self.busy:return
        selected=self.selection;owner=self.owner.get();address=self.address.get();number=self.number.get()
        self.set_editable(False);self.status.set('Đang sao lưu và cập nhật MDB…')
        def done(result):
            self.selection['connected']=result['connected']
            row=next(r for r in result['connected']['rows'] if r['ID']==selected['row']['ID'])
            self.selection['row']=row;self.header.set(self.metadata(row))
            self.number.set('' if row.get('TCT') is None else str(row['TCT']))
            self.owner.set(row.get('TenChu') or '');self.address.set(row.get('DiaChi') or '')
            self.on_saved(result['connected'])
            self.status.set('Đã lưu vào MDB. Sao lưu: '+result['backup'])
            self.set_editable(True);self.dialog.lift()
        self.run(lambda:update_owner(selected['connected']['path'],selected['connected']['sha256'],selected['row']['ID'],owner,address,number=number),done)
