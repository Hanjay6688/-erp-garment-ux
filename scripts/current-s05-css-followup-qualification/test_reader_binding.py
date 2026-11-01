"""Reproduce the actual stale reader pin before DB; no ERP case credit."""
from pathlib import Path
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import patch
import importlib.util,json,socket,subprocess,tempfile,unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def binding():return load('reader_binding_control',HERE/'reader_binding.py')
def original(module):return subprocess.check_output(['git','-C',str(ROOT),'show',module.BASE+':'+module.PATH])

class CurrentReaderBindingControls(unittest.TestCase):
    def test_original_actual_reader_sources_reproduces_failure_then_checks_all41_after_exact_pin_change(self):
        module=binding();raw=original(module);derived,proof=module.derive(raw)
        reader=load('unmodified_actual_S05_reader_guard',ROOT/'scripts/cp7_s05_s03_sku_composition/stage.py')
        parent=SimpleNamespace(sources=lambda:dict(synthetic_parent_not_ERP_qualification=True))
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder);(root/'SOURCE.json').write_bytes(raw)
            # Only the pure parent's source return is simulated; execute the
            # ORIGINAL reader.sources(), including every actual file digest.
            with patch.object(reader,'HERE',root),patch.object(reader,'parent',return_value=parent),\
                    patch.object(socket,'create_connection',side_effect=AssertionError('NETWORK_FORBIDDEN')):
                with self.assertRaisesRegex(ValueError,'S05_SOURCE_CHANGED: src/accessory-standard-report.css'):
                    reader.sources()
                (root/'SOURCE.json').write_bytes(derived)
                actual=reader.sources()
        self.assertEqual(actual['stage'],json.loads(derived));self.assertTrue(proof['complete_original_recovered'])
        self.assertEqual(proof['other_reader_source_pins_unchanged'],40)

    def test_only_current_CSS_digest_changes_and_historical_contract_metadata_stays_exact(self):
        module=binding();raw=original(module);derived,proof=module.derive(raw)
        before=json.loads(raw);after=json.loads(derived)
        self.assertEqual([k for k in before['files']if before['files'][k]!=after['files'][k]],[module.CSS])
        self.assertEqual({k:v for k,v in before.items()if k!='files'},{k:v for k,v in after.items()if k!='files'})
        self.assertEqual(len(raw),len(derived));self.assertFalse(proof['historical_manifests_changed'])
        self.assertEqual(module.preflight()['actual_reader_inputs_checked'],41)

    def test_foreign_original_or_changed_report_SQL_cannot_be_rebound(self):
        module=binding();raw=original(module)
        with self.assertRaisesRegex(ValueError,'EXACT_ORIGINAL'):module.derive(raw+b'\n')
        derived,_=module.derive(raw)
        def read(name):
            actual=(ROOT/name).read_bytes()
            return actual+b'-- forbidden SQL change\n'if name=='scripts/cp7_accessory_standard_report/report.sql'else actual
        with self.assertRaisesRegex(ValueError,'S05_SOURCE_CHANGED: scripts/cp7_accessory_standard_report/report.sql'):
            module.check_files(derived,read)

    def test_admission_rejects_the_actual_old_reader_guard_before_runtime_then_admits_derived_reader(self):
        module=binding();reader=load('actual_reader_at_admission_control',ROOT/'scripts/cp7_s05_s03_sku_composition/stage.py')
        admission=load('actual_admission_with_synthetic_parent_only',HERE/'admission.py')
        financial={'synthetic_financial_parent_not_ERP_acceptance':True}
        parent=SimpleNamespace(admitted=lambda:dict(current_installation=financial),import_scope=nullcontext)
        proof=dict(receipt=dict(qualified_financial_sources=admission.json_pin(financial)),synthetic_control=True)
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder);raw=original(module);(root/'SOURCE.json').write_bytes(raw)
            with patch.object(reader,'HERE',root),patch.object(reader,'parent',return_value=SimpleNamespace(sources=lambda:financial)),\
                    patch.object(admission,'retained',return_value=proof),patch.object(admission,'parent_admission',return_value=parent),\
                    patch.object(admission.importlib,'import_module',return_value=reader),\
                    patch.object(socket,'create_connection',side_effect=AssertionError('NETWORK_FORBIDDEN')):
                with self.assertRaisesRegex(ValueError,'S05_SOURCE_CHANGED: src/accessory-standard-report.css'):admission.admitted()
                (root/'SOURCE.json').write_bytes(module.derive(raw)[0]);actual=admission.admitted()
        self.assertTrue(actual['current_reader_graph_checked_before_database'])
        self.assertEqual(actual['current_reader_installation']['parent'],financial)

    def test_final_gate_refuses_missing_reader_graph_wrong_parent_or_old_CSS_pin(self):
        tests=load('focused_existing_gate_fixture_for_reader_control',HERE/'test_followup.py')
        for mutation in('missing','flag','parent','old_css'):
            gate,p,*values=tests.fixture();declaration=values[0]['source_declaration']
            if mutation=='missing':declaration.pop('current_reader_installation')
            elif mutation=='flag':declaration['current_reader_graph_checked_before_database']=False
            elif mutation=='parent':declaration['current_reader_installation']['parent']={'foreign':True}
            else:declaration['current_reader_installation']['stage']=json.loads(original(binding()))
            with self.subTest(mutation=mutation),self.assertRaises((KeyError,ValueError)):gate.validate(*values,p)

if __name__=='__main__':unittest.main()
