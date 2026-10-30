"""Controls exercise the complete captured classifier; no DB/runtime credit."""
from copy import deepcopy
from pathlib import Path
import importlib.util
import os
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('root_context_types', HERE / 'context_types.py')
c = importlib.util.module_from_spec(spec); spec.loader.exec_module(c)


class ContextTypeControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(os.environ['GLOBAL_CENSUS_SOURCE_ROOT'])
        cls.source = (root / 'scripts/current-global-actual-writer-census-qualification/census.py').read_text()
        cls.old = staticmethod(c.classifier(cls.source, corrected=False))
        cls.new = staticmethod(c.classifier(cls.source))

    def catalog(self, types, *, kind='r', persistence='p', partition=False):
        row = ['owner', kind, persistence, True, False, partition]
        return dict(relations={'model.context': row}, columns={
            'model.context:' + name: [name, i + 1, type_name] for i, (name, type_name) in enumerate(types)})

    def test_original_xid8_false_alarm_is_reproduced_and_only_type_issue_changes(self):
        catalog = self.catalog([('txid', 'xid8')]); old, new = self.old(catalog), self.new(catalog)
        self.assertEqual(old['model.context']['issues'], ['WRONG_TRANSACTION_TYPE'])
        self.assertEqual(new['model.context']['issues'], [])
        old['model.context']['issues'] = []
        self.assertEqual(old, new)
        self.assertEqual(new['model.context']['active_authority'], 'UNKNOWN')
        self.assertFalse(new['model.context']['ephemeral'])

    def test_bigint_metadata_and_behavior_remain_exact(self):
        catalog = self.catalog([('transaction_id', 'bigint')])
        self.assertEqual(self.old(catalog), self.new(catalog))

    def test_unsupported_and_32bit_transaction_types_remain_rejected(self):
        for type_name in ('xid', 'integer', 'text', 'numeric', 'public.xid8', ''):
            with self.subTest(type_name=type_name):
                result = self.new(self.catalog([('txid', type_name)]))
                self.assertIn('WRONG_TRANSACTION_TYPE', result['model.context']['issues'])

    def test_mixed_columns_cannot_hide_invalid_type_in_either_order(self):
        types = [('txid', 'text'), ('transaction_id', 'bigint')]
        for order in (types, list(reversed(types))):
            self.assertIn('WRONG_TRANSACTION_TYPE', self.new(self.catalog(order))['model.context']['issues'])

    def test_nonordinary_persistence_checks_remain(self):
        for settings in (dict(kind='p'), dict(persistence='u'), dict(partition=True)):
            result = self.new(self.catalog([('txid', 'xid8')], **settings))
            self.assertIn('NON_ORDINARY_PERSISTENT_TABLE', result['model.context']['issues'])

    def test_source_derivation_is_bounded_and_unknown_anchor_refuses(self):
        after, proof = c.derive(self.source)
        self.assertEqual(after.replace(c.AFTER, c.BEFORE, 1), self.source)
        self.assertEqual(proof['counted_changes'], 1)
        for source in (self.source + c.BEFORE, after, self.source.replace(c.BEFORE, '')):
            with self.assertRaises(ValueError): c.derive(source)

    def test_catalogue_input_is_not_mutated(self):
        catalog = self.catalog([('txid', 'xid8'), ('transaction_id', 'bigint')]); before = deepcopy(catalog)
        self.new(catalog); self.assertEqual(catalog, before)

    def test_unknown_empty_inventory_still_refuses(self):
        with self.assertRaisesRegex(ValueError, 'CENSUS_UNKNOWN_EMPTY_CONTEXT_INVENTORY'):
            self.new(dict(relations={}, columns={}))


if __name__ == '__main__':
    unittest.main(verbosity=2)
