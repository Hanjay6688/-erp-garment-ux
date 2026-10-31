"""Exact terminal e925/a209 failure intake; no runtime imports or new acceptance."""
from pathlib import Path
from hashlib import sha256
import argparse,gzip,json,zipfile
from intake_common import GitBytes,exact,fields,pin,require
from intake_sku27 import strict,group,literal,raw_evidence,declared_files,CASE,MAIN,NATIVE,COST,PACKAGE,RESTORE,NS

PLANS={
 'SKU':dict(head='e9256772579f387df77dde949f8ea619cbd86856',tree='8de422523afa42c20d85e830749ed232b7edc6b9',run_id=41109346033,job_id=124247417634,artifact_id=13009010614,bytes=94787144,sha256='06d8605b40b05c62b6a9cc7115444560f403d6c1844aa114e901e76a26ac9ac0',members=170,main=MAIN,source=NS+'SOURCE.json'),
 'S03':dict(head='a2096c570b6a0300b8ef299d6a167b68849e427d',tree='9732ed1ecfe9b14e78adef4e4e12c9b960b92714',run_id=41113128260,job_id=124260357407,artifact_id=13009109235,bytes=359771010,sha256='6e26f2ea5836aca14a514a9c3d2b6a2254fc4d1b513a72028b1f44745020c808',members=195,main='CP7_S03_MOUNTED_FULL_APP_BROWSER4.json',source='scripts/current-attendance-choice-browser4-lawful-successor/SOURCE.json')}
GATES=dict(installed=True,primary_unchanged=True,backup_restore_drill=True,security_advisors=True,writer_runtime=False)


def check(g,z,p,kind):
 source=strict(g.read(p['source']));files=source['files']
 pins=files.items() if type(files)is dict else ((x['path'],x)for x in files)
 checked=0
 for name,expected in pins:
  g.verify_pin(name,{key:expected[key]for key in('bytes','sha256')});checked+=1
 main,package,restore=(strict(z.read(name))for name in (p['main'],PACKAGE,RESTORE))
 fields(main,dict(status='INCOMPLETE',qualification_commit=p['head'],baseline_full22_all_rows_all_sequences_equal=True,restore_raw_public_equal=True,cp6_restored=True,baseline_advisors_equal=True,advisor_gate=True,production_go=False,independent_acceptance=False),'EXACT_FAILED_OUTER_AND_RESTORATION')
 exact(main.get('restore_error'),None,'NO_OUTER_RESTORE_FAILURE')
 exact(package['gate'],GATES,'EXACT_4_OF_5_GATES')
 fields(package,dict(primary_unchanged=True,auth_users_before=0,auth_users_after=0,backup_restore_drill='RESTORED_IDENTICAL'),'PACKAGE_AUTH_AND_RESTORE')
 fields(package['run_identity'],dict(tool_head=p['head'],github_sha=p['head'],run_id=str(p['run_id']),run_attempt='1'),'EXACT_CURRENT_RUN')
 fields(restore,dict(status='RESTORED_IDENTICAL'),'BACKUP_DRILL')
 require(all(restore['checks'].values()),'ALL_BACKUP_CHECKS')
 exact(restore['data']['differ'],{},'NO_BACKUP_ROW_DIFFERENCE')
 require(len(main['committed'])==1,'ONE_CURRENT_COMPOSITE_CASE')
 part=next(iter(main['committed'].values()))
 fields(part,dict(status='INCOMPLETE'),'FAILED_COMPOSITE_KEPT_FAILED')
 detail={}
 if kind=='SKU':
  exact(set(main['committed']),{CASE},'EXACT_SKU_COMPOSITE')
  native_ids=list(literal(g,'scripts/current-sku-pair-conversion-qualification/cases.py','IDS'))
  cost_ids=list(literal(g,'scripts/current-sku-group-cost-qualification/cases.py','IDS'))+list(literal(g,NS+'recovery_cases.py','IDS'))
  for label,name,ids in [('fresh_base_native7',NATIVE,native_ids),('fresh_cost_native5',COST,cost_ids)]:
   value=strict(z.read(name));exact(part[label]['native'],value,'SAME_RUN_NATIVE_RAW_ORIGINAL');group(value,ids)
  callbacks=part['fresh_callbacks11']['concurrency']
  fields(callbacks,dict(status='RUN_COMPLETE',counts={'PASS':11},database_remaining=0),'ALL11_FRESH_CALLBACKS')
  require(len(callbacks['races'])==11 and all(r['status']=='PASS'for r in callbacks['races'].values()),'EXACT11_PASS_ROWS')
  require(not callbacks.get('business_day_retried')and not callbacks.get('business_day_first_attempt'),'SINGLE_FIRST_ATTEMPT')
  for row in callbacks['races'].values():
   fields(row['installed_baseline_restoration'],dict(all22_all_rows_all_sequences_roles_exact=True,complete_database_dump_restored=True,cp6_restored=True,advisors_equal=True,selected_table_cleanup=False),'EACH11_FULL_RESTORE')
  exact(len(part['fresh_callbacks11']['copy_catalog_admissions']),11,'ELEVEN_COPY_ADMISSIONS')
  browser=part['fresh_real_Auth_browser4']['browser']
  raw=raw_evidence(z,part)
  source_maps=declared_files(g,main['source_declaration']['current_installation'])
  detail=dict(observed_native=7,observed_cost=5,observed_callbacks=11,raw_evidence=raw,actual_product_source_maps=source_maps,complete27_qualified=False)
 else:
  browser=part['browser']
  hosts=[n for n in z.namelist()if n.startswith('S03_BROWSER4_HOST_ORIGINAL_')and n.endswith('.json.gz')]
  exact(len(hosts),1,'ONE_COMPLETE_RAW_HOST_ORIGINAL')
  host=strict(gzip.decompress(z.read(hosts[0])))
  fields(host,dict(status='RUN_COMPLETE',auth_cleanup_failures=[],console_errors=[]),'ACTUAL_RAW_HOST_COMPLETED_AND_CLEANED')
  exact(host['cases'],browser['cases'],'HOST_CASES_EQUAL_EMBEDDED_ORIGINAL')
  script=g.read('scripts/current-attendance-choice-browser4-lawful-successor/cases.mjs')
  exact(browser['script_sha256'],sha256(script).hexdigest(),'EXACT_EXECUTED_PUBLIC_SCRIPT')
  before=next(n for n in z.namelist()if '_MOBILE390_'in n and '_013_BEFORE_POOL_READ_'in n)
  after=next(n for n in z.namelist()if '_MOBILE390_'in n and '_014_AFTER_POOL_READ_'in n)
  a,b=(strict(gzip.decompress(z.read(n)))for n in(before,after));exact(a,b,'ACTUAL_FAILED_POOL_READ_ALL22_ROWS_ALL_SEQUENCES_UNCHANGED')
  control=a['all_rows']['erp.accounting_period_control'];exact(control[0]['closed_through'],'2026-10-24','ACTUAL_DATABASE_SOURCE_PERIOD_CLOSED')
  detail=dict(complete_browser4_qualified=False,raw_host_original=pin(z.read(hosts[0])),failed_pool_read_raw_censuses_equal=True,actual_closed_through=control[0]['closed_through'],read_selection_stale_answer_is_inference=True)
 fields(browser,dict(status='INCOMPLETE',counts={'PASS':2,'INCOMPLETE':2},real_auth=True,jwt_signed_by_runtime=False,host_exit=0,host_status='RUN_COMPLETE',database_remaining=0,session_leaks=[],console_errors=0,auth_cleanup_failures=[],auth_counts=dict(before=[0,0,0,0],after=[0,0,0,0],restored=True)),'ACTUAL_TWO_PASS_TWO_FAILED_BROWSER_WITH_FULL_CLEANUP')
 require(not browser['cleanup_failures'],'NO_BROWSER_CLEANUP_FAILURE')
 exact(len(browser['cases']),4,'EXACT_FOUR_BROWSER_RESULTS')
 failures={name:row['error']for name,row in browser['cases'].items()if row['status']=='INCOMPLETE'}
 exact(len(failures),2,'EXACT_TWO_FAILURES_RETAINED')
 originals={name:pin(z.read(name))for name in(p['main'],PACKAGE,RESTORE)}
 return dict(status='EXACT_TERMINAL_FAILED_ORIGINAL_AND_RESTORATION_ROOT_VERIFIED',head=p['head'],tree=p['tree'],run_id=p['run_id'],job_id=p['job_id'],artifact_id=p['artifact_id'],archive={key:p[key]for key in('bytes','sha256','members')},originals=originals,exact_source_pins=checked,browser_counts=browser['counts'],failures=failures,package_gates=package['gate'],outer_restore_source_bound_receipts=True,outer_raw_before_after_not_serialized=True,prior_runs_aggregated=False,production_go=False,independent_acceptance=False,**detail)


def main():
 parser=argparse.ArgumentParser();parser.add_argument('--kind',choices=PLANS,required=True)
 for name in('source','archive','output'):parser.add_argument('--'+name,type=Path,required=True)
 args=parser.parse_args();p=PLANS[args.kind];g=GitBytes(args.source,p['head'],p['tree'])
 exact(pin(args.archive.read_bytes()),{key:p[key]for key in('bytes','sha256')},'EXACT_CANONICAL_ARCHIVE')
 with zipfile.ZipFile(args.archive)as z:
  exact(len(z.namelist()),p['members'],'EXACT_ARCHIVE_MEMBER_COUNT');exact(len(set(z.namelist())),p['members'],'NO_DUPLICATE_MEMBER')
  receipt=check(g,z,p,args.kind)
 args.output.write_text(json.dumps(receipt,indent=2)+'\n')
 print(json.dumps(dict(status=receipt['status'],kind=args.kind,source_pins=receipt['exact_source_pins'],browser_counts=receipt['browser_counts'])))


if __name__=='__main__':main()
