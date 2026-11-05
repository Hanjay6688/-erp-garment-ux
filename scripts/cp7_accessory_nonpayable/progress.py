"""Small best-effort phase receipts; never a financial success oracle.

No timer, worker, file, database connection or payload logging is introduced.
Monotonic durations do not participate in the genuine business-day policy.
"""
from contextlib import contextmanager
import json,os,re,time

PHASES=frozenset(('WHOLE_PACKAGE','COMPLETE_STATE_PREREQUISITE','NATIVE_GROUP','NATIVE_CASE','COMMITTED_PREREQUISITE',
    'HTTP_GROUP','SESSION_GROUP','BROWSER_GROUP'))


def emit(phase,case,event,started,error_type=None):
    value=dict(afui_progress=event,phase=phase,case=case,pid=os.getpid(),
        monotonic_seconds=round(time.monotonic(),3),elapsed_seconds=round(time.monotonic()-started,3),
        diagnostic_only=True)
    if error_type is not None:value['error_type']=error_type
    # A closed log stream must not replace the original transaction failure
    # or prevent the unchanged package from restoring its database boundary.
    try:print(json.dumps(value,separators=(',',':')),flush=True)
    except Exception:pass


@contextmanager
def phase(name,case=None):
    if name not in PHASES or(case is not None and(type(case)is not str or re.fullmatch(r'[A-Z][A-Z0-9_]{0,159}',case)is None)):
        raise ValueError('NONPAYABLE_FIXED_BOUNDED_PROGRESS_ID_REQUIRED')
    started=time.monotonic();emit(name,case,'ENTER',started)
    try:yield
    except BaseException as error:
        emit(name,case,'RAISED',started,type(error).__name__);raise
    else:emit(name,case,'RETURNED',started)
