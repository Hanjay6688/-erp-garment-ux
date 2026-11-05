"""Bounded reproduction of the owning Afui cache allocation, no ERP database."""
from decimal import Decimal
from pathlib import Path
import json
import os
import resource
import sys
import time
import traceback

mode, checkout, directory = sys.argv[1:]
directory = Path(directory).resolve()
sys.path.insert(0, str(Path(checkout).resolve() / 'scripts'))
from cp7_accessory_nonpayable import complete_original_io as originals, lossless_state as cache

COUNT = 180_000
PAGE = os.sysconf('SC_PAGE_SIZE')
started = time.monotonic()
original = directory / 'REGRESSION_RAW_ORIGINAL.json'
manifest = directory / 'REGRESSION_INPUT.json'
target = directory / 'REGRESSION_STREAMED_CACHE.json'


def virtual():
    return int(Path('/proc/self/statm').read_text().split()[0]) * PAGE


def hot():
    skus = [f'grade-A-{number:04d}' for number in range(2000)]
    policy = ['existing-approval', 'reversible-caller', 'one-owner']
    rows = [
        dict(row_id=i, sku=skus[i % len(skus)], count=i % 17, hpp=(i % 9901) / 100,
             access=policy, payable=False, state='OPEN', location='internal-fixture',
             cut_at='2026-11-06T01:23:00+07:00', refund=None, ledger=i // 11,
             source='synthetic-cache-regression')
        for i in range(COUNT)
    ]
    return dict(current=rows, retained_parent=rows, exact_alias=rows[0], independent=dict(rows[0]),
                decimal=Decimal('0.014'), negative_zero=-0.0, tuple_value=(1, 'x'), schema=policy)


if mode == 'fixture':
    value = hot()
    base = virtual()
    reference = originals.save_sorted(original, value, 'AFUI_REPRODUCTION_FIRST_ORIGINAL_CONFLICT')
    plan = dict(reference=reference, fixture_rows=COUNT, address_limit_bytes=base + 96 * 1024 * 1024,
                fixture_initial_virtual_bytes=base)
    manifest.write_text(json.dumps(plan, indent=2) + '\n')
    print(json.dumps(dict(status='ONE_EXACT_FIXTURE_ORIGINAL_SAVED', **plan)))
    sys.exit()

plan = json.loads(manifest.read_bytes())
reference = plan['reference']
limit = plan['address_limit_bytes']
value = hot() if mode in ('old','stream') else None
before = virtual()
soft, hard = resource.getrlimit(resource.RLIMIT_AS)
resource.setrlimit(resource.RLIMIT_AS, (limit, hard))
if mode == 'old':
    try:
        cache.save(directory / 'OLD_CACHE_MUST_NOT_BE_PUBLISHED.json', value, reference)
    except MemoryError as error:
        where = traceback.extract_tb(error.__traceback__)[-1]
        result = dict(status='LEGACY_CACHE_ALLOCATION_REFUSED_WITH_MEMORY_ERROR', failure=where.name,
                      first_line=where.lineno, code=where.line)
    else:
        raise AssertionError('Old allocation unexpectedly passed the bounded regression')
elif mode == 'stream':
    before_graph = cache.graph_pin(value)
    receipt = cache.save(target, value, reference)
    assert cache.graph_pin(value) == before_graph
    (directory / 'REGRESSION_CACHE_PIN.json').write_text(json.dumps(receipt, indent=2) + '\n')
    result = dict(status='NEW_STREAM_CACHE_SAVED_UNDER_SAME_LIMIT', cache=receipt,
                  exact_hot_identity_graph=before_graph, original_pin=reference)
elif mode == 'cold':
    receipt = json.loads((directory / 'REGRESSION_CACHE_PIN.json').read_bytes())
    decoded = cache.read(target, receipt['sha256'], original, reference['sha256'])
    assert len(decoded['current']) == COUNT
    assert decoded['current'] is decoded['retained_parent']
    assert decoded['exact_alias'] is decoded['current'][0]
    assert decoded['exact_alias'] == decoded['independent'] and decoded['exact_alias'] is not decoded['independent']
    assert decoded['schema'] is decoded['current'][0]['access']
    assert cache.canonical_pin(decoded) == {k:reference[k] for k in ('bytes','sha256')}
    result = dict(status='NEW_COLD_READ_EXACT_RAW_BYTES_AND_ALIASES_UNDER_SAME_LIMIT',
                  exact_immutable_original=True, exact_aliases_preserved=True, independent_containers_preserved=True)
else:
    raise AssertionError(mode)
result.update(fixture_rows=COUNT, address_limit_bytes=limit, before_virtual_bytes=before,
              peak_RSS_KiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
              elapsed_seconds=round(time.monotonic()-started,3), actual_ERP_cases=0)
(directory / f'{mode.upper()}_RESULT.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, sort_keys=True))
