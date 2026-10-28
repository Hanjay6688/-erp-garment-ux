"""Reuse strict committed-copy race/HTTP modes; never run a browser here."""
from pathlib import Path
from types import SimpleNamespace
import importlib.util
import cp6_auditor_modes as modes
from cp7_vendor_receivable import composition as product

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
CASE='VENDOR_RECEIVABLE_RACES3_AUTH_HTTP1'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def scheduler_quiet(url):
    return load('vendor_followup_scheduler',ROOT/'scripts/current-factory-initial-stage/factory.py').scheduler_quiet(url)


def exercise(conn,cur,database,url,report,state):
    from cp7_p21_current_chain_rehearsal_probe import helper
    control=helper.control
    business=load('vendor_followup_cases',HERE/'cases.py')
    _,_,_,_,catalog=product.runtime()
    race_copy=load('vendor_followup_race_copy',ROOT/'scripts/ow04-payment-current-races-qualification/copy_authority.py')
    http_copy=load('vendor_followup_http_copy',ROOT/'scripts/ow04-payment-current-qualification/copy_authority.py')
    original_copy=modes.copy_db
    for adapter in (race_copy,http_copy):
        adapter.ORIGINAL_COPY_DATABASE=original_copy
        adapter.PRODUCT=SimpleNamespace(catalog=catalog,verify=product.verify)
        adapter.STATE=dict(state,installed_catalog=state['after'])

    def verify(cursor):
        with control.product_catalog(cursor):return product.verify(cursor,state)

    def used_witness(connection):
        with connection.cursor()as cursor,control.product_catalog(cursor):
            before=catalog._catalog_rows(cursor);data=catalog._data(cursor)
            try:product.rollback_delta_preuse(cursor,state)
            except ValueError as error:assert str(error)==product.USED_ERROR,str(error)
            else:raise AssertionError('VENDOR_USED_INVERSE_NOT_REFUSED')
            assert catalog._catalog_rows(cursor)==before and catalog._data(cursor)==data
        connection.rollback()

    class Selected:
        @staticmethod
        def races(tools,today):
            def run(operation):
                result=operation()
                with tools.connect()as connection:used_witness(connection)
                return dict(result,used_guard_refused_before_DDL=True)
            return [(name,lambda op=operation:run(op))for name,operation in business.races(tools,today)]

        @staticmethod
        def http_cases(http,today):
            def run(operation):
                result=operation()
                with http.connect()as connection:used_witness(connection)
                return dict(result,used_guard_refused_before_DDL=True)
            return [(name,lambda op=operation:run(op))for name,operation in business.http_cases(http,today)]

    def copy(name):
        if name=='cp6_auditor_race':return race_copy.copy_database(name)
        if name=='cp6_auditor_http':return http_copy.copy_database(name)
        raise ValueError('VENDOR_FOLLOWUP_UNDECLARED_COPY_DATABASE')

    # Do not leave this wrapper's own source connection blocking TEMPLATE.
    conn.rollback();cur.close();conn.close()
    try:
        modes.copy_db=copy
        report['races']=modes.run_races(Selected,verify,'vendor_receivable3')
        report['http']=modes.run_http(Selected,verify,'vendor_receivable1')
    finally:
        modes.copy_db=original_copy
        report['copy_catalog_admissions']=dict(races=list(race_copy.COPY_ADMISSIONS),http=list(http_copy.COPY_ADMISSIONS))
    races,http=report['races'],report['http']
    assert races.get('counts')=={'PASS':3}and set(races.get('races',{}))==set(business.RACE_IDS),races
    assert http.get('counts')=={'PASS':1}and set(http.get('cases',{}))==set(business.HTTP_IDS),http
    for group,rows in ((races,races['races']),(http,http['cases'])):
        assert group['database_remaining']==0 and not group.get('cleanup_failures'),group
        assert all(v['status']=='PASS'and not v['session_leaks']and v['used_guard_refused_before_DDL']is True for v in rows.values()),rows
    assert http['auth_counts']['restored']is True and http['real_auth']is True,http
    assert len(race_copy.COPY_ADMISSIONS)==3 and len(http_copy.COPY_ADMISSIONS)==1
    assert all(v['all22_groups_equal_original_install']is True for v in race_copy.COPY_ADMISSIONS+http_copy.COPY_ADMISSIONS)
    report.update(status='PASS',used_guard_refused_before_DDL=True,actual_two_session_races=3,
        actual_Auth_HTTP_cases=1,actual_Native_cases=0,retained_Native_cases=7,
        actual_browser_cases=0,real_Auth_browser_claim=False,production_go=False,independent_acceptance=False)
