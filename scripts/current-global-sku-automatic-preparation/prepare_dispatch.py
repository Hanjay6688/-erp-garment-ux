"""Offline source closure; projections never become actual parent observations.

Supply the retained proof and exact automatic donor worktree. The original
dispatch parser is byte verified and reused without modifying its decisions.
Only exact definition/language facts may be reused from the previous review.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import argparse
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
INPUTS = {
    'mandor/evidence/ACTUAL25.json': (14755737, '80856b7ec2cebf08318a21617091b73c6744161b72bb3be98bcb9ecd2b8109eb'),
    'global/evidence/input-review/GLOBAL_INPUT_LITERAL13_AND_EXPRESSIONS_FIRST.json':
        (456316, '0f1b073b684eda4bf0780f22a11ebe38ee2e18d850b949235c45ab8265054faf'),
    'global/money-review/PREPARED_MONEY_PO_GLOBAL_SOURCE_CACHE.json':
        (273657, 'e1d371c838584fc30b1a7bb28dadab9fc889204625c1832fdffa2be256e4bf6d'),
    'global/money-review/PREPARED_MONEY_PO_GLOBAL_DISPATCH_INPUT_FIRST.json':
        (638122, '1021b85e354e7d7505a7113a6e5697c6a4bcbe0662a002727c0932a129fe56dc'),
    'global/review/original_c_contract.json': (5724, '44dda9c2f0833760957db3bd6353730ba8d37cd1f1525c303c595ce7290aeb21'),
    'global/review/original_compiled_input_review.json': (2203, '24b82aa82acb2f4ab4594f951fd37a8b89dff451ce81946d5145e7316ab56a9b'),
    'global/review/original_dispatch_inputs.py': (18374, '583a87ba25ed6ebf83b281c435a90336ec8b4031128e68707bdb07edf410846a'),
    'global/review/intake_common.py': (6518, '698216cfb4c31e8c93167e1b67f52f0b7532e5906ac8a09584b0a32c728b41e9'),
    'global/review/scan_saved_writer_census.py': (13782, '69adaed6494ea81cc93ed304718eda7a94131052a81ae3dbc2c8a6d54b4e045c'),
}


def require(value, message):
    if not value:
        raise ValueError(message)


def pin(raw):
    return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def function_body(definition):
    from pglast.parser import parse_sql_json
    items = json.loads(parse_sql_json(definition))['stmts']
    require(items and list(items[0]['stmt']) == ['CreateFunctionStmt']
            and all(list(item['stmt'])[0] in ('AlterOwnerStmt', 'GrantStmt') for item in items[1:]),
            'AUTOMATIC_DISPATCH_SINGLE_FUNCTION_WITH_DECLARED_OWNER_ACL_ONLY')
    stmt = items[0]['stmt']['CreateFunctionStmt']
    bodies = [x['DefElem']['arg']['List']['items'] for x in stmt['options']
              if x['DefElem']['defname'] == 'as']
    require(len(bodies) == 1 and len(bodies[0]) == 1, 'AUTOMATIC_DISPATCH_SINGLE_BODY_REQUIRED')
    return bodies[0][0]['String']['sval']


def prepare(evidence, sku_root, output):
    require(not output.exists(), 'AUTOMATIC_DISPATCH_FIRST_OUTPUT_MUST_NOT_BE_OVERWRITTEN')
    inputs = {}
    for name, (size, digest) in INPUTS.items():
        raw = (evidence / name).read_bytes()
        require(pin(raw) == dict(bytes=size, sha256=digest), 'AUTOMATIC_DISPATCH_EXACT_RETAINED_INPUT:' + name)
        inputs[name] = raw
    sys.path.insert(0, str(evidence / 'global/review'))
    original = module('automatic_exact_original_dispatch', evidence / 'global/review/original_dispatch_inputs.py')
    graph = module('automatic_source_dispatch_graph', HERE / 'routes.py')
    profile, reference = graph.sources()
    donor_tree = reference['automatic_source']['tree']
    # Verify each materialized compiler input before importing or reading it.
    names = ['private_delta.py', 'consumer_delta.py', 'reader_delta.py', 'credit_delta.py',
             'CATALOG_ADDITIONS.json', 'valuation.sql']
    paths = ['scripts/cp7_sku_moving_average/' + name for name in names]
    paths += ['scripts/cp7_sku_cost_components/CATALOG_ADDITIONS.json',
              'scripts/cp7_sku_automatic_pending/CATALOG_ADDITIONS.json']
    for name in paths:
        require((sku_root / name).read_bytes() == graph.base.git('show', donor_tree + ':' + name),
                'AUTOMATIC_DISPATCH_EXACT_MATERIALIZED_DONOR:' + name)
    retained = original.catalogue(inputs['mandor/evidence/ACTUAL25.json'])
    candidate = deepcopy(retained)
    changes = {}

    def replace(signature, row, label):
        before = candidate['functions'][signature]
        require(len(row) == 19 and row[1:] == before[1:], 'AUTOMATIC_DISPATCH_UNCHANGED_FULL19_METADATA:' + signature)
        candidate['functions'][signature] = deepcopy(row)
        origin = retained['functions'].get(signature)
        changes.setdefault(signature, dict(original=pin(origin[0].encode()) if origin else None, stages=[]))['stages'].append(
            dict(stage=label, before=pin(before[0].encode()), after=pin(row[0].encode())))

    moving = sku_root / 'scripts/cp7_sku_moving_average'
    for name in ('private_delta', 'consumer_delta', 'reader_delta', 'credit_delta'):
        compiler = module('automatic_dispatch_' + name, moving / (name + '.py'))
        for signature, definition in compiler.patched({s: retained['functions'][s][0] for s in compiler.SIGNATURES}).items():
            row = deepcopy(candidate['functions'][signature])
            row[0] = definition
            replace(signature, row, 'MOVING_AVERAGE_SOURCE')
    moving_profile = json.loads((moving / 'CATALOG_ADDITIONS.json').read_bytes())
    require(moving_profile['valuation_source'] == pin((moving / 'valuation.sql').read_bytes()),
            'AUTOMATIC_DISPATCH_EXACT_MOVING_DDL')

    def add_groups(groups, label):
        for group, entries in groups.items():
            require(not set(entries) & set(candidate[group]), 'AUTOMATIC_DISPATCH_NO_ADDITION_CONFLICT:' + label + ':' + group)
            candidate[group].update(deepcopy(entries))

    add_groups(moving_profile['groups'], 'MOVING')
    money = json.loads((sku_root / 'scripts/cp7_sku_cost_components/CATALOG_ADDITIONS.json').read_bytes())
    for label, delta, count in (('MONEY', money, 30), ('AUTOMATIC', profile, 9)):
        require(len(delta['replacement_functions']) == count, 'AUTOMATIC_DISPATCH_EXACT_REPLACEMENT_COUNT:' + label)
        for signature, row in delta['replacement_before'].items():
            require(candidate['functions'].get(signature) == row, 'AUTOMATIC_DISPATCH_EXACT_PARENT_FULL19:' + signature)
        for signature, row in delta['replacement_functions'].items():
            replace(signature, row, label)
        add_groups(delta['groups'], label)
    helpers, graph_proof = graph.derive()
    for name, definition in helpers.items():
        signature = 'cp7_global_nonpo_native_graph.' + name + '_v1(' + (
            'jsonb,boolean' if name == 'capture' else 'uuid[]' if name in ('scope', 'inspect') else '') + ')'
        row = deepcopy(candidate['functions'][signature])
        before, after = function_body(row[0]), function_body(definition)
        require(row[0].count(before) == 1, 'AUTOMATIC_DISPATCH_SINGLE_CANONICAL_GLOBAL_BODY')
        row[0] = row[0].replace(before, after, 1)
        require(function_body(row[0]) == after, 'AUTOMATIC_DISPATCH_EXACT_GLOBAL_BODY')
        replace(signature, row, 'GLOBAL_AUTOMATIC_OBSERVATION')
    prior = json.loads(inputs['global/evidence/input-review/GLOBAL_INPUT_LITERAL13_AND_EXPRESSIONS_FIRST.json'])
    new_functions = set(profile['groups']['functions']) | set(profile['replacement_functions'])
    require(len(new_functions) == 19, 'AUTOMATIC_DISPATCH_EXPLICIT_NINETEEN_AUTOMATIC_SEEDS')
    prior['all_branch_reachable_function_candidates'] = sorted(set(prior['all_branch_reachable_function_candidates']) | new_functions)
    trigger_scope = module('automatic_exact_trigger_argument_dispatch', HERE / 'trigger_dispatch.py').bind(candidate, retained, prior)
    cache = json.loads(inputs['global/money-review/PREPARED_MONEY_PO_GLOBAL_SOURCE_CACHE.json'])
    contract = json.loads(inputs['global/review/original_c_contract.json'])
    builtin = json.loads(inputs['global/review/original_compiled_input_review.json'])['unknown_type_resolution']
    require(set(builtin['exact_builtin_catalogue_records']) == {'regproc', 'regoper'},
            'AUTOMATIC_DISPATCH_RETAINED_EXPLICIT_BUILTIN_RESOLUTION')
    original.BUILTIN |= {'regproc', 'regoper'}
    captured = {}
    definition_names = {pin(row[0].encode())['sha256']: sig for sig, row in candidate['functions'].items()}
    parser_class = original.DispatchParser

    class RecordingParser(parser_class):
        def inspect_function(self, row):
            value = super().inspect_function(row)
            signature = definition_names[pin(row[0].encode())['sha256']]
            encoded = {key: sorted(item) if isinstance(item, set) else item for key, item in value.items()}
            captured[signature] = dict(encoded, definition=pin(row[0].encode()), language=row[2])
            return value

    original.DispatchParser = RecordingParser
    projected = (json.dumps({key: sorted(rows.items()) for key, rows in candidate.items()}, separators=(',', ':')) + '\n').encode()
    try:
        report = original.review(projected, prior, contract, cache)
    finally:
        original.DispatchParser = parser_class
    previous = json.loads(inputs['global/money-review/PREPARED_MONEY_PO_GLOBAL_DISPATCH_INPUT_FIRST.json'])
    require(new_functions <= set(report['selected_function_identities']), 'AUTOMATIC_DISPATCH_ALL_AUTOMATIC_BODIES_REVIEWED')
    report['prepared_metadata_input'] = report.pop('original_full25')
    report['exact_source_body_projections_reused'] = report.pop('saved_actual_DE_dispatch_projections_reused')
    report.update(status='AUTOMATIC_GLOBAL_SOURCE_EXPECTATION_ONLY_NOT_ACTUAL_PARENT_OR_ACCEPTANCE',
                  exact_retained_inputs={key: pin(raw) for key, raw in inputs.items()},
                  automatic_source=reference['automatic_source'], unqualified_source_changes=changes,
                  automatic_function_seeds=sorted(new_functions), graph_source_routes=graph_proof['derived_helpers'],
                  exact_additional_trigger_dispatch=trigger_scope,
                  new_physical_relation_candidates=sorted(set(report['physical_relation_candidates']) - set(previous['physical_relation_candidates'])),
                  new_possible_write_relations=sorted(set(report['possible_write_relations']) - set(previous['possible_write_relations'])),
                  reuse_includes_unqualified_source_expectations_not_actual_database_observations=True,
                  proposed_catalogue_is_not_actual_or_final_parent=True,
                  all_writer_actual_complete_input_review_still_required=True)
    facts = {}
    for signature in report['selected_function_identities']:
        value = captured.get(signature, cache['facts'].get(signature))
        require(value is not None and value['definition'] == pin(candidate['functions'][signature][0].encode())
                and value['language'] == candidate['functions'][signature][2], 'AUTOMATIC_DISPATCH_EXACT_REUSABLE_FACT:' + signature)
        facts[signature] = value
    output.mkdir(parents=True)
    (output / 'DISPATCH_REPORT.json').write_text(json.dumps(report, indent=2) + '\n')
    (output / 'SOURCE_CACHE.json').write_text(json.dumps(dict(classification='SOURCE_EXPECTATION_ONLY_NOT_ACTUAL_FINANCIAL_ACCEPTANCE', facts=facts), indent=2) + '\n')
    print(json.dumps({key: report[key] for key in ('status', 'selected_current_bodies_with_dispatch_projection',
        'selected_bodies_parsed_for_NEW_dispatch_projection', 'exact_source_body_projections_reused',
        'new_physical_relation_candidates', 'new_possible_write_relations', 'unknown_type_names', 'unresolved_opaque',
        'unresolved_dynamic', 'unresolved_qualified_calls', 'unresolved_qualified_relations', 'source_projection_has_no_unresolved')}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--sku-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.evidence.resolve(), args.sku_root.resolve(), args.output.resolve())
