"""Twenty unchanged business cases on the full dated-target composition."""
from contextlib import contextmanager
from pathlib import Path
from hashlib import sha256
import ast,inspect,importlib.util
import cp7_ow11_model_target_consumer_cases as target
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('retained_full_finance_model_business',ROOT/'current-finance-model-qualification/cases.py')
previous=importlib.util.module_from_spec(s);s.loader.exec_module(previous)
IDS=(*previous.IDS,*target.IDS['native'][1:])
assert len(IDS)==len(set(IDS))==20
STATE=CHECKER=None
SETUP_ADMISSIONS=[]

def source_binding():
    p=Path(target.__file__);text=p.read_text();tree=ast.parse(text)
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='cases')
    body=inspect.getsource(target.cases).strip();assert body==ast.get_source_segment(text,node).strip()
    return dict(retained_finance_policy_v2=previous.source_binding(),target=dict(path='scripts/'+p.name,
        file_sha256=sha256(p.read_bytes()).hexdigest(),cases_body_sha256=sha256(body.encode()).hexdigest()),
        excluded_target_catalog_anchor=target.IDS['native'][0],original_business_assertions_unchanged=True,
        baseline_fix_predecessor_regression_is_separate_component_proof=True)

def setup_target(cur):
    assert STATE is not None and callable(CHECKER)
    target.plan.b.api.admin(cur);proof=CHECKER(cur)
    SETUP_ADMISSIONS.append(dict(stage='DATED_MODEL_TARGET',actual_full_current_verification=proof))
    return dict(current=STATE['stages'][1]['state'],fresh=STATE['stages'][0]['state'],
        policy=STATE['predecessor']['stages'][0]['state'],model=STATE['predecessor']['stages'][1]['state'])

@contextmanager
def installed(state,checker):
    global STATE,CHECKER
    old=target.install,STATE,CHECKER;STATE,CHECKER=state,checker;target.install=setup_target
    try:
        with previous.installed(state['predecessor'],checker):yield source_binding()
    finally:target.install,STATE,CHECKER=old

def cases(cur,today):
    assert target.install is setup_target
    result=previous.cases(cur,today)+target.cases(cur,today)[1:]
    assert tuple(k for k,_ in result)==IDS
    return result
