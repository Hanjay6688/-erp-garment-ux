"""Check Root's new metadata intake with saved PG17 observations, never ERP."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import argparse,json
import intake_complete_de30 as target
from intake_common import GitBytes,exact,pin


def check(root,model_path):
    raw=model_path.read_bytes();model=json.loads(raw)
    exact(model['classification'],'DISPOSABLE_POSTGRESQL17_METADATA_MODEL_NOT_ERP','CONTROL_ONLY')
    exact(model['actual_ERP_calls'],0,'NO_ERP_CALLS')
    exact(model['provider_functions_invoked'],0,'NO_PROVIDER_EXECUTION')
    with GitBytes(root,target.PREPARED_HEAD,target.PREPARED_TREE)as g:
        source=target.source(g)
        declaration,_=target.execution_oid_sources(g)
        exact(model['declaration_sha256'],sha256(g.read(target.NS+'EXECUTION_OID_QUERIES.json')).hexdigest(),
            'SAVED_PG17_MODEL_USES_EXACT_PUBLIC_QUERIES')
        observations=model['counterexample']
        exact(len(observations),2,'TWO_ACTUAL_OVERLOADS')
        exact(len({row['prior_json_value']for row in observations}),1,'OLD_NAMES_ARE_AMBIGUOUS')
        exact(len({row['exact_function_oid']for row in observations}),2,'ACTUAL_EXECUTION_IDS_DIFFER')
        by_id={row['oid']:row for row in model['groups']['operator_routine_oids']}
        for row in observations:
            exact(by_id[row['oid']]['oprcode'],row['exact_function_oid'],'EXACT_OVERLOAD_ID_PRESERVED')
        supplement=dict(classification=declaration['classification'],groups=model['groups'],
            group_counts={name:len(rows)for name,rows in model['groups'].items()},
            declaration_sha256=model['declaration_sha256'],
            query_sha256={name:sha256(spec['query'].encode()).hexdigest()
                for name,spec in declaration['groups'].items()},same_original_readonly_snapshot=True,
            original_27_groups_rewritten=False,unresolved=declaration['unresolved'],
            writer_closure=False,permission_closure=False,actual_Native_case_credit=0,
            production_go=False,independent_acceptance=False)
        row=dict(groups=model['original_groups'],execution_oid_supplement=supplement)
        accepted=target.execution_oid_observation(g,row);negative=[]
        changes=[
            ('missing-supplement',lambda r:r.pop('execution_oid_supplement')),
            ('old-name-instead-of-exact-oid',lambda r:r['execution_oid_supplement']['groups']['operator_routine_oids'][0].update(oprcode='public.metadata_probe_equal')),
            ('unknown-function',lambda r:r['execution_oid_supplement']['groups']['operator_routine_oids'][0].update(oprcode='4294967295')),
            ('missing-range-catalog',lambda r:r['execution_oid_supplement']['groups'].pop('range_execution_oids')),
            ('forged-count',lambda r:r['execution_oid_supplement']['group_counts'].update(type_routine_oids=0)),
            ('boolean-zero-count',lambda r:r['execution_oid_supplement']['group_counts'].update(transform_execution_oids=False)),
            ('different-query',lambda r:r['execution_oid_supplement']['query_sha256'].update(type_routine_oids='0'*64)),
            ('different-declaration',lambda r:r['execution_oid_supplement'].update(declaration_sha256='0'*64)),
            ('different-snapshot',lambda r:r['execution_oid_supplement'].update(same_original_readonly_snapshot=False)),
            ('rewritten-original27',lambda r:r['execution_oid_supplement'].update(original_27_groups_rewritten=True)),
            ('permission-closure-claim',lambda r:r['execution_oid_supplement'].update(permission_closure=True)),
            ('hidden-remaining-limits',lambda r:r['execution_oid_supplement'].update(unresolved=[])),
        ]
        for label,change in changes:
            changed=deepcopy(row);change(changed)
            try:target.execution_oid_observation(g,changed)
            except (ValueError,KeyError,TypeError):negative.append(label)
            else:raise AssertionError('ROOT_ACCEPTED_INVALID_METADATA:'+label)
    # It must refuse before looking for an archive, creating Git readers, or SQL.
    exact([target.HEAD,target.TREE,target.RUN,target.JOB,target.PARENT_HEAD,target.PARENT_TREE],
        [None]*6,'PREPARED_IS_NOT_ACTUAL')
    try:target.intake('/does-not-exist','/does-not-exist',{})
    except ValueError as error:
        exact(str(error),'DE30_ACTUAL_QUALIFIED_PARENT_AND_OWNING_RUN_NOT_YET_PINNED','UNARMED_BEFORE_IO')
    else:raise AssertionError('UNARMED_INTAKE_ACCEPTED')
    return dict(status='ROOT_EXACT_EXECUTION_METADATA_CONTROLS_PASS',
        head=target.PREPARED_HEAD,tree=target.PREPARED_TREE,source=source,
        input_model=pin(raw),intake_source=pin(Path(target.__file__).read_bytes()),
        positive_saved_PG17_observation=1,negative_controls=negative,
        accepted_observation=accepted,unarmed_before_archive_or_Git=True,
        original_PG17_model_rerun=False,actual_ERP_calls=0,actual_Native_case_credit=0,
        production_go=False,independent_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--model',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=check(a.source,a.model);a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],own_paths=result['source']['own_paths'],
        positive=1,negative=len(result['negative_controls']),actual_ERP_calls=0)))
