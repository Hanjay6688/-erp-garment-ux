"""Exact complete retained vendor engine; qualification-only current editor ABI."""
from pathlib import Path
from types import ModuleType, SimpleNamespace
import importlib.util
import os
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = ROOT/'scripts/current-s05-lawful-master-dates-qualification'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def runtime():
    admission = load('s05_current_AC_source_before_imports', HERE/'admission.py')
    admission.offline()
    inherited = load('s05_current_AC_unchanged_full_acl_engine', ROOT/'scripts/current-s05-public-default-acl-qualification/probe.py')
    engine = inherited.runtime()
    factory = load('s05_current_AC_only_private_recipe_factory', HERE/'factory.py')
    binding = load('s05_current_AC_actual_editor_guard', HERE/'binding.py')
    component_path = ROOT/'scripts/current-s05-native10-qualification/component.py'
    code, derivation = load('s05_current_AC_unchanged_one_component_binding', OLD/'component_derivation.py').derive(component_path.read_bytes())
    selected, installation = {}, {}

    def business(retained):
        selected['module'] = factory.business(retained, installation['state'])
        return selected['module']

    component = ModuleType('s05_current_AC_private_exact_component')
    component.__file__ = str(component_path)
    component.__S05_BUSINESS_FACTORY__ = business
    exec(compile(code, str(component_path), 'exec'), component.__dict__)

    def exercise(conn, cur, database, url, report, state):
        from cp7_vendor_receivable import composition as product
        from cp7_p21_current_chain_rehearsal_probe import helper
        component.require_local(conn, cur)
        observations = []
        report['current_editor_preflight_observations'] = observations
        # Current all22/source proof and editor identity precede ANY fixture.
        with helper.control.product_catalog(cur):
            report['current_editor_actual_parent_proof'] = product.verify(cur, state)
        binding.admit_editor(cur, state, observations)
        installation['state'] = state
        try:
            return component.exercise(conn, cur, database, url, report, state)
        finally:
            private = selected.get('module')
            report['current_AC_editor_fixture'] = dict(component_derivation=derivation,
                original_case_derivation=private.fixture_derivation if private else None,
                recipe_ABI_derivation=private.current_editor_derivation if private else None,
                actual_observed_editor_rows=private.current_editor_observations if private else [],
                actual_fixture_master_events=private.lawful_fixture_observations if private else [],
                all_original_ten_financial_callbacks_assertions_and_dates_unchanged=True,
                new_Native_function_rewrites=0, actual_editor_observations_are_not_financial_case_credit=True,
                production_go=False, independent_acceptance=False)
            installation.clear()

    engine.runner = SimpleNamespace(CASE=component.CASE, exercise=exercise, scheduler_quiet=component.scheduler_quiet)
    old_admitted = engine.admitted

    def admitted():
        proof = old_admitted()
        return dict(proof, current_AC_fixture_source=admission.offline(),
            private_component_derivation=derivation, failed_cdbdea_is_success_prerequisite=False)

    engine.admitted = admitted
    return engine


def check():
    boundary = load('s05_current_AC_retained_import_arguments', ROOT/'scripts/current-s05-native10-qualification/import_argv.py')
    with boundary.source_import_arguments():
        return runtime().admitted()


def execute():
    if os.environ.get('S05_NATIVE_CONFIRM') != 'cp6_rollback':
        raise ValueError('S05_EXPLICIT_LOCAL_QUALIFICATION_CONFIRMATION_REQUIRED')
    engine = runtime(); engine.admitted()
    engine.package._writer_runtime = lambda browser_mode=False: engine.run()
    engine.package.run('install')


if __name__ == '__main__':
    if sys.argv[1:] == ['--check']:
        import json
        print(json.dumps(check(), indent=2, default=str))
    elif not sys.argv[1:]:
        execute()
    else:
        raise SystemExit('Use --check for source-only admission; only root executes disposable Native qualification.')
