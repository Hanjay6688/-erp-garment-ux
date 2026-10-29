"""Reversible qualification-only fixture controls; no SQL executed here."""
from pathlib import Path
import importlib.util
from hashlib import sha256
import gzip
import json
import unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def module():
    spec=importlib.util.spec_from_file_location('sku_local_supplement_derive',HERE/'derive.py')
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


class FixtureSourceControls(unittest.TestCase):
    def test_full_source_reconstructs_and_all_fifteen_IDs_and_money_assertions_remain(self):
        m=module();raw=(ROOT/m.ORIGINAL).read_bytes();derived,proof=m.derive(raw)
        for before,after in reversed(m.REPLACEMENTS):
            self.assertEqual(derived.decode().count(after),1)
            derived=derived.replace(after.encode(),before.encode(),1)
        self.assertEqual(derived,raw)
        self.assertEqual(len(proof['same15_test_IDs']),15)
        self.assertEqual(proof['original_assertion_lines'],66)
        self.assertTrue(proof['all_original_assertions_preserved'])
        self.assertTrue(proof['unchanged_other14_test_bodies'])

    def test_source_mutation_refuses_instead_of_resealing_expectations(self):
        m=module()
        with self.assertRaisesRegex(ValueError,'EXACT_ORIGINAL15_REQUIRED'):
            m.derive((ROOT/m.ORIGINAL).read_bytes()+b'\n')

    def test_dependencies_are_typed_and_downstream_uses_real_movement_predicate(self):
        deps=(HERE/'fixture_dependencies.sql').read_text();derived=(ROOT/module().DERIVED).read_text()
        for table in ('be_conversion_sources_v1','be_conversion_cost_sources_v1','be_conversion_returns_v1',
                      'bc_documents_v1','bc_return_lots_v1','product_conversion_allocations','journal_entries'):
            self.assertIn('create table erp.'+table,deps)
        for fragment in ('original_hpp_per_pcs numeric(18,6)','conversion_cost_allocated numeric(20,2)',
                         'source_revision text not null','source_type character varying(50)','status text not null'):
            self.assertIn(fragment,deps)
        self.assertIn("source_type='PRODUCT_CONVERSION'",derived)
        self.assertIn("values(p_id,source_id,'FG'",derived)
        self.assertIn("'GRADE_A','SALE',-1",derived)
        self.assertNotIn(".rejects.toThrow('DOWNSTREAM_ACTIVE')",derived)
        native=(HERE/'native_downstream.sql').read_text()
        self.assertIn('fm.source_type=p_origin_source_type',native)
        self.assertIn('rv.reversal_of_id=fm.id',native)

    def test_config_preserves_original_build_secret_preflight_and_only_adds_owned_testpath(self):
        text=(HERE/'vitest.config.ts').read_text()
        self.assertIn("import original from '../../../vite.config.ts'",text)
        self.assertIn('mergeConfig(',text)
        self.assertIn('sku-pair-conversion.derived.test.ts',text)
        self.assertNotIn('exclude:',text)

    def test_exact_native_downstream_definition_comes_from_retained_original_catalogue(self):
        catalogue=json.loads(gzip.decompress((ROOT/'docs/cp7/evidence/p00/CP7_P00_CATALOGUE.json.gz').read_bytes()))
        rows=[r for r in catalogue['functions']if r['schema']=='erp'and r['name']=='fg_lot_has_active_downstream']
        self.assertEqual(len(rows),1)
        raw=(HERE/'native_downstream.sql').read_bytes()
        self.assertEqual(raw,rows[0]['definition'].encode())
        self.assertEqual(sha256(raw).hexdigest(),'f65dc3f4888809d0566095f7d5c7a59a6103cfa83f688aef679845d6fba85045')


if __name__=='__main__':unittest.main()
