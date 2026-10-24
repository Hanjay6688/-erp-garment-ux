"""Fifteen unchanged business cases on the installed full finance/model chain.

The two original stage-install/catalog cases are not relabelled as covered.
The outer qualifier proves the composed preuse inverse separately. Only two
installation setup hooks are temporarily replaced; all case bodies and limits
remain byte-identical to their original source modules.
"""
from contextlib import contextmanager
from pathlib import Path
from hashlib import sha256
import ast,importlib.util,inspect
import cp7_ow11_model_policy_cases as policy
import cp7_ow11_model_evaluation_v2_cases as evaluation

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('retained_current_bounded_finance_cases',ROOT/'current-bounded-finance-native-qualification/cases.py')
finance=importlib.util.module_from_spec(spec);spec.loader.exec_module(finance)
IDS=(*finance.IDS,*policy.IDS['native'][1:],*evaluation.IDS['native'][1:])
STATE=None
CHECKER=None
SETUP_ADMISSIONS=[]


def source_binding():
    result={}
    for name,module in(('finance',finance),('policy',policy),('evaluation_v2',evaluation)):
        p=Path(module.__file__);text=p.read_text();tree=ast.parse(text)
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='cases')
        actual=inspect.getsource(module.cases).strip()
        assert actual==ast.get_source_segment(text,node).strip(),('MODEL_RETAINED_CASE_BODY_CHANGED',name)
        result[name]=dict(path='scripts/'+str(p.relative_to(ROOT)),file_sha256=sha256(p.read_bytes()).hexdigest(),cases_body_sha256=sha256(actual.encode()).hexdigest())
    return dict(retained=result,only_replaced_setup_hooks=['policy.install','evaluation.install'],
        excluded_original_catalog_case_ids=[policy.IDS['native'][0],evaluation.IDS['native'][0]],
        original_business_assertions_unchanged=True)


def setup_policy(cur):
    assert STATE is not None and callable(CHECKER),'CURRENT_FINANCE_MODEL_INSTALLATION_REQUIRED'
    policy.plan.b.api.admin(cur)
    proof=CHECKER(cur)
    SETUP_ADMISSIONS.append(dict(stage='MODEL_POLICY',actual_full_current_verification=proof))
    return STATE['stages'][0]['state']


def setup_evaluation(cur):
    ps=setup_policy(cur)
    return ps,STATE['stages'][1]['state']


@contextmanager
def installed(state,checker):
    global STATE,CHECKER
    previous=policy.install,evaluation.install,STATE,CHECKER
    STATE,CHECKER=state,checker
    policy.install,evaluation.install=setup_policy,setup_evaluation
    try:yield source_binding()
    finally:policy.install,evaluation.install,STATE,CHECKER=previous


def cases(cur,today):
    assert policy.install is setup_policy and evaluation.install is setup_evaluation
    groups=finance.cases(cur,today)+policy.cases(cur,today)[1:]+evaluation.cases(cur,today)[1:]
    assert tuple(k for k,_ in groups)==IDS and len(IDS)==15
    return groups
