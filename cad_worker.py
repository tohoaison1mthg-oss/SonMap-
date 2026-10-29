"""Serialized, reusable PowerShell bridge. Never replay a failed CAD write."""
import atexit
import json
import os
import queue
import subprocess
import threading
import time
import uuid
from pathlib import Path


class CadWorker:
    def __init__(self, root):
        self.root = Path(root)
        self.lock = threading.Lock()
        self.process = None
        self.responses = None

    def _start(self):
        executable = Path(os.environ.get('WINDIR', r'C:\Windows')) / 'SysWOW64/WindowsPowerShell/v1.0/powershell.exe'
        self.process = subprocess.Popen(
            [str(executable), '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(self.root/'cad_worker.ps1')],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding='utf-8', errors='replace', bufsize=1, creationflags=0x08000000)
        responses = self.responses = queue.Queue()
        process = self.process
        def read():
            try:
                for line in process.stdout:
                    responses.put(line.lstrip('\ufeff'))
            finally:
                responses.put(None)
        threading.Thread(target=read, daemon=True).start()

    def close(self):
        with self.lock:
            self._close()

    def _close(self):
        process, self.process = self.process, None
        if process is None:
            return
        # Closing stdin lets the worker exit between requests. On a transport
        # failure, killing the bridge does not kill MicroStation itself.
        try:
            process.stdin.close()
            process.wait(timeout=2)
        except (OSError, subprocess.TimeoutExpired):
            process.kill()
            process.wait()
        finally:
            process.stdout.close()

    def run(self, script, arguments, timeout=300):
        with self.lock:
            if self.process is None or self.process.poll() is not None:
                self._close()
                self._start()
            request_id = uuid.uuid4().hex
            noise = []
            try:
                # UTF-8 without a BOM on each request (stdin is an existing stream).
                request = json.dumps(dict(id=request_id, script=script, arguments=list(map(str, arguments))), ensure_ascii=True)
                self.process.stdin.write(request+'\n')
                self.process.stdin.flush()
                deadline = time.monotonic()+timeout
                while True:
                    line = self.responses.get(timeout=max(.001, deadline-time.monotonic()))
                    if line is None:
                        raise RuntimeError('Cầu nối V8i đã dừng. Thao tác không được tự chạy lại.\n'+''.join(noise))
                    if not line.startswith('SONMAP_RESPONSE '):
                        noise.append(line)
                        continue
                    response = json.loads(line[len('SONMAP_RESPONSE '):])
                    if response['id'] != request_id:
                        raise RuntimeError('Cầu nối V8i trả kết quả không khớp yêu cầu.')
                    output = ''.join(noise)+response.get('output', '')
                    return bool(response['ok']), output.strip()
            except queue.Empty as exc:
                self._close()
                raise RuntimeError('Cầu nối V8i quá thời gian chờ. Kiểm tra bản vẽ trước khi thử lại; chưa xác nhận thành công.') from exc
            except Exception:
                self._close()
                raise


worker = CadWorker(Path(__file__).resolve().parent)
atexit.register(worker.close)
