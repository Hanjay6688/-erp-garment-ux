"""Bind full Native36 plus actual old policy/model and new versioned browser evidence."""
from pathlib import Path
from hashlib import sha256
import json,os,subprocess
VARS={'CURRENT_VERSIONED_PERFORMANCE_NATIVE_ORIGINAL_REPORT','CURRENT_MODEL_TARGET_BROWSER_ORIGINAL_REPORT','B_PERFORMANCE_BROWSER_ORIGINAL_REPORT'}


def admitted(repo,here,ids,product,native,groups):
    parent=native.admitted();assert parent['current_installation']==product.sources()
    pins=json.loads((here/'SOURCE.json').read_bytes())
    assert pins['contract']=='cp7.current-versioned-performance-browser6-qualification.v1'
    assert pins['case_ids']==list(ids)and len(ids)==len(set(ids))==6
    for path,digest in pins['files'].items():assert sha256((repo/path).read_bytes()).hexdigest()==digest,('CURRENT_VERSIONED_BROWSER_SOURCE_CHANGED',path)
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--',str(here)],text=True).strip()
    modules={'policy':'cp7_ow11_model_policy_browser.mjs','evaluation':'cp7_ow11_model_evaluation_v2_browser.mjs','target':'cp7_ow11_model_target_v2_browser.mjs'}
    for group,name in modules.items():assert(here/(group+'.mjs')).read_text()=="export { cases } from '../"+name+"'\n"
    proofs=pins['actual_qualification_originals'];assert set(proofs)==VARS
    B_root=Path(os.environ['B_PERFORMANCE_FROZEN_SOURCE_ROOT']).resolve()
    originals={}
    for variable,proof in proofs.items():
        raw=Path(os.environ[variable]).read_bytes();assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256']
        actual=json.loads(raw)
        assert actual['status']==proof['status']=='PASS'and actual['cp6_restored']and actual['advisor_gate']
        assert actual['production_go']is False and actual['independent_acceptance']is False
        if variable=='CURRENT_VERSIONED_PERFORMANCE_NATIVE_ORIGINAL_REPORT':
            assert actual['qualification_commit']==proof['head']
            assert actual['source_declaration']['qualification']==parent['qualification']and actual['source_declaration']['current_installation']==product.sources()
            assert actual['native']['counts']=={'PASS':36}and actual['observed_case_count']==36 and actual['required_case_ids_pass']
            assert actual['required_case_ids']==parent['qualification']['case_ids']and actual['complete_preuse_removal']
            assert actual['baseline_full22_all_rows_all_sequences_equal']and actual['baseline_advisors_equal']and actual['restore_raw_public_equal']
            assert all(r['status']=='PASS'and r['full_boundary_restored']and r['public_schema_unchanged']for r in actual['native']['cases'].values())
        else:
            if variable=='CURRENT_MODEL_TARGET_BROWSER_ORIGINAL_REPORT':
                assert actual['candidate_commit']==proof['head']=='f88c4ee99fb5d18cf11caada5fab86ad161b007a'
                assert actual['label']=='CP7_CURRENT_MODEL_TARGET_BROWSER6'
                assert actual['source_declaration']['current_installation']==product.predecessor.predecessor.predecessor.predecessor.sources()
                assert actual['required_case_ids_pass']and actual['observed_case_count']==6 and actual['complete_preuse_removal']and actual['restore_raw_public_equal']
                for group in('policy','evaluation'):
                    assert set(actual['browser_groups'][group]['cases'])==set(groups[group])
                    path='scripts/'+modules[group]
                    assert actual['source_declaration']['qualification']['files'][path]==sha256((repo/path).read_bytes()).hexdigest()
                observed=actual['browser_groups'].values()
            else:
                assert proof==parent['qualification']['actual_qualification_originals'][variable]
                assert actual['required_case_ids']['browser']==groups['target']and actual['observed_case_count']==2
                assert actual['required_case_ids_pass']and actual['required_case_counts_pass']and all(actual['restore_components'].values())
                found=0
                for name,values in actual.items():
                    if name.endswith('source_sha256')and isinstance(values,dict):
                        found+=1
                        for path,digest in values.items():
                            path=path if path.startswith(('scripts/','src/'))else'scripts/'+path
                            assert sha256((B_root/path).read_bytes()).hexdigest()==digest,path
                assert found
                for path in ['scripts/cp7_ow11_model_target_v2_browser.mjs','scripts/cp7_ow11_model_target_v2_browser_cases.py']:
                    assert(repo/path).read_bytes()==(B_root/path).read_bytes(),path
                observed=[actual['browser']]
            for b in observed:
                assert b['counts']=={'PASS':2}and all(r['status']=='PASS'for r in b['cases'].values())
                assert b['host_status']=='RUN_COMPLETE'and b['host_exit']==0 and b['console_errors']==0
                assert b['real_auth']and not b['jwt_signed_by_runtime']and not b['test_only_usage_grant']
                assert b['auth_counts']['restored']and not b['auth_cleanup_failures']
                assert b['database_remaining']==0 and not b['cleanup_failures']and not b['session_leaks']
        originals[variable]=dict(proof,observed_status='PASS')
    return dict(qualified_current_versioned_target=parent,current_installation=product.sources(),qualification=pins,actual_originals_verified=originals,
        retained_policy_model_cases=4,exact_B_versioned_target_cases=2,unchanged_browser_business_bodies=True,production_go=False,independent_acceptance=False)
