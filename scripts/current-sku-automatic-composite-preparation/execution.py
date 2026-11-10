"""Unarmed Native25 execution routes; every financial helper needs actual inputs.

Reuse the complete retained fetch, materialization, supervision and retention
implementations. Only explicit owning names, the fourth frozen source and the
private admission/runtime bindings differ. This module dispatches no workflow.
"""
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType, SimpleNamespace
import argparse
import importlib.util
import json
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRIOR = ROOT / 'scripts/current-sku-money-composite-preparation'
PINS = {
    'candidate': (5405, 'ca6829e41a08c20ac8f53148a2e163050a4bfe7e1ca3277b73d9a892a83b63a6'),
    'materialize': (2132, '388e3fd0d6bac6953ac6f9c0e69f441b834533d7a520b690eebb03186aec9554'),
    'fetch': (4596, 'e5d4033abda157ec254cfb645cffa73d8206d5fce1591831ba16e47e2459ecf7'),
    'supervisor': (2274, '232b020be549b58ece0521ebf6e785b62615126e6ef9b064260cd6c8d54847af'),
    'artifacts': (4122, '4923072e22e0582da6457d8a9ed8391053bf6f57f4481e7136b7004c81f706d3'),
    'receipts': (2184, 'e19c16b4c5786e2e798eb8fff5f07b0ab6642101ea3607f3c6de9f4c164ff2df'),
}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runtime = load('automatic_execution_exact_owning_runtime', HERE / 'qualification.py')


def require(value, message):
    if not value:
        raise ValueError(message)


def derive(kind, raw=None):
    require(kind in PINS, 'AUTOMATIC_FIXED_EXECUTION_HELPER_REQUIRED')
    if raw is None:
        name = 'candidate_source.py' if kind == 'candidate' else 'money_current_parent_' + kind + '.py'
        raw = (PRIOR / name).read_bytes()
    size, digest = PINS[kind]
    require(runtime.admission.pin(raw) == dict(bytes=size, sha256=digest),
            'AUTOMATIC_EXACT_RETAINED_EXECUTION_HELPER_REQUIRED:' + kind)
    text = raw.decode()
    routes = []
    if kind in ('materialize', 'fetch'):
        routes.append(('from money_execution_bindings import admission', 'admission = _ADMISSION'))
    if kind != 'receipts':
        routes.append(('import money_current_parent_runtime as runtime', 'runtime = _RUNTIME'))
    if kind == 'candidate':
        # This observer owns the frozen money19 reference, not the automatic25
        # reference in the new dispatch namespace. Preserve every source and
        # retained-report assertion; route only its exact reference directory.
        routes.append(('HERE=Path(__file__).resolve().parent', 'HERE=_MONEY_REFERENCE_ROOT'))
    if kind == 'materialize':
        routes.extend([
            ("folder in('qualified-mandor-parent','qualified-sku-money')",
             "folder in('qualified-mandor-parent','qualified-sku-money','qualified-sku-automatic')"),
            ("one('qualified-sku-money',admission.SKU_HEAD,admission.SKU_TREE)]",
             "one('qualified-sku-money',admission.SKU_HEAD,admission.SKU_TREE),\n"
             "             one('qualified-sku-automatic',*_AUTOMATIC)]"),
            ('No Git, filesystem inspection or ERP import before all ten gates.',
             'No Git, filesystem inspection or ERP import before all five actual owning gates.'),
            ('EXACT_ACCEPTED_MANDOR_SKU_AND_AFUI_WORKTREES_READY',
             'EXACT_ACCEPTED_MANDOR_SKU_AFUI_AND_AUTOMATIC_WORKTREES_READY'),
        ])
    elif kind == 'supervisor':
        routes.extend([
            ('SKU_CURRENT_PARENT_MONEY_RUNTIME_SUPERVISION.json', 'SKU_CURRENT_PARENT_MONEY_AUTOMATIC_RUNTIME_SUPERVISION.json'),
            ("os.environ.get('SKU_CURRENT_PARENT_MONEY_CONFIRM')", "os.environ.get('SKU_CURRENT_AUTOMATIC_CONFIRM')"),
            ("os.environ['SKU_CURRENT_PARENT_MONEY_JOB_START_MONOTONIC']", "os.environ['SKU_CURRENT_AUTOMATIC_JOB_START_MONOTONIC']"),
            ('    ("str(HERE/\'qualification.py\')","str(HERE/\'money_current_parent_runtime.py\')"),',
             '    # The retained Mandor worker already names the owning qualification.py.'),
            ('exact_routes=4', 'exact_routes=3'),
            ("str(HERE/'money_current_parent_supervisor.py')", "str(HERE/'execution.py')"),
        ])
    elif kind == 'artifacts':
        routes.extend([
            ('SKU_CURRENT_PARENT_MONEY_PREREQUISITE_FILES.json', 'SKU_CURRENT_PARENT_MONEY_AUTOMATIC_PREREQUISITE_FILES.json'),
            ("OWN/'SKU_CURRENT_PARENT_MONEY_FROZEN_EXECUTION'", "OWN/'SKU_CURRENT_PARENT_MONEY_AUTOMATIC_FROZEN_EXECUTION'"),
            ('SKU_CURRENT_PARENT_MONEY_FROZEN_EXECUTION_RECEIPT.json', 'SKU_CURRENT_PARENT_MONEY_AUTOMATIC_FROZEN_EXECUTION_RECEIPT.json'),
            ("FOLDERS=('qualified-mandor-parent','qualified-afui-parent','qualified-sku-money')",
             "FOLDERS=('qualified-mandor-parent','qualified-afui-parent','qualified-sku-money','qualified-sku-automatic')"),
            ('    sources=h.inventory(OWN);states={}',
             '    inventory=h.inventory(OWN)\n'
             '    owning_only={name:inventory[name] for name in sorted(_OWNING_ONLY & inventory.keys())}\n'
             '    sources={name:pin for name,pin in inventory.items() if name not in owning_only};states={}'),
            ('source_files=sources,frozen=states',
             'source_files=sources,owning_only_files=owning_only,frozen=states'),
        ])
    elif kind == 'receipts':
        before = text[text.index('NAMES='):text.index('\n\n\ndef receipts')]
        names = (
            'SKU_CURRENT_PARENT_MONEY_AUTOMATIC_RUNTIME_SUPERVISION.json', runtime.LABEL + '.json',
            runtime.component.LABEL + '.json', runtime.component.LABEL + '_PREFLIGHT.json',
            runtime.component.LABEL + '_BUSINESS_DAY_FIRST_ATTEMPT.json',
            'SKU_CURRENT_PARENT_MONEY_AUTOMATIC_BROWSER2.json',
            'SKU_CURRENT_PARENT_MONEY_AUTOMATIC_BROWSER_PREREQUISITES.json',
            'SKU_CURRENT_PARENT_MONEY_AUTOMATIC_FINAL_GATE.json', 'SKU_CURRENT_MANDOR17_ORIGINAL_ADMISSION.json',
            'SKU_CURRENT_PARENT_MONEY_AUTOMATIC_PREREQUISITE_FILES.json',
            'SKU_CURRENT_PARENT_MONEY_AUTOMATIC_FROZEN_EXECUTION_RECEIPT.json',
            'T3_PACKAGE_INSTALL.json', 'T3_BACKUP_RESTORE_DRILL.json', 'T3_PACKAGE_FILES_INSTALL.json',
            'SKU_COST_ARTIFACT_COPY_RECEIPT.json')
        routes.extend([
            (before, 'NAMES=' + repr(names)),
            ('SKU_CURRENT_PARENT_MONEY_ORIGINAL_FILE_RECEIPTS.json', 'SKU_CURRENT_PARENT_MONEY_AUTOMATIC_ORIGINAL_FILE_RECEIPTS.json'),
        ])
    for before, after in routes:
        require(text.count(before) == 1 and after not in text,
                'AUTOMATIC_EXACT_EXECUTION_ROUTE_REQUIRED:' + kind + ':' + before)
        text = text.replace(before, after, 1)
    recovered = text
    for before, after in reversed(routes):
        require(recovered.count(after) == 1, 'AUTOMATIC_EXACT_EXECUTION_INVERSE_ROUTE_REQUIRED:' + kind)
        recovered = recovered.replace(after, before, 1)
    require(recovered.encode() == raw, 'AUTOMATIC_COMPLETE_EXECUTION_HELPER_NOT_RECOVERED:' + kind)
    compile(text, str(HERE / ('derived_' + kind + '.py')), 'exec', dont_inherit=True)
    return text, dict(retained=runtime.admission.pin(raw), derived=runtime.admission.pin(text.encode()),
                      exact_reversible_routes=len(routes), complete_original_recovered=True,
                      financial_and_recovery_assertions_unchanged=True, actual_ERP_cases=0)


def admitted_context():
    # First action is the real five-gate/three-input admission. No model Root,
    # source-only graph marker or historical closed ten-gate module is accepted.
    originals = runtime.actual_inputs()
    parent_raw, money_raw, plan_raw, receipt = originals
    bridge, _ = runtime.money_binding.bind(parent_raw, money_raw, plan_raw)
    reference = runtime.assembly.prepared_sources()[0]['automatic_source']

    def actual_inputs():
        require(runtime.actual_inputs() == originals, 'AUTOMATIC_EXECUTION_ORIGINAL_INPUTS_CHANGED')
        return parent_raw, money_raw, receipt

    facade = SimpleNamespace(actual_inputs=actual_inputs, frozen=runtime.frozen,
                             FROZEN_SKU=runtime.FROZEN_SKU, admission=bridge.admission)
    return facade, bridge.admission, (reference['public_head'], reference['tree'])


def helper(kind, *, admitted=False):
    if admitted:
        facade, admission, automatic = admitted_context()
    else:
        # Failed-run retention/receipts and guarded database cleanup must still
        # work when admission failed. None of them grants financial admission.
        facade, admission, automatic = runtime, runtime.admission, None
    text, proof = derive(kind)
    module = ModuleType('automatic_complete_execution_' + kind)
    module.__file__ = str(HERE / ('derived_' + kind + '.py'))
    module.__dict__.update(_RUNTIME=facade, _ADMISSION=admission, _AUTOMATIC=automatic,
                           _MONEY_REFERENCE_ROOT=PRIOR)
    if kind == 'artifacts':
        source = load('automatic_execution_proof_namespace', HERE / 'check_source.py')
        module._OWNING_ONLY = frozenset(name.removeprefix(source.SKU_PROOF_ROOT)
                                        for name in source.SKU_PARENT_PROOF_FILES)
    exec(compile(text, module.__file__, 'exec', dont_inherit=True), module.__dict__)
    return module, proof


def prepare_history():
    """Restore only the retained, untracked proof inputs in all four trees."""
    _, admission, automatic = admitted_context()  # Real gates precede all reads.
    targets = (
        (runtime.FROZEN_PARENT, admission.PARENT_HEAD, admission.PARENT_TREE),
        (runtime.FROZEN_SKU, admission.SKU_HEAD, admission.SKU_TREE),
        (runtime.FROZEN_AFUI, runtime.report_io.COMPLETE_ORIGINALS_HEAD,
         runtime.report_io.COMPLETE_ORIGINALS_TREE),
        (runtime.assembly.FROZEN_AUTO, *automatic),
    )
    pins = {
        'materialize.py': dict(bytes=2153, sha256='53fbfe1cc59c77f49f67fcf4a6ebaa39395c2ae833942270a408a9a82bd99519'),
        'ARCHIVE.json': dict(bytes=10852, sha256='0abb7b292818d66e104d0174d790612049afe9efad099943744eb38b4daa7a8b'),
    }
    sources = []
    # Inspect every tree before writing the first proof input.
    for root, head, tree in targets:
        runtime.frozen(root, head, tree)
        here = root / 'scripts/current-workflow-history-isolation'
        for name, expected in pins.items():
            path = here / name
            require(path.is_file() and not any(p.is_symlink() for p in (path, *path.parents))
                    and runtime.admission.pin(path.read_bytes()) == expected,
                    'AUTOMATIC_EXACT_HISTORICAL_PROOF_MATERIALIZER_REQUIRED:' + root.name + ':' + name)
        sources.append((root, head, tree, here))
    result = []
    for root, head, tree, here in sources:
        proof = load('automatic_exact_history_' + root.name.replace('-', '_'), here / 'materialize.py').materialize()
        require(proof == dict(status='EXACT_HISTORICAL_PROOF_INPUTS_ONLY', files=24,
                             all_bytes_equal_frozen_original=True, Git_workflow_entries_restored=0,
                             active_workflow_behavior_added=False),
                'AUTOMATIC_EXACT_24_HISTORICAL_PROOF_INPUTS_REQUIRED')
        runtime.frozen(root, head, tree)
        result.append(dict(folder=root.name, **proof))
    return result


@contextmanager
def arguments(values):
    original, contents = sys.argv, list(sys.argv)
    sys.argv = original[:1] + list(values)
    try:
        yield
    finally:
        original[:] = contents
        sys.argv = original


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('materialize', 'fetch', 'check-money-source', 'prepare', 'retain', 'receipts', 'supervise'))
    parser.add_argument('--allow-database-stop', action='store_true')
    args = parser.parse_args()
    require(not args.allow_database_stop or args.command == 'supervise', 'AUTOMATIC_FIXED_CLEANUP_COMMAND_REQUIRED')
    financial = args.command in ('materialize', 'fetch', 'check-money-source', 'prepare') or (args.command == 'supervise' and not args.allow_database_stop)
    kind = {'check-money-source': 'candidate', 'prepare': 'artifacts', 'retain': 'artifacts', 'supervise': 'supervisor'}.get(args.command, args.command)
    module, _ = helper(kind, admitted=financial)
    if args.command == 'supervise':
        with arguments(['--allow-database-stop'] if args.allow_database_stop else []):
            return module.main()
    if args.command == 'fetch':
        parent_raw, *_ = runtime.actual_inputs()
        if json.loads(parent_raw).get('status') == runtime.money_binding.cumulative_parent.STATUS:
            load('automatic_cumulative_canonical_fetch', HERE / 'cumulative_fetch.py').main(runtime)
            runtime.frozen(runtime.FROZEN_SKU, module.admission.SKU_HEAD, module.admission.SKU_TREE)
            for entry in ('scripts/current-sku-moving-average-qualification/fetch_parent.py',
                          'scripts/current-sku-cost-money-qualification/fetch_moving_parent.py'):
                subprocess.run([sys.executable, '-B', str(runtime.FROZEN_SKU / entry)],
                               cwd=runtime.FROZEN_SKU, check=True)
        else:
            module.main()
        return 0
    if args.command == 'check-money-source':
        value, observation, raw = module.check_frozen()
        result = dict(status=value['status'], actual_ERP_cases=0, complete_candidate_rechecked=True,
                      source_report=runtime.admission.pin(raw), observation=observation)
    elif args.command == 'materialize':
        result = module.materialize()
        result['historical_proof_inputs'] = prepare_history()
    elif args.command == 'receipts':
        result = module.receipts(ROOT / 'cp6-proof/t3')
    else:
        result = getattr(module, {'materialize': 'materialize', 'prepare': 'prepare', 'retain': 'retain'}[args.command])()
    print(json.dumps(result, sort_keys=True), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
