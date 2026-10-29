"""Actual caller regressions: generated output policy cannot hide new source."""
from pathlib import Path
import importlib.util
import json
import unittest
import uuid

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('s03_full_generated_caller_regressions', HERE / 'source_check.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class FullGeneratedGate(unittest.TestCase):
    def test_actual_source_gate_rejects_arbitrary_python_beside_metadata(self):
        target = ROOT / 'cp6-proof/t3' / ('UNDECLARED_SOURCE_' + uuid.uuid4().hex + '.py')
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            with target.open('xb') as stream:
                stream.write(b'raise RuntimeError("THIS_UNDECLARED_SOURCE_MUST_NEVER_RUN")\n')
            with self.assertRaisesRegex(ValueError, 'UNDECLARED_UNTRACKED_SOURCE'):
                gate.check()
        finally:
            target.unlink(missing_ok=True)

    def test_actual_source_gate_rejects_symlink_receipt_before_reading_it(self):
        target = ROOT / 'cp6-proof/t3/ARTIFACT_FETCH' / (uuid.uuid4().hex + '-1.json')
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            target.symlink_to(HERE / 'GENERATED_RECEIPTS.json')
            with self.assertRaisesRegex(ValueError, 'SYMLINK'):
                gate.check()
        finally:
            target.unlink(missing_ok=True)

    def test_actual_source_gate_rejects_extra_source_field_in_receipt(self):
        target = ROOT / 'cp6-proof/t3/ARTIFACT_FETCH' / (uuid.uuid4().hex + '-1.json')
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            with target.open('x') as stream:
                json.dump(dict(source_module='UNDECLARED.py'), stream)
            with self.assertRaisesRegex(ValueError, 'ARTIFACT_CLOSED_FIELDS'):
                gate.check()
        finally:
            target.unlink(missing_ok=True)


if __name__ == '__main__':
    unittest.main()
