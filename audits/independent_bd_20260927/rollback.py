"""Execute the exact delivered rollback under its required maintenance contract."""
from pathlib import Path
import sys,os,json,traceback,hashlib
from audit_state import snapshot
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'audit-results'
sys.path.insert(0,str(ROOT/'scripts'))
from cp6_t3_release_package import Applier,CLONE
MODE=sys.argv[1]
def main():
    result={'id':'IND-42.'+MODE.upper(),'status':'BLOCKED','scope':'Exact supplied rollback file, independent before/after data+function+column+relation comparison'}
    f=ROOT/'supabase/release/cp6-t3-rollbacks/20260925040000_erp_v2_6_20bd_cp6_laundry_prices_invoices.rollback.sql'
    text=f.read_text();result['rollback_sha256']=hashlib.sha256(f.read_bytes()).hexdigest()
    a=Applier(CLONE,os.environ['CP6_ADMISSION_CONTROL_PGURL'])
    try:
        before=snapshot();error=None
        try:a.closed(lambda c:c.execute(text,prepare=False))
        except Exception as e:error=str(e)
        result['response_error']=error
        after=snapshot()
        if MODE=='pre':
            expected=json.loads((OUT/'independent-before-bd.json').read_text())
            assert error is None,error
            result['expected']=expected;result['actual']=after
            assert after==expected,'Rollback did not restore independent BC data/catalogue snapshot'
            result['status']='PASS'
        else:
            result['before']=before;result['after']=after
            assert error is not None and 'BD_POST_USE_ROLLBACK_REFUSED' in error,error
            assert after==before,'Refused post-use rollback changed state'
            result['status']='PASS'
    except Exception as e:result.update(status='FAIL',error=str(e),traceback=traceback.format_exc())
    finally:
        (OUT/('rollback-'+MODE+'.json')).write_text(json.dumps(result,indent=2,default=str)+'\n')
        print(json.dumps({k:v for k,v in result.items() if k not in ('before','after','actual','expected')},default=str),flush=True)
    if result['status']!='PASS':return 1
    if MODE=='pre':
        # Restore the same frozen BD product for the native business tests.
        manifest=json.loads((ROOT/'supabase/release/cp6-t3/MANIFEST.json').read_text())
        b=next(x for x in manifest['files'] if x['key']=='BD');data=(ROOT/b['file']).read_bytes()
        assert hashlib.sha256(data).hexdigest()==b['package_sha256']
        a.install({'stamp':b['stamp'],'name':b['name'],'closed':b['closed_admission']},data.decode())
    return 0
if __name__=='__main__':raise SystemExit(main())
