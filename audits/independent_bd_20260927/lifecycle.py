"""Independent invoice lifecycle through public RPCs, from our own opening import.

This is NOT ordinary laundry delivery/receipt or downstream product HPP coverage.
No writer fixtures/tests are executed. SQL readbacks independently inspect ledgers.
"""
import suite as s
import json,time,traceback,hashlib,threading
from decimal import Decimal as D
from concurrent.futures import ThreadPoolExecutor
from psycopg.types.json import Jsonb
import psycopg

C=s.CTX;R=s.RESULTS;E=s.EVENTS;admin=s.admin;eq=s.eq;cmd=s.command;uid=s.uid
def save():
    (s.OUT/'lifecycle-results.json').write_text(json.dumps({'candidate':'08065a3b4da71c51ffbbab77f0a6b1ac7e6638ec',
      'plan_sha256':hashlib.sha256((s.Path(__file__).parent/'PLAN.md').read_bytes()).hexdigest(),
      'scope':'Public native RPC: independently imported opening uninvoiced laundry, invoices, payments, corrections, concurrent posting',
      'limits':['not HTTP/browser','not ordinary physical delivery/receipt','not product WIP/FG/COGS reconciliation','not claims or returns','not release rollback'],
      'results':R,'production_go':False},indent=2,default=str)+'\n')
    (s.OUT/'lifecycle-events.json').write_text(json.dumps(E,indent=2,default=str)+'\n')
s.save=save
def imp(action,payload):
    req=uid();event={'api':'initial_import','action':action,'payload':payload,'request':req}
    try:
        with s.actor_conn() as c:r=c.execute('select public.erp_save_initial_import_action_v1(%s,%s,%s::uuid)',(action,Jsonb(payload),req)).fetchone()[0]
        event['response']=r;return r
    except psycopg.Error as e:event.update(error=str(e),sqlstate=e.sqlstate);raise
    finally:E.append(event)
def fingerprint(names):
    return {n:admin('select md5(coalesce(string_agg(to_jsonb(t)::text,\'\' order by to_jsonb(t)::text),\'\')) from erp.'+n+' t',one=True) for n in names}
PHYSICAL=['laundry_deliveries','laundry_delivery_lines','laundry_receipts','laundry_receipt_lines','fg_stock_movements','wip_stock_movements']
FINANCIAL=['journal_entries','journal_lines','vendor_invoices','vendor_payments']
BUSINESS=['bd_requests_v1','bd_laundry_invoices_v1','bd_laundry_invoice_lines_v1','bd_opening_laundry_uninvoiced_v1']
def refuse(fn,contains=None):
    before=fingerprint(FINANCIAL+PHYSICAL+BUSINESS)
    try:fn()
    except psycopg.Error as e:
        if e.sqlstate!='P0001':raise AssertionError('Unexpected SQL failure, not demonstrated domain refusal: '+str(e))
        if contains and contains.lower() not in str(e).lower():raise AssertionError('Wrong rejection: '+str(e))
        eq(fingerprint(FINANCIAL+PHYSICAL+BUSINESS),before,'Atomic rejected operation')
        return {'sqlstate':e.sqlstate,'message':str(e),'state_unchanged':before}
    raise AssertionError('Operation accepted; expected business refusal')
def read_invoice(i):return admin('select to_jsonb(i) from erp.bd_laundry_invoices_v1 i where id=%s',(i,),one=True)
def source(key):return C['sources'][key]
def line(key,qty,amount,kind='BILL'):
    return {'line_kind':kind,'opening_uninvoiced_id':source(key),'category':'GOOD','qty':qty,'amount':amount,'note':'Independent audit '+key}
def payload(name,lines,amount,vendor=None,**extra):
    return {'vendor_id':vendor or C['v1'],'invoice_number':'AUD-'+name,'invoice_date':'2026-09-21','header_total':amount,'lines':lines,**extra}
def draft(name,lines,amount,**extra):return cmd('SAVE_INVOICE_DRAFT',payload(name,lines,amount,**extra))
def post(d,request=None):return cmd('POST_INVOICE',{'invoice_id':d['invoice_id'],'expected_version':str(d['row_version'])},request)
def billed(key):
    return admin("select coalesce(sum(l.qty),0) from erp.bd_laundry_invoice_lines_v1 l join erp.bd_laundry_invoices_v1 i on i.id=l.invoice_id where i.status='POSTED' and l.line_kind='BILL' and l.opening_uninvoiced_id=%s",(source(key),),one=True)
def journal(jid):
    return admin('select account_id::text,sum(debit),sum(credit) from erp.journal_lines where journal_entry_id=%s group by account_id order by account_id',(jid,))
def assert_journal(jid,expected,date='2026-09-21'):
    got={a:(str(debit),str(credit)) for a,debit,credit in journal(jid)}
    eq({a:(D(x),D(y)) for a,(x,y) in got.items()},expected,'independent journal oracle')
    dates=admin('select transaction_date::text,economic_date::text,status from erp.journal_entries where id=%s',(jid,))[0]
    eq(dates,(date,date,'POSTED'),'economic and accounting dates')
    return {'journal_id':jid,'lines':got,'dates':dates}
def setup():
    C.update(json.loads((s.OUT/'fixture-identities.json').read_text()))
    available={n for n, in admin("select tablename from pg_tables where schemaname='erp'")}
    PHYSICAL[:]=[n for n in PHYSICAL if n in available]
    assert {'laundry_deliveries','laundry_receipts'}<=set(PHYSICAL)
    for key in ['AP_VENDOR','ACCRUED_MANUFACTURING']:
        C[key]=str(admin('select erp.account_id(%s)',(key,),one=True))
    C['expense']=str(admin("select id from erp.chart_accounts where account_type='EXPENSE' and is_postable and is_active order by account_code limit 1",one=True))
    b=imp('CREATE',{'batch_code':'AUD-INDEPENDENT-BD','cutover_date':'2026-09-19','notes':'Independent synthetic source documents'})
    C['batch']=b['batch_id']
    rows=[]
    for n,(key,qty,estimate) in enumerate([('A',13,'56174.17'),('RACE',9,'2007.81'),('REV',13,'56174.17'),('ATOMIC',13,'56174.17'),('UNKNOWN',13,'')],1):
        rows.append({'source_row_no':n,'payload':{'document_number':'AUD-SOURCE-'+key,'vendor_code':'AUD-CEDAR','receipt_date':'2026-09-15','category':'GOOD','qty':str(qty),'estimated_amount':estimate,'notes':'Independent fictitious source '+key}})
    b=imp('SAVE_FILE',{'batch_id':b['batch_id'],'expected_revision':b['revision'],'entity':'OPENING_LAUNDRY_UNINVOICED','filename':'independent-sources.csv','rows':rows})
    b=imp('VALIDATE',{'batch_id':b['batch_id'],'expected_revision':b['revision']})
    if b['error_rows']:
        raise AssertionError({'import_result':b,'validation':admin('select source_row_no,validation_status,validation_errors from erp.migration_staging_rows where batch_id=%s',(b['batch_id'],))})
    b=imp('FINALIZE',{'batch_id':b['batch_id'],'expected_revision':b['revision']});eq(b['status'],'POSTED')
    C['sources']={number.removeprefix('AUD-SOURCE-'):str(i) for i,number in admin('select id,document_number from erp.bd_opening_laundry_uninvoiced_v1 where batch_id=%s',(b['batch_id'],))}
    eq(len(C['sources']),5);C['physical_before']=fingerprint(PHYSICAL)
    (s.OUT/'lifecycle-fixture.json').write_text(json.dumps(C,indent=2,default=str)+'\n')
    return {'import':b,'sources':C['sources'],'physical_tables':PHYSICAL}
def draft_edit():
    before=fingerprint(FINANCIAL+PHYSICAL)
    a=draft('PART-7',[line('A',7,'1.00')],'1.00');C['draft_stale']=a
    b=draft('PART-7',[line('A',7,'31150.91')],'31150.91',invoice_id=a['invoice_id'],expected_version=a['row_version'])
    C['draft7']=b;eq(b['status'],'DRAFT');eq(b['journal_id'],None)
    eq(fingerprint(FINANCIAL+PHYSICAL),before,'Draft edit must not post ledger/physical facts')
    return {'first':a,'edited':b,'financial_physical_unchanged':before}
def set_policies():
    return [s.policy('LAU_DEC02',{'billable':['GOOD']}),s.policy('LAU_DEC06',{'variance_mode':'VARIANCE_ACCOUNT','after_payment':'CORRECTION_DOCUMENT','variance_account_id':C['expense']})]
def post_seven():
    C['post_request']=uid();C['posted7']=post(C['draft7'],C['post_request']);r=C['posted7'];eq(r['status'],'POSTED');eq(billed('A'),7)
    j=assert_journal(r['journal_id'],{C['AP_VENDOR']:(D(0),D('31150.91')),C['ACCRUED_MANUFACTURING']:(D('30247.63'),D(0)),C['expense']:(D('903.28'),D(0))})
    eq(fingerprint(PHYSICAL),C['physical_before']);return {'invoice':r,'journal':j}
def replay_post():
    before=fingerprint(FINANCIAL+PHYSICAL+BUSINESS);r=post(C['draft7'],C['post_request']);eq(r['invoice_id'],C['posted7']['invoice_id']);eq(fingerprint(FINANCIAL+PHYSICAL+BUSINESS),before)
    return {'response':r,'unchanged':before}
def post_six():
    d=draft('PART-6',[line('A',6,'26700.78')],'26700.78');r=post(d);C['posted6']=r
    eq(billed('A'),13)
    j=assert_journal(r['journal_id'],{C['AP_VENDOR']:(D(0),D('26700.78')),C['ACCRUED_MANUFACTURING']:(D('25926.54'),D(0)),C['expense']:(D('774.24'),D(0))})
    sums=admin("select sum(l.net_amount),sum(l.released_estimate),sum(l.variance) from erp.bd_laundry_invoice_lines_v1 l join erp.bd_laundry_invoices_v1 i on i.id=l.invoice_id where i.status='POSTED' and l.opening_uninvoiced_id=%s",(source('A'),))[0]
    eq(sums,(D('57851.69'),D('56174.17'),D('1677.52')))
    eq(fingerprint(PHYSICAL),C['physical_before']);return {'journal':j,'net_release_variance':sums}
def excess():
    d=draft('EXCESS',[line('A',1,'4450.13')],'4450.13');return refuse(lambda:post(d),'CAPACITY')
def atomic_capacity():
    d=draft('ATOMIC',[line('ATOMIC',7,'31150.91'),line('ATOMIC',7,'31150.91')],'62301.82')
    r=refuse(lambda:post(d),'CAPACITY');eq(billed('ATOMIC'),0);return r
def header_mismatch():
    d=draft('MISMATCH',[line('ATOMIC',7,'31150.91')],'31150.90');return refuse(lambda:post(d),'TOTAL_MISMATCH')
def race():
    ds=[draft('RACE-'+str(n),[line('RACE',9,'2007.81')],'2007.81') for n in (1,2)]
    barrier=threading.Barrier(2)
    def call(d):
        barrier.wait()
        try:return {'accepted':True,'response':post(d)}
        except psycopg.Error as e:return {'accepted':False,'error':str(e),'sqlstate':e.sqlstate}
    with ThreadPoolExecutor(max_workers=2) as ex:out=list(ex.map(call,ds))
    eq(sum(x['accepted'] for x in out),1);eq(billed('RACE'),9)
    loser=next(x for x in out if not x['accepted']);eq(loser['sqlstate'],'P0001');assert 'CAPACITY' in loser['error'],loser
    statuses=[read_invoice(d['invoice_id'])['status'] for d in ds];eq(sorted(statuses),['DRAFT','POSTED'])
    eq(fingerprint(PHYSICAL),C['physical_before']);return {'two_sessions':out,'states':statuses,'posted_qty':9}
def reversal():
    d=draft('REVERSE',[line('REV',13,'57851.69')],'57851.69');p=post(d);C['reverse_posted']=p
    original_lines=journal(p['journal_id']);r=cmd('REVERSE_INVOICE',{'invoice_id':p['invoice_id'],'expected_version':p['row_version'],'reason':'Independent unpaid reversal'})
    C['reversed']=r;eq(r['status'],'REVERSED');eq(billed('REV'),0)
    rev=admin('select id::text from erp.journal_entries where reversal_of_id=%s',(p['journal_id'],))
    eq(len(rev),1);eq(journal(p['journal_id']),original_lines,'Original journal lines retained')
    eq({a:(debit,credit) for a,debit,credit in journal(rev[0][0])},{a:(credit,debit) for a,debit,credit in original_lines})
    eq(fingerprint(PHYSICAL),C['physical_before']);return {'response':r,'original_lines':original_lines,'reversal_journal':rev}
def cash_id():
    rows=admin('select id::text from erp.cash_accounts where is_active order by cash_account_code limit 1')
    if not rows:raise AssertionError('Fixture missing active cash account; payment tests BLOCKED')
    return rows[0][0]
def payment(amount,name):
    p=C['posted7'];before=journal(p['journal_id']);phy=fingerprint(PHYSICAL)
    r=cmd('PAY_VENDOR_DOCUMENT',{'target_kind':'VENDOR_INVOICE','target_id':p['invoice_id'],'amount':amount,'date':'2026-09-22','cash_account_id':cash_id(),'reason':'Independent '+name})
    C[name]=r;eq(journal(p['journal_id']),before);eq(fingerprint(PHYSICAL),phy)
    jid=admin("select id::text from erp.journal_entries where source_type='VENDOR_PAYMENT' and source_id=%s and reversal_of_id is null",(r['payment_id'],),one=True)
    cash_coa=admin('select coa_account_id::text from erp.cash_accounts where id=%s',(cash_id(),),one=True)
    assert_journal(jid,{C['AP_VENDOR']:(D(amount),D(0)),cash_coa:(D(0),D(amount))},'2026-09-22')
    return r
def partial_payment():
    r=payment('10000.00','partial_payment');eq(D(r['remaining']),D('21150.91'));return r
def final_payment():
    r=payment('21150.91','final_payment');eq(D(r['remaining']),D(0));return r
def paid_reversal():
    p=read_invoice(C['posted7']['invoice_id']);return refuse(lambda:cmd('REVERSE_INVOICE',{'invoice_id':str(p['id']),'expected_version':str(p['row_version']),'reason':'Independent paid reversal attempt'}),'PAID')
def upward_correction():
    origin=read_invoice(C['posted7']['invoice_id']);before=fingerprint(['vendor_payments']);lines=journal(str(origin['journal_id']))
    d=draft('CORRECTION-UP',[line('A',0,'129.04','CORRECTION')],'129.04',corrects_invoice_id=str(origin['id']),invoice_date='2026-09-23')
    r=post(d);eq(r['corrects_invoice_id'],str(origin['id']));eq(billed('A'),13);eq(fingerprint(['vendor_payments']),before)
    eq(read_invoice(str(origin['id'])),origin,'Paid original immutable');eq(journal(str(origin['journal_id'])),lines)
    j=assert_journal(r['journal_id'],{C['AP_VENDOR']:(D(0),D('129.04')),C['expense']:(D('129.04'),D(0))},'2026-09-23')
    eq(fingerprint(PHYSICAL),C['physical_before']);return {'correction':r,'journal':j}
def unknown_import():
    u=admin('select estimated_amount,accrued_amount,accrual_journal_id from erp.bd_opening_laundry_uninvoiced_v1 where id=%s',(source('UNKNOWN'),))[0]
    eq(u,(None,D(0),None));return {'source':source('UNKNOWN'),'estimate_accrual_journal':u}
def future_invoice():
    d=draft('FUTURE',[line('ATOMIC',1,'4450.13')],'4450.13',invoice_date='2099-01-01');return refuse(lambda:post(d),'FUTURE')
def dependency_case(key,title,fn,needs=()):
    missing=[x for x in needs if x not in C]
    if missing:R.append({'id':key,'title':title,'status':'BLOCKED','dependency_missing':missing});save();return
    s.case(key,title,fn,'public SQL RPC + independent ledger readback')
def main():
    try:setup()
    except Exception as e:R.append({'id':'SETUP.LIFECYCLE','status':'BLOCKED','error':str(e),'traceback':traceback.format_exc()});save();raise
    dependency_case('IND-07.OPENING','Unknown opening estimate creates no fake zero-priced accrual',unknown_import)
    dependency_case('IND-13','Editable invoice draft has no financial/physical effects',draft_edit)
    dependency_case('IND-37.INVOICE','Unset billing policy refuses posting atomically',lambda:refuse(lambda:post(C['draft7']),'POLICY'),['draft7'])
    try:E.append({'synthetic_policy_setup':set_policies()})
    except Exception as e:R.append({'id':'SETUP.POLICY','status':'BLOCKED','error':str(e)});save();return 1
    dependency_case('IND-21','Stale draft cannot post old content',lambda:refuse(lambda:post(C['draft_stale']),'STALE_VERSION'),['draft_stale'])
    dependency_case('IND-14.SEVEN','First 7 PCS invoice releases estimate and posts exact payable',post_seven,['draft7'])
    dependency_case('IND-19.INVOICE','Identical posting replay creates no second effect',replay_post,['posted7'])
    dependency_case('IND-14.SIX','Remaining 6 PCS consumes capacity and reconciles 1677.52 variance',post_six,['posted7'])
    dependency_case('IND-15','Fourteenth billed piece refused atomically',excess,['posted6'])
    dependency_case('IND-17','Other vendor cannot invoice source',lambda:refuse(lambda:draft('OTHER-VENDOR',[line('ATOMIC',1,'4450.13')],'4450.13',vendor=C['v2']),'VENDOR'))
    dependency_case('IND-18.INVOICE','Valid first line plus excess second line rolls back wholly',atomic_capacity)
    dependency_case('IND-18.HEADER','One-cent header mismatch refused atomically',header_mismatch)
    dependency_case('IND-22','Two sessions invoice 9 PCS source; exactly one succeeds',race)
    dependency_case('IND-25','Unpaid reversal restores capacity and creates linked opposite journal',reversal)
    dependency_case('IND-27','Second invoice reversal refused without extra journal',lambda:refuse(lambda:cmd('REVERSE_INVOICE',{'invoice_id':C['reversed']['invoice_id'],'expected_version':C['reversed']['row_version'],'reason':'Independent duplicate reversal'})),['reversed'])
    dependency_case('IND-24.PARTIAL','Payment reduces payable by 10000, with no repeat cost',partial_payment,['posted7'])
    dependency_case('IND-24.FULL','Remaining payment clears original invoice',final_payment,['partial_payment'])
    dependency_case('IND-26.PAID','Paid invoice cannot be reversed in place',paid_reversal,['final_payment'])
    dependency_case('IND-26.CORRECTION','Separate upward correction preserves paid original',upward_correction,['final_payment'])
    dependency_case('IND-33.FUTURE','Future invoice refuses posting',future_invoice)
    save();print(json.dumps({'lifecycle_counts':{x:sum(r['status']==x for r in R) for x in ['PASS','FAIL','BLOCKED']}}),flush=True)
    return 1 if any(r['status']!='PASS' for r in R) else 0
if __name__=='__main__':raise SystemExit(main())
