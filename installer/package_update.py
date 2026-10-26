"""Build a per-user Windows installer ZIP from source, without bundling private assets."""
import argparse
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def release_version(root=ROOT):
    version=(root/'VERSION').read_text(encoding='utf-8-sig').strip()
    if not re.fullmatch(r'\d+\.\d+',version):raise ValueError('VERSION must contain major.minor')
    return version


def source_files(root=ROOT):
    allowed={'.py','.ps1','.bas','.cls','.md','.cmd','.ico','.code-workspace'}
    files=[p for p in root.iterdir() if p.is_file() and
           (p.suffix.lower() in allowed or p.name in ('VERSION','admin_catalog.json','requirements-topology.txt'))]
    files += [p for p in (root/'installer').iterdir() if p.is_file() and p.suffix.lower() in ('.cs','.py','.ps1','.cmd')]
    return sorted(files,key=lambda p:p.relative_to(root).as_posix())


def build(output,root=ROOT):
    version=release_version(root)
    files=source_files(root)
    for required in ('app.py','VERSION','start_topology.ps1','requirements-topology.txt','dgn_models.ps1'):
        if root/required not in files:raise ValueError('Missing release file: '+required)
    manifest=[{'file':p.relative_to(root).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as package:
        for path in files:package.write(path,path.relative_to(root).as_posix())
        package.writestr('MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    with zipfile.ZipFile(io.BytesIO(stream.getvalue())) as package:
        if package.testzip():raise ValueError('Invalid payload ZIP')
        for entry in manifest:
            if hashlib.sha256(package.read(entry['file'])).hexdigest()!=entry['sha256']:raise ValueError('Payload integrity check failed')
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    destination=output/('SonMapPlus_V'+version.replace('.','_')+'_Update.zip')
    if destination.exists():raise FileExistsError('Release package already exists; choose a new version or output directory.')
    guide=f'''SONMAP+ V{version} - CAI DAT / CAP NHAT LAPTOP

1. Dong SonMap dang chay. Giai nen toan bo ZIP vao mot thu muc.
2. Nhan dup Cai_dat.cmd. Khong chay file ben trong cua so xem ZIP.
3. Lan dau can Internet; trinh cai tu chuan bi Python 3.12 rieng neu thieu.
4. Trinh cai tu tao moi truong Python rieng va loi tat SonMap+ tren Desktop.
5. Mo V8i va luu DGN truoc khi cai. Trinh cai thu quet truc tiep tren V8i.
   Mo bang loi tat, kiem tra tieu de SonMap+ V{version}.
   Neu can thu lai: chay Kiem_tra_quet_DGN.cmd. Bao cao o data/v8i-scan-*.json.
6. Mo MicroStation va DGN, chay Kiem_tra_V8i.cmd neu can kiem tra ket noi
   va tham khao cau hinh C:\\VietMapXM (chi doc). Bao cao o thu muc cai\\data\\vietmapxm-diagnostic.json.

Thu muc cai: %LOCALAPPDATA%\\SonMapPlus\\App
Sao luu ma cu: %LOCALAPPDATA%\\SonMapPlus\\Backups
Nhat ky cai dat: %LOCALAPPDATA%\\SonMapPlus\\Logs
Khong ghi de DGN/MDB, assets, runtime, settings.json hay data hien co.
Ban cai nguon nay khong kem MicroStation, runtime/vendor DLL hoac
bo tai nguyen xuat ho so rieng. Python 3.12 phu hop duoc tai su dung; neu thieu se tai bo cai chinh thuc,
kiem tra chu ky va cai rieng, khong go Python 3.15 hoac doi PATH.

Neu con loi V8i: gui file data\\dgn-topology-last.log trong thu muc cai.
Cau noi V8i/Jet va trinh cai moi van can kiem chung tren Windows thuc te.
'''
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as installer:
        installer.write(root/'installer/update.cmd','Cai_dat.cmd')
        installer.write(root/'installer/update.ps1','Cai_dat.ps1')
        installer.write(root/'Kiem_tra_V8i.cmd','Kiem_tra_V8i.cmd')
        installer.write(root/'Kiem_tra_quet_DGN.cmd','Kiem_tra_quet_DGN.cmd')
        installer.writestr('payload.zip',stream.getvalue())
        installer.writestr('HUONG_DAN.txt',guide.encode('utf-8-sig'))
    with zipfile.ZipFile(destination) as installer:
        if installer.testzip():raise ValueError('Installer ZIP integrity check failed')
    return destination


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    print(build(args.output))
