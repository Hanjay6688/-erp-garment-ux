"""Preserve wrapper arguments around inherited no-argument entrypoint imports."""
from contextlib import contextmanager
from functools import wraps
import sys


@contextmanager
def inherited_arguments():
    original = sys.argv
    sys.argv = original[:1]
    try:
        yield
    finally:
        sys.argv = original


def inherited_entrypoint(operation):
    @wraps(operation)
    def scoped(*args,**kwargs):
        with inherited_arguments():
            return operation(*args,**kwargs)
    return scoped
