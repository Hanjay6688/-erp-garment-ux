"""Report the qualified SKU install phases on a private disposable runner."""

from contextlib import contextmanager
from contextvars import ContextVar
from time import monotonic_ns
from types import FunctionType, SimpleNamespace


PHASES = frozenset((
    'AFUI_PARENT_INSTALL', 'MANDOR_PARENT_DELTA', 'SKU_MOVING_PARENT_DELTA', 'SKU_MONEY_PARENT_DELTA',
    'SKU_COMPLETE_PARENT_STATE_DIGEST', 'SKU_MOVING_RUNTIME_SOURCE', 'SKU_MOVING_LOCKS',
    'SKU_MOVING_VERIFY_MANDOR', 'SKU_MOVING_CAPTURE_BEFORE', 'SKU_MOVING_PREPARE_DEFINITIONS',
    'SKU_MOVING_DDL_AND_GRANTS', 'SKU_MOVING_CAPTURE_AND_BIND_STATE', 'SKU_MOVING_VERIFY_MOVING',
    'SKU_AUTOMATIC_DELTA', 'SKU_AUTOMATIC_VERIFY', 'SKU_FULL25_COMPARE', 'GLOBAL_PRESEAL', 'B_BROWSER',
    'BF_BACKUP', 'BF_RESTORE', 'SKU_CREDIT_BASELINE', 'SKU_CREDIT_RESEAL',
))
_before_mandor = ContextVar('before_mandor', default=None)


@contextmanager
def before_mandor(callback):
    token = _before_mandor.set(callback)
    try:
        yield
    finally:
        _before_mandor.reset(token)


@contextmanager
def observe(phase):
    """The emitted values are fixed phase labels, states, and elapsed time."""
    if phase not in PHASES:
        raise ValueError('GLOBAL_PARENT_UNKNOWN_SKU_INSTALL_PHASE')
    callback = _before_mandor.get() if phase == 'MANDOR_PARENT_DELTA' else None
    if callback is not None:
        with observe('SKU_CREDIT_BASELINE'):
            callback()
    start = monotonic_ns()

    def emit(status):
        try:
            print(f'GLOBAL_PARENT_PHASE {phase} {status} elapsed_ms={(monotonic_ns() - start) // 1_000_000}', flush=True)
        except OSError:
            pass

    emit('STARTED')
    try:
        yield
    except BaseException:
        emit('FAILED')
        raise
    else:
        emit('COMPLETED')


def runtime_with_progress(entry, *, use_reviewed_digest=False):
    """Attach the observer where the exact source injects diagnostic callbacks."""
    original = entry.runtime
    if original.__globals__ is not vars(entry) or original.__closure__ is not None:
        raise ValueError('GLOBAL_PARENT_EXACT_SKU_RUNTIME_PROGRESS_ENTRY_REQUIRED')
    namespace = dict(original.__globals__, checkpoint=SimpleNamespace(observe_parent_phase=observe))
    if use_reviewed_digest:
        from sku_digest_binding import bind

        namespace['package_source'] = bind(entry)
        print('GLOBAL_PARENT_REVIEWED_BYTE_EQUIVALENT_DIGEST_BOUND', flush=True)
    return FunctionType(original.__code__, namespace, original.__name__, original.__defaults__)()
