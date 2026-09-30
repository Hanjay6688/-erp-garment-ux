"""Actual disposable native cash sources; no hosted runtime target allowed."""
from datetime import date
from urllib.parse import urlparse
import json,os,sys
import psycopg
import cp7_f03_cash_cases as cases

def main():
    target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
    assert url.hostname in ('localhost','127.0.0.1') and url.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
    op,p=sys.argv[1],json.load(sys.stdin)
    with psycopg.connect(target) as conn,conn.cursor() as cur:
        had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
        if not had:cur.execute('grant usage on schema erp to authenticated')
        if op=='prepare':
            f=cases.fixture(cur,date.fromisoformat(p['today']));out=dict(query=f['query'],expected=cases.pages(cur,f),transfer=str(f['transfer']),before=f['before'])
        elif op=='read':out=dict(pages=[cases.analysis.read(cur,dict(p['query'],offset=offset,limit=25)) for offset in (0,25)])
        elif op in ('report-read','report-verify'):
            q=p['dates']
            native=cases.analysis.finance.read(cur,date.fromisoformat(q['as_of']),**{'from':q['from'],'to':q['to'],'filing_id':None,'offset':0,'limit':25})
            if op=='report-verify':
                actual=dict(p['report']);expected=dict(native);actual.pop('captured_at');expected.pop('captured_at');assert actual==expected
                out=dict(status='PASS',complete_finance_report_matches_native=True)
            else:out=dict(report=native)
        elif op=='verify-pages':
            # Exact native response comparison includes every journal/source,
            # signed cent, economic/accounting date and linked inverse identity.
            expected=[cases.analysis.read(cur,dict(p['query'],offset=offset,limit=25)) for offset in (0,25)]
            for actual,native in zip(p['pages'],expected):
                actual=dict(actual);native=dict(native);actual.pop('captured_at');native.pop('captured_at');assert actual==native
            assert len(p['pages'])==2 and [len(x['cash']['entries']['rows']) for x in p['pages']]==[25,8]
            assert len({row['id'] for x in p['pages'] for row in x['cash']['entries']['rows']})==33
            out=dict(status='PASS',all_33_source_rows_exact=True)
        elif op=='revoke':
            role=cur.execute("select id from erp.app_roles where role_code='ADMIN'").fetchone()[0]
            cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.reports.view'",(role,))
            out=dict(status='PASS',report_permission_revoked=True)
        else:raise ValueError('Unknown cash fixture operation')
        cases.b.api.admin(cur)
        if not had:cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl
        conn.commit()
    print(json.dumps(out,default=str))
if __name__=='__main__':main()
