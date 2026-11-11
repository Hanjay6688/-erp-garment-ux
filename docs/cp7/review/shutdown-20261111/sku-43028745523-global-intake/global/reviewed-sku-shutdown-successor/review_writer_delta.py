"""Rebuild the writer candidate inventory from a verified current SKU catalogue."""
from collections import defaultdict
from pathlib import Path
import argparse
import importlib.util
import json
import sys

from compare_sku_catalogue import checked_catalogue, review as verified_catalogue_review
from verify_terminal_sku import fields, pin, require, strict


CENSUS = dict(bytes=6000014, sha256='3ca5e335ceb2198e2e069ff8ddedf249991e2326215a157c4f2c17dd1458cfbf')
PARSER = dict(bytes=13782, sha256='69adaed6494ea81cc93ed304718eda7a94131052a81ae3dbc2c8a6d54b4e045c')
COMMON = dict(bytes=6518, sha256='698216cfb4c31e8c93167e1b67f52f0b7532e5906ac8a09584b0a32c728b41e9')
CALLBACKS = dict(bytes=22414, sha256='fb798b7793604cf4b79162b7ef18bf80e6e9e1a5f69b90091e5c5359bd0bba7a')
GLOBAL_INSTALL_TABLES = frozenset(('cp7_global_nonpo_envelope.profiles',
    'cp7_global_nonpo_envelope.scope_completions_v1', 'cp7_global_nonpo_envelope.work_scopes_v1'))
STATE = 'CURRENT_ALL_FUNCTION_WRITER_CANDIDATES_REBUILT_INPUT_REVIEW_PENDING'


MANDOR_RECEIPT_SCHEMA = 'cp7_note_zero_effect'
MANDOR_WRITERS = {
    'cp7_note_zero_effect.prepare_v1(jsonb,uuid,text,uuid,jsonb)': 'cp7_note_zero_effect.preparations',
    'cp7_note_zero_effect.finish_v1(jsonb,jsonb)': 'cp7_note_zero_effect.receipts',
}
MANDOR_RECEIPT_RELATIONS = frozenset(MANDOR_WRITERS.values())


def postgres_only_acl(rows):
    return type(rows) is list and all(type(row) is list and len(row) == 4
                                     and row[:2] == ['postgres', 'postgres'] for row in rows)


def mandor_receipt_scope(current):
    schema = current['schemas'].get(MANDOR_RECEIPT_SCHEMA)
    require(type(schema) is list and len(schema) == 2 and schema[0] == 'postgres'
            and postgres_only_acl(schema[1]), 'GLOBAL_MANDOR_RECEIPT_SCHEMA_AUTHORITY_CHANGED')
    for relation in sorted(MANDOR_RECEIPT_RELATIONS):
        row = current['relations'].get(relation)
        require(type(row) is list and len(row) == 13 and row[:5] == ['postgres', 'r', 'p', True, True]
                and postgres_only_acl(row[12]), 'GLOBAL_MANDOR_RECEIPT_RELATION_AUTHORITY_CHANGED:' + relation)
        name = relation.rsplit('.', 1)[1]
        trigger = current['triggers'].get(relation + ':cp7_note_zero_effect_' + name + '_immutable')
        require(type(trigger) is list and len(trigger) >= 10 and trigger[:3] == [False, 'O', 27]
                and trigger[8] == 'cp7_note_zero_effect.reject_receipt_mutation_v1()',
                'GLOBAL_MANDOR_RECEIPT_APPEND_ONLY_TRIGGER_CHANGED:' + relation)
    for signature in sorted(MANDOR_WRITERS):
        row = current['functions'].get(signature)
        require(type(row) is list and len(row) == 19 and row[1:5] == ['postgres', 'plpgsql', 'f', True]
                and postgres_only_acl(row[18]), 'GLOBAL_MANDOR_RECEIPT_WRITER_AUTHORITY_CHANGED:' + signature)
    return MANDOR_RECEIPT_RELATIONS


def mandor_receipt_writers(result):
    writes = result['direct_watched_writes']
    require(all(relation in writes.get(signature, ()) for signature, relation in MANDOR_WRITERS.items()),
            'GLOBAL_MANDOR_RECEIPT_WRITER_NOT_COVERED_BY_ACTUAL_CATALOGUE')
    return {name: sorted(set(targets) & MANDOR_RECEIPT_RELATIONS) for name, targets in writes.items()
            if set(targets) & MANDOR_RECEIPT_RELATIONS}


def pinned(path, expected):
    raw = path.read_bytes()
    require(pin(raw) == expected, 'GLOBAL_WRITER_REUSE_EXACT_SOURCE_REQUIRED:' + path.name)
    return raw


def parser_for(source, runtime):
    source = source.resolve()
    raw = pinned(source, PARSER)
    pinned(source.parent / 'intake_common.py', COMMON)
    before = list(sys.path)
    try:
        sys.path[:0] = [str(runtime.resolve()), str(source.parent)]
        spec = importlib.util.spec_from_file_location('global_retained_exact_syntax_parser', source)
        module = importlib.util.module_from_spec(spec)
        exec(compile(raw, str(source), 'exec', dont_inherit=True), module.__dict__)
        return module.Parser()
    finally:
        sys.path[:] = before


def retained_facts(path):
    value = strict(pinned(path, CENSUS))
    fields(value, dict(functions_scanned=2979, exact_runtime_call_graph_claim=False,
                      global_writer_or_current_rights_or_phantom_closure=False), 'GLOBAL_RETAINED_SYNTAX_ONLY')
    require(len(value['functions']) == 2979, 'GLOBAL_COMPLETE_RETAINED_BODY_FACTS_REQUIRED')
    return value['functions']


def catalogue_index(names, *, functions=False):
    exact, simple = defaultdict(set), defaultdict(set)
    for identity in names:
        name = identity.split('(', 1)[0] if functions else identity
        exact[name].add(identity)
        simple[name.rsplit('.', 1)[-1]].add(identity)
    return exact, simple


def possible_targets(index, name):
    exact, simple = index
    return exact.get(name, ()) if '.' in name else simple.get(name, ())


def inventory(catalogue, retained, parser, watched_relations):
    functions, relations = catalogue['functions'], catalogue['relations']
    function_index = catalogue_index(functions, functions=True)
    relation_index = catalogue_index(relations)
    reused, parsed, changed_metadata, unresolved = [], [], [], {}
    callers, direct_writes = defaultdict(set), {}
    for identity, row in sorted(functions.items()):
        require(type(row) is list and len(row) == 19 and type(row[0]) is str and type(row[2]) is str,
                'GLOBAL_EXACT_FULL19_FUNCTION_ROW_REQUIRED:' + identity)
        old = retained.get(identity)
        if old and old['definition'] == pin(row[0].encode()) and old['language'] == row[2]:
            fact, calls = old, old['static_call_names']
            reused.append(identity)
            row_bytes = json.dumps(row, separators=(',', ':'), ensure_ascii=False).encode()
            if old['full19_row'] != pin(row_bytes):
                changed_metadata.append(identity)
        else:
            fact = parser.function(row[0], row[2])
            calls = fact['calls']
            parsed.append(identity)
        # Rebuild edges even for reused body facts. The current catalogue can
        # have different overloads, relations, owners or executable grants.
        for call in calls:
            for target in possible_targets(function_index, call):
                callers[target].add(identity)
        watched = {target for _, name in fact['writes'] for target in possible_targets(relation_index, name)
                   if target in watched_relations}
        if watched:
            direct_writes[identity] = sorted(watched)
        reasons = [key for key in ('outer_error', 'body_error', 'query_errors',
                                   'dynamic_PL_statements', 'opaque_language') if fact[key]]
        if reasons:
            unresolved[identity] = reasons
    closure = set(direct_writes)
    queue = list(closure)
    while queue:
        for caller in callers[queue.pop()] - closure:
            closure.add(caller)
            queue.append(caller)
    return dict(status=STATE, current_functions=len(functions), reused_body_fact_identities=reused,
                freshly_parsed_body_identities=parsed, reused_body_changed_full19_metadata=changed_metadata,
                removed_retained_function_identities=sorted(set(retained)-set(functions)),
                direct_watched_writes=direct_writes, transitive_static_candidates=sorted(closure),
                syntax_dynamic_or_opaque_obligations=unresolved,
                obligations_on_static_writer_candidates=sorted(set(unresolved)&closure),
                missing_watched_relations=sorted(watched_relations-set(relations)),
                current_call_and_relation_edges_rebuilt=True,
                complete_input_review=False, runtime_admission=False, actual_ERP_cases=0)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ('receipt', 'root', 'catalogue', 'historical', 'cache', 'writer-census',
                 'parser-source', 'parser-runtime', 'callback-review', 'output'):
        cli.add_argument('--' + name, type=Path, required=True)
    args = cli.parse_args()
    receipt, root, catalogue, history, cache = (path.read_bytes() for path in
        (args.receipt, args.root, args.catalogue, args.historical, args.cache))
    delta = verified_catalogue_review(receipt, root, catalogue, history, cache)
    callback_raw = pinned(args.callback_review, CALLBACKS)
    names = strict(callback_raw)['required_relation_lower_bound']
    require(names == sorted(set(names)) and len(names) == 276 and GLOBAL_INSTALL_TABLES <= set(names),
            'GLOBAL_PREPARED_RELATION_LOWER_BOUND_REQUIRED')
    current = checked_catalogue(catalogue)
    require(not GLOBAL_INSTALL_TABLES.intersection(current['relations']), 'GLOBAL_PARENT_MUST_PRECEDE_GLOBAL_INSTALLATION')
    mandor_receipts = mandor_receipt_scope(current)
    watched = (set(names) - GLOBAL_INSTALL_TABLES) | mandor_receipts
    result = inventory(current, retained_facts(args.writer_census),
                       parser_for(args.parser_source, args.parser_runtime), watched)
    result.update(verified_catalogue_delta=delta, prepared_callback_review=pin(callback_raw),
                  watched_relation_count=len(watched), verified_mandor_receipt_relations=sorted(mandor_receipts),
                  direct_mandor_receipt_writer_candidates=mandor_receipt_writers(result),
                  planned_private_tables=sorted(GLOBAL_INSTALL_TABLES), production_go=False, independent_acceptance=False)
    with args.output.open('x') as out:
        json.dump(result, out, indent=2)
        out.write('\n')
    print(json.dumps(dict(status=STATE, current_functions=result['current_functions'],
        exact_body_facts_reused=len(result['reused_body_fact_identities']),
        changed_or_new_bodies_parsed=len(result['freshly_parsed_body_identities']),
        actual_ERP_cases=0, complete_input_review=False)))


if __name__ == '__main__':
    main()
