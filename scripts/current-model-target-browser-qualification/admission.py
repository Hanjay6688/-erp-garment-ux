"""Admit full Native20 and all three unchanged B browser2 prerequisites."""
from pathlib import Path
from hashlib import sha256
import json,os,subprocess,sys


def admitted(repo,here,ids,product,native,groups):
    predecessor=native.admitted()
    assert predecessor['current_installation']==product.sources()
    pins=json.loads((here/'SOURCE.json').read_bytes())
    assert pins['case_ids']==list(ids)and len(ids)==len(set(ids))==6
    for path,digest in pins['files'].items():
        assert sha256((repo/path).read_bytes()).hexdigest()==digest,('CURRENT_MODEL_TARGET_BROWSER_SOURCE_CHANGED',path)
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--',str(here)],text=True).strip()
    binding=helper_binding(repo,here)
    originals={}
    for variable,proof in pins['actual_qualification_originals'].items():
        raw=Path(os.environ[variable]).read_bytes()
        assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256'],variable
        actual=json.loads(raw)
        assert actual['status']=='PASS'and actual['cp6_restored']and actual['advisor_gate'],variable
        if variable=='CURRENT_MODEL_TARGET_ORIGINAL_REPORT':
            assert actual['source_declaration']['current_installation']==product.sources()
            assert actual['native']['counts']=={'PASS':20}and actual['observed_case_count']==20
            assert actual['required_case_ids_pass']and actual['required_case_ids']==predecessor['qualification']['case_ids']
            assert actual['baseline_full22_all_rows_all_sequences_equal']and actual['baseline_advisors_equal']
        elif variable in('MODEL_POLICY_BROWSER_ORIGINAL_REPORT','MODEL_V2_BROWSER_ORIGINAL_REPORT'):
            assert actual['required_case_ids_pass']and actual['required_case_counts_pass']and actual['observed_case_count']==2
            group='policy'if variable=='MODEL_POLICY_BROWSER_ORIGINAL_REPORT'else'evaluation'
            assert actual['required_case_ids']['browser']==groups[group]and actual['browser']['counts']=={'PASS':2}
            assert actual['model_policy_source_sha256']==product.predecessor.policy.verify_sources()
            if group=='evaluation':assert actual['model_evaluation_v2_source_sha256']==product.predecessor.evaluation.verify_sources()
        elif variable=='MODEL_TARGET_BROWSER_ORIGINAL_REPORT':
            assert actual['required_case_ids_pass']and actual['required_case_counts_pass']and actual['observed_case_count']==2
            assert actual['required_case_ids']['browser']==groups['target']and actual['browser']['counts']=={'PASS':2}
            assert actual['model_target_source_sha256']==product.target.verify_sources()
            assert actual['browser']['copy_runtime']['model_target']['existing_replacements']==19
            assert actual['browser']['copy_runtime']['model_target']['new_private_functions']==8
        else:raise ValueError('CURRENT_MODEL_TARGET_BROWSER_UNDECLARED_ORIGINAL: '+variable)
        originals[variable]=dict(proof,observed_status='PASS')
    assert set(originals)=={'CURRENT_MODEL_TARGET_ORIGINAL_REPORT','MODEL_POLICY_BROWSER_ORIGINAL_REPORT','MODEL_V2_BROWSER_ORIGINAL_REPORT','MODEL_TARGET_BROWSER_ORIGINAL_REPORT'}
    loaded=[]
    for name,module in tuple(sys.modules.items()):
        if name.startswith(('cp6_','cp7_sales_'))and getattr(module,'__file__',None):
            path=Path(module.__file__);assert sha256(path.read_bytes()).hexdigest()==pins['files']['scripts/'+path.name]
            loaded.append(name)
    return dict(qualified_current_model_target=predecessor,current_installation=product.sources(),
        qualification=pins,actual_originals_verified=originals,actual_loaded_modules_verified=loaded,
        original_B_case_bodies_and_fixtures_unchanged=True,helper_binding=binding)


def helper_binding(repo,here):
    original=(repo/'scripts/cp7_ow11_model_target_browser.mjs').read_text()
    needle="from './cp7_ow11_analog_browser.mjs'"
    assert original.count(needle)==1
    assert(here/'target.mjs').read_text()==original.replace(needle,"from './analog-helpers.mjs'",1)
    shared=(repo/'scripts/cp7_ow11_analog_browser.mjs').read_text()
    body=shared[shared.index('async function quantity('):shared.index('async function journey(')]
    body=body.replace('async function quantity(','export async function quantity(',1).replace('async function open(','export async function open(',1)
    expected="import assert from 'node:assert/strict'\nimport {openCuttingMenu} from '../cp7_ow13c_checked_browser.mjs'\nconst RPC='erp_cp7_read_product_analog_candidates_v1'\n"+body
    assert(here/'analog-helpers.mjs').read_text()==expected
    for group,module in [('policy','cp7_ow11_model_policy_browser.mjs'),('evaluation','cp7_ow11_model_evaluation_v2_browser.mjs')]:
        assert(here/(group+'.mjs')).read_text()=="export { cases } from '../"+module+"'\n"
    return dict(target_original_sha256=sha256(original.encode()).hexdigest(),
        target_only_import_path_changed=True,three_helper_bodies_byte_exact=True,
        helper_sha256=sha256(expected.encode()).hexdigest(),original_assertions_unchanged=True)
