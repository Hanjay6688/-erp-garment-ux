from pathlib import Path
import importlib.util,sys,subprocess,re,json,hashlib
root=Path.cwd();here=Path(__file__).resolve().parent
name='scripts/cp7_customer_credit/admission/03_native_admission_transform.py'
def load(label,path):
 s=importlib.util.spec_from_file_location(label,path);m=importlib.util.module_from_spec(s);sys.modules[label]=m;s.loader.exec_module(m);return m
old=here/'BEFORE.py';old.write_bytes(subprocess.check_output(['git','show','80b97175bb7e29189af115dd24e1580330d8a660:'+name]))
a,b=load('old_completion',old),load('new_completion',root/name)
results=[];controls=[]
for identity,file,function,transform in b.SPECS:
 if function not in ('post_sales_payment','reverse_sales_payment','reverse_sales_return','reverse_sale'):continue
 text=(root/'supabase/release/cp6-t3'/file).read_text()
 body=re.search(r'CREATE OR REPLACE FUNCTION erp\.'+function+r'\([^$]*?\$function\$(.*?)\$function\$',text,re.S)[1]
 old_fn={'post_sales_payment':a.post_payment,'reverse_sales_payment':a.reverse_payment,'reverse_sales_return':a.reverse_return,'reverse_sale':a.reverse_sale}[function]
 prior,new=old_fn(body),transform(body)
 action,param,permission={'post_sales_payment':('PAYMENT','p_payment_id','require_internal'),'reverse_sales_payment':('PAYMENT_REVERSE','p_payment_id','require_owner_admin'),'reverse_sales_return':('RETURN_REVERSE','p_return_id','require_owner_admin'),'reverse_sale':('SALE_REVERSE','p_sale_id','require_owner_admin')}[function]
 callback="perform cp7_credit.native_source_complete('%s',%s);"%(action,param)
 assert prior.count(callback)==new.count(callback)==1
 assert new.index(callback)>new.rfind('update erp.sales_headers')
 assert new.index(callback)>new.rfind('insert into erp.audit_logs')
 def erased(v):
  v=v.replace(callback+'\n  perform erp.'+permission+'();','',1)
  return re.sub(r'\s+',' ',v).strip()
 assert erased(prior)==erased(new),function
 assert prior.count('perform erp.'+permission+'();')==new.count('perform erp.'+permission+'();')
 try:transform(body+'\n-- unreviewed trailing statement')
 except ValueError:pass
 else:raise AssertionError('unknown terminal accepted')
 results.append({'function':function,'status':'PASS','only_complete_and_its_final_authority_check_moved':prior!=new,'remaining_statements_identical':True,'callback_after_header_audit_and_native_tail':True,'unknown_terminal_refused':True})
 if function!='reverse_sale':
  update=re.search(r'  update erp.sales_headers\n  set status=case[\s\S]*?where id=[hs]\.id;',body)[0]
  controls.append({'function':function,'update':update,'record':'s'if function=='reverse_sales_return'else'h'})
guard=(root/'scripts/cp7_customer_credit/native-empty/02_native_empty_callbacks.sql').read_text()
start=guard.index('  if net<0 or paid<0 or paid>net or h.status is distinct from(')
end=guard.index('end if;',start)+7
(here/'FRAGMENTS.json').write_text(json.dumps({'updates':controls,'unchanged_final_predicate':guard[start:end]},indent=2)+'\n')
(here/'TRANSFORM_RESULT.json').write_text(json.dumps({'classification':'PURE_EXACT_NATIVE_SOURCE_TRANSFORM_NOT_RUNTIME','results':results,'admission_sha256':hashlib.sha256((root/name).read_bytes()).hexdigest(),'native_empty_callback_sha256':hashlib.sha256((root/'scripts/cp7_customer_credit/native-empty/02_native_empty_callbacks.sql').read_bytes()).hexdigest()},indent=2)+'\n')
print(json.dumps({'exact_transform_checks':'PASS','functions':len(results),'native_runtime_executed':False}))
