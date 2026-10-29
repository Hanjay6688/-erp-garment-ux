"""Execution of the new wrapper with explicit local no-SQL API/group doubles.

These controls test orchestration and first-raw preservation, not ERP behavior.
No synthetic group is saved as a runtime Original or Native qualification.
"""
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from types import ModuleType, SimpleNamespace
from unittest import TestCase, main
from unittest.mock import patch
import importlib.util
import json

HERE = Path(__file__).resolve().parent


def helper():
    spec = importlib.util.spec_from_file_location('s03_reader14_wiring_local_unit', HERE / 'reader_group.py')
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


def group(ids):
    return dict(status='PASS', counts={'PASS': len(ids)}, planned_case_ids=list(ids),
        complete_boundary_restored=True, cases={key: dict(status='PASS',
            full_boundary_restored=True, public_schema_unchanged=True) for key in ids})


class ReaderWiring(TestCase):
    def test_same_state_evidence_fresh11_and_physical_overlay_reach_factory_then_separate_group(self):
        reader = helper(); cfg = json.loads((HERE / 'CONFIG.json').read_bytes())
        old = group(cfg['original_Native11_ids']); new = group(cfg['reader_Native3_ids'])
        state, evidence, cursor = object(), {}, object()
        trace = []; active = []
        factory = SimpleNamespace(IDS=tuple(cfg['reader_Native3_ids']))

        def planned(cur, today, *, state: object, evidence: dict, fresh_original11: dict):
            self.assertIs(cur, cursor); self.assertEqual(today, 'DECLARED_LOCAL_UNIT_DAY')
            self.assertIs(state, fixture_state); self.assertIs(evidence, fixture_evidence)
            self.assertIs(fresh_original11, old); self.assertEqual(active, ['PRODUCT_CATALOG_OVERLAY'])
            trace.append('factory'); return [(key, lambda: None) for key in factory.IDS]
        fixture_state, fixture_evidence = state, evidence
        factory.cases = planned

        @contextmanager
        def product_catalog(cur):
            self.assertIs(cur, cursor); active.append('PRODUCT_CATALOG_OVERLAY')
            try:
                yield
            finally:
                active.pop()

        @contextmanager
        def exact_public_catalog(actual_native, *, retain_raw):
            self.assertIs(actual_native, native); self.assertIs(retain_raw, True)
            trace.append('strict3_enter'); yield {'classification': 'LOCAL_PUBLIC_CATALOG_DOUBLE'}
            trace.append('strict3_exit')

        def strict_group(label, cases, verify):
            self.assertEqual(label, reader.LABEL); self.assertIs(verify, verifier)
            self.assertEqual([key for key, _ in cases(cursor, 'DECLARED_LOCAL_UNIT_DAY')], list(factory.IDS))
            self.assertEqual(active, []); trace.append('strict3'); return new

        verifier = lambda cur: None
        native = SimpleNamespace(strict_group=strict_group)
        catalog_module = ModuleType('cp7_catalog_state'); catalog_module.exact_public_catalog = exact_public_catalog
        real_spec = reader.importlib.util.spec_from_file_location
        def spec(name, path):
            if Path(path) == reader.ROOT / reader.FACTORY:
                return SimpleNamespace(loader=SimpleNamespace(exec_module=lambda module: None))
            return real_spec(name, path)
        with patch.dict('sys.modules', {'cp7_catalog_state': catalog_module}), \
             patch.object(reader.importlib.util, 'spec_from_file_location', spec), \
             patch.object(reader.importlib.util, 'module_from_spec', return_value=factory), \
             patch.object(reader, 'retain', side_effect=lambda n, r: trace.append('retain')):
            result = reader.run(native, SimpleNamespace(product_catalog=product_catalog), state, evidence, verifier, old)
        self.assertIs(result, new); self.assertIs(evidence['reader_native3'], new)
        self.assertEqual(trace, ['strict3_enter', 'factory', 'strict3', 'strict3_exit', 'retain'])
        self.assertTrue(evidence['both_groups_same_actual_installation'])
        self.assertTrue(evidence['reader3_requires_actual_fresh_original11'])
        self.assertFalse(evidence['combined_strict14_fabricated'])

    def test_actual_first_raw_bytes_are_copied_once_and_different_retry_is_refused(self):
        reader = helper()
        with TemporaryDirectory() as folder:
            root = Path(folder); source = root / 'source'; source.mkdir()
            names = [reader.LABEL + '.json', reader.LABEL + '_BUSINESS_DAY_FIRST_ATTEMPT.json']
            for index, name in enumerate(names):
                (source / name).write_bytes(('LOCAL_ONLY_RAW_PRESERVATION_DOUBLE_' + str(index)).encode())
            native = SimpleNamespace(r1=SimpleNamespace(OUT=source)); evidence = {}
            with patch.object(reader, 'ROOT', root):
                reader.retain(native, evidence); reader.retain(native, evidence)
                for name in names:
                    self.assertEqual((root / 'cp6-proof/t3' / name).read_bytes(), (source / name).read_bytes())
                original = (root / 'cp6-proof/t3' / names[1]).read_bytes()
                (source / names[1]).write_bytes(b'LOCAL_DIFFERENT_RETRY')
                with self.assertRaisesRegex(ValueError, 'FIRST_ORIGINAL_CANNOT_BE_OVERWRITTEN'):
                    reader.retain(native, evidence)
                self.assertEqual((root / 'cp6-proof/t3' / names[1]).read_bytes(), original)
        self.assertEqual(len(evidence['reader3_strict_originals']), 2)


if __name__ == '__main__':
    main(verbosity=2)
