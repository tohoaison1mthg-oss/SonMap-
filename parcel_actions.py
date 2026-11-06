"""Resolve list and drawing selections by record identity, never parcel number."""
def record_index(parcels,record_id):
    found=[i for i,p in enumerate(parcels) if p['ID']==record_id]
    if len(found)!=1:
        raise ValueError('Không tìm thấy duy nhất ID thửa đã chọn. Đọc lại MDB trước khi xuất.')
    return found[0]
