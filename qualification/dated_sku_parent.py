"""Keep the a625 SKU authority when reviewing the exact dated Laundry child."""

import json

import dated_source_stage as dated


def project_sku(value, archived, all22):
    """Recover only the three pinned preimages and two pinned private additions."""
    archived_functions = dict(archived['functions'])
    if len(dict(value['functions'])) != len(value['functions']):
        raise ValueError('S02_SKU_DUPLICATE_FUNCTION_IDENTITY')
    functions = []
    for signature, row in value['functions']:
        if signature in dated.HELPERS:
            continue
        if signature in dated.PREIMAGES:
            row = archived_functions[signature]
        functions.append([signature, row])
    projected = dict(value, functions=functions)
    dated.verify_transition(all22(projected), all22(value))
    return projected


def prepare(verify_sku, catalogue_raw, all22, identity):
    """Use the original complete SKU verifier and also bind the real child hash."""
    archived = json.loads(catalogue_raw)

    def verify(cur, value, inputs, fingerprint):
        if dated.native_identity(cur, dated.POSTIMAGES) != identity:
            raise ValueError('S02_SKU_LIVE_RAW_AUTHORITY_CHANGED')
        projected = project_sku(value, archived, all22)
        proof = verify_sku(cur, projected, inputs, fingerprint)
        if proof.get('status') != 'GLOBAL_ACTUAL_PARENT_CATALOGUE_AND_CENSUS_VERIFIED':
            raise ValueError('S02_SKU_EXACT_RETAINED_PARENT_PROOF_REQUIRED')
        return dict(proof, live_fingerprint=fingerprint(cur, value),
                    dated_laundry={
                        'projected_sku_fingerprint': proof['live_fingerprint'],
                        'exact_replaced_functions': sorted(dated.PREIMAGES),
                        'exact_private_helpers': sorted(dated.HELPERS),
                        'same_connection_raw_authority_verified': True,
                    })

    return verify
