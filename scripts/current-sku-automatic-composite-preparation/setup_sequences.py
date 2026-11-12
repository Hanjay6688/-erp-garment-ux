"""Account for sequence allocations by the strict Native runner's fixture seed."""
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from types import ModuleType
import importlib.util

AUDIT = 'erp.audit_logs_id_seq'
AUDIT_KEY = 'sequence:' + AUDIT
CASE_BOUNDARY_PIN = (7764, '40b457f54d0082ae969c0a6d55a33dfe90e27fb88674ef6ffbf908b78f5fa837')
SEED_PIN = (6076, 'c5ff9f51bfeaa04c95f1f77f8b82ce5129d93965ea4d452c867135e48a57bd62')


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def checked_source(path, expected):
    require(path.is_file() and not any(p.is_symlink() for p in (path, *path.parents)),
            'SKU_NATIVE_SETUP_REGULAR_SOURCE_REQUIRED:' + path.name)
    raw = path.read_bytes()
    require((len(raw), sha256(raw).hexdigest()) == expected,
            'SKU_NATIVE_SETUP_EXACT_SOURCE_REQUIRED:' + path.name)
    return raw


def bind(api, case_output, report_io):
    """Use the exact seed callable and the retained Afui sequence reader."""
    seed_path = Path(api.__file__)
    require(seed_path.as_posix().endswith('/scripts/cp6_ao_ap_installed.py'),
            'SKU_NATIVE_SETUP_EXACT_SEED_SOURCE_PATH_REQUIRED')
    raw = checked_source(seed_path, SEED_PIN)
    require(api.seed.__globals__ is api.__dict__
            and api.seed.__code__ == report_io.function_code(raw, str(seed_path), 'seed'),
            'SKU_NATIVE_SETUP_EXACT_SEED_CALLABLE_REQUIRED')

    path = Path(case_output.__file__).with_name('case_boundary.py')
    checked_source(path, CASE_BOUNDARY_PIN)
    spec = importlib.util.spec_from_file_location('sku_exact_native_setup_sequence_reader', path)
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    proof = dict(seed=dict(bytes=SEED_PIN[0], sha256=SEED_PIN[1]),
                 sequence_reader=dict(bytes=CASE_BOUNDARY_PIN[0], sha256=CASE_BOUNDARY_PIN[1]))
    return reader, proof


@contextmanager
def scope(native, business, prefix, before, report, reader):
    """Observe the existing seed call on its own transaction and cursor."""
    initial = prefix.sequences(before['data'])
    receipt = dict(status='SEED_NOT_INVOKED', prefix=prefix.prefix(initial, initial))
    report['native_fixture_seed_sequence_prefix'] = receipt
    original = native.api
    api = ModuleType('sku_native_observed_fixture_api')
    api.__dict__.update(vars(original))

    def seed(cur):
        require(receipt['status'] == 'SEED_NOT_INVOKED', 'SKU_NATIVE_SETUP_REPEATED_SEED')
        receipt.update(status='INCOMPLETE', prefix=None)
        catalog = business.n.product.runtime()[-1]
        definition = before['catalog']
        table, column, dependency = reader.OWNED[AUDIT]
        require(definition['sequences'].get(AUDIT) == reader.SEQUENCE_DEFINITION
                and definition['sequence_ownership'].get(AUDIT) == [dependency, table, column]
                and definition['columns'][table + ':' + column][-1] == "nextval('erp.audit_logs_id_seq'::regclass)",
                'SKU_NATIVE_SETUP_EXACT_AUDIT_SEQUENCE_OWNERSHIP_AND_DEFAULT_REQUIRED')
        baseline = dict(full_data_and_sequences=initial)
        observed_before = reader.capture_generated(cur, catalog, baseline)['sequences']
        receipt['observed_before'] = observed_before
        require(observed_before == initial, 'SKU_NATIVE_SETUP_UNATTRIBUTED_SEQUENCE_BEFORE_SEED')

        original.seed(cur)

        observed = reader.capture_generated(cur, catalog, baseline)
        observed_after = observed['sequences']
        receipt['observed_after'] = observed_after
        transition = prefix.prefix(observed_before, observed_after)
        require(set(transition['changed']) == {AUDIT_KEY},
                'SKU_NATIVE_SETUP_ONLY_AUDIT_SEQUENCE_MAY_ADVANCE')
        allocated = reader.allocations(observed_before[AUDIT_KEY], observed_after[AUDIT_KEY])
        audit_ids = [str(row[column]) for row in observed['generated_rows'][AUDIT]]
        receipt['audit_row_ids'] = audit_ids
        require(audit_ids == allocated and bool(allocated),
                'SKU_NATIVE_SETUP_EVERY_AUDIT_ALLOCATION_REQUIRES_ITS_ROW')
        receipt.update(status='SEED_ALLOCATIONS_VERIFIED', prefix=transition,
                       audit_allocation_count=len(allocated))

    api.seed = seed
    native.api = api
    try:
        yield receipt
    finally:
        native.api = original
