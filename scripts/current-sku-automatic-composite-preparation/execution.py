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
    module.__dict__.update(_RUNTIME=facade, _ADMISSION=admission, _AUTOMATIC=automatic)
    exec(compile(text, module.__file__, 'exec', dont_inherit=True), module.__dict__)
    return module, proof


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
        module.main()
        return 0
    if args.command == 'check-money-source':
        value, observation, raw = module.check_frozen()
        result = dict(status=value['status'], actual_ERP_cases=0, complete_candidate_rechecked=True,
                      source_report=runtime.admission.pin(raw), observation=observation)
    elif args.command == 'receipts':
        result = module.receipts(ROOT / 'cp6-proof/t3')
    else:
        result = getattr(module, {'materialize': 'materialize', 'prepare': 'prepare', 'retain': 'retain'}[args.command])()
    print(json.dumps(result, sort_keys=True), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
