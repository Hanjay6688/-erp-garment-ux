"""Local transition guards using an actual prior full-backup catalog.

New function catalog rows are synthetic. This is not a Native runtime proof.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json,sys
ARGS=sys.argv[1:]
sys.argv=sys.argv[:1]
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cp7_current_versioned_target_installation as product


def run(path):
    raw=Path(path).read_bytes();backup=json.loads(raw)
    baseline=backup['catalog'];data=backup['data'];assert len(baseline)==22
    before=deepcopy(baseline);positive=[];negative=[]
    for name,module in product.STAGES:
        if module is product.selected:
            after=module.delta.expected(before)
            state=dict(sources=module.verify_sources(),delta=dict(before=before,after=after))
            product.admit_catalog(before,after,state,name);product.admit_data(data,dict(data))
            selected_before,selected_after,selected_state=before,after,state
            positive.append(name);before=after
            continue
        after=deepcopy(before)
        schemas=module.SCHEMAS if module is product.target else (module.SCHEMA,)
        for schema in schemas:
            assert schema not in after['schemas'];after['schemas'][schema]=['synthetic-only']
        for sig in module.FUNCTIONS:
            assert sig not in after['functions'];after['functions'][sig]=['synthetic-only']
        if module is product.target:
            _,_,old,new=module.definitions()
            changed=[sig for sig in old if module._body(old[sig])!=module._body(new[sig])]
            assert len(changed)==14
            for sig in changed:
                assert sig in before['functions'];after['functions'][sig]=['synthetic-replacement-only']
        state=dict(catalog=module.own_catalog(after))
        product.admit_catalog(before,after,state,name)
        product.admit_data(data,dict(data));positive.append(name)
        if module is product.target:
            final_before,final_after,final_state=before,after,state
        before=after
    def rejected(label,fn):
        try:fn()
        except ValueError as error:
            negative.append(dict(id=label,refusal=str(error).split(':')[0]))
        else:raise AssertionError('UNSAFE_DELTA_ACCEPTED: '+label)
    def catalog_fault(label,mutate,refresh=False):
        changed=deepcopy(final_after);mutate(changed)
        state=dict(catalog=product.target.own_catalog(changed)) if refresh else final_state
        rejected(label,lambda:product.admit_catalog(final_before,changed,state,'VERSIONED_TARGET'))
    catalog_fault('legacy_projection_changed',lambda c:c['functions'].__setitem__('cp7_model_target_projection.project(jsonb,jsonb,date)',['changed']))
    catalog_fault('legacy_consumer_removed',lambda c:c['functions'].pop('cp7_model_target_consumer.rows(jsonb,jsonb,jsonb,text,jsonb)'))
    catalog_fault('unchanged_hook_changed',lambda c:c['functions'].__setitem__('cp7_baseline_native.serve(uuid)',['changed']),True)
    catalog_fault('undeclared_schema_added',lambda c:c['schemas'].__setitem__('unreviewed_schema',['new']))
    catalog_fault('catalog_group_missing',lambda c:c.pop('aggregates'))
    sig=next(iter(product.target.FUNCTIONS))
    catalog_fault('required_function_missing',lambda c:c['functions'].pop(sig),True)
    sig=next(iter(product.target.FUNCTIONS));preexisting=deepcopy(final_before)
    preexisting['functions'][sig]=['preexisting']
    rejected('new_function_preexists',lambda:product.admit_catalog(preexisting,final_after,final_state,'VERSIONED_TARGET'))
    for label,key in [('old_row_changed',next(k for k in data if not k.startswith('sequence:'))),('old_sequence_advanced',next(k for k in data if k.startswith('sequence:'))),('undeclared_data_key','unexpected.table')]:
        changed=dict(data);changed[key]=['changed']
        rejected(label,lambda changed=changed:product.admit_data(data,changed))
    changed=deepcopy(selected_after);changed['functions'][product.selected.delta.SIGNATURE][1:]=['altered-authority']
    rejected('selected_customer_authority_changed',lambda:product.admit_catalog(selected_before,changed,selected_state,'SELECTED_RETURN_CUSTOMER'))
    changed=deepcopy(selected_after);changed['functions'][product.selected.delta.SIGNATURE]=selected_before['functions'][product.selected.delta.SIGNATURE]
    rejected('selected_customer_delta_omitted',lambda:product.admit_catalog(selected_before,changed,selected_state,'SELECTED_RETURN_CUSTOMER'))
    return dict(status='PASS',scope='LOCAL_GUARD_ONLY_SYNTHETIC_NEW_CATALOG_ROWS',
        trusted_manifest_sha256=sha256(raw).hexdigest(),baseline_groups=22,baseline_data_keys=len(data),
        positive_stages=positive,negative_controls=negative,new_private_functions=13,new_schemas=4,
        hook_bodies_changed=14,hook_bodies_retained=7,legacy_source_projection_consumer_retained=True,
        selected_customer_refusal_body_changes=1,
        Native_runtime_qualified=False,production_go=False,independent_acceptance=False)


if __name__=='__main__':print(json.dumps(run(ARGS[0]),indent=2))
