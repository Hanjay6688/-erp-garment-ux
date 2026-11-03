"""Unique inert bindings for the owning money qualifier; no ERP imports."""
from contextlib import contextmanager
from pathlib import Path
import importlib.util
import sys

HERE=Path(__file__).resolve().parent


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


assembly=load('money_owning_explicit_current_parent_bridge',HERE/'assembly.py')
admission=assembly.admission
component=load('money_owning_explicit_nineteen_component',HERE/'component.py')
package_derivation=load('money_owning_explicit_complete_package',HERE/'package.py')


@contextmanager
def retained_arguments():
    original=sys.argv;contents=list(original)
    sys.argv=original[:1]
    try:yield
    finally:
        original[:]=contents
        sys.argv=original
