"""Unchanged B policy/v2/dated-target Auth and races, admitted on full A composition."""
from pathlib import Path
from hashlib import sha256
import ast,inspect
import cp7_ow11_model_policy_transport_cases as policy
import cp7_ow11_model_evaluation_v2_transport_cases as evaluation

import importlib.util
from contextlib import contextmanager
_spec=importlib.util.spec_from_file_location('versioned_full_transport_target',Path(__file__).with_name('target_cases.py'))
target=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(target)

MODULES=dict(policy=policy,evaluation=evaluation,target=target)
GROUPS={name+'_'+kind:list(module.IDS[kind])for name,module in MODULES.items()for kind in('http','races')}
IDS=tuple(key for group in GROUPS.values()for key in group)
assert len(IDS)==len(set(IDS))==28

def source_binding():
    result={}
    for name,module in MODULES.items():
        if name=='target':continue
        p=Path(module.__file__);text=p.read_text();tree=ast.parse(text);bodies={}
        for factory in('races','http_cases'):
            node=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name==factory)
            actual=inspect.getsource(getattr(module,factory)).strip()
            assert actual==ast.get_source_segment(text,node).strip(),('RETAINED_MODEL_TRANSPORT_BODY_CHANGED',name,factory)
            bodies[factory]=sha256(actual.encode()).hexdigest()
        result[name]=dict(path='scripts/'+p.name,file_sha256=sha256(p.read_bytes()).hexdigest(),factory_body_sha256=bodies)
    expected=ast.parse(inspect.getsource(target.original.http_cases))
    changed=0
    class ActualVerifier(ast.NodeTransformer):
        def visit_Call(self,node):
            nonlocal changed
            node=self.generic_visit(node)
            if isinstance(node.func,ast.Attribute)and isinstance(node.func.value,ast.Name)and node.func.value.id=='stage'and node.func.attr=='verify':
                changed+=1;node.func=ast.Name(id='verify_full',ctx=ast.Load())
            return node
    expected=ActualVerifier().visit(expected)
    assert changed==1 and ast.dump(expected)==ast.dump(ast.parse(inspect.getsource(target.http_cases))),'VERSIONED_HTTP_BUSINESS_ASSERTION_CHANGED'
    assert inspect.getsource(target.races).strip()==inspect.getsource(target.original.races).strip(),'VERSIONED_RACE_BUSINESS_ASSERTION_CHANGED'
    p=Path(target.original.__file__)
    result['target']=dict(path='scripts/'+p.name,file_sha256=sha256(p.read_bytes()).hexdigest(),
        races_entire_body_unchanged=True,http_AST_equal_except_one_full_verifier=True,full_verifier_calls_changed=1)
    return dict(retained=result,excluded_component_catalog_anchors=[m.IDS['native'][0]for m in MODULES.values()],
        retained_18_and_versioned_10_business_assertions_unchanged=True,only_setup_hooks=['policy.native.install','evaluation.native.install','target.install','target.http_actual_full_verify'])


@contextmanager
def installed(native_business,state,checker):
    old=target.STATE,target.CHECKER
    target.STATE,target.CHECKER=state,checker
    try:
        with native_business.installed(state,checker):yield source_binding()
    finally:target.STATE,target.CHECKER=old
