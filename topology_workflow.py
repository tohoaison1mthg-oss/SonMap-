"""Windows I/O coordinator with checked snapshots and recoverable direct updates."""
import hashlib
import copy
import json
import os
import shutil
import subprocess
import uuid
import tempfile
import math
import time
from pathlib import Path

from topology import build, export_rows, save_project, levels, finite

ROOT = Path(__file__).resolve().parent


def database_value_equal(wanted, actual):
    if wanted == actual or (wanted in ('', None) and actual in ('', None)):
        return True
    # Jet/Windows PowerShell JSON can round a Double by one or two ULPs.
    # Keep IDs/text/binary geometry exact; never compare using displayed 0.1 m².
    if isinstance(wanted, float) and isinstance(actual, (int, float)) and not isinstance(actual, bool):
        return math.isfinite(wanted) and math.isfinite(actual) and abs(wanted-actual) <= 8*max(math.ulp(wanted), math.ulp(float(actual)))
    return False


def display_levels(source, selected, restore=False):
    """Change view display only; preserve the exact prior per-view level states."""
    source=str(Path(source).resolve());selected=levels(selected)
    folder=ROOT/'data'/'view-states';folder.mkdir(parents=True,exist_ok=True)
    state=folder/(hashlib.sha256(source.casefold().encode()).hexdigest()+'.json')
    if restore and not state.is_file():raise ValueError('Chưa có trạng thái lớp đã lưu cho bản vẽ này.')
    from cad_bridge import request
    request('restore' if restore else 'hide',source,levels=selected,state=str(state))
    if restore:state.unlink()
    return str(state)


def check_database_replaceable(path):
    """Check Windows sharing/permissions without renaming or changing the MDB."""
    if os.name != 'nt':return
    import ctypes
    from ctypes import wintypes
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    create=kernel.CreateFileW
    create.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,
                     wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
    create.restype=wintypes.HANDLE
    close=kernel.CloseHandle;close.argtypes=[wintypes.HANDLE];close.restype=wintypes.BOOL
    # DELETE access tests the same sharing requirement as replacing the file.
    handle=create(str(Path(path).resolve()),0x10000,7,None,3,0,None)
    if handle==ctypes.c_void_p(-1).value:
        error=ctypes.get_last_error()
        if error in (32,33):
            raise RuntimeError('MDB đang bị khóa. Ngắt kết nối MDB trong phần mềm đang dùng rồi thử lại. '
                               'Chưa ghi thay đổi DGN/MDB.\n'+str(path))
        raise ctypes.WinError(error)
    close(handle)


def replace_database(staged, target):
    """Install through a sibling file: os.replace cannot cross C:/D: volumes."""
    target=Path(target)
    descriptor,name=tempfile.mkstemp(prefix='.sonmap-pending-',suffix='.mdb',dir=target.parent)
    os.close(descriptor)
    sibling=Path(name)
    try:
        shutil.copyfile(staged,sibling)
        if digest(sibling)!=digest(staged):raise RuntimeError('MDB tạm sao chép không khớp; chưa thay tệp.')
        os.replace(sibling,target)
    finally:
        if sibling.exists():sibling.unlink()


def issue_point(project, issue):
    if issue.get('point') is not None:return list(issue['point'])
    if issue.get('points'):return list(issue['points'][0])
    if issue.get('parcel'):
        return next((list(p['centre']) for p in project['parcels'] if p['ID']==issue['parcel']),None)
    return None


def clear_error_markers(source, project=None, issue=None):
    """Remove only named SonMap error cells, even after manual drawing edits."""
    source=Path(source).resolve()
    if project and Path(project['source']['path']).resolve()!=source:
        raise ValueError('Bản vẽ đã đổi; chưa xóa dấu lỗi.')
    point=issue_point(project,issue) if issue is not None else None
    if issue is not None and point is None:raise ValueError('Lỗi này chưa có tọa độ vòng báo lỗi.')
    # Save manual corrections before taking the recovery snapshot.
    with tempfile.TemporaryDirectory(prefix='sonmap-clear-') as directory:
        folder=Path(directory)
        context=['-ModelName',project['model']] if project and project.get('model') else []
        powershell('dgn_topology.ps1','-Action','SaveActive','-InputPath',source,
                   '-SourcePath',source,'-OutputPath',folder/'unused.dgn','-SkipSaveBackup',*context)
        original=digest(source);backup=folder/source.name
        shutil.copyfile(source,backup)
        if digest(backup)!=original:raise RuntimeError('DGN đổi khi sao chép; chưa xóa dấu lỗi.')
        plan=folder/'clear.json'
        save_project(plan,{'source':{'path':str(source),'sha256':original},
                           'working_dgn':str(source),'direct_backup':str(backup),
                           'model':project.get('model') if project else None,'marker_point':point})
        try:
            return powershell('dgn_topology.ps1','-Action','ClearErrors','-InputPath',plan,'-OutputPath',source)
        except Exception as exc:
            # Keep rescue data only if the source could not be restored.
            if digest(source)!=original:
                rescue=Path(tempfile.mkdtemp(prefix='sonmap-rescue-'))/source.name
                shutil.copyfile(backup,rescue)
                raise RuntimeError(str(exc)+'\nTệp khôi phục: '+str(rescue)) from exc
            raise


def focus_geometry(source, points, model=None, minimum=2):
    if not points:raise ValueError('Lỗi này chưa có tọa độ để tìm trên DGN.')
    xs=[float(p[0]) for p in points];ys=[float(p[1]) for p in points]
    if not all(math.isfinite(v) for v in xs+ys):raise ValueError('Tọa độ không hợp lệ.')
    from cad_bridge import request
    return request('focus',source,model=model,x=(min(xs)+max(xs))/2,y=(min(ys)+max(ys))/2,
                   span=max(max(xs)-min(xs),max(ys)-min(ys),minimum)*1.5)


def focus_parcel(selection):
    from app import geometry
    return focus_geometry(selection['source'],geometry(selection['row']['Geometry']),selection.get('model'))


def validate_parcel_context(selection):
    with tempfile.TemporaryDirectory(prefix='sonmap-context-') as directory:
        plan=Path(directory)/'context.json'
        plan.write_text(json.dumps({'source':str(Path(selection['source']).resolve()),'model':selection.get('model')}),encoding='utf-8')
        return powershell('dgn_view.ps1','-Action','Check','-PlanPath',plan)


def focus_issue(project, issue, zoom=1):
    zoom=finite(zoom,'Tỷ lệ phóng',True)
    points=[issue['point']] if issue.get('point') is not None else issue.get('points',[])
    if not points and issue.get('parcel'):
        points=next((p['points'] for p in project['parcels'] if p['ID']==issue['parcel']),[])
    scale=float(project['options']['metres_per_unit'])
    if not points:raise ValueError('Lỗi này chưa có tọa độ để tìm trên DGN.')
    # Scale the viewport around the same error; do not change DGN coordinates.
    xs=[p[0] for p in points];ys=[p[1] for p in points]
    centre=[(min(xs)+max(xs))/2,(min(ys)+max(ys))/2]
    span=max(max(xs)-min(xs),max(ys)-min(ys),2/scale)*zoom
    return focus_geometry(project['source']['path'],[centre],project.get('model'),span)


def mark_errors(project_path):
    project_path=Path(project_path);project=json.loads(project_path.read_text(encoding='utf-8'))
    source=Path(project['source']['path'])
    if digest(source)!=project['source']['sha256']:raise ValueError('DGN đã đổi; kiểm tra lại trước khi ghi dấu lỗi.')
    folder=Path(tempfile.mkdtemp(prefix='sonmap-markers-'))
    backup=folder/source.name;shutil.copyfile(source,backup)
    if digest(backup)!=project['source']['sha256']:raise ValueError('Sao lưu DGN không khớp.')
    project['direct_backup']=str(backup);plan=folder/'markers.json';save_project(plan,project)
    powershell('dgn_topology.ps1','-Action','ApplyPreview','-InputPath',plan,'-OutputPath',source)
    project['source']['sha256']=digest(source)
    if Path(project['working_dgn']).resolve()!=source.resolve():shutil.copyfile(source,project['working_dgn'])
    project['working_sha256']=project['source']['sha256']
    project.pop('direct_backup',None)
    save_project(project_path,project)
    shutil.rmtree(folder)
    return None


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def powershell(script, *arguments):
    if os.name != 'nt':
        raise RuntimeError('Đọc/ghi DGN và tạo MDB cần Windows có MicroStation V8i và Jet 32-bit.')
    from cad_worker import worker
    ok,raw=worker.run(script,arguments)
    if not ok:
        log=ROOT/'data'/'dgn-topology-last.log'
        log.parent.mkdir(exist_ok=True)
        log.write_text(raw,encoding='utf-8')
        for line in reversed(raw.splitlines()):
            try:
                error=json.loads(line)
            except (ValueError,TypeError):
                continue
            if isinstance(error,dict) and 'stage' in error:
                raise RuntimeError(f"V8i không thực hiện được bước: {error['stage']}\n{error.get('message','')}\nChi tiết: {log}")
        raise RuntimeError(f'{raw.strip()}\nChi tiết: {log}')
    return raw


def validate_options(options):
    levels(options['boundary_levels'])
    centre = levels(options.get('centre_level', '11'))
    if len(centre) != 1 or centre[0] in levels(options['boundary_levels']):
        raise ValueError('Lớp tâm thửa phải là một lớp riêng, khác lớp ranh.')
    if not 0 <= int(options.get('centre_color', 3)) <= 255:
        raise ValueError('Màu tâm từ 0 đến 255.')
    finite(options.get('centre_height', 1), 'Cỡ chữ tâm', True)
    finite(options.get('chord_tolerance', .001), 'Sai số dây cung', True)
    error = levels(options.get('error_level', '60'))
    if len(error)!=1 or error[0] in levels(options['boundary_levels']) or error == centre:
        raise ValueError('Lớp báo lỗi phải khác lớp ranh và lớp tâm.')
    if not 0 <= int(options.get('error_color',3)) <= 255:
        raise ValueError('Màu lỗi từ 0 đến 255.')
    finite(options.get('error_radius',.01),'Bán kính báo lỗi',True)
    for value in options.get('label_levels', {}).values():
        if str(value).strip():
            if centre[0] in levels(value) or error[0] in levels(value):
                raise ValueError('Lớp tâm và báo lỗi phải khác các lớp nhãn cần gán.')


def prepare(source, options):
    started=time.perf_counter()
    validate_options(options)
    from topology import _engine
    _engine()  # Fail before creating outputs when the optional dependency is missing.
    source = Path(source).resolve()
    if source.suffix.lower() != '.dgn' or not source.is_file():
        raise ValueError('Chọn tệp .dgn tồn tại và mở đúng tệp đó trong V8i.')
    if os.name != 'nt':
        raise RuntimeError('Chuẩn bị bản vẽ cần Windows + MicroStation V8i.')
    folder = ROOT / 'data' / 'topology-jobs' / uuid.uuid4().hex
    folder.mkdir(parents=True)
    if options.get('auto_hide',True):
        visible=set(levels(options['boundary_levels']))
        for spec in options.get('label_levels',{}).values():
            if str(spec).strip():visible.update(levels(spec))
        display_levels(source,','.join(map(str,sorted(visible))))
    if options.get('in_place'):
        from cad_bridge import request
        request('save',source)
    original = digest(source)
    working = source if options.get('in_place') else folder / source.name
    if working != source:shutil.copyfile(source, working)
    if digest(source) != original or digest(working) != original:
        raise RuntimeError('DGN thay đổi trong khi sao chép. Lưu bản vẽ và thử lại.')
    args = ['-Action', 'Extract', '-InputPath', working, '-OutputPath', folder / 'snapshot.json', '-SourcePath', source,
            '-ChordTolerance', float(options['chord_tolerance']) / float(options['metres_per_unit']),
            '-BoundaryLevels', options['boundary_levels'],
            '-TextLevels', ','.join(str(n) for n in sorted({n for spec in options.get('label_levels',{}).values() if str(spec).strip() for n in levels(spec)})) or 'none']
    if options.get('break_arcs'):
        args.append('-BreakArcs')
    if not options.get('break_complex',True):
        args.append('-KeepComplex')
    if options.get('in_place'):
        from cad_bridge import request
        snapshot=json.loads(request('extract',source,levels=levels(options['boundary_levels']),
                          text_levels=levels(args[args.index('-TextLevels')+1]) if args[args.index('-TextLevels')+1]!='none' else [],
                          arcs=bool(options.get('break_arcs')),keep_complex=not options.get('break_complex',True),
                          tolerance=float(options['chord_tolerance'])/float(options['metres_per_unit'])))
        (folder/'snapshot.json').write_text(json.dumps(snapshot,ensure_ascii=False),encoding='utf-8')
    else:powershell('dgn_topology.ps1', *args)
    scanned=time.perf_counter()
    if digest(source)!=original:raise RuntimeError('DGN thay đổi trong khi quét; hãy chạy lại trên bản vẽ đã lưu.')
    snapshot = json.loads((folder / 'snapshot.json').read_text(encoding='utf-8-sig'))
    snapshot['text_levels']=args[args.index('-TextLevels')+1]
    (folder/'snapshot.json').write_text(json.dumps(snapshot,ensure_ascii=False),encoding='utf-8')
    snapshot['source'] = {'path': str(source), 'sha256': original}
    project = build(snapshot, options)
    project.update(working_dgn=str(working), working_sha256=original,
                   references_excluded=snapshot.get('references_excluded', 0), status='review',
                   timing={'scan_seconds':scanned-started,'build_seconds':time.perf_counter()-scanned})
    save_project(folder / 'project.json', project)
    return folder / 'project.json', project


def preview_project(project_path):
    project_path = Path(project_path)
    project = json.loads(project_path.read_text(encoding='utf-8'))
    validate_options(project['options'])
    if digest(project['working_dgn']) != project['working_sha256']:
        raise ValueError('Bản sao DGN đã đổi; phân tích lại trước khi ghi báo lỗi.')
    path=project_path.parent / ('errors_' + uuid.uuid4().hex[:8] + '.dgn')
    powershell('dgn_topology.ps1','-Action','WritePreview','-InputPath',project_path,'-OutputPath',path)
    return path


def export_project(project_path):
    project_path = Path(project_path)
    project = json.loads(project_path.read_text(encoding='utf-8'))
    validate_options(project['options'])
    rows = export_rows(project)
    source = Path(project['source']['path'])
    if digest(source) != project['source']['sha256'] or digest(project['working_dgn']) != project['working_sha256']:
        raise ValueError('Nguồn hoặc bản sao đã đổi; hãy phân tích lại, không xuất từ dự án cũ.')
    folder = project_path.parent / ('result_' + uuid.uuid4().hex[:8])
    folder.mkdir()
    dgn, mdb = folder / source.name, folder / source.with_suffix('.mdb').name
    rows_path = folder / 'rows.json'
    rows_path.write_text(json.dumps(rows, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    powershell('dgn_topology.ps1', '-Action', 'WriteMdb', '-InputPath', rows_path, '-OutputPath', mdb)
    # Verify every field including geometry using the existing read-only MDB reader.
    roundtrip = folder / 'mdb-check.json'
    powershell('read_mdb.ps1', '-MdbPath', mdb, '-JsonPath', roundtrip)
    actual = json.loads(roundtrip.read_text(encoding='utf-8-sig'))
    if isinstance(actual, dict):
        actual = [actual]
    if len(actual) != len(rows):
        raise RuntimeError('Kiểm tra MDB: sai số lượng bản ghi.')
    from app import geometry
    for wanted, found in zip(sorted(rows, key=lambda p: (p['ToBD'], p['TCT'], p['ID'])), actual):
        for key, value in wanted.items():
            if key == 'Geometry':
                if geometry(value) != geometry(found[key]):
                    raise RuntimeError('MDB đọc lại không khớp hình học.')
            elif found[key] != value and not (value == '' and found[key] is None):
                raise RuntimeError(f'MDB đọc lại không khớp trường {key}.')
    powershell('dgn_topology.ps1', '-Action', 'WriteDrawing', '-InputPath', project_path, '-OutputPath', dgn)
    # Re-extract and polygonize the saved DGN: a save/COM success alone is insufficient.
    snapshot_path = folder / 'dgn-check.json'
    check_args=['-Action','Extract','-InputPath',dgn,'-OutputPath',snapshot_path,'-ModelName',project['model']]
    if project.get('model_is_default'):check_args.append('-DefaultModel')
    powershell('dgn_topology.ps1',*check_args)
    snapshot = json.loads(snapshot_path.read_text(encoding='utf-8-sig'))
    check = build(snapshot, {**project['options'], 'snap': False, 'label_levels': {}})
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    original_polygons = [Polygon(p['points']) for p in project['parcels']]
    saved_polygons = [Polygon(p['points']) for p in check['parcels']]
    if len(original_polygons) != len(saved_polygons) or not unary_union(original_polygons).equals(unary_union(saved_polygons)):
        raise RuntimeError('DGN đọc lại không khớp vùng thửa dự kiến.')
    # Individual faces must match too: equal union alone can hide a missing shared boundary.
    if any(not any(a.equals(b) for b in saved_polygons) for a in original_polygons):
        raise RuntimeError('DGN đọc lại không khớp ranh chung.')
    centres = [t for t in snapshot['texts'] if int(t['level']) == int(project['options']['centre_level'])]
    for p in project['parcels']:
        if not any(t['text'] == str(p['TCT']) and sum((a-b)**2 for a,b in zip(t['point'], p['centre'])) < 1e-12 for t in centres):
            raise RuntimeError('Không xác minh được tâm/số thửa trong DGN đã lưu.')
    if digest(source) != project['source']['sha256']:
        raise RuntimeError('DGN nguồn đã thay đổi trong quá trình xuất.')
    receipt = {'status': 'verified', 'dgn': str(dgn), 'mdb': str(mdb), 'parcels': len(rows), 'source_unchanged': True}
    (folder / 'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
    return receipt


def inspect_database(path):
    """Read an MDB with the existing schema reader, without touching application state."""
    path=Path(path).resolve()
    if path.suffix.lower()!='.mdb' or not path.is_file():
        raise ValueError('Chọn tệp MDB tồn tại.')
    original=digest(path)
    with tempfile.TemporaryDirectory(prefix='sonmap-mdb-') as directory:
        target=Path(directory)/'rows.json'
        snapshot=Path(directory)/'source.mdb'
        schema_path=Path(directory)/'schema.json'
        shutil.copyfile(path,snapshot)
        if digest(snapshot)!=original or digest(path)!=original:raise RuntimeError('MDB thay đổi trong lúc sao chép. Hãy lưu và kết nối lại.')
        powershell('read_mdb.ps1','-MdbPath',snapshot,'-JsonPath',target,'-SchemaPath',schema_path)
        rows=json.loads(target.read_text(encoding='utf-8-sig'))
        columns=json.loads(schema_path.read_text(encoding='utf-8-sig')) if schema_path.exists() else []
    if isinstance(rows,dict):rows=[rows]
    if not isinstance(rows,list):raise ValueError('MDB trả dữ liệu không hợp lệ.')
    if digest(path)!=original:raise RuntimeError('MDB đã thay đổi khi đọc. Kết nối lại sau khi lưu dữ liệu.')
    return {'path':str(path),'rows':rows,'count':len(rows),'sha256':original,'columns':columns}


def create_database(path):
    """Create an empty SonMap schema; never truncate an existing database."""
    path=Path(path).resolve()
    if path.suffix.lower()!='.mdb':raise ValueError('Tên CSDL phải có phần mở rộng .mdb.')
    if path.exists():raise ValueError('Tệp MDB đã tồn tại. Chọn tên mới để giữ nguyên CSDL cũ.')
    with tempfile.TemporaryDirectory(prefix='sonmap-mdb-') as directory:
        rows_path=Path(directory)/'empty.json';rows_path.write_text('[]',encoding='utf-8')
        powershell('dgn_topology.ps1','-Action','WriteMdb','-InputPath',rows_path,'-OutputPath',path,'-AllowEmpty')
    result=inspect_database(path)
    if result['count']!=0:raise RuntimeError('CSDL vừa tạo không trống như dự kiến.')
    return result


def drawing_project(project_path, topology=False):
    """Save cleaned linework (and optional provisional centres) before attributes/MDB."""
    project_path=Path(project_path)
    project=json.loads(project_path.read_text(encoding='utf-8'))
    validate_options(project['options'])
    from topology import BLOCKING
    forbidden=BLOCKING if topology else {'UNSUPPORTED'}
    if any(i['code'] in forbidden for i in project['issues']):
        raise ValueError('Còn lỗi ranh cần xử lý. Mở Báo lỗi hoặc ghi cell lỗi để kiểm tra.')
    if digest(project['working_dgn'])!=project['working_sha256'] or digest(project['source']['path'])!=project['source']['sha256']:
        raise ValueError('Bản vẽ đã thay đổi; cần phân tích lại.')
    kind='topology' if topology else 'cleaned'
    path=project_path.parent/(kind+'_'+uuid.uuid4().hex[:8]+'.dgn')
    powershell('dgn_topology.ps1','-Action','TopologyDrawing' if topology else 'CleanDrawing','-InputPath',project_path,'-OutputPath',path)
    return str(path)


def assign_labels(project_path, label_levels):
    """Reassign labels on the saved snapshot, preserving explicitly edited attributes."""
    project_path=Path(project_path)
    old=json.loads(project_path.read_text(encoding='utf-8'))
    if digest(old['working_dgn'])!=old['working_sha256']:
        raise ValueError('Bản sao DGN đã thay đổi; phân tích lại trước khi gán nhãn.')
    snapshot=json.loads((project_path.parent/'snapshot.json').read_text(encoding='utf-8-sig'))
    requested={n for spec in label_levels.values() if str(spec).strip() for n in levels(spec)}
    scanned=snapshot.get('text_levels','*')
    if scanned!='*' and not requested.issubset(set() if scanned=='none' else set(levels(scanned))):
        target=project_path.parent/('labels-'+uuid.uuid4().hex+'.json')
        args=['-Action','Extract','-InputPath',old['working_dgn'],'-OutputPath',target,
              '-ModelName',old['model'],'-BoundaryLevels',old['options']['boundary_levels'],
              '-TextLevels',','.join(map(str,sorted(requested))) or 'none']
        if old.get('model_is_default'):args.append('-DefaultModel')
        powershell('dgn_topology.ps1',*args)
        snapshot=json.loads(target.read_text(encoding='utf-8-sig'))
    snapshot['source']=old['source']
    options={**old['options'],'label_levels':label_levels}
    validate_options(options)
    new=build(snapshot,options)
    from shapely.geometry import Polygon
    if len(new['parcels'])!=len(old['parcels']):raise ValueError('Số vùng thay đổi; cần phân tích lại.')
    for before,after in zip(old['parcels'],new['parcels']):
        if not Polygon(before['points']).equals(Polygon(after['points'])):
            raise ValueError('Ranh thay đổi; cần phân tích lại.')
        after['ID']=before['ID']
        for key in ('ToBD','TCT','TenChu','DiaChi','DiaChiThuaDatChiTiet','Xudong','LRD','MaLD'):
            if key in before.get('manual_fields',[]) or not label_levels.get(key):after[key]=before.get(key)
        after['manual_fields']=before.get('manual_fields',[])
        after['MaLD']=after.get('LRD','')
    for key in ('working_dgn','working_sha256','references_excluded','status'):new[key]=old.get(key)
    for issue in new['issues']:
        if issue.get('parcel'):
            p=new['parcels'][issue['parcel']-1]
            issue['parcel']=p['ID']
            if issue.get('field') in p.get('manual_fields',[]) and p.get(issue['field']):issue['resolved_by_manual_edit']=True
    save_project(project_path,new)
    return new


def apply_current(project_path, database_path=None,clean_only=False,keep_backup=False):
    """Update active DGN/MDB with temporary recovery data and checked readback."""
    from database_topology import reconcile
    project_path=Path(project_path)
    original_project=json.loads(project_path.read_text(encoding='utf-8'))
    project=copy.deepcopy(original_project)
    source=Path(project['source']['path'])
    if digest(source)!=project['source']['sha256']:
        raise ValueError('DGN đã đổi từ lúc phân tích. Thực hiện topology lại trước khi cập nhật.')
    backup=source.parent/'SonMap_backups'/uuid.uuid4().hex if keep_backup else Path(tempfile.mkdtemp(prefix='sonmap-transaction-'))
    backup.mkdir(parents=True,exist_ok=True)
    dgn_backup=backup/source.name
    shutil.copyfile(source,dgn_backup)
    if digest(dgn_backup)!=project['source']['sha256']:raise RuntimeError('Bản sao lưu DGN không khớp nguồn.')
    delta=None;target=None;staged=None;db_backup=None;db_before=None;db_applied=False;dgn_applied=False;dgn_attempted=False;new_db_digest=None
    try:
        if database_path:
            target=Path(database_path).resolve()
            if target.suffix.lower()!='.mdb':raise ValueError('CSDL cần có phần mở rộng .mdb.')
            old=inspect_database(target);db_before=old['sha256']
            db_backup=backup/target.name
            if db_backup==dgn_backup:raise ValueError('Tên sao lưu DGN/MDB không hợp lệ.')
            shutil.copyfile(target,db_backup)
            if digest(db_backup)!=db_before:raise RuntimeError('MDB thay đổi khi sao lưu; không cập nhật.')
            delta=reconcile(project,old['rows']);project=delta['project']
            changes=any(delta[key] for key in ('delete_ids','insert_rows','update_rows'))
            if changes:
                check_database_replaceable(target)
                staged=backup/('pending-'+uuid.uuid4().hex+'.mdb')
                shutil.copyfile(db_backup,staged)
                plan=backup/'mdb-plan.json'
                plan.write_text(json.dumps({k:delta[k] for k in ('delete_ids','insert_rows','update_rows')},ensure_ascii=False),encoding='utf-8')
                powershell('update_mdb_topology.ps1','-PlanPath',plan,'-MdbPath',staged)
                actual=inspect_database(staged)
            else:
                # Verified source rows already equal the plan; no Jet staging/readback needed.
                actual=old
            wanted={int(r['ID']):r for r in delta['final_rows']}
            found={int(r['ID']):r for r in actual['rows']}
            if set(wanted)!=set(found):raise RuntimeError('MDB tạm đọc lại không khớp danh sách ID dự kiến.')
            for rid,row in wanted.items():
                for key,value in row.items():
                    if key not in found[rid]:continue
                    other=found[rid][key]
                    if not database_value_equal(value,other):
                        raise RuntimeError(f'MDB tạm không khớp trường {key} của ID {rid}.')
        # Geometry must remain exportable, but new parcels may wait for official numbering.
        if clean_only:
            if any(i['code']=='UNSUPPORTED' for i in project['issues']):raise ValueError('Còn phần tử ranh chưa hỗ trợ; không ghi đè.')
        else:export_rows(project,allow_unnumbered=True,allow_zero_id=bool(delta),allow_duplicate_numbers=bool(delta))
        project['direct_backup']=str(dgn_backup)
        save_project(project_path,project)
        if target and digest(target)!=db_before:raise ValueError('MDB đang bị thay đổi bởi chương trình khác. Chưa ghi thay đổi.')
        dgn_attempted=True
        write_started=time.perf_counter()
        if clean_only and not target and not project.get('scope_rings'):
            from cad_bridge import request
            request('clean',source,model=project['model'],project=project)
        else:powershell('dgn_topology.ps1','-Action','ApplyClean' if clean_only else 'ApplyDrawing','-InputPath',project_path,'-OutputPath',source)
        write_seconds=time.perf_counter()-write_started
        dgn_applied=True
        if target:
            if digest(target)!=db_before:raise ValueError('MDB thay đổi trong khi cập nhật DGN; cần kết nối lại.')
            if changes:
                new_db_digest=digest(staged)
                try:replace_database(staged,target)
                except OSError as exc:
                    if getattr(exc,'winerror',None) in (32,33) or isinstance(exc,PermissionError):
                        raise RuntimeError('Không thay được MDB bị khóa hoặc thiếu quyền ghi. Ngắt kết nối MDB trong phần mềm khác rồi thử lại.') from exc
                    raise RuntimeError('Không thay được MDB: '+str(exc)) from exc
                db_applied=True
            connected=inspect_database(target) if changes else old
        else:connected=None
        project['source']['sha256']=digest(source)
        # Refresh the analysis copy so a subsequent explicit operation does not use stale geometry.
        if Path(project['working_dgn']).resolve()!=source.resolve():shutil.copyfile(source,project['working_dgn'])
        project['working_sha256']=project['source']['sha256']
        project.pop('direct_backup',None)
        save_project(project_path,project)
        receipt={'status':'updated_current','dgn':str(source),'mdb':str(target) if target else None,
                 'backup':str(backup) if keep_backup else None,'project':project,'connected':connected,
                 'before_count':delta['before_count'] if delta else None,
                 'after_count':delta['after_count'] if delta else None,
                 'splits':delta['splits'] if delta else [],'unnumbered':delta['unnumbered'] if delta else 0,
                 'write_seconds':write_seconds}
        (backup/'receipt.json').write_text(json.dumps({k:v for k,v in receipt.items() if k not in ('project','connected')},ensure_ascii=False,indent=2),encoding='utf-8')
        if not keep_backup:shutil.rmtree(backup)
        return receipt
    except Exception as exc:
        failures=[]
        if getattr(exc,'rescue_required',False):failures.append('V8i chưa tự khôi phục được; giữ tệp cứu hộ.')
        if db_applied and target and db_backup:
            try:
                if digest(target)!=new_db_digest:raise RuntimeError('MDB đã được tiến trình khác sửa sau khi ghi; không ghi đè dữ liệu mới của tiến trình đó.')
                replace_database(db_backup,target)
            except Exception as rollback:failures.append('Không tự khôi phục MDB: '+str(rollback))
        if dgn_applied or (dgn_attempted and digest(source)!=original_project['source']['sha256']):
            try:powershell('dgn_topology.ps1','-Action','RestoreActive','-InputPath',dgn_backup,'-OutputPath',source)
            except Exception as rollback:failures.append('Không tự khôi phục DGN: '+str(rollback))
        save_project(project_path,original_project)
        if not keep_backup and not failures:shutil.rmtree(backup)
        recovery='\nTệp khôi phục: '+str(backup) if keep_backup or failures else ''
        raise RuntimeError(str(exc)+recovery+ ('\n'+'\n'.join(failures) if failures else '')) from exc
