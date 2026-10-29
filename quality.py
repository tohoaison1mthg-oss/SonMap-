"""Independent parcel checks; does not read or modify DGN geometry."""
import math
from collections import defaultdict

def area(points):
    x,y=points[0]
    return abs(sum((a[0]-x)*(b[1]-y)-(b[0]-x)*(a[1]-y)
                   for a,b in zip(points,points[1:]+points[:1])))/2

def ring_issues(points):
    n=len(points)
    if n<3 or not all(len(p)==2 and all(math.isfinite(v) for v in p) for p in points):
        return ['Tọa độ không hợp lệ hoặc không đủ ba đỉnh.']
    if n>2000:return ['Vượt giới hạn kiểm tra 2000 đỉnh; cần kiểm tra chuyên sâu.']
    if len(set(map(tuple,points)))!=n:return ['Có đỉnh trùng trong vòng thửa.']
    segments=list(zip(points,points[1:]+points[:1]))
    if any(math.dist(a,b)<1e-6 for a,b in segments):return ['Có cạnh dài gần bằng không.']
    def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    def sign(a,b,c):
        v=cross(a,b,c);eps=1e-9*max(1,math.dist(a,b))
        return 0 if abs(v)<=eps else (1 if v>0 else -1)
    def on(a,b,p):return min(a[0],b[0])-1e-9<=p[0]<=max(a[0],b[0])+1e-9 and min(a[1],b[1])-1e-9<=p[1]<=max(a[1],b[1])+1e-9
    for i,(a,b) in enumerate(segments):
        c=points[(i+2)%n]
        if sign(a,b,c)==0 and (b[0]-a[0])*(c[0]-b[0])+(b[1]-a[1])*(c[1]-b[1])<0:
            return [f'Cạnh {i+1} quay ngược, chồng lên cạnh kề.']
        for j in range(i+2,n):
            if i==0 and j==n-1:continue
            c,d=segments[j]
            if max(a[0],b[0])<min(c[0],d[0]) or max(c[0],d[0])<min(a[0],b[0]) or max(a[1],b[1])<min(c[1],d[1]) or max(c[1],d[1])<min(a[1],b[1]):continue
            s,t,u,v=sign(a,b,c),sign(a,b,d),sign(c,d,a),sign(c,d,b)
            if s*t<0 and u*v<0 or s==0 and on(a,b,c) or t==0 and on(a,b,d) or u==0 and on(c,d,a) or v==0 and on(c,d,b):
                return [f'Vòng tự cắt/chạm tại cạnh {i+1} và {j+1}.']
    if area(points)<1e-8:return ['Thửa có diện tích gần bằng không.']
    return []

def audit(parcels,rejected=()):
    issues=[];numbers=defaultdict(list);ids=defaultdict(list)
    def add(p,code,detail):issues.append({'key':p['key'],'code':code,'detail':detail})
    for p in parcels:
        if p.get('TCT') is None:add(p,'NUMBER_MISSING','Thửa mới chưa có số hiệu chính thức.')
        else:numbers[(p['ToBD'],p['TCT'])].append(p)
        ids[p['key']].append(p)
        errors=ring_issues(p['points'])
        for detail in errors:add(p,'GEOMETRY',detail)
        if not errors:
            measured=area(p['points'])-sum(area(r) for r in p.get('holes',[]))
            try:stored=float(p['DienTich'])
            except (ValueError,TypeError,KeyError):stored=float('nan')
            if not math.isfinite(stored) or stored<=0:add(p,'AREA_INVALID','Diện tích MDB trống/không dương.')
            elif abs(measured-stored)>max(.1,stored*.001):add(p,'AREA_DIFF',f'MDB={stored:.3f}; hình học={measured:.3f}; lệch={measured-stored:+.3f} m² (ngưỡng cảnh báo 0,1 m² hoặc 0,1%).')
        if not (p.get('LRD') or p.get('MaLD') or p.get('land_override')):add(p,'LAND_MISSING','Chưa có mã loại đất.')
    for group in numbers.values():
        if len(group)>1:
            for p in group:add(p,'DUP_NUMBER','Trùng số tờ/thửa; chọn theo ID MDB, không tự đánh lại số.')
    for group in ids.values():
        if len(group)>1:
            for p in group:add(p,'DUP_ID','Trùng khóa bản ghi; không xuất.')
    for p in rejected:issues.append({'key':p['key'],'code':'REJECTED','detail':p['reason']})
    return issues

def matches(parcel,sheet='',number='',record_id='',owner=''):
    return all(not value.strip() or str(parcel[field])==value.strip() for field,value in
               [('ToBD',sheet),('TCT',number),('ID',record_id)]) and owner.strip().casefold() in str(parcel.get('owner_override') or parcel.get('TenChu') or '').casefold()

EDIT_FIELDS=('owner_override','address_override','land_override')
def source_key(path,digest):
    from pathlib import Path
    return str(Path(path).resolve()).casefold()+'|'+digest

def read_edits(document,source):
    if document.get('version')!=2:return {}  # Legacy data stays on disk for manual reconciliation.
    return document.get('sources',{}).get(source,{})

def merge_edits(document,source,parcels):
    result={'version':2,'sources':dict(document.get('sources',{}))} if document.get('version')==2 else {'version':2,'sources':{},'legacy_unassigned':document}
    saved=dict(result['sources'].get(source,{}))
    for p in parcels:
        values={k:p[k] for k in EDIT_FIELDS if k in p}
        if values:saved[p['key']]=values
    result['sources'][source]=saved
    return result
