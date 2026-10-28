from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import importlib.util,json,os,shutil,unittest
import admission,composition,source_guard,workflow_guard
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
class Browser3194Boundaries(unittest.TestCase):
    def test_closed_or_wrong_acceptance_refuses_before_backend(self):
        for cfg in ({},{'allow_database_execution':True},{'allow_database_execution':False,'backend_acceptance':'six-retained-one-fresh-3194'},{'allow_database_execution':True,'backend_acceptance':'seven-fresh'}):
            with self.subTest(cfg=cfg),self.assertRaisesRegex(ValueError,'ACTUAL_COMBINED_RUNTIME_REQUIRED'):composition.gate(cfg)
    def test_all_runtime_interfaces_stay_closed_without_binding(self):
        class NoDatabase:
            def __getattr__(self,name):raise AssertionError('DATABASE_TOUCHED')
        with TemporaryDirectory()as name:
            folder=Path(name);(folder/'CONFIG.json').write_text('{}')
            with patch.object(composition,'HERE',folder),patch.object(composition,'parent',side_effect=AssertionError('BACKEND_TOUCHED')):
                for call in (lambda:composition.install(NoDatabase()),lambda:composition.verify(NoDatabase(),{}),lambda:composition.rollback_preuse(NoDatabase(),{}),composition.sources,lambda:getattr(composition,'catalog')):
                    with self.assertRaisesRegex(ValueError,'ACTUAL_COMBINED_RUNTIME_REQUIRED'):call()
    def test_admission_stays_closed_before_source_or_db(self):
        with TemporaryDirectory()as name:
            folder=Path(name);(folder/'CONFIG.json').write_text('{}');shutil.copy2(HERE/'composition.py',folder/'composition.py')
            with self.assertRaisesRegex(ValueError,'ACTUAL_COMBINED_RUNTIME_REQUIRED'):admission.admitted(ROOT,folder,(),None,None,{})
    def test_current_frontend_cannot_impersonate_frozen_backend(self):
        with patch.dict(os.environ,D17_18_SELECTED_BACKEND_ROOT=str(ROOT)),self.assertRaisesRegex(AssertionError,'SEPARATE_FROZEN_BACKEND_REQUIRED'):composition.backend_root()
    def test_original_host_and_declared_successors_are_exact(self):
        result=source_guard.check(ROOT,HERE)
        self.assertEqual(result['host_exact_files'],113);self.assertEqual(result['current_B_exact_files'],91)
        self.assertFalse(result['historical_manifests_rewritten'])
    def test_original_lost_reply_oracle_cannot_be_removed(self):
        changed=(HERE/'browser.mjs').read_text().replace("route.abort('failed')","route.continue()",1)
        with self.assertRaisesRegex(AssertionError,'UNDECLARED_ORACLE_CHANGE'):source_guard.check(ROOT,HERE,overrides={'browser.mjs':changed})
    def test_browser_runtime_cannot_be_skipped(self):
        value=workflow_guard.expected(ROOT,HERE)
        runtime=[s for s in value['jobs']['p21']['steps']if s.get('name')=='Run real Auth desktop and mobile on exact qualified combined backend'];self.assertEqual(len(runtime),1);runtime[0]['run']='true'
        with self.assertRaisesRegex(AssertionError,'UNDECLARED_WORKFLOW_CHANGE'):workflow_guard.check(ROOT,HERE,actual=value)
    def test_backend_checkout_cannot_follow_moving_frontend(self):
        value=workflow_guard.expected(ROOT,HERE);value['jobs']['p21']['steps'][0]['with'].pop('ref')
        with self.assertRaisesRegex(AssertionError,'UNDECLARED_WORKFLOW_CHANGE'):workflow_guard.check(ROOT,HERE,actual=value)
    def test_fetch_stays_closed_before_network(self):
        fetch=admission.load('B_closed_3194_fetch',HERE/'fetch_combined.py')
        with TemporaryDirectory()as name:
            folder=Path(name);(folder/'CONFIG.json').write_text('{}')
            with patch.object(fetch,'HERE',folder),patch.object(fetch.subprocess,'check_output',side_effect=AssertionError('NETWORK_TOUCHED')),self.assertRaisesRegex(ValueError,'ACTUAL_COMBINED_RUNTIME_REQUIRED'):fetch.fetch()
if __name__=='__main__':unittest.main()
