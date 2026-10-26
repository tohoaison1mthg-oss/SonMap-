"""Package source history for local development; GitHub credentials are never included."""
import hashlib
import subprocess
import tempfile
import zipfile
from pathlib import Path
try:
    from installer.package_update import ROOT, release_version
except ModuleNotFoundError:
    from package_update import ROOT, release_version


def build_workspace(output):
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT).strip():
        raise ValueError('Commit the release before packaging its source history.')
    objects=subprocess.check_output(['git','rev-list','--objects','--all'],cwd=ROOT,text=True)
    for item in objects.splitlines():
        name=item.partition(' ')[2].lower()
        if name.endswith(('.mdb','.dgn','.mvba','.dll','.key','.pfx','.pem')):
            raise ValueError('Private/runtime material in Git history; do not distribute bundle: '+name)
    destination=Path(output)/('SonMapPlus_V'+release_version().replace('.','_')+'_Laptop_Workspace.zip')
    if destination.exists():raise FileExistsError(destination)
    destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as folder:
        bundle=Path(folder)/'source.bundle'
        subprocess.run(['git','bundle','create',str(bundle),'--branches','--tags'],cwd=ROOT,check=True)
        subprocess.run(['git','bundle','verify',str(bundle)],cwd=ROOT,check=True,capture_output=True)
        with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as archive:
            archive.write(bundle,'SonMap-source.bundle')
            archive.writestr('bundle.sha256',hashlib.sha256(bundle.read_bytes()).hexdigest())
            archive.write(ROOT/'installer/workspace.cmd','Bat_dau_lam_viec.cmd')
            archive.write(ROOT/'installer/workspace.ps1','Chuan_bi_workspace.ps1')
            archive.writestr('HUONG_DAN.txt','Install Git for Windows if missing. Extract all files, run Bat_dau_lam_viec.cmd. Source goes to %USERPROFILE%/SonMap-Dev. Open Mo_Codex_laptop.cmd in VS Code with the official OpenAI Codex extension to run an assistant locally; this cloud chat does not gain laptop access automatically. Run Lam_viec_laptop.cmd. Save code with Gui_len_GitHub.cmd; authenticate locally, never send tokens in chat. Private DGN/MDB/assets/runtime are excluded from sync.\n')
    return destination


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True)
    print(build_workspace(parser.parse_args().output))
