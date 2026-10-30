"""Minimal adjustment-journal source successor controls, Native0."""
from pathlib import Path
from hashlib import sha256
from unittest import TestCase,main
import json,gzip
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];RUNTIME=ROOT/'scripts/cp7_global_nonpo_native_graph_adapter'
EDGE="  union select 'JOURNAL',j.id,'ADJUSTMENT',j.source_id from erp.journal_entries j where j.source_type='MATERIAL_ADJUSTMENT'and j.source_id is not null\n"


class AdjustmentSource(TestCase):
    def test_exact_actual_602_native_source_uses_header_id_with_account_only_lines(self):
        source=json.loads((HERE/'retained/Actual602_material_adjustment_source.json').read_bytes());item=source['captured'];raw=item['definition'].encode()
        self.assertEqual(len(raw),2639);self.assertEqual(sha256(raw).hexdigest(),'de207556f98b3aac44dd51fb50669b57652768fbdf2ed26ff04b362864ff9faa')
        self.assertEqual(item['owner'],'postgres');self.assertTrue(item['before_and_after_exact_equal']);self.assertFalse(source['executed_in_this_qualification'])
        self.assertEqual(item['definition'].count("erp.post_journal('MATERIAL_ADJUSTMENT',h.id,"),2)
        self.assertNotIn('product_id',item['definition']);self.assertNotIn('po_id',item['definition'])

    def test_BC_facade_does_not_supply_universal_journal_link_and_no_header_pointer_in_retained_DDL(self):
        proof=json.loads((HERE/'ADJUSTMENT_JOURNAL_SOURCE_PROOF.json').read_bytes());part=proof['exact_BC_adjustment_facade']
        self.assertIn(part['definition'],(ROOT/part['source']).read_text());self.assertEqual(sha256(part['definition'].encode()).hexdigest(),part['sha256'])
        self.assertIn("bc_link_v1(p_document,'ADJUSTMENT',v_id)",part['definition']);self.assertNotIn("'JOURNAL'",part['definition'])
        self.assertNotIn('journal_entry_id',proof['exact_retained_header_DDL']['definition']);self.assertFalse(proof['header_journal_entry_id_present'])
        self.assertIsNone(proof['runtime_entry']);self.assertIsNone(proof['required_final_composition_parent']);self.assertFalse(proof['writer_or_phantom_lock_closed'])

    def test_exact_one_new_native_identity_edge_and_frozen_capture_no_runtime_or_calculation_change(self):
        old=(HERE/'retained/923_scope.sql').read_text();current=(RUNTIME/'scope.sql').read_text()
        self.assertEqual(current.count(EDGE),1);self.assertEqual(current.replace(EDGE,'',1),old)
        historical=json.loads((HERE/'retained/923_SOURCE.json').read_bytes())
        for name in ['capture.sql','inspect.sql','authority.sql']:
            self.assertEqual(sha256((RUNTIME/name).read_bytes()).hexdigest(),historical['files']['scripts/cp7_global_nonpo_native_graph_adapter/'+name]['sha256'])
        self.assertNotIn('erp.post_material_adjustment(', '\n'.join((RUNTIME/x).read_text()for x in ['scope.sql','capture.sql','inspect.sql','authority.sql']))

    def test_previous_oracles_and_first_failure_preserved_with_no_private_Git_read_route(self):
        historical=json.loads((HERE/'retained/923_SOURCE.json').read_bytes())
        for name in ['test_model.mjs','test_identity_closure.mjs','test_fixed_point.mjs','test_source.py','test_identity_source.py','retained/Native_authority.sql']:
            self.assertEqual(sha256((HERE/name).read_bytes()).hexdigest(),historical['files']['scripts/current-global-nonpo-native-graph-qualification/'+name]['sha256'])
        first=json.loads(gzip.decompress((HERE/'evidence/ADJUSTMENT_FIRST_923_REPRO.json.gz').read_bytes()))
        self.assertEqual(first['status'],'CONFIRMED_923_OMITTED_NATIVE_ADJUSTMENT_JOURNAL_IDENTITY');self.assertFalse(first['qualified_for_runtime'])
        self.assertEqual(first['direct_before'],first['direct_after']);self.assertEqual(first['direct_before_changed'],first['direct_after_changed'])
        for name in ['check.py','freeze.py']:
            text=(HERE/name).read_text();self.assertNotIn('923a9620',text);self.assertIn('cde78b2c',text)
        self.assertNotIn('subprocess',(HERE/'first_adjustment_repro.mjs').read_text())


if __name__=='__main__':main(verbosity=2)
