"""Finance/history/model, versioned target and selected-return business controls."""
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
history_replay=module('full_versioned_history_replay',HERE/'history_replay.py')
scoped_model_replay=module('full_versioned_scoped_model_replay',HERE/'scoped_model_replay.py')
selected_contract=module('full_versioned_selected_contract_cases',ROOT/'current-cp6-contract-qualification/cases.py')
private=module('full_frozen_private_business_cases',HERE/'private_cases.py')
finance=module('full_frozen_finance_business_cases',HERE/'finance_cases.py')
SELECTED_FIXTURES={}
old_target_ids=tuple(previous.previous.previous.target.IDS['native'][1:])
retained_ids=tuple(x for x in previous.IDS if x not in old_target_ids)
RETAINED_IDS=(*retained_ids,*target.IDS,*selected_contract.IDS)
IDS=(*RETAINED_IDS,*private.IDS,*finance.IDS)
assert len(retained_ids)==25 and len(selected_contract.IDS)==6 and len(RETAINED_IDS)==36 and len(IDS)==len(set(IDS))==45


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
                return ast.Constant(value='CURRENT_FROZEN_FINANCE_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE')
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
        history_replay_guard=history_replay.source_binding(),scoped_model_replay_guard=scoped_model_replay.source_binding(),
        unchanged_complete_retained_case_bodies=23,
        selected_contract_case_ids=list(selected_contract.IDS),selected_contract_file_sha256=sha256(Path(selected_contract.__file__).read_bytes()).hexdigest(),
        selected_contract_business_source_unchanged=True,
        private_business_source=private.source_binding(),finance_business_source=finance.source_binding(),full_A_runtime_qualified=False,production_go=False)


@contextmanager
def installed(state,checker):
    old=target.STATE,target.CHECKER
    old_history=history_replay.STATE,history_replay.CHECKER
    old_model=scoped_model_replay.STATE,scoped_model_replay.CHECKER
    scoped_model_replay.STATE,scoped_model_replay.CHECKER=state,checker
    history_replay.STATE,history_replay.CHECKER=state,checker
    target.STATE,target.CHECKER=state,checker
    try:
        with previous.installed(state['predecessor']['predecessor']['predecessor']['predecessor'],checker), private.installed(state,checker):yield source_binding()
    finally:
        target.STATE,target.CHECKER=old
        history_replay.STATE,history_replay.CHECKER=old_history
        scoped_model_replay.STATE,scoped_model_replay.CHECKER=old_model


def cases(cur,today):
    result=[(key,case)for key,case in previous.cases(cur,today)if key not in old_target_ids]+target.cases(cur,today)
    replacement=dict(history_replay.cases(cur,today)+scoped_model_replay.cases(cur,today))
    assert set(replacement)=={history_replay.ID,scoped_model_replay.ID}
    result=[(key,replacement.get(key,case))for key,case in result]
    def selected_case(name):
        def run():
            assert target.STATE is not None and callable(target.CHECKER)
            target.CHECKER(cur)
            # Prepare the retained physical fixture only inside its own case,
            # never before unrelated finance/model cases are selected.
            operations=dict(selected_contract.cases(cur,today,current=True,evidence=SELECTED_FIXTURES.setdefault(name,{})))
            return operations[name]()
        return run
    result.extend((key,selected_case(key))for key in selected_contract.IDS)
    assert tuple(key for key,_ in result)==RETAINED_IDS
    result.extend(private.cases(cur,today))
    result.extend(finance.cases(cur,today))
    assert tuple(key for key,_ in result)==IDS
    return result
