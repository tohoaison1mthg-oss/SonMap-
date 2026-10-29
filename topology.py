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
    ignore = finite(options.get('ignore_tolerance', .001), 'Sai số bỏ qua') / scale
    min_area = finite(options.get('min_area', .3), 'Diện tích nhỏ')
    sheet = int(options.get('sheet', 1))
    if sheet <= 0:
        raise ValueError('Số tờ phải lớn hơn 0.')
    selected = set(levels(options.get('boundary_levels', '10')))
    issues, segments, seen, styles = [], [], set(), []

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
            styles.append({k:element.get(k,default) for k,default in
                           [('level',min(selected)),('color',0),('weight',0),('line_style','0'),('source_id',element.get('id'))]})
    if not segments:
        raise ValueError('Không có đường ranh trên các lớp đã chọn.')
    if options.get('snap',False) and tolerance:
        # Collapse submillimetre digitising noise even at connected vertices.
        # Complete-link groups prevent a chain from drifting across the map.
        from shapely.strtree import STRtree
        from shapely.geometry import box
        nodes=sorted({p for pair in segments for p in pair})
        tree=STRtree([Point(p) for p in nodes]);mapping={};radius=min(tolerance,.001/scale)
        for p in nodes:
            if p in mapping:continue
            group=[p]
            for index in sorted(map(int,tree.query(box(p[0]-radius,p[1]-radius,p[0]+radius,p[1]+radius)))):
                q=nodes[index]
                if q not in mapping and q!=p and all(math.dist(q,r)<=radius for r in group):group.append(q)
            for q in group:
                mapping[q]=p
                if q!=p:issue('SNAPPED_ENDPOINT',point=q,target=p,displacement_m=math.dist(q,p)*scale)
        normalized=[];new_styles=[];seen_normalized=set()
        for (a,b),style in zip(segments,styles):
            a,b=mapping[a],mapping[b];key=tuple(sorted((a,b)))
            if a==b:issue('ZERO_LENGTH_REMOVED',point=a);continue
            if key in seen_normalized:issue('DUPLICATE_REMOVED',point=a);continue
            seen_normalized.add(key);normalized.append((a,b));new_styles.append(style)
        segments,styles=normalized,new_styles
        if not segments:raise ValueError('Không còn đường ranh sau xử lý.')
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
    if options.get('snap',False) and tolerance:
        # Attach isolated ends to an existing junction, bounded endpoint group,
        # or a unique projection on another edge. Never chain a cluster beyond
        # the requested displacement or snap through an ambiguous junction.
        endpoint_tree=STRtree([LineString(pair) for pair in segments])
        assigned=set(replacements)
        for p in vertices:
            if counts[p]!=1 or p in assigned or p in replacements.values():continue
            close=nearby(p,tolerance)
            anchors=[q for q in close if counts[q]>1]
            target=None
            if len(anchors)==1:target=anchors[0]
            elif not anchors and close:
                group=[p]+close
                if all(counts[q]==1 for q in group) and all(math.dist(a,b)<=tolerance for a in group for b in group):
                    target=min(group)
                    for q in group:
                        assigned.add(q)
                        if q!=target and q not in replacements:
                            replacements[q]=target
                            issue('SNAPPED_ENDPOINT',point=q,target=target,displacement_m=math.dist(q,target)*scale)
                    continue
            if target is None and not close:
                point=Point(p);projections=[]
                for index in endpoint_tree.query(box(p[0]-tolerance,p[1]-tolerance,p[0]+tolerance,p[1]+tolerance)):
                    a,b=segments[int(index)]
                    if p in (a,b):continue
                    edge=LineString((a,b));q=edge.interpolate(edge.project(point))
                    if 0<point.distance(q)<=tolerance:projections.append(tuple(q.coords[0]))
                if projections and all(math.dist(projections[0],q)<=1e-9 for q in projections):target=projections[0]
            if target is not None and target!=p:
                replacements[p]=target;assigned.add(p)
                issue('SNAPPED_ENDPOINT',point=p,target=target,displacement_m=math.dist(p,target)*scale)
    repaired_with_style = [(replacements.get(a,a),replacements.get(b,b),style)
                           for (a,b),style in zip(segments,styles) if replacements.get(a,a)!=replacements.get(b,b)]
    repaired = [(a,b) for a,b,_ in repaired_with_style]
    if not repaired:
        raise ValueError('Không còn đường ranh sau xử lý.')
    network = unary_union([LineString(pair) for pair in repaired])
    # Save every crossing/T-junction as actual segment endpoints while retaining source symbology.
    source_lines=[LineString((a,b)) for a,b,_ in repaired_with_style]
    source_tree=STRtree(source_lines)
    noded_lines=[]
    for part in (list(network.geoms) if hasattr(network,'geoms') else [network]):
        for a,b in zip(part.coords,list(part.coords)[1:]):
            middle=Point((a[0]+b[0])/2,(a[1]+b[1])/2)
            candidates=sorted(int(i) for i in source_tree.query(middle.buffer(1e-7))
                              if source_lines[int(i)].distance(middle)<=1e-7)
            if not candidates:raise ValueError('Không xác định được thuộc tính ranh tại giao điểm; chưa ghi DGN.')
            noded_lines.append(dict(points=[list(a),list(b)],**repaired_with_style[candidates[0]][2]))
    original_vertices=set(vertices)
    original_edges=Counter((str(style.get('source_id')),tuple(sorted((a,b)))) for a,b,style in repaired_with_style)
    noded_edges=Counter((str(row.get('source_id')),tuple(sorted(map(tuple,row['points'])))) for row in noded_lines)
    boundary_changed=bool(replacements or options.get('join_lines') or original_edges!=noded_edges
                          or any(i['code']=='SNAPPED_ENDPOINT' for i in issues)
                          or any(i['code'] in ('DUPLICATE_REMOVED','ZERO_LENGTH_REMOVED','ARC_APPROXIMATED') for i in issues))
    for point in sorted({tuple(p) for row in noded_lines for p in row['points']}-original_vertices):
        issue('INTERSECTION_NODE',point=point)
    noded_degree=Counter(tuple(p) for row in noded_lines for p in (row['points'][0],row['points'][-1]))
    polygons, cuts, dangles, invalid = polygonize_full(network)
    for code, collection in [('CUT_EDGE', cuts), ('DANGLE', dangles), ('INVALID_RING', invalid)]:
        for geom in collection.geoms:
            coords=list(geom.coords)
            free=[p for p in (coords[0],coords[-1]) if noded_degree[tuple(p)]==1]
            issue(code, points=coords,point=(free or coords)[0])
    parcels = []
    for polygon in sorted(polygons.geoms, key=lambda g: (-g.representative_point().y, g.representative_point().x)):
        index = len(parcels) + 1
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
    # Ignore reporting noise without moving vertices or changing the parcel network.
    # A long dangling chain is only hidden if EVERY free end meets another edge
    # within the requested tolerance; one nearby end must not hide a real open end.
    ignored=[]
    if ignore:
        graph=[LineString(row['points']) for row in noded_lines]
        graph_tree=STRtree(graph)
        def close_to_other_edge(p):
            point=Point(p)
            for index in graph_tree.query(box(p[0]-ignore,p[1]-ignore,p[0]+ignore,p[1]+ignore)):
                edge=graph[int(index)]
                if tuple(p) in (tuple(edge.coords[0]),tuple(edge.coords[-1])):continue
                if point.distance(edge)<=ignore:return True
            return False
        retained=[]
        for item in issues:
            hidden=False
            if item['code']=='NEAR_NODE':
                hidden=all(math.dist(item['point'],q)<=ignore for q in item['candidates'])
            elif item['code']=='SHORT_SEGMENT':hidden=item['length_m']<=ignore*scale
            elif item['code']=='DANGLE':
                coords=item['points']
                free=[p for p in (coords[0],coords[-1]) if noded_degree[tuple(p)]==1]
                hidden=LineString(coords).length<=ignore or bool(free) and all(close_to_other_edge(p) for p in free)
            (ignored if hidden else retained).append(item)
        issues=retained
    drawing_network = network
    if options.get('join_lines'):
        from shapely.ops import linemerge
        if hasattr(network, 'geoms'):
            drawing_network = linemerge(network)
        groups={}
        for row in noded_lines:
            key=(row['level'],row['color'],row['weight'],row['line_style'],row['source_id'])
            groups.setdefault(key,[]).append(LineString(row['points']))
        merged=[]
        for key,group in groups.items():
            geometry=linemerge(group)
            for part in (list(geometry.geoms) if hasattr(geometry,'geoms') else [geometry]):
                merged.append(dict(zip(('level','color','weight','line_style','source_id'),key),points=list(part.coords)))
        noded_lines=merged
    lines = list(drawing_network.geoms) if hasattr(drawing_network, 'geoms') else [drawing_network]
    return dict(version=1, source=snapshot.get('source'), model=snapshot.get('model'),
                model_is_default=bool(snapshot.get('model_is_default',False)),
                unit=snapshot.get('unit'),uors_per_master_unit=snapshot.get('uors_per_master_unit'), options=options, parcels=parcels,
                cleaned_lines=[list(line.coords) for line in lines],noded_lines=noded_lines,boundary_changed=boundary_changed, issues=issues,ignored_issues=ignored,
                input_summary={str(level):sum(int(e['level'])==level for e in snapshot['elements']) for level in sorted(selected)})


BLOCKING = {'UNSUPPORTED', 'CUT_EDGE', 'DANGLE', 'INVALID_RING', 'HOLE_UNSUPPORTED', 'NO_PARCELS'}


def export_rows(project,allow_unnumbered=False,allow_zero_id=False,allow_duplicate_numbers=False):
    """Refuse incomplete topology; preserve DGN coordinates for existing world-coordinate export."""
    if any(i['code'] in BLOCKING for i in project['issues']):
        raise ValueError('Còn lỗi topology/kiểu phần tử chưa hỗ trợ. Xem báo cáo và sửa ranh trước khi tạo MDB.')
    # Suppressing a visual contact warning does not close a missing polygon.
    ignore=finite(project['options'].get('ignore_tolerance',.001),'Sai số bỏ qua')
    scale=float(project['options']['metres_per_unit'])
    if any(i['code']=='DANGLE' and sum(math.dist(a,b) for a,b in zip(i['points'],i['points'][1:]))*scale>ignore
           for i in project.get('ignored_issues',[])):
        raise ValueError('Có ranh tiếp xúc trong sai số bỏ qua nhưng chưa khép vùng. Nối ranh trước khi tạo MDB.')
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
        if ring_issues(p['points']):
            raise ValueError(f"Hình học thửa {p['ID']} không tương thích bộ xuất hiện tại.")
        LineString, Point, Polygon, _, _ = _engine()
        polygon = Polygon(p['points'],p.get('holes',[]))
        if not polygon.is_valid:raise ValueError('Các vòng thửa không hợp lệ.')
        if not polygon.contains(Point(p['centre'])):
            raise ValueError('Tâm thửa phải nằm bên trong vùng.')
        if not math.isfinite(float(p['DienTich'])) or abs(polygon.area-float(p['DienTich'])) > max(1e-8,polygon.area*1e-10):
            raise ValueError('Diện tích không khớp hình học; hãy phân tích lại.')
        rings=[p['points']]+p.get('holes',[])
        blob = b'\0' + struct.pack('<II',3,len(rings))
        for ring in rings:
            closed=list(map(tuple,ring))
            if closed[-1]!=closed[0]:closed.append(closed[0])
            if ring_issues(closed[:-1]):raise ValueError('Vòng thửa không hợp lệ.')
            blob+=struct.pack('<I',len(closed))+b''.join(struct.pack('<dd',*point) for point in closed)
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
