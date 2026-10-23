"""Launch with a persistent error log instead of failing invisibly."""
import runpy
import traceback
from pathlib import Path

root = Path(__file__).resolve().parent
try:
    runpy.run_path(str(root / 'app.py'), run_name='__main__')
except Exception:
    error = traceback.format_exc()
    (root / 'data').mkdir(exist_ok=True)
    (root / 'data/startup-error.log').write_text(error, encoding='utf-8')
    print(error)
    raise SystemExit(1)
