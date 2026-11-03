"""Native money callbacks with complete census, sequence prefixes and used guard."""
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
import importlib.util
import json
import psycopg
from cp7_sku_cost_components import composition as product
from cp7_p21_current_chain_rehearsal_probe import helper
from cp7_catalog_state import exact_public_catalog

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
LABEL='CP7_SKU_COST_MONEY_NATIVE19'

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def require_local(connection,cursor):
    assert connection.info.host in('localhost','127.0.0.1')and connection.info.port==54322,'SKU_MONEY_LOCAL_DISPOSABLE_ONLY'
    assert cursor.execute('select current_database()').fetchone()==('cp6_rollback',),'SKU_MONEY_DISPOSABLE_DATABASE_ONLY'

def boundary(cursor,business):
    captured=business.n.capture(cursor)
    return dict(catalog=captured['catalog'],data=captured['data_and_sequences'])

def exercise(conn,cur,database,url,report,state):
    business=load('sku_money_actual_native_cases',HERE/'native_cases.py')
    preflight=load('sku_money_all_native_prerequisites',HERE/'native_preflight.py')
    prefix=load('sku_money_original_complete_sequence_prefix',ROOT/'scripts/current-sku-managed-recovery-native27-qualification/sequence_prefix.py')
    control=helper.control;native=control.native
    require_local(conn,cur)
    if state['sources']!=product.sources():raise ValueError('SKU_MONEY_EXACT_CURRENT_INSTALLATION_REQUIRED')
    with control.product_catalog(cur):before=boundary(cur,business)
    conn.rollback();cur.close();conn.close()
    def verify(cursor):
        with control.product_catalog(cursor):return product.verify(cursor,state)
    def selected(cursor,today):
        report['native_prerequisites']=preflight.check(cursor,today,business)
        destination=ROOT/'cp6-proof/t3';destination.mkdir(parents=True,exist_ok=True)
        (destination/(LABEL+'_PREFLIGHT.json')).write_text(json.dumps(report['native_prerequisites'],indent=2,default=str)+'\n')
        operations=business.cases(cursor,today)
        assert tuple(key for key,_ in operations)==business.IDS
        return prefix.wrap(operations,SimpleNamespace(capture_current=lambda:business.n.capture(cursor)))
    try:
        with exact_public_catalog(native,retain_raw=True)as public:
            actual=native.strict_group(LABEL,selected,verify)
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
    assert actual.get('status')=='PASS'and actual.get('counts')=={'PASS':len(business.IDS)}and set(actual.get('cases',{}))==set(business.IDS),actual
    with psycopg.connect(url)as connection,connection.cursor()as cursor:
        require_local(connection,cursor)
        with control.product_catalog(cursor):after=boundary(cursor,business)
        report['all22_rows_and_sequence_prefix']=prefix.strict_rollback(before,after)
        chain=prefix.sequences(before['data'])
        for key in business.IDS:
            receipt=actual['cases'][key]['complete_case_sequence_prefix']
            assert receipt['before']==chain,('SKU_MONEY_UNATTRIBUTED_SEQUENCE_BEFORE_CASE',key)
            chain=receipt['after']
        assert chain==prefix.sequences(after['data']),'SKU_MONEY_UNATTRIBUTED_SEQUENCE_AFTER_CASES'
        if not cursor.execute('select count(*)from erp.app_users').fetchone()[0]:business.f.b.api.seed(cursor)
        today=cursor.execute("select(statement_timestamp()at time zone'Asia/Jakarta')::date").fetchone()[0]
        had_usage=cursor.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        if not had_usage:cursor.execute('grant usage on schema erp to authenticated')
        try:
            # Commit a used legacy child as well as its parent before testing the
            # global pre-use guard. Only the outer full backup may remove them.
            fixture=business.canonical(cursor,today)
            business.legacy_post(cursor,fixture,'CONVERTED')
        finally:
            if connection.info.transaction_status!=psycopg.pq.TransactionStatus.INERROR:
                business.f.admin(cursor)
                if not had_usage:cursor.execute('revoke usage on schema erp from authenticated')
        product.verify(cursor,state);connection.commit()
        with control.product_catalog(cursor):
            _,_,_,_,catalog=product.runtime();before_used=catalog._catalog_rows(cursor);data=catalog._data(cursor)
            try:product.rollback_delta_preuse(cursor,state)
            except ValueError as error:assert str(error)==product.USED_ERROR,str(error)
            else:raise AssertionError('SKU_MONEY_USED_INVERSE_NOT_REFUSED')
            assert catalog._catalog_rows(cursor)==before_used and catalog._data(cursor)==data
        connection.rollback()
    report.update(status='PASS',actual_Native_cases=len(business.IDS),used_guard_refused_before_DDL=True,
        failure_evidence_preserved=True,acceptance_requires_complete_outer_restore_and_package=True,
        full_sequence_restore_owned_by='COMPLETE_OUTER_BACKUP_AND_ALL_FIVE_PACKAGE_GATES',
        physical_FIFO_preserved=True,economic_valuation='SKU_LOCATION_GRADE_MOVING_AVERAGE_WITH_SOURCE_CENTS')
