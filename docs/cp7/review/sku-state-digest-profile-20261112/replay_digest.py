"""Compare the exact SKU v1 digest on retained catalogues, without a DB."""
import argparse
import cProfile
import hashlib
import importlib.util
import io
import json
import platform
import pstats
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from statistics import median
from time import perf_counter, process_time
from types import MappingProxyType
from uuid import UUID
from zipfile import ZipFile


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def catalogue(path, pin, member):
    assert digest(path.read_bytes()) == pin, path
    with ZipFile(path) as archive:
        names = [name for name in archive.namelist() if name.rsplit('/', 1)[-1] == member]
        assert len(names) == 1, names
        raw = archive.read(names[0])
    return json.loads(raw), {'member': names[0], 'bytes': len(raw), 'sha256': digest(raw)}


def canonical(package, payload):
    tree = ['cp7.complete-postgres-parent-state.v1', package.state_value(payload)]
    return json.dumps(tree, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()


def compare_bytes(old, new, payload):
    expected = canonical(old, payload)
    assert old.state_digest(payload) == new.state_digest(payload) == digest(expected)

    class Sink(io.BytesIO):
        update = io.BytesIO.write

        def hexdigest(self):
            return self.getvalue()

    for package in (old, new):
        sha256 = package.sha256
        try:
            package.sha256 = Sink
            assert package.state_digest(payload) == expected
        finally:
            package.sha256 = sha256
    return {'bytes': len(expected), 'sha256': digest(expected)}


def controls(old, new):
    tz = timezone(timedelta(hours=7))
    shared = {'money': Decimal('-73.0100'), 'ints': [1, True, 0, False, 10**100, -9],
              'escaped': 'é😀\n\x00"\\', 'binary': [b'\x00\xff', bytearray(b'\x00\xff')]}
    values = MappingProxyType({
        UUID(int=42): [datetime(2026, 11, 12, 6, 0, tzinfo=tz, fold=1), date(2026, 11, 12),
                       time(6, 1, tzinfo=tz, fold=1), timedelta(seconds=-1)],
        ('nested key', 2): [frozenset({(False, None), 'é', b'x'}), set(), {}, [], (), frozenset()],
        4: (shared, shared, [-0.0, 0.0, 1e40]),
        '4': ['é😀' * 35000, list(range(63)), list(range(64)), list(range(65))],
    })
    exact = {
        'all_types_and_flush': compare_bytes(old, new, values),
        'cache_capacity_and_repeat': compare_bytes(old, new, [
            [f'text {i}' for i in range(66000)], list(range(2080)), ['text 0', 0],
        ]),
    }
    before = new.state_digest(values)
    shared['money'] = Decimal('-73.0101')
    assert new.state_digest(values) != before
    exact['changed_nested_state'] = compare_bytes(old, new, values)

    failures = []
    for payload in ([object()], {'x': float('inf')}, [Decimal('NaN')], {object(): None}, ['\ud800']):
        outcomes = []
        for package in (old, new):
            try:
                package.state_digest(payload)
            except (TypeError, UnicodeError) as error:
                outcomes.append((type(error).__name__, str(error)))
        assert len(outcomes) == 2 and outcomes[0] == outcomes[1], outcomes
        failures.append(outcomes[0])
    return {'byte_preimages': exact, 'refusals_unchanged': failures}


def run(package, payload):
    wall, cpu = perf_counter(), process_time()
    actual = package.state_digest(payload)
    return {'wall_s': round(perf_counter() - wall, 6), 'cpu_s': round(process_time() - cpu, 6),
            'sha256': actual}


def main(args):
    old = load(args.baseline, 'baseline_package')
    new = load(args.candidate, 'candidate_package')
    full, a165 = catalogue(args.a165, 'b92b23d962ab2f91fffcbdf30403140c3dbd11ff89a160c573ac64e12c1abecd',
                           'SKU_GLOBAL_PARENT_ACTUAL_FULL25.json')
    original, native27 = catalogue(args.native27, '9ad923d20d0972b2a01df3ce3307bf03db537406ac89f99f700cf6d235bfc341',
                                  'CP7_SKU_MANAGED_RECOVERY_NATIVE27.json')
    native = original['committed']['SKU_NATIVE7_COST5_RACES3_PERMISSION_WAITS7_RECOVERY_BUSY1_AUTH_BROWSER4']
    native = native['Native_to_copy_handoff']['raw_current_catalog']
    assert len(full) == 25 and len(native) == 22

    # The envelopes are replay fixtures. The catalogues inside are actual
    # retained originals. CI does not persist all 15 in-memory preimages.
    before = {key: full[key] for key in native}
    payloads = [
        ('MANDOR_NATIVE22', {'before': native, 'after': native}),
        ('MOVING_NATIVE22_TO_A165_22', {'before': native, 'after': before}),
        ('MONEY_A165_25_WITH_NESTED_PARENT', {'before': before, 'after': full,
                                             'predecessor': {'before': native, 'after': before}}),
    ]
    comparisons = []
    for lap in range(5):
        for index, ((name, snapshot), binding) in enumerate(zip(payloads, old.STATE_BINDINGS, strict=True)):
            _, _, key, contract = binding
            payload = {key: snapshot, 'verified_parent_proof': {'replay': name}, 'contract': contract}
            methods = [('baseline', old), ('candidate', new)]
            if (lap + index) % 2:
                methods.reverse()
            measured = {label: run(package, payload) for label, package in methods}
            assert measured['baseline']['sha256'] == measured['candidate']['sha256'], (name, lap)
            comparisons.append({'case': name, 'lap': lap + 1, **measured})
            print(name, lap + 1, *(measured[k]['cpu_s'] for k in ('baseline', 'candidate')), flush=True)
    summary = {}
    for label, _ in payloads:
        selected = [row for row in comparisons if row['case'] == label]
        summary[label] = {mode: {unit: median(row[mode][unit] for row in selected)
                                 for unit in ('cpu_s', 'wall_s')} for mode in ('baseline', 'candidate')}

    profile = {}
    for label, package in [('baseline', old), ('candidate', new)]:
        profiler = cProfile.Profile()
        profiler.runcall(package.state_digest, full)
        stats = pstats.Stats(profiler)
        profile[label] = {'calls': stats.total_calls, 'seconds_with_profiler': stats.total_tt,
                          'top': [{'function': f'{name[0].rsplit("/", 1)[-1]}:{name[2]}',
                                   'calls': data[1], 'self_s': round(data[2], 6)}
                                  for name, data in sorted(stats.stats.items(), key=lambda pair: -pair[1][2])[:10]]}
    output = {'python': platform.python_version(), 'baseline_source': digest(args.baseline.read_bytes()),
              'candidate_source': digest(args.candidate.read_bytes()), 'a165_original': a165,
              'native27_original': native27, 'comparisons': comparisons, 'medians': summary,
              'profile_actual_full25': profile, 'controls': controls(old, new)}
    args.out.write_text(json.dumps(output, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('baseline', 'candidate', 'a165', 'native27', 'out'):
        parser.add_argument(name, type=Path)
    main(parser.parse_args())
