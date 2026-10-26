"""Thanh Tan exporter: read-only MDB preparation and MicroStation VBA bridge."""
import base64, csv, datetime, hashlib, json, math, os, shutil, struct, subprocess, sys
from pathlib import Path
from workflow import drawing_paths, address_profile, save_address_profile, parcel_address, toolbar_icon
from quality import ring_issues, audit, matches, source_key, read_edits, merge_edits

ROOT = Path(__file__).resolve().parent
APP_VERSION = (ROOT / 'VERSION').read_text(encoding='utf-8-sig').strip()
APP_TITLE = 'SonMap+ V' + APP_VERSION
DEFAULTS = {'mdb': r'D:\BANDODUNGCHUNG\1. PHUONG NGA NAM\dc100.mdb',
 'dgn': r'D:\BANDODUNGCHUNG\1. PHUONG NGA NAM\dc100.dgn',
 'template': r'D:\TX NGA NAM\MAU\TrichLucTT26 -ThanhTan.dgn',
 'output': str(ROOT / 'exports'), 'address_suffix': '',
 'label_colors': True}

def geometry(encoded):
    data = base64.b64decode(encoded or '', validate=True)
    if len(data) < 13 or data[0] != 0 or struct.unpack_from('<II', data, 1) != (3, 1):
        raise ValueError('Chỉ hỗ trợ Geometry polygon một vòng đã xác minh của MDB này.')
    count = struct.unpack_from('<I', data, 9)[0]
    if count < 4 or count > 10000 or len(data) != 13 + count * 16:
        raise ValueError('Độ dài Geometry không hợp lệ.')
    points = [struct.unpack_from('<dd', data, 13 + i * 16) for i in range(count)]
    if not all(math.isfinite(v) for p in points for v in p):
        raise ValueError('Geometry có tọa độ không hữu hạn.')
    if math.dist(points[0], points[-1]) > .001:
        raise ValueError('Vòng thửa không khép kín.')
    points.pop()
    if len(set(points)) < 3: raise ValueError('Thửa suy biến.')
    errors=ring_issues(points)
    if errors:raise ValueError("; ".join(errors))
    return number_vertices(points)

def number_vertices(points):
    points=list(points)
    x0,y0=points[0]
    area2=sum((a[0]-x0)*(b[1]-y0)-(b[0]-x0)*(a[1]-y0) for a,b in edges(points))
    if area2>0:points.reverse()
    first=min(range(len(points)),key=lambda i:(-points[i][1],points[i][0]))
    return points[first:]+points[:first]

def edges(points):
    return zip(points, points[1:] + points[:1])

def neighbors(parcel, parcels):
    """Shared collinear segments; never infer neighbors by nearest centroid."""
    result, rays = [], []
    p = parcel['points']
    bounds=lambda pts:(min(v[0] for v in pts),min(v[1] for v in pts),max(v[0] for v in pts),max(v[1] for v in pts))
    box=bounds(p)
    for other in parcels:
        if other['key'] == parcel['key']: continue
        other_box=bounds(other['points'])
        if box[2]+.05<other_box[0] or other_box[2]+.05<box[0] or box[3]+.05<other_box[1] or other_box[3]+.05<box[1]:continue
        hits = []
        for i, (a, b) in enumerate(edges(p)):
            dx, dy = b[0]-a[0], b[1]-a[1]; length = math.hypot(dx, dy)
            if length < .001: continue
            for c, d in edges(other['points']):
                distance = lambda v: abs(dx*(v[1]-a[1])-dy*(v[0]-a[0]))/length
                if max(distance(c), distance(d)) > .05: continue
                project = lambda v: ((v[0]-a[0])*dx+(v[1]-a[1])*dy)/length
                lo, hi = sorted((project(c), project(d)))
                lo, hi = max(0, lo), min(length, hi)
                if hi-lo > .5: hits.append((hi-lo, i, (lo+hi)/(2*length)))
        if not hits: continue
        _, i, fraction = max(hits)
        result.append((i, fraction, str(other['TCT'])))
        q = other['points']
        for i, a in enumerate(p):
            for j, b in enumerate(q):
                if math.dist(a,b) > .05: continue
                for c in (q[j-1],q[(j+1)%len(q)]):
                    dx,dy=c[0]-a[0],c[1]-a[1]; length=math.hypot(dx,dy)
                    if length < .001: continue
                    shared=False
                    for t in (p[i-1],p[(i+1)%len(p)]):
                        ex,ey=t[0]-a[0],t[1]-a[1]; el=math.hypot(ex,ey)
                        if el and abs(dx*ey-dy*ex)/(length*el)<.01 and dx*ex+dy*ey>0: shared=True
                    if not shared:
                        ray=(i,dx/length,dy/length)
                        if not any(i==r[0] and abs(ray[1]-r[1])+abs(ray[2]-r[2])<.01 for r in rays):rays.append(ray)
    return result,rays

def load_mdb(path,allow_empty=False):
    if Path(path).suffix.lower() != '.mdb':
        raise ValueError('Ô Access MDB phải chọn tệp .mdb, không phải .dgn. Kiểm tra lại hai đường dẫn nguồn.')
    ps = Path(os.environ.get('WINDIR',r'C:\Windows'))/'SysWOW64/WindowsPowerShell/v1.0/powershell.exe'
    target=ROOT/'data/source.json'; target.parent.mkdir(exist_ok=True)
    # Jet creates a lock sidecar even for read-only connections. Use a verified
    # local snapshot so it never creates a file beside the user's original MDB.
    before=sha(path);snapshot=ROOT/'data/source_snapshot.mdb'
    shutil.copyfile(path,snapshot)
    if sha(path)!=before or sha(snapshot)!=before:
        raise RuntimeError('MDB thay đổi khi sao chép; đóng phần mềm đang cập nhật rồi đọc lại.')
    completed=subprocess.run([str(ps),'-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'read_mdb.ps1'),
        '-MdbPath',str(snapshot),'-JsonPath',str(target)],capture_output=True,text=True,creationflags=0x08000000)
    if completed.returncode: raise RuntimeError(completed.stderr.strip() or completed.stdout.strip())
    raw=json.loads(target.read_text(encoding='utf-8-sig')); raw=raw if isinstance(raw,list) else [raw]
    return decode_mdb_rows(raw,path,before,allow_empty)


def decode_mdb_rows(raw,path,before,allow_empty=False):
    parcels=[]; rejected=[]
    for row in raw:
        row['key']=f"{row['ToBD']}/{row['TCT']}/{row['ID']}"
        row['_source_key']=source_key(path,before)
        try:row['points']=geometry(row['Geometry']);parcels.append(row)
        except ValueError as exc:rejected.append({'key':row['key'],'reason':str(exc)})
    if not parcels and (raw or not allow_empty):raise ValueError('Không có thửa hợp lệ trong MDB.')
    overrides=ROOT/'data/overrides.json'
    if overrides.exists():
        saved=read_edits(json.loads(overrides.read_text(encoding='utf-8-sig')),source_key(path,before))
        for p in parcels:p.update({k:v for k,v in saved.get(p['key'],{}).items() if k in ('owner_override','address_override','land_override')})
    return parcels,rejected

def clean(value):return str('' if value is None else value).replace('\t',' ').replace('\r',' ').replace('\n',' ').strip()
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def vb_string(value):
    if any(ord(c)>127 for c in value):return 'U("'+' '.join(f'{ord(c):04X}' for c in value)+'")'
    return '"'+value.replace('"','""')+'"'

def prepare(config,parcels,rejected):
    expected=source_key(config['mdb'],sha(config['mdb']))
    if any(p.get('_source_key')!=expected for p in parcels):
        raise ValueError('MDB đã đổi hoặc dữ liệu không thuộc nguồn đang chọn. Đọc lại MDB trước khi xuất.')
    for parcel in parcels:
        if parcel.get('TCT') is None:raise ValueError('Thửa mới chưa có số hiệu chính thức. Nhập số thửa trước khi xuất hồ sơ.')
        errors=ring_issues(parcel['points'])
        if errors:raise ValueError(parcel['key']+': '+'; '.join(errors))
        parcel['points']=number_vertices(parcel['points'])
    for name in ('mdb','dgn','template'):
        if not Path(config[name]).is_file():raise FileNotFoundError(config[name])
    output=Path(config['output']).resolve();output.mkdir(parents=True,exist_ok=True)
    if any(output==Path(config[k]).resolve() for k in ('mdb','dgn','template')):raise ValueError('Thư mục xuất không hợp lệ.')
    rows=[]
    keys=[p['key'] for p in parcels]
    if len(set(keys))!=len(keys):raise ValueError('MDB có ID bản ghi trùng nhau; cần kiểm tra trước khi xuất.')
    for p in parcels:
        near,rays=neighbors(p,parcels)
        address=clean(parcel_address(p,config.get('address_profile',{})))
        land=clean(p.get('land_override')) or clean(p.get('LRD')) or clean(p.get('MaLD'))
        row=[p['ToBD'],p['TCT'],p['DienTich'],p.get('owner_override') or p.get('TenChu'),address,land,
            ';'.join(f'{x:.12g}|{y:.12g}' for x,y in p['points']),
            ';'.join(f'{i}|{f:.12g}|{number}' for i,f,number in near),
            ';'.join(f'{i}|{x:.12g}|{y:.12g}' for i,x,y in rays),p['ID'],p.get('DiaChi')]
        rows.append('\t'.join(clean(v) for v in row))
    data=ROOT/'data/parcels.tsv';data.write_text('\n'.join(rows),encoding='utf-16')
    template=(ROOT/'template_engine.bas').read_text(encoding='ascii')
    bridge=(ROOT/'bridge.bas').read_text(encoding='ascii')
    bridge+='\n'+(ROOT/'mau03_engine.bas').read_text(encoding='ascii')
    # Keep already verified drawing/text primitives; replace fixed test logic.
    helpers=template[template.index('Private Sub PutText'):]
    for name in ('DrawCoordinateTable','DrawLengthTable','DrawParcelAnnotations','PutNeighborLabel','FillParcelHeader'):
        start=helpers.index('Private Sub '+name+'(')
        end=helpers.index('End Sub',start)+len('End Sub')
        helpers=helpers[:start]+helpers[end:]
    helpers=helpers.replace('Point3dFromXYZ(x, y, 0)', 'Point3dFromXYZ(x + tableOffset, y, 0)')
    helpers=helpers.replace('Point3dFromXYZ(x1, y1, 0), Point3dFromXYZ(x2, y2, 0)',
        'Point3dFromXYZ(x1 + tableOffset, y1, 0), Point3dFromXYZ(x2 + tableOffset, y2, 0)')
    helpers=helpers.replace('If levelCode > 0 Then Set t.Level = CadLevel(levelCode)',
        'If levelCode = 0 Then levelCode = 63\n    Set t.Level = CadLevel(levelCode)')
    helpers=helpers.replace('If levelCode > 0 Then Set e.Level = CadLevel(levelCode)',
        'If levelCode = 0 Then levelCode = 63\n    Set e.Level = CadLevel(levelCode)')
    helpers=helpers.replace('ActiveModelReference.AddElement t',
        'If labelParts Is Nothing Then\n        ActiveModelReference.AddElement t\n    Else\n        labelParts.Add t\n    End If')
    helpers=helpers.replace('ActiveModelReference.AddElement e',
        'If labelParts Is Nothing Then\n        ActiveModelReference.AddElement e\n    Else\n        labelParts.Add e\n    End If')
    declarations=template[:template.index('Public Sub GhepThanhTan')]
    declarations=declarations.replace('LH_GhepThanhTan','LH_ThanhTanApp')
    replacements={'@DATA@':vb_string(str(data)), '@SOURCE@':'RuntimeSetting(0)',
        '@TEMPLATE@':vb_string(str(Path(config['template']).resolve())), '@MAU03@':vb_string(str(ROOT/'assets/Mau03CLBD.dgn')), '@OUTPUT@':'RuntimeSetting(4)',
        '@REQUEST@':vb_string(str(ROOT/'data/request.txt')), '@RESULT@':vb_string(str(ROOT/'data/result.txt')),
        '@COLORS@':'True' if config.get('label_colors') else 'False'}
    for key,name in [('@MDB@','mdb'),('@MDBDATE@','mdb'),('@DGNDATE@','dgn')]:
        replacements[key]=vb_string(str(Path(config[name]).resolve()) if key=='@MDB@' else
            datetime.datetime.fromtimestamp(Path(config[name]).stat().st_mtime).strftime('%Y%m%d%H%M%S'))
    replacements.update({'@MDB@':'RuntimeSetting(1)','@DGNDATE@':'RuntimeSetting(2)','@MDBDATE@':'RuntimeSetting(3)','@RUNTIME@':vb_string(str(ROOT/'data/runtime.txt'))})
    for key,value in replacements.items():bridge=bridge.replace(key,value)
    runtime=[str(Path(config['dgn']).resolve()),str(Path(config['mdb']).resolve()),datetime.datetime.fromtimestamp(Path(config['dgn']).stat().st_mtime).strftime('%Y%m%d%H%M%S'),datetime.datetime.fromtimestamp(Path(config['mdb']).stat().st_mtime).strftime('%Y%m%d%H%M%S')]
    runtime.append(str(output))
    (ROOT/'data/runtime.txt').write_text('\n'.join(runtime),encoding='utf-16')
    macro=ROOT/'LH_ThanhTanApp.bas';macro.write_bytes((declarations+bridge+'\n'+helpers).replace('\r\n','\n').replace('\n','\r\n').encode('ascii'))
    manifest={'source':{key:{'path':config[key],'sha256':sha(config[key])} for key in ('mdb','dgn','template')},
        'parcels':len(parcels),'rejected':rejected,'config':config}
    (ROOT/'data/manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    saved=json.loads((ROOT/'data/overrides.json').read_text(encoding='utf-8-sig')) if (ROOT/'data/overrides.json').exists() else {}
    saved=merge_edits(saved,source_key(config['mdb'],sha(config['mdb'])),parcels)
    (ROOT/'data/overrides.json').write_text(json.dumps(saved,ensure_ascii=False,indent=2),encoding='utf-8')
    return macro

def gui():
    import tkinter as tk
    from tkinter import ttk,filedialog,messagebox
    cfg=DEFAULTS.copy()
    if (ROOT/'settings.json').exists():cfg.update(json.loads((ROOT/'settings.json').read_text(encoding='utf-8-sig')))
    for key in ('mdb','dgn','template','output'):
        if not Path(cfg[key]).is_absolute():cfg[key]=str((ROOT/cfg[key]).resolve())
    win=tk.Tk();win.title(APP_TITLE);win.geometry('900x300');win.iconbitmap(str(ROOT/'sonmap.ico'))
    def show_window():
        win.deiconify()
        win.lift()
        win.attributes('-topmost',True)
        win.after(700,lambda:win.attributes('-topmost',False))
        win.focus_force()
    win.after(200,show_window)
    state={'parcels':[],'rejected':[],'exporting':False};variables={}
    for key in ('mdb','dgn','template','output','address_suffix'):variables[key]=tk.StringVar(value='')
    state['drawing']='';state['address_profile']={}
    drawing_label=tk.StringVar(value='Đang chờ DGN mở trong MicroStation V8i…')
    ttk.Label(win,textvariable=drawing_label,wraplength=860).grid(row=0,column=0,columnspan=3,sticky='w',padx=10,pady=8)
    icons={key:toolbar_icon(tk,win,key) for key in ('read','save','build','export','print','sheet','address','find','check','list','map')}
    color=tk.BooleanVar(value=cfg['label_colors'])
    color_option=ttk.Checkbutton(win,text='Màu nhãn theo mẫu',variable=color)
    tree=ttk.Treeview(win,columns=('sheet','parcel','id','owner','area','land'),show='headings',selectmode='browse')
    for k,title,width in [('sheet','Tờ',60),('parcel','Thửa',70),('id','ID MDB',60),('owner','Chủ sử dụng',290),('area','Diện tích',100),('land','Loại đất',90)]:
        tree.heading(k,text=title);tree.column(k,width=width)
    searchbar=ttk.Frame(win);searchbar.grid(row=11,column=0,columnspan=3,sticky='ew',padx=10,pady=4)
    search_vars={}
    for label,key,width in [('Tờ','sheet',6),('Thửa','number',8),('ID','record_id',8),('Tên chủ','owner',24)]:
        ttk.Label(searchbar,text=label).pack(side='left');search_vars[key]=tk.StringVar()
        ttk.Entry(searchbar,textvariable=search_vars[key],width=width).pack(side='left',padx=3)
    def filter_rows():
        if state['exporting']:return
        tree.delete(*tree.get_children())
        query={k:v.get() for k,v in search_vars.items()}
        for i,p in enumerate(state['parcels']):
            if matches(p,**query):tree.insert('', 'end',iid=str(i),values=(p['ToBD'],p.get('TCT') or 'Chờ số',p['ID'],p.get('owner_override') or p.get('TenChu'),p['DienTich'],p.get('land_override') or p.get('LRD') or p.get('MaLD')))
        status.set(f'{len(tree.get_children())}/{len(state["parcels"])} kết quả. Thửa trùng số được giữ riêng theo ID.')
    def clear_search():
        for v in search_vars.values():v.set('')
        filter_rows()
    def quality_report():
        if state['exporting']:return
        if not state['parcels'] and not state['rejected']:read()
        if not state['parcels'] and not state['rejected']:return
        checks=audit(state['parcels'],state['rejected'])
        dialog=tk.Toplevel(win);dialog.title('Kiểm tra dữ liệu MDB — chưa kiểm tra ranh DGN');dialog.geometry('1000x500')
        ttk.Label(dialog,text=f'{len(checks)} cảnh báo. Nhấp đúp để chọn thửa trong danh sách. Không tự sửa ranh hoặc số thửa.').pack(fill='x')
        table=ttk.Treeview(dialog,columns=('key','code','detail'),show='headings')
        for key,title,width in [('key','Tờ/thửa/ID',130),('code','Loại lỗi',120),('detail','Chi tiết',700)]:table.heading(key,text=title);table.column(key,width=width)
        scroll=ttk.Scrollbar(dialog,orient='vertical',command=table.yview);table.configure(yscrollcommand=scroll.set);scroll.pack(side='right',fill='y');table.pack(fill='both',expand=True)
        for i,item in enumerate(checks):table.insert('','end',iid=str(i),values=(item['key'],item['code'],item['detail']))
        def locate(_):
            if not table.selection():return
            key=checks[int(table.selection()[0])]['key'];clear_search()
            if not state['list_open']:toggle_parcels()
            for i,p in enumerate(state['parcels']):
                if p['key']==key:tree.selection_set(str(i));tree.see(str(i));selected();return
            messagebox.showinfo('Thửa bị loại','Thửa này không được nạp để xuất vì hình học chưa hợp lệ.',parent=dialog)
        def export_report():
            target=filedialog.asksaveasfilename(parent=dialog,defaultextension='.csv',initialfile='kiem-tra-thua.csv',filetypes=[('CSV','*.csv')])
            if target:
                try:
                    with open(target,'x',encoding='utf-8-sig',newline='') as f:
                        writer=csv.DictWriter(f,fieldnames=['key','code','detail']);writer.writeheader();writer.writerows(checks)
                except Exception as exc:messagebox.showerror('Không lưu báo cáo',str(exc),parent=dialog)
        table.bind('<Double-1>',locate)
        ttk.Button(dialog,text='Lưu báo cáo CSV',command=export_report).pack()
    ttk.Button(searchbar,text='Tìm',image=icons['find'],compound='left',command=filter_rows).pack(side='left',padx=4)
    ttk.Button(searchbar,text='Xóa lọc',command=clear_search).pack(side='left',padx=4)
    ttk.Button(searchbar,text='Kiểm tra dữ liệu',image=icons['check'],compound='left',command=quality_report).pack(side='left',padx=4)
    tree.grid(row=7,column=0,columnspan=3,sticky='nsew',padx=10,pady=8)
    edit_vars={}
    panel=ttk.Frame(win);panel.grid(row=8,column=0,columnspan=3,sticky='ew',padx=10)
    for i,(k,label) in enumerate([('owner_override','Chủ sử dụng'),('address_override','Địa chỉ thửa đất'),('land_override','Mã loại đất')]):
        ttk.Label(panel,text=label).grid(row=i,column=0,sticky='w');edit_vars[k]=tk.StringVar()
        ttk.Entry(panel,textvariable=edit_vars[k],width=95,state='readonly' if k=='address_override' else 'normal').grid(row=i,column=1,sticky='ew',pady=3)
    status=tk.StringVar(value='Đọc MDB, kiểm tra địa chỉ và thông tin, rồi tạo bộ xuất MicroStation.')
    ttk.Label(win,textvariable=status,wraplength=860).grid(row=10,column=0,columnspan=3,sticky='w',padx=10,pady=8)
    def settings(mode='TrichLuc'):
        if not state['drawing']:raise ValueError('Mở bản đồ DGN trong MicroStation trước.')
        paths=drawing_paths(state['drawing'],ROOT,mode,require_mdb=False)
        paths['mdb']=state.get('connected_mdb') or paths['mdb']
        if not Path(paths['mdb']).is_file():raise FileNotFoundError('Kết nối hoặc tạo MDB trước khi xuất hồ sơ.')
        return {**cfg,**paths,'address_suffix':'','address_profile':state['address_profile'],'label_colors':color.get()}
    def edit_address():
        if not state['drawing']:
            messagebox.showinfo('Địa chỉ thửa','Mở DGN trong MicroStation trước.');return
        dialog=tk.Toplevel(win);dialog.title('Địa bàn của thư mục bản đồ')
        fields={}
        catalog=json.loads((ROOT/'admin_catalog.json').read_text(encoding='utf-8'))['provinces']
        for i,(key,label) in enumerate([('province','Tỉnh / thành phố'),('commune','Xã / phường')]):
            ttk.Label(dialog,text=label).grid(row=i,column=0,padx=8,pady=5,sticky='w')
            fields[key]=tk.StringVar(value=state['address_profile'].get(key,''))
        province_box=ttk.Combobox(dialog,textvariable=fields['province'],values=sorted(catalog),state='readonly',width=48)
        province_box.grid(row=0,column=1,padx=8,pady=5)
        commune_box=ttk.Combobox(dialog,textvariable=fields['commune'],values=catalog.get(fields['province'].get(),[]),width=48)
        commune_box.grid(row=1,column=1,padx=8,pady=5)
        def province_changed(_):
            fields['commune'].set('');commune_box.configure(values=catalog.get(fields['province'].get(),[]))
        province_box.bind('<<ComboboxSelected>>',province_changed)
        ttk.Label(dialog,text='Chọn địa bàn; xứ đồng tự lấy từ trường Xudong của từng thửa.\nDanh sách năm 2025 gồm đơn vị mới; nếu thiếu xã giữ nguyên có thể bổ sung.').grid(row=2,column=0,columnspan=2,padx=8,pady=5)
        def commit():
            if state['exporting']:return
            profile={k:v.get() for k,v in fields.items()}
            try:save_address_profile(ROOT,state['drawing'],profile)
            except Exception as exc:messagebox.showerror('Không lưu được địa bàn',str(exc),parent=dialog);return
            state['address_profile']=profile;selected();dialog.destroy()
        ttk.Button(dialog,text='Lưu địa bàn',command=commit).grid(row=5,column=1,pady=8)

    def read():
        if state['exporting']:return
        if not state['drawing']:
            status.set('Mở DGN trong MicroStation; MDB cùng tên sẽ được nhận tự động.');return
        state.update(parcels=[],rejected=[])
        tree.delete(*tree.get_children())
        for variable in edit_vars.values():variable.set('')
        try:
            parcels,rejected=load_mdb(variables['mdb'].get(),allow_empty=True);state.update(parcels=parcels,rejected=rejected)
            tree.delete(*tree.get_children())
            for i,p in enumerate(parcels):tree.insert('', 'end',iid=str(i),values=(p['ToBD'],p.get('TCT') or 'Chờ số',p['ID'],p.get('TenChu'),p['DienTich'],p.get('LRD') or p.get('MaLD')))
            status.set(f'Đã đọc {len(parcels)} thửa; {len(rejected)} thửa không hỗ trợ. Chọn một dòng để bổ sung thông tin.')
        except Exception as exc:
            status.set('Chưa đọc được tờ mới. Kiểm tra đường dẫn Access MDB (.mdb).')
            messagebox.showerror('Không đọc được MDB',str(exc))
    def source_changed(*_):
        state.update(parcels=[],rejected=[])
        tree.delete(*tree.get_children())
        for variable in edit_vars.values():variable.set('')
        status.set('Nguồn đã đổi; bấm Đọc lại MDB trước khi chọn thửa xuất.')
    for key in ('mdb','dgn'):variables[key].trace_add('write',source_changed)
    def selected(_=None):
        if not tree.selection():return
        p=state['parcels'][int(tree.selection()[0])]
        edit_vars['owner_override'].set(p.get('owner_override') or p.get('TenChu') or '')
        address=parcel_address(p,state['address_profile'])
        state['shown_address']=address
        edit_vars['address_override'].set(address)
        edit_vars['land_override'].set(p.get('land_override') or p.get('LRD') or p.get('MaLD') or '')
        status.set('Địa chỉ thửa: xứ đồng MDB + xã/phường + tỉnh/thành phố. Có thể sửa riêng dòng đang chọn; dùng nút Địa chỉ thửa để đặt địa bàn.')
    tree.bind('<<TreeviewSelect>>',selected)
    def save_edit():
        if state['exporting']:return
        if tree.selection():
            if state['parcels'][int(tree.selection()[0])].get('_source_key')!=source_key(variables['mdb'].get(),sha(variables['mdb'].get())):
                raise ValueError('Nguồn MDB đã thay đổi. Đọc lại trước khi lưu chỉnh tay.')
            p=state['parcels'][int(tree.selection()[0])];p.update({k:v.get() for k,v in edit_vars.items() if k!='address_override'})
            tree.item(tree.selection()[0],values=(p['ToBD'],p.get('TCT') or 'Chờ số',p['ID'],p['owner_override'],p['DienTich'],p['land_override']))
            try:
                path=ROOT/'data/overrides.json'
                saved=json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else {}
                saved=merge_edits(saved,source_key(variables['mdb'].get(),sha(variables['mdb'].get())),state['parcels'])
                temp=path.with_suffix('.tmp');temp.write_text(json.dumps(saved,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(path)
                status.set('Đã lưu thông tin chỉnh tay riêng cho nguồn MDB này.')
            except Exception as exc:messagebox.showerror('Không lưu được thông tin',str(exc))
    def build(show_message=True):
        if state['exporting']:return False
        try:
            if Path(variables['dgn'].get()).suffix.lower() != '.dgn':
                raise ValueError('Ô Bản đồ DGN gốc phải chọn tệp .dgn, không phải .mdb.')
            if not state['parcels']:read()
            if not state['parcels']:return
            save_edit();config=settings();macro=prepare(config,state['parcels'],state['rejected'])
            (ROOT/'settings.json').write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
            status.set(f'Đã tạo {macro.name}. Import vào VBA MicroStation; chọn nhãn/đường bao rồi chạy XuatThuaDaChon.')
            if show_message:messagebox.showinfo('Đã tạo bộ xuất',f'{macro}\n\nMicroStation: import module, Debug → Compile.\nChọn đúng một nhãn hoặc đường bao thửa trong DGN gốc; chạy XuatThuaDaChon.')
            return True
        except Exception as exc:
            messagebox.showerror('Chưa tạo được bộ xuất',str(exc));return False
    def request(mode='TrichLuc'):
        if state['exporting']:messagebox.showinfo('Đang xuất','Đợi lượt xuất hiện tại hoàn tất.');return
        if not tree.selection():messagebox.showwarning('Chọn thửa','Chọn một dòng trong danh sách.');return
        import threading,queue,copy
        save_edit()
        config=settings(mode)
        if Path(config['dgn']).suffix.lower()!='.dgn':
            messagebox.showerror('Sai tệp','Bản đồ DGN gốc phải là .dgn.');return
        p=copy.deepcopy(state['parcels'][int(tree.selection()[0])])
        parcels=copy.deepcopy(state['parcels']);rejected=copy.deepcopy(state['rejected'])
        state['exporting']=True
        status.set('Đang chuẩn bị dữ liệu và tứ cận; giao diện vẫn hoạt động…')
        result=ROOT/'data/result.txt'
        completion=queue.Queue()
        def worker():
            try:
                prepare(config,parcels,rejected)
                (ROOT/'settings.json').write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
                (ROOT/'data/request.txt').write_text(p['key'],encoding='utf-16')
                result.write_text('PENDING\t'+p['key'],encoding='utf-16')
                ps=Path(os.environ.get('WINDIR',r'C:\Windows'))/'SysWOW64/WindowsPowerShell/v1.0/powershell.exe'
                updater=ROOT/'update_vba.ps1'
                if updater.exists():
                    updated=subprocess.run([str(ps),'-NoProfile','-ExecutionPolicy','Bypass','-File',str(updater),'-Root',str(ROOT)],capture_output=True,timeout=30,creationflags=0x08000000)
                    (ROOT/'data/vba-update-last.log').write_bytes(updated.stdout+b'\n'+updated.stderr)
                    if updated.returncode:raise RuntimeError('Chưa kết nối/cập nhật được VBA. Mở MicroStation V8i và DGN nguồn, đóng hộp thoại đang chặn rồi bấm xuất lại. Chi tiết: data/vba-update-last.log')
                process=subprocess.Popen([str(ps),'-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'run_export.ps1'),'-Mode',mode],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,creationflags=0x08000000)
                try:
                    stdout,stderr=process.communicate(timeout=2)
                    if process.returncode:raise RuntimeError(stderr.strip() or stdout.strip())
                except subprocess.TimeoutExpired:
                    # SendKeyin can remain blocked by the running macro or its
                    # message box. The VBA result file confirms actual success.
                    threading.Thread(target=process.communicate,daemon=True).start()
                completion.put(None)
            except Exception as exc:completion.put(str(exc))
        def wait_preparation():
            try:error=completion.get_nowait()
            except queue.Empty:
                win.after(200,wait_preparation);return
            if error:
                state['exporting']=False;status.set('Chưa gửi được lệnh xuất.')
                messagebox.showerror('Xuất chưa thành công',error);return
            status.set(f'Đang chờ MicroStation xuất tờ {p["ToBD"]}, thửa {p["TCT"]}…')
            win.after(500,poll)
        threading.Thread(target=worker,daemon=True).start()
        win.after(200,wait_preparation)
        def poll(attempt=0):
            try:fields=result.read_text(encoding='utf-16').split('\t',2)
            except (OSError,UnicodeError):fields=[]
            if len(fields)==3 and fields[1]==p['key'] and fields[0] in ('OK','ERROR'):
                state['exporting']=False
                if fields[0]=='OK':
                    state['last_output']=fields[2]
                    status.set('Đã lưu DGN: '+fields[2]);messagebox.showinfo('Đã xuất Mẫu 03/CLBĐ' if mode=='Mau03' else 'Đã tạo bản In GCN' if mode=='GCN' else 'Đã xuất trích lục',fields[2])
                else:status.set('Xuất chưa thành công.');messagebox.showerror('MicroStation báo lỗi',fields[2])
            elif attempt>=240:
                state['exporting']=False
                status.set('Chưa nhận được kết quả; kiểm tra hộp thoại MicroStation và module VBA.')
                messagebox.showwarning('Chưa có xác nhận xuất','Kiểm tra MicroStation. Import module mới có PublishResult, Debug → Compile. Không bấm xuất lại nếu macro vẫn đang chạy.')
            else:win.after(500,lambda:poll(attempt+1))
    def open_output_folder():
        try:
            folder=Path(state['last_output']).parent if state.get('last_output') else Path(settings('Mau03')['output'])
            folder.mkdir(parents=True,exist_ok=True);os.startfile(str(folder))
        except Exception as exc:messagebox.showerror('Chưa mở được thư mục',str(exc))
    def connect_v8i():
        ps=Path(os.environ.get('WINDIR',r'C:\Windows'))/'SysWOW64/WindowsPowerShell/v1.0/powershell.exe'
        subprocess.Popen([str(ps),'-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'start_v8i.ps1')],creationflags=0x08000000)
        status.set('Đang kết nối/khởi động V8i. Mở DGN nguồn; SonMap sẽ tự nhận MDB cùng tên.')
    state['list_open']=False
    def toggle_parcels():
        state['list_open']=not state['list_open']
        if state['list_open']:
            tree.grid();searchbar.grid();panel.grid();win.rowconfigure(7,weight=1);win.geometry('1050x730')
        else:
            tree.grid_remove();searchbar.grid_remove();panel.grid_remove();win.rowconfigure(7,weight=0);win.geometry('900x300')
    def reference_map():
        if state['exporting']:return
        if not state.get('last_output'):
            messagebox.showinfo('Ánh xạ tờ bản đồ','Xuất hồ sơ thành công trước, giữ bản vẽ kết quả mở rồi bấm Ánh xạ.');return
        import threading,queue
        result=queue.Queue();state['exporting']=True
        def work():
            try:
                ps=Path(os.environ.get('WINDIR',r'C:\Windows'))/'SysWOW64/WindowsPowerShell/v1.0/powershell.exe'
                proc=subprocess.run([str(ps),'-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'reference_map.ps1'),'-Source',state['drawing'],'-Target',state['last_output']],capture_output=True,timeout=20,creationflags=0x08000000)
                result.put((proc.returncode,(proc.stdout+proc.stderr).decode('utf-8',errors='replace')))
            except Exception as exc:result.put((1,str(exc)))
        def wait():
            try:code,text=result.get_nowait()
            except queue.Empty:win.after(200,wait);return
            state['exporting']=False
            (ROOT/'data/reference-last.log').write_text(text,encoding='utf-8')
            if code:messagebox.showerror('Chưa gắn được Reference',text)
            elif 'DISPLAY_OFF' in text:status.set('Đã tắt hiển thị tờ bản đồ Reference. Bấm Ánh xạ lần nữa để bật lại.')
            else:status.set('Đã bật hiển thị tờ bản đồ Reference. Bấm Ánh xạ lần nữa để tắt.')
        threading.Thread(target=work,daemon=True).start();win.after(200,wait)
    def database_connected(result):
        path=result['path']
        variables['mdb'].set(path);state['connected_mdb']=path;state['connected_drawing']=state.get('drawing','')
        if not state['drawing']:
            status.set('Đã kết nối MDB. Mở DGN trong V8i để làm việc với bản đồ.');return
        try:
            parcels,rejected=decode_mdb_rows(result['rows'],path,result['sha256'],allow_empty=True)
            state.update(parcels=parcels,rejected=rejected);filter_rows()
            status.set(f'Đã kết nối CSDL: {len(parcels)} thửa; {len(rejected)} hình học chưa hỗ trợ.')
        except Exception as exc:messagebox.showerror('Không nạp được dữ liệu thửa',str(exc))
    def dgn_tools(mode='main'):
        if state['exporting']:return
        from topology_ui import TopologyWorkspace
        workspace=state.get('topology_workspace')
        if workspace is None:
            workspace=TopologyWorkspace(win,state.get('drawing',''),lambda busy:state.update(exporting=busy),database_connected)
            state['topology_workspace']=workspace
        source=state.get('drawing','')
        if source and source!=workspace.source.get():workspace.source.set(source)
        workspace.current_mdb=variables['mdb'].get() if Path(variables['mdb'].get()).is_file() else None
        if workspace.current_mdb:workspace.database.set(workspace.current_mdb)
        {'main':workspace.main,'clean':workspace.clean,'topology':workspace.topology,'database':workspace.database_dialog}[mode]()
    compact=ttk.Frame(win);compact.grid(row=1,column=0,columnspan=3,sticky='w',padx=10,pady=5)
    ttk.Button(compact,text='Mở V8i',image=icons['read'],compound='left',command=connect_v8i).pack(side='left',padx=4)
    ttk.Button(compact,text='Danh sách thửa ▾',image=icons['list'],compound='left',command=toggle_parcels).pack(side='left',padx=4)
    ttk.Button(compact,text='Ánh xạ tờ bản đồ',image=icons['map'],compound='left',command=reference_map).pack(side='left',padx=4)
    primary=ttk.LabelFrame(win,text='BẢN ĐỒ ĐỊA CHÍNH');primary.grid(row=2,column=0,columnspan=3,sticky='ew',padx=10,pady=6)
    for title,mode in [('Sửa lỗi','clean'),('Tạo topology','topology'),('Kết nối CSDL','database')]:
        ttk.Button(primary,text=title,command=lambda selected_mode=mode:dgn_tools(selected_mode),width=24).pack(side='left',padx=8,pady=10)
    tree.grid_remove();searchbar.grid_remove();panel.grid_remove()
    buttons=ttk.Frame(win);buttons.grid(row=6,column=0,columnspan=3,sticky='w',padx=10,pady=8)
    for title,kind,command in [('Trích lục','export',request),('In GCN','print',lambda:request('GCN')),('Mẫu 03/CLBĐ','sheet',lambda:request('Mau03')),('Địa chỉ thửa','address',edit_address),('Thư mục hồ sơ','export',open_output_folder)]:
        ttk.Button(buttons,text=title,image=icons[kind],compound='left',command=command).pack(side='left',padx=3)
    state['export_tools_open']=False
    def toggle_export_tools():
        state['export_tools_open']=not state['export_tools_open']
        if state['export_tools_open']:
            buttons.grid();color_option.grid(row=5,column=0,columnspan=3,sticky='w',padx=10)
        else:buttons.grid_remove();color_option.grid_remove()
    ttk.Button(compact,text='Xuất hồ sơ ▾',command=toggle_export_tools).pack(side='left',padx=4)
    buttons.grid_remove()
    win.columnconfigure(1,weight=1);win.rowconfigure(7,weight=0)
    # Query document API in a worker: never use a stale marker or sample source.
    import threading,queue
    active_results=queue.Queue();state['probe_busy']=False
    def probe():
        try:
            ps=Path(os.environ.get('WINDIR',r'C:\Windows'))/'SysWOW64/WindowsPowerShell/v1.0/powershell.exe'
            result=subprocess.run([str(ps),'-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'active_dgn.ps1')],capture_output=True,timeout=4,creationflags=0x08000000)
            active_results.put((result.returncode,result.stdout.decode('utf-8-sig').strip() if result.returncode==0 else ''))
        except Exception:active_results.put((1,''))
    def follow_active():
        try:
            connection_code,raw=active_results.get_nowait();state['probe_busy']=False
            if connection_code==2:status.set('MicroStation V8i chưa chạy. Bấm Mở V8i rồi mở DGN nguồn.')
            elif connection_code==3:status.set('Đã kết nối V8i, đang chờ bạn mở DGN; giữ User/Project VietMapXM như hiện tại.')
            elif connection_code:status.set('V8i đang bận hoặc có hộp thoại chặn; xử lý thông báo trong V8i, app sẽ tự kết nối lại.')
            if not state['exporting']:
                # Recover source context after reopening the app on an exported drawing.
                if raw and not state.get('drawing'):
                    try:
                        receipt=(ROOT/'data/result.txt').read_text(encoding='utf-16').split('\t',2)
                        runtime=(ROOT/'data/runtime.txt').read_text(encoding='utf-16').splitlines()
                        if receipt[0]=='OK' and Path(receipt[2].strip()).resolve()==Path(raw).resolve():
                            paths=drawing_paths(cfg.get('dgn') or runtime[0],ROOT)
                            for key,value in paths.items():variables[key].set(value)
                            state['drawing']=paths['dgn'];state['last_output']=raw
                            state['address_profile']=address_profile(ROOT,paths['dgn'])
                            drawing_label.set('Nguồn: '+Path(paths['dgn']).name+' — Hồ sơ: '+Path(raw).name);read()
                    except (OSError,ValueError,IndexError):pass
                # Output DGN stays visible after exporting; keep the source context.
                generated=state.get('drawing') and raw and Path(raw).parent.name in ('Trích lục','In GCN','Phiếu đo đạc chỉnh lý','Trich luc','Phieu do dac chinh ly') and Path(raw).parent.parent==Path(state['drawing']).parent
                if not generated and (raw!=state.get('observed_dgn')):
                    state['observed_dgn']=raw;state['drawing']=''
                    if state.get('connected_mdb') and not state.get('connected_drawing'):state['connected_drawing']=raw
                    elif state.get('connected_drawing')!=raw:state['connected_mdb']='';state['connected_drawing']=''
                    source_changed()
                    if raw:
                        try:
                            paths=drawing_paths(raw,ROOT,require_mdb=False)
                            if state.get('connected_mdb'):paths['mdb']=state['connected_mdb']
                            for key,value in paths.items():variables[key].set(value)
                            state['drawing']=paths['dgn'];state['address_profile']=address_profile(ROOT,raw)
                            drawing_label.set('Bản đồ: '+Path(raw).name+'  —  '+str(Path(raw).parent))
                            if Path(paths['mdb']).is_file():read()
                            else:status.set('DGN chưa có MDB. Bấm Sửa lỗi hoặc Tạo topology để tạo dữ liệu từ bản vẽ.')
                        except Exception as exc:drawing_label.set(str(exc));status.set('Không nạp dữ liệu cũ. Mở DGN có MDB cùng tên để tiếp tục.')
                    else:drawing_label.set('Đang chờ DGN mở trong MicroStation V8i…')
        except queue.Empty:pass
        if not state['probe_busy'] and not state['exporting']:
            state['probe_busy']=True;threading.Thread(target=probe,daemon=True).start()
        win.after(2000,follow_active)
    win.after(100,follow_active)
    def close_main():
        if state['exporting']:
            messagebox.showinfo('Đang xử lý','Đợi tác vụ hiện tại hoàn tất trước khi đóng.');return
        win.destroy()
    win.protocol('WM_DELETE_WINDOW',close_main)
    win.mainloop()

if __name__=='__main__':
    if '--install' in sys.argv:
        config=DEFAULTS.copy();config.update(json.loads((ROOT/'settings.json').read_text(encoding='utf-8-sig')))
        parcels,rejected=load_mdb(config['mdb']);print(prepare(config,parcels,rejected))
    elif '--prepare' in sys.argv:
        config=DEFAULTS.copy();parcels,rejected=load_mdb(config['mdb']);print(prepare(config,parcels,rejected))
    else:
        import msvcrt
        (ROOT/'data').mkdir(exist_ok=True)
        import ctypes
        # Keep separate desktops/sessions from blocking the user's visible app.
        kernel32=ctypes.windll.kernel32
        user32=ctypes.windll.user32
        session=ctypes.c_ulong()
        kernel32.ProcessIdToSessionId(os.getpid(),ctypes.byref(session))
        user32.GetProcessWindowStation.restype=ctypes.c_void_p
        user32.GetThreadDesktop.argtypes=[ctypes.c_ulong]
        user32.GetThreadDesktop.restype=ctypes.c_void_p
        user32.GetUserObjectInformationW.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p,ctypes.c_ulong,ctypes.POINTER(ctypes.c_ulong)]
        scope=[str(session.value)]
        for handle in (user32.GetProcessWindowStation(),user32.GetThreadDesktop(kernel32.GetCurrentThreadId())):
            name=ctypes.create_unicode_buffer(256)
            needed=ctypes.c_ulong()
            if not user32.GetUserObjectInformationW(handle,2,name,ctypes.sizeof(name),ctypes.byref(needed)):
                raise ctypes.WinError()
            scope.append(name.value)
        scope_id=hashlib.sha256('|'.join(scope).encode()).hexdigest()[:16]
        instance_lock=open(ROOT/'data'/f'app-{scope_id}.lock','a+b')
        instance_lock.seek(0)
        try:msvcrt.locking(instance_lock.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:
            # A second launch should restore the existing window.
            import ctypes
            user32=ctypes.windll.user32
            user32.FindWindowW.argtypes=[ctypes.c_wchar_p,ctypes.c_wchar_p]
            user32.FindWindowW.restype=ctypes.c_void_p
            user32.ShowWindow.argtypes=[ctypes.c_void_p,ctypes.c_int]
            user32.SetForegroundWindow.argtypes=[ctypes.c_void_p]
            window=user32.FindWindowW(None,APP_TITLE)
            if window:
                user32.ShowWindow(window,9)
                user32.SetForegroundWindow(window)
            else:
                raise RuntimeError('ThanhTanApp is already running but its window is unavailable. Close that ThanhTanApp process and retry Start.cmd.')
            sys.exit(0)
        gui()
