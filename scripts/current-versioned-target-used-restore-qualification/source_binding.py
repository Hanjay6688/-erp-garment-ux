"""Check retained whole fixture AST and every predecessor restore assertion."""
from collections import Counter
from hashlib import sha256
from pathlib import Path
import ast,importlib.util,json

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'current-scoped-model-used-restore-qualification'
UNCHANGED=('fixture.py','opening_fixture.py','finance_fixture.py','model_fixture.py','history_fixture.py','scoped_model_fixture.py')
PROTOCOL={'cp7.native-baseline.v3':'cp7.native-baseline.v4',
          'cp7.target-demand-provenance.v2':'cp7.target-demand-provenance.v3'}


class TargetProtocol(ast.NodeTransformer):
    def visit_Import(self,node):
        for alias in node.names:
            if alias.name=='cp7_ow11_model_target_consumer_cases':
                alias.name='cp7_ow11_model_target_consumer_v2_cases'
        return node

    def visit_Constant(self,node):
        if isinstance(node.value,str):node.value=PROTOCOL.get(node.value,node.value)
        return node

    def visit_keyword(self,node):
        node.arg={'actual_Native_baseline_v3':'actual_Native_baseline_v4',
                  'actual_provenance_v2':'actual_provenance_v3'}.get(node.arg,node.arg)
        return self.generic_visit(node)


def verify(target_text=None,probe_text=None):
    def module(name,path):
        spec=importlib.util.spec_from_file_location(name,path)
        value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
    helper=module('combined_restore_selected_refusal_guard',HERE.parent/'current-selected-return-used-restore-qualification/selected_refusal.py')
    business=module('combined_restore_retained_refusal_business',HERE.parent/'draft-return-isolation-qualification/cases.py')
    refusal=helper.source_binding(business)
    unchanged={}
    for name in UNCHANGED:
        raw=(HERE/name).read_bytes()
        assert raw==(OLD/name).read_bytes(),('RESTORE_FIXTURE_CHANGED',name)
        unchanged[name]=sha256(raw).hexdigest()
    expected=TargetProtocol().visit(ast.parse((OLD/'target_fixture.py').read_text()))
    actual=ast.parse((HERE/'target_fixture.py').read_text()if target_text is None else target_text)
    assert ast.dump(actual)==ast.dump(expected),'TARGET_RESTORE_BUSINESS_OR_PROTOCOL_CHANGED'
    previous=ast.parse((OLD/'probe.py').read_text())
    current=ast.parse((HERE/'probe.py').read_text()if probe_text is None else probe_text)
    assertions=lambda tree:Counter(ast.dump(n)for n in ast.walk(tree)if isinstance(n,ast.Assert))
    before,after=assertions(previous),assertions(current)
    assert not(before-after),'RETAINED_RESTORE_ASSERTION_REMOVED_OR_CHANGED'
    steps=lambda tree:ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='STEPS'for t in n.targets)))
    assert steps(previous)==steps(current)and len(steps(current))==8
    return dict(unchanged_fixture_sha256=unchanged,target_entire_AST_equal_after_exact_provider_and_protocol_changes=True,
        retained_probe_assertions=sum(before.values()),new_probe_assertions=sum(after.values())-sum(before.values()),
        required_steps=8,retained_refusal_business_source=refusal,production_go=False,Native_credit=False)


if __name__=='__main__':print(json.dumps(verify(),indent=2))
