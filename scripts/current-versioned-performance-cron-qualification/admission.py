"""Exact full Native36 and retained actual finance execution before new runtime."""
from pathlib import Path
from hashlib import sha256
import json,os,subprocess


def admitted(repo,here,ids,product,native):
    config=json.loads((here/'CONFIG.json').read_bytes())
    predecessor=native.admitted();assert predecessor['current_installation']==product.sources()
    pins=json.loads((here/'SOURCE.json').read_bytes())
    assert pins['contract']==config['contract']and pins['case_ids']==list(ids)
    assert len(ids)==len(set(ids))==config['count']
    for path,digest in pins['files'].items():assert sha256((repo/path).read_bytes()).hexdigest()==digest,('CURRENT_VERSIONED_FINANCE_SOURCE_CHANGED',path)
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--',str(here)],text=True).strip()
    olddir=repo/('scripts/current-model-target-'+config['kind']+'-qualification')
    original=olddir/config['helper']
    assert(here/config['helper']).read_text()==original.read_text().replace('import cp7_current_model_target_installation','import cp7_current_versioned_performance_installation')
    if config['kind']=='finance':assert(here/'utc_snapshot.py').read_bytes()==(olddir/'utc_snapshot.py').read_bytes()
    proofs=pins['actual_qualification_originals'];assert set(proofs)=={config['native_variable'],config['old_variable']}
    originals={}
    for variable,proof in proofs.items():
        raw=Path(os.environ[variable]).read_bytes()
        assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256']
        actual=json.loads(raw)
        assert actual['status']==proof['status']=='PASS'and actual['cp6_restored']and actual['advisor_gate']and actual['restore_raw_public_equal']
        assert(actual.get('qualification_commit')or actual.get('candidate_commit'))==proof['head']
        assert actual['production_go']is False and actual['independent_acceptance']is False
        if variable==config['native_variable']:
            assert actual['source_declaration']['current_installation']==product.sources()
            assert actual['source_declaration']['qualification']==predecessor['qualification']
            assert actual['native']['counts']=={'PASS':36}and actual['observed_case_count']==36
            assert actual['required_case_ids_pass']and actual['required_case_ids']==predecessor['qualification']['case_ids']
            assert actual['complete_preuse_removal']and actual['baseline_full22_all_rows_all_sequences_equal']and actual['baseline_advisors_equal']
            assert all(r['status']=='PASS'and r['full_boundary_restored']and r['public_schema_unchanged']for r in actual['native']['cases'].values())
        else:
            assert proof['head']==config['old_head']
            assert actual['source_declaration']['current_installation']==product.predecessor.predecessor.predecessor.predecessor.sources()
            path=str(original.relative_to(repo))
            assert actual['source_declaration']['qualification']['files'][path]==sha256(original.read_bytes()).hexdigest()
            assert actual['required_case_ids_pass']and actual['required_case_ids']==list(ids)and actual['observed_case_count']==config['count']
            assert actual['complete_preuse_removal']
            if config['kind']=='finance':
                assert actual['label']=='CP7_CURRENT_MODEL_TARGET_FINANCE10'
                groups=actual['transport_groups'];assert groups['finance_auth']['counts']=={'PASS':3}and groups['finance_races']['counts']=={'PASS':7}
                assert groups['finance_auth']['real_auth']and not groups['finance_auth']['jwt_signed_by_runtime']and not groups['finance_auth']['test_only_usage_grant']
                assert groups['finance_auth']['auth_counts']['restored']and not groups['finance_auth']['auth_cleanup_failures']
                assert all(g['status']=='RUN_COMPLETE'and g['database_remaining']==0 and not g['cleanup_failures']and not g['session_leaks']for g in groups.values())
                assert len(actual['full_capture_snapshot_observations'])==7
                assert all(o['all_fields_retained']==23 and o['session_timezone_restored']for o in actual['full_capture_snapshot_observations'])
            else:
                assert actual['label']=='CP7_CURRENT_MODEL_TARGET_CRON1'and actual['actual_cron_claim']
                assert actual['manual_steps']==0 and not actual['changed_schedule']
                assert actual['baseline_full22_all_rows_all_sequences_equal']and actual['baseline_advisors_equal']and actual['used_guard_refused_before_DDL']
                assert all(r['status']=='PASS'for r in actual['committed'].values())
        originals[variable]=dict(proof,observed_status='PASS')
    return dict(qualified_current_versioned_target=predecessor,current_installation=product.sources(),qualification=pins,
        actual_originals_verified=originals,only_retained_helper_product_import_changed=True,production_go=False,independent_acceptance=False)
