"""Exact local output and scope controls; no financial case is executed."""
from contextlib import contextmanager
from copy import deepcopy
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from types import FunctionType, ModuleType
from unittest.mock import patch
import gzip
import importlib.util
import io
import json
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('mandor_complete_output_control_subject', HERE / 'output_binding.py')
subject = importlib.util.module_from_spec(spec)
spec.loader.exec_module(subject)


@contextmanager
def fixture():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        for name in subject.SOURCES:
            relative = Path('scripts/cp7_accessory_nonpayable') / name
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((ROOT / relative).read_bytes())
        path = root / subject.RETENTION
        path.parent.mkdir(parents=True)
        path.write_bytes((ROOT / subject.RETENTION).read_bytes())
        for relative in ('scripts/cp6_auditor_runner.py', 'scripts/current-s03-sku-s05-composite-qualification/modes.py'):
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((ROOT / relative).read_bytes())
        with patch.object(subject, 'ROOT', root):
            yield root


class MandorCompleteOutput(unittest.TestCase):
    def test_fixed_sorted_Originals_keep_exact_legacy_bytes_and_refuse_even_identical_overwrite(self):
        value = dict(amount=Decimal('0.00'), all_fields=[0, False, None, 'complete raw values' * 10000])
        expected = (json.dumps(value, sort_keys=True, default=str) + '\n').encode()
        with fixture() as root:
            record = subject.save_access(value, 'MANDOR_BROWSER_STATE.json')
            path = root / 'cp6-proof/t3' / record['name']
            self.assertEqual(path.read_bytes(), expected)
            self.assertEqual(record, dict(name=path.name, bytes=len(expected), sha256=sha256(expected).hexdigest()))
            with self.assertRaisesRegex(ValueError, 'FIRST_SESSION_ORIGINAL_OVERWRITE_REFUSED'):
                subject.save_access(value, path.name)
            self.assertEqual(path.read_bytes(), expected)
            with self.assertRaisesRegex(ValueError, 'FIXED_ACCESS_ORIGINAL_NAME'):
                subject.save_access(value, 'UNREVIEWED.json')
            partial = root / 'partial.json'
            partial.write_bytes(expected)
            with self.assertRaises(FileExistsError):
                subject.finish_exclusive(partial, path, 'conflict')
            self.assertTrue(partial.is_file())
            self.assertEqual(path.read_bytes(), expected)

    def test_access_gzip_keeps_every_boundary_value_and_all_original_refusals(self):
        with fixture() as root:
            path = root / subject.RETENTION
            spec = importlib.util.spec_from_file_location('mandor_exact_retention_local_fixture', path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            original = module.retain
            before = dict(actual_all22={str(index): dict(complete='catalogue ' * 100) for index in range(22)},
                          full_data_and_sequences={'erp.explicit_model': ['0.00', 'original'], 'sequence:explicit_model': ['1', False]})
            after = deepcopy(before)
            raw = (json.dumps(dict(before=before, after=after), sort_keys=True, default=str) + '\n').encode()
            with self.assertRaisesRegex(RuntimeError, 'ORIGINAL_FAILURE'):
                with subject.retention_scope(module):
                    record = module.retain('EXPLICIT_MODEL', before, after)
                    saved = root / 'cp6-proof/t3' / record['original']['name']
                    packed = saved.read_bytes()
                    self.assertEqual(gzip.decompress(packed), raw)
                    self.assertEqual(packed, gzip.compress(raw, mtime=0))
                    self.assertEqual(record['original']['raw_bytes'], len(raw))
                    self.assertEqual(record['original']['raw_sha256'], sha256(raw).hexdigest())
                    self.assertEqual(record['original']['gzip_sha256'], sha256(packed).hexdigest())
                    changed = deepcopy(after)
                    changed['full_data_and_sequences']['erp.explicit_model'] = ['9.00', 'changed']
                    with self.assertRaisesRegex(ValueError, 'UNEXPECTED_DATA_OR_SEQUENCE_CHANGE'):
                        module.retain('EXPLICIT_MODEL_REFUSAL', before, changed)
                    allowed = module.retain('EXPLICIT_MODEL_ALLOWED', before, changed, allowed=('erp.explicit_model',))
                    self.assertEqual(allowed['changed_tables'], ['erp.explicit_model'])
                    raise RuntimeError('ORIGINAL_FAILURE')
            self.assertIs(module.retain, original)
            self.assertNotIn(subject.GZIP_HELPER, module.__dict__)
            changed = bytearray(path.read_bytes());changed[-1] ^= 1
            with self.assertRaisesRegex(ValueError, 'EXACT_ACCESS_RETENTION_SOURCE'):
                subject.derive_retention(bytes(changed))

    def test_native_and_copy_print_scopes_use_full_compiler_context_and_restore_after_failure(self):
        with fixture() as root:
            for kind, relative, name in (
                ('native', 'scripts/cp6_auditor_runner.py', '_strict_group_once'),
                ('copies', 'scripts/current-s03-sku-s05-composite-qualification/modes.py', 'strict_rows')):
                path = root / relative
                module = ModuleType('mandor_exact_case_print_compiler_fixture_' + kind)
                module.__file__ = str(path)
                original = FunctionType(subject.function_code(path.read_bytes(), path, name), module.__dict__)
                setattr(module, name, original)
                with self.assertRaisesRegex(RuntimeError, 'ORIGINAL_FAILURE'):
                    with subject.case_scope(module, kind):
                        self.assertIsNot(getattr(module, name), original)
                        self.assertIsNot(getattr(module, name).__code__, original.__code__)
                        helper = module.__dict__['_afui_retain_complete_case_stdout']
                        output = io.StringIO()
                        from contextlib import redirect_stdout
                        with redirect_stdout(output):
                            receipt = helper('EXPLICIT_MODEL_' + kind, 'CONTROL', dict(status='PASS', all_values=[0, False, None]))
                        saved = root / 'cp6-proof/t3/MANDOR_CASE_STDOUT' / receipt['complete_original_file']
                        self.assertEqual(json.loads(saved.read_bytes())['all_values'], [0, False, None])
                        self.assertLess(len(output.getvalue().encode()), 2048)
                        raise RuntimeError('ORIGINAL_FAILURE')
                self.assertIs(getattr(module, name), original)
                self.assertNotIn('_afui_retain_complete_case_stdout', module.__dict__)

    def test_exact_complete_copy_preserves_existing_original_and_changed_sources_refuse(self):
        with fixture() as root:
            before, after = root / 'before.json', root / 'after.json'
            before.write_bytes(b'{"exact":"original"}\n')
            result = subject.copy_exact(before, after)
            self.assertEqual(result['bytes'], before.stat().st_size)
            self.assertEqual(before.read_bytes(), after.read_bytes())
            before.write_bytes(b'{"changed":"source"}\n')
            with self.assertRaisesRegex(ValueError, 'FIRST_STRICT_ORIGINAL_CHANGED'):
                subject.copy_exact(before, after)
            self.assertEqual(after.read_bytes(), b'{"exact":"original"}\n')
            path = root / 'scripts/cp7_accessory_nonpayable/case_output.py'
            path.write_bytes(path.read_bytes() + b'\n')
            with self.assertRaisesRegex(ValueError, 'EXACT_CURRENT_AFUI_SOURCE_REQUIRED'):
                subject.frozen_source(path.name)


if __name__ == '__main__':
    unittest.main()
