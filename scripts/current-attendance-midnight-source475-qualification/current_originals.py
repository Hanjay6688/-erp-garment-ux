"""Source-only real five-environment intake; cannot admit the future Native14."""
from types import ModuleType
import importlib.util
import sys
from midnight_common import ROOT, HERE, pin, regular, document
import source_check
import historical_inputs
import parent_binding

ENVIRONMENT = ('D17_18_RETAINED_COMBINED_AF_DIRECTORY', 'CP7_VENDOR_BACKEND11_ORIGINALS',
               'D17_18_ACCEPTED_CONSISTENCY_DIRECTORY', 'D17_18_RETAINED_FOCUSED64_DIRECTORY',
               'D17_18_ACCEPTED_CONSISTENCY_FOCUSED_DIRECTORY')
INTAKE = 'scripts/current-s03-lawful-fixture-successor-qualification/admission.py'
ANCHOR = "    current=load('s03_lawful_unprojected_current_source',HERE/'source_check.py').check(root,HERE,require_bound=True)"
REPLACEMENT = '    current=CURRENT_COMPLETE_SOURCE475_CLOSURE'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def admitted():
    # The complete physical475/public3c0/own-source check always precedes this
    # separate historical intake. No accepted14 pin is fabricated or bypassed.
    closure = source_check.check()
    _, files = parent_binding.source()
    raw = regular(ROOT, INTAKE).read_bytes()
    if pin(raw) != files[INTAKE] or raw.decode().count(ANCHOR) != 1:
        raise ValueError('MIDNIGHT_CURRENT475_ONE_INTAKE_ANCHOR_REQUIRED')
    changed = raw.decode().replace(ANCHOR, REPLACEMENT, 1)
    if changed.count(REPLACEMENT) != 1 or changed.replace(REPLACEMENT, ANCHOR, 1).encode() != raw:
        raise ValueError('MIDNIGHT_CURRENT475_INTAKE_MUST_REVERSE_EXACT')
    boundary = load('midnight_current_Original_argv_boundary', ROOT / 'scripts/current-attendance-period-choice-native11-qualification/argv_boundary.py')
    with boundary.inherited_imports():
        sys.path.insert(0, str(ROOT / 'scripts'))
        materialized = historical_inputs.original_reader().materialize(ROOT, ROOT / historical_inputs.PARENT)
        # Recheck after actual unchanged materialization; exact named four gzip
        # bytes are admitted individually, without excluding any unknown path.
        closure = source_check.check()
        from cp7_attendance_period_choice import composition as product
        inherited = ModuleType('midnight_private_current475_authoritative_Original_intake')
        inherited.__file__ = str(ROOT / INTAKE)
        inherited.CURRENT_COMPLETE_SOURCE475_CLOSURE = closure
        exec(compile(changed, str(ROOT / INTAKE), 'exec'), inherited.__dict__)
        cfg = document((ROOT / historical_inputs.PARENT / 'CONFIG.json').read_bytes())
        proof = inherited.admitted(ROOT, ROOT / historical_inputs.PARENT, product, cfg['runner_derivation'])
        actual = product.sources()
        if proof['current_installation'] != actual:
            raise ValueError('MIDNIGHT_CURRENT475_FULL_UNPROJECTED_PRODUCT_SOURCES_REQUIRED')
    return dict(status='SOURCE_ONLY_CURRENT475_AND_ACTUAL_INHERITED_ORIGINALS_ADMITTED_FUTURE14_CLOSED',
        current_installation=actual, inherited_Original_proof=proof,
        full_current_source=closure, inherited_materialization=materialized,
        counted_current475_intake_changes=1, unchanged_authoritative_Original_readers=True,
        accepted_parent14=None, future_six_Originals_admitted=False,
        actual_Native_cases=0, production_go=False, independent_acceptance=False)
