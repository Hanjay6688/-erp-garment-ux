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
  if after!=expected:
   # PostgreSQL reparses a varchar[] -> text[] cast into equivalent per-element casts.
   # Retain the raw mismatch and require identical nonconstraint state and equal predicates.
   delta=[k for k in expected if expected[k]!=after[k]]
   assert set(delta)<=set(['constraints','constraint_definitions']),('Material rollback drift',delta)
   a={tuple(x[:3]):x[3] for x in expected['constraint_definitions']};b={tuple(x[:3]):x[3] for x in after['constraint_definitions']}
   changed=[k for k in a.keys()|b.keys() if a.get(k)!=b.get(k)]
   assert changed==[('erp','rework_component_lines','rework_component_lines_rate_basis_check')],changed
   import psycopg,re
   from install import audit_state
   key=changed[0];allowed=['CONTRACTOR_RATE','PO_SNAPSHOT','LAUNDRY_ZERO','LEGACY_CLIENT']
   assert re.findall(r"'([^']*)'",a[key])==re.findall(r"'([^']*)'",b[key])==allowed
   probes=allowed+['SKU_RATE','','contractor_rate',' CONTRACTOR_RATE','OTHER',None];observed=[]
   with psycopg.connect(audit_state.DSN) as c:
    for value in probes:
     pair=[c.execute('select '+definition[6:]+' from (values(%s::varchar)) t(rate_basis)',(value,)).fetchone()[0] for definition in [a[key],b[key]]]
     assert pair[0]==pair[1] and (pair[0] is None if value is None else pair[0]==(value in allowed)),(value,pair)
     observed.append({'value':value,'before':pair[0],'after':pair[1]})
   r['textual_catalogue_difference']={'before':a[key],'after':b[key],'scope':'Same finite text membership predicate; PostgreSQL moved array cast to each literal. Raw definitions are not byte-identical.','membership_checks':observed}
   r['comparison']='All data/other catalogue exact; sole check-constraint representation differs equivalently'

 else:
  assert error and 'BF_USED_ROLLBACK_REFUSED' in error,error
  assert after==before,'Refused rollback changed state'
 r['status']='PASS'
except Exception as e:r.update(error=str(e),traceback=traceback.format_exc())
finally:
 (OUT/('sku-rollback-'+mode+'.json')).write_text(json.dumps(r,indent=2,default=str));print(json.dumps({k:v for k,v in r.items() if k not in ['before','after','expected']},default=str))
# Reinstall whenever rollback succeeded, even if independent comparison found drift.
if mode=='pre' and r.get('response_error') is None:apply('supabase/dev/cp6_bf_t1_family.sql')
