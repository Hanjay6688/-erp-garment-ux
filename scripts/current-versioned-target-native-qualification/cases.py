"""25 unchanged finance/history/model cases plus five explicit versioned cases."""
from contextlib import contextmanager
from pathlib import Path
from hashlib import sha256
import ast,inspect,importlib.util
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


previous=module('retained_full_scoped_model_cases',ROOT/'current-scoped-model-native-qualification/cases.py')
target=module('full_versioned_target_business_cases',HERE/'target_cases.py')
old_target_ids=tuple(previous.previous.previous.target.IDS['native'][1:])
retained_ids=tuple(x for x in previous.IDS if x not in old_target_ids)
IDS=(*retained_ids,*target.IDS)
assert len(retained_ids)==25 and len(IDS)==len(set(IDS))==30


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
            if n.value=='MODEL_TARGET_V2_AFTER_USE_REQUIRES_COMPOSED_BACKUP_RESTORE':
                changes['refusal_constants']+=1
                return ast.Constant(value='CURRENT_VERSIONED_TARGET_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE')
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
    return dict(retained_scoped_source=previous.source_binding(),retained_case_ids=list(retained_ids),
        omitted_obsolete_target_v1_business_ids=list(old_target_ids),versioned_case_ids=list(target.IDS),
        B_original_sha256=sha256(p.read_bytes()).hexdigest(),explicit_AST_changes=changes,
        target_business_assertions_and_limits_unchanged=True,full_A_setup_and_real_full_guard=True,
        full_A_runtime_qualified=False,production_go=False)


@contextmanager
def installed(state,checker):
    old=target.STATE,target.CHECKER
    target.STATE,target.CHECKER=state,checker
    try:
        with previous.installed(state['predecessor'],checker):yield source_binding()
    finally:target.STATE,target.CHECKER=old


def cases(cur,today):
    result=[(key,case)for key,case in previous.cases(cur,today)if key not in old_target_ids]+target.cases(cur,today)
    assert tuple(key for key,_ in result)==IDS
    return result
