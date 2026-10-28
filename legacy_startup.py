"""Route legacy V8i app.py entry points to the installed SonMap, preserving rollback."""
import argparse
import hashlib
import json
from pathlib import Path
import uuid

MARKER = '# SonMap installed-version redirect\n'


def redirect_header():
    # This header runs under the legacy Python too; keep it stdlib-only.
    return MARKER + '''import os as _sm_os, subprocess as _sm_subprocess
from pathlib import Path as _SmPath
_sm_root = _SmPath(_sm_os.environ.get('LOCALAPPDATA', '')) / 'SonMapPlus' / 'App'
if (_sm_root / 'VERSION').is_file() and (_sm_root / 'launch.py').is_file():
    _sm_version = tuple(int(v) for v in (_sm_root / 'VERSION').read_text(encoding='utf-8-sig').strip().split('.'))
    _sm_python = _sm_root / '.venv-topology' / 'Scripts' / 'pythonw.exe'
    if _sm_version > (10, 3) and _sm_python.is_file() and _sm_root.resolve() != _SmPath(__file__).resolve().parent:
        _sm_subprocess.Popen([str(_sm_python), str(_sm_root / 'launch.py')], cwd=str(_sm_root), creationflags=getattr(_sm_subprocess, 'CREATE_NO_WINDOW', 0))
        raise SystemExit(0)
''' + '# End SonMap installed-version redirect\n'


def snapshot(root, content):
    folder = root / 'SonMap_startup_backups' / uuid.uuid4().hex
    folder.mkdir(parents=True)
    (folder / 'app.py').write_bytes(content)
    (folder / 'receipt.json').write_text(json.dumps({'sha256': hashlib.sha256(content).hexdigest()}), encoding='utf-8')
    return folder


def repair(root):
    root = Path(root)
    target = root / 'app.py'
    if not target.is_file():
        return None
    original = target.read_bytes()
    text = original.decode('utf-8-sig')
    if text.startswith(MARKER):
        return None
    # Restrict the compatibility repair to the known old application.
    if "win.title('SonMap+ V10.3')" not in text:
        return None
    replacement = (redirect_header() + text).encode('utf-8-sig')
    compile(replacement, str(target), 'exec')
    backup = snapshot(root, original)
    temporary = root / ('app-' + uuid.uuid4().hex + '.tmp')
    temporary.write_bytes(replacement)
    temporary.replace(target)
    return backup


def restore(root, backup):
    root, backup = Path(root).resolve(), Path(backup).resolve()
    if backup.parent != root / 'SonMap_startup_backups':
        raise ValueError('Choose a startup backup inside the legacy application.')
    content = (backup / 'app.py').read_bytes()
    receipt = json.loads((backup / 'receipt.json').read_text(encoding='utf-8'))
    if hashlib.sha256(content).hexdigest() != receipt['sha256']:
        raise ValueError('Startup backup checksum mismatch.')
    undo = snapshot(root, (root / 'app.py').read_bytes())
    temporary = root / ('app-' + uuid.uuid4().hex + '.tmp')
    temporary.write_bytes(content)
    temporary.replace(root / 'app.py')
    return undo


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--legacy-root', type=Path, required=True)
    parser.add_argument('--restore', type=Path)
    args = parser.parse_args()
    result = restore(args.legacy_root, args.restore) if args.restore else repair(args.legacy_root)
    print('Startup backup: ' + str(result) if result else 'No legacy startup change required.')
