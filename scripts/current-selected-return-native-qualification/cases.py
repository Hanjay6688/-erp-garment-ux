"""15 unchanged finance/model cases and five target cases with the full used guard."""
from contextlib import contextmanager
from pathlib import Path
from hashlib import sha256
import ast,inspect,importlib.util
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


previous=module('retained_full_finance_model_business',ROOT/'current-finance-model-qualification/cases.py')
target=module('selected_return_target_business_cases',HERE/'target_cases.py')
IDS=(*previous.IDS,*target.IDS)
SETUP_ADMISSIONS=target.SETUP_ADMISSIONS
assert len(IDS)==len(set(IDS))==20


def source_binding():
    actual=ast.parse(inspect.getsource(target.cases))
    original=ast.parse(inspect.getsource(target.original.cases))
    root=original.body[0]
    root.body=[n for n in root.body if not(isinstance(n,ast.FunctionDef)and n.name=='catalog')]
    changes={'rollback_calls':0,'refusal_constants':0,'case_list':0,'case_tuple':0}
    class Allowed(ast.NodeTransformer):
        def visit_Call(self,n):
            n=self.generic_visit(n)
            if isinstance(n.func,ast.Attribute)and isinstance(n.func.value,ast.Name)and n.func.value.id=='stage'and n.func.attr=='rollback_preuse':
                n.func=ast.Name(id='rollback_full',ctx=ast.Load());changes['rollback_calls']+=1
            return n
        def visit_Constant(self,n):
            if n.value=='MODEL_TARGET_AFTER_USE_REQUIRES_COMPOSED_BACKUP_RESTORE':
                changes['refusal_constants']+=1
                return ast.Constant(value='CURRENT_SELECTED_RETURN_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE')
            return n
        def visit_Subscript(self,n):
            if isinstance(n.value,ast.Name)and n.value.id=='IDS'and isinstance(n.slice,ast.Constant)and n.slice.value=='native':
                changes['case_list']+=1;return ast.Name(id='IDS',ctx=ast.Load())
            return self.generic_visit(n)
        def visit_Tuple(self,n):
            if n.elts and isinstance(n.elts[0],ast.Name)and n.elts[0].id=='catalog':
                changes['case_tuple']+=1;n.elts=n.elts[1:]
            return self.generic_visit(n)
    original=Allowed().visit(original)
    assert changes==dict(rollback_calls=3,refusal_constants=3,case_list=1,case_tuple=1)
    assert ast.dump(actual,include_attributes=False)==ast.dump(original,include_attributes=False),'UNDECLARED_BUSINESS_ASSERTION_CHANGE'
    for name in ('call','capture','read'):
        assert inspect.getsource(getattr(target,name)).strip()==inspect.getsource(getattr(target.original,name)).strip(),name
    p=Path(target.original.__file__)
    return dict(retained_finance_policy_v2=previous.source_binding(),retained_case_ids=list(previous.IDS),
        target_case_ids=list(target.IDS),B_original_sha256=sha256(p.read_bytes()).hexdigest(),explicit_AST_changes=changes,
        target_business_assertions_and_limits_unchanged=True,full_A_setup_and_real_full_guard=True,
        finance_model_state_from_selected_return_target_predecessor=True,production_go=False)


@contextmanager
def installed(state,checker):
    old=target.STATE,target.CHECKER
    target.STATE,target.CHECKER=state,checker
    try:
        # selected return -> dated target -> full finance/model state
        with previous.installed(state['predecessor']['predecessor'],checker):yield source_binding()
    finally:target.STATE,target.CHECKER=old


def cases(cur,today):
    result=previous.cases(cur,today)+target.cases(cur,today)
    assert tuple(key for key,_ in result)==IDS
    return result
