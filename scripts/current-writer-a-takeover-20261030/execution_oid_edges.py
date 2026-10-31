"""Positive catalogue references only, after exact execution-OID validation.

An OID is scoped to its catalogue and captured snapshot. A reference does not
prove that a caller reaches it, that it executes, or that its writer is safe.
"""
from collections import Counter
from hashlib import sha256
import json


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def derive(declaration,groups,original_groups):
    routines={str(row['oid']):row for row in original_groups['routines']['rows']}
    edges=[]
    for group,spec in declaration['groups'].items():
        for row in groups[group]:
            for field in spec['routine_fields']:
                target=row[field]
                if target=='0':
                    continue
                edges.append(dict(source_catalog=spec['table'],source_identity_column=spec['identity'],
                    source_oid=row[spec['identity']],reference_field=field,
                    target_catalog='pg_proc',target_oid=target,
                    target_captured_row_sha256=sha256(canonical(routines[target])).hexdigest()))
    edges.sort(key=lambda row:(row['source_catalog'],row['source_identity_column'],
        int(row['source_oid']),row['reference_field'],int(row['target_oid'])))
    per_catalog=dict(sorted(Counter(row['source_catalog']for row in edges).items()))
    return dict(classification='POSITIVE_CATALOG_EXECUTION_REFERENCES_NOT_RUNTIME_REACHABILITY',
        edges=edges,edge_count=len(edges),per_catalog=per_catalog,
        distinct_target_routines=len({row['target_oid']for row in edges}),
        target_identity='pg_proc OID within this same captured snapshot only',
        zero_sentinel_is_not_a_routine=True,distinct_reference_fields_preserved=True,
        edges_sha256=sha256(canonical(edges)).hexdigest(),
        unresolved=list(declaration['unresolved'])+[
            'ROUTINE_PLANNER_SUPPORT_IDENTITIES','AGGREGATE_SUPPORT_IDENTITIES',
            'ACCESS_METHOD_AND_OPERATOR_FAMILY_DISPATCH','ACTUAL_CALLER_REACHABILITY'],
        routine_execution_observed=False,writer_closure=False,permission_closure=False,
        lockset_approved=False,actual_Native_case_credit=0,production_go=False,independent_acceptance=False)


def summary(value):
    """Keep canonical Root receipts compact; exact edges are reproducible."""
    return {name:item for name,item in value.items()if name!='edges'}
