"""Own source-import boundary; inherited no-argument CLIs stay unchanged."""
from contextlib import contextmanager
import sys


@contextmanager
def source_import_arguments():
    """After the outer parser accepts flags, import sources with argv[0] only.

    Includes lazy imports during admission. Restore the exact caller list and
    contents for every exit, including SystemExit and KeyboardInterrupt. This
    does not select a runtime operation or change an inherited CLI/function.
    """
    caller = sys.argv
    contents = caller[:]
    sys.argv = contents[:1]
    try:
        yield
    finally:
        caller[:] = contents
        sys.argv = caller
