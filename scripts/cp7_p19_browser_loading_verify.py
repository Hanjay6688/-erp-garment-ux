"""Strict bounded browser loading diagnostic; no factory or new Native credit."""
from pathlib import Path
import hashlib,json,math,sys,traceback

def verify(root):
    root=Path(root)
    result=dict(classification='BOUNDED_CI_LOOPBACK_REAL_AUTH_CLICK_TO_RENDER',status='INCOMPLETE',
                Native_case_credit_added=0,factory_SLA_acceptance=False,full_P19_acceptance=False,
                independent_acceptance=False,production_go=False,observations=[])
    try:
        native=json.loads((root/'CP7_P18_E01_BRIDGE.json').read_text())
        package=json.loads((root/'T3_PACKAGE_INSTALL.json').read_text())
        backup=json.loads((root/'T3_BACKUP_RESTORE_DRILL.json').read_text())
        assert native['status']=='PASS' and native['expected_case_count']==native['observed_case_count']==9
        assert native['cp6_restored'] and native['advisor_gate']
        expected=dict(native=5,races=1,http=1,browser=2)
        for name,count in expected.items():
            group=native[name];rows=group['races' if name=='races' else 'cases']
            assert group['counts']==dict(PASS=count) and len(rows)==count
            assert all(row['status']=='PASS' for row in rows.values())
            assert group.get('database_remaining',0)==0 and group.get('auth_counts',{}).get('restored',True)
            assert not group.get('cleanup_failures') and not group.get('auth_cleanup_failures')
        assert all(package['gate'].values()) and package['primary_unchanged']
        assert package['auth_users_before']==package['auth_users_after']==0
        assert backup['status']=='RESTORED_SAME_MEANING' and all(backup['checks'].values())
        result.update(source_commit=package['run_identity']['tool_head'],run_identity=package['run_identity'],
                      source_bundle_sha256=native['source_sha256'],Native_correctness_and_restoration=True)
        for device in ('DESKTOP','MOBILE'):
            path=root/('P19_BROWSER_LOADING_'+device+'.json');raw=path.read_bytes();r=json.loads(raw)
            assert r['device']==device and r['complete_Native_Original_verified']
            assert r['classification']==result['classification'] and r['network']=='DISPOSABLE_SUPABASE_LOOPBACK_NO_THROTTLING'
            assert r['Native_case_credit_added']==0 and r['factory_SLA_acceptance'] is False
            samples=r['samples'];assert len(samples)==2
            expected_ids={'ANALYSIS_CAPTURE_'+device:('HEAVY_COMPLETE',3000,True,'erp_cp7_capture_analysis_v1'),
                          'STOCK_POPUP_'+device:('ROUTINE_READ',1000,False,'erp_cp7_read_analysis_v1')}
            assert {s['id']for s in samples}==set(expected_ids)
            case=native['browser']['cases']['P18_E01_BRIDGE_BROWSER_'+device]
            assert case['p19_loading_samples']==samples
            for sample in samples:
                kind,limit,inclusive,rpc=expected_ids[sample['id']]
                assert sample['status']=='OBSERVED' and sample['trusted_click']
                assert sample['clock']=='BROWSER_PERFORMANCE_MONOTONIC'
                elapsed=sample['elapsed_ms'];assert type(elapsed) in (float,int) and math.isfinite(elapsed) and 0<=elapsed<60000
                budget=sample['budget'];assert (budget['class'],budget['limit_ms'],budget['inclusive'])==(kind,limit,inclusive)
                assert budget['elapsed_ms']==elapsed
                meets=elapsed<=limit if inclusive else elapsed<limit
                assert budget['meets_limit'] is meets
                assert sample['rendered']['run_id']==r['source_run']
                assert sample['http']['status']==200 and sample['http']['rpc']==rpc and sample['http']['complete_body_utf8_bytes']>0
                assert sample['http']['timing']['responseEnd']>=0
                result['observations'].append(dict(device=device,id=sample['id'],elapsed_ms=elapsed,limit_ms=limit,
                    meets_limit=meets,http=sample['http'],file_utf8_sha256=hashlib.sha256(raw).hexdigest()))
        assert len(result['observations'])==4
        result['violations']=[r for r in result['observations']if not r['meets_limit']]
        result['status']='PASS_BOUNDED_DECLARED_SAMPLES' if not result['violations'] else 'LOADING_LIMIT_EXCEEDED'
    except Exception as error:
        result.update(error=str(error),traceback=traceback.format_exc())
    finally:
        (root/'P19_BROWSER_LOADING_RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':
    result=verify(sys.argv[1]);print(json.dumps(result,indent=2),flush=True)
    raise SystemExit(0 if result['status']=='PASS_BOUNDED_DECLARED_SAMPLES' else 1)
