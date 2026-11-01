"""Read-only exact-copy derivation and closed-parent controls, no DB credit."""
import unittest
from . import copy_context as copy

class CopyPreparationControls(unittest.TestCase):
    def test_one_fixed_race_name_extension_recovers_every_original_authority_check(self):
        raw=(copy.ROOT/copy.ORIGINAL).read_bytes();text,proof=copy.derive(raw)
        self.assertEqual(text.replace(copy.AFTER,copy.BEFORE,1).encode(),raw)
        self.assertEqual(proof['exact_copy_name_extension_count'],1)
        self.assertTrue(proof['all_raw22_authority_checks_unchanged'])
        self.assertFalse(proof['product_or_schema_or_RPC_grants_added'])

    def test_changed_authority_source_refuses_instead_of_resealing(self):
        raw=(copy.ROOT/copy.ORIGINAL).read_bytes()
        with self.assertRaisesRegex(ValueError,'EXACT_ORIGINAL_COPY_AUTHORITY_SOURCE_REQUIRED'):
            copy.derive(raw.replace(b"assert changes==",b"assert False and changes==",1))

    def test_copy_scope_refuses_missing_parent_before_modes_or_database_access(self):
        with self.assertRaisesRegex(ValueError,'ACTUAL_FREE3_ROOT_INTAKE_PENDING'):
            with copy.scope(object(),{}):raise AssertionError('CLOSED_SCOPE_ENTERED')

if __name__=='__main__':unittest.main()
