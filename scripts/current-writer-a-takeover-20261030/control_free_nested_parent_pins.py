"""Source grammar controls for the actual two nested FREE manifests. No ERP."""
from pathlib import Path
from types import SimpleNamespace
import json
from intake_common import GitBytes,exact,pin
import intake_free3 as child
import prepare_free_activation as planner


def controls(root):
    with GitBytes(root,child.ACTIVATION_SOURCE_HEAD,child.ACTIVATION_SOURCE_TREE)as g:
        declaration=json.loads(g.read(child.NS+'SOURCE.json'))
        before={name:g.read(name)for name in set(declaration['files'])|{child.NS+'SOURCE.json'}}
        initial=child.nested_manifest_sources(g)
    # Distinct source-only sentinels exercise dependency propagation. They
    # are not parent receipts, candidate files, or proposed ERP operations.
    values=dict(before)
    for name in('admission.py','source.py'):
        values[child.NS+name]+=b'\n# ROOT source-pin propagation control only; not a candidate.\n'
    routes=planner.rebind_nested_parent_manifests(values,before)
    exact(len(routes),4,'FREE_NESTED_CONTROL_EXACT_FOUR_PROPAGATED_PINS')
    def check(data):
        def verify(name,expected):
            raw=data[name];exact(pin(raw),expected,'FREE_NESTED_CONTROL_DEPENDENCY_PIN:'+name);return raw
        return child.nested_manifest_sources(SimpleNamespace(read=lambda name:data[name],verify_pin=verify))
    positive=check(values)
    broken=dict(values);broken['scripts/cp7_current_de_free_date/SOURCE.json']=before['scripts/cp7_current_de_free_date/SOURCE.json']
    try:check(broken)
    except ValueError as error:stale=str(error)
    else:raise ValueError('FREE_NESTED_CONTROL_STALE_COMPOSITE_MANIFEST_WAS_ACCEPTED')
    broken_before=dict(before);path='scripts/cp7_special_free_date_on_de/SOURCE.json'
    corrupt=json.loads(before[path]);corrupt['files'][child.NS+'admission.py']['bytes']+=1
    broken_before[path]=(json.dumps(corrupt,indent=2)+'\n').encode()
    try:planner.rebind_nested_parent_manifests(dict(values),broken_before)
    except ValueError as error:wrong=str(error)
    else:raise ValueError('FREE_NESTED_CONTROL_WRONG_ORIGINAL_PIN_WAS_ACCEPTED')
    for path in set(before)-{child.NS+'admission.py',child.NS+'source.py',*(p for p,_ in planner.NESTED_PARENT_MANIFESTS)}:
        exact(values[path],before[path],'FREE_NESTED_CONTROL_UNRELATED_SOURCE_UNCHANGED:'+path)
    for path,_ in planner.NESTED_PARENT_MANIFESTS:
        previous=json.loads(before[path]);following=json.loads(values[path])
        exact({k:v for k,v in previous.items()if k!='files'},
              {k:v for k,v in following.items()if k!='files'},'FREE_NESTED_CONTROL_ALL_PRODUCT_METADATA_PRESERVED')
    return dict(status='ACTUAL_FREE_SOURCE_NESTED_DEPENDENCY_CONTROLS_PASS_NOT_RUNTIME',
        immutable_prepared_head=child.ACTIVATION_SOURCE_HEAD,immutable_prepared_tree=child.ACTIVATION_SOURCE_TREE,
        original_source_closure=initial,source_sentinel_propagation=positive,existing_pin_routes=routes,
        stale_composite_manifest_refused=stale,wrong_original_nested_pin_refused=wrong,
        actual_parent_receipt_created=False,activation_planner_armed=False,candidate_tree_or_ref_written=False,
        actual_ERP_imports=0,actual_SQL_executed=0,actual_Native_cases=0,
        production_go=False,independent_acceptance=False)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=controls(a.source);a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k]for k in('status','actual_ERP_imports','actual_SQL_executed','actual_Native_cases')}))
