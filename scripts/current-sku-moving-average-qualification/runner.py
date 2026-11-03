"""Actual Native component runner for the installed moving-average successor."""
from hashlib import sha256
from pathlib import Path
import importlib.util
import psycopg
from cp7_sku_moving_average import composition as product
from cp7_p21_current_chain_rehearsal_probe import helper
from cp7_catalog_state import exact_public_catalog

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
LABEL='CP7_SKU_MOVING_AVERAGE_NATIVE6'

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def require_local(connection,cursor):
    assert connection.info.host in('localhost','127.0.0.1')and connection.info.port==54322,'SKU_MOVAVG_LOCAL_DISPOSABLE_ONLY'
    assert cursor.execute('select current_database()').fetchone()==('cp6_rollback',),'SKU_MOVAVG_DISPOSABLE_DATABASE_ONLY'

def exercise(conn,cur,database,url,report,state):
    business=load('sku_movavg_actual_native_cases',ROOT/'scripts/cp7_sku_moving_average/qualification_cases.py')
    control=helper.control;native=control.native
    require_local(conn,cur)
    if state['sources']!=product.sources():raise ValueError('SKU_MOVAVG_EXACT_CURRENT_INSTALLATION_REQUIRED')
    conn.rollback();cur.close();conn.close()
    def verify(cursor):
        with control.product_catalog(cursor):return product.verify(cursor,state)
    try:
        with exact_public_catalog(native,retain_raw=True)as public:
            actual=native.strict_group(LABEL,business.cases,verify)
    finally:
        destination=ROOT/'cp6-proof/t3';destination.mkdir(parents=True,exist_ok=True);retained=[]
        for name in(LABEL+'.json',LABEL+'_BUSINESS_DAY_FIRST_ATTEMPT.json'):
            original=native.r1.OUT/name
            if original.is_file():
                raw=original.read_bytes();(destination/name).write_bytes(raw)
                retained.append(dict(name=name,bytes=len(raw),sha256=sha256(raw).hexdigest()))
        report['strict_group_originals']=retained
    report.update(native=actual,public_catalog_observation=public,actual_Native_cases=0,
      actual_Auth_browser=False,actual_two_session_races=0,qualification_scope='NATIVE_COMPONENT_ONLY',
      production_go=False,independent_acceptance=False)
    assert actual.get('counts')=={'PASS':len(business.IDS)}and set(actual.get('cases',{}))==set(business.IDS),actual
    with psycopg.connect(url)as connection,connection.cursor()as cursor:
        require_local(connection,cursor)
        if not cursor.execute('select count(*)from erp.app_users').fetchone()[0]:business.f.b.api.seed(cursor)
        today=cursor.execute("select(statement_timestamp()at time zone'Asia/Jakarta')::date").fetchone()[0]
        # The unchanged Native owner helper introspects erp.current_app_role.
        # Its temporary qualification-only usage never reaches committed copies.
        had_usage=cursor.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        if not had_usage:cursor.execute('grant usage on schema erp to authenticated')
        try:
            fixture=business.canonical(cursor,today);business.forward(cursor,fixture)
        finally:
            if connection.info.transaction_status!=psycopg.pq.TransactionStatus.INERROR:
                business.f.admin(cursor)
                if not had_usage:cursor.execute('revoke usage on schema erp from authenticated')
        product.verify(cursor,state);connection.commit()
        with control.product_catalog(cursor):
            _,_,_,_,catalog=product.runtime();before=catalog._catalog_rows(cursor);data=catalog._data(cursor)
            try:product.rollback_delta_preuse(cursor,state)
            except ValueError as error:assert str(error)==product.USED_ERROR,str(error)
            else:raise AssertionError('SKU_MOVAVG_USED_INVERSE_NOT_REFUSED')
            assert catalog._catalog_rows(cursor)==before and catalog._data(cursor)==data
        connection.rollback()
    report.update(status='PASS',actual_Native_cases=len(business.IDS),used_guard_refused_before_DDL=True,
      failure_evidence_preserved=True,acceptance_requires_complete_outer_restore_and_package=True,
      physical_FIFO_preserved=True,economic_valuation='SKU_LOCATION_GRADE_MOVING_AVERAGE')
