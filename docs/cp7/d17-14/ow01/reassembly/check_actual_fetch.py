"""Actual fetch function + SYNTHETIC RPC envelopes; no Native/source proof.

The old function is the exact b040 source retained in INITIAL_FETCH_SOURCE.py.
The new function is extracted unchanged from root's active file. Only its RPC
dependency is a local fixture. All actual fetch byte/hash/range/identity/count
assertions execute; no database module, database connection or Native writer is
loaded. Fixture fields are not claimed as a valid complete business analysis.
"""
import argparse
import ast
from copy import deepcopy
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUN = '00000000-0000-0000-0000-000000000001'
REQUEST = '00000000-0000-0000-0000-000000000002'
EPOCH = '3' * 64


def digest(text):
    return sha256(text.encode('utf8')).hexdigest()


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def function_source(file):
    source = file.read_text()
    fn = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == 'fetch')
    return ast.get_source_segment(source, fn) + '\n'


def fixture(fixed=('GLOBAL_SCHEDULE', 'GLOBAL_FABRIC_SUFFIX'), prefix=1, extra_array=False):
    header = dict(contract_version='cp7.native-analysis-header.v1', run_id=RUN, request_id=REQUEST,
                  query=dict(from_date='2026-09-01', through_date='2026-09-30', group_mode='CURRENT_RESTATED'),
                  financial_source=None, product_labels=[], analysis_header=dict(assumptions=list(fixed)),
                  paged=dict(assumptions=dict(prefix=prefix, items=2)), targets_total=2, page_count=2,
                  apply_enabled=False, production_go=False)
    docs = []
    for index, target in enumerate(('TARGET_A', 'TARGET_B')):
        docs.append(dict(contract_version='cp7.native-analysis-page.v1', run_id=RUN, index=index, page_count=2,
                         target_lo=index + 1, target_hi=index + 1, targets_total=2,
                         counts=dict(assumptions=1), items=dict(assumptions=[target]),
                         apply_enabled=False, production_go=False))
    if extra_array:
        header['analysis_header']['metrics'] = ['METRIC_SUFFIX']
        header['paged']['metrics'] = dict(prefix=0, items=2)
        for index, doc in enumerate(docs):
            doc['counts']['metrics'] = 1
            doc['items']['metrics'] = ['METRIC_' + str(index)]
    return rebuild(header, docs)


def rebuild(header, docs):
    header, docs = deepcopy(header), deepcopy(docs)
    h = encoded(header)
    entries, envelopes = [], []
    for index, doc in enumerate(docs):
        doc['header_sha256'] = digest(h)
        body = encoded(doc)
        entry = dict(index=index, target_lo=doc['target_lo'], target_hi=doc['target_hi'],
                     utf8_bytes=len(body.encode('utf8')), sha256=digest(body), counts=doc['counts'])
        entries.append(entry)
        envelopes.append(dict(contract_version='cp7.native-analysis-page-read.v1', run_id=RUN,
                              index=index, page_count=len(docs), target_lo=doc['target_lo'], target_hi=doc['target_hi'],
                              header_sha256=digest(h), utf8_bytes=entry['utf8_bytes'], sha256=entry['sha256'], body=body))
    identity = digest(digest(h) + '\n' + '\n'.join(e['sha256'] for e in entries))
    for envelope in envelopes:
        envelope['identity_hash'] = identity
    page_set = dict(contract_version='cp7.native-analysis-pages.v1', run_id=RUN, request_id=REQUEST,
                    apply_enabled=False, production_go=False, access_epoch=EPOCH,
                    header=dict(body=h, utf8_bytes=len(h.encode('utf8')), sha256=digest(h)),
                    paged=header['paged'], targets_total=header['targets_total'], page_count=len(docs),
                    pages=entries, identity_hash=identity)
    return dict(header=header, docs=docs, page_set=page_set, envelopes=envelopes)


def actual_fetch(source, model):
    calls = []

    def synthetic_rpc(cur, name, args, subject):
        assert cur is None and subject == 'SYNTHETIC_UNIT_ACTOR', 'CONTROL_TRIED_A_REAL_CONTEXT'
        calls.append(name)
        if name == 'erp_cp7_read_staged_analysis_pages_v1':
            assert args == (RUN,)
            return deepcopy(model['page_set'])
        assert name == 'erp_cp7_read_staged_analysis_page_v1'
        assert args[0] == RUN and args[2] == EPOCH
        return deepcopy(model['envelopes'][args[1]])

    namespace = dict(limited=synthetic_rpc, sha=digest, PAGE_BYTES=8000000,
                     parse=lambda text: json.loads(text, parse_float=Decimal))
    exec(compile(source, 'ACTUAL_FETCH_SOURCE_UNCHANGED', 'exec'), namespace)
    return namespace['fetch'](None, RUN, 'SYNTHETIC_UNIT_ACTOR'), calls


def expected_original(model):
    header = model['header']
    arrays = deepcopy(header['analysis_header'])
    for name, layout in header['paged'].items():
        fixed = arrays[name]
        items = [x for doc in model['docs'] for x in doc['items'].get(name, [])]
        arrays[name] = fixed[:layout['prefix']] + items + fixed[layout['prefix']:]
    return dict(contract_version='cp7.native-analysis-run.v1', run_id=RUN, request_id=REQUEST,
                analysis=arrays, product_labels=header['product_labels'], query=header['query'],
                financial_source=None, apply_enabled=False, production_go=False)


def main(repo, old_only):
    old = (HERE / 'INITIAL_FETCH_SOURCE.py').read_text()
    model = fixture()
    first = dict(classification='FIRST_RED_ACTUAL_OLD_FETCH_SYNTHETIC_RPC_NOT_NATIVE',
                 source_sha256=digest(old), expected_original=expected_original(model),
                 expected_assertion=['assumptions', 2, dict(prefix=1, items=2)], Native_execution_proven=False)
    try:
        actual_fetch(old, model)
    except AssertionError as error:
        first['observed_assertion'] = error.args[0]
        assert error.args == (('assumptions', 2, dict(prefix=1, items=2)),), error.args
        first['first_red_reproduced'] = True
    else:
        raise AssertionError('EXPECTED_EXACT_OLD_FETCH_FAILURE_NOT_OBSERVED')
    first_file = HERE / 'FIRST_RED.json'
    if first_file.exists():
        assert json.loads(first_file.read_text()) == json.loads(json.dumps(first)), 'FIRST_RED_MUST_STAY_IMMUTABLE'
    else:
        first_file.write_text(json.dumps(first, indent=2) + '\n')
    if old_only:
        print(json.dumps(dict(classification=first['classification'], exact_first_red=True)))
        return

    source_file = repo / 'scripts/cp7_p19_staged_cases.py'
    current = function_source(source_file)
    rows = []

    def control(name, value, accept):
        original_fixture = deepcopy(value)
        try:
            (original, ps, shape), calls = actual_fetch(current, value)
        except AssertionError as error:
            assert not accept, (name, error.args)
            rows.append(dict(id=name, expected='REJECT', observed='REJECT', assertion=repr(error.args)))
        else:
            assert accept, ('MALFORMED_ENVELOPE_NOT_REFUSED', name)
            assert original == expected_original(value), ('ORIGINAL_POSITION_OR_CONTENT_LOST', name, original)
            assert ps == value['page_set'] and shape['page_count'] == 2
            assert calls == ['erp_cp7_read_staged_analysis_pages_v1'] + ['erp_cp7_read_staged_analysis_page_v1'] * 2
            rows.append(dict(id=name, expected='ACCEPT', observed='ACCEPT', complete_original=original,
                             identity_hash=ps['identity_hash']))
        assert value == original_fixture, ('FIXTURE_OR_ORIGINAL_MUTATED', name)

    control('PREFIX1_ITEMS2_SUFFIX1_PRESERVES_ALL4', fixture(), True)
    control('PREFIX_ONLY_EXISTING_LAYOUT_UNCHANGED', fixture(('GLOBAL_SCHEDULE',), 1), True)
    control('ZERO_PREFIX_WITH_GLOBAL_SUFFIX', fixture(('GLOBAL_FABRIC_SUFFIX',), 0), True)
    control('EMPTY_HEADER_ARRAY', fixture((), 0), True)
    control('EACH_ARRAY_HAS_ITS_OWN_INSERTION_INDEX', fixture(extra_array=True), True)
    for name, edit in (
        ('HEADER_BODY_HASH', lambda m: m['page_set']['header'].__setitem__('body', m['page_set']['header']['body'] + ' ')),
        ('PAGE_BODY_HASH', lambda m: m['envelopes'][0].__setitem__('body', m['envelopes'][0]['body'] + ' ')),
        ('HEADER_UTF8_SIZE', lambda m: m['page_set']['header'].__setitem__('utf8_bytes', m['page_set']['header']['utf8_bytes'] + 1)),
        ('PAGE_UTF8_SIZE', lambda m: m['envelopes'][0].__setitem__('utf8_bytes', m['envelopes'][0]['utf8_bytes'] + 1)),
        ('PAGESET_IDENTITY', lambda m: m['page_set'].__setitem__('identity_hash', '0' * 64)),
        ('CONTIGUOUS_TARGET_RANGE', lambda m: m['page_set']['pages'][1].__setitem__('target_lo', 3)),
        ('PAGE_FOREIGN_RUN', lambda m: m['envelopes'][0].__setitem__('run_id', REQUEST)),
        ('PAGE_WRONG_INDEX', lambda m: m['envelopes'][0].__setitem__('index', 1)),
        ('HEADER_LAYOUT_EQUALS_PAGESET', lambda m: m['page_set']['paged']['assumptions'].__setitem__('prefix', 0)),
    ):
        value = fixture()
        edit(value)
        control('REJECT_' + name, value, False)
    for name, edit in (
        ('PREFIX_OUT_OF_HEADER', lambda h, d: h['paged']['assumptions'].__setitem__('prefix', 3)),
        ('PREFIX_NEGATIVE', lambda h, d: h['paged']['assumptions'].__setitem__('prefix', -1)),
        ('HEADER_NOT_ARRAY', lambda h, d: h['analysis_header'].__setitem__('assumptions', {})),
        ('MISSING_PER_TARGET_ITEM', lambda h, d: d[1]['items'].__setitem__('assumptions', [])),
    ):
        value = fixture()
        edit(value['header'], value['docs'])
        control('REJECT_' + name + '_WITH_CONSISTENT_HASHES', rebuild(value['header'], value['docs']), False)
    result = dict(classification='ACTUAL_ROOT_FETCH_SYNTHETIC_RPC_ORACLE_CONTROLS_NOT_NATIVE',
                  actual_source_file=str(source_file), actual_fetch_sha256=digest(current),
                  expected_sha256=digest((HERE/'EXPECTED.json').read_text()), first_red_sha256=digest(first_file.read_text()),
                  controls=rows, status='PASS', Native_execution_proven=False, database_calls=0,
                  no_hash_range_identity_or_item_count_guard_removed=True)
    (HERE/'RESULT.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(classification=result['classification'], status='PASS', controls=len(rows),
                         actual_fetch_sha256=result['actual_fetch_sha256'], Native_execution_proven=False)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo', type=Path)
    parser.add_argument('--old-only', action='store_true')
    args = parser.parse_args()
    main(args.repo.resolve(), args.old_only)
