"""Pick a parcel by an interior DGN point; update owner fields in its actual MDB."""
import json
import math
import shutil
import tempfile
import uuid
from pathlib import Path
from shapely.geometry import Point, Polygon
from topology_workflow import inspect_database, powershell, digest


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
    return {'source':str(source),'connected':connected,'row':locate_parcel(connected['rows'],result['point'])}


def update_owner(mdb, expected_hash, record_id, owner, address):
    target=Path(mdb).resolve()
    for value in (owner,address):
        if not isinstance(value,str) or len(value)>255 or '\x00' in value:raise ValueError('Tên và địa chỉ chủ sử dụng tối đa 255 ký tự, không chứa ký tự NUL.')
    before=inspect_database(target)
    if before['sha256']!=expected_hash:raise ValueError('MDB đã đổi. Đóng bảng và chọn lại thửa trước khi lưu.')
    if isinstance(record_id,bool) or sum(r['ID']==record_id for r in before['rows'])!=1:raise ValueError('Không xác định duy nhất được ID thửa.')
    backup=target.parent/'SonMap_backups'/('owner-'+uuid.uuid4().hex)
    backup.mkdir(parents=True)
    shutil.copyfile(target,backup/target.name)
    if digest(backup/target.name)!=expected_hash or digest(target)!=expected_hash:raise ValueError('MDB thay đổi khi sao lưu; chưa ghi thông tin.')
    try:
        with tempfile.TemporaryDirectory(prefix='sonmap-owner-') as folder:
            plan=Path(folder)/'plan.json'
            plan.write_text(json.dumps({'sha256':expected_hash,'ID':record_id,'TenChu':owner,'DiaChi':address},ensure_ascii=False),encoding='utf-8')
            powershell('update_parcel_owner.ps1','-MdbPath',target,'-PlanPath',plan)
        connected=inspect_database(target)
        row=next(r for r in connected['rows'] if r['ID']==record_id)
        if (row.get('TenChu') or '',row.get('DiaChi') or '')!=(owner,address):raise RuntimeError('MDB đọc lại không khớp thông tin vừa lưu.')
    except Exception as exc:raise RuntimeError(str(exc)+'\nSao lưu trước thay đổi: '+str(backup)) from exc
    receipt={'ID':record_id,'backup':str(backup),'mdb':str(target),'status':'owner_updated'}
    (backup/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    return {**receipt,'connected':connected}
