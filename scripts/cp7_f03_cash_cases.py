"""Cash route qualification through the unchanged dated native report reader.

This prepares real journal/payment source facts in disposable databases only.
The new browser page reads; it does not acquire a cash/journal write privilege.
"""
from decimal import Decimal as D
import cp7_finance_analysis_cases as analysis

b=analysis.b

def fixture(cur,today):
    f=analysis.cash_fixture(cur,today)
    for _ in range(30):
        analysis.journal(cur,f['day'],[dict(account_id=f['coa1'],debit='1.25'),dict(mapping_key='OPENING_EQUITY',credit='1.25')],'CP7_CASH_PAGE_SOURCE')
    return f

def pages(cur,f):
    first=analysis.read(cur,f['query']);second=analysis.read(cur,dict(f['query'],offset=25,limit=25))
    return first,second

def check(cur,f,observed):
    first,second=observed;expected=pages(cur,f)
    for actual,native in zip(observed,expected):
        actual=dict(actual);native=dict(native);actual.pop('captured_at');native.pop('captured_at');assert actual==native
    assert [len(x['cash']['entries']['rows']) for x in observed]==[25,8]
    assert [x['cash']['entries']['next_offset'] for x in observed]==[25,None]
    assert all(x['cash']['entries']['total']=='33' for x in observed)
    rows=[row for page in observed for row in page['cash']['entries']['rows']]
    assert len({row['id'] for row in rows})==33
    # Fixed worksheet: native transfer1000 nets0, real receipt300/payment200,
    # plus30 actual capital journals of1.25. Totals never become page subtotals.
    before=f['before']['cash']
    for page in observed:
        cash=page['cash'];assert cash['reconciled']
        assert D(cash['debit'])-D(before['debit'])==D('1337.50')
        assert D(cash['credit'])-D(before['credit'])==D('1200.00')
        assert D(cash['net_change'])-D(before['net_change'])==D('137.50')
    transfer=next(row for row in rows if row['id']==str(f['transfer']));assert D(transfer['net'])==0
    return dict(status='PASS',source_count=33,pages=[25,8],cash_delta='137.50',debit_delta='1337.50',credit_delta='1200.00',transfer_net='0.00',native_and_public_source_rows_exact=True,complete_totals_on_both_pages=True)

def cases(cur,today):
    def full():
        f=fixture(cur,today);before=b.boundary.snapshot(cur);result=check(cur,f,pages(cur,f))
        assert b.boundary.snapshot(cur)==before
        return dict(result,read_only_full_boundary_exact=True)
    # The actual predecessor inverse/auth controls are repeated on this source,
    # not relabeled new financial policy or additional historic test coverage.
    old=dict(analysis.cases(cur,today))
    return [('F03_CASH_O14_COMPLETE_33_SOURCE_PAGES',full),
            ('F03_CASH_E13_LINKED_NATIVE_INVERSE_DATES',old['P13_ANALYSIS_INVERSE_DATES']),
            ('F03_CASH_CURRENT_AUTHORITY_NO_WRITE',old['P13_ANALYSIS_ACCESS'])]

def http_cases(http,today):
    def exact():
        owner=http.login('OWNER','f03-cash-owner')
        with http.connect() as conn,conn.cursor() as cur:
            f=fixture(cur,today);expected=pages(cur,f);before=b.boundary.snapshot(cur);conn.commit()
        observed=[]
        for offset in (0,25):
            response=owner.rpc('erp_cp7_get_finance_analysis_v1',dict(p_query=dict(f['query'],offset=offset,limit=25)))
            assert response['status']==200,response;observed.append(response['body'])
        with http.connect() as conn,conn.cursor() as cur:
            check(cur,f,observed);assert b.boundary.snapshot(cur)==before;conn.rollback()
        assert http.anon_rpc('erp_cp7_get_finance_analysis_v1',dict(p_query=f['query']))['status'] in (401,403)
        with http.connect() as conn,conn.cursor() as cur:
            cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
        assert owner.rpc('erp_cp7_get_finance_analysis_v1',dict(p_query=f['query']))['status']==403
        return dict(status='PASS',real_auth_33_complete_source_rows=True,read_changes_no_business_facts=True,anonymous_and_current_deactivation_denied=True,not_a_cash_write=True)
    return [('F03_CASH_REAL_HTTP_COMPLETE_SOURCE_AUTH',exact)]
