from pathlib import Path
import zipfile, shutil
root=Path(__file__).parent
source=root.parent
with zipfile.ZipFile(root/'payload.zip','w',compression=zipfile.ZIP_STORED) as z:
    for p in source.iterdir():
        if p.is_file() and p.suffix in ('.py','.ps1','.cmd','.bas','.cls','.md','.mvba'):
            if p.name not in ('setup_prepare.py','update_vba.ps1'):z.write(p,p.name)
    z.write(source/'VERSION','VERSION')
    z.write(source/'requirements-topology.txt','requirements-topology.txt')
    z.write(source/'admin_catalog.json','admin_catalog.json')
    z.write(source/'sonmap.ico','sonmap.ico')
    for folder in ('runtime','assets'):
        for p in (source/folder).rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts:z.write(p,p.relative_to(source).as_posix())
    for name in ('setup_prepare.py','update_vba.ps1'):z.write(root/name,name)
# Windows PowerShell needs BOM for Vietnamese paths and messages.
p=root/'install.ps1';p.write_text(p.read_text(encoding='utf-8-sig'),encoding='utf-8-sig')
print('Payload ready:',(root/'payload.zip').stat().st_size)
