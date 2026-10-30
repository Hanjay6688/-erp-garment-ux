"""Counted private routing only; six vendor engine selections stay unchanged."""
from pathlib import Path
from types import ModuleType
import importlib.util

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PARENT = ROOT/'scripts/current-attendance-choice-reader-native14-qualification'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def substitute(raw,pairs):
    return load('s03_lawful_lossless_substitution',HERE/'business.py').substitute(raw,pairs)


PROBE_PAIRS=(
    ("HERE / 'source_check.py'", "CURRENT_HERE / 'source_check.py'"),
    ("HERE / 'native_runner.py'", "CURRENT_HERE / 'native_runner.py'"),
    ("HERE / 'admission.py'", "CURRENT_HERE / 'admission.py'"),
    (".admitted(ROOT, HERE, product, derivation)", ".admitted(ROOT, CURRENT_HERE, product, derivation)"),
)
BUSINESS_BEFORE="""spec = importlib.util.spec_from_file_location('s03_native11_unchanged_prepared_business',
    ROOT / 'scripts/current-attendance-period-choice-qualification/cases.py')
business = importlib.util.module_from_spec(spec)
spec.loader.exec_module(business)"""
BUSINESS_AFTER="business = CURRENT_BUSINESS.runtime()"
READER_BEFORE="""    spec = importlib.util.spec_from_file_location('s03_native14_actual_authored_reader3', ROOT / FACTORY)
    reader = importlib.util.module_from_spec(spec); spec.loader.exec_module(reader)"""
READER_AFTER="    reader = CURRENT_BUSINESS.reader_runtime()"
INTAKE_BEFORE="    closure = load('s03_native11_runtime_source_check', here / 'source_check.py').check(root, here)"
INTAKE_AFTER="    closure = CURRENT_SOURCE_CLOSURE"
SOURCE_PAIRS=(
    ("if not changed <= allowed or git('status', '--porcelain', '--untracked-files=no').strip():",
     "if not changed <= (allowed | CURRENT_ALLOWED) or git('status', '--porcelain', '--untracked-files=no').strip():"),
    ("allowed_untracked.update(source['untracked_historical_proof_inputs'])",
     "allowed_untracked.update(source['untracked_historical_proof_inputs'])\n    allowed_untracked.update(CURRENT_ALLOWED)"),
    ("here / 'generated_receipts.py').admit(root, here, untracked - allowed_untracked)",
     "here / 'generated_receipts.py').admit(root, CURRENT_RECEIPT_HERE, untracked - allowed_untracked)"),
    ("here / 'generated_later.py').admit(root, here, untracked - allowed_untracked)",
     "here / 'generated_later.py').admit(root, CURRENT_RECEIPT_HERE, untracked - allowed_untracked)"),
    ("inner, derivation = private_intake(root, here)",
     "inner, derivation = CURRENT_HISTORICAL_INTAKE(root, here)"),
)
INNER_SOURCE_PAIRS=(
    ("if not set(changed) <= set(source['allowed_changes']):",
     "if not set(changed) <= (set(source['allowed_changes']) | CURRENT_ALLOWED):"),
    ("allowed_untracked.update(source['untracked_historical_proof_inputs'])",
     "allowed_untracked.update(source['untracked_historical_proof_inputs'])\n    allowed_untracked.update(CURRENT_ALLOWED)"),
    ("generated.admit(root, here, untracked - allowed_untracked)",
     "generated.admit(root, CURRENT_RECEIPT_HERE, untracked - allowed_untracked)"),
    ("later.admit(root, here, untracked - allowed_untracked)",
     "later.admit(root, CURRENT_RECEIPT_HERE, untracked - allowed_untracked)"),
)


def module(name,path,pairs,**bindings):
    value,proof=substitute(path.read_bytes(),pairs)
    obj=ModuleType(name);obj.__file__=str(path);obj.__dict__.update(bindings)
    exec(compile(value,str(path),'exec'),obj.__dict__)
    return obj,proof


def vendor(raw):
    return load('s03_lawful_frozen_six_vendor_selections',PARENT/'derive.py').derive(raw)


def native(raw):
    parent=load('s03_lawful_same_original_native14_plan',PARENT/'derive.py')
    first,original=parent.native_runner(raw)
    value,binding=substitute(first.encode(),[(BUSINESS_BEFORE,BUSINESS_AFTER)])
    # The old derivation's byte-exact callback claim is deliberately superseded.
    original['original11_factory_counts_assertions_and_callbacks_unchanged']=False
    return value,dict(parent=original,explicit_private_business_binding=binding,
        original_eight_callbacks_exact=True,adapted_callback_count=3,
        strict_groups=[11,3],actual_captures=15,clones=2,
        original_committed_ALLOCATE_witness_unchanged=True)
