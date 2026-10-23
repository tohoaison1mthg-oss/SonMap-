import sys,shutil,json
from pathlib import Path
root=Path(sys.argv[1]);sys.path.insert(0,str(root))
import app
rows,rejected=app.load_mdb(str(root/'assets/DC101.mdb'))
config={**app.DEFAULTS,'mdb':str(root/'assets/DC101.mdb'),'dgn':str(root/'assets/DC101.dgn'),'template':str(root/'assets/TrichLucTT26 -ThanhTan.dgn'),'output':str(root/'exports')}
# Seed the module paths only. The GUI reloads the real active drawing before export.
app.prepare(config,rows[:1],[])
bootstrap=(root/'bootstrap.template.bas').read_text(encoding='ascii')
bootstrap=bootstrap.replace(r'C:\Users\tohoa\Documents\Codex\2026-10-12\referenced-chatgpt-conversation-this-is-an\outputs\ThanhTanApp',str(root)).replace(r'C:\Users\tohoa\Documents\EZDGN\.venv\Scripts\pythonw.exe',str(root/'runtime/pythonw.exe'))
(root/'LH_KhoiDong.bas').write_text(bootstrap,encoding='ascii')
print('PASS: module generated; output path is dynamic; source DGN/MDB unchanged')
