"""Current fullsource first, bounded readers/ABI and complete unchanged engine."""
from pathlib import Path
from hashlib import sha256
from unittest import mock
import contextlib
import importlib.util
import io
import json
import unittest
import yaml

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def load(name,file):
    s=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


class Source(unittest.TestCase):
    def test_complete_public_source_and_current242_before_historical_intake(self):
        source=load('s05_final_source','source_check.py').check();self.assertGreater(source['public_files'],13000);self.assertEqual(source['historical_untracked_proofs'],24)
        proof=load('s05_final_admission','admission.py').offline();self.assertEqual(proof['historical_current_AC_source']['source_files'],242)
        self.assertEqual(len(proof['Native_case_ids']),10);self.assertIsNone(proof['accepted_fresh_native10']);self.assertEqual(proof['actual_Native_credit'],0)

    def test_current_source_refusal_precedes_any_private_historical_reader(self):
        m=load('s05_source_order','admission.py')
        with mock.patch.object(m,'load',return_value=type('Rejected',(),{'check':staticmethod(lambda **kw:(_ for _ in()).throw(ValueError('CURRENT_SOURCE_REFUSED')))})),mock.patch.object(m,'historical',side_effect=AssertionError('too early')):
            with self.assertRaisesRegex(ValueError,'CURRENT_SOURCE_REFUSED'):m.offline()

    def test_exact_reversible_two_source_scope_and_four_probe_transitions(self):
        d=load('s05_derivations','derive.py');old=ROOT/'scripts/current-s05-current-ac-editor-qualification'
        text,proof=d.admission((old/'admission.py').read_bytes());self.assertEqual(proof['counted_changes'],2);self.assertTrue(proof['reverse_original_bytes_exact']);compile(text,'<source-reader>','exec')
        text,proof=d.probe((old/'probe.py').read_bytes());self.assertEqual(proof['counted_changes'],4);self.assertTrue(proof['reverse_original_bytes_exact']);compile(text,'<private-probe>','exec')
        with self.assertRaisesRegex(ValueError,'EXACT_ANCHOR'):d.probe((old/'probe.py').read_bytes()+b'\n'+(old/'probe.py').read_bytes())

    def test_vendor_complete_six_substitutions_and_original_component_gate_witness_unchanged(self):
        p=ROOT/'scripts/current-s05-native10-qualification';spec=importlib.util.spec_from_file_location('s05_six_engine',p/'derive.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        raw=(p/'frozen_vendor/probe.py').read_bytes();text,proof=m.derive(raw);self.assertEqual(proof['counted_changes'],6)
        for before,after in reversed(m.REPLACEMENTS):self.assertEqual(text.count(after),1);text=text.replace(after,before,1)
        self.assertEqual(text.encode(),raw)
        component=(p/'component.py').read_text()
        for value in ('exact_group(actual, business.IDS)','connection.commit()',"report['separate_committed_business_witness'] = witness",'product.rollback_delta_preuse(cursor, state)',"actual_Native_cases=len(business.IDS)"):
            self.assertIn(value,component)

    def test_workflow_exact_original_steps_with_only_routing_and_pre_GET_addition(self):
        w=load('s05_workflow','workflow_source.py');expected,proof=w.derive((ROOT/w.PARENT).read_bytes());self.assertEqual(expected,(ROOT/w.PATH).read_text())
        old=yaml.safe_load((ROOT/w.PARENT).read_bytes());new=yaml.safe_load(expected);steps=new['jobs']['p21']['steps'];self.assertEqual(len(steps),65)
        self.assertEqual(new['on']['push']['branches'],[w.BRANCH]);self.assertIn('materialize.py',steps[3]['run']);self.assertIn('source_check.py',steps[4]['run'])
        for index in (4,5,6,55,56,57,58,59,61,62):
            if index in(55,61):continue
            self.assertEqual(old['jobs']['p21']['steps'][index],steps[index+1])
        self.assertEqual(steps[-1]['with']['path'],'auditor/cp6-proof/t3');self.assertEqual(steps[-1]['if'],'always()')

    def test_unknown_cli_flag_refuses_before_any_source_or_product_import(self):
        m=load('s05_unknown_cli','check.py')
        with mock.patch.object(m,'load',side_effect=AssertionError('too early')),contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit)as result:m.main(['--unknown'])
            self.assertEqual(result.exception.code,2)

    def test_generic_generated_helpers_byte_exact_independently_frozen(self):
        pins={'generated_receipts.py':'a569138a5b6d4c0d1ce542ab45af98ee156f47e6d772766c214bbae3366ffc7e','generated_later.py':'7bf35d85d9f7ec19da34c5626f24af908f3691a4e3ed7251dbc4958e59b4bea3'}
        for name,pin in pins.items():self.assertEqual(sha256((HERE/name).read_bytes()).hexdigest(),pin)


if __name__=='__main__':unittest.main()
