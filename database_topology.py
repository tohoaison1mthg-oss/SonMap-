"""Plan a scoped MDB parcel update; retain records outside the rebuilt footprint."""
import copy
import math
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import unary_union
from shapely.strtree import STRtree
from app import geometry
from topology import export_rows

FIELDS=('ToBD','TCT','TenChu','DiaChi','DiaChiThuaDatChiTiet','Xudong','LRD','MaLD')


def scope_splits(project, old_rows):
    """Rebuild complete split parcels only; reject errors touching their footprint."""
    from topology import BLOCKING
    if any(i['code'] in ('UNSUPPORTED','SNAPPED_ENDPOINT') for i in project['issues']):
        raise ValueError('Không thể cập nhật cục bộ khi có phần tử chưa hỗ trợ hoặc đã nối ranh.')
    faces=[Polygon(p['points']) for p in project['parcels']]
    selected=set();parents=[]
    for row in old_rows:
        parent=Polygon(geometry(row['Geometry']))
        tolerance=max(1e-8,parent.length*1e-7)
        children=[i for i,p in enumerate(faces) if p.intersection(parent).area>tolerance
                  and p.difference(parent).area<=tolerance]
        if len(children)<2:continue
        union=unary_union([faces[i] for i in children])
        if union.symmetric_difference(parent).area>tolerance:continue
        if union.boundary.hausdorff_distance(parent.boundary)>1e-7:continue
        selected.update(children);parents.append(row['ID'])
    if not selected:raise ValueError('Chưa có thửa tách kín và phủ đủ thửa MDB cũ để cập nhật cục bộ.')
    footprint=unary_union([faces[i] for i in selected])
    chosen_ids={project['parcels'][i]['ID'] for i in selected}
    issues=[];excluded=[]
    for issue in project['issues']:
        location=None
        if issue.get('points'):location=LineString(issue['points'])
        elif issue.get('point'):location=Point(issue['point'])
        relevant=(location is not None and location.distance(footprint)<=1e-7) or issue.get('parcel') in chosen_ids
        if issue['code'] in BLOCKING and (relevant or (location is None and not issue.get('parcel'))):
            raise ValueError('Còn lỗi ranh trong phạm vi thửa tách: '+issue['code'])
        (issues if relevant else excluded).append(copy.deepcopy(issue))
    result=copy.deepcopy(project)
    result['parcels']=[copy.deepcopy(project['parcels'][i]) for i in sorted(selected)]
    result['issues']=issues
    result['scope_rings']=[p['points'] for p in result['parcels']]
    result['scope_parent_ids']=parents
    result['excluded_issues']=excluded
    return result


def reconcile(project, old_rows):
    updated=copy.deepcopy(project)
    new=updated['parcels']
    polygons=[Polygon(p['points']) for p in new]
    if not polygons:raise ValueError('Chưa có vùng thửa mới.')
    old_polygons=[Polygon(geometry(r['Geometry'])) for r in old_rows]
    # World-coordinate intersections lose a few ULPs near million-metre origins.
    # This is floating-point roundoff only, independent of the user's snap setting.
    magnitude=max(abs(v) for p in polygons+old_polygons for v in p.bounds)
    epsilon=max(1e-7,16*math.ulp(magnitude))
    def area_tolerance(p):
        return max(1e-8,p.area*1e-10,p.length*epsilon)
    def same_region(a,b):
        return (a.equals(b) or (a.symmetric_difference(b).area<=max(area_tolerance(a),area_tolerance(b))
                and a.boundary.hausdorff_distance(b.boundary)<=epsilon))
    if any(not p.is_valid for p in old_polygons):raise ValueError('MDB cũ chứa hình học không hợp lệ; chưa cập nhật.')
    ids=[int(r['ID']) for r in old_rows]
    if len(set(ids))!=len(ids):raise ValueError('MDB có ID trùng.')
    tree=STRtree(old_polygons)
    footprint=unary_union(polygons)
    touched=set()
    for i,p in enumerate(old_polygons):
        tolerance=area_tolerance(p)
        overlap=p.intersection(footprint).area
        if overlap>tolerance:
            if p.difference(footprint).area>tolerance:
                raise ValueError(f"Ranh mới chỉ phủ một phần thửa ID {old_rows[i]['ID']}; không xóa hoặc thay thửa này.")
            touched.add(i)
    next_id=max(ids,default=0)+1
    matched=set();parents_for_new=[];new_ids=[];unchanged_geometry={}
    for parcel,polygon in zip(new,polygons):
        candidates=[int(i) for i in tree.query(polygon) if old_polygons[int(i)].intersection(polygon).area>area_tolerance(polygon)]
        exact=[i for i in candidates if same_region(polygon,old_polygons[i])]
        inherited=None
        if len(exact)==1:
            i=exact[0];matched.add(i);parcel['ID']=int(old_rows[i]['ID']);inherited=old_rows[i]
            unchanged_geometry[parcel['ID']]=old_rows[i]
        else:
            parcel['ID']=next_id;new_ids.append(next_id);next_id+=1
            containers=[i for i in candidates if polygon.difference(old_polygons[i]).area<=area_tolerance(polygon)]
            if len(containers)==1:inherited=old_rows[containers[0]]
            if 'TCT' not in parcel.get('manual_fields',[]) and 'TCT' not in parcel.get('label_sources',{}):parcel['TCT']=None
        if inherited:
            for field in FIELDS:
                if field in parcel.get('manual_fields',[]) or field in parcel.get('label_sources',{}):continue
                parcel[field]=inherited.get(field) if field in ('ToBD','TCT') else (inherited.get(field) or '')
        parcel['parent_ids']=[int(old_rows[i]['ID']) for i in candidates]
        parents_for_new.append(candidates)
    # Re-key parcel-index diagnostics after stable MDB IDs are assigned.
    for item in updated['issues']:
        if item.get('parcel') and 0<int(item['parcel'])<=len(new):item['parcel']=new[int(item['parcel'])-1]['ID']
    rows=export_rows(updated,allow_unnumbered=True,allow_zero_id=0 in ids,allow_duplicate_numbers=True)
    for row in rows:
        if row['ID'] in unchanged_geometry:
            # Keep the original binary geometry and measured value for an unchanged
            # parcel; rebuilding topology must not rewrite every MDB record.
            row['Geometry']=unchanged_geometry[row['ID']]['Geometry']
            row['DienTich']=unchanged_geometry[row['ID']]['DienTich']
    delete=[int(old_rows[i]['ID']) for i in sorted(touched-matched)]
    existing_ids=set(ids)
    inserts=[dict(r) for r in rows if r['ID'] not in existing_ids]
    by_id={p['ID']:p for p in new}
    for row in inserts:
        parents=by_id[row['ID']].get('parent_ids',[])
        if len(parents)==1:row['_parent_id']=parents[0]
    old_by_id={int(r['ID']):r for r in old_rows}
    updates=[r for r in rows if r['ID'] in existing_ids and any(
        value!=old_by_id[r['ID']].get(key) and not (value in ('',None) and old_by_id[r['ID']].get(key) in ('',None))
        for key,value in r.items())]
    final=[dict(r) for i,r in enumerate(old_rows) if i not in touched]+rows
    splits=[{'old_id':int(old_rows[i]['ID']),'new_ids':[p['ID'] for p,c in zip(new,parents_for_new) if i in c]}
            for i in sorted(touched) if sum(i in c for c in parents_for_new)>1]
    return {'project':updated,'delete_ids':delete,'insert_rows':inserts,'update_rows':updates,'final_rows':final,
            'before_count':len(old_rows),'after_count':len(final),'splits':splits,
            'unnumbered':sum(r.get('TCT') is None for r in final)}
