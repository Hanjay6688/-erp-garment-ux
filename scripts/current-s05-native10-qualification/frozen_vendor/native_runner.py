"""Existing Native strict runner + real committed used-inverse witness."""
from pathlib import Path
import psycopg
from cp7_vendor_receivable import cases as business,composition as product
from cp7_p21_current_chain_rehearsal_probe import helper
from cp7_catalog_state import exact_public_catalog
CASE='VENDOR_RECEIVABLE_NATIVE7_AND_USED_INVERSE'

def scheduler_quiet(url):
    module=product.parent().load('vendor_parent_scheduler_quiet',product.ROOT/'scripts/current-factory-initial-stage/factory.py')
    return module.scheduler_quiet(url)

def exercise(conn,cur,database,url,report,state):
    control=helper.control;native=control.native
    conn.rollback();cur.close();conn.close()
    def verify(cursor):
        with control.product_catalog(cursor):return product.verify(cursor,state)
    with exact_public_catalog(native,retain_raw=True)as public:
        actual=native.strict_group('CP7_VENDOR_RECEIVABLE_NATIVE7_CASES',business.cases,verify)
    report.update(native=actual,public_catalog_observation=public,actual_Native_cases=7,actual_Auth_browser=False,actual_two_session_races=0)
    assert actual.get('counts')=={'PASS':7}and set(actual.get('cases',{}))==set(business.IDS),actual
    # A separate real commit proves that uninstall cannot erase used money.
    with psycopg.connect(url)as connection,connection.cursor()as cursor:
        if not cursor.execute('select count(*)from erp.app_users').fetchone()[0]:business.bd.api.seed(cursor)
        cursor.execute('grant usage on schema erp to authenticated')  # harness only; isolated by product_catalog
        today=cursor.execute("select(statement_timestamp()at time zone'Asia/Jakarta')::date").fetchone()[0]
        f=business.fixture(cursor,today);c=business.correction(cursor,f)
        refund=business.refund(cursor,f,c['invoice_id']);connection.commit()
        with control.product_catalog(cursor):
            _,_,_,_,catalog=product.runtime();before=catalog._catalog_rows(cursor);data=catalog._data(cursor)
            try:product.rollback_delta_preuse(cursor,state)
            except ValueError as error:assert str(error)==product.USED_ERROR,str(error)
            else:raise AssertionError('VENDOR_USED_INVERSE_NOT_REFUSED')
            assert catalog._catalog_rows(cursor)==before and catalog._data(cursor)==data
        connection.rollback()
    report.update(status='PASS',used_guard_refused_before_DDL=True,committed_refund_id=refund['refund_id'],
        failure_evidence_preserved=True,new_engine_created=False,production_go=False,independent_acceptance=False)
