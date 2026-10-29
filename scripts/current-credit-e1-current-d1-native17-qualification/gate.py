"""Current D1 remains CLOSED until root binds its complete terminal Originals."""
from pathlib import Path
import importlib.util

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CLOSED = 'E1_CURRENT_D1_CLOSED_ROOT_TERMINAL_NATIVE13_FULL_RESTORE_PACKAGE5_REQUIRED'


def original():
    path = ROOT / 'scripts/current-credit-e1-native-qualification/gate.py'
    spec = importlib.util.spec_from_file_location('e1_current_private_retained_gate', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def selected(cfg):
    if any(cfg.get(key) is None for key in ('accepted_D1', 'accepted_raw_parent', 'required_qualified_parent')):
        raise ValueError(CLOSED)
    pin = original().selected(cfg)
    if pin['head'] == 'd902e4d2e65cf5b382af1ab041120611f9a61078':
        raise ValueError('E1_CURRENT_FAILED_D902_IS_NOT_A_PREREQUISITE')
    expected = {key: pin[key] for key in ('original', 'native_group', 'package')}
    if cfg['accepted_raw_parent'] != expected:
        raise ValueError('E1_CURRENT_EXACT_ROOT_RAW_BINDING_REQUIRED')
    return pin


def retained_failure(cfg, raw):
    return original().retained_failure(cfg, raw)


def exact_group(group, ids, count):
    return original().exact_group(group, ids, count)


def admitted(cfg, originals, current_D1, frozen_D1_source, ids):
    selected(cfg)
    return original().admitted(cfg, originals, current_D1, frozen_D1_source, ids)
