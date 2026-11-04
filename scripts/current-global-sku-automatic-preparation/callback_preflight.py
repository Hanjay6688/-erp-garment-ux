"""Current automatic dispatch and exact Afui/Mandor callback lower bound.

All facts describe source preparation. A future accepted combined parent still
needs its own complete catalogue, dispatch, privileges and all-writer review.
"""
from pathlib import Path
import importlib.util
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRIOR_PIN = dict(bytes=917371, sha256='6c18953212bc277b0fa498a06cbcbd2710791e6db2eaa3037196bead6d46393e')


def retained():
    path = ROOT / 'scripts/current-global-sku-money-preparation/callback_preflight.py'
    spec = importlib.util.spec_from_file_location('automatic_exact_retained_callback_review', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original = module.retained()
    original.PINS = dict(original.PINS, prior=(PRIOR_PIN['bytes'], PRIOR_PIN['sha256']))
    return original


def review(actual, prior, parser_sources, parser_runtime):
    return retained().review(actual, prior, parser_sources, parser_runtime)


def requirements():
    original = retained()
    require = original.require
    report = json.loads((HERE / 'CALLBACK_SOURCE_REVIEW.json').read_bytes())
    inputs = json.loads((HERE / 'INPUT_REVIEW_CONTROLS.json').read_bytes())
    require(report['prior_source_review'] == inputs['full_source_review'] == PRIOR_PIN
            and inputs['classification'] == 'AUTOMATIC_SOURCE_EXPECTATION_NOT_ACTUAL_INPUT_PROFILE'
            and inputs['selected_source_projection_has_no_unresolved'] is True
            and inputs['complete_input_review'] is False and inputs['actual_final_parent_adopted'] is False
            and inputs['explicit_automatic_function_seeds'] == 19
            and inputs['exact_trigger_argument_bindings'] == 21,
            'GLOBAL_AUTOMATIC_EXACT_DISPATCH_SOURCE_NOT_ACCEPTANCE')
    require(report['status'] == 'PREPARED_COMPOSITE_CALLBACK_REVIEW_NOT_FINAL_INPUT_PROFILE'
            and report['focused_callback_source_has_no_unresolved'] is True
            and report['complete_input_review'] is False and report['actual_final_parent_adopted'] is False,
            'GLOBAL_AUTOMATIC_CALLBACK_SOURCE_NOT_ACCEPTANCE')
    require(report['installation_SQL'] == {name: original.pin(text.encode())
            for name, text in original.current_source_expectations().items()},
            'GLOBAL_AUTOMATIC_CURRENT_AFUI_MANDOR_CALLBACK_SOURCE_CHANGED')
    names = report['required_relation_lower_bound']
    require(names == sorted(set(names)) and len(names) == 276
            and len(inputs['physical_relation_candidates']) == 264
            and len(report['new_physical_relation_candidates']) == 12
            and set(names) == set(inputs['physical_relation_candidates']) | set(report['new_physical_relation_candidates']),
            'GLOBAL_AUTOMATIC_COMPLETE_KNOWN_RELATION_LOWER_BOUND')
    require(len(report['additional_firing_triggers']) == 4
            and len(report['additional_parent_side_foreign_keys']) == 4
            and len(report['new_callback_sources']) == 6
            and report['direct_Native_function_overlap_with_prior_review'] == []
            and report['new_write_targets_requiring_full_actual_callback_review'] == [],
            'GLOBAL_AUTOMATIC_COMPLETE_CURRENT_CALLBACK_AND_OVERLAP_REVIEW')
    return report
