"""Read and focus on V8i's UI thread. CAD writes stay in the checked workflow."""
import hashlib
import json
import threading
import time
import uuid
from pathlib import Path

ROOT=Path(__file__).resolve().parent
lock=threading.Lock()
directory=None


def request(action,source,**values):
    global directory
    from topology_workflow import powershell
    with lock:
        if directory is None:
            identity=hashlib.sha256(str(ROOT.resolve()).casefold().encode('utf-8')+b''.join((ROOT/name).read_bytes() for name in ('cad_bridge.cs','cad_clean.cs','dgn_interop.ps1'))).hexdigest()[:12]
            directory=ROOT/'data'/'cad-bridge'/identity
            directory.mkdir(parents=True,exist_ok=True)
        try:
            # Verify the owning V8i process as well, including after V8i restarts.
            powershell('dgn_bridge.ps1','-Directory',directory)
            deadline=time.monotonic()+15
            while not (directory/'ready.json').exists():
                if time.monotonic()>deadline:raise RuntimeError('V8i chưa nạp cầu nối SonMap. Khởi động lại V8i rồi thử lại.')
                time.sleep(.04)
        except Exception:
            directory=None
            raise
        rid=uuid.uuid4().hex
        if action=='focus':
            import ctypes
            ready=json.loads((directory/'ready.json').read_text(encoding='utf-8-sig'))
            ctypes.windll.user32.AllowSetForegroundWindow(int(ready['pid']))
        payload=dict(id=rid,action=action,source=str(Path(source).resolve()),model=None)
        payload.update(values)
        temporary=directory/'request.tmp'
        temporary.write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8')
        response=directory/'response.json'
        if response.exists():response.unlink()
        temporary.replace(directory/'request.json')
        deadline=time.monotonic()+30
        while not response.exists():
            if time.monotonic()>deadline:
                pending=directory/'request.json'
                if pending.exists():pending.unlink()
                raise RuntimeError('V8i chưa trả kết quả. Đóng hộp thoại đang chặn thao tác rồi thử lại.')
            time.sleep(.02)
        result=json.loads(response.read_text(encoding='utf-8-sig'))
        response.unlink()
        if result['id']!=rid:raise RuntimeError('Kết quả V8i không khớp yêu cầu.')
        if not result['ok']:
            error=RuntimeError(result['result']);error.rescue_required=bool(result.get('rescue_required'))
            raise error
        return result['result']
