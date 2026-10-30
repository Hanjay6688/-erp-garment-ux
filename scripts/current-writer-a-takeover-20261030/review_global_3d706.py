"""Bind prior source review to the qualified actual catalogue; no runtime credit."""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import argparse
import importlib.util
import json
import subprocess

HERE = Path(__file__).resolve().parent
HEAD = '3d7066b852176d9f343ec831d2f63aee6665579b'
TREE = 'c5a09173421af936df719971b2c5f1043d292818'
PINS = {
    'graph': (121604642, 'c45bd57f4d15905c1b94fc44b9dbe4883d764e0e263e1a6933a549c786ea9fbf'),
    'review': (302694, '30c448baaba7e0b7727a0422678e7ff7051648de0e37e2b1e0601fc1fabc916b'),
    'receipt': (8402, '5c23a9898c52d37d36df98e07d35993270167082fa342bc1653f21aa88359c18'),
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                            ensure_ascii=False).encode()).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def document(path, name):
    raw = path.read_bytes()
    require((len(raw), sha256(raw).hexdigest()) == PINS[name], 'EXACT_INPUT_REQUIRED:' + name)
    return json.loads(raw)


def review(graph, prior, metadata_receipt, source):
    require(graph['provenance']['actual_head'] == HEAD, 'EXACT_ACTUAL_HEAD_REQUIRED')
    require(metadata_receipt['head'] == HEAD and metadata_receipt['source_tree'] == TREE,
            'EXACT_METADATA_RECEIPT_REQUIRED')
    require(metadata_receipt['status'] == 'ROOT_EXACT_3D706_METADATA_GATE_AND_RAW_LOSSLESS_PROJECTION_PASS',
            'ROOT_METADATA_GATE_REQUIRED')
    catalog = graph['retained_actual_all22']
    require(digest(catalog) == graph['catalogue_sha256'], 'RETAINED_CATALOGUE_DIGEST_REQUIRED')
    types = load('root_global_context_types', HERE / 'context_types.py')
    original = types.classifier(source, corrected=False)(catalog)
    current = types.classifier(source)(catalog)
    require(original == graph['contexts'], 'ORIGINAL_CONTEXT_CLASSIFIER_REPRODUCTION_REQUIRED')
    require(len(current) == 55 and set(current) == set(graph['context_membership']['expected']),
            'EXACT_CONTEXT55_MEMBERSHIP_REQUIRED')
    expected = deepcopy(original)
    name = 'cp7_plan_native.apply_own_drafts'
    require(expected[name]['issues'] == ['WRONG_TRANSACTION_TYPE'], 'EXACT_ORIGINAL_FALSE_ALARM_REQUIRED')
    expected[name]['issues'] = []
    require(current == expected and not any(v['issues'] for v in current.values()),
            'ONLY_OBSERVED_TYPE_FALSE_ALARM_MAY_CHANGE')
    require(all(v['active_authority'] == 'UNKNOWN' and v['ephemeral'] is False for v in current.values()),
            'NO_CONTEXT_AUTHORITY_OR_EPHEMERAL_INFERENCE')

    records = prior['records']
    require(len(records) == 35 and len({x['function'] for x in records}) == 35
            and set(graph['all_dynamic_sql_candidates']) == {x['function'] for x in records},
            'EXACT_CURRENT_DYNAMIC35_MEMBERSHIP_REQUIRED')
    function_pins = {}
    relation_pins = {}

    def bind_function(signature, expected_hash):
        actual_hash = digest(catalog['functions'][signature])
        require(actual_hash == expected_hash, 'REVIEWED_FULL_FUNCTION19_CHANGED:' + signature)
        function_pins[signature] = actual_hash

    for record in records:
        bind_function(record['function'], record['source']['function19_sha256'])
        for target in record['dynamic_function_candidates']:
            bind_function(target['signature'], target['full19_sha256'])
        for target in record['dynamic_relation_candidates']:
            actual_hash = digest(catalog['relations'][target['name']])
            require(actual_hash == target['row_sha256'], 'REVIEWED_RELATION13_CHANGED:' + target['name'])
            relation_pins[target['name']] = actual_hash
    for anchor in prior['dependent_definition_anchors']:
        bind_function(anchor['function'], anchor['full19_sha256'])
    addendum = prior['positive_edge_addendum']
    for target in addendum['added_functions']:
        bind_function(target['signature'], target['full19_sha256'])

    enumeration = prior['current_enumeration_details']
    triggers = {}
    for row in enumeration['guard_child_trigger_bindings']:
        actual_hash = digest(catalog['triggers'][row['identity']])
        require(actual_hash == row['raw_row_sha256'], 'REVIEWED_TRIGGER16_CHANGED:' + row['identity'])
        triggers[row['identity']] = actual_hash
    constraints = {}
    for key, row in enumeration['product_FK_candidates'].items():
        require(catalog['constraints'][key] == row['full_constraint11_row'], 'REVIEWED_CONSTRAINT11_CHANGED:' + key)
        constraints[key] = digest(catalog['constraints'][key])
    change_columns = {}
    for row in enumeration['change_sources']:
        relation = row['schema'] + '.' + row['table']
        require(relation in catalog['relations'], 'CHANGE_SOURCE_RELATION_MISSING:' + relation)
        for column in row['columns']:
            key = relation + ':' + column
            require(key in catalog['columns'], 'CHANGE_SOURCE_COLUMN_MISSING:' + key)
            change_columns[key] = digest(catalog['columns'][key])
    for relation in enumeration['pool_relation_candidates']:
        require(relation in catalog['relations'], 'POOL_RELATION_MISSING:' + relation)

    original_functions = set(graph['outward_root_function_candidates'])
    expanded = set(original_functions)
    pending = list(expanded)
    while pending:
        signature = pending.pop()
        calls = set(graph['functions'][signature]['call_candidates'])
        calls.update(addendum['reviewed_dynamic_call_edges'].get(signature, []))
        for called in calls - expanded:
            require(called in graph['functions'], 'POSITIVE_CALL_TARGET_UNKNOWN:' + called)
            expanded.add(called)
            pending.append(called)
    added = sorted(expanded - original_functions)
    require(added == sorted(x['signature'] for x in addendum['added_functions']), 'POSITIVE_ADDED31_CHANGED')
    original_relations = set(graph['outward_root_relation_candidates'])
    expanded_relations = set(original_relations)
    for signature in expanded:
        expanded_relations.update(graph['functions'][signature]['relation_candidates'])
    added_relations = sorted(expanded_relations - original_relations)
    require(added_relations == sorted(addendum['added_relations']), 'POSITIVE_ADDED2_RELATIONS_CHANGED')

    resolved = {
        'CONTEXT_TYPE_OR_PERSISTENCE_UNREVIEWED': 'Exact context55 recheck with corrected type classifier; authority remains UNKNOWN.',
        'SUPPLEMENT_CALLER_FULL_CATALOGUE_ROWS_SEQUENCES_AND_RESTORE_EVIDENCE_REQUIRED':
            'Existing exact 3d706 root actual metadata receipt verifies the caller and restoration; no rerun or new runtime credit.',
    }
    require(set(resolved) <= set(graph['blockers']), 'ORIGINAL_BLOCKER_SET_CHANGED')
    return dict(status='ROOT_CONTEXT55_AND_PRIOR_DYNAMIC35_REBIND_PASS', actual_head=HEAD,
        actual_run=graph['provenance']['actual_run'], source_tree=TREE,
        inputs={k: dict(bytes=v[0], sha256=v[1]) for k, v in PINS.items()},
        catalogue_sha256=graph['catalogue_sha256'], type_derivation=types.derive(source)[1],
        corrected_context_count=len(current), corrected_contexts_sha256=digest(current),
        corrected_context_row=current[name], unchanged_other_contexts=54,
        dynamic_review_records=35, dependent_definition_anchors=len(prior['dependent_definition_anchors']),
        rebound_full_function19_rows=function_pins, rebound_relation13_rows=relation_pins,
        rebound_trigger16_rows=triggers, rebound_constraint11_rows=constraints,
        current_declared_change_columns=change_columns,
        declared_change_column_proof='Existence and current metadata only; no writer, permission or runtime closure.',
        source_resolution_counts=dict(Counter(x['resolution'] for x in records)),
        positive_call_edges=addendum['reviewed_dynamic_call_edges'],
        original_outward_functions=len(original_functions), expanded_positive_functions=len(expanded),
        added_positive_functions=added, added_positive_relations=added_relations,
        original_inventory_preserved=True, resolved_metadata_findings=resolved,
        remaining_blockers=sorted(set(graph['blockers']) - set(resolved)),
        raw_dependency_multisets_present=True, structural_dependency_closure='UNKNOWN',
        current_context_row_authority='UNKNOWN', all_contexts_ephemeral=False,
        writer_or_phantom_lock_closed=False, permission_closure='UNKNOWN',
        runtime_entry=None, actual_Native_credit=0, production_go=False, independent_acceptance=False)


def main():
    parser = argparse.ArgumentParser()
    for name in ('source', 'graph', 'review', 'receipt', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    root = args.source.resolve()
    tree = subprocess.check_output(['/usr/bin/git', '-C', str(root), 'rev-parse', 'HEAD^{tree}'], text=True).strip()
    require(tree == TREE, 'EXACT_ACTUAL_SOURCE_TREE_REQUIRED')
    ns = root / 'scripts/current-de-sku-global-census-multiset-qualification'
    admission = load('root_review_source_admission', ns / 'admission.py')
    context = load('root_review_source_fence', root / 'scripts/current-sku-managed-recovery-native27-qualification/source_context.py')
    with context.fenced_source_read() as fence:
        admitted = admission.preflight()
        source = (root / 'scripts/current-global-actual-writer-census-qualification/census.py').read_text()
        result = review(document(args.graph, 'graph'), document(args.review, 'review'),
                        document(args.receipt, 'receipt'), source)
    result['source_admission'] = admitted
    result['source_DB_guard'] = fence
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('status', 'corrected_context_count',
        'dynamic_review_records', 'expanded_positive_functions', 'remaining_blockers', 'actual_Native_credit')}))


if __name__ == '__main__':
    main()
