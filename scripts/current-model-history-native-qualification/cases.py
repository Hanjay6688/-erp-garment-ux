"""Twenty retained current cases plus five unchanged immutable-history cases."""
from contextlib import contextmanager
from pathlib import Path
from hashlib import sha256
import ast, inspect, importlib.util
import cp7_ow11_model_history_runtime_cases as history

ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('retained_current_target_business',ROOT/'current-model-target-native-qualification/cases.py')
previous=importlib.util.module_from_spec(s);s.loader.exec_module(previous)
IDS=(*previous.IDS,*history.IDS['native'][1:])
assert len(IDS)==len(set(IDS))==25
STATE=CHECKER=None
SETUP_ADMISSIONS=[]


def source_binding():
    p=Path(history.__file__);text=p.read_text();tree=ast.parse(text)
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='cases')
    body=inspect.getsource(history.cases).strip();assert body==ast.get_source_segment(text,node).strip()
    return dict(retained_current_target=previous.source_binding(),history=dict(path='scripts/'+p.name,
        file_sha256=sha256(p.read_bytes()).hexdigest(),cases_body_sha256=sha256(body.encode()).hexdigest()),
        excluded_history_catalog_anchor=history.IDS['native'][0],original_business_assertions_unchanged=True,
        full_composed_preuse_inverse_is_separate=True)


def setup_history(cur):
    assert STATE is not None and callable(CHECKER)
    history.plan.b.api.admin(cur)
    proof=CHECKER(cur)
    SETUP_ADMISSIONS.append(dict(stage='IMMUTABLE_SCOPED_HISTORY',actual_full_current_verification=proof))
    return STATE['stages'][0]['state'],STATE['stages'][1]['state']


@contextmanager
def installed(state,checker):
    global STATE,CHECKER
    old=history.install,STATE,CHECKER
    STATE,CHECKER=state,checker;history.install=setup_history
    try:
        with previous.installed(state['predecessor'],checker):yield source_binding()
    finally:history.install,STATE,CHECKER=old


def cases(cur,today):
    assert history.install is setup_history
    result=previous.cases(cur,today)+history.cases(cur,today)[1:]
    assert tuple(k for k,_ in result)==IDS
    return result
