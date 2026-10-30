"""Preserve caller identity/content across inherited import guards and errors."""
from contextlib import contextmanager
import sys


@contextmanager
def inherited_imports():
    caller, contents = sys.argv, sys.argv[:]
    sys.argv = contents[:1]
    try:
        yield
    finally:
        caller[:] = contents
        sys.argv = caller
