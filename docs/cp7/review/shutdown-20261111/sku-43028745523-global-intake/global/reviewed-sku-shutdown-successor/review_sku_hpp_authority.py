"""Review the two pinned SKU cent corrections against the closed Global authority."""
from copy import deepcopy
from pathlib import Path
import importlib.util
import json
import re

from reviewed_sku_source import CANDIDATE, SKU_AREA, exact_checkout, pin, require


SOURCE = SKU_AREA + 'non_po_rounding.py'
SOURCE_PIN = dict(bytes=4768, sha256='ac1424fcc242dfcd05e823111316724d7b671ad313e3603f7196f32cb24846d6')


def corrected_rows(sku, money):
    exact_checkout(sku, CANDIDATE)
    path = sku / SOURCE
    require(path.is_file() and not path.is_symlink() and pin(path.read_bytes()) == SOURCE_PIN,
            'GLOBAL_EXACT_REVIEWED_SKU_ROUNDING_SOURCE_REQUIRED')
    spec = importlib.util.spec_from_file_location('global_reviewed_sku_cent_correction', path)
    rounding = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rounding)
    profile, _ = money.sources()
    originals = {signature: profile['replacement_functions'][signature] for signature in rounding.ROUTES}
    require(all(len(row) == 19 for row in originals.values()), 'GLOBAL_SKU_ROUNDING_FULL19_REQUIRED')
    definitions = {signature: row[0] for signature, row in originals.items()}
    _, output = rounding.correct(dict(definitions=definitions),
                                 dict(replacement_functions=originals, derived_replacements={}))
    rows = output['replacement_functions']
    require(all(rows[signature][1:] == original[1:] for signature, original in originals.items()),
            'GLOBAL_SKU_ROUNDING_OWNER_ACL_AND_SIGNATURE_METADATA_MUST_MATCH')
    return rounding.NATIVE, originals, rows


def derive(sku, routes):
    signature, originals, corrected = corrected_rows(sku, routes.prior)
    expected, known, *_ = routes.prior.expected_authority()
    require(len(expected) == 19 and expected[signature] == originals[signature]
            and set(corrected) & set(expected) == {signature},
            'GLOBAL_SKU_EXACT_ONE_OBSERVER_AUTHORITY_CORRECTION_REQUIRED')
    revised_expected, revised_known = deepcopy(expected), deepcopy(known)
    revised_expected[signature] = corrected[signature]
    body = corrected[signature][0].split('$function$')
    require(len(body) == 3, 'GLOBAL_SKU_ROUNDING_CANONICAL_SQL_BODY_REQUIRED')
    revised_known[signature].update(prosrc_sha256=pin(body[1].encode())['sha256'],
                                    source_function_sha256=pin(corrected[signature][0].encode())['sha256'],
                                    source=SOURCE, source_kind='EXACT_REVIEWED_SKU_ROUNDING_SOURCE')
    helpers, retained = routes.derive()
    before = helpers['authority']
    literals = list(re.finditer(r"jsonb_each\('((?:[^']|'')*)'::jsonb\)", before))
    require(len(literals) == 2, 'GLOBAL_SKU_EXACT_TWO_AUTHORITY_LITERALS_REQUIRED')
    revision = before
    replacements = []
    for literal, old, new in zip(literals, (known, expected), (revised_known, revised_expected)):
        original = literal[0]
        require(json.loads(literal[1].replace("''", "'")) == old and revision.count(original) == 1,
                'GLOBAL_SKU_ROUNDING_AUTHORITY_PREIMAGE_CHANGED')
        text = json.dumps(new, sort_keys=True, separators=(',', ':')).replace("'", "''")
        replacement = "jsonb_each('" + text + "'::jsonb)"
        revision = revision.replace(original, replacement, 1)
        replacements.append((original, replacement))
    recovered = revision
    for original, replacement in reversed(replacements):
        require(recovered.count(replacement) == 1, 'GLOBAL_SKU_ROUNDING_AUTHORITY_INVERSE_CHANGED')
        recovered = recovered.replace(replacement, original, 1)
    require(recovered == before, 'GLOBAL_SKU_ROUNDING_COMPLETE_AUTHORITY_RECOVERY_REQUIRED')
    return revision, dict(status='CLOSED_GLOBAL_SKU_HPP_AUTHORITY_SOURCE_REVIEW',
                          sku_commit=CANDIDATE, sku_source=SOURCE_PIN, retained_authority=pin(before.encode()),
                          proposed_authority=pin(revision.encode()), observed_authority_function=signature,
                          functions={name: dict(before=pin(originals[name][0].encode()),
                                                after=pin(row[0].encode()), all_other_attributes_equal=True)
                                     for name, row in corrected.items()},
                          other_graph_helpers={name: value for name, value in retained['derived_helpers'].items()
                                               if name != 'authority'},
                          actual_SQL_executed=0, actual_catalogue_admitted=False, runtime_admission=False)
