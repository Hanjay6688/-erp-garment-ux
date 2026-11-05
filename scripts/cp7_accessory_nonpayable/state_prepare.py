"""Prepare the actual complete hot state before expensive business cases.

The temporary address-space limit protects recovery headroom. It does not
diagnose the previous runner disconnection or replace any financial gate.
"""
from contextlib import contextmanager
from pathlib import Path
import os
import resource
import time
from . import complete_original_io, lossless_state

START = 'AFUI_COMPLETE_STATE_PREREQUISITE_START.json'
RESULT = 'AFUI_COMPLETE_STATE_PREREQUISITE_RESULT.json'
MiB = 1024 * 1024


def memory_snapshot():
    info = {}
    for line in Path('/proc/meminfo').read_text().splitlines():
        name, _, value = line.partition(':')
        if name in ('MemTotal', 'MemAvailable'):
            info[name] = int(value.split()[0]) * 1024
    total, available = info['MemTotal'], info['MemAvailable']
    limits = []
    root = Path('/sys/fs/cgroup')
    directories = {root}
    for line in Path('/proc/self/cgroup').read_text().splitlines():
        if line.startswith('0::'):
            relative = Path(line[3:]).relative_to('/')
            if '..' in relative.parts:raise ValueError('AFUI_STATE_CGROUP_PATH_REQUIRED')
            current = root / relative
            while current != root:
                directories.add(current);current = current.parent
    for directory in sorted(directories):
        usage = directory / 'memory.current'
        if not usage.is_file():continue
        used = int(usage.read_text().strip())
        for name in ('memory.max', 'memory.high'):
            path = directory / name
            if not path.is_file():continue
            raw = path.read_text().strip()
            if raw == 'max':continue
            ceiling = int(raw)
            total = min(total, ceiling);available = min(available, max(0, ceiling - used))
            limits.append(dict(path=str(path), ceiling_bytes=ceiling, used_bytes=used))
    pages = [int(v) for v in Path('/proc/self/statm').read_text().split()[:2]]
    page_size = os.sysconf('SC_PAGE_SIZE')
    return dict(effective_total_bytes=total, available_bytes=available,
                virtual_bytes=pages[0] * page_size, resident_bytes=pages[1] * page_size,
                cgroup_limits=limits)


def memory_budget(snapshot, original_limits):
    reserve = max(256 * MiB, min(1024 * MiB, snapshot['effective_total_bytes'] // 4))
    headroom = snapshot['available_bytes'] - reserve
    ceiling = snapshot['virtual_bytes'] + headroom
    for limit in original_limits:
        if limit != resource.RLIM_INFINITY:ceiling = min(ceiling, limit)
    if headroom < 64 * MiB or ceiling - snapshot['virtual_bytes'] < 64 * MiB:
        raise ValueError('AFUI_COMPLETE_STATE_INSUFFICIENT_RECOVERY_MEMORY_HEADROOM')
    return dict(temporary_soft_bytes=ceiling, reserved_available_bytes=reserve,
                original_soft_bytes=original_limits[0], original_hard_bytes=original_limits[1])


@contextmanager
def memory_limit(budget):
    original = resource.getrlimit(resource.RLIMIT_AS)
    if original != (budget['original_soft_bytes'], budget['original_hard_bytes']):
        raise ValueError('AFUI_COMPLETE_STATE_RESOURCE_LIMIT_CHANGED_BEFORE_ENTRY')
    resource.setrlimit(resource.RLIMIT_AS, (budget['temporary_soft_bytes'], original[1]))
    try:yield
    finally:resource.setrlimit(resource.RLIMIT_AS, original)


def verify_unchanged(state, prepared):
    if lossless_state.graph_pin(state) != prepared['graph']:
        raise ValueError('AFUI_COMPLETE_STATE_CHANGED_AFTER_EARLY_PREREQUISITE')


def prepare(state, directory, save):
    directory = Path(directory)
    started = time.monotonic()
    source = dict(github_sha=os.environ.get('GITHUB_SHA'),
                  manifest=complete_original_io.pin(Path(__file__).with_name('SOURCE.json')))
    base = dict(actual_case_credit=0, production_go=False, independent_acceptance=False,
                previous_runner_shutdown_origin_proven=False, source=source)
    stage, budget, snapshot = 'RESOURCE_SNAPSHOT', None, None
    save(START, dict(base, status='STARTED_COMPLETE_HOT_STATE_PREREQUISITE'))
    try:
        snapshot = memory_snapshot()
        budget = memory_budget(snapshot, resource.getrlimit(resource.RLIMIT_AS))
        with memory_limit(budget):
            stage = 'COMPLETE_GRAPH_BEFORE'
            graph = lossless_state.graph_pin(state)
            stage = 'COMPLETE_CANONICAL_ORIGINAL'
            original = save('AFUI_BROWSER_SETTINGS_STATE.json', state)
            stage = 'COMPLETE_LOSSLESS_CACHE_AND_EVERY_CANONICAL_BYTE'
            target = directory / 'AFUI_BROWSER_SETTINGS_STATE_CACHE.json'
            cache = lossless_state.save(target, state, original)
            complete_original_io.publish(target)
            stage = 'COMPLETE_GRAPH_AFTER'
            verify_unchanged(state, dict(graph=graph))
        result = dict(graph=graph, browser_settings_state_original=original,
                      browser_settings_cache_original=cache)
        receipt = save(RESULT, dict(base, status='PASS_COMPLETE_HOT_STATE_PREREQUISITE',
            stage=stage, memory_before=snapshot, memory_after=memory_snapshot(), budget=budget,
            elapsed_seconds=time.monotonic() - started, **result))
        result['prerequisite_result_original'] = receipt
        return result
    except Exception as error:
        # The cap has already been restored before recording the original
        # failure. Owning engine recovery remains responsible for the DB.
        try:
            receipt = save(RESULT, dict(base, status='FAILED_COMPLETE_HOT_STATE_PREREQUISITE',
                stage=stage, memory_before=snapshot, budget=budget,
                elapsed_seconds=time.monotonic() - started,
                error_type=type(error).__name__, error=str(error)[:2000]))
            error.add_note('AFUI_COMPLETE_STATE_FAILURE_ORIGINAL:' + str(receipt))
        except Exception as capture_error:
            error.add_note('AFUI_COMPLETE_STATE_FAILURE_CAPTURE_UNAVAILABLE:' + type(capture_error).__name__)
        raise
