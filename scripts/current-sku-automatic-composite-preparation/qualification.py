"""Unarmed full owning Native25 entry over the exact accepted Mandor parent.

This stage executes no ERP work on import. A source check never substitutes
for a genuine parent Root, financial execution or complete outer restoration.
"""
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType
import argparse
import importlib.util
import json
import os
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ENTRY = 'scripts/current-sku-automatic-composite-preparation/qualification.py'
BRANCH = 'refs/heads/astra-a/sku-current-parent-money-automatic-native25-20261105'
LABEL = 'CP7_SKU_CURRENT_PARENT_MONEY_AUTOMATIC_QUALIFICATION'
FROZEN_PARENT = ROOT.parent / 'qualified-mandor-parent'
FROZEN_SKU = ROOT.parent / 'qualified-sku-money'
FROZEN_AFUI = ROOT.parent / 'qualified-afui-parent'
PARENT_FILE = HERE / 'MANDOR17_PARENT_ROOT_ACTUAL_INTAKE.json'
MONEY_FILE = ROOT / 'scripts/current-sku-money-composite-preparation/SKU_MONEY_PREPARED_SOURCE_INTAKE.json'
PLAN_FILE = HERE / 'PREPARED_NATIVE25_PLAN.json'
CASE_OUTPUT_PATH = 'scripts/cp7_accessory_nonpayable/case_output.py'
CASE_OUTPUT_PIN = dict(bytes=6200, sha256='53cad5f461603efbf84533d6c5804612901137d495af59a0de942f7df52baca5')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


assembly = load('automatic_owning_source_assembly', HERE / 'assembly.py')
admission = assembly.admission
component = load('automatic_owning_native25_component', HERE / 'component.py')
package_source = load('automatic_owning_complete_package', HERE / 'package.py')
report_io = load('automatic_owning_atomic_report_output', HERE / 'report_io.py')
modules = load('automatic_owning_inherited_module_selection', HERE / 'module_scope.py')
authority = load('automatic_owning_private_authority', HERE / 'advisor_review.py')
money_binding = load('automatic_owning_private_money_binding', HERE / 'money_binding.py')


def require(value, message):
    if not value:
        raise ValueError(message)


def actual_inputs():
    admission.require_ready()  # Before receipts, files, Git or ERP imports.
    require(admission.OWNING_RUNTIME_ENTRY == ENTRY, 'SKU_AUTOMATIC_EXACT_OWNING_RUNTIME_ENTRY_REQUIRED')
    for path in (PARENT_FILE, MONEY_FILE, PLAN_FILE):
        require(path.is_file() and not any(part.is_symlink() for part in (path, *path.parents)),
                'SKU_AUTOMATIC_EXACT_REGULAR_INPUT_ORIGINAL_REQUIRED')
    raw = PARENT_FILE.read_bytes(), MONEY_FILE.read_bytes(), PLAN_FILE.read_bytes()
    return (*raw, admission.inputs(*raw))


def frozen(root, head, tree):
    require(root.is_dir() and not root.is_symlink(), 'SKU_AUTOMATIC_EXACT_FROZEN_DIRECTORY_REQUIRED')
    def git(*args):
        return subprocess.check_output(['git', '-C', str(root), *args],
            env=dict(os.environ, GIT_NO_LAZY_FETCH='1'), text=True).strip()
    require(git('rev-parse', 'HEAD') == head and git('rev-parse', 'HEAD^{tree}') == tree,
            'SKU_AUTOMATIC_EXACT_FROZEN_HEAD_AND_TREE_REQUIRED')
    require(not git('status', '--porcelain', '--untracked-files=no'), 'SKU_AUTOMATIC_FROZEN_SOURCE_CHANGED')


def frozen_afui():
    frozen(FROZEN_AFUI, report_io.COMPLETE_ORIGINALS_HEAD, report_io.COMPLETE_ORIGINALS_TREE)


def complete_case_output():
    path = FROZEN_AFUI / CASE_OUTPUT_PATH
    require(path.is_file() and not path.is_symlink() and admission.pin(path.read_bytes()) == CASE_OUTPUT_PIN,
            'SKU_AUTOMATIC_EXACT_COMPLETE_CASE_OUTPUT_SOURCE_REQUIRED')
    original = load('automatic_exact_Afui_complete_case_output', path)
    return money_binding.private_module(original, dict(OUT=ROOT / 'cp6-proof/t3/SKU_AUTOMATIC_CASE_STDOUT'))


@contextmanager
def inherited_scope():
    original = sys.argv
    contents = list(original)
    sys.argv = original[:1]
    try:
        with modules.scope(FROZEN_PARENT / 'scripts/current-mandor-shop-native-qualification'):
            yield
    finally:
        original[:] = contents
        sys.argv = original


def runtime():
    parent_raw, money_raw, plan_raw, receipt = actual_inputs()
    assembly.source_manifest()
    frozen_afui()
    # Binding validates the actual Root with the retained admission before
    # loading any inherited financial runtime. Original money gates stay None.
    bridge, binding_proof = money_binding.bind(parent_raw, money_raw, plan_raw)
    frozen(FROZEN_PARENT, bridge.admission.PARENT_HEAD, bridge.admission.PARENT_TREE)
    frozen(FROZEN_SKU, bridge.admission.SKU_HEAD, bridge.admission.SKU_TREE)
    reference = assembly.prepared_sources()[0]
    frozen(assembly.FROZEN_AUTO, reference['automatic_source']['public_head'], reference['automatic_source']['tree'])
    qualifier = FROZEN_PARENT / 'scripts/current-mandor-shop-native-qualification'
    import_closure = modules.require_import_closure(qualifier)
    with inherited_scope():
        inherited = load('automatic_actual_accepted_Mandor_entry', qualifier / 'qualification.py').runtime()
        with inherited.inherited_admission.parent_scope():
            parent_proof = inherited.admitted()
            previous_path = list(sys.path)
            try:
                for root in (assembly.FROZEN_AUTO, FROZEN_SKU):
                    sys.path.insert(1, str(root / 'scripts'))
                for package, expected in (('cp7_sku_cost_components', FROZEN_SKU / 'scripts/cp7_sku_cost_components'),
                                          ('cp7_sku_moving_average', FROZEN_SKU / 'scripts/cp7_sku_moving_average'),
                                          ('cp7_sku_pending_accounting', assembly.FROZEN_AUTO / 'scripts/cp7_sku_pending_accounting'),
                                          ('cp7_sku_automatic_pending', assembly.FROZEN_AUTO / 'scripts/cp7_sku_automatic_pending')):
                    modules.select_package(package, expected)
                from cp7_sku_cost_components import composition as money_product
                from cp7_sku_automatic_pending import composition as automatic_product
                product = assembly.load_prepared(bridge, inherited.product, money_product, automatic_product,
                                                 parent_raw, money_raw, plan_raw)
                original = FROZEN_PARENT / package_source.load('automatic_exact_retained_money_package', package_source.RETAINED).ORIGINAL
                text, package_proof = package_source.derive(original.read_bytes())
                engine = ModuleType('current_parent_money_automatic_native25_whole_package')
                engine.__file__ = str(original)
                engine.__dict__[report_io.HELPER] = report_io.write_complete
                exec(compile(text, engine.__file__ + '::current-automatic-native25', 'exec', dont_inherit=True), engine.__dict__)
                engine.product = product
                case_output = complete_case_output()
                engine.runner, component_proof = component.load_prepared(assembly, product, parent_raw, money_raw, plan_raw,
                                                                         inherited.runner.scheduler_quiet, case_output=case_output)
                engine.current_advisor = authority.bind(inherited.current_advisor, FROZEN_PARENT)
                engine.trusted_installer_connection = inherited.trusted_installer_connection
                engine.inherited_admission = inherited.inherited_admission
                engine.IDS = (component.CASE,)
                engine.LABEL = LABEL
                engine.REPO = ROOT
                engine.PRE_DUMP = '/tmp/current_parent_money_automatic_native25_pre.dump'
                engine.OUT = ROOT / 'cp6-proof/t3' / (LABEL + '.json')
                engine.prepared_parent_proof = parent_proof
                def admitted():
                    require(actual_inputs() == (parent_raw, money_raw, plan_raw, receipt),
                            'SKU_AUTOMATIC_ACTUAL_PARENT_SOURCE_OR_PLAN_CHANGED')
                    frozen(FROZEN_PARENT, bridge.admission.PARENT_HEAD, bridge.admission.PARENT_TREE)
                    frozen(FROZEN_SKU, bridge.admission.SKU_HEAD, bridge.admission.SKU_TREE)
                    frozen(assembly.FROZEN_AUTO, reference['automatic_source']['public_head'], reference['automatic_source']['tree'])
                    source = load('automatic_owning_actual_source_fence', HERE / 'check_source.py').check(runtime=True)
                    return dict(status='ACTUAL_CURRENT_MANDOR_AND_EXACT_AUTOMATIC_SOURCES_ADMITTED_RUNTIME_STILL_REQUIRED',
                                receipt=receipt, owning_source=source, parent_source=inherited.admitted(),
                                complete_combined_sources=product.sources(), private_money_binding=binding_proof,
                                package_derivation=package_proof, component_derivation=component_proof,
                                actual_inherited_import_closure=import_closure,
                                complete_case_output_source=CASE_OUTPUT_PIN,
                                private_authority_source=authority.source(), actual_ERP_cases=0,
                                actual_Auth_HTTP_cases=0, actual_browser_cases=0, production_go=False, independent_acceptance=False)
                engine.admitted = admitted
                return engine
            finally:
                sys.path[:] = previous_path


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--runtime', action='store_true')
    args = parser.parse_args()
    actual_inputs()
    require(os.environ.get('GITHUB_REF') == BRANCH, 'SKU_AUTOMATIC_SINGLE_OWNING_BRANCH_REQUIRED')
    require(os.environ.get('SKU_CURRENT_AUTOMATIC_CONFIRM') == 'cp6_rollback', 'SKU_AUTOMATIC_EXPLICIT_DISPOSABLE_CONFIRMATION')
    frozen_afui()
    if args.check:
        fence = load('automatic_exact_source_import_DB_fence',
                     FROZEN_AFUI / 'scripts/current-sku-managed-recovery-native27-qualification/source_context.py')
        with fence.fenced_source_read() as guard, inherited_scope():
            engine = runtime()
            with engine.inherited_admission.parent_scope():
                proof = engine.admitted()
                browser_preflight = load('automatic_current_browser_before_any_database', HERE / 'browser_preflight.py').check(runtime=True)
                browser_binding = load('automatic_actual_browser_fixture_before_any_database', HERE / 'browser_binding.py')
                _, browser_fixture = browser_binding.fixture(engine.product)
        print(json.dumps(dict(source=proof, source_DB_guard=guard, browser_source_preflight=browser_preflight,
                              actual_browser_fixture_source_binding=browser_fixture, actual_SQL_executed=0)))
        return
    attempts = load('automatic_unchanged_real_WIB_day_window', FROZEN_AFUI / 'scripts/current-de-free-date-preparation/attempt_policy.py')
    attempts.require_window()
    with inherited_scope():
        engine = runtime()
        with engine.inherited_admission.parent_scope():
            engine.admitted()
            import cp6_auditor_business_day as business_day
            identity = load('automatic_owning_exact_run_identity', ROOT / 'scripts/current-mandor-shop-native-qualification/package_identity.py')
            prior_runtime, prior_output = engine.package._writer_runtime, engine.package.OUT
            try:
                engine.package._writer_runtime = lambda browser_mode=False: engine.run()
                engine.package.OUT = ROOT / 'cp6-proof/t3'
                with identity.scope(), attempts.single_attempt(business_day):
                    engine.package.run('install')
            finally:
                engine.package._writer_runtime, engine.package.OUT = prior_runtime, prior_output


if __name__ == '__main__':
    main()
