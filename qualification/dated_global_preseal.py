"""Prepare the closed Global preseal on the verified dated Laundry child."""

from contextlib import contextmanager
import json

import dated_sku_install
import dated_sku_parent
import global_preseal
import scope_witness


REVIEW_NAME = 'S02_GLOBAL_STATIC_RELATION_DELTA.json'
WORKSPACE_NAME = 'GLOBAL_S02_LAUNDRY_DIRECT_SOURCE.json'
WORKSPACE_PIN = 'a73566f9722cfeabfec79b35a2b9da03e363c0e21280774f9ce6c4feed30c3d8'
RELATION_LIST_PIN = dict(bytes=14681, sha256='7032cd10531f991a67dcb962c291d5d8f5d812195f75ddd0a5892f493a63e3fa')
EXPANDED_REVIEW_NAME = 'GLOBAL_DATED_S05_RELATION_LOWER_BOUND.json'
EXPANDED_REVIEW_SHA = '9a8374a4e563cf99591b1b7d4dfbc845ea787a8e9801355213945a07b2da13f1'


def reviewed_relations(expanded_review=None):
    """Resolve the retained catalogue scope and the reviewed additive input."""
    base = global_preseal.exact(global_preseal.INPUTS / 'relation_candidates.json', global_preseal.RELATIONS_SHA)
    delta = global_preseal.exact(global_preseal.INPUTS / REVIEW_NAME, scope_witness.S02_DELTA)
    review = json.loads(delta)
    global_preseal.require(review['actual_full25'] == global_preseal.CATALOGUE_PIN
                           and review['sku_run'] == 43347020525,
                           'S02_GLOBAL_EXACT_SCOPE_PARENT_REQUIRED')
    # Owner Laundry reads the vendor workspace. The retained Global Nota case
    # reads Finance, which includes filing history. No CLOSE is planned here.
    prior = scope_witness.candidate_inputs(base, delta, opening_claim_or_visible_workspace=True,
                                           filing_read_or_close=True)
    workspace_raw = global_preseal.exact(global_preseal.INPUTS / WORKSPACE_NAME, WORKSPACE_PIN)
    workspace = json.loads(workspace_raw)
    names = workspace['relation_names']
    global_preseal.require(workspace['parent_a625_Full25_sha256'] == global_preseal.CATALOGUE_PIN['sha256']
                           and workspace['exact_base'] == global_preseal.pin(base)
                           and workspace['exact_dated_delta'] == global_preseal.pin(delta)
                           and workspace['relation_list_pin'] == RELATION_LIST_PIN
                           and global_preseal.pin(json.dumps(names, separators=(',', ':')).encode()) == RELATION_LIST_PIN
                           and workspace['source_review_limits']['complete_input_review'] is False
                           and len(prior) == 445 and len(names) == 454
                           and names == sorted(set(prior) | set(workspace['additional_relations'])),
                           'S02_GLOBAL_EXACT_CANDIDATE_RELATIONS_REQUIRED')
    if expanded_review is None:
        return names

    expanded = json.loads(global_preseal.exact(expanded_review, EXPANDED_REVIEW_SHA))
    additions = set(expanded['additions'])
    combined = expanded['proposed_relations']
    global_preseal.require(expanded.get('status') == 'GLOBAL_DATED_S05_RELATION_LOWER_BOUND_VERIFIED'
                           and expanded['archived_parent_catalogue'] == global_preseal.CATALOGUE_PIN['sha256']
                           and expanded['dated_preseal_source'] == global_preseal.pin(workspace_raw)
                           and expanded['retained_live_run'] == 43466695454
                           and expanded['retained_live_relations'] == len(names)
                           and not additions & set(names) and len(additions) == 7
                           and combined == sorted(set(names) | additions)
                           and global_preseal.pin(json.dumps(combined, separators=(',', ':')).encode())
                           == expanded['proposed_relations_pin']
                           and expanded['archived_outside_origin_RI_write_edges'] == 0
                           and all(expanded[key] is False for key in ('live_scope_observation_complete',
                               'complete_input_review', 'runtime_admission', 'production_go')),
                           'GLOBAL_EXACT_EXPANDED_RELATION_REVIEW_REQUIRED')
    return combined


@contextmanager
def prepare(candidate, catalogue, fingerprint, output, *, verify_as=None, expanded_review=None):
    """Use the existing preseal observation with the exact dated child overlay."""
    dated_sku_install.verify_source()
    names = reviewed_relations(expanded_review)

    @contextmanager
    def installed_parent(cur, provider, compare, inputs):
        def verify(cursor, value, expected, digest):
            if verify_as is None:
                return compare(cursor, value, expected, digest)
            with verify_as(cursor):
                return compare(cursor, value, expected, digest)

        before = provider.capture(cur)
        bound = verify(cur, before, inputs, provider.fingerprint)
        state = dated_sku_install.install_delta(cur, provider, bound)
        yield dated_sku_parent.prepare(verify, catalogue, provider.all22, state.installed_identity)
        dated_sku_install.restore_preuse(cur, provider, state)

    with global_preseal.prepare(candidate, catalogue, fingerprint, output, relation_names=names,
                                installed_parent=installed_parent) as observe:
        yield observe
