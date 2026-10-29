"""Inherited import guards see no child CLI flags, including lazy admission."""
from contextlib import contextmanager
import sys


@contextmanager
def inherited_imports():
    caller = sys.argv
    contents = caller[:]
    sys.argv = contents[:1]
    try:
        yield
    finally:
        caller[:] = contents
        sys.argv = caller
