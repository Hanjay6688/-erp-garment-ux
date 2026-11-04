"""Private provider binding over the exact retained closed Global installer."""
from pathlib import Path
from types import FunctionType, ModuleType, SimpleNamespace
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


routes = load('global_automatic_install_observation_routes', HERE / 'routes.py')
callbacks = load('global_automatic_complete_source_callback_review', HERE / 'callback_preflight.py')
parent = load('global_automatic_retained_closed_installer', ROOT / 'scripts/current-global-sku-money-preparation/install_routes.py')
base, original, admission = routes.base, parent.original, parent.admission
GATES = parent.GATES
PLAN = HERE / 'INSTALL_PLAN.json'


def sql_sources():
    result = parent.sql_sources()
    helpers, _ = routes.derive()
    for name, text in helpers.items():
        result['graph_helpers/' + name + '.sql'] = text
    return result


def build_plan():
    parent.exact_original()
    namespace = dict(parent.build_install_plan.build.__globals__)
    namespace['composition'] = SimpleNamespace(sql_sources=sql_sources, CONTRACT=original.CONTRACT)
    return FunctionType(parent.build_install_plan.build.__code__, namespace, 'build')()


def require_input_relations(profile):
    parent.callbacks.require_input_relations(profile)
    required = set(callbacks.requirements()['required_relation_lower_bound'])
    names = profile['relations']
    missing = required - set(names)
    base.require(not missing, 'GLOBAL_AUTOMATIC_INPUT_RELATIONS_MISSING:' + ','.join(sorted(missing)))
    return dict(required_relation_lower_bound=len(required), complete_input_review=False,
                actual_final_parent_adopted=False, current_catalogue_and_all_writer_review_still_required=True)


def check_sources():
    parent.check_sources()
    value = json.loads((HERE / 'SOURCE.json').read_bytes())
    base.require(value['contract'] == 'cp7.global-automatic-closed-preparation.v1'
                 and value['runtime_entry'] is None and value['actual_ERP_cases'] == 0,
                 'GLOBAL_AUTOMATIC_PREPARATION_ONLY')
    required = {str(path.relative_to(ROOT)) for path in HERE.iterdir() if path.is_file() and path.name != 'SOURCE.json'}
    base.require(set(value['files']) == required, 'GLOBAL_AUTOMATIC_COMPLETE_OWN_PROVIDER_MANIFEST_REQUIRED')
    for name, expected in value['files'].items():
        path = ROOT / name
        base.require(path.is_file() and not path.is_symlink() and base.pin(path.read_bytes()) == expected,
                     'GLOBAL_AUTOMATIC_DECLARED_SOURCE_CHANGED:' + name)
    plan = json.loads(PLAN.read_bytes())
    base.require(plan['contract'] == original.CONTRACT and plan['actual_parent_adoption'] is False
                 and plan['source_sql'] == {name: base.pin(text.encode()) for name, text in sql_sources().items()},
                 'GLOBAL_AUTOMATIC_EXACT_SOURCE_PLAN_REQUIRED')
    return value


def manifest_pin():
    value = dict(retained=parent.manifest_pin(), automatic=base.pin((HERE / 'SOURCE.json').read_bytes()))
    return base.pin((json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode())


def load_prepared():
    base.require(all(getattr(admission, name) is None for name in GATES),
                 'GLOBAL_AUTOMATIC_ACTUAL_PARENT_AND_COMPLETE_INPUT_ADOPTION_PENDING')
    check_sources()
    source, retained = parent.derive()
    module = ModuleType('cp7_global_nonpo_envelope.prepared_automatic_composition')
    module.__package__ = 'cp7_global_nonpo_envelope'
    module.__file__ = original.__file__
    module.__dict__.update(_money_sql_sources=sql_sources, _money_plan_path=lambda: PLAN,
        _money_compare_current=routes.current_reference, _money_check_sources=check_sources,
        _money_manifest_pin=manifest_pin, _money_input_relations=require_input_relations)
    exec(compile(source, module.__file__ + '::prepared_automatic', 'exec'), module.__dict__)
    return module, dict(retained_installer_derivation=retained, additional_installer_body_changes=0,
                        whole_installation_ownership_inverse_and_recovery_source_unchanged=True,
                        actual_ERP_cases=0, production_go=False, independent_acceptance=False)
