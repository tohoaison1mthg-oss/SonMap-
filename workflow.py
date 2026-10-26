"""Active drawing conventions and address composition."""
from pathlib import Path
import json

FOLDERS={'TrichLuc':'Trich luc','GCN':'In GCN','Mau03':'Phieu do dac chinh ly'}
def drawing_paths(dgn,root,mode='TrichLuc',require_mdb=True):
    path=Path(dgn).resolve()
    if path.suffix.lower()!='.dgn' or not path.is_file():raise ValueError('DGN đang mở không hợp lệ.')
    mdb=path.with_suffix('.mdb')
    if require_mdb and not mdb.is_file():raise FileNotFoundError('Không tìm thấy MDB cùng tên: '+str(mdb))
    if mode not in FOLDERS:raise ValueError('Loại hồ sơ không hợp lệ.')
    return {'dgn':str(path),'mdb':str(mdb),'template':str(Path(root)/'assets/TrichLucTT26 -ThanhTan.dgn'),'output':str(path.parent/FOLDERS[mode])}

def profile_key(dgn):return str(Path(dgn).resolve().parent).casefold()
def address_profile(root,dgn):
    p=Path(root)/'data/address_profiles.json'
    data=json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
    return data.get(profile_key(dgn),{})
def save_address_profile(root,dgn,profile):
    p=Path(root)/'data/address_profiles.json';p.parent.mkdir(exist_ok=True)
    data=json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
    data[profile_key(dgn)]={k:str(profile.get(k,'')).strip() for k in ('commune','province')}
    temp=p.with_suffix('.tmp');temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(p)
def parcel_address(parcel,profile):
    if parcel.get('address_override','').strip():return parcel['address_override'].strip()
    values=[parcel.get('Xudong') or parcel.get('XuDong') or '']+[profile.get(k,'') for k in ('commune','province')]
    parts=[];seen=set()
    for value in values:
        for part in str(value).split(','):
            part=' '.join(part.split());key=part.casefold()
            if part and key not in seen:parts.append(part);seen.add(key)
    return ', '.join(parts)

def toolbar_icon(tk,master,kind):
    image=tk.PhotoImage(master=master,width=20,height=20)
    color={'read':'#168c9c','save':'#3479bb','build':'#7656a8','export':'#269462','print':'#596778','sheet':'#cf8431','address':'#b55575','find':'#3479bb','check':'#d59a20'}.get(kind,'#64748b')
    image.put(color,to=(2,2,18,18));image.put('#ffffff',to=(5,5,15,15))
    if kind=='map':
        image.put('#4da879',to=(6,6,10,12));image.put('#4da879',to=(12,10,16,15))
    elif kind=='save':image.put(color,to=(7,11,13,16));image.put(color,to=(7,4,13,7))
    elif kind=='check':image.put(color,to=(9,5,11,11));image.put(color,to=(9,13,11,15))
    else:
        for y in (7,10,13):image.put(color,to=(7,y,14,y+1))
    return image
