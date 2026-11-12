"""Bind read-only Global source review to the verified current SKU terminal.

This reads archived catalogue data and immutable sources. It never opens a
database, publishes a runtime, or substitutes for Global qualification.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for key in ('reviewers', 'repo', 'terminal', 'global-checkout',
                'origin-sku-checkout', 'census', 'parser-source',
                'parser-runtime', 'dynamic-source', 'output'):
        cli.add_argument('--' + key, type=Path, required=True)
    cli.add_argument('--verified-terminal-receipt-sha256', required=True)
    args = cli.parse_args()
    helper_pins_raw = Path(__file__).with_name('GLOBAL_REVIEW_HELPER_PINS.json').read_bytes()
    if hashlib.sha256(helper_pins_raw).hexdigest() != 'ce9aff7a593dc0810910f0657d2823aeba4db6a572ca81c05ddcb10359c9f8fb':
        raise ValueError('GLOBAL_EXACT_REVIEW_HELPER_MANIFEST_REQUIRED')
    helper_pins = json.loads(helper_pins_raw)
    reviewer_root = args.reviewers.resolve().parents[1]
    for name, expected_blob in helper_pins.items():
        path = reviewer_root / name
        if not path.is_file() or path.is_symlink():
            raise ValueError('GLOBAL_REGULAR_REVIEW_HELPER_REQUIRED:' + name)
        raw_helper = path.read_bytes()
        actual_blob = hashlib.sha1(b'blob ' + str(len(raw_helper)).encode() + b'\0' + raw_helper).hexdigest()
        if actual_blob != expected_blob:
            raise ValueError('GLOBAL_EXACT_REVIEW_HELPER_REQUIRED:' + name)
    sys.path[:0] = [str(args.reviewers.resolve()), str(args.parser_runtime.resolve())]
    import pglast
    from review_combined_global_authority import actual_inputs, expected_references
    from review_native_authority import compare
    from compare_sku_catalogue import checked_catalogue
    from verify_wib_successor import CANDIDATE, source_review
    from verify_terminal_sku import pin, require, strict
    from review_writer_delta import (
        CALLBACKS, GLOBAL_INSTALL_TABLES, inventory, mandor_receipt_scope,
        mandor_receipt_writers, parser_for, pinned, retained_facts,
    )

    require(pglast.__version__ == 'v7.20' and pglast.get_postgresql_version() == (17, 7),
            'GLOBAL_EXACT_RETAINED_PARSER_RUNTIME_REQUIRED')
    scope, _ = source_review(args.repo.resolve())
    terminal_raw = (args.terminal / 'SKU_COMBINED_TERMINAL_RECEIPT.json').read_bytes()
    require(pin(terminal_raw)['sha256'] == args.verified_terminal_receipt_sha256,
            'GLOBAL_VERIFIED_TERMINAL_RECEIPT_BYTES_CHANGED')
    raw = actual_inputs(args.terminal.resolve(), scope)
    current = checked_catalogue(raw)
    root_raw = (args.terminal / 'SKU_COMBINED_ROOT.json').read_bytes()
    expected, reasons, corrected = expected_references(
        args.global_checkout.resolve(), args.origin_sku_checkout.resolve())
    authority = compare(current, expected, reasons)
    require(not authority['problems'], 'GLOBAL_ACTUAL_AUTHORITY_ROWS_DIFFER')

    callback_path = args.global_checkout / 'scripts/current-global-sku-automatic-preparation/CALLBACK_SOURCE_REVIEW.json'
    callback_raw = pinned(callback_path, CALLBACKS)
    names = strict(callback_raw)['required_relation_lower_bound']
    require(names == sorted(set(names)) and len(names) == 276 and GLOBAL_INSTALL_TABLES <= set(names),
            'GLOBAL_EXACT_RETAINED_CALLBACK_BOUND_REQUIRED')
    require(not GLOBAL_INSTALL_TABLES.intersection(current['relations']),
            'GLOBAL_ACTUAL_PARENT_ALREADY_CONTAINS_GLOBAL_INSTALLATION')
    watched = (set(names) - GLOBAL_INSTALL_TABLES) | mandor_receipt_scope(current)
    dynamic_raw = args.dynamic_source.read_bytes()
    require(hashlib.sha1(b'blob ' + str(len(dynamic_raw)).encode() + b'\0' + dynamic_raw).hexdigest()
            == 'e4bd5e36b7cebf253015df63013230d99056ecac', 'GLOBAL_EXACT_DYNAMIC_SOURCE_REVIEWER_REQUIRED')
    dynamic = load(args.dynamic_source.resolve(), 'global_exact_dynamic_source_reviewer')
    functions, relations = current['functions'], current['relations']
    columns = {tuple(name.rsplit(':', 1)) for name in current['columns']}
    migration = dynamic.migration_routes(functions[dynamic.MIGRATION][0], relations, columns)
    prepayment = dynamic.prepayment_routes(functions[dynamic.PREPAY][0], set(relations), set(functions), watched)
    parser = parser_for(args.parser_source, args.parser_runtime)
    dynamic_relations = {'erp.initial_import_prepayment_payments'}
    dynamic_relations.update('erp.' + route[field] for route in prepayment['routes'].values()
                             for field in ('table', 'parent'))
    static_writes_in_dynamic_writers = {
        target for signature in (dynamic.MIGRATION, dynamic.PREPAY)
        for _, target in parser.function(functions[signature][0], functions[signature][2])['writes']
    }
    require(static_writes_in_dynamic_writers <= set(relations),
            'GLOBAL_DYNAMIC_WRITER_STATIC_TARGET_MISSING')
    dynamic_relations |= static_writes_in_dynamic_writers
    added = sorted(dynamic_relations - watched)
    require(set(added) <= set(relations), 'GLOBAL_DYNAMIC_RELATION_ABSENT_FROM_ACTUAL_CATALOGUE')
    watched |= dynamic_relations
    require(added == ['erp.migration_staging_rows', 'erp.opening_subledger_balances',
                      'erp.opening_subledger_settlements', 'erp.supplier_payments', 'erp.vendor_payments']
            and len(watched) == 280, 'GLOBAL_REVIEWED_FIVE_RELATION_EXTENSION_CHANGED')
    writer_inventory = inventory(current, retained_facts(args.census), parser, watched)
    require(not writer_inventory['missing_watched_relations'], 'GLOBAL_ACTUAL_WATCHED_RELATIONS_MISSING')
    permissions = dynamic.direct_private_permission_calls(strict(raw))
    require(not permissions['authenticated_has_private_execute']
            and not permissions['exposed_direct_with_missing_grant'],
            'GLOBAL_PRIVATE_PERMISSION_ROUTE_EXPOSURE_CHANGED')

    args.output.mkdir(parents=True, exist_ok=False)
    inventory_raw = (json.dumps(writer_inventory, sort_keys=True, indent=2) + '\n').encode()
    (args.output / 'GLOBAL_ACTUAL_WRITER_INVENTORY.json').write_bytes(inventory_raw)
    report = dict(
        status='QUALIFIED_SKU_GLOBAL_SOURCE_REVIEW_COMPLETED_RUNTIME_PENDING',
        candidate=CANDIDATE, root=pin(root_raw), terminal_receipt=pin(terminal_raw),
        actual_catalogue=pin(raw), authority=authority,
        reviewed_timezone_functions=sorted(corrected), callback_source=pin(callback_raw),
        review_helper_manifest=pin(helper_pins_raw),
        dynamic_source=pin(dynamic_raw), dynamic_added_relations=added,
        watched_relations=len(watched), current_functions=writer_inventory['current_functions'],
        reused_body_facts=len(writer_inventory['reused_body_fact_identities']),
        parsed_bodies=len(writer_inventory['freshly_parsed_body_identities']),
        static_writer_candidates=len(writer_inventory['transitive_static_candidates']),
        writer_inventory=pin(inventory_raw), mandor_receipt_writers=mandor_receipt_writers(writer_inventory),
        dynamic_migration=migration, dynamic_prepayment=prepayment,
        direct_private_permission=permissions,
        actual_new_ERP_cases=0, complete_global_input_review=False,
        global_advisors_D1E_and_recovery_pending=True,
        live_guard_verification_for_global_pending=True,
        runtime_admission=False, production_go=False,
    )
    (args.output / 'GLOBAL_ACTUAL_SOURCE_REVIEW.json').write_text(json.dumps(report, sort_keys=True, indent=2) + '\n')
    print(json.dumps({key: report[key] for key in (
        'status', 'watched_relations', 'current_functions', 'reused_body_facts',
        'parsed_bodies', 'static_writer_candidates', 'runtime_admission')}))


if __name__ == '__main__':
    main()
