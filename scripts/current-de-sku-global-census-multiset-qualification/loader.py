"""All direct runtime loaders admit the complete current source first."""
from pathlib import Path
import importlib.util

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


def module(kind):
    load('global_multiset_loader_early_admission', HERE / 'admission.py').preflight()
    return load('global_multiset_admitted_compiler', HERE / 'compile_modules.py').module(kind)


def capture(): return module('capture')
def integration(): return module('integration')
def runner(): return module('runner')
def gate(): return module('gate')
def census(): return module('census')
