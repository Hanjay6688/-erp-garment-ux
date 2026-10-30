"""Lossless dependency bags and a raw Original written before validation.

Only the two pg_depend-derived groups are bags. Every other identity remains
unique. A bag preserves all returned pairs, even different values sharing an
identity; it is never a distinct projection or a dictionary of last values.
"""
from collections import Counter
from hashlib import sha256
from pathlib import Path
import json
import re

RAW_NAME = 'GLOBAL_WRITER_RAW_CAPTURE.json'
RAW_CONTRACT = 'cp7.global.writer.raw-query-capture.v1'
BAG_CONTRACT = 'cp7.global.writer.dependency-multiset.v1'
BAG_GROUPS = {'dependencies': 9, 'view_relation_dependencies': 8}
REFERENCE_KEYS = {'name', 'bytes', 'sha256', 'catalogue_sha256', 'raw_capture_sha256'}


def require(ok, message):
    if not ok: raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def digest(value): return sha256(canonical(value).encode()).hexdigest()


def pairs_unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'GLOBAL_MULTISET_DUPLICATE_JSON_MEMBER')
        result[key] = value
    return result


def document(raw):
    return json.loads(raw, object_pairs_hook=pairs_unique,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError('GLOBAL_MULTISET_NONFINITE_JSON')))


def pairs(rows):
    require(type(rows) is list, 'GLOBAL_MULTISET_RAW_ROWS_LIST_REQUIRED')
    for row in rows:
        require(type(row) is list and len(row) == 2 and type(row[0]) is str and bool(row[0]),
                'GLOBAL_MULTISET_RAW_PAIR_ABI')
    return rows


def encode_group(name, rows):
    pairs(rows)
    if name not in BAG_GROUPS:
        result = dict(rows)
        require(len(result) == len(rows), 'GLOBAL_CENSUS_DUPLICATE_SUPPLEMENT_IDENTITY:' + name)
        return result
    for key, row in rows:
        require(type(row) is list and len(row) == BAG_GROUPS[name], 'GLOBAL_MULTISET_DEPENDENCY_ROW_ABI:' + name)
        if name == 'dependencies':
            require(re.fullmatch(r'[0-9]+:[0-9]+:-?[0-9]+:[0-9]+:[0-9]+:-?[0-9]+:.', key) is not None,
                    'GLOBAL_MULTISET_SEVEN_FIELD_IDENTITY_REQUIRED')
            fields = key.split(':')
            require(type(row[2]) is int and type(row[5]) is int
                and fields[1:3] == [row[1], str(row[2])]
                and fields[4:] == [row[4], str(row[5]), row[6]],
                'GLOBAL_MULTISET_DEPENDENCY_IDENTITY_VALUE_MISMATCH')
        else:
            require(re.fullmatch(r'[0-9]+:[0-9]+:-?[0-9]+:.', key) is not None
                and type(row[6]) is int and key.split(':')[2:] == [str(row[6]), row[7]],
                'GLOBAL_MULTISET_VIEW_DEPENDENCY_IDENTITY_VALUE_MISMATCH')
    multiplicities = dict(sorted(Counter(key for key, _ in rows).items()))
    return dict(contract=BAG_CONTRACT, group=name, rows=rows, occurrence_count=len(rows),
        distinct_identity_count=len(multiplicities), identity_multiplicities=multiplicities,
        raw_pairs_sha256=digest(rows))


def values(group):
    require(type(group) is dict and group.get('group') in BAG_GROUPS, 'GLOBAL_MULTISET_EXPLICIT_GROUP_REQUIRED')
    require(type(group.get('occurrence_count')) is int and type(group.get('distinct_identity_count')) is int
        and type(group.get('identity_multiplicities')) is dict
        and all(type(v) is int and v > 0 for v in group['identity_multiplicities'].values()),
        'GLOBAL_MULTISET_EXACT_TYPED_MULTIPLICITY_REQUIRED')
    expected = encode_group(group['group'], group['rows'])
    require(canonical(group) == canonical(expected), 'GLOBAL_MULTISET_LOSSLESS_BAG_CHANGED')
    return [row for _, row in group['rows']]


def reference(value):
    require(type(value) is dict and set(value) == REFERENCE_KEYS and value['name'] == RAW_NAME
        and type(value['bytes']) is int and value['bytes'] > 0
        and all(type(value[k]) is str and re.fullmatch('[0-9a-f]{64}', value[k])
                for k in ('sha256', 'catalogue_sha256', 'raw_capture_sha256')),
        'GLOBAL_MULTISET_EXACT_RAW_REFERENCE_REQUIRED')
    return value


def regular(directory, name):
    directory = Path(directory)
    require(not any(p.is_symlink() for p in (directory, *directory.parents)), 'GLOBAL_MULTISET_RAW_DIRECTORY_SYMLINK')
    path = directory / name
    require(not path.is_symlink(), 'GLOBAL_MULTISET_RAW_ORIGINAL_SYMLINK')
    return path


def validate_raw(value, queries, catalog=None):
    required = {'contract', 'catalogue_sha256', 'identity', 'params', 'query_order', 'query_sha256',
        'raw_groups', 'captured_groups', 'status', 'query_failure', 'transaction_writes',
        'runtime_entry', 'actual_Native_credit', 'production_go', 'independent_acceptance'}
    require(type(value) is dict and set(value) == required and value['contract'] == RAW_CONTRACT,
        'GLOBAL_MULTISET_RAW_FIELDS_OR_CONTRACT_CHANGED')
    require(value['transaction_writes'] is False and value['runtime_entry'] is None
        and type(value['actual_Native_credit']) is int and value['actual_Native_credit'] == 0
        and value['production_go'] is False and value['independent_acceptance'] is False,
        'GLOBAL_MULTISET_RAW_MUST_STAY_CLOSED')
    identity = value['identity']
    require(type(identity) is list and len(identity) == 6 and identity[0] == 'cp6_rollback'
        and identity[1] in ('postgres', 'supabase_admin') and identity[2:5] == ['on', '', 'UTC']
        and type(identity[5]) is str and identity[5].isdigit() and 170000 <= int(identity[5]) < 180000,
        'GLOBAL_MULTISET_RAW_READONLY_PG17_IDENTITY_REQUIRED')
    require(value['query_order'] == list(queries) and value['query_sha256'] == {
        name: sha256(query.encode()).hexdigest() for name, query in queries.items()},
        'GLOBAL_MULTISET_RAW_EXACT_UNCHANGED_QUERIES_REQUIRED')
    params = value['params']
    require(type(params) is dict and set(params) == {'schemas', 'relations', 'functions'}
        and all(type(v) is list and bool(v) and all(type(x) is str for x in v)
            and v == sorted(set(v)) for v in params.values()), 'GLOBAL_MULTISET_RAW_EXACT_SCOPE_REQUIRED')
    require(type(value['catalogue_sha256']) is str and re.fullmatch('[0-9a-f]{64}', value['catalogue_sha256']),
        'GLOBAL_MULTISET_RAW_CATALOGUE_DIGEST_REQUIRED')
    if catalog is not None:
        require(value['catalogue_sha256'] == digest(catalog) and params == {
            key: sorted(catalog[key]) for key in ('schemas', 'relations', 'functions')},
            'GLOBAL_MULTISET_RAW_CATALOGUE_SCOPE_CHANGED')
    require(type(value['raw_groups']) is dict and type(value['captured_groups']) is list
        and value['captured_groups'] == list(queries)[:len(value['captured_groups'])]
        and set(value['raw_groups']) == set(value['captured_groups']), 'GLOBAL_MULTISET_RAW_QUERY_PREFIX_REQUIRED')
    for rows in value['raw_groups'].values(): pairs(rows)
    if value['status'] == 'ALL_QUERIES_CAPTURED_BEFORE_VALIDATION':
        require(value['captured_groups'] == list(queries) and value['query_failure'] is None,
            'GLOBAL_MULTISET_RAW_COMPLETE_REQUIRED')
    else:
        failure = value['query_failure']; n = len(value['captured_groups'])
        require(value['status'] == 'QUERY_FAILED_BEFORE_VALIDATION' and n < len(queries)
            and type(failure) is dict and set(failure) == {'phase', 'sqlstate'}
            and failure['phase'] == list(queries)[n]
            and (failure['sqlstate'] is None or type(failure['sqlstate']) is str),
            'GLOBAL_MULTISET_RAW_FAILURE_PREFIX_REQUIRED')
    return value


def persist_raw(directory, catalog, identity, params, raw_groups, queries, failure=None):
    value = dict(contract=RAW_CONTRACT, catalogue_sha256=digest(catalog), identity=list(identity),
        params=params, query_order=list(queries), query_sha256={name: sha256(query.encode()).hexdigest()
            for name, query in queries.items()}, raw_groups=raw_groups, captured_groups=list(raw_groups),
        status='ALL_QUERIES_CAPTURED_BEFORE_VALIDATION' if failure is None else 'QUERY_FAILED_BEFORE_VALIDATION',
        query_failure=failure, transaction_writes=False, runtime_entry=None, actual_Native_credit=0,
        production_go=False, independent_acceptance=False)
    # Raw payload is persisted before shape/uniqueness/supplement validation.
    # Even malformed returned row data remains inspectable after a rejection.
    path = regular(directory, RAW_NAME); path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode()
    with path.open('xb') as output: output.write(raw)
    require(path.read_bytes() == raw, 'GLOBAL_MULTISET_RAW_BYTE_ROUNDTRIP_CHANGED')
    ref = dict(name=RAW_NAME, bytes=len(raw), sha256=sha256(raw).hexdigest(),
        catalogue_sha256=value['catalogue_sha256'], raw_capture_sha256=digest(value))
    observed = document(path.read_bytes())
    require(canonical(observed) == canonical(value), 'GLOBAL_MULTISET_RAW_JSON_ROUNDTRIP_CHANGED')
    return ref


def read_raw(directory, ref, queries, catalog=None):
    reference(ref); path = regular(directory, RAW_NAME)
    require(path.is_file(), 'GLOBAL_MULTISET_RAW_ORIGINAL_REQUIRED')
    raw = path.read_bytes()
    require(len(raw) == ref['bytes'] and sha256(raw).hexdigest() == ref['sha256'], 'GLOBAL_MULTISET_RAW_BYTES_CHANGED')
    value = document(raw)
    require(digest(value) == ref['raw_capture_sha256'] and value['catalogue_sha256'] == ref['catalogue_sha256'],
        'GLOBAL_MULTISET_RAW_REFERENCE_IDENTITY_CHANGED')
    validate_raw(value, queries, catalog)
    return value


def require_projection(directory, supplement, catalog, queries):
    value = read_raw(directory, supplement['raw_capture_reference'], queries, catalog)
    require(value['status'] == 'ALL_QUERIES_CAPTURED_BEFORE_VALIDATION', 'GLOBAL_MULTISET_PARTIAL_RAW_CANNOT_QUALIFY')
    require(supplement.get('identity') == value['identity'], 'GLOBAL_MULTISET_RAW_IDENTITY_CHANGED')
    expected = {name: encode_group(name, rows) for name, rows in value['raw_groups'].items()}
    require(canonical(expected) == canonical(supplement['groups']), 'GLOBAL_MULTISET_RAW_TO_SUPPLEMENT_NOT_LOSSLESS')
    return value
