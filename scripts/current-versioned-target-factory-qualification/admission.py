"""Require actual full Native36 and versioned minute cron; retain failed factory proof."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,os,subprocess


def guard(here):
    spec=importlib.util.spec_from_file_location('versioned_factory_source_guard',here/'source_guard.py')
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value.source_binding()


def admitted(repo,here,ids,product,native):
    c=json.loads((here/'CONFIG.json').read_bytes());bound=guard(here)
    predecessor=native.admitted();assert predecessor['current_installation']==product.sources()
    pins=json.loads((here/'SOURCE.json').read_bytes());assert pins['contract']==c['contract']and pins['case_ids']==list(ids)and len(ids)==1
    for path,digest in pins['files'].items():assert sha256((repo/path).read_bytes()).hexdigest()==digest,('VERSIONED_FACTORY_SOURCE_CHANGED',path)
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain'],text=True).strip()
    proofs=pins['actual_qualification_originals'];assert set(proofs)=={c['native_variable'],c['cron_variable'],c['first_failure_variable']}
    verified={}
    for variable,proof in proofs.items():
        raw=Path(os.environ[variable]).read_bytes();assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256']
        actual=json.loads(raw);assert(actual.get('qualification_commit')or actual.get('candidate_commit'))==proof['head']
        failed=variable==c['first_failure_variable'];assert actual['status']==proof['status']==('INCOMPLETE'if failed else'PASS')
        assert actual['cp6_restored']and actual['advisor_gate']and actual['baseline_full22_all_rows_all_sequences_equal']and actual['baseline_advisors_equal']
        assert actual['production_go']is actual['independent_acceptance']is False
        if failed:
            assert proof['head']==c['old_head']and actual['label']=='CP7_CURRENT_FACTORY_FINANCE1'
            old=actual['source_declaration']['qualification']['files']
            assert old['scripts/current-factory-finance-qualification/fixture.py']==c['fixture_sha256']
            assert old['scripts/current-factory-finance-qualification/runner.py']==c['runner_sha256']
        else:
            assert actual['source_declaration']['current_installation']==product.sources()and actual['required_case_ids_pass']
            if variable==c['native_variable']:
                assert actual['source_declaration']['qualification']==predecessor['qualification']
                assert actual['native']['counts']=={'PASS':36}and actual['observed_case_count']==36 and actual['complete_preuse_removal']
                assert actual['required_case_ids']==predecessor['qualification']['case_ids']
            else:
                assert actual['label']=='CP7_CURRENT_VERSIONED_TARGET_CRON1'and actual['observed_case_count']==1
                assert actual['actual_cron_claim']and actual['manual_steps']==0 and not actual['changed_schedule']
                assert actual['scheduler_quiet_before_baseline_restore']and actual['used_guard_refused_before_DDL']
                case=actual['committed']['CURRENT_FINANCE_MODEL_ACTUAL_MINUTE_CRON_BOUNDED_READY_AND_DEFERRED']
                assert case['status']=='PASS'and case['official_sections_and_metrics_exact']and case['independent_book_signature']and case['metric_count']==24
                assert case['unknown_never_zero']and case['unchanged_production_minute_schedule']
                assert actual['source_declaration']['qualification']==json.loads((repo/'scripts/current-versioned-target-cron-qualification/SOURCE.json').read_bytes())
        verified[variable]=dict(proof,observed_status=actual['status'])
    return dict(qualified_current_versioned_target=predecessor,current_installation=product.sources(),qualification=pins,actual_originals_verified=verified,retained_business_source=bound,synthetic_factory_scope=dict(commercial_skus=1200,sizes_per_sku=3,variants=3600),first_failure_preserved=True,independent_acceptance=False,production_go=False)
