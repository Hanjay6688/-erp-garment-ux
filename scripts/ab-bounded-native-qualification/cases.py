"""Twelve actual integration controls; retained five finance and six bounded.

Only the bounded provider's declared installer is the integrator adapter.
Its assertions, expected data, case IDs and budgets are unchanged.
"""
from pathlib import Path
import importlib.util,json,uuid
HERE=Path(__file__).resolve().parent

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

finance=load('ab_bounded_retained_finance',HERE.parent/'finance-bridge-chain-qualification/cases.py')
bounded=load('ab_bounded_retained_bounded',HERE/'bounded_cases.py')
EXTRA='OW12_AB_BOUNDED_FINANCE_METHOD_ISOLATION'
IDS=(*finance.IDS,*bounded.IDS['native'],EXTRA)
STATE=None

def cases(cur,today):
    bounded.STAGE_STATE=STATE['stages'][-1]['state']
    def method_isolation():
        finance.setup(cur,today)
        key=uuid.uuid4();job=finance.request(cur,today,key)
        sidecar=finance.sidecar(job,key,'RUNNING');cid=sidecar['capture']['capture_id']
        original=finance.stored_capture(cur,cid)
        plan=bounded.plan
        plan.refused(cur,lambda:bounded.request(cur,today,key),'CP7_ANALYSIS_REQUEST_CHANGED')
        q=dict(plan.staged.query(today),finance_mode='STAGED')
        plan.refused(cur,lambda:bounded.request(cur,today,uuid.uuid4(),q=q),'CP7_WIP_FIELDS')
        other=uuid.uuid4();bounded.request(cur,today,other)
        plan.refused(cur,lambda:finance.request(cur,today,other),'CP7_ANALYSIS_REQUEST_CHANGED')
        assert finance.stored_capture(cur,cid)==original
        assert finance.sidecar(finance.request(cur,today,key),key,'RUNNING')==sidecar
        return dict(status='PASS',legacy_finance_UUID_not_bounded=True,
            bounded_UUID_not_legacy_finance=True,bounded_rejects_finance_mode=True,
            original_capture_unchanged=True,legacy_finance_exact_replay=True)
    return [*finance.cases(cur,today),*bounded.cases(cur,today),(EXTRA,method_isolation)]
