"""Small stdlib-only report used before creating SonMap's Python environment."""
import importlib
import json
import struct
import sys


def inspect_python():
    version='.'.join(map(str,sys.version_info[:3]))
    result={'executable':sys.executable,'version':version,'bits':struct.calcsize('P')*8,'compatible':False,'reason':''}
    if sys.implementation.name!='cpython' or sys.version_info[:2]!=(3,12):
        result['reason']='SonMap requires CPython 3.12; found '+version
    elif result['bits']!=64:
        result['reason']='SonMap requires 64-bit Python'
    else:
        try:
            for module in ('tkinter','venv','ensurepip'):importlib.import_module(module)
        except Exception as exc:result['reason']='Required component unavailable: '+str(exc)
        else:result.update(compatible=True,reason='Ready')
    return result


if __name__=='__main__':
    report=inspect_python()
    print(json.dumps(report,ensure_ascii=True))
    raise SystemExit(0 if report['compatible'] else 1)
