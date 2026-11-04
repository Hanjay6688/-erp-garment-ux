"""Observe the money graph after genuine Mandor Root review, with gates closed.

The integrator supplies the exact Root pin already verified against the
terminal owning run and canonical Originals. This source-only observer cannot
prove that upstream financial qualification itself. It never substitutes a
graph placeholder, changes admission values, installs or dispatches anything.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import re
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('automatic_source_intake_owning_entry', HERE / 'qualification.py')
entry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(entry)
MONEY_PIN = dict(bytes=368964, sha256='55c13119aef4a9307b1638864b8eec3199e574a8876c26aa3254aa0920b1a8cb')
AFUI_HEAD = '92a376091a1d1ea9901648e614f3e5212677a81f'
AFUI_TREE = 'ef194e421402ae1e45625e2d57f58c848ef9e08f'


def require(value, message):
    if not value:
        raise ValueError(message)


def inputs(expected_parent):
    require(all(getattr(entry.admission, name) is None for name in entry.admission.GATES),
            'AUTOMATIC_SOURCE_INTAKE_REQUIRES_ALL_FIVE_FINANCIAL_GATES_CLOSED')
    require(type(expected_parent) is dict and set(expected_parent) == {'bytes', 'sha256'}
            and type(expected_parent['bytes']) is int and expected_parent['bytes'] > 0
            and type(expected_parent['sha256']) is str and re.fullmatch('[a-f0-9]{64}', expected_parent['sha256']),
            'AUTOMATIC_SOURCE_INTAKE_EXACT_REVIEWED_ACTUAL_PARENT_PIN_REQUIRED')
    for path in (entry.PARENT_FILE, entry.MONEY_FILE):
        require(path.is_file() and not any(part.is_symlink() for part in (path, *path.parents)),
                'AUTOMATIC_SOURCE_INTAKE_GENUINE_REGULAR_INPUT_ORIGINAL_REQUIRED')
    parent_raw, money_raw = entry.PARENT_FILE.read_bytes(), entry.MONEY_FILE.read_bytes()
    require(entry.admission.pin(parent_raw) == expected_parent and entry.admission.pin(money_raw) == MONEY_PIN,
            'AUTOMATIC_SOURCE_INTAKE_REVIEWED_PARENT_OR_IMMUTABLE_MONEY_SOURCE_CHANGED')
    return parent_raw, money_raw


def observe(expected_parent):
    parent_raw, money_raw = inputs(expected_parent)
    entry.assembly.source_manifest()  # Still a closed preparation, never adopted.
    root = json.loads(parent_raw)
    reference = entry.money_binding.load('automatic_graph_exact_retained_money_bridge', entry.money_binding.PRIOR).prepared_sources()[0]
    entry.frozen(entry.FROZEN_PARENT, root['head'], root['tree'])
    entry.frozen(entry.FROZEN_SKU, reference['candidate_head'], reference['candidate_tree'])
    entry.frozen(entry.FROZEN_AFUI, AFUI_HEAD, AFUI_TREE)
    import_closure = entry.modules.require_import_closure(
        entry.FROZEN_PARENT / 'scripts/current-mandor-shop-native-qualification')
    fence = entry.load('automatic_graph_exact_source_DB_network_fence',
                       entry.FROZEN_AFUI / 'scripts/current-sku-managed-recovery-native27-qualification/source_context.py')
    with fence.fenced_source_read() as guard, entry.inherited_scope():
        def unchanged():
            require(inputs(expected_parent) == (parent_raw, money_raw), 'AUTOMATIC_SOURCE_INTAKE_INPUTS_CHANGED')
            require(not guard['attempts'] and not guard['network_nonGit_attempts'],
                    'AUTOMATIC_SOURCE_INTAKE_DATABASE_OR_NETWORK_ATTEMPTED')

        bridge, binding_proof = entry.money_binding._private_bridge(parent_raw, money_raw, unchanged)
        qualifier = entry.FROZEN_PARENT / 'scripts/current-mandor-shop-native-qualification'
        inherited = entry.load('automatic_graph_actual_Mandor_entry', qualifier / 'qualification.py').runtime()
        with inherited.inherited_admission.parent_scope():
            parent_source = inherited.admitted()
            original_path = list(sys.path)
            try:
                sys.path.insert(1, str(entry.FROZEN_SKU / 'scripts'))
                for package in ('cp7_sku_moving_average', 'cp7_sku_cost_components'):
                    entry.modules.select_package(package, entry.FROZEN_SKU / 'scripts' / package)
                from cp7_sku_cost_components import composition as money_module
                money = bridge.load_prepared(inherited.product, money_module, parent_raw, money_raw)
                complete_graph = money.sources()
                unchanged()
            finally:
                sys.path[:] = original_path
    require(not guard['attempts'] and not guard['network_nonGit_attempts'],
            'AUTOMATIC_SOURCE_INTAKE_DATABASE_OR_NETWORK_ATTEMPTED')
    require(inputs(expected_parent) == (parent_raw, money_raw), 'AUTOMATIC_SOURCE_INTAKE_INPUTS_CHANGED_AFTER_FENCE')
    entry.frozen(entry.FROZEN_PARENT, root['head'], root['tree'])
    entry.frozen(entry.FROZEN_SKU, reference['candidate_head'], reference['candidate_tree'])
    entry.frozen(entry.FROZEN_AFUI, AFUI_HEAD, AFUI_TREE)
    return dict(classification='CURRENT_MANDOR_MONEY_GRAPH_SOURCE_OBSERVATION_NOT_FINANCIAL_ACCEPTANCE',
                parent_root=expected_parent, immutable_money_source=MONEY_PIN,
                proposed_CURRENT_MONEY_GRAPH_PIN=entry.admission.pin(entry.admission.canonical(complete_graph)),
                complete_current_money_graph=complete_graph, complete_parent_source_admission=parent_source,
                private_money_binding=binding_proof, database_network_guard=guard,
                actual_parent_import_closure=import_closure,
                all_five_financial_gates_still_closed=True, graph_placeholder_used=False,
                upstream_terminal_run_and_canonical_Root_review_required=True,
                financial_runtime_activated=False, actual_ERP_cases=0, actual_Auth_HTTP_cases=0,
                actual_browser_cases=0, production_go=False, independent_acceptance=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--reviewed-parent-bytes', type=int, required=True)
    parser.add_argument('--reviewed-parent-sha256', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    expected = dict(bytes=args.reviewed_parent_bytes, sha256=args.reviewed_parent_sha256)
    result = observe(expected)
    target = Path(args.output).absolute()
    require(not target.exists() and not target.is_symlink(), 'AUTOMATIC_SOURCE_INTAKE_FIRST_OBSERVATION_MUST_SURVIVE')
    helper = entry.report_io.complete_originals()
    helper.save_sorted(target, result, 'AUTOMATIC_SOURCE_INTAKE_COMPLETE_OBSERVATION_CONFLICT')
    print(json.dumps(dict(classification=result['classification'],
                          proposed_CURRENT_MONEY_GRAPH_PIN=result['proposed_CURRENT_MONEY_GRAPH_PIN'],
                          complete_observation=helper.pin(target), actual_ERP_cases=0, financial_runtime_activated=False)))


if __name__ == '__main__':
    main()
