"""Resolve list and drawing selections by record identity, never parcel number."""
import json
from pathlib import Path

def reference_context(root,source='',target=''):
    root=Path(root)
    candidates=[]
    if source and target:candidates.append({'source':source,'target':target})
    try:candidates.append(json.loads((root/'data/last-export.json').read_text(encoding='utf-8')))
    except (OSError,ValueError):pass
    try:
        receipt=(root/'data/result.txt').read_text(encoding='utf-16').split('\t',2)
        runtime=(root/'data/runtime.txt').read_text(encoding='utf-16').splitlines()
        if len(receipt)==3 and receipt[0]=='OK' and runtime:
            candidates.append({'source':runtime[0],'target':receipt[2].strip()})
    except (OSError,ValueError):pass
    for pair in candidates:
        try:
            source_path=Path(pair['source']).resolve();target_path=Path(pair['target']).resolve()
            if source_path!=target_path and source_path.suffix.lower()=='.dgn' and target_path.suffix.lower()=='.dgn' and source_path.is_file() and target_path.is_file():
                return {'source':str(source_path),'target':str(target_path)}
        except (KeyError,TypeError,OSError):continue
    raise ValueError('Chưa có cặp bản đồ nguồn và hồ sơ xuất hợp lệ. Xuất hồ sơ thành công, giữ DGN kết quả mở rồi bấm Ánh xạ.')

def record_index(parcels,record_id):
    found=[i for i,p in enumerate(parcels) if p['ID']==record_id]
    if len(found)!=1:
        raise ValueError('Không tìm thấy duy nhất ID thửa đã chọn. Đọc lại MDB trước khi xuất.')
    return found[0]
