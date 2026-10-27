"""Pick a parcel by an interior DGN point; update owner fields in its actual MDB."""
import json
import math
import shutil
import tempfile
import uuid
import os
from pathlib import Path
from shapely.geometry import Point, Polygon
from topology_workflow import inspect_database, powershell, digest

KEEP_NUMBER=object()

# Physical area and record/geometry identity are deliberately read-only.
READ_ONLY={'ID','Geometry','DienTich'}
INTEGER_TYPES={'System.Int16':(-32768,32767),'System.Int32':(-2147483648,2147483647),
               'System.Int64':(-9223372036854775808,9223372036854775807),'System.Byte':(0,255)}


def editable_columns(connected):
    return [c for c in connected.get('columns',[]) if c['name'] not in READ_ONLY and
            c['type'] in {'System.String','System.Double','System.Single','System.Decimal','System.Boolean',*INTEGER_TYPES}]


def attribute_values(connected, changes):
    columns={c['name']:c for c in editable_columns(connected)}
    result={}
    if not changes:raise ValueError('Chọn ít nhất một thuộc tính cần lưu.')
    for name,value in changes.items():
        if name not in columns:raise ValueError('Thuộc tính không cho phép sửa: '+name)
        column=columns[name];kind=column['type']
        if value is None or value=='':
            if kind=='System.String':value=''
            elif column.get('nullable',True):value=None
            else:raise ValueError(name+': không được để trống.')
        if value is not None:
            if kind=='System.String':
                if not isinstance(value,str) or '\x00' in value or len(value)>column.get('size',255):
                    raise ValueError(name+': nội dung quá dài hoặc có ký tự không hợp lệ.')
            elif name=='TCT':value=parcel_number(value)
            elif name=='ToBD':
                value=parcel_number(value)
                if value is None:raise ValueError('Tờ bản đồ phải lớn hơn 0.')
            elif kind in INTEGER_TYPES:
                text=str(value).strip()
                if not text.lstrip('-').isascii() or not text.lstrip('-').isdigit():raise ValueError(name+': cần số nguyên.')
                value=int(text);low,high=INTEGER_TYPES[kind]
                if not low<=value<=high:raise ValueError(name+': vượt giới hạn số nguyên.')
            elif kind=='System.Boolean':
                if str(value).lower() not in ('true','false','0','1'):raise ValueError(name+': nhập true/false hoặc 1/0.')
                value=str(value).lower() in ('true','1')
            else:
                # Accept the Vietnamese decimal comma without accepting grouping separators.
                text=str(value).strip()
                if ',' in text and '.' in text:raise ValueError(name+': chỉ dùng một dấu thập phân.')
                value=float(text.replace(',','.'))
                if not math.isfinite(value):raise ValueError(name+': cần số hữu hạn.')
        if name=='ToBD' and value is None:raise ValueError('Tờ bản đồ phải lớn hơn 0.')
        result[name]=value
    return result


def update_attributes(mdb, expected_hash, record_id, changes):
    """Stage an exact selected-field delta, verify all rows, then replace the unlocked MDB."""
    target=Path(mdb).resolve();before=inspect_database(target)
    if before['sha256']!=expected_hash:raise ValueError('MDB đã đổi. Pick lại thửa trước khi lưu.')
    rows=before['rows']
    if isinstance(record_id,bool) or sum(r['ID']==record_id for r in rows)!=1:raise ValueError('ID thửa không duy nhất.')
    values=attribute_values(before,changes)
    current=next(r for r in rows if r['ID']==record_id)
    values={k:v for k,v in values.items() if current.get(k)!=v}
    if not values:return {'connected':before,'backup':'','status':'unchanged'}
    backup=target.parent/'SonMap_backups'/('attributes-'+uuid.uuid4().hex);backup.mkdir(parents=True)
    saved=backup/target.name;shutil.copyfile(target,saved)
    if digest(saved)!=expected_hash or digest(target)!=expected_hash:raise ValueError('MDB thay đổi khi sao lưu; chưa ghi.')
    staged=backup/('pending-'+target.name);shutil.copyfile(saved,staged)
    plan=backup/'plan.json'
    plan.write_text(json.dumps({'sha256':expected_hash,'ID':record_id,'changes':values},ensure_ascii=False),encoding='utf-8')
    try:
        powershell('update_parcel_attributes.ps1','-MdbPath',staged,'-PlanPath',plan)
        checked=inspect_database(staged)
        wanted=[dict(r,**values) if r['ID']==record_id else r for r in rows]
        if sorted(checked['rows'],key=lambda r:r['ID'])!=sorted(wanted,key=lambda r:r['ID']):
            raise RuntimeError('MDB tạm đọc lại không khớp; chưa thay MDB gốc.')
        if digest(target)!=expected_hash:raise ValueError('MDB đã đổi trong lúc sửa; chưa thay tệp.')
        os.replace(staged,target)
        connected=inspect_database(target)
        if connected['rows']!=checked['rows']:raise RuntimeError('MDB thay đổi sau khi ghi; xem sao lưu và kết nối lại.')
    except Exception as exc:raise RuntimeError(str(exc)+'\nSao lưu: '+str(backup)) from exc
    receipt={'ID':record_id,'fields':list(values),'backup':str(backup),'status':'attributes_updated'}
    (backup/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    return {**receipt,'connected':connected}


def parcel_number(value):
    if value is None or isinstance(value,str) and not value.strip():return None
    text=str(value).strip()
    if not text.isascii() or not text.isdigit() or not 1<=int(text)<=2147483647:
        raise ValueError('Số thửa phải là số nguyên dương; có thể để trống nếu chưa có số.')
    return int(text)


def locate_parcel(rows, point):
    from app import geometry
    if len(point)!=2 or not all(math.isfinite(float(v)) for v in point):raise ValueError('Điểm chọn không hợp lệ.')
    p=Point(point);inside=[];boundary=False
    for row in rows:
        try:polygon=Polygon(geometry(row['Geometry']))
        except ValueError:continue
        if not polygon.is_valid:continue
        if polygon.boundary.distance(p)<=1e-7:boundary=True
        if polygon.contains(p):inside.append(row)
    if boundary:raise ValueError('Điểm nằm trên ranh thửa. Chọn một điểm bên trong thửa.')
    if len(inside)>1:raise ValueError('Điểm nằm trong nhiều thửa MDB chồng lấn; chưa chọn thửa để tránh cập nhật nhầm.')
    if not inside:raise ValueError('Không tìm thấy thửa MDB tại điểm này. Kiểm tra kết nối MDB hoặc tạo topology trước.')
    if sum(r['ID']==inside[0]['ID'] for r in rows)!=1:raise ValueError('MDB có ID trùng; chưa cập nhật.')
    return dict(inside[0])


def pick_parcel(source, mdb):
    source=Path(source).resolve()
    connected=inspect_database(mdb)
    result=json.loads(powershell('pick_dgn_point.ps1','-SourcePath',source))
    if result.get('cancelled'):return None
    if digest(connected['path'])!=connected['sha256']:raise ValueError('MDB đã đổi trong lúc chọn. Chọn lại thửa để đọc thông tin mới.')
    return {'source':str(source),'model':result.get('model'),'connected':connected,'row':locate_parcel(connected['rows'],result['point'])}


def update_owner(mdb, expected_hash, record_id, owner, address, number=KEEP_NUMBER):
    target=Path(mdb).resolve()
    for value in (owner,address):
        if not isinstance(value,str) or len(value)>255 or '\x00' in value:raise ValueError('Tên và địa chỉ chủ sử dụng tối đa 255 ký tự, không chứa ký tự NUL.')
    before=inspect_database(target)
    if before['sha256']!=expected_hash:raise ValueError('MDB đã đổi. Đóng bảng và chọn lại thửa trước khi lưu.')
    if isinstance(record_id,bool) or sum(r['ID']==record_id for r in before['rows'])!=1:raise ValueError('Không xác định duy nhất được ID thửa.')
    current=next(r for r in before['rows'] if r['ID']==record_id)
    number=current.get('TCT') if number is KEEP_NUMBER else parcel_number(number)
    backup=target.parent/'SonMap_backups'/('owner-'+uuid.uuid4().hex)
    backup.mkdir(parents=True)
    shutil.copyfile(target,backup/target.name)
    if digest(backup/target.name)!=expected_hash or digest(target)!=expected_hash:raise ValueError('MDB thay đổi khi sao lưu; chưa ghi thông tin.')
    try:
        with tempfile.TemporaryDirectory(prefix='sonmap-owner-') as folder:
            plan=Path(folder)/'plan.json'
            plan.write_text(json.dumps({'sha256':expected_hash,'ID':record_id,'TCT':number,'TenChu':owner,'DiaChi':address},ensure_ascii=False),encoding='utf-8')
            powershell('update_parcel_owner.ps1','-MdbPath',target,'-PlanPath',plan)
        connected=inspect_database(target)
        row=next(r for r in connected['rows'] if r['ID']==record_id)
        if (row.get('TenChu') or '',row.get('DiaChi') or '')!=(owner,address):raise RuntimeError('MDB đọc lại không khớp thông tin vừa lưu.')
        if row.get('TCT')!=number:raise RuntimeError('MDB đọc lại không khớp số thửa vừa lưu.')
    except Exception as exc:raise RuntimeError(str(exc)+'\nSao lưu trước thay đổi: '+str(backup)) from exc
    receipt={'ID':record_id,'backup':str(backup),'mdb':str(target),'status':'owner_updated'}
    (backup/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    return {**receipt,'connected':connected}
