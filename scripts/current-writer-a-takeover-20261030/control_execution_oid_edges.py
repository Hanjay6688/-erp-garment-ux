"""Exercise positive-reference derivation on saved real PG17 catalogue rows."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import argparse,json
import execution_oid_edges as edge
import intake_complete_de30 as target
from intake_common import GitBytes,exact,pin


def check(root,model_path,edges_path):
    raw=model_path.read_bytes();model=json.loads(raw)
    exact(model['actual_ERP_calls'],0,'DISPOSABLE_MODEL_ONLY')
    with GitBytes(root,target.PREPARED_HEAD,target.PREPARED_TREE)as g:
        declaration,validate=target.execution_oid_sources(g)
        groups=model['groups'];original=model['original_groups']
        validate(groups,declaration['groups'],original)
        result=edge.derive(declaration,groups,original)
        expected=sum(1 for name,spec in declaration['groups'].items()
            for row in groups[name]for field in spec['routine_fields']if row[field]!='0')
        exact(result['edge_count'],expected,'EVERY_NONZERO_REFERENCE_ONCE')
        observed={(row['source_catalog'],row['source_identity_column'],row['source_oid'],row['reference_field']):row
            for row in result['edges']}
        exact(len(observed),expected,'FULL_PROVENANCE_UNIQUE')
        for row in model['counterexample']:
            actual=observed[('pg_operator','oid',row['oid'],'oprcode')]
            exact(actual['target_oid'],row['exact_function_oid'],'SAME_NAME_DIFFERENT_ACTUAL_ROUTINES')
        exact(any(row['target_oid']=='0'for row in result['edges']),False,'ZERO_IS_NOT_EXECUTION')
        shuffled={name:list(reversed(rows))for name,rows in groups.items()}
        exact(edge.derive(declaration,shuffled,original),result,'INPUT_ORDER_DOES_NOT_CHANGE_GRAPH')
        changed=deepcopy(groups)
        operator=changed['operator_routine_oids'][0]
        # Two different fields pointing at one routine must remain two edges.
        operator['oprrest']=operator['oprcode']
        validate(changed,declaration['groups'],original)
        aliased=edge.derive(declaration,changed,original)
        same=[row for row in aliased['edges']if row['source_catalog']=='pg_operator'
            and row['source_oid']==operator['oid']and row['reference_field']in('oprcode','oprrest')]
        exact(len(same),2,'DISTINCT_REFERENCE_FIELDS_NOT_DEDUPLICATED')
        exact(len({row['target_oid']for row in same}),1,'SAME_TARGET_FIELDS_BOTH_RETAINED')
        # Catalogue identity is part of the key; global OID equality is insufficient.
        isolated={'type_routine_oids':[dict(groups['type_routine_oids'][0])],
            'operator_routine_oids':[dict(groups['operator_routine_oids'][0])],
            'range_execution_oids':[],'transform_execution_oids':[]}
        isolated['type_routine_oids'][0]['oid']=isolated['operator_routine_oids'][0]['oid']
        fixture=edge.derive(declaration,isolated,original)
        exact({row['source_catalog']for row in fixture['edges']},{'pg_type','pg_operator'},
            'SYNTHETIC_CROSS_CATALOG_OID_COLLISION_PRESERVED')
        missing=deepcopy(original)
        missing['routines']['rows']=[r for r in missing['routines']['rows']
            if str(r['oid'])!=model['counterexample'][0]['exact_function_oid']]
        try:validate(groups,declaration['groups'],missing)
        except ValueError:pass
        else:raise AssertionError('ORPHAN_REFERENCE_NOT_REFUSED_BEFORE_DERIVATION')
        supplement=dict(classification=declaration['classification'],groups=groups,
            group_counts={name:len(rows)for name,rows in groups.items()},
            declaration_sha256=sha256(g.read(target.NS+'EXECUTION_OID_QUERIES.json')).hexdigest(),
            query_sha256={name:sha256(spec['query'].encode()).hexdigest()
                for name,spec in declaration['groups'].items()},same_original_readonly_snapshot=True,
            original_27_groups_rewritten=False,unresolved=declaration['unresolved'],
            writer_closure=False,permission_closure=False,actual_Native_case_credit=0,
            production_go=False,independent_acceptance=False)
        admitted=target.execution_oid_observation(g,dict(groups=original,execution_oid_supplement=supplement))
        exact(admitted['positive_references'],edge.summary(result),'ROOT_INTAKE_BINDS_EXACT_DERIVED_EDGES')
    edges_path.write_text(json.dumps(result,indent=2)+'\n')
    return dict(status='POSITIVE_EXECUTION_REFERENCE_CONTROLS_PASS',input_model=pin(raw),
        original_PG17_model_rerun=False,actual_ERP_calls=0,
        actual_saved_PG17_reference_derivation=True,controls=[
            'all_nonzero_fields_exact_once','overloaded_actual_function_ids_preserved',
            'zero_sentinel_excluded','input_order_invariant','same_target_distinct_fields_preserved',
            'synthetic_cross_catalog_OID_collision_preserved','orphan_target_refused_before_derivation',
            'Root_metadata_intake_binds_exact_graph_digest'],
        output=pin(edges_path.read_bytes()),observed=edge.summary(result),
        helper_source=pin(Path(edge.__file__).read_bytes()),
        Root_intake_source=pin(Path(target.__file__).read_bytes()),
        actual_Native_case_credit=0,production_go=False,independent_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--model',type=Path,required=True);p.add_argument('--edges',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=check(a.source,a.model,a.edges);a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],edges=result['observed']['edge_count'],
        controls=len(result['controls']),actual_ERP_calls=0)))
