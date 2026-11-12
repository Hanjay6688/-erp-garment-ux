"""Check whether the reviewed function settings change the Global writer inventory."""

from pathlib import Path
import json
from zipfile import ZipFile

from review_combined_global_authority import expected_references, replay
from verify_combined_sku import source_review
from verify_terminal_sku import CATALOGUE, pin, strict
from review_writer_delta import (
    CALLBACKS, GLOBAL_INSTALL_TABLES, checked_catalogue, inventory, mandor_receipt_scope,
    mandor_receipt_writers, parser_for, pinned, retained_facts,
)


HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ADDED = {'erp.migration_staging_rows', 'erp.opening_subledger_balances',
         'erp.opening_subledger_settlements', 'erp.supplier_payments', 'erp.vendor_payments'}


def main():
    with ZipFile(BASE / 'cp7-current-checks/origin/canonical.zip') as bundle:
        raw = bundle.read(CATALOGUE)
    scope, _ = source_review(BASE / 'cp7-erp')
    expected, _, before = expected_references(BASE / 'cp7-global-full', BASE / 'cp7-sku-origin')
    projected = replay(raw, scope, expected, before)
    old, new = map(checked_catalogue, (raw, projected))
    old_bodies = old['functions']
    new_bodies = new['functions']
    assert {name for name in old_bodies if old_bodies[name] != new_bodies[name]} == set(before)
    for name in before:
        assert old_bodies[name][0].split('$function$')[1] == new_bodies[name][0].split('$function$')[1]
    callback = strict(pinned(HERE / 'callbacks.json', CALLBACKS))
    watched = (set(callback['required_relation_lower_bound']) - GLOBAL_INSTALL_TABLES) | mandor_receipt_scope(new) | ADDED
    assert watched <= set(new['relations']) and len(watched) == 280
    parser = parser_for(HERE / 'scan_saved_writer_census.py', BASE / 'cp7-pydeps')
    facts = retained_facts(HERE / 'census.json')
    first, last = (inventory(catalogue, facts, parser, watched) for catalogue in (old, new))
    for key in ('direct_watched_writes', 'transitive_static_candidates', 'syntax_dynamic_or_opaque_obligations'):
        assert first[key] == last[key], key
    assert len(last['transitive_static_candidates']) == 592 and last['current_functions'] == 3105
    result = dict(status='SKU_THREE_TIMEZONE_CHANGES_PRESERVE_GLOBAL_WRITER_PROJECTION',
                  original_catalogue=pin(raw), projected_catalogue=pin(projected),
                  changed_settings=list(before), relations_watched=len(watched),
                  current_functions=last['current_functions'], transitive_writer_candidates=len(last['transitive_static_candidates']),
                  reused_exact_body_facts=len(last['reused_body_fact_identities']),
                  parsed_bodies=len(last['freshly_parsed_body_identities']), mandor_receipt_writers=mandor_receipt_writers(last),
                  actual_terminal_original=False, complete_global_input_review=False, runtime_admission=False)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
