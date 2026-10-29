"""Use the unchanged owning all22 queries for local additive boundary controls.

No imported installer, DB connection or source copying. The AST extraction
executes only its exact _acl/NAMESPACE/QUERIES definitions. A local catalog
capture is evidence of this model alone, never actual installed Native proof.
"""
from pathlib import Path
import ast,hashlib,json,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OWNER=ROOT/'scripts/cp7_ow04_restore_bundle.py'

def queries():
    env={}
    for node in ast.parse(OWNER.read_text()).body:
        selected=(isinstance(node,ast.FunctionDef)and node.name=='_acl')or(
            isinstance(node,ast.Assign)and any(isinstance(target,ast.Name)and target.id in('NAMESPACE','QUERIES')for target in node.targets))
        if selected:exec(compile(ast.Module(body=[node],type_ignores=[]),str(OWNER),'exec'),env)
    if len(env['QUERIES'])!=22:raise ValueError('LOCAL_ALL22_QUERY_SET_CHANGED')
    return env['QUERIES']

def identities(capture):
    before,after=capture['before'],capture['after']
    return dict(contract_version='cp7.attendance-period-choice-additive-identities.v1',
        classification='LOCAL_RENDERED_OWN_ADDITIVE_IDENTITIES_NOT_NATIVE_CAPTURE',
        query_owner=str(OWNER.relative_to(ROOT)),query_owner_sha256=hashlib.sha256(OWNER.read_bytes()).hexdigest(),
        objects={group:sorted(set(after[group])-set(before[group]))for group in queries()})

if __name__=='__main__':
    if len(sys.argv)==1:
        print(json.dumps(queries()));raise SystemExit(0)
    capture=json.loads(Path(sys.argv[2]).read_bytes())
    if sys.argv[1]=='--render-identities':
        print(json.dumps(identities(capture),indent=2));raise SystemExit(0)
    if sys.argv[1]!='--check':raise ValueError('LOCAL_BAD_COMMAND')
    sys.path.insert(0,str(ROOT/'scripts'))
    from cp7_attendance_period_choice.catalog_contract import transition
    transition(capture['before'],capture['after'],capture['definitions'])
    print('LOCAL_ALL22_ADDITIVE_TRANSITION_PASS')
