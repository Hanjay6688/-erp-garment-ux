"""Exact old complete engine plus one explicit private recipe dependency."""
from pathlib import Path
from types import ModuleType, SimpleNamespace
import importlib.util
import os
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = ROOT/'scripts/current-s05-public-default-acl-qualification'
COMPONENT = ROOT/'scripts/current-s05-native10-qualification/component.py'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value


def runtime():
    admission = load('s05_lawful_source_before_imports', HERE/'admission.py')
    admission.offline()
    inherited = load('s05_lawful_unchanged_full_acl_engine', OLD/'probe.py')
    engine = inherited.runtime()
    factory = load('s05_lawful_only_recipe_factory', HERE/'factory.py')
    code, derivation = load('s05_lawful_one_component_binding', HERE/'component_derivation.py').derive(COMPONENT.read_bytes())
    selected = {}

    def business(retained):
        selected['module'] = factory.business(retained)
        return selected['module']

    component = ModuleType('s05_lawful_private_exact_component')
    component.__file__ = str(COMPONENT)
    component.__S05_BUSINESS_FACTORY__ = business
    exec(compile(code, str(COMPONENT), 'exec'), component.__dict__)

    def exercise(conn, cur, database, url, report, state):
        try:
            return component.exercise(conn, cur, database, url, report, state)
        finally:
            private = selected.get('module')
            report['lawful_recipe_fixture'] = dict(
                component_derivation=derivation,
                private_cases_derivation=private.fixture_derivation if private else None,
                actual_fixture_master_events=private.lawful_fixture_observations if private else [],
                inherited_physical_dates_and_all_Native10_money_oracles_unchanged=True,
                initial_historical_BF_master_creation_claim=False,
                local_or_source_checks_grant_actual_Native_credit=False,
                production_go=False, independent_acceptance=False)

    engine.runner = SimpleNamespace(CASE=component.CASE, exercise=exercise, scheduler_quiet=component.scheduler_quiet)
    old_admitted = engine.admitted

    def admitted():
        proof = old_admitted()
        current = admission.offline()
        return dict(proof, lawful_fixture_source=current, private_component_derivation=derivation,
                    retained_911_is_success_prerequisite=False)

    engine.admitted = admitted
    return engine


def check():
    boundary = load('s05_lawful_retained_import_arguments', ROOT/'scripts/current-s05-native10-qualification/import_argv.py')
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
        raise SystemExit('Use --check for source-only admission; only root runs disposable qualification.')
