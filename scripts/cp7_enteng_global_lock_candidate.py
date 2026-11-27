"""Derive the CP7 Global lock body for the managed PostgreSQL project role.

The caller still needs a reviewed final parent and a release procedure that
serializes role and event trigger administration. This file renders or
describes the change. It never connects or runs an installation.
"""

import argparse
from hashlib import sha256
import json

from cp7_global_nonpo_envelope import catalog_bridge


CATALOGUE_CALL = ' catalogs_:=cp7_global_catalog_fence.lock_v1();'
MANAGED_CALL = ' perform cp7_global_release_guard.enter_correction();'
ORIGINAL_MODE = "  'catalog_mode','SHARE','relation_mode','EXCLUSIVE'"
MANAGED_MODE = "  'catalog_mode','DDL_EVENT_INTERLOCK','relation_mode','EXCLUSIVE'"


def only_once(text, before, after):
    if text.count(before) != 1:
        raise ValueError('CP7_GLOBAL_MANAGED_LOCK_ANCHOR_CHANGED')
    return text.replace(before, after, 1)


def derive():
    native, audit = catalog_bridge.derive()
    catalogue = audit['route']['after']
    first_statement = catalogue.index(CATALOGUE_CALL)
    managed_catalogue = only_once(catalogue[first_statement:], CATALOGUE_CALL, MANAGED_CALL)
    managed_catalogue = (
        ' -- Serialize against hosted DDL and the approved migration transaction.\n'
        + managed_catalogue
    )
    relation = audit['relation_route']
    result = only_once(native, catalogue, managed_catalogue)
    result = only_once(result, relation['after'], relation['before'])
    result = only_once(result, ORIGINAL_MODE, MANAGED_MODE)
    restored = only_once(result, MANAGED_MODE, ORIGINAL_MODE)
    restored = only_once(restored, relation['before'], relation['after'])
    restored = only_once(restored, managed_catalogue, catalogue)
    if restored != native or 'supabase_admin' in result:
        raise ValueError('CP7_GLOBAL_MANAGED_LOCK_CHANGED_UNDECLARED_SOURCE')
    receipt = {
        'canonical_bridge_sha256': sha256(native.encode()).hexdigest(),
        'managed_lock_sha256': sha256(result.encode()).hexdigest(),
        'changed_routes': ['catalogue_interlock', 'application_relation_lock', 'returned_lock_mode'],
        'original_full_catalogue_and_native_authority_comparisons_preserved': True,
        'requires_reviewed_release_procedure': True,
        'requires_exact_final_parent': True,
        'runtime_approved': False,
    }
    return result, receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sql', action='store_true', help='Print the source candidate')
    body, proof = derive()
    print(body if parser.parse_args().sql else json.dumps(proof, indent=2))
