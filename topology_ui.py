"""Compact cadastral tools: separate Clean, Topology and Database dialogs."""
import copy
import json
import queue
import threading
from pathlib import Path

from topology import BLOCKING, finite, save_project
from topology_workflow import (prepare, export_project, preview_project, drawing_project,
                               inspect_database, create_database, assign_labels, validate_options, apply_current,
                               display_levels, focus_issue, mark_errors, clear_error_markers)

ISSUES = {
 'UNSUPPORTED':'Phần tử ranh chưa hỗ trợ', 'SHORT_SEGMENT':'Đoạn ngắn',
 'ZERO_LENGTH_REMOVED':'Đã bỏ đoạn dài 0', 'DUPLICATE_REMOVED':'Đã bỏ đoạn trùng',
 'NEAR_NODE':'Các nút gần nhau', 'SNAPPED_ENDPOINT':'Đã nối cặp đầu hở',
 'CUT_EDGE':'Đường thừa / chưa tạo vùng', 'DANGLE':'Đầu ranh hở',
 'INVALID_RING':'Vòng không hợp lệ', 'HOLE_UNSUPPORTED':'Thửa có lỗ',
 'NO_PARCELS':'Chưa tạo được vùng', 'SMALL_PARCEL':'Vùng diện tích nhỏ',
 'LABEL_MISSING':'Thiếu nhãn', 'LABEL_AMBIGUOUS':'Nhãn trùng / nằm trên ranh',
 'LABEL_INVALID':'Số thửa không hợp lệ', 'ARC_APPROXIMATED':'Đã chia cung'
 ,'INTERSECTION_NODE':'Đã tạo giao điểm ranh'
}
DEFAULTS = dict(boundary_levels='10',sheet='1',metres_per_unit='1',short_length='.001',
 min_area='.3',near_distance='.1',snap_tolerance='.01',chord_tolerance='.001',
 centre_level='11',centre_color='3',centre_height='1',error_level='60',error_color='3',
 error_radius='.01',label_TCT='',label_LRD='',label_TenChu='',label_Xudong='')
FLAGS = dict(snap=False,break_arcs=False,break_complex=True,join_lines=False,
             short_enabled=True,area_enabled=True,near_enabled=True,auto_hide=True)


class TopologyWorkspace:
    def __init__(self,parent,source='',set_busy=lambda value:None,on_database=lambda value:None):
        import tkinter as tk
        self.parent=parent;self.set_busy=set_busy;self.on_database=on_database
        self.source=tk.StringVar(master=parent,value=source)
        self.vars={k:tk.StringVar(master=parent,value=v) for k,v in DEFAULTS.items()}
        self.flags={k:tk.BooleanVar(master=parent,value=v) for k,v in FLAGS.items()}
        self.status=tk.StringVar(master=parent,value='Chọn Sửa lỗi, Tạo topology hoặc Kết nối CSDL.')
        self.database=tk.StringVar(master=parent,value='Chưa kết nối CSDL')
        self.in_place=tk.BooleanVar(master=parent,value=True)
        self.current_mdb=None
        self.windows={};self.controls=[];self.busy=False;self.project=None;self.path=None
        self.source.trace_add('write',self.source_changed)

    def style_dialog(self,win):
        """Named styles keep the exporter's existing widgets unchanged."""
        from tkinter import ttk
        style=ttk.Style(win)
        style.configure('Topo.TFrame',background='#f2f6fa')
        style.configure('Topo.TLabel',background='#f2f6fa',foreground='#182f46',font=('Segoe UI',10))
        style.configure('Topo.TLabelframe',background='#f2f6fa',padding=4)
        style.configure('Topo.TLabelframe.Label',background='#f2f6fa',foreground='#185879',font=('Segoe UI',10,'bold'))
        for name in ('TCheckbutton','TRadiobutton'):
            style.configure('Topo.'+name,background='#f2f6fa',foreground='#182f46',font=('Segoe UI',10))
        style.configure('Topo.TButton',font=('Segoe UI',10),padding=(8,5))
        style.configure('Topo.Treeview',font=('Segoe UI',10),rowheight=28,background='#ffffff',foreground='#182f46')
        style.map('Topo.Treeview',background=[('selected','#185879')],foreground=[('selected','#ffffff')])
        win.configure(background='#f2f6fa')
        def apply(parent):
            for widget in parent.winfo_children():
                kind=widget.winfo_class()
                if kind in ('TFrame','TLabel','TLabelframe','TCheckbutton','TRadiobutton','TButton','Treeview'):
                    widget.configure(style='Topo.'+kind)
                apply(widget)
        apply(win)

    def source_changed(self,*_):
        self.project=None;self.path=None
        self.refresh_parcels()
        report=self.windows.get('report')
        if report and report.winfo_exists():report.destroy()
        self.status.set('Đã đổi DGN. Thực hiện Sửa lỗi hoặc Tạo topology trên bản vẽ mới.')

    def window(self,key,title,size):
        import tkinter as tk
        if self.busy:return None
        old=self.windows.get(key)
        if old and old.winfo_exists():old.deiconify();old.lift();return None
        win=tk.Toplevel(self.parent);win.title('SonMap+ — '+title);win.geometry(size)
        win.resizable(False,False)
        def close():
            if not self.busy:win.destroy()
        win.protocol('WM_DELETE_WINDOW',close)
        self.windows[key]=win
        return win

    def button(self,parent,text,command,**kwargs):
        from tkinter import ttk
        button=ttk.Button(parent,text=text,command=lambda:None if self.busy else command(),**kwargs)
        self.controls.append(button)
        return button

    def entry(self,parent,key,row,label,width=12,unit='',column=0,combo=False):
        from tkinter import ttk
        ttk.Label(parent,text=label).grid(row=row,column=column,sticky='w',padx=7,pady=5)
        if combo:
            values=tuple(str(i) for i in range(1,64))
            widget=ttk.Combobox(parent,textvariable=self.vars[key],values=values,width=width,state='readonly')
        else:widget=ttk.Entry(parent,textvariable=self.vars[key],width=width)
        widget.grid(row=row,column=column+1,sticky='w',padx=5,pady=5)
        if unit:ttk.Label(parent,text=unit).grid(row=row,column=column+2,sticky='w')
        self.controls.append(widget)
        return widget

    def checkbox(self,parent,key,text,row,column=0):
        from tkinter import ttk
        widget=ttk.Checkbutton(parent,text=text,variable=self.flags[key])
        widget.grid(row=row,column=column,sticky='w',padx=7,pady=5)
        self.controls.append(widget)
        return widget

    def source_box(self,parent):
        from tkinter import ttk,filedialog
        box=ttk.Frame(parent);box.pack(fill='x',padx=10,pady=8)
        ttk.Label(box,text='Bản vẽ').pack(side='left')
        entry=ttk.Entry(box,textvariable=self.source);entry.pack(side='left',fill='x',expand=True,padx=6)
        self.controls.append(entry)
        def choose():
            name=filedialog.askopenfilename(parent=parent,title='Chọn DGN đang mở trong V8i',filetypes=[('Bản vẽ DGN','*.dgn')])
            if name:self.source.set(name)
        self.button(box,'…',choose,width=3).pack(side='right')

    def footer(self,win,command,label='Thực hiện'):
        from tkinter import ttk
        ttk.Label(win,textvariable=self.status,wraplength=590).pack(fill='x',padx=12,pady=6)
        line=ttk.Frame(win);line.pack(fill='x',padx=12,pady=(4,12))
        self.button(line,'Đóng',win.destroy,width=12).pack(side='right',padx=4)
        self.button(line,label,command,width=16).pack(side='right',padx=4)
        self.style_dialog(win)

    def options(self):
        options={k:v.get().strip() for k,v in self.vars.items() if not k.startswith('label_')}
        options.update({k:v.get() for k,v in self.flags.items()})
        options['in_place']=self.in_place.get()
        options['label_levels']={k:self.vars['label_'+k].get().strip() for k in ('TCT','LRD','TenChu','Xudong')}
        validate_options(options)
        for key in ('metres_per_unit','short_length','min_area','near_distance','snap_tolerance'):
            finite(options[key],key,key=='metres_per_unit')
        if int(options['sheet'])<=0:raise ValueError('Số tờ bản đồ phải lớn hơn 0.')
        return options

    def launch(self,work,done):
        from tkinter import messagebox
        if self.busy:return
        self.busy=True;self.set_busy(True)
        saved=[]
        for widget in self.controls:
            if widget.winfo_exists():
                saved.append((widget,str(widget.cget('state'))));widget.configure(state='disabled')
        self.status.set('Đang thực hiện… Giữ nguyên bản vẽ và model trong V8i.')
        bars=[]
        from tkinter import ttk
        for win in self.windows.values():
            if win.winfo_exists():
                for widget in win.winfo_children():
                    if isinstance(widget,ttk.Progressbar):widget.start(12);bars.append(widget)
        result=queue.Queue()
        def run():
            try:result.put((True,work()))
            except Exception as exc:result.put((False,str(exc)))
        def poll():
            try:ok,value=result.get_nowait()
            except queue.Empty:self.parent.after(120,poll);return
            self.busy=False;self.set_busy(False)
            for bar in bars:
                if bar.winfo_exists():bar.stop()
            for widget,old in saved:
                if widget.winfo_exists():widget.configure(state=old)
            if ok:
                try:done(value)
                except Exception as exc:
                    self.status.set('Chưa cập nhật được kết quả.');messagebox.showerror('SonMap+',str(exc),parent=self.parent)
            else:
                self.status.set('Chưa hoàn tất. Xem thông báo lỗi để kiểm tra.')
                messagebox.showerror('Không thực hiện được',value,parent=self.parent)
        threading.Thread(target=run,daemon=True).start();self.parent.after(120,poll)

    def process(self,kind):
        from tkinter import messagebox
        try:options=self.options()
        except Exception as exc:messagebox.showerror('Thông số chưa đúng',str(exc),parent=self.parent);return
        source=self.source.get();target=self.current_mdb;self.project=None;self.path=None;self.refresh_parcels();self.refresh_report()
        def work():
            path,project=prepare(source,options)
            if kind=='topology' and target and options['in_place'] and any(i['code'] in BLOCKING for i in project['issues']):
                from database_topology import scope_splits
                project=scope_splits(project,inspect_database(target)['rows'])
                save_project(path,project)
            return path,project
        def done(value):
            self.path,self.project=value
            self.refresh_report();self.refresh_parcels()
            count=len(self.project['parcels']);errors=sum(i['code'] in BLOCKING for i in self.project['issues'])
            evidence='; '.join('lớp '+k+': '+str(v)+' phần tử' for k,v in self.project.get('input_summary',{}).items())
            timing=self.project.get('timing',{})
            elapsed=sum(timing.values())
            self.status.set(f'Đọc {evidence}. Tạo {count} vùng; {errors} lỗi ranh.'+(f' {elapsed:.1f} giây.' if timing else ''))
            if kind=='inspect':self.show_report();return
            if kind=='topology' and errors:self.show_report();return
            if kind=='clean' and any(i['code']=='UNSUPPORTED' for i in self.project['issues']):self.show_report();return
            if options['in_place']:
                self.launch(lambda:apply_current(self.path,target if kind=='topology' else None,clean_only=kind=='clean'),self.current_done)
            else:self.launch(lambda:drawing_project(self.path,topology=kind=='topology'),lambda path:self.drawing_done(kind,path))
        self.launch(work,done)

    def current_done(self,result):
        from tkinter import messagebox
        self.project=result['project'];self.refresh_parcels();self.refresh_report()
        text='Đã ghi vào DGN hiện tại. '
        if result.get('connected'):
            self.on_database(result['connected'])
            text+=f"MDB: {result['before_count']} → {result['after_count']} thửa; {len(result['splits'])} thửa được tách."
            if result['unnumbered']:text+=f" {result['unnumbered']} thửa chờ nhập số hiệu chính thức."
        else:text+='Chưa cập nhật MDB (chưa kết nối CSDL hoặc đang sửa ranh).'
        errors=sum(i['code'] in BLOCKING for i in self.project['issues'])
        if errors:text+=f' Còn {errors} lỗi ranh cần tìm và sửa thủ công.'
        if self.project.get('scope_rings'):
            outside=sum(i['code'] in BLOCKING for i in self.project.get('excluded_issues',[]))
            text+=f' Cập nhật cục bộ; {outside} lỗi ranh ngoài phạm vi chưa xử lý.'
        self.status.set(text)
        messagebox.showinfo('Đã cập nhật',text+ ('\nSao lưu trước thay đổi: '+result['backup'] if result.get('backup') else ''),parent=self.parent)
        if errors:self.show_report()

    def drawing_done(self,kind,path):
        from tkinter import messagebox
        count=len(self.project['parcels']);errors=sum(i['code'] in BLOCKING for i in self.project['issues'])
        title='Đã sửa ranh trên bản sao' if kind=='clean' else 'Đã tạo topology và tâm thửa'
        self.status.set(f'{title}. {count} vùng; {errors} lỗi ranh còn lại.')
        messagebox.showinfo(title,'Mở bản vẽ kết quả trong V8i:\n'+str(path)+'\n\nDGN nguồn được giữ nguyên.',parent=self.parent)

    def clean(self):
        from tkinter import ttk
        win=self.window('clean','Tự động tìm sửa lỗi','630x590')
        if not win:return
        self.status.set('')
        tabs=ttk.Notebook(win);tabs.pack(fill='both',expand=True,padx=8,pady=8)
        body=ttk.Frame(tabs);tabs.add(body,text='Tự động tìm sửa lỗi')
        top=ttk.Frame(body);top.pack(fill='x',padx=4,pady=6)
        duplicates=ttk.LabelFrame(top,text='Tùy chọn sửa lỗi trùng đè');duplicates.pack(side='left',fill='both',expand=True,padx=(0,5))
        ttk.Combobox(duplicates,values=('Giữ một đoạn trùng chính xác',),state='readonly',width=28).pack(fill='x',padx=8,pady=9)
        duplicates.winfo_children()[0].current(0)
        markers=ttk.LabelFrame(top,text='Thuộc tính cell báo lỗi');markers.pack(side='left',fill='both',expand=True)
        self.entry(markers,'error_level',0,'Lớp',width=10,combo=True)
        self.entry(markers,'error_color',1,'Màu',width=10)
        self.entry(markers,'error_radius',2,'Bán kính',width=10)
        grid=ttk.Frame(body);grid.pack(fill='x',padx=4,pady=3)
        self.checkbox(grid,'break_arcs','Phá vỡ Arc',0)
        self.checkbox(grid,'break_complex','Phá vỡ ComplexShape',0,2)
        self.checkbox(grid,'short_enabled','Báo đoạn thẳng ngắn hơn',1)
        ttk.Entry(grid,textvariable=self.vars['short_length'],width=10).grid(row=1,column=3,padx=4,pady=4)
        ttk.Label(grid,text='m').grid(row=1,column=4)
        self.checkbox(grid,'area_enabled','Báo vùng diện tích nhỏ hơn',2)
        ttk.Entry(grid,textvariable=self.vars['min_area'],width=10).grid(row=2,column=3,padx=4,pady=4)
        ttk.Label(grid,text='m²').grid(row=2,column=4)
        self.checkbox(grid,'join_lines','Kết nối LineString',3)
        self.checkbox(grid,'snap','Nối cặp đầu hở',3,2)
        self.checkbox(grid,'near_enabled','Kiểm tra nút gần nhau',4)
        ttk.Entry(grid,textvariable=self.vars['near_distance'],width=7).grid(row=4,column=1,padx=4)
        ttk.Label(grid,text='Sai số tiếp xúc').grid(row=4,column=2,sticky='w',padx=7)
        ttk.Entry(grid,textvariable=self.vars['snap_tolerance'],width=10).grid(row=4,column=3,padx=4)
        levels_box=ttk.LabelFrame(body,text='Danh sách các lớp tham gia');levels_box.pack(fill='x',padx=6,pady=8)
        ttk.Entry(levels_box,textvariable=self.vars['boundary_levels']).pack(fill='x',padx=8,pady=8)
        self.compact_footer(win,lambda:self.process('clean'),clean=True)

    def compact_footer(self,win,command,clean=False):
        import tkinter as tk
        from tkinter import ttk
        ttk.Label(win,textvariable=self.status,wraplength=600).pack(fill='x',padx=12,pady=3)
        ttk.Progressbar(win,mode='indeterminate').pack(fill='x',padx=12,pady=3)
        view=ttk.Frame(win);view.pack(fill='x',padx=10,pady=3)
        self.checkbox(view,'auto_hide','Tự ẩn lớp không tham gia trước khi chạy',0)
        self.button(view,'Hiện lại lớp',lambda:self.change_display(True),width=12).grid(row=0,column=1,padx=4)
        actions=ttk.Frame(win);actions.pack(fill='x',padx=10,pady=(4,10))
        self.button(actions,'Báo lỗi…',self.show_report,width=10).pack(side='left',padx=2)
        self.button(actions,'Xóa dấu lỗi',self.clear_markers,width=12).pack(side='left',padx=2)
        options=ttk.Menubutton(actions,text='Tùy chọn…',width=10);options.pack(side='left',padx=3)
        menu=tk.Menu(options,tearoff=False);options.configure(menu=menu)
        menu.add_command(label='Gán thông tin từ nhãn…',command=lambda:None if self.busy else self.labels())
        menu.add_command(label='Danh sách thửa dự án…',command=lambda:None if self.busy else self.parcels())
        menu.add_command(label='Đơn vị và sai số cung…',command=lambda:None if self.busy else self.advanced())
        self.button(actions,'Thực hiện',command,width=14).pack(side='right',padx=2)
        self.button(actions,'Đóng',win.destroy,width=10).pack(side='right',padx=4)
        def track(parent):
            for widget in parent.winfo_children():
                if isinstance(widget,(ttk.Entry,ttk.Combobox,ttk.Checkbutton,ttk.Radiobutton,ttk.Button,ttk.Menubutton)) and widget not in self.controls:self.controls.append(widget)
                track(widget)
        track(win)
        self.style_dialog(win)

    def clear_markers(self):
        source=self.source.get()
        def done(_):
            self.project=None;self.path=None
            self.refresh_parcels();self.refresh_report()
            self.status.set('Đã xóa vòng tròn báo lỗi SonMap. Chạy kiểm tra lại để cập nhật danh sách lỗi.')
        self.launch(lambda:clear_error_markers(source),done)

    def change_display(self,restore):
        source=self.source.get();selected=self.vars['boundary_levels'].get()
        self.launch(lambda:display_levels(source,selected,restore),lambda _:self.status.set(
            'Đã khôi phục trạng thái hiển thị lớp.' if restore else 'Đã ẩn lớp không tham gia. Phần tử bản vẽ được giữ nguyên.'))

    def topology(self):
        from tkinter import ttk
        win=self.window('topology','Tạo topology','630x565')
        if not win:return
        self.status.set('')
        tabs=ttk.Notebook(win);tabs.pack(fill='both',expand=True,padx=8,pady=8)
        body=ttk.Frame(tabs);tabs.add(body,text='Tạo topology')
        fields=ttk.Frame(body);fields.pack(fill='x',padx=4,pady=6)
        self.entry(fields,'boundary_levels',0,'Lớp tạo vùng (nhập số)',width=30)
        self.entry(fields,'sheet',1,'Tờ bản đồ số (nhập số)',width=30)
        self.controls.append(ttk.Radiobutton(body,text='Cập nhật DGN và CSDL đang kết nối',variable=self.in_place,value=True))
        self.controls[-1].pack(anchor='w',padx=12,pady=3)
        mode=ttk.LabelFrame(body,text='Thuộc tính khi ranh thửa thay đổi');mode.pack(fill='x',padx=12,pady=4)
        for row,pair in enumerate((('✓ Đo lại diện tích','✓ Giữ số hiệu thửa'),('✓ Giữ thông tin chủ','✓ Giữ loại đất, địa chỉ'))):
            for col,text in enumerate(pair):ttk.Label(mode,text=text).grid(row=row,column=col,sticky='w',padx=12,pady=4)
        self.controls.append(ttk.Radiobutton(body,text='Tạo DGN bản riêng',variable=self.in_place,value=False))
        self.controls[-1].pack(anchor='w',padx=12,pady=3)
        middle=ttk.Frame(body);middle.pack(fill='x',padx=8,pady=4)
        centre=ttk.LabelFrame(middle,text='Cell tâm thửa');centre.pack(side='left',fill='both',expand=True,padx=4)
        self.entry(centre,'centre_level',0,'Lớp',width=9,combo=True)
        self.entry(centre,'centre_color',1,'Màu',width=9)
        self.entry(centre,'centre_height',2,'Tỷ lệ / cỡ chữ',width=9)
        markers=ttk.LabelFrame(middle,text='Báo lỗi tạo vùng');markers.pack(side='left',fill='both',expand=True,padx=4)
        self.entry(markers,'error_level',0,'Lớp',width=9,combo=True)
        self.entry(markers,'error_color',1,'Màu',width=9)
        self.entry(markers,'error_radius',2,'Bán kính',width=9)
        self.compact_footer(win,lambda:self.process('topology'))

    def advanced(self):
        from tkinter import ttk
        win=self.window('advanced','Đơn vị và sai số','510x220')
        if not win:return
        box=ttk.Frame(win);box.pack(padx=10,pady=12)
        self.entry(box,'metres_per_unit',0,'Mét trên một đơn vị DGN')
        self.entry(box,'chord_tolerance',1,'Sai số dây cung',unit='m')
        ttk.Label(win,text='DGN dùng mét: nhập 1. Xuất MDB hiện yêu cầu đơn vị mét.').pack(padx=10,pady=8)
        self.button(win,'Đóng',win.destroy).pack(pady=8)

    def require_project(self):
        from tkinter import messagebox
        if self.project and self.path:return True
        messagebox.showinfo('Chưa có dữ liệu thửa','Thực hiện Tạo topology hoặc mở dự án đã lưu trước.',parent=self.parent)
        return False

    def labels(self):
        from tkinter import ttk
        win=self.window('labels','Gán thông tin từ nhãn bản vẽ','510x320')
        if not win:return
        box=ttk.Frame(win);box.pack(padx=10,pady=8)
        for row,(key,label) in enumerate([('label_TCT','Lớp số hiệu thửa'),('label_LRD','Lớp mã loại đất'),('label_TenChu','Lớp tên chủ sử dụng'),('label_Xudong','Lớp xứ đồng / địa chỉ')]):
            self.entry(box,key,row,label,width=16)
        ttk.Label(win,text='Để trống lớp nếu nhập tay. Nhãn phải nằm trong thửa.\nCác trường đã sửa tay được giữ lại.',wraplength=470).pack(padx=12,pady=6)
        def apply():
            if not self.require_project():return
            mapping={k:self.vars['label_'+k].get().strip() for k in ('TCT','LRD','TenChu','Xudong')}
            def done(project):self.project=project;self.refresh_report();self.status.set('Đã gán nhãn. Mở Thông tin thửa để kiểm tra.');self.refresh_parcels()
            self.launch(lambda:assign_labels(self.path,mapping),done)
        self.footer(win,apply,'Gán thông tin')

    def report_detail(self,item):
        parts=[]
        if item.get('field'):parts.append('Trường: '+{'TCT':'Số thửa','LRD':'Loại đất','TenChu':'Tên chủ','Xudong':'Xứ đồng'}.get(item['field'],item['field']))
        point=item.get('point') or (item.get('points') or [None])[0]
        if point:parts.append(f'X={point[0]:.4f}; Y={point[1]:.4f}')
        if 'area_m2' in item:
            from app import format_area
            parts.append("Diện tích "+format_area(item['area_m2'])+" m²")
        if 'length_m' in item:parts.append(f"Dài {item['length_m']:.5f} m")
        if item.get('reason'):parts.append(item['reason'])
        if item.get('detail'):parts.append(str(item['detail']))
        return ' — '.join(parts)

    def show_report(self):
        from tkinter import ttk
        if not self.require_project():return
        win=self.window('report','Danh sách lỗi','950x485')
        if not win:return
        table=ttk.Treeview(win,columns=('type','parcel','detail'),show='headings',height=13)
        for key,title,width in [('type','Loại lỗi',230),('parcel','ID thửa',70),('detail','Chi tiết',510)]:table.heading(key,text=title);table.column(key,width=width)
        scroll=ttk.Scrollbar(win,orient='vertical',command=table.yview);scroll.pack(side='right',fill='y')
        table.configure(yscrollcommand=scroll.set);table.pack(fill='both',expand=True,padx=8,pady=8)
        self.report_table=table
        self.refresh_report()
        actions=ttk.Frame(win);actions.pack(fill='x',padx=8,pady=10)
        self.button(actions,'◀ Trước',lambda:self.navigate_error(-1)).pack(side='left',padx=3)
        self.button(actions,'Tìm trên DGN',lambda:self.navigate_error(0)).pack(side='left',padx=3)
        self.button(actions,'Sau ▶',lambda:self.navigate_error(1)).pack(side='left',padx=3)
        self.button(actions,'Ghi dấu lỗi',self.mark_current).pack(side='left',padx=3)
        self.button(actions,'Xóa dấu lỗi',self.clear_markers).pack(side='left',padx=3)
        self.button(actions,'Kiểm tra lại sau sửa tay',lambda:self.process('inspect')).pack(side='left',padx=3)
        table.bind('<Double-1>',lambda _:self.navigate_error(0))
        self.style_dialog(win)

    def navigate_error(self,direction):
        table=self.report_table;items=table.get_children()
        if not items:return
        selected=table.selection();index=items.index(selected[0]) if selected else (-1 if direction>0 else 0)
        index=(index+direction)%len(items);iid=items[index]
        table.selection_set(iid);table.see(iid)
        issue=self.project['issues'][int(iid)]
        self.launch(lambda:focus_issue(self.project,issue),lambda _:self.status.set(
            f"Lỗi / thông báo {index+1}/{len(items)}: {ISSUES.get(issue['code'],issue['code'])}. Sửa trong V8i rồi kiểm tra lại."))

    def mark_current(self):
        def done(backup):
            self.project=json.loads(Path(self.path).read_text(encoding='utf-8'))
            self.status.set('Đã ghi dấu lỗi trên bản vẽ.')
        if self.require_project():self.launch(lambda:mark_errors(self.path),done)

    def refresh_report(self):
        table=getattr(self,'report_table',None)
        if table is None or not table.winfo_exists():return
        table.delete(*table.get_children())
        if not self.project:return
        for index,item in enumerate(self.project['issues']):
            if item['code'] in ('INTERSECTION_NODE','DUPLICATE_REMOVED','ZERO_LENGTH_REMOVED','SNAPPED_ENDPOINT'):continue
            label=('Đã sửa tay: ' if item.get('resolved_by_manual_edit') else '')+ISSUES.get(item['code'],item['code'])
            table.insert('','end',iid=str(index),values=(label,item.get('parcel',''),self.report_detail(item)))

    def preview(self):
        if not self.require_project():return
        def done(path):
            from tkinter import messagebox
            self.status.set('Đã ghi cell báo lỗi trên bản sao.')
            messagebox.showinfo('Bản vẽ báo lỗi','Mở trong V8i:\n'+str(path),parent=self.parent)
        self.launch(lambda:preview_project(self.path),done)

    def parcels(self):
        import tkinter as tk
        from tkinter import ttk
        if not self.require_project():return
        win=self.window('parcels','Sửa thông tin thửa','820x585')
        if not win:return
        table=ttk.Treeview(win,columns=('ID','ToBD','TCT','DienTich','TenChu','LRD'),show='headings',selectmode='browse',height=7)
        for key,title,width in [('ID','ID',45),('ToBD','Tờ',45),('TCT','Thửa',60),('DienTich','Diện tích',110),('TenChu','Tên chủ sử dụng',330),('LRD','Loại đất',140)]:table.heading(key,text=title);table.column(key,width=width)
        table.pack(fill='x',padx=10,pady=8);self.parcel_table=table
        form=ttk.LabelFrame(win,text='Thông tin thửa');form.pack(fill='x',padx=10,pady=5)
        entries={};enabled={}
        for row,(key,label) in enumerate([('ToBD','Tờ BĐ'),('TCT','Số hiệu thửa'),('LRD','Mục đích sử dụng'),('TenChu','Tên chủ sử dụng'),('Xudong','Xứ đồng'),('DiaChiThuaDatChiTiet','Địa chỉ thửa đất'),('DiaChi','Địa chỉ chủ sử dụng')]):
            entries[key]=tk.StringVar(master=win);enabled[key]=tk.BooleanVar(master=win,value=True)
            check=ttk.Checkbutton(form,text=label,variable=enabled[key]);check.grid(row=row,column=0,sticky='w',padx=8,pady=6);self.controls.append(check)
            entry=ttk.Entry(form,textvariable=entries[key],width=65);entry.grid(row=row,column=1,sticky='ew',padx=8,pady=6);self.controls.append(entry)
        form.columnconfigure(1,weight=1)
        area=tk.StringVar(master=win,value='Chọn một thửa trong danh sách.')
        ttk.Label(win,textvariable=area).pack(anchor='w',padx=15,pady=6)
        def select(_=None):
            if not table.selection() or not self.project:return
            p=self.project['parcels'][int(table.selection()[0])]
            for key,var in entries.items():var.set('' if p.get(key) is None else p.get(key,''))
            from app import format_area
            area.set("Diện tích đo: "+format_area(p['DienTich'])+" m²")
        table.bind('<<TreeviewSelect>>',select)
        def save():
            from tkinter import messagebox
            if not table.selection() or not self.project:return
            index=int(table.selection()[0]);updated=copy.deepcopy(self.project);p=updated['parcels'][index]
            try:
                manual=set(p.get('manual_fields',[]))
                for key,var in entries.items():
                    if not enabled[key].get():continue
                    value=var.get().strip()
                    if key in ('ToBD','TCT'):
                        value=int(value)
                        if not 0<value<=2147483647:raise ValueError('Số tờ và số thửa phải là số nguyên dương.')
                    elif len(value)>255:raise ValueError('Mỗi trường chữ tối đa 255 ký tự.')
                    p[key]=value;manual.add(key)
                p['manual_fields']=sorted(manual);p['MaLD']=p['LRD']
                for issue in updated['issues']:
                    if issue.get('parcel')==p['ID'] and issue.get('field') in manual:issue['resolved_by_manual_edit']=bool(p.get(issue['field']))
                save_project(self.path,updated);self.project=updated;self.refresh_parcels();self.refresh_report()
                table.selection_set(str(index));self.status.set('Đã lưu thông tin thửa vào dự án.')
            except Exception as exc:messagebox.showerror('Không lưu được thửa',str(exc),parent=win)
        self.refresh_parcels();self.footer(win,save,'Lưu')

    def refresh_parcels(self):
        from app import format_area
        table=getattr(self,'parcel_table',None)
        if table is None or not table.winfo_exists():return
        table.delete(*table.get_children())
        if not self.project:return
        for i,p in enumerate(self.project['parcels']):
            table.insert('','end',iid=str(i),values=[format_area(p.get(k)) if k=='DienTich' else p.get(k,'') for k in ('ID','ToBD','TCT','DienTich','TenChu','LRD')])

    def load_project(self):
        from tkinter import filedialog,messagebox
        name=filedialog.askopenfilename(parent=self.parent,title='Mở dự án SonMap',filetypes=[('Dự án SonMap','project.json')])
        if not name:return
        try:
            project=json.loads(Path(name).read_text(encoding='utf-8'))
            if project.get('version')!=1 or not all(k in project for k in ('source','parcels','options','working_dgn','working_sha256')):raise ValueError('Không phải dự án topology SonMap.')
            self.source.set(project['source']['path']);self.project=project;self.path=Path(name)
            for key,var in self.vars.items():
                value=project['options'].get('label_levels',{}).get(key[6:],'') if key.startswith('label_') else project['options'].get(key,DEFAULTS[key])
                var.set(value)
            for key,var in self.flags.items():var.set(project['options'].get(key,FLAGS[key]))
            self.status.set(f"Đã mở dự án: {len(project['parcels'])} thửa.");self.refresh_parcels();self.refresh_report()
        except Exception as exc:messagebox.showerror('Không mở được dự án',str(exc),parent=self.parent)

    def database_dialog(self):
        from tkinter import ttk,filedialog,messagebox
        win=self.window('database','Kết nối cơ sở dữ liệu','630x410')
        if not win:return
        box=ttk.LabelFrame(win,text='Cơ sở dữ liệu Access MDB');box.pack(fill='x',padx=12,pady=12)
        ttk.Label(box,textvariable=self.database,wraplength=580).pack(anchor='w',padx=10,pady=12)
        def connected(result):
            self.current_mdb=result['path']
            self.database.set(result['path']);self.status.set(f"Đã kết nối CSDL: {result['count']} thửa.")
            self.on_database(result)
        def connect():
            name=filedialog.askopenfilename(parent=win,title='Đọc / kết nối MDB',filetypes=[('Access MDB','*.mdb')])
            if name:self.launch(lambda:inspect_database(name),connected)
        def create():
            initial=Path(self.source.get()).with_suffix('.mdb').name if self.source.get() else 'BanDo.mdb'
            name=filedialog.asksaveasfilename(parent=win,title='Tạo MDB mới (không ghi đè)',defaultextension='.mdb',initialfile=initial,filetypes=[('Access MDB','*.mdb')])
            if name:self.launch(lambda:create_database(name),connected)
        buttons=ttk.Frame(box);buttons.pack(fill='x',padx=8,pady=8)
        self.button(buttons,'Đọc / kết nối MDB…',connect).pack(side='left',padx=4)
        self.button(buttons,'Tạo MDB mới…',create).pack(side='left',padx=4)
        project=ttk.LabelFrame(win,text='Dữ liệu từ topology');project.pack(fill='x',padx=12,pady=4)
        ttk.Label(project,text='Tạo MDB có dữ liệu sau khi kiểm tra vùng và gán số thửa.').pack(anchor='w',padx=10,pady=8)
        self.button(project,'Cập nhật MDB hiện tại',self.update_current).pack(anchor='w',padx=10,pady=(0,5))
        self.button(project,'Tạo DGN + MDB riêng…',self.export).pack(anchor='w',padx=10,pady=(0,10))
        links=ttk.Frame(win);links.pack(fill='x',padx=12,pady=8)
        self.button(links,'Mở dự án…',self.load_project).pack(side='left',padx=3)
        self.button(links,'Thông tin thửa…',self.parcels).pack(side='left',padx=3)
        self.button(links,'Đóng',win.destroy).pack(side='right',padx=3)
        ttk.Label(win,textvariable=self.status,wraplength=590).pack(fill='x',padx=12,pady=4)
        self.style_dialog(win)

    def update_current(self):
        from tkinter import messagebox
        if not self.require_project():return
        if not self.current_mdb:
            messagebox.showinfo('Chưa kết nối CSDL','Chọn Đọc / kết nối MDB trước.',parent=self.parent);return
        self.launch(lambda:apply_current(self.path,self.current_mdb),self.current_done)

    def export(self):
        from tkinter import messagebox
        if not self.require_project():return
        def done(receipt):
            self.status.set(f"Đã tạo DGN + MDB: {receipt['parcels']} thửa.")
            self.database.set(receipt['mdb'])
            messagebox.showinfo('Đã tạo dữ liệu','Mở DGN kết quả trong V8i để dùng cùng MDB:\n'+receipt['dgn'],parent=self.parent)
        self.launch(lambda:export_project(self.path),done)

    def main(self):
        from tkinter import ttk
        win=self.window('main','Bản đồ địa chính','640x210')
        if not win:return self.windows.get('main')
        self.source_box(win)
        bar=ttk.Frame(win);bar.pack(fill='x',padx=10,pady=10)
        for text,command in [('Sửa lỗi',self.clean),('Tạo topology',self.topology),('Kết nối CSDL',self.database_dialog)]:
            self.button(bar,text,command,width=22).pack(side='left',expand=True,padx=4,ipady=8)
        ttk.Label(win,textvariable=self.database,wraplength=600).pack(fill='x',padx=14,pady=4)
        ttk.Label(win,textvariable=self.status,wraplength=600).pack(fill='x',padx=14,pady=4)
        self.style_dialog(win)
        return win


def open_topology(parent,source='',set_busy=lambda value:None,on_database=lambda value:None):
    workspace=TopologyWorkspace(parent,source,set_busy,on_database)
    win=workspace.main();win.workspace=workspace
    return win
