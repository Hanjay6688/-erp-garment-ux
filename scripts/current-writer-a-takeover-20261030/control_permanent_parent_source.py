"""Actual qualified parent source admission without starting child ERP work."""
from pathlib import Path
from unittest.mock import patch
import argparse,json
import intake_permanent6 as target
from intake_common import GitBytes,exact,pin


def check(root,head,tree):
    with GitBytes(root,head,tree)as g:
        value=target.source(g)
        exact(value['own_paths'],57,'BOUND_PARENT_ADDS_ONLY_ONE_ORIGINAL_RECEIPT')
        exact(value['parent_root_acceptance_pending'],False,'ACTUAL_PARENT_ALREADY_ROOT_ACCEPTED')
        raw=g.read(target.NS+'JOIN37_ROOT_ACTUAL_INTAKE.json')
        financial=g.read(target.NS+'persistent_financial.py')
        class Changed:
            def __init__(self,mode):self.mode=mode
            def read(self,name):
                if name==target.NS+'JOIN37_ROOT_ACTUAL_INTAKE.json':
                    if self.mode=='missing':raise KeyError(name)
                    if self.mode=='edited':return raw+b' '
                if name==target.NS+'persistent_financial.py'and self.mode=='unbound':
                    before=('PARENT_RECEIPT='+repr(target.PARENT_RECEIPT)).encode()
                    exact(financial.count(before),1,'EXACT_CURRENT_PARENT_BINDING')
                    return financial.replace(before,b'PARENT_RECEIPT=None',1)
                return g.read(name)
        negatives=[]
        for mode in('missing','edited','unbound'):
            try:target.parent_receipt_source(Changed(mode))
            except(ValueError,KeyError):negatives.append(mode)
            else:raise AssertionError('PARENT_SOURCE_ACCEPTED:'+mode)
        with patch.object(target,'PARENT_RECEIPT',None):
            class Pending:
                def read(self,name):
                    if name!=target.NS+'persistent_financial.py':
                        raise AssertionError('PENDING_PARENT_READ_AN_UNQUALIFIED_RECEIPT')
                    before=('PARENT_RECEIPT='+repr(pin(raw))).encode()
                    return financial.replace(before,b'PARENT_RECEIPT=None',1)
            exact(target.parent_receipt_source(Pending()),None,'PENDING_REMAINS_CLOSED_WITHOUT_READING_ARCHIVE')
        for name in('HEAD','TREE','RUN','JOB'):
            exact(getattr(target,name),None,'CHILD_RUNTIME_IDENTITY_STILL_UNARMED:'+name)
        try:target.intake(None,None,None)
        except ValueError as error:
            if'ACTIVATED_EXACT_RUN_INTAKE_NOT_YET_PINNED'not in str(error):raise
            negatives.append('own_runtime_unarmed_before_archive')
        else:raise AssertionError('BOUND_PARENT_OPENED_OWN_UNQUALIFIED_RUNTIME_INTAKE')
    return dict(status='ROOT_PERMANENT_ACTUAL_PARENT_SOURCE_CONTROLS_PASS',head=head,tree=tree,
        source=value,positive=2,negative_controls=negatives,actual_ERP_cases=0,
        actual_SQL_executed=0,production_go=False,independent_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--head',required=True);p.add_argument('--tree',required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=check(a.source,a.head,a.tree)
    with a.output.open('x')as out:out.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],positive=result['positive'],
        negative=len(result['negative_controls']),actual_ERP_cases=0)))
