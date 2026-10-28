"""Writer B evidence verification; no database/browser run or independent audit."""
from pathlib import Path
from hashlib import sha256
from statistics import median
import json,zipfile,subprocess
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
CANDIDATE='f5e4a0eb98f52c7615c3f4fb2459128bc76ed007'
BACKEND='3194b9c56be7af86ee45ccb1c6605204a712f91b'
ZIP_SHA='33b27ed1e46bb5a335fb119be03b40fcf1e9c2a14e97697f11c799f4072a40c5'
def verify():
    packed=(HERE/'ORIGINAL_BROWSER_ARTIFACT.zip').read_bytes()
    assert len(packed)==4449681 and sha256(packed).hexdigest()==ZIP_SHA
    manifest=json.loads((HERE/'ORIGINAL_MEMBERS.json').read_bytes())
    with zipfile.ZipFile(HERE/'ORIGINAL_BROWSER_ARTIFACT.zip')as z:
        assert z.testzip()is None and len(z.namelist())==len(set(z.namelist()))
        assert set(z.namelist())=={m['name']for m in manifest}
        for m in manifest:
            raw=z.read(m['name']);assert len(raw)==m['bytes']and sha256(raw).hexdigest()==m['sha256'],m['name']
        d=json.loads(z.read('CP7_D17_18_COMBINED_FINANCE_UI_BROWSER2.json'))
        package=json.loads(z.read('T3_PACKAGE_INSTALL.json'))
        assert d['status']=='PASS'and d['candidate_commit']==CANDIDATE and d['backend_commit']==BACKEND
        assert d['expected_case_count']==d['observed_case_count']==2 and d['required_case_ids_pass']is True
        assert d['production_go']is d['independent_acceptance']is d['formal_CP7C_started']is False
        assert not d.get('error')and not d.get('restore_error')
        assert d['cp6_restored']is d['advisor_gate']is d['restore_raw_public_equal']is True
        assert d['complete_installed_verification']['status']=='EXACT_FACTORY_INITIAL_STAGE_ALL22'
        assert d['complete_preuse_removal']['status']=='EXACT_INITIAL_STAGE_PREUSE_INVERSE'
        assert package['gate']==dict(installed=True,primary_unchanged=True,backup_restore_drill=True,security_advisors=True,writer_runtime=True)
        assert len(d['copy_catalog_admissions'])==2
        for c in d['copy_catalog_admissions']:
            assert c['all22_groups_equal_original_install']is c['full22_after_must_equal_original_install']is True
            assert c['product_state_modified']is c['Native_or_schema_or_RPC_permissions_changed']is False
        source=d['source_declaration'];accepted=source['accepted_combined_runtime']
        assert accepted['status']=='PASS_BACKEND_COMPONENT_FOR_B_BINDING'and accepted['selected_backend_head']==BACKEND
        assert accepted['selected_backend_tree']=='dd98cd5bbbafb3f257668d22317ab4b237c2fea8'
        assert accepted['retained_groups']==6 and accepted['fresh_groups']==1 and accepted['seven_fresh_groups_claim']is False
        assert accepted['historical_11c_status']=='INCOMPLETE'
        actual=source['actual_selected_backend_declaration']['current_installation']
        assert source['current_installation']['combined_installation']==actual
        assert sha256(json.dumps(actual,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()=='193f4c18476a1e1abd5e05231d8d7755864b61e2998c4456f5a87459b17da59d'
        # This checks the runtime's recorded actual-source admission, not a new
        # admission by substituting an expected dictionary for product.sources().
        def candidate(path):return subprocess.check_output(['git','-C',str(REPO),'show',CANDIDATE+':'+path])
        cfg=json.loads(candidate('scripts/current-finance-combined-browser-qualification/CONFIG.json'))
        pins=json.loads(candidate('scripts/current-finance-combined-browser-qualification/SOURCE.json'))
        assert source['qualification']==pins
        for path,digest in pins['files'].items():assert sha256(candidate(path)).hexdigest()==digest,path
        graph=json.loads(candidate('scripts/current-finance-combined-browser-qualification/BUILD_SOURCE_3194.json'))
        expected_graph={f['path']:f['sha256']for f in graph['files']}
        assert len(expected_graph)==79 and set(d['browser_groups'])==set(cfg['groups'])
        summaries={};shots=[]
        for name,g in d['browser_groups'].items():
            assert set(g['cases'])==set(cfg['groups'][name])and g['counts']=={'PASS':1}
            assert g['host_exit']==g['database_remaining']==g['console_errors']==0
            assert g['status']==g['host_status']=='RUN_COMPLETE'
            assert g['auth_counts']['restored']is True and g['auth_counts']['before']==g['auth_counts']['after']
            assert not g.get('cleanup_failures')and not g['auth_cleanup_failures']and not g['session_leaks']
            assert g['real_auth']is True and g['test_only_usage_grant']is g['jwt_signed_by_runtime']is False
            c=next(iter(g['cases'].values()));assert c['status']=='PASS'and c['source_sha256']==expected_graph
            for key in ('actual_AuthProvider','actual_AuthGate','actual_Auth_PostgREST_browser','actual_public_finance_RPC','actual_operational_DEFERRED_no_capture','operational_DONE_finance_RUNNING','official_sections_and_24_metrics_equal','independent_book_signature','one_finance_capture','sealed_operational_original_unchanged','no_stock_money_HPP_effect','no_horizontal_overflow','progress_counts_from_server','no_overall_fake_percent','private_SQL_finance_advancement_not_cron'):assert c[key]is True,key
            assert c['full_factory_finance_qualified']is c['default_application_adopted']is c['production_go']is False
            assert not c['console_evidence']['unexpected_errors']and len(c['actual_progress_RPC_and_DOM'])>=3
            times=[x['millis']for x in c['actual_call_timings']];assert times and max(times)<8000
            contrasts=[x['ratio']for shot in c['visible_text_contrasts']for x in shot['rows']];assert contrasts and min(contrasts)>=4.5
            for path in c['shots']:
                file=Path(path).name;assert file in z.namelist();shots.append(file)
            summaries[name]=dict(status='PASS',case_id=cfg['groups'][name][0],official_readiness=c['official_readiness'],RPC_calls=len(times),RPC_max_ms=max(times),RPC_median_ms=median(times),minimum_text_contrast=min(contrasts),unexpected_console_errors=0,Auth_and_copy_restored=True)
            if name=='desktop':
                assert c['official_readiness']=='READY'and c['all24_READY_figures_rendered']is c['actual_lost_reply_same_UUID_reopen']is True
                recovery=c['initial_driver_recovery'];assert recovery['label']=='TRANSPORT_FAULT_WITH_REAL_AUTH_JOB_AND_STATUS'
                assert recovery['actual_large_server_refusal_claim']is False and len(recovery['synthetic_refusals'])==2
                assert all(x['synthetic']is True and x['args']['p_request']==recovery['request']for x in recovery['synthetic_refusals'])
                assert recovery['same_UUID_reload']is recovery['safe_same_UUID_recovery']is recovery['real_two_minute_observation']is True
                assert 120000<=recovery['elapsed_ms']<150000 and recovery['actual_status_reads']==62
                summaries[name]['initial_observer_elapsed_ms']=recovery['elapsed_ms']
            else:
                assert c['official_readiness']=='BLOCKED'and c['BLOCKED_figures_withheld_UNKNOWN_not_zero']is c['actual_mobile_finance_permission_revocation']is True
        assert len(shots)==7 and len(set(shots))==7
        assert z.read('A_PROGRESS_FINANCE_DESKTOP_OFFICIAL_READY24.png')==z.read('A_PROGRESS_FINANCE_DESKTOP_REOPENED_SAME_CAPTURE.png')
        # Expected old AC expiry/fallback is retained, never reclassified PASS.
        failures=[json.loads(z.read(n))for n in z.namelist()if n.startswith('ARTIFACT_FETCH/')and n.endswith('.json')and json.loads(z.read(n))['exit_code']!=0]
        assert len(failures)==1 and failures[0]['artifact_id']==10392910720 and failures[0]['retry']is False
    return dict(status='PASS_WRITER_EVIDENCE_VERIFICATION',candidate=CANDIDATE,backend=BACKEND,archive_sha256=ZIP_SHA,original_members=len(manifest),browser_cases=summaries,screenshots=7,unique_screenshot_contents=6,full22_copy_authority_and_CP6_restore=True,package_gates=package['gate'],old_AC_expiry_failure_retained=True,actual_browser_reruns=0,independent_acceptance=False,production_go=False)
if __name__=='__main__':print(json.dumps(verify(),indent=2))
