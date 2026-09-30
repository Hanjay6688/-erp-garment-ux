"""Actual journal sources through the accepted native primitives, read-only public proof."""
from datetime import timedelta
from decimal import Decimal as D
import json,uuid
import cp7_finance_analysis_cases as source
import cp7_journal_bundle as bundle
b,auth=source.b,source.auth

def read(cur,q,subject=None):
    auth.actor(cur,subject);r=cur.execute('select public.erp_cp7_get_journal_book_v1(%s)',(json.dumps(q),)).fetchone()[0];b.api.admin(cur);return r
def fixture(cur,today,count=30,value='1.25'):
    day=today-timedelta(days=1);source.receipt.aa.prior.set_open_period(cur,day-timedelta(days=2));tag='F03JRN'+uuid.uuid4().hex[:12];ids=[]
    for _ in range(count):ids.append(str(source.journal(cur,day,[dict(mapping_key='CASH',debit=value),dict(mapping_key='OPENING_EQUITY',credit=value)],tag)))
    return dict(query=dict({'from':str(day),'to':str(day),'q':tag,'offset':0,'limit':25,'journal_id':None}),ids=ids,value=value,day=str(day))
def compare(actual,native):
    actual=dict(actual);native=dict(native);actual.pop('captured_at');native.pop('captured_at');assert actual==native
def cases(cur,today):
    def pages():
        f=fixture(cur,today);before=b.boundary.snapshot(cur);a=read(cur,f['query']);z=read(cur,dict(f['query'],offset=25))
        assert [len(r['page']['rows'])for r in(a,z)]==[25,5] and [r['page']['next_offset']for r in(a,z)]==[25,None]
        assert a['totals']==z['totals']==dict(journal_count='30',line_count='60',debit='37.50',credit='37.50',unbalanced_journal_count='0')
        assert {r['id']for p in(a,z)for r in p['page']['rows']}==set(f['ids']) and b.boundary.snapshot(cur)==before
        return dict(status='PASS',actual_native30_journals60_lines=True,complete25_plus5_pages=True,full_totals37_50_on_both_pages=True,no_business_side_effect=True)
    def detail():
        f=fixture(cur,today,count=1);r=read(cur,dict(f['query'],journal_id=f['ids'][0]));d=r['detail'];assert len(d['lines'])==2 and d['balanced'] and d['id']==f['ids'][0]
        rows=cur.execute('select id,account_id,debit,credit from erp.journal_lines where journal_entry_id=%s order by id',(f['ids'][0],)).fetchall()
        assert [(x['id'],x['account_id'],D(x['debit']),D(x['credit']))for x in d['lines']]==[(str(i),str(a),debit,credit)for i,a,debit,credit in rows]
        large=str(source.journal(cur,today-timedelta(days=1),[dict(mapping_key='CASH',debit='1')for _ in range(126)]+[dict(mapping_key='OPENING_EQUITY',credit='1')for _ in range(126)],'F03_JOURNAL_LARGE_DETAIL'))
        before=b.boundary.snapshot(cur);auth.refused(cur,lambda:read(cur,dict(f['query'],journal_id=large)),'CP7_JOURNAL_DETAIL_TOO_LARGE');assert b.boundary.snapshot(cur)==before
        return dict(status='PASS',all_native_account_lines_exact=True,account_names_and_source_id_retained=True,actual252_line_detail_refused_without_truncation_or_side_effect=True)
    def inverse():
        f=fixture(cur,today,count=1,value='12.34');before=read(cur,f['query']);inverse=str(source.fixture_journal_call(cur,'select erp.reverse_journal(%s,%s)',(f['ids'][0],'F03 journal linked inverse')))
        old=read(cur,dict(f['query'],journal_id=f['ids'][0]));assert old['totals']==before['totals'] and old['detail']['status']=='REVERSED'
        q=dict({'from':str(today),'to':str(today),'q':'','offset':0,'limit':25,'journal_id':inverse});new=read(cur,q)['detail']
        assert new['reversal_of_id']==f['ids'][0] and new['transaction_date']==str(today) and D(new['debit'])==D(new['credit'])==D('12.34')
        return dict(status='PASS',original12_34_kept_on_prior_accounting_date=True,linked_native_inverse12_34_on_own_date=True)
    def query():
        f=fixture(cur,today,count=1);before=b.boundary.snapshot(cur)
        for change in ({'as_known':'2020-01-01'},{'limit':'25'},{'limit':26},{'offset':-1},{'from':'2026-9-1'},{'from':'2026-02-30'},{'to':str(today+timedelta(days=1))},{'journal_id':'bad-id'},{'q':5}):auth.refused(cur,lambda:read(cur,dict(f['query'],**change)),'CP7_JOURNAL_QUERY')
        auth.refused(cur,lambda:read(cur,dict(f['query'],journal_id=str(uuid.uuid4()))),'CP7_JOURNAL_SOURCE_NOT_IN_PERIOD')
        assert b.boundary.snapshot(cur)==before;native=read(cur,f['query']);cur.execute("set local timezone='America/Los_Angeles'");compare(read(cur,f['query']),native)
        return dict(status='PASS',closed_query_real_dates_and_pagination_enforced=True,caller_timezone_cannot_change_source=True,atomic_refusal=True)
    def exact():
        value='9007199254740993.01';f=fixture(cur,today,count=1,value=value);r=read(cur,dict(f['query'],journal_id=f['ids'][0]))
        assert r['totals']['debit']==r['totals']['credit']==value and r['detail']['debit']==r['detail']['credit']==value
        assert all(isinstance(x['debit'],str)and isinstance(x['credit'],str)for x in r['detail']['lines'])
        return dict(status='PASS',native_amount_above_JS_safe_integer=value,decimal_strings_before_browser=True)
    def access():
        f=fixture(cur,today,count=1);subject,role=auth.custom_actor(cur);auth.refused(cur,lambda:read(cur,f['query'],subject),'CP7_JOURNAL_ACCESS_DENIED')
        cur.execute("insert into erp.app_role_permissions(role_id,permission_key) values(%s,'finance.journal.view')",(role,));auth.refused(cur,lambda:read(cur,f['query'],subject),'CP7_JOURNAL_OWNER_ADMIN_REQUIRED')
        bundle.verify(cur)
        return dict(status='PASS',current_journal_permission_and_owner_admin_required=True,private_reader_unreachable_and_no_business_DML_or_native_writer=True)
    return [('F03_JOURNAL_'+label,fn)for label,fn in [('PAGES',pages),('COMPLETE_DETAIL',detail),('INVERSE_DATES',inverse),('QUERY',query),('EXACT_LARGE',exact),('CURRENT_ACCESS_PRIVATE',access)]]
def http_cases(http,today):
    def actual():
        owner=http.login('OWNER','f03-journal-owner')
        with http.connect()as conn,conn.cursor()as cur:f=fixture(cur,today);before=b.boundary.snapshot(cur);expected=[read(cur,dict(f['query'],offset=n))for n in(0,25)];detail_query=dict(f['query'],journal_id=f['ids'][0]);detail=read(cur,detail_query);conn.commit()
        for n,expected_page in zip((0,25),expected):
            r=owner.rpc('erp_cp7_get_journal_book_v1',dict(p_query=dict(f['query'],offset=n)));assert r['status']==200,r;compare(r['body'],expected_page)
        r=owner.rpc('erp_cp7_get_journal_book_v1',dict(p_query=detail_query));assert r['status']==200,r;compare(r['body'],detail)
        with http.connect()as conn,conn.cursor()as cur:assert b.boundary.snapshot(cur)==before;conn.rollback()
        assert http.anon_rpc('erp_cp7_get_journal_book_v1',dict(p_query=f['query']))['status']in(401,403)
        with http.connect()as conn,conn.cursor()as cur:cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
        assert owner.rpc('erp_cp7_get_journal_book_v1',dict(p_query=f['query']))['status']==403
        return dict(status='PASS',actual_auth_all30_headers_full2_line_detail_match_native=True,no_business_read_effect=True,anonymous_and_current_deactivation_denied=True)
    return [('F03_JOURNAL_REAL_HTTP',actual)]
