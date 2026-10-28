"""Twenty-five retained current cases plus five unchanged scoped-model cases."""
from contextlib import contextmanager
from pathlib import Path
from hashlib import sha256
import ast, inspect, importlib.util
import cp7_ow11_model_scoped_evaluation_cases as model

ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('retained_current_target_business',ROOT/'current-model-history-native-qualification/cases.py')
previous=importlib.util.module_from_spec(s);s.loader.exec_module(previous)
IDS=(*previous.IDS,*model.IDS['native'][1:])
assert len(IDS)==len(set(IDS))==30
s=importlib.util.spec_from_file_location('current_scoped_history_replay',Path(__file__).with_name('history_replay.py'))
history_replay=importlib.util.module_from_spec(s);s.loader.exec_module(history_replay)
STATE=CHECKER=None
SETUP_ADMISSIONS=[]


def source_binding():
    p=Path(model.__file__);text=p.read_text();tree=ast.parse(text)
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='cases')
    body=inspect.getsource(model.cases).strip();assert body==ast.get_source_segment(text,node).strip()
    return dict(retained_current_target=previous.source_binding(),scoped_model=dict(path='scripts/'+p.name,
        file_sha256=sha256(p.read_bytes()).hexdigest(),cases_body_sha256=sha256(body.encode()).hexdigest()),
        excluded_scoped_model_catalog_anchor=model.IDS['native'][0],original_business_assertions_unchanged=True,
        full_composed_preuse_inverse_is_separate=True,explicit_history_replay_guard=history_replay.source_binding())


def setup_model(cur):
    assert STATE is not None and callable(CHECKER)
    model.plan.b.api.admin(cur)
    proof=CHECKER(cur)
    SETUP_ADMISSIONS.append(dict(stage='IMMUTABLE_SCOPED_MODEL_V3',actual_full_current_verification=proof))
    # The catalog/inverse anchor is replaced by the complete composer probe.
    # Retained business cases only consume the current runtime state.
    return None,STATE['stages'][1]['state']


@contextmanager
def installed(state,checker):
    global STATE,CHECKER
    old=model.install,STATE,CHECKER
    old_history=history_replay.STATE,history_replay.CHECKER
    history_replay.STATE,history_replay.CHECKER=state,checker
    STATE,CHECKER=state,checker;model.install=setup_model
    try:
        with previous.installed(state['predecessor'],checker):yield source_binding()
    finally:
        model.install,STATE,CHECKER=old
        history_replay.STATE,history_replay.CHECKER=old_history


def cases(cur,today):
    assert model.install is setup_model
    result=previous.cases(cur,today)+model.cases(cur,today)[1:]
    replacement=dict(history_replay.cases(cur,today));assert set(replacement)=={history_replay.ID}
    result=[(key,replacement.get(key,case))for key,case in result]
    assert tuple(k for k,_ in result)==IDS
    return result
