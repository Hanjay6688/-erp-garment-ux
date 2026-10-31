"""Root intake controls reuse the saved actual PostgreSQL17 privilege model."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import argparse,ast,json
import intake_complete_de30 as target
from intake_common import GitBytes,exact,pin


def check(root,path):
    raw=path.read_bytes();model=json.loads(raw)
    exact(model['classification'],'DISPOSABLE_PG17_P0_PRIVILEGE_MODEL_NOT_ERP','MODEL_NOT_ERP')
    exact(model['actual_ERP_calls'],0,'NO_ERP_CALLS');exact(model['provider_functions_invoked'],0,'NO_PROVIDER_CALLS')
    with GitBytes(root,target.PREPARED_HEAD,target.PREPARED_TREE)as g:
        source=target.source(g);declaration,_=target.p0_privilege_sources(g)
        exact(model['declaration_sha256'],sha256(g.read(target.NS+'P0_PRIVILEGE_QUERIES.json')).hexdigest(),'EXACT_MODEL_QUERIES')
        row=deepcopy(model['base'])
        value=dict(classification=declaration['classification'],groups=model['groups'],
            group_counts={name:len(rows)for name,rows in model['groups'].items()},
            declaration_sha256=model['declaration_sha256'],
            query_sha256={name:sha256(spec['query'].encode()).hexdigest()for name,spec in declaration['groups'].items()},
            same_original_readonly_snapshot=True,original_27_groups_rewritten=False,provider_function_calls=0,
            unresolved=declaration['unresolved'],writer_closure=False,permission_closure=False,lockset_approved=False,
            actual_Native_case_credit=0,production_go=False,independent_acceptance=False)
        row['P0_privilege_supplement']=value
        accepted=target.p0_privilege_observation(g,row);negative=[]
        primary=dict(database='postgres',primary_scheduler_database=True)
        exact(target.p0_privilege_observation(g,primary),dict(status='NOT_APPLICABLE_PRIMARY_SCHEDULER_DATABASE',actual_Native_case_credit=0),'PRIMARY_WITHOUT_ERP')
        changes=[
            ('missing-supplement',lambda r:r.pop('P0_privilege_supplement')),
            ('missing-role-function',lambda r:r['P0_privilege_supplement']['groups']['functions'].pop()),
            ('omitted-physical-column',lambda r:r['P0_privilege_supplement']['groups']['columns'].pop()),
            ('column-only-access-hidden',lambda r:r['P0_privilege_supplement']['groups'].pop('column_privileges')),
            ('wrong-declaration',lambda r:r['P0_privilege_supplement'].update(declaration_sha256='0'*64)),
            ('wrong-query',lambda r:r['P0_privilege_supplement']['query_sha256'].update(functions='0'*64)),
            ('forged-count',lambda r:r['P0_privilege_supplement']['group_counts'].update(functions=True)),
            ('changed-snapshot',lambda r:r['P0_privilege_supplement'].update(same_original_readonly_snapshot=False)),
            ('original27-rewritten',lambda r:r['P0_privilege_supplement'].update(original_27_groups_rewritten=True)),
            ('provider-executed',lambda r:r['P0_privilege_supplement'].update(provider_function_calls=1)),
            ('permission-closure-invented',lambda r:r['P0_privilege_supplement'].update(permission_closure=True)),
            ('lock-closure-invented',lambda r:r['P0_privilege_supplement'].update(lockset_approved=True)),
            ('hidden-remaining-limits',lambda r:r['P0_privilege_supplement'].update(unresolved=[])),
            ('primary-claiming-candidate-privileges',lambda r:r.update(database='postgres',primary_scheduler_database=True)),
        ]
        for label,change in changes:
            changed=deepcopy(row);change(changed)
            try:target.p0_privilege_observation(g,changed)
            except (ValueError,KeyError,TypeError):negative.append(label)
            else:raise AssertionError('ROOT_ACCEPTED_INVALID_PRIVILEGE_METADATA:'+label)
    # The owning full intake must call this validator, not merely define it.
    function=next(n for n in ast.parse(Path(target.__file__).read_bytes()).body
        if isinstance(n,ast.FunctionDef)and n.name=='metadata_observation')
    calls=[n for n in ast.walk(function)if isinstance(n,ast.Call)
        and isinstance(n.func,ast.Name)and n.func.id=='p0_privilege_observation']
    exact(len(calls),1,'OWNING_METADATA_GATE_CALLS_PRIVILEGE_VALIDATOR_ONCE')
    exact([target.HEAD,target.TREE,target.RUN,target.JOB,target.PARENT_HEAD,target.PARENT_TREE],[None]*6,'UNARMED_ACTUAL_IDS')
    try:target.intake('/does-not-exist','/does-not-exist',{})
    except ValueError as error:exact(str(error),'DE30_ACTUAL_QUALIFIED_PARENT_AND_OWNING_RUN_NOT_YET_PINNED','UNARMED_BEFORE_IO')
    else:raise AssertionError('UNARMED_ACTUAL_INTAKE_OPENED')
    return dict(status='ROOT_P0_PRIVILEGE_CONTROLS_PASS',head=target.PREPARED_HEAD,tree=target.PREPARED_TREE,
        source=source,input_model=pin(raw),intake_source=pin(Path(target.__file__).read_bytes()),
        positive_saved_PG17_observation=1,positive_primary_scope=1,negative_controls=negative,
        accepted_observation=accepted,unarmed_before_archive_or_Git=True,
        original_PG17_model_rerun=False,actual_ERP_calls=0,actual_Native_case_credit=0,
        production_go=False,independent_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--model',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();result=check(a.source,a.model)
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],own_paths=result['source']['own_paths'],positive=2,
        negative=len(result['negative_controls']),actual_ERP_calls=0)))
