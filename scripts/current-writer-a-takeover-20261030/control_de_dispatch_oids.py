"""Root intake controls against saved PG17 dispatch observations; no SQL."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import argparse,json
import intake_complete_de30 as target
from intake_common import GitBytes,exact,pin


def check(root,path):
    raw=path.read_bytes();model=json.loads(raw)
    exact(model['classification'],'DISPOSABLE_POSTGRESQL17_DISPATCH_MODEL_NOT_ERP','DISPOSABLE_MODEL_ONLY')
    exact(model['actual_ERP_calls'],0,'NO_ERP_CALLS')
    exact(model['provider_functions_invoked'],0,'NO_PROVIDER_CALLS')
    with GitBytes(root,target.PREPARED_HEAD,target.PREPARED_TREE)as g:
        source=target.source(g);declaration,_=target.dispatch_oid_sources(g)
        exact(model['declaration_sha256'],sha256(g.read(target.NS+'DISPATCH_OID_QUERIES.json')).hexdigest(),
            'MODEL_EXACT_PUBLIC_DISPATCH_QUERIES')
        value=dict(classification=declaration['classification'],groups=model['groups'],
            group_counts={name:len(rows)for name,rows in model['groups'].items()},
            declaration_sha256=model['declaration_sha256'],
            query_sha256={name:sha256(spec['query'].encode()).hexdigest()
                for name,spec in declaration['groups'].items()},same_original_readonly_snapshot=True,
            original_27_groups_rewritten=False,original_four_execution_queries_rewritten=False,
            unresolved=declaration['unresolved'],routine_execution_observed=False,
            writer_closure=False,permission_closure=False,actual_Native_case_credit=0,
            production_go=False,independent_acceptance=False)
        row=dict(groups=model['original_groups'],execution_oid_supplement=dict(groups=model['execution_groups']),
            dispatch_oid_supplement=value)
        accepted=target.dispatch_oid_observation(g,row);negative=[]
        changes=[
            ('missing-dispatch-supplement',lambda r:r.pop('dispatch_oid_supplement')),
            ('ambiguous-function-name',lambda r:r['dispatch_oid_supplement']['groups']['aggregate_support_oids'][0].update(aggtransfn='public.metadata_probe_transition')),
            ('missing-family-support',lambda r:r['dispatch_oid_supplement']['groups'].pop('family_support_oids')),
            ('wrong-declaration',lambda r:r['dispatch_oid_supplement'].update(declaration_sha256='0'*64)),
            ('wrong-query',lambda r:r['dispatch_oid_supplement']['query_sha256'].update(routine_support_oids='0'*64)),
            ('forged-count',lambda r:r['dispatch_oid_supplement']['group_counts'].update(routine_support_oids=True)),
            ('changed-snapshot',lambda r:r['dispatch_oid_supplement'].update(same_original_readonly_snapshot=False)),
            ('original27-rewritten',lambda r:r['dispatch_oid_supplement'].update(original_27_groups_rewritten=True)),
            ('execution4-rewritten',lambda r:r['dispatch_oid_supplement'].update(original_four_execution_queries_rewritten=True)),
            ('invented-runtime-observation',lambda r:r['dispatch_oid_supplement'].update(routine_execution_observed=True)),
            ('invented-permission-closure',lambda r:r['dispatch_oid_supplement'].update(permission_closure=True)),
            ('hidden-remaining-limits',lambda r:r['dispatch_oid_supplement'].update(unresolved=[])),
        ]
        for label,change in changes:
            changed=deepcopy(row);change(changed)
            try:target.dispatch_oid_observation(g,changed)
            except (ValueError,KeyError,TypeError):negative.append(label)
            else:raise AssertionError('ROOT_ACCEPTED_INVALID_DISPATCH_METADATA:'+label)
    exact([target.HEAD,target.TREE,target.RUN,target.JOB,target.PARENT_HEAD,target.PARENT_TREE],[None]*6,'UNARMED_ACTUAL_IDS')
    try:target.intake('/does-not-exist','/does-not-exist',{})
    except ValueError as error:
        exact(str(error),'DE30_ACTUAL_QUALIFIED_PARENT_AND_OWNING_RUN_NOT_YET_PINNED','UNARMED_BEFORE_IO')
    else:raise AssertionError('UNARMED_ACTUAL_INTAKE_OPENED')
    return dict(status='ROOT_DISPATCH_METADATA_CONTROLS_PASS',head=target.PREPARED_HEAD,tree=target.PREPARED_TREE,
        source=source,input_model=pin(raw),intake_source=pin(Path(target.__file__).read_bytes()),
        positive_saved_PG17_observation=1,negative_controls=negative,accepted_observation=accepted,
        unarmed_before_archive_or_Git=True,original_PG17_model_rerun=False,actual_ERP_calls=0,
        actual_Native_case_credit=0,production_go=False,independent_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--model',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=check(a.source,a.model);a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],own_paths=result['source']['own_paths'],
        positive=1,negative=len(result['negative_controls']),actual_ERP_calls=0)))
