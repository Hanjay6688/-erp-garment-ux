#!/usr/bin/env python3
"""Admit exact AM evidence for unchanged mutations; seal only fresh AN family."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,zipfile
ROOT=Path('cp6-proof/writer-an')
SOURCE=Path(__file__).resolve().parents[1]
BASE='6b0aa79753b3dd5a0dd7cd77012094971e7fa8aa'
BASE_TREE='882986cd99b22fe1bb0192aa5841f0841ac7a23e'
FULL_HEAD='bf05659d4f8e99d0332215772d658417e4233cc8'
FULL_TREE='e5ac4db612e5c9097daf0c6a446abeafffc29cd2'
FULL_DIGEST='299684058ecb0e3f03c8ab18a374f4d944848268d4462348e89c89e8036fd4cc'
BRIDGE_DIGEST='a909662a4c33099980f60bb2d6dc3bf0e26620d9c21c078679f1874fde07df7b'
MIGRATION='supabase/migrations/20260921223438_erp_v2_6_20an_cp6_cutting_selectors.sql'
ROLLBACK='supabase/rollbacks/20260921223438_erp_v2_6_20an_cp6_cutting_selectors.rollback.sql'
ALLOWED={'.github/workflows/cp6-final-boundary-audit.yml','scripts/cp6_disposable_ui_scope.py',
 'scripts/cp6_preuse_rollback_maintenance.py','scripts/check-cp6-expanded-audit-closure.mjs',
 'scripts/check-source-ownership.mjs','scripts/cp6_foundation_qualification.py','scripts/cp6_final_gap_ui.mjs',
 'scripts/cp6_disposable_ui_e2e.mjs','scripts/cp6_frontend_recovery_ui.mjs',
 'docs/cp6-frontend-recovery.md','docs/evidence/cp6-disposable-ui-source-pins.json',
 'src/ConnectedCuttingPage.tsx','src/connected-cutting.css','src/useProductionMutation.ts','src/types/database.preconnect.ts','src/cuttingSelectors.ts','src/cuttingSelectors.test.ts',
 'src/ConnectedProductionRecovery.dom.test.tsx','tests/fixtures/productionRecovery.ts',MIGRATION,ROLLBACK}


def save(name,data):
 ROOT.mkdir(parents=True,exist_ok=True)
 (ROOT/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')


def source_boundary():
 git=lambda *a:subprocess.check_output(['git','-C',str(SOURCE),*a],text=True).strip()
 assert git('rev-parse',BASE+'^{tree}')==BASE_TREE and git('merge-base',BASE,'HEAD')==BASE
 assert not git('diff','--name-only','HEAD')
 changed=set(git('diff','--name-only',BASE,'HEAD').splitlines())
 extra={n for n in changed if (n.startswith('scripts/cp6_v2620an_') and n.endswith(('.py','.mjs'))) or (n.startswith('docs/evidence/cp6-an-') and n.endswith('.json'))}
 assert changed<=ALLOWED|extra,changed-(ALLOWED|extra)
 assert set(git('diff','--name-only',BASE,'HEAD','--','supabase').splitlines())=={MIGRATION,ROLLBACK}
 assert not git('diff','--name-only','--diff-filter=MDRTCUXB',BASE,'HEAD','--','supabase')
 assert not git('diff','--name-only',BASE,'HEAD','--','scripts/cp6_v2620am_*','scripts/cp6_final_crossflow_review.py','scripts/cp6_v2620al_*')
 head,tree=git('rev-parse','HEAD'),git('rev-parse','HEAD^{tree}')
 assert (head,tree)==(os.environ['CP6_RUNTIME_HEAD'],os.environ['CP6_RUNTIME_TREE'])
 import cp6_v2620an_runtime as runtime
 pins=runtime.verify_source_files()
 assert len(pins['new_functions'])==2 and pins['functions'][0]['predecessor_sha256']==pins['functions'][0]['installed_sha256']
 return dict(head=head,tree=tree,changed=sorted(changed),all_prior_sql_unchanged=True,am_mutation_oracles_unchanged=True,
   original_reader_preserved=True,new_readers=2,new_business_tables=0)


def archive(path,size,digest,entries):
 p=Path(path);assert p.stat().st_size==size and hashlib.sha256(p.read_bytes()).hexdigest()==digest
 z=zipfile.ZipFile(p);assert z.testzip() is None and len(z.namelist())==entries
 assert all(not n.startswith('/') and '..' not in Path(n).parts for n in z.namelist())
 return z


def admit(full,bridge):
 source=source_boundary()
 with archive(full,64497485,FULL_DIGEST,355) as z:
  read=lambda n:json.loads(z.read('candidate/cp6-proof/'+n))
  final=read('writer-am/FINAL_GATE.json')
  assert final['status']=='WRITER_PASS_AFFECTED_AM_FAMILY' and (final['head'],final['tree'])==(FULL_HEAD,FULL_TREE)
  assert final['exact_restore'] and final['cleanup'] and not final['independent_acceptance']
  gate=read('writer-am/WRITER_GATE.json');assert gate['status']=='WRITER_GROUPS_COMPLETE_RESTORE_PENDING'
  assert len(gate['results'])==19
  for n,r in gate['results'].items():assert r['actual']==r['expected']==read(n)['status'],n
  business=read('writer-am/BUSINESS.json')
  assert business['counts']==dict(PASS=179,CONTROL_PASS=39,BUG_PROVEN=0,GAP_PROVEN=0,DATE_POLICY_REVIEW_REQUIRED=12,INCOMPLETE=0,FAIL=0)
  assert len(business['cases'])==len(set(business['planned_case_ids']))==230 and set(business['cases'])==set(business['planned_case_ids'])
  assert read('writer-am/VALUES.json')['counts']==dict(PASS=65,BUG_PROVEN=0,GAP_PROVEN=0,INCOMPLETE=0)
  assert read('AM_MAINTENANCE_ROLLBACK/manifest.json')['completed_case_count']==20
 with archive(bridge,1613668,BRIDGE_DIGEST,45) as z:
  read=lambda n:json.loads(z.read('candidate/cp6-proof/'+n))
  final=read('writer-am/FOLLOWUP_FINAL_GATE.json')
  assert final['status']=='WRITER_PASS_AM_TRANSFER_INVOICE_FOLLOWUP' and (final['source']['head'],final['source']['tree'])==(BASE,BASE_TREE)
  assert final['exact_restore'] and final['cleanup'] and final['fresh_transfer_invoice_cases']==8
  cases=read('writer-am/TRANSFER_CROSSFLOW.json')
  assert cases['status']=='WRITER_PASS' and cases['counts']==dict(CONTROL_PASS=8,BUG_PROVEN=0,INCOMPLETE=0)
 result=dict(status='AN_SCOPE_AND_REUSED_AM_EVIDENCE_ADMITTED',source=source,
  reused_evidence=[dict(classification='REUSED_EVIDENCE',run=35663140263,artifact=10668124130,sha256=FULL_DIGEST,head=FULL_HEAD,tree=FULL_TREE),
   dict(classification='REUSED_EVIDENCE',run=35665864959,artifact=10669107236,sha256=BRIDGE_DIGEST,head=BASE,tree=BASE_TREE)],
  business230_fresh=False,am_maintenance20_fresh=False,historical460_fresh=False,
  fresh_required=['AN_SELECTORS_NATIVE_28','AN_SELECTORS_UI_15','AN_MAINTENANCE_20','HTTP_UI_RECOVERY','EXACT_RESTORES','CLEANUP'],
  global_status='CP6_HOLD',independent_acceptance=False,production_go=False)
 save('ADMISSION',result);return result


def seal():
 source=source_boundary();root=Path('cp6-proof');read=lambda n:json.loads((root/n).read_text())
 admission=read('writer-an/ADMISSION.json');assert admission['status']=='AN_SCOPE_AND_REUSED_AM_EVIDENCE_ADMITTED' and admission['source']==source
 native=read('writer-an/SELECTORS_NATIVE.json');assert native['status']=='WRITER_PASS'
 assert native['counts']==dict(CONTROL_PASS=28,INCOMPLETE=0)
 assert len(native['cases'])==len(set(native['planned_case_ids']))==28 and set(native['cases'])==set(native['planned_case_ids'])
 assert all(native[k] for k in ('boundary_restored','schema_usage_restored','runtime_verified'))
 ui=read('final-audit/SELECTORS_UI.json');assert ui['status']=='WRITER_PASS'
 assert len(ui['cases'])==len(set(ui['planned_case_ids']))==15 and {r['id'] for r in ui['cases']}==set(ui['planned_case_ids'])
 assert all(r['status']=='PASS' for r in ui['cases'])
 for r in (native,ui):assert (r['head'],r['tree'])==(source['head'],source['tree'])
 access=read('final-audit/ACCESS_REVALIDATION.json')
 assert access['status']=='WRITER_PASS' and (access['head'],access['tree'])==(source['head'],source['tree'])
 assert len(access['cases'])==len(set(access['planned_case_ids']))==92
 assert {r['id'] for r in access['cases']}==set(access['planned_case_ids']) and all(r['status']=='PASS' for r in access['cases'])
 assert access['boundary_tables']>=223 and not access['schema_acl_modified'] and not access['product_changed']
 assert access['product_reference_head']=='08645547394a502584f5270ac64b4f116817c387'
 assert not subprocess.check_output(['git','-C',str(SOURCE),'diff','--name-only',access['product_reference_head'],'HEAD','--','src','supabase','package.json','package-lock.json'],text=True).strip()
 for n,status in {'writer-an/ADVISORS_AFTER.json':'PASS_REVIEWED_SECURITY_DELTA','AN_MAINTENANCE_ROLLBACK/manifest.json':'PASS',
  'final-audit/HTTP.json':'PASS','final-audit/UI.json':'WRITER_PASS','final-audit/FRONTEND_RECOVERY.json':'WRITER_PASS',
  'final-audit/INDEPENDENT_UI_GAPS.json':'PASS_REVIEWED_SCOPE','final-audit/MONEY_INDEPENDENT.json':'PASS_REVIEWED_SCOPE'}.items():assert read(n)['status']==status,n
 assert read('AN_MAINTENANCE_ROLLBACK/manifest.json')['completed_case_count']==20
 recovery=read('final-audit/FRONTEND_RECOVERY.json');assert len(recovery['cases'])==9 and all(r['status']=='PASS' for r in recovery['cases'])
 unit=read('final-audit/FRONTEND_UNIT_DOM.json');assert unit['numFailedTests']==0 and unit['numPassedTests']>=342
 foundation=read('final-audit/FOUNDATION_QUALIFICATION.json')
 assert foundation['runtime_generation']=='AN' and foundation['counts']==dict(CONTROL_PASS=11,BUG_PROVEN=0,GAP_PROVEN=4,INCOMPLETE=0)
 # Original v1 remains bounded for compatibility. Its two selector findings are
 # closed only for the v2 caller by the dedicated native+real HTTP/UI proof above.
 restore=read('writer-an/EXACT_AM_RESTORE.json')
 assert restore['status']=='PASS' and restore['full_boundary_exact'] and restore['public_catalog_exact']
 assert (restore['functions'],restore['tables'])==(533,228)
 refusals=read('writer-an/ROLLBACK_REFUSALS.json')['cases'];assert len(refusals)==11 and all(r['status']=='PASS' and r['boundary_restored'] for r in refusals.values())
 ah=read('independent-ai/EXACT_RESTORE.json');assert ah['status']=='PASS_REVIEWED_SCOPE' and ah['full_boundary_exact']
 assert (ah['functions'],ah['tables'],ah['auth_users'],ah['app_users'])==(533,223,0,0)
 for name,marker in [('independent-ai/PHYSICAL_CLEANUP.txt','remaining_database_container=0'),('CP6_AUTH_CLONE_CLEANUP.txt','remaining_databases=0')]:
  raw=(root/name).read_text();assert 'status=PASS' in raw and marker in raw
 result=dict(status='WRITER_PASS_AFFECTED_AN_SELECTOR_FAMILY',source=source,native_controls=28,real_http_ui_cases=15,
   maintenance_schedules=20,recovery_cases=9,access_revalidation_cases=92,exact_restore=True,cleanup=True,
   reused_evidence=admission['reused_evidence'],date_policy_hold=12,global_status='CP6_HOLD',production_go=False,independent_acceptance=False)
 save('FINAL_GATE',result);return result

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--full');p.add_argument('--bridge');p.add_argument('--seal',action='store_true');a=p.parse_args()
 r=seal() if a.seal else admit(a.full,a.bridge)
 print(json.dumps({k:v for k,v in r.items() if k!='source'}))
