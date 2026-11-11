"""Separate cold source validation from the unchanged Native operation budget."""
from contextlib import contextmanager
import signal

# CI complete source validation took 199 seconds on the exact e8 candidate.
# Keep a bounded 360-second cold-source allowance; transaction time is separate.
SOURCE_SECONDS = 360
OPERATION_SECONDS = 120
CLEANUP_SECONDS = 5


@contextmanager
def phase(name):
    if name not in ('SOURCE', 'OPERATION'):
        raise ValueError('CURRENT_SKU_FIXED_BROWSER_DEADLINE_PHASE_REQUIRED')
    if signal.getitimer(signal.ITIMER_REAL) != (0.0, 0.0):
        raise ValueError('CURRENT_SKU_BROWSER_PREEXISTING_DEADLINE_REFUSED')
    previous = signal.getsignal(signal.SIGALRM)
    def expired(signum, frame):
        raise TimeoutError('CURRENT_SKU_BROWSER_' + name + '_DEADLINE_EXCEEDED')
    signal.signal(signal.SIGALRM, expired)
    try:
        signal.setitimer(signal.ITIMER_REAL, SOURCE_SECONDS if name == 'SOURCE' else OPERATION_SECONDS)
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)
