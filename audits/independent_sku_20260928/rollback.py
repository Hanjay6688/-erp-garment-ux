from install import state,apply,ROOT,OUT
import sys,json,traceback
mode=sys.argv[1];r={'id':'SKU.ROLLBACK.'+mode.upper(),'status':'FAIL','mode':mode}
try:
 before=state();error=None
 try:apply('supabase/dev/cp6_bf_t2_rollback.sql')
 except Exception as e:error=str(e)
 after=state();r.update(before=before,after=after,response_error=error)
 if mode=='pre':
  expected=json.loads((OUT/'sku-before-bf.json').read_text());r['expected']=expected
  assert error is None,error
  assert after==expected,'Pre-use rollback changed predecessor data/catalogue'
 else:
  assert error and 'BF_USED_ROLLBACK_REFUSED' in error,error
  assert after==before,'Refused rollback changed state'
 r['status']='PASS'
except Exception as e:r.update(error=str(e),traceback=traceback.format_exc())
finally:
 (OUT/('sku-rollback-'+mode+'.json')).write_text(json.dumps(r,indent=2,default=str));print(json.dumps({k:v for k,v in r.items() if k not in ['before','after','expected']},default=str))
# Reinstall whenever rollback succeeded, even if independent comparison found drift.
if mode=='pre' and r.get('response_error') is None:apply('supabase/dev/cp6_bf_t1_family.sql')
