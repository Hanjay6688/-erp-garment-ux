"""Verify restored B metadata after the complete trusted backup has matched.

The ordinary stage verifier deliberately binds raw proargtypes OIDs inside
one database. A fresh pg_restore gives composite row types new local OIDs.
Only that field is rebound in a COPY of the verifier state, after the full22
catalog has proved the exact named argument/result types and all metadata.
No stored receipt, SQL body, ACL, type identity or business row is changed.
"""
from copy import deepcopy
from cp7_ab_bounded_chain import recovery,composition as product

ROW_FIELDS=('definition','body','owner','security_definer','volatility',
    'configuration','acl','return_type','argument_type_oids','kind',
    'leakproof','parallel','cost','rows')


def rebind_and_verify(cur,state,backup,digest,*,expected_database):
    # This is the full trusted restore proof, including all22 and every row,
    # before any stage-local metadata is adapted. It seals only the one
    # qualified Native trigger census with this new database's local OIDs.
    receipt=recovery.rebind_restored(cur,backup,digest,expected_database=expected_database)
    original=state['stages'][-1]['state']
    original_snapshot=deepcopy(original)
    adapted=deepcopy(original)
    rebound=[]
    for group in ('new_rows','dependencies'):
        for signature,expected in original[group].items():
            actual=product.bounded._row(cur,signature)
            if len(expected)!=len(ROW_FIELDS) or len(actual)!=len(ROW_FIELDS):
                raise ValueError('AB_RESTORE_FUNCTION_ROW_SHAPE_CHANGED: '+signature)
            changed=[i for i,(a,b)in enumerate(zip(expected,actual))if a!=b]
            if any(i!=8 for i in changed):
                raise ValueError('AB_RESTORE_NONLOCAL_FUNCTION_METADATA_CHANGED: '+signature+': '+
                    ','.join(ROW_FIELDS[i]for i in changed))
            if changed:
                # Complete catalog already compared function arguments,
                # results and full type implementation by qualified name.
                with product.catalog._catalog(cur):
                    identity,types=cur.execute("select p.oid::regprocedure::text,"
                        "array(select t::regtype::text from unnest(p.proargtypes)t) "
                        "from pg_proc p where p.oid=%s::regprocedure",(signature,)).fetchone()
                if identity!=signature:
                    raise ValueError('AB_RESTORE_NAMED_FUNCTION_IDENTITY_CHANGED: '+signature)
                adapted[group][signature][8]=actual[8]
                if signature in adapted['original_rows']:
                    old=adapted['original_rows'][signature]
                    if old[2:]!=expected[2:]:
                        raise ValueError('AB_RESTORE_ORIGINAL_AUTHORITY_NOT_PRESERVED: '+signature)
                    old[8]=actual[8]
                rebound.append(dict(group=group,signature=signature,
                    named_input_types=types,before_local_oids=expected[8],after_local_oids=actual[8]))
    proof=product.bounded.verify(cur,adapted)
    if original_snapshot!=state['stages'][-1]['state']:
        raise ValueError('AB_RESTORE_ORIGINAL_VERIFIER_STATE_MUTATED')
    return dict(binding=receipt,restored_stage_proof=proof,local_argument_oid_bindings=rebound,
        only_verifier_state_copied=True,all_other_row_fields_exact=True,
        complete_named_type_catalog_verified=True,original_state_unchanged=True,
        production_go=False)
