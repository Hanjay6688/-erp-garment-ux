"""Current full source first; authoritative four-Original readers stay unchanged."""
from pathlib import Path
import importlib.util

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PARENT=ROOT/'scripts/current-attendance-choice-reader-native14-qualification'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def admitted(root,here,product,derivation):
    current=load('s03_lawful_unprojected_current_source',HERE/'source_check.py').check(root,HERE,require_bound=True)
    helper=load('s03_lawful_original_intake_one_source_binding',HERE/'derive.py')
    intake,proof=helper.module('s03_lawful_unchanged_vendor_Original_intake',
        Path(root)/'scripts/current-attendance-period-choice-native11-qualification/admission.py',
        [(helper.INTAKE_BEFORE,helper.INTAKE_AFTER)],CURRENT_SOURCE_CLOSURE=current)
    prior=intake.admitted(root,PARENT,product,derivation)
    return dict(prior,status='EXACT_VENDOR41C_UNCHANGED_RUNTIME15_LAWFUL_THREE_FIXTURES_FRESH11_THEN_READER3',
        current_qualification=current,Original_intake_source_binding=proof,
        fresh_groups=[11,3],fresh_Native_case_count=14,actual_Native_cases=0,
        failed9ac_8partialPASS_used_as_prerequisite=False,
        original_eleven_runtime_callbacks_byte_exact=False,production_go=False,independent_acceptance=False)
