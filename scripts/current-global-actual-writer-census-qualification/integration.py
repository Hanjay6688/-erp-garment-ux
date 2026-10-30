"""Read-only bracket helpers for an explicit successor of the retained runner.

No connection or installation. The existing outer runner owns every connection,
snapshot, rollback, dump restoration and result gate. An installed committed
parent, not an install savepoint, must already exist when this helper runs.
"""
from pathlib import Path
import importlib.util
import json
from hashlib import sha256
import re
from psycopg.pq import TransactionStatus

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('global_census_integration_capture', HERE / 'capture.py')
capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)
census = capture.census
CONTRACT = 'cp7.global.actual-writer-census.read-bracket.v1'
ORIGINAL = 'GLOBAL_ACTUAL_WRITER_SUPPLEMENT.json'


def begin_readonly(conn, cur):
    """Must be the first SQL operation on the outer runner's fresh connection."""
    census.require(cur.connection is conn and conn.info.host in ('127.0.0.1', 'localhost')
                   and conn.info.port == 54322, 'GLOBAL_CENSUS_BRACKET_LOCAL_CONNECTION_REQUIRED')
    census.require(conn.autocommit is False and conn.info.transaction_status == TransactionStatus.IDLE,
                   'GLOBAL_CENSUS_BRACKET_FRESH_NONAUTOCOMMIT_CONNECTION_REQUIRED')
    # Psycopg starts BEGIN implicitly before this first SET, so SET TRANSACTION
    # takes effect before any SELECT. Do not commit/rollback a caller's work.
    cur.execute('SET TRANSACTION ISOLATION LEVEL READ COMMITTED READ ONLY')
    cur.execute("SET LOCAL search_path = ''")
    cur.execute("SET LOCAL TimeZone = 'UTC'")
    identity = cur.execute("select current_database(),current_user,current_setting('transaction_read_only'),current_setting('transaction_isolation'),current_setting('search_path'),current_setting('TimeZone')").fetchone()
    census.require(identity[0] == 'cp6_rollback' and identity[1] in ('postgres', 'supabase_admin')
                   and identity[2:] == ('on', 'read committed', '', 'UTC'),
                   'GLOBAL_CENSUS_BRACKET_IDENTITY_OR_TRANSACTION_SETTINGS_CHANGED')
    return dict(contract=CONTRACT, identity=list(identity), first_statement_read_only=True,
                isolation='read committed', transaction_writes=False, runtime_entry=None,
                actual_Native_credit=0, production_go=False, independent_acceptance=False)


def complete_snapshot(snapshot):
    """Require every provider-scoped table and sequence, not a target subset."""
    census.require(type(snapshot) is dict and set(snapshot) == {'catalog', 'data_and_sequences'},
                   'GLOBAL_CENSUS_COMPLETE_SNAPSHOT_OBJECT_REQUIRED')
    catalog = census.validate_catalog(snapshot['catalog'])
    values = snapshot['data_and_sequences']
    census.require(type(values) is dict, 'GLOBAL_CENSUS_COMPLETE_DATA_SEQUENCE_MAP_REQUIRED')
    tables = {name for name, row in catalog['relations'].items() if row[1] in ('r', 'p', 'm')}
    sequences = {name for name, row in catalog['relations'].items() if row[1] == 'S'}
    census.require(bool(tables) and sequences == set(catalog['sequences']),
                   'GLOBAL_CENSUS_CATALOGUE_TABLE_SEQUENCE_IDENTITY_REQUIRED')
    expected = tables | {'sequence:' + name for name in sequences}
    census.require(set(values) == expected, 'GLOBAL_CENSUS_ALL_TABLES_AND_ALL_SEQUENCES_REQUIRED')
    for name in tables:
        row = values[name]
        census.require(type(row) is list and len(row) == 2 and type(row[0]) is int and row[0] >= 0
                       and type(row[1]) is str and re.fullmatch('[0-9a-f]{64}', row[1]),
                       'GLOBAL_CENSUS_TABLE_FINGERPRINT_ABI:' + name)
    for name in sequences:
        row = values['sequence:' + name]
        census.require(type(row) is list and len(row) == 2 and type(row[0]) is str
                       and re.fullmatch('-?[0-9]+', row[0]) and type(row[1]) is bool,
                       'GLOBAL_CENSUS_ALL_SEQUENCE_STATE_ABI:' + name)
    return dict(all22_groups=22, table_count=len(tables), sequence_count=len(sequences),
                catalogue_sha256=census.digest(catalog), data_and_sequences_sha256=census.digest(values),
                snapshot_sha256=census.digest(snapshot))


def require_current_preuse(before, state):
    proof = complete_snapshot(before)
    census.require(type(state) is dict and before['catalog'] == state.get('after')
                   and before['data_and_sequences'] == state.get('preuse_data_and_sequences'),
                   'GLOBAL_CENSUS_INSTALLED_COMMITTED_PREUSE_STATE_CHANGED')
    return proof


def finish(before, after, supplement, state):
    before_proof = require_current_preuse(before, state)
    after_proof = complete_snapshot(after)
    census.require(before == after, 'GLOBAL_CENSUS_COMPLETE_READ_CHANGED_CATALOGUE_ROWS_OR_SEQUENCES')
    metadata = capture.validate(supplement, before['catalog'])
    return dict(contract=CONTRACT, status='EXACT_ACTUAL_SUPPLEMENTAL_READ_NOEFFECT_ONLY',
                before=before_proof, after=after_proof, supplemental_metadata=metadata,
                supplement_sha256=census.digest(supplement), installed_preuse_state_matches=True,
                all_catalogue_rows_and_ALL_sequences_equal=True, transaction_writes=False,
                caller_outer_restoration_required=True, outer_restoration_verified=False,
                permission_closure='UNKNOWN', writer_or_phantom_lock_closed=False,
                runtime_entry=None, actual_Native_credit=0, production_go=False, independent_acceptance=False)


def persist_original(directory, supplement, catalog):
    """Keep full metadata as one separate Original, never report/log payload."""
    capture.validate(supplement, catalog)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / ORIGINAL
    raw = (json.dumps(supplement, indent=2, ensure_ascii=False) + '\n').encode()
    # Exclusive creation preserves an earlier result instead of overwriting it.
    with path.open('xb') as output:
        output.write(raw)
    reference = dict(name=ORIGINAL, bytes=len(raw), sha256=sha256(raw).hexdigest(),
                     catalogue_sha256=census.digest(catalog), supplement_sha256=census.digest(supplement))
    observed, observed_raw = read_original(directory, reference, catalog)
    census.require(observed == supplement and observed_raw == raw,
                   'GLOBAL_CENSUS_ORIGINAL_RAW_ROUNDTRIP_CHANGED')
    return reference


def read_original(directory, reference, catalog):
    census.require(type(reference) is dict and set(reference) == {
        'name', 'bytes', 'sha256', 'catalogue_sha256', 'supplement_sha256'}
        and reference['name'] == ORIGINAL and type(reference['bytes']) is int and reference['bytes'] > 0,
        'GLOBAL_CENSUS_EXACT_ORIGINAL_REFERENCE_REQUIRED')
    path = Path(directory) / ORIGINAL
    census.require(path.is_file() and not path.is_symlink(), 'GLOBAL_CENSUS_ORIGINAL_REGULAR_FILE_REQUIRED')
    raw = path.read_bytes()
    census.require(len(raw) == reference['bytes'] and sha256(raw).hexdigest() == reference['sha256'],
                   'GLOBAL_CENSUS_ORIGINAL_RAW_BYTES_CHANGED')
    observed = json.loads(raw, object_pairs_hook=census.unique_pairs)
    census.require(reference['catalogue_sha256'] == census.digest(catalog)
                   and reference['supplement_sha256'] == census.digest(observed),
                   'GLOBAL_CENSUS_ORIGINAL_METADATA_IDENTITY_CHANGED')
    capture.validate(observed, catalog)
    return observed, raw


def validate_case(case, original_directory):
    """Additional successor gate; never replaces the parent's outer/all5 gate."""
    census.require(type(case) is dict, 'GLOBAL_CENSUS_CASE_REQUIRED')
    before, after = case['read_before'], case['read_after']
    proof = case['global_writer_supplemental_noeffect']
    supplement, _ = read_original(original_directory, case['global_writer_supplemental_reference'], before['catalog'])
    settings = case['global_writer_read_transaction']
    census.require(settings.get('contract') == CONTRACT and settings.get('first_statement_read_only') is True
                   and settings.get('isolation') == 'read committed' and settings.get('transaction_writes') is False
                   and type(settings.get('identity')) is list and len(settings['identity']) == 6
                   and settings['identity'][0] == 'cp6_rollback'
                   and settings['identity'][1] in ('postgres', 'supabase_admin')
                   and settings['identity'][2:] == ['on', 'read committed', '', 'UTC']
                   and 'runtime_entry' in settings and settings['runtime_entry'] is None
                   and type(settings.get('actual_Native_credit')) is int and settings['actual_Native_credit'] == 0
                   and settings.get('production_go') is False and settings.get('independent_acceptance') is False,
                   'GLOBAL_CENSUS_CASE_READ_ONLY_READ_COMMITTED_REQUIRED')
    # Runtime's preuse comparison is repeated against the retained exact read
    # snapshot here. The original stage verifier and immutable derived-source
    # identity remain obligations of the original parent gate.
    expected = finish(before, after, supplement, dict(after=before['catalog'],
                      preuse_data_and_sequences=before['data_and_sequences']))
    census.require(census.canonical(proof) == census.canonical(expected) and proof['installed_preuse_state_matches'] is True,
                   'GLOBAL_CENSUS_CASE_FULL_READ_BRACKET_PROOF_CHANGED')
    return dict(status='SUPPLEMENTAL_CASE_METADATA_ONLY_PARENT_OUTER_GATE_STILL_REQUIRED',
                parent_outer_all5_gate_required=True, runtime_entry=None,
                actual_Native_credit=0, production_go=False, independent_acceptance=False)
