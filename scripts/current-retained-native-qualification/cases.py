"""Run the 153 unique Native controls behind the historical 180 Native entries.

All six historical factories remain unchanged. Identical inherited baseline
closures are admitted by module, qualified name, line and source bytes before
one execution is credited. This does not cover 106 race/HTTP/browser entries.
"""
from hashlib import sha256
from datetime import date,timedelta
import importlib,inspect,json,traceback
from pathlib import Path
import cp7_retained_cp6_fixture as fixture
import cp7_wa_forward_cases as wa

REPO=Path(__file__).resolve().parents[2]
INVENTORY=json.loads((REPO/'docs/cp7/d17-14/ow15/retained-286-mode-inventory.json').read_text())
OVERLAP=json.loads((REPO/'docs/cp7/d17-14/ow15/retained-286-native-overlap.json').read_text())
MODULES={s['module']:importlib.import_module(s['module'])for s in INVENTORY['suites']}
IDS=tuple(OVERLAP['unique_controls'])
assert len(IDS)==153 and OVERLAP['duplicate_entries']==27
FIXTURE={}


def identity(fn):
    return dict(module=fn.__module__,qualname=fn.__qualname__,line=fn.__code__.co_firstlineno,
        source_sha256=sha256(inspect.getsource(fn).encode()).hexdigest())


def enumerate_cases(cur,today):
    found={};duplicates=[]
    for suite in INVENTORY['suites']:
        name=suite['module'];rows=MODULES[name].cases(cur,today)
        assert [key for key,_ in rows]==suite['native_ids'],name
        for key,fn in rows:
            actual=identity(fn);expected=OVERLAP['unique_controls'][key]
            assert actual==expected['callable'],('RETAINED_CALLABLE_CHANGED',key)
            if key in found:
                duplicates.append(dict(case_id=key,first_suite=expected['suite'],repeat_suite=name,callable=actual))
            else:
                assert name==expected['suite'];found[key]=(name,fn)
    assert tuple(found)==IDS and duplicates==OVERLAP['duplicate_callable_proofs']
    return found


def cases(cur,today):
    # Native SQL test queues are rolled back by the strict per-case harness.
    # Frozen setup changes transport to this fake local host before any send.
    assert wa.FAKE=='http://fake-callmebot:8080/whatsapp.php'
    assert wa.PHONE=='+620000000000'and wa.KEY.startswith('FAKEKEY-')
    fixture.prepare(cur,today,current=True,closed_through=today-timedelta(days=8),evidence=FIXTURE)
    result=[]
    for key,(suite,fn)in enumerate_cases(cur,today).items():
        def run(operation=fn,source=suite,case_id=key):
            try:
                row=operation()
                return dict(status=row.get('status'),original_result=row,retained_suite=source,retained_id=case_id)
            except Exception as error:
                # Preserve complete original failure without truncating its
                # financial report; the outer strict runner rolls back its savepoint.
                return dict(status='INCOMPLETE',error=str(error),traceback=traceback.format_exc(),
                    retained_suite=source,retained_id=case_id)
        result.append((key,run))
    return result
