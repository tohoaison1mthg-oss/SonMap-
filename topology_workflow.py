"""Windows-only I/O coordinator. Never modifies the original DGN or an existing MDB."""
import hashlib
import json
import os
import shutil
import subprocess
import uuid
import tempfile
from pathlib import Path

from topology import build, export_rows, save_project, levels, finite

ROOT = Path(__file__).resolve().parent


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def powershell(script, *arguments):
    if os.name != 'nt':
        raise RuntimeError('Đọc/ghi DGN và tạo MDB cần Windows có MicroStation V8i và Jet 32-bit.')
    executable = Path(os.environ.get('WINDIR', r'C:\Windows')) / 'SysWOW64/WindowsPowerShell/v1.0/powershell.exe'
    result = subprocess.run([str(executable), '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(ROOT / script), *map(str, arguments)], capture_output=True, timeout=300, creationflags=0x08000000)
    if result.returncode:
        raw=(result.stdout + result.stderr).decode('utf-8-sig', errors='replace')
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
    return result.stdout.decode('utf-8-sig').strip()


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
    validate_options(options)
    from topology import _engine
    _engine()  # Fail before creating outputs when the optional dependency is missing.
    source = Path(source).resolve()
    if source.suffix.lower() != '.dgn' or not source.is_file():
        raise ValueError('Chọn tệp .dgn tồn tại và mở đúng tệp đó trong V8i.')
    if os.name != 'nt':
        raise RuntimeError('Chuẩn bị bản vẽ cần Windows + MicroStation V8i.')
    folder = source.parent / (source.stem + '_SonMap_' + uuid.uuid4().hex[:10])
    folder.mkdir()
    original = digest(source)
    working = folder / source.name
    shutil.copyfile(source, working)
    if digest(source) != original or digest(working) != original:
        raise RuntimeError('DGN thay đổi trong khi sao chép. Lưu bản vẽ và thử lại.')
    args = ['-Action', 'Extract', '-InputPath', working, '-OutputPath', folder / 'snapshot.json', '-SourcePath', source,
            '-ChordTolerance', float(options['chord_tolerance']) / float(options['metres_per_unit'])]
    if options.get('break_arcs'):
        args.append('-BreakArcs')
    if not options.get('break_complex',True):
        args.append('-KeepComplex')
    powershell('dgn_topology.ps1', *args)
    snapshot = json.loads((folder / 'snapshot.json').read_text(encoding='utf-8-sig'))
    snapshot['source'] = {'path': str(source), 'sha256': original}
    project = build(snapshot, options)
    project.update(working_dgn=str(working), working_sha256=original,
                   references_excluded=snapshot.get('references_excluded', 0), status='review')
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
        shutil.copyfile(path,snapshot)
        if digest(snapshot)!=original or digest(path)!=original:raise RuntimeError('MDB thay đổi trong lúc sao chép. Hãy lưu và kết nối lại.')
        powershell('read_mdb.ps1','-MdbPath',snapshot,'-JsonPath',target)
        rows=json.loads(target.read_text(encoding='utf-8-sig'))
    if isinstance(rows,dict):rows=[rows]
    if not isinstance(rows,list):raise ValueError('MDB trả dữ liệu không hợp lệ.')
    if digest(path)!=original:raise RuntimeError('MDB đã thay đổi khi đọc. Kết nối lại sau khi lưu dữ liệu.')
    return {'path':str(path),'rows':rows,'count':len(rows),'sha256':original}


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
    snapshot['source']=old['source']
    options={**old['options'],'label_levels':label_levels}
    validate_options(options)
    new=build(snapshot,options)
    from shapely.geometry import Polygon
    if len(new['parcels'])!=len(old['parcels']):raise ValueError('Số vùng thay đổi; cần phân tích lại.')
    for before,after in zip(old['parcels'],new['parcels']):
        if not Polygon(before['points']).equals(Polygon(after['points'])):
            raise ValueError('Ranh thay đổi; cần phân tích lại.')
        for key in before.get('manual_fields',[]):after[key]=before[key]
        after['manual_fields']=before.get('manual_fields',[])
        after['MaLD']=after.get('LRD','')
    for key in ('working_dgn','working_sha256','references_excluded','status'):new[key]=old.get(key)
    for issue in new['issues']:
        if issue.get('parcel'):
            p=new['parcels'][issue['parcel']-1]
            if issue.get('field') in p.get('manual_fields',[]) and p.get(issue['field']):issue['resolved_by_manual_edit']=True
    save_project(project_path,new)
    return new
