"""Exact four inherited vendor Original inputs, never arbitrary output waivers."""
import importlib.util
from midnight_common import ROOT, regular, pin

PARENT = 'scripts/current-attendance-choice-reader-native14-qualification'
TARGET = 'docs/cp7/d17-14/ow08/vendor-combined41c-pass/'


def original_reader(root=ROOT):
    path = regular(root, PARENT + '/proof_inputs.py')
    spec = importlib.util.spec_from_file_location('midnight_unchanged_four_Original_reader', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def present_pins(root=ROOT):
    names = ('CP7_VENDOR_RECEIVABLE_COMBINED11.json', 'T3_PACKAGE_INSTALL.json',
             'T3_PACKAGE_FILES_INSTALL.json', 'T3_BACKUP_RESTORE_DRILL.json')
    present = [TARGET + name + '.gz' for name in names
               if (root / (TARGET + name + '.gz')).exists() or (root / (TARGET + name + '.gz')).is_symlink()]
    if not present:
        return {}
    checked = original_reader(root).documents(root / PARENT)
    if set(checked) != set(names):
        raise ValueError('MIDNIGHT_EXACT_FOUR_INHERITED_ORIGINALS_REQUIRED')
    result = {}
    for name in present:
        raw = regular(root, name).read_bytes()
        key = name[len(TARGET):-3]
        if raw != checked[key]['compressed']:
            raise ValueError('MIDNIGHT_INHERITED_ORIGINAL_CHANGED:' + name)
        result[name] = pin(raw)
    return result
