"""Capture actual AN and proposed AO/AP catalogs; every proposal is rolled back."""
from pathlib import Path
import json,subprocess,traceback
import psycopg
import cp6_v2620an_runtime as runtime
import cp6_v2620ao_definitions as ao
import cp6_v2620ap_definitions as ap
from cp6_ao_ap_inventory import inventory,data,platform,function_pins,sha

ROOT=Path('cp6-proof/ao-ap-package');ROOT.mkdir(parents=True,exist_ok=True)
report=dict(status='INCOMPLETE',head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),tree=subprocess.check_output(['git','rev-parse','HEAD^{tree}'],text=True).strip(),production_go=False,independent_acceptance=False,migration_installed=False,stages={})
try:
 with psycopg.connect('postgresql://supabase_admin:postgres@127.0.0.1:54322/postgres') as conn,conn.cursor() as cur:
  cur.execute("set local timezone='UTC';set local statement_timeout='120s'")
  assert len(runtime.verified_successor(cur))==692
  baseline=data(cur);before=inventory(cur);ledger=platform(cur)
  report['stages']['AN']=dict(objects=before,functions=function_pins(cur))
  report['restore_constraints']=cur.execute("select c.conname,pg_get_constraintdef(c.oid) from pg_constraint c where c.conrelid='erp.payroll_deductions'::regclass and c.conname='payroll_deductions_deduction_type_check'").fetchall()
  for name,m in [('AO',ao),('AP',ap)]:
   for identity,definition,acl,owner in m.PREDECESSOR:
    found=cur.execute('select pg_get_functiondef(p.oid),p.proacl::text,pg_get_userbyid(p.proowner) from pg_proc p where p.oid=to_regprocedure(%s)',(identity,)).fetchone()
    assert found==(definition,acl,owner),identity
   cur.execute('set local role postgres');cur.execute(m.SCHEMA,prepare=False)
   old={r[0] for r in m.PREDECESSOR}
   for identity,definition in m.FUNCTIONS.items():
    cur.execute(definition,prepare=False)
    if identity not in old:
     cur.execute(f'revoke all on function {identity} from public,anon,authenticated,service_role')
     if identity.startswith('public.'):cur.execute(f'grant execute on function {identity} to authenticated,service_role')
   if getattr(m,'TRIGGERS',''):cur.execute(m.TRIGGERS,prepare=False)
   report['stages'][name]=dict(objects=inventory(cur),functions=function_pins(cur),schema_sha256=sha(m.SCHEMA),triggers_sha256=sha(getattr(m,'TRIGGERS','')),definitions_sha256=sha(json.dumps(m.FUNCTIONS,sort_keys=True)))
  conn.rollback()
  assert inventory(cur)==before and data(cur)==baseline and platform(cur)==ledger
  report.update(status='CAPTURE_PASS',complete_boundary_restored=True)
except Exception as exc:report.update(error=str(exc),traceback=traceback.format_exc())
(ROOT/'CATALOG_CAPTURE.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in('stages','restore_constraints')}))
raise SystemExit(0 if report['status']=='CAPTURE_PASS' else 1)
