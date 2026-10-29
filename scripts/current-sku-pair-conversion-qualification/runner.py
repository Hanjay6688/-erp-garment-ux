"""Native component runner for an already installed exact SKU delta.

The calling qualifier owns full prerequisite admission, install/preuse inverse,
all-22/data/sequence/roles/advisor restoration and all five package gates.
Nothing here starts hosted work, browser Auth, a scheduler or a workflow.
"""
from pathlib import Path
import importlib.util,json
import psycopg
from cp7_sku_pair_conversion import composition as product
from cp7_p21_current_chain_rehearsal_probe import helper
from cp7_catalog_state import exact_public_catalog

HERE=Path(__file__).resolve().parent
LABEL='CP7_SKU_PAIR_CONVERSION_NATIVE7'

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def require_local(connection,cursor):
    assert connection.info.host in('localhost','127.0.0.1')and connection.info.port==54322,'SKU29_LOCAL_DISPOSABLE_ONLY'
    assert cursor.execute('select current_database()').fetchone()==('cp6_rollback',),'SKU29_DISPOSABLE_DATABASE_ONLY'

def exercise(conn,cur,database,url,report,state):
    business=load('sku29_actual_native_cases',HERE/'cases.py');control=helper.control;native=control.native
    require_local(conn,cur)
    if state['sources']!=product.sources():raise ValueError('SKU29_EXACT_CURRENT_INSTALLATION_REQUIRED')
    conn.rollback();cur.close();conn.close()
    def verify(cursor):
        with control.product_catalog(cursor):return product.verify(cursor,state)
    with exact_public_catalog(native,retain_raw=True)as public:
        actual=native.strict_group(LABEL,business.cases,verify)
    report.update(native=actual,public_catalog_observation=public,actual_Native_cases=0,
      actual_Auth_browser=False,actual_two_session_races=0,qualification_scope='NATIVE_COMPONENT_ONLY',
      full_manual_group_accessory_recovery_claim=False,production_go=False,independent_acceptance=False)
    assert actual.get('counts')=={'PASS':len(business.IDS)}and set(actual.get('cases',{}))==set(business.IDS),actual
    # One separate real commit makes the global used-data inverse guard
    # observable. Only the caller's complete dump restore may clean it up.
    with psycopg.connect(url)as connection,connection.cursor()as cursor:
        require_local(connection,cursor)
        if not cursor.execute('select count(*)from erp.app_users').fetchone()[0]:business.f.b.api.seed(cursor)
        today=cursor.execute("select(statement_timestamp()at time zone'Asia/Jakarta')::date").fetchone()[0]
        fixture=business.f.nonpo(cursor,today);payload,_=business.f.review(cursor,fixture['payload'])
        made=business.f.action(cursor,'POST',payload);connection.commit()
        with control.product_catalog(cursor):
            _,_,_,_,catalog=product.runtime();before=catalog._catalog_rows(cursor);data=catalog._data(cursor)
            try:product.rollback_delta_preuse(cursor,state)
            except ValueError as error:assert str(error)==product.USED_ERROR,str(error)
            else:raise AssertionError('SKU29_USED_INVERSE_NOT_REFUSED')
            assert catalog._catalog_rows(cursor)==before and catalog._data(cursor)==data
        connection.rollback()
    report.update(status='PASS',actual_Native_cases=len(business.IDS),used_guard_refused_before_DDL=True,
      committed_conversion_group_id=made['conversion_id'],failure_evidence_preserved=True,
      acceptance_requires_complete_outer_restore_and_package=True,new_cost_engine_created=False)
