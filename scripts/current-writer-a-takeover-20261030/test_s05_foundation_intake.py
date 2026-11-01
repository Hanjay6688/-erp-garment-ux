"""Independent Root checks of setup evidence shape; no ERP runtime/test credit."""
from copy import deepcopy
from pathlib import Path
import importlib.util,os,unittest
import intake_s05_focused as root

SOURCE=Path(os.environ.get('S05_FOCUSED_SOURCE',str(Path(__file__).resolve().parents[2].parent/'erp-s05-focused')))

def sample():
    # Reuse only the explicitly synthetic gate-data factory, never product code.
    path=SOURCE/root.NS/'test_followup.py'
    spec=importlib.util.spec_from_file_location('root_synthetic_followup_data_only',path)
    data=importlib.util.module_from_spec(spec);spec.loader.exec_module(data)
    _,_,main,*_=data.fixture();part=main['committed'][root.CASE]
    return main,part,deepcopy(part['fixture_foundation']['source'])

@unittest.skipUnless((SOURCE/root.NS/'test_followup.py').is_file(),'exact scoped source checkout is not provided')
class RootFoundationControls(unittest.TestCase):
    def test_source_matches_published_git_and_candidate_retained_proof_exactly(self):
        with root.GitBytes(SOURCE,root.HEAD,root.TREE)as g:expected=root.source(g)
        spec=importlib.util.spec_from_file_location('root_candidate_retained_read_only',SOURCE/root.NS/'admission.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        self.assertEqual(expected['expected_runtime_retention'],module.retained())
        self.assertEqual(len(expected['foundation_setup_source']['files']),7)
        self.assertEqual(expected['actual_case_credit'],0)

    def test_synthetic_complete_setup_requires_all22_and_full_role_data(self):
        main,part,source=sample();value=root.check_foundation(main,part,source)
        self.assertTrue(value['setup_has_no_Native_case_credit'])
        self.assertTrue(value['all22_catalog_and_protected_role_rows_unchanged'])

    def test_incomplete_source_role_catalog_or_false_credit_is_refused(self):
        for mutation in ('missing_material','users_only','bool','catalog','roles','source','seed_twice','credit'):
            main,part,source=sample();setup=part['fixture_foundation']
            if mutation=='missing_material':setup['final']['required']['erp.materials']=False
            elif mutation=='users_only':main['fixture_foundation_precheck']['initial']['app_users']=1
            elif mutation=='bool':setup['final']['app_users']=True
            elif mutation=='catalog':setup['actual_all22_after']['triggers']={'unrestored':[]}
            elif mutation=='roles':setup['protected_role_data_after']={}
            elif mutation=='source':setup['source']=dict(source,files={})
            elif mutation=='seed_twice':setup['seed_called']=False
            else:setup['Native_case_credit']=1
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):root.check_foundation(main,part,source)

if __name__=='__main__':unittest.main()
