"""One install, fresh Native7 then reused race3/AuthHTTP1, full outer restore."""
from pathlib import Path
import importlib.util
import psycopg
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
CASE='VENDOR_RECEIVABLE_NATIVE7_RACES3_AUTH1'

def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def scheduler_quiet(url):
 return load('vendor_combined_quiet',HERE/'native_runner.py').scheduler_quiet(url)

def handoff_source(url,report,state):
 from cp7_p21_current_chain_rehearsal_probe import helper
 from cp7_vendor_receivable import composition as product
 _,_,_,_,catalog=product.runtime()
 with psycopg.connect(url)as connection,connection.cursor()as cursor:
  before=catalog._catalog_rows(cursor);data=catalog._data(cursor)
  # Native committed used-inverse witness has one declared test ERP USAGE
  # grant. Prove that exact delta, then remove it before TEMPLATE copies.
  with helper.control.product_catalog(cursor):product.verify(cursor,state)
  if before!=state['after']:cursor.execute('revoke usage on schema erp from authenticated')
  assert catalog._catalog_rows(cursor)==state['after'],'COMBINED_NATIVE_HANDOFF_NOT_EXACT22'
  assert catalog._data(cursor)==data,'COMBINED_NATIVE_HANDOFF_CHANGED_BUSINESS_DATA'
  product.verify(cursor,state);connection.commit()
 report['native_to_followup_handoff']=dict(classification='LOCAL_NATIVE_USAGE_HARNESS_HANDOFF',
  only_declared_test_grant_removed=before!=state['after'],all22_equal_installed_product=True,
  committed_Native_business_data_unchanged=True)

def exercise(conn,cur,database,url,report,state):
 native=load('vendor_combined_native7',HERE/'native_runner.py')
 first=report.setdefault('fresh_native7',dict(status='INCOMPLETE'))
 native.exercise(conn,cur,database,url,first,state)
 assert first['status']=='PASS'and first['native']['counts']=={'PASS':7},first
 handoff_source(url,report,state)
 follow=load('vendor_combined_race_auth',ROOT/'scripts/current-vendor-receivable-followup/runner.py')
 second=report.setdefault('followup4',dict(status='INCOMPLETE'))
 with psycopg.connect(url)as connection,connection.cursor()as cursor:
  follow.exercise(connection,cursor,database,url,second,state)
 assert second['status']=='PASS',second
 groups=(first['native']['cases'],second['races']['races'],second['http']['cases'])
 cases={key:dict(status=value['status'])for group in groups for key,value in group.items()}
 assert sum(map(len,groups))==len(cases)==11 and all(v['status']=='PASS'for v in cases.values()),cases
 report.update(status='PASS',native=first['native'],business_cases=cases,business_counts={'PASS':11},
  used_guard_refused_before_DDL=True,actual_Native_cases=7,actual_two_session_races=3,actual_Auth_HTTP_cases=1,actual_browser_cases=0,
  acceptance_requires_complete_outer_restore_and_package=True,production_go=False,independent_acceptance=False)
