"""Whole retained controls, one explicit report-count substitution."""
from pathlib import Path
from hashlib import sha256
_path=Path(__file__).resolve().parents[2]/"scripts/current-sku-pair-concurrency-qualification/controls.py"
_raw=_path.read_bytes()
assert sha256(_raw).hexdigest()=='4c92e7ffce75d2257823470c0f6bc40d83425b003e6f9b556a92212849efd969'
_before='actual_Native_session_permission_waits=6, actual_Native_cases=0,'
_after='actual_Native_session_permission_waits=7, actual_Native_nonblocking_busy_cases=1, actual_Native_cases=0,'
assert _raw.decode().count(_before)==1
_text=_raw.decode().replace(_before,_after,1)
assert _text.replace(_after,_before,1).encode()==_raw
exec(compile(_text,str(_path),"exec"),globals())
