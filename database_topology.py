"""Plan a scoped MDB parcel update; retain records outside the rebuilt footprint."""
import copy
from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely.strtree import STRtree
from app import geometry
from topology import export_rows

FIELDS=('ToBD','TCT','TenChu','DiaChi','DiaChiThuaDatChiTiet','Xudong','LRD','MaLD')


def reconcile(project, old_rows):
    updated=copy.deepcopy(project)
    new=updated['parcels']
    polygons=[Polygon(p['points']) for p in new]
    if not polygons:raise ValueError('Chưa có vùng thửa mới.')
    old_polygons=[Polygon(geometry(r['Geometry'])) for r in old_rows]
    if any(not p.is_valid for p in old_polygons):raise ValueError('MDB cũ chứa hình học không hợp lệ; chưa cập nhật.')
    ids=[int(r['ID']) for r in old_rows]
    if len(set(ids))!=len(ids):raise ValueError('MDB có ID trùng.')
    tree=STRtree(old_polygons)
    footprint=unary_union(polygons)
    touched=set()
    for i,p in enumerate(old_polygons):
        tolerance=max(1e-8,p.area*1e-10)
        overlap=p.intersection(footprint).area
        if overlap>tolerance:
            if p.difference(footprint).area>tolerance:
                raise ValueError(f"Ranh mới chỉ phủ một phần thửa ID {old_rows[i]['ID']}; không xóa hoặc thay thửa này.")
            touched.add(i)
    next_id=max(ids,default=0)+1
    matched=set();parents_for_new=[];new_ids=[]
    for parcel,polygon in zip(new,polygons):
        candidates=[int(i) for i in tree.query(polygon) if old_polygons[int(i)].intersection(polygon).area>max(1e-8,polygon.area*1e-10)]
        exact=[i for i in candidates if polygon.equals(old_polygons[i])]
        inherited=None
        if len(exact)==1:
            i=exact[0];matched.add(i);parcel['ID']=int(old_rows[i]['ID']);inherited=old_rows[i]
        else:
            parcel['ID']=next_id;new_ids.append(next_id);next_id+=1
            containers=[i for i in candidates if polygon.difference(old_polygons[i]).area<=max(1e-8,polygon.area*1e-10)]
            if len(containers)==1:inherited=old_rows[containers[0]]
            if 'TCT' not in parcel.get('manual_fields',[]) and 'TCT' not in parcel.get('label_sources',{}):parcel['TCT']=None
        if inherited:
            for field in FIELDS:
                if field=='TCT' and not exact:continue
                if field in parcel.get('manual_fields',[]) or field in parcel.get('label_sources',{}):continue
                parcel[field]=inherited.get(field) if field in ('ToBD','TCT') else (inherited.get(field) or '')
        parcel['parent_ids']=[int(old_rows[i]['ID']) for i in candidates]
        parents_for_new.append(candidates)
    # Re-key parcel-index diagnostics after stable MDB IDs are assigned.
    for item in updated['issues']:
        if item.get('parcel') and 0<int(item['parcel'])<=len(new):item['parcel']=new[int(item['parcel'])-1]['ID']
    rows=export_rows(updated,allow_unnumbered=True)
    delete=[int(old_rows[i]['ID']) for i in sorted(touched-matched)]
    existing_ids=set(ids)
    inserts=[r for r in rows if r['ID'] not in existing_ids]
    updates=[r for r in rows if r['ID'] in existing_ids]
    final=[dict(r) for i,r in enumerate(old_rows) if i not in touched]+rows
    splits=[{'old_id':int(old_rows[i]['ID']),'new_ids':[p['ID'] for p,c in zip(new,parents_for_new) if i in c]}
            for i in sorted(touched) if sum(i in c for c in parents_for_new)>1]
    return {'project':updated,'delete_ids':delete,'insert_rows':inserts,'update_rows':updates,'final_rows':final,
            'before_count':len(old_rows),'after_count':len(final),'splits':splits,
            'unnumbered':sum(r.get('TCT') is None for r in final)}
