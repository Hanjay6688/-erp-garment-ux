"""Only inherited imports see argv[0]; caller object/content always return."""
from contextlib import contextmanager
import sys


@contextmanager
def inherited_imports():
    original, values = sys.argv, list(sys.argv)
    sys.argv = values[:1]
    try:
        yield
    finally:
        original[:] = values
        sys.argv = original
