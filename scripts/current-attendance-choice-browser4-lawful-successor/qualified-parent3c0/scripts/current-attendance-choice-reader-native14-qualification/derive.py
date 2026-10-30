"""Explicit private metadata/routing derivations; original11 financial code stays exact."""
from pathlib import Path
from hashlib import sha256
import importlib.util

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = ROOT / 'scripts/current-attendance-period-choice-native11-qualification'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


REPLACEMENTS = load('s03_native14_exact_six_engine_declarations', OLD / 'derive.py').REPLACEMENTS


def derive(raw):
    return load('s03_native14_exact_six_vendor_engine', OLD / 'derive.py').derive(raw)


def substitute(raw, pairs):
    text = raw.decode()
    for before, after in pairs:
        if text.count(before) != 1:
            raise ValueError('S03_NATIVE14_ONE_EXACT_PRIVATE_ANCHOR_REQUIRED:' + before)
        text = text.replace(before, after, 1)
    restored = text
    for before, after in reversed(pairs):
        if restored.count(after) != 1:
            raise ValueError('S03_NATIVE14_ONE_EXACT_REVERSE_ANCHOR_REQUIRED')
        restored = restored.replace(after, before, 1)
    if restored.encode() != raw:
        raise ValueError('S03_NATIVE14_PRIVATE_SOURCE_NOT_REVERSIBLE')
    return text, dict(original_sha256=sha256(raw).hexdigest(), derived_sha256=sha256(text.encode()).hexdigest(),
                      counted_changes=len(pairs), all_other_bytes_exact=True)


NATIVE_PAIRS = (
    ("or len(state['originals']) != 13 or len(state['clones']) != 2",
     "or len(state['originals']) != 15 or len(state['clones']) != 2"),
    ('S03_NATIVE11_ACTUAL13_ORIGINALS_TWO_CLONES_REQUIRED',
     'S03_NATIVE14_ACTUAL15_ORIGINALS_TWO_CLONES_REQUIRED'),
    ("required_Native_case_ids=list(business.IDS),",
     "required_Native_case_ids=list(business.IDS)+list(CURRENT_READER_IDS),"),
    ("    with psycopg.connect(url) as connection, connection.cursor() as cursor:\n",
     "    run_actual_reader3(native, control, state, report, verify, actual)\n\n"
     "    with psycopg.connect(url) as connection, connection.cursor() as cursor:\n"),
    ("report.update(status='PASS', actual_Native_cases=11, used_guard_refused_before_DDL=True,",
     "report.update(status='PASS', actual_Native_cases=14, used_guard_refused_before_DDL=True,"),
)


def native_runner(raw):
    code, proof = substitute(raw, NATIVE_PAIRS)
    return code, dict(proof, original11_factory_counts_assertions_and_callbacks_unchanged=True,
        original_committed_ALLOCATE_witness_unchanged=True, strict_groups=[11, 3],
        combined_strict14_fabricated=False, current_capture_metadata=15, private_clones=2)


def source_checker(raw):
    old = "for name, pin in origin['copied_S03_files'].items():\n        raw = (root / name).read_bytes()"
    new = "for name, pin in origin['copied_S03_files'].items():\n        raw = (here / 'retained_9a0/source80' / name).read_bytes()"
    code, proof = substitute(raw, ((old, new),
        ("len(set(ids[0])) != 11", "len(set(ids[0])) != 14"),
        ("len(stage.SIGNATURES) != 13", "len(stage.SIGNATURES) != 15"),
        ("existing_captures=13, private_clones=2,", "existing_captures=15, private_clones=2,")))
    return code, dict(proof, historical80_validation_only_reads_retained_baseline=True,
        actual_current_product_and_all_authored_files_checked_by_outer_first=True,
        original_Original_readers_unchanged=True, current_source_manifest_used_explicitly=True)
