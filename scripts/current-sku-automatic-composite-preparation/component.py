"""Derive the owning Native25 group without changing retained money cases."""
from hashlib import sha256
from pathlib import Path
from types import ModuleType, SimpleNamespace
import importlib.util
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ORIGINAL = 'scripts/current-sku-cost-money-qualification/runner.py'
LABEL = 'CP7_SKU_CURRENT_PARENT_MONEY_AUTOMATIC_NATIVE25'
CASE = 'CURRENT_MANDOR_PARENT_SKU_MONEY_AUTOMATIC_NATIVE25_AND_USED_INVERSE'
RETAINED = ROOT / 'scripts/current-sku-money-composite-preparation/component.py'
RETAINED_PIN = {'bytes': 3335, 'sha256': '4b94140c5c766b25302713b67a5bcc821c9199016d7783c926517666336e19bc'}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def derive(raw):
    retained = RETAINED.read_bytes()
    if dict(bytes=len(retained), sha256=sha256(retained).hexdigest()) != RETAINED_PIN:
        raise ValueError('SKU_AUTOMATIC_EXACT_CURRENT_MONEY_COMPONENT_DERIVER_REQUIRED')
    before, parent_proof = load('automatic_retained_money_component', RETAINED).derive(raw)
    routes = (
        ("prefix=load('sku_money_original_complete_sequence_prefix',_FROZEN_SKU/'scripts/current-sku-managed-recovery-native27-qualification/sequence_prefix.py')",
         "prefix=load('sku_money_original_complete_sequence_prefix',_FROZEN_SKU/'scripts/current-sku-managed-recovery-native27-qualification/sequence_prefix.py')\n"
         '    business,preflight=_NATIVE_SUITE.bind(business,preflight,product,prefix)'),
        ("with exact_public_catalog(native,retain_raw=True)as public:",
         "with _REPORT_IO.group_scope(native.r1),_CASE_OUTPUT.scope(native,'native'),exact_public_catalog(native,retain_raw=True)as public:"),
        ("                raw=original.read_bytes();(destination/name).write_bytes(raw)\n"
         "                retained.append(dict(name=name,bytes=len(raw),sha256=sha256(raw).hexdigest()))",
         "                retained.append(_COMPLETE_ORIGINALS.copy_exact(original,destination/name,\n"
         "                    'SKU_AUTOMATIC_COMPLETE_GROUP_ORIGINAL_CONFLICT'))"),
        ("LABEL='CP7_SKU_CURRENT_PARENT_MONEY_NATIVE19'", "LABEL='" + LABEL + "'"),
    )
    after = before
    for old, new in routes:
        if after.count(old) != 1 or new in after:
            raise ValueError('SKU_AUTOMATIC_ONE_REVIEWED_COMPONENT_ROUTE_REQUIRED')
        after = after.replace(old, new, 1)
    restored = after
    for old, new in reversed(routes):
        restored = restored.replace(new, old, 1)
    if restored != before:
        raise ValueError('SKU_AUTOMATIC_COMPLETE_MONEY_COMPONENT_NOT_RECOVERED')
    compile(after, 'current-automatic-native25-exact-owning-component', 'exec', dont_inherit=True)
    return after, dict(retained_money=parent_proof, exact_additional_routes=len(routes),
                       complete_money_component_recovered=True, source_sha256=sha256(after.encode()).hexdigest(),
                       retained_money19_assertions_and_used_guard_unchanged=True,
                       added_upstream_native_callbacks=6, actual_ERP_cases=0, production_go=False)


def load_prepared(bridge, product, parent_raw, money_raw, plan_raw, scheduler_quiet, *, case_output=None):
    bridge.admission.require_ready()  # Before caller, receipt, file, Git or ERP inspection.
    bridge.admission.inputs(parent_raw, money_raw, plan_raw)
    bridge.source_manifest()
    money_bridge = load('automatic_original_current_money_bridge',
                        ROOT / 'scripts/current-sku-money-composite-preparation/assembly.py')
    path = money_bridge.FROZEN_SKU / ORIGINAL
    if not path.is_file() or path.is_symlink():
        raise ValueError('SKU_AUTOMATIC_EXACT_FROZEN_NATIVE_MONEY_RUNNER_REQUIRED')
    source, proof = derive(path.read_bytes())
    module = ModuleType('current_automatic_exact_native25_component')
    module.__file__ = str(HERE / 'component.py')
    module._CURRENT_MONEY_ASSEMBLY = product
    module._FROZEN_SKU = money_bridge.FROZEN_SKU
    module._NATIVE_SUITE = load('automatic_complete_native25_suite', HERE / 'native_suite.py')
    ids = (tuple(money_bridge.prepared_sources()[0]['native_case_ids']) + module._NATIVE_SUITE.native.IDS
           + module._NATIVE_SUITE.invoices.IDS)
    if tuple(json.loads(plan_raw)['case_ids']) != ids:
        raise ValueError('SKU_AUTOMATIC_EXACT_ORDERED_MONEY19_AND_UPSTREAM_SIX_PLAN_REQUIRED')
    module._REPORT_IO = load('automatic_owning_group_report_IO', HERE / 'report_io.py')
    module._COMPLETE_ORIGINALS = module._REPORT_IO.complete_originals()
    if case_output is None:
        raise ValueError('SKU_AUTOMATIC_COMPLETE_CASE_OUTPUT_BINDING_REQUIRED')
    module._CASE_OUTPUT = case_output
    exec(compile(source, module.__file__ + '::complete_native25', 'exec', dont_inherit=True), module.__dict__)
    if module.ROOT != ROOT or module.LABEL != LABEL:
        raise ValueError('SKU_AUTOMATIC_EXACT_OWNING_NATIVE_OUTPUT_NAMESPACE_REQUIRED')
    _, _, output = case_output.binding(module.helper.control.native, 'native')
    return SimpleNamespace(CASE=CASE, LABEL=LABEL, exercise=module.exercise, scheduler_quiet=scheduler_quiet), dict(
        proof, complete_original_case_output=output)
