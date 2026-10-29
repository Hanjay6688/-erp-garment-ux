"""Offline allocation/source controls; imports no ERP, DB client or runtime."""
import importlib.util
import os
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('e1_late_source_only', HERE/'source_check.py')
source = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source)


class SourceBoundary(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = source.git('show', source.BASE+':'+source.CASES)
        cls.after = (source.ROOT/source.CASES).read_bytes()

    def test_exact_one_callback_derivation_preserves_seventeen_ids(self):
        proof = source.derivation(self.before, self.after)
        self.assertEqual(len(proof['all_seventeen_case_ids']), 17)
        self.assertTrue(proof['other_sixteen_callback_bodies_unchanged'])
        self.assertFalse(proof['Native_execution'])

    def test_change_before_callback_is_rejected(self):
        altered = self.after.replace(b"def upstream():", b"def upstream_unauthorized():", 1)
        with self.assertRaisesRegex(ValueError, 'OUTSIDE_SINGLE_APPROVED'):
            source.derivation(self.before, altered)

    def test_change_after_callback_is_rejected(self):
        altered = self.after.replace(b"def altered(date):", b"def altered_unauthorized(date):", 1)
        with self.assertRaisesRegex(ValueError, 'OUTSIDE_SINGLE_APPROVED'):
            source.derivation(self.before, altered)

    def test_case_id_mutation_is_rejected(self):
        altered = self.after.replace(b'E_PRICE_INCREASE_80_NET550_AR470', b'E_UNAUTHORIZED_CASE', 1)
        with self.assertRaisesRegex(ValueError, 'OUTSIDE_SINGLE_APPROVED|SEVENTEEN_CASE_IDS'):
            source.derivation(self.before, altered)

    def test_absent_or_duplicate_callback_is_rejected(self):
        absent = self.after.replace(b'def late_failure():', b'def unauthorized_callback():', 1)
        for raw in (absent, self.after+b'\ndef late_failure():\n    pass\n'):
            with self.assertRaisesRegex(ValueError, 'EXACT_SINGLE_LATE_FAILURE'):
                source.derivation(self.before, raw)

    def test_native_journal_target_is_rejected(self):
        altered = self.after.replace(b'after insert on cp7_credit_note_carry_de.operations_v1',
                                     b'before insert on erp.journal_entries', 1)
        with self.assertRaisesRegex(ValueError, 'APPROVED_PRIVATE_AFTER_INSERT'):
            source.derivation(self.before, altered)

    def test_frozen_product_runtime_mutation_is_rejected_without_writing(self):
        path = source.ROOT/'scripts/cp7_credit_correction_de/note_carry/06_owning.sql'
        original = Path.read_bytes

        def read(current):
            value = original(current)
            return value+b'\n' if current == path else value

        with patch.object(Path, 'read_bytes', read):
            with self.assertRaisesRegex(ValueError, 'NINE_RUNTIME_LEAVES_MUST_REMAIN_EXACT'):
                source.expected()

    def test_bind_refuses_ci_without_mutating_source(self):
        path = HERE/'SOURCE.json'
        before = path.read_bytes() if path.exists() else None
        with patch.dict(os.environ, {'CI':'true'}):
            with self.assertRaisesRegex(ValueError, 'CANNOT_BE_REGENERATED_IN_CI'):
                source.run(bind=True)
        after = path.read_bytes() if path.exists() else None
        self.assertEqual(before, after)


if __name__ == '__main__':
    main(verbosity=2)
