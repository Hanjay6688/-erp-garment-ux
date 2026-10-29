"""Read-only evidence, scope and independent Decimal controls, never Native."""
from pathlib import Path
from hashlib import sha256
from decimal import Decimal as D
import ast
import importlib.util
import json
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('d1_product_cap_file_checks', HERE / 'source_check.py')
checks = importlib.util.module_from_spec(spec); spec.loader.exec_module(checks)


class SourceControls(unittest.TestCase):
    def test_only_quote_changed_other_thirteen_bodies_eight_leaves_and_original_qualifier_exact(self):
        result = checks.admitted()
        self.assertEqual(result['scope']['other_owning_function_bodies_byte_exact'], 13)
        self.assertEqual(result['other_business_leaves_byte_exact'], 8)
        self.assertFalse(result['Native_execution'])

    def test_other_owning_body_change_fails_scope_even_with_valid_quote(self):
        before = (HERE / 'retained/owning.before.sql').read_text()
        current = (ROOT / checks.OWNING).read_text()
        bad = current.replace('create function cp7_credit_correction_de.has_source_v1',
                              'create function cp7_credit_correction_de.unallocated_change_v1', 1)
        with self.assertRaisesRegex(ValueError, 'OTHER_OWNING_BODY_CHANGED'):
            checks.quote_scope(before, bad)

    def test_first_actual_sql_reproduction_retained_as_ready_plus_strict_native_refusal(self):
        value = json.loads((HERE / 'evidence/FIRST_QUOTE_READY_NATIVE_REFUSAL.json').read_bytes())
        self.assertEqual(value['status'], 'CONFIRMED_LOCAL_QUOTE_READY_NATIVE_AGGREGATE_REFUSAL')
        self.assertEqual(value['reviewed']['state'], 'READY')
        self.assertEqual(value['reviewed']['issues'], [])
        self.assertEqual(value['refusal']['sqlstate'], 'P0001')
        self.assertIn('Refund exceeds original net sale value for product.', value['refusal']['message'])
        self.assertEqual(D(value['math']['peerPOSTED']) + D(value['math']['replacement']), D('1000.01'))
        self.assertLessEqual(D(value['math']['replacement']), D(value['math']['perLineMax']) + D('.01'))
        self.assertFalse(value['Native_financial_execution'])

    def test_native_post_and_normalizer_sources_are_exact_and_their_caps_differ(self):
        post = (HERE / 'retained/post_sales_return.sql').read_bytes()
        normalizer = (HERE / 'retained/normalizer.sql').read_bytes()
        self.assertEqual(len(post), 12167)
        self.assertEqual(sha256(post).hexdigest(), '5f974ad9b9fff9ec9fef3018153683d35b79a9a5e8bd4c60e9a4a17b97622cdc')
        self.assertEqual(sha256(normalizer).hexdigest(), '1ca83d0e1728833c1fff2d3a285b142f8b1064e85afd3560573f885fedfd92bc')
        self.assertIn(b'if v_prior_product_refund+v_current_product_refund>v_product_sale_value then', post)
        self.assertIn(b"sr.id<>h.id and sr.status='POSTED' and sri.product_id=r.product_id", post)
        self.assertIn(b'v_max_refund+0.01', normalizer)

    def test_original_thirteen_ids_and_all_financial_callback_bytes_survive(self):
        source = json.loads((HERE / 'PARENT.json').read_bytes())
        path = 'scripts/cp7_credit_correction_de/cases.py'
        self.assertEqual(sha256((ROOT / path).read_bytes()).hexdigest(), source['frozen_callback_sha256'])
        tree = ast.parse((ROOT / path).read_text())
        ids = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == 'IDS' for t in n.targets))
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), 13)
        self.assertEqual(list(ids), source['original_Native13_ids'])

    def test_final_directed_sql_evidence_and_exact_decimal_boundary(self):
        result = json.loads((HERE / 'evidence/DIRECTED_FINAL34_PASS.json').read_bytes())
        self.assertEqual(result['status'], 'PASS_LOCAL_SQL_ONLY')
        self.assertEqual(result['tests'], 34)
        by_name = {c['name']: c for c in result['checks']}
        self.assertEqual(len(by_name), 34)
        over = by_name['posted peer + replacement exceeds product by .01']
        equal = by_name['posted peer exact product equality400 allowed; excludes old200']
        self.assertGreater(D('600.00') + D('400.01'), D('1000.00'))
        self.assertEqual(D('600.00') + D('400.00'), D('1000.00'))
        self.assertTrue(over['unchanged_Native_predicate']['aggregate_refused'])
        self.assertEqual(over['quote']['state'], 'REFUSE')
        self.assertTrue(equal['unchanged_Native_predicate']['passed_guard_stopped_before_stock'])
        self.assertEqual(equal['quote']['state'], 'READY')
        self.assertFalse(result['Native_financial_execution'])
        self.assertEqual(result['actual_Native_cases'], 0)
        self.assertFalse(result['stock_or_journal_writer_called'])

    def test_peer_stale_token_and_malformed_inputs_never_claim_ready(self):
        value = json.loads((HERE / 'evidence/DIRECTED_FINAL34_PASS.json').read_bytes())
        stale = next(c for c in value['checks'] if c['name'].startswith('local peer change'))
        self.assertEqual(stale['before']['state'], 'READY')
        self.assertEqual(stale['after']['state'], 'REFUSE')
        self.assertNotEqual(stale['before']['review_token'], stale['after']['review_token'])
        malformed = [c for c in value['checks'] if c.get('malformed_source_double')]
        self.assertEqual(len(malformed), 21)
        for case in malformed:
            self.assertEqual(case['quote']['state'], 'REFUSE')
            self.assertIn('REFUND_CAP_SOURCE_UNAVAILABLE', case['quote']['issues'])


if __name__ == '__main__':
    unittest.main()
