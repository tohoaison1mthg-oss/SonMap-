"""Planar linework -> reviewable SonMap parcels. Coordinates stay in DGN master units."""
import base64
import json
import math
import struct
from collections import Counter
from pathlib import Path


def _engine():
    try:
        from shapely.geometry import LineString, Point, Polygon
        from shapely.ops import polygonize_full, unary_union
    except ImportError as exc:
        raise RuntimeError('Chức năng topology cần Shapely: python -m pip install -r requirements-topology.txt') from exc
    return LineString, Point, Polygon, polygonize_full, unary_union


def finite(value, name, positive=False):
    value = float(value)
    if not math.isfinite(value) or (value <= 0 if positive else value < 0):
        raise ValueError(f'{name}: giá trị không hợp lệ.')
    return value


def levels(value):
    result = {int(v.strip()) for v in str(value).split(',') if v.strip()}
    if not result or any(v < 1 or v > 63 for v in result):
        raise ValueError('Nhập lớp V8i/V7 từ 1 đến 63, ngăn bằng dấu phẩy.')
    return sorted(result)


def build(snapshot, options):
    LineString, Point, Polygon, polygonize_full, unary_union = _engine()
    scale = finite(options.get('metres_per_unit', 1), 'Mét/đơn vị', True)
    small = finite(options.get('short_length', .001), 'Đoạn ngắn') / scale
    near = finite(options.get('near_distance', .1), 'Nút gần') / scale
    tolerance = finite(options.get('snap_tolerance', .01), 'Sai số nối') / scale
    min_area = finite(options.get('min_area', .3), 'Diện tích nhỏ')
    sheet = int(options.get('sheet', 1))
    if sheet <= 0:
        raise ValueError('Số tờ phải lớn hơn 0.')
    selected = set(levels(options.get('boundary_levels', '10')))
    issues, segments, seen = [], [], set()

    def issue(code, **kw):
        issues.append(dict(code=code, **kw))

    for element in snapshot['elements']:
        if int(element['level']) not in selected:
            continue
        if element['kind'] != 'line':
            issue('UNSUPPORTED', element=element.get('id'), detail=element.get('kind'), reason=element.get('reason',''))
            continue
        if element.get('approximate'):
            issue('ARC_APPROXIMATED', element=element.get('id'), tolerance_m=options.get('chord_tolerance'))
        points = [tuple(map(float, p)) for p in element['points']]
        if len(points) < 2 or any(len(p) != 2 or not all(map(math.isfinite, p)) for p in points):
            raise ValueError('Phần tử có tọa độ không hợp lệ.')
        for a, b in zip(points, points[1:]):
            length = math.dist(a, b)
            if length <= 1e-12:
                issue('ZERO_LENGTH_REMOVED', point=a)
                continue
            if options.get('short_enabled',True) and length < small:
                issue('SHORT_SEGMENT', point=a, length_m=length * scale)
            key = tuple(sorted((a, b)))
            if key in seen:
                issue('DUPLICATE_REMOVED', point=a)
                continue
            seen.add(key)
            segments.append((a, b))
    if not segments:
        raise ValueError('Không có đường ranh trên các lớp đã chọn.')
    # Snap only isolated endpoints to ONE existing endpoint within the explicit tolerance.
    # Do not use transitive clustering or extend a line through a junction.
    counts = Counter(p for pair in segments for p in pair)
    vertices = sorted(counts)
    from shapely.strtree import STRtree
    from shapely.geometry import box
    vertex_tree = STRtree([Point(p) for p in vertices])

    def nearby(p, radius):
        indices = vertex_tree.query(box(p[0]-radius, p[1]-radius, p[0]+radius, p[1]+radius))
        return [vertices[int(i)] for i in indices if vertices[int(i)] != p and math.dist(p, vertices[int(i)]) <= radius]

    replacements = {}
    if len(vertices) > 30000:
        raise ValueError('Vượt 30.000 nút; hãy chia phạm vi bản đồ trước khi xử lý.')
    for p in vertices:
        if counts[p] != 1:
            continue
        candidates = nearby(p, near)
        if candidates and options.get('near_enabled',True):
            issue('NEAR_NODE', point=p, candidates=candidates)
        close = nearby(p, tolerance)
        if options.get('snap', False) and len(close) == 1:
            q = close[0]
            reverse = nearby(q, tolerance)
            if counts[q] == 1 and reverse == [p]:
                # Deterministic pair, retain one existing coordinate (no averaged drift).
                replacements[max(p, q)] = min(p, q)
    for p, q in replacements.items():
        issue('SNAPPED_ENDPOINT', point=p, target=q, displacement_m=math.dist(p, q) * scale)
    repaired = [(replacements.get(a, a), replacements.get(b, b)) for a, b in segments]
    repaired = [(a, b) for a, b in repaired if a != b]
    if not repaired:
        raise ValueError('Không còn đường ranh sau xử lý.')
    network = unary_union([LineString(pair) for pair in repaired])
    polygons, cuts, dangles, invalid = polygonize_full(network)
    for code, collection in [('CUT_EDGE', cuts), ('DANGLE', dangles), ('INVALID_RING', invalid)]:
        for geom in collection.geoms:
            issue(code, points=list(geom.coords))
    parcels = []
    for polygon in sorted(polygons.geoms, key=lambda g: (-g.representative_point().y, g.representative_point().x)):
        index = len(parcels) + 1
        if polygon.interiors:
            issue('HOLE_UNSUPPORTED', parcel=index)
        centre = polygon.representative_point()
        measured = polygon.area * scale * scale
        if options.get('area_enabled',True) and measured < min_area:
            issue('SMALL_PARCEL', parcel=index, area_m2=measured)
        p = dict(ID=index, ToBD=sheet, TCT=None, DienTich=measured, TenChu='', DiaChi='',
                 DiaChiThuaDatChiTiet='', Xudong='', LRD='', MaLD='',
                 points=list(polygon.exterior.coords)[:-1],
                 holes=[list(r.coords) for r in polygon.interiors],
                 centre=[centre.x, centre.y], label_sources={})
        for field, level_spec in options.get('label_levels', {}).items():
            if field not in ('TCT', 'TenChu', 'Xudong', 'LRD') or not str(level_spec).strip():
                continue
            wanted = set(levels(level_spec))
            labels = []
            for text in snapshot.get('texts', []):
                if int(text['level']) in wanted and polygon.covers(Point(text['point'])):
                    labels.append(text)
            # Labels exactly on a boundary are ambiguous, never assign twice.
            if len(labels) != 1 or (labels and not polygon.contains(Point(labels[0]['point']))):
                issue('LABEL_MISSING' if not labels else 'LABEL_AMBIGUOUS', parcel=index, field=field, labels=labels)
                continue
            value = str(labels[0]['text']).strip()
            if field == 'TCT':
                if not value.isascii() or not value.isdecimal() or not 0 < int(value) <= 2147483647:
                    issue('LABEL_INVALID', parcel=index, field=field, value=value)
                    continue
                value = int(value)
            p[field] = value
            p['label_sources'][field] = labels[0]
        p['MaLD'] = p['LRD']
        parcels.append(p)
    if not parcels:
        issue('NO_PARCELS')
    drawing_network = network
    if options.get('join_lines'):
        from shapely.ops import linemerge
        if hasattr(network, 'geoms'):
            drawing_network = linemerge(network)
    lines = list(drawing_network.geoms) if hasattr(drawing_network, 'geoms') else [drawing_network]
    return dict(version=1, source=snapshot.get('source'), model=snapshot.get('model'),
                model_is_default=bool(snapshot.get('model_is_default',False)),
                unit=snapshot.get('unit'), options=options, parcels=parcels,
                cleaned_lines=[list(line.coords) for line in lines], issues=issues,
                input_summary={str(level):sum(int(e['level'])==level for e in snapshot['elements']) for level in sorted(selected)})


BLOCKING = {'UNSUPPORTED', 'CUT_EDGE', 'DANGLE', 'INVALID_RING', 'HOLE_UNSUPPORTED', 'NO_PARCELS'}


def export_rows(project,allow_unnumbered=False,allow_zero_id=False,allow_duplicate_numbers=False):
    """Refuse incomplete topology; preserve DGN coordinates for existing world-coordinate export."""
    if any(i['code'] in BLOCKING for i in project['issues']):
        raise ValueError('Còn lỗi topology/kiểu phần tử chưa hỗ trợ. Xem báo cáo và sửa ranh trước khi tạo MDB.')
    if float(project['options']['metres_per_unit']) != 1:
        raise ValueError('Xuất MDB hiện yêu cầu DGN dùng mét để tương thích bộ xuất hồ sơ SonMap.')
    rows, seen, ids = [], set(), set()
    from quality import ring_issues
    for parcel in project['parcels']:
        p = dict(parcel)
        try:
            for field in ('ToBD', 'TCT', 'ID'):
                value = p[field]
                if field=='TCT' and value is None and allow_unnumbered:continue
                minimum=0 if field=='ID' and allow_zero_id else 1
                if isinstance(value, bool) or str(value).strip() != str(int(value)) or not minimum <= int(value) <= 2147483647:
                    raise ValueError()
                p[field] = int(value)
        except (TypeError, ValueError, KeyError):
            raise ValueError(f"Thửa ID {p.get('ID')}: nhập số tờ, số thửa và ID nguyên dương.") from None
        if p['ID'] in ids:
            raise ValueError('Trùng ID thửa.')
        ids.add(p['ID'])
        for field in ('TenChu','DiaChi','DiaChiThuaDatChiTiet','Xudong','LRD'):
            if not isinstance(p.get(field, ''), str) or len(p.get(field, '')) > 255:
                raise ValueError(f'{field}: cần chuỗi tối đa 255 ký tự.')
        key = (p['ToBD'], p['TCT'])
        if p['TCT'] is not None and key in seen and not allow_duplicate_numbers:
            raise ValueError(f'Trùng số tờ/thửa {key}.')
        if p['TCT'] is not None:seen.add(key)
        if p.get('holes') or ring_issues(p['points']):
            raise ValueError(f"Hình học thửa {p['ID']} không tương thích bộ xuất hiện tại.")
        LineString, Point, Polygon, _, _ = _engine()
        polygon = Polygon(p['points'])
        if not polygon.contains(Point(p['centre'])):
            raise ValueError('Tâm thửa phải nằm bên trong vùng.')
        if not math.isfinite(float(p['DienTich'])) or abs(polygon.area-float(p['DienTich'])) > max(1e-8,polygon.area*1e-10):
            raise ValueError('Diện tích không khớp hình học; hãy phân tích lại.')
        closed = p['points'] + [p['points'][0]]
        blob = b'\0' + struct.pack('<III', 3, 1, len(closed))
        blob += b''.join(struct.pack('<dd', *point) for point in closed)
        p['Geometry'] = base64.b64encode(blob).decode('ascii')
        p['MaLD'] = p.get('MaLD', p.get('LRD', ''))
        rows.append({k: p.get(k) for k in ('ID', 'ToBD', 'TCT', 'DienTich', 'TenChu', 'DiaChi', 'DiaChiThuaDatChiTiet', 'Xudong', 'LRD', 'MaLD', 'Geometry')})
    if not rows:
        raise ValueError('Chưa có thửa để xuất.')
    return rows


def save_project(path, project):
    path = Path(path)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(project, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    temporary.replace(path)
