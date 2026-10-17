"""R3-03 (owner D16-1, "selesain biar gausa sembunyiin"): Riwayat Pelanggan reads real data.

Native, race and real-Auth HTTP cases for scripts/cp7-src/sales/customer-history.sql (cp7_customer_history_bundle.py),
spliced into the CP17 harness through cp7_r3_cases.py. The fixture is built only with the accepted writers: a posted
invoice of 4 pcs x Rp20 (Native erp.save_sale_draft_v2 + erp.post_sale_v2), a payment of Rp30 and a return of 1 pc for
Rp20 through the Penjualan command (erp_cp7_save_sale_v1, Native erp.post_sales_payment / erp.post_sales_return), and a
second draft of the same customer cancelled through Native erp.cancel_sale_draft_v2. The oracle reads the Native rows
(erp.sales_headers, sales_items, sales_payments, sales_returns, sales_return_items, and erp.audit_logs for when a document
was cancelled) and does every sum in Python; it never takes the facade's own answer as the truth. The invoice figures are
also compared with the receivables reader (erp_cp7_get_sales_v1), so both screens show the same numbers.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta,timezone
from decimal import Decimal as D
import json,re,time,uuid
import psycopg
import cp7_snapshot_cases as auth
import cp7_master_cases as master
import cp7_sales_return_cases as returns
payments,cmd,source=returns.payments,returns.cmd,returns.source
b=auth.b
refused=auth.refused

FUNCTIONS=('erp_cp7_get_customer_history_v1',)
NATIVE=['CP17_R3_03_HISTORY_EVENTS_AND_BALANCES_EQUAL_NATIVE','CP17_R3_03_HISTORY_REVERSALS_LISTED_NOT_COUNTED',
        'CP17_R3_03_HISTORY_AMOUNTS_HIDDEN_WITHOUT_AR','CP17_R3_03_HISTORY_DENIED_WITHOUT_VIEW',
        'CP17_R3_03_HISTORY_TIMELINE_PAGING','CP17_R3_03_HISTORY_LIST_SEARCH_PAGING','CP17_R3_03_HISTORY_QUERY_REFUSALS',
        'CP17_R3_03_HISTORY_FACADE_PRIVATE_READ_ONLY']
RACES=['CP17_RACE_R3_03_HISTORY_PAYMENT_DURING_READ_ONE_SNAPSHOT']
HTTP=['CP17_HTTP_R3_03_HISTORY_OWNER_AND_SALES_KASIR']
BROWSER=['CP17_BROWSER_R3_03_HISTORY_DESKTOP','CP17_BROWSER_R3_03_HISTORY_MOBILE']
WIB=timezone(timedelta(hours=7))
ACTIVE=('POSTED','PARTIAL_PAID','PAID')
RANK=dict(INVOICE=1,PAYMENT=2,RETURN=3,CANCELLATION=4)
TABLE=dict(INVOICE='sales_headers',PAYMENT='sales_payments',RETURN='sales_returns')
MONEY=re.compile(r'^-?(0|[1-9][0-9]*)\.[0-9]{2}$')

def one(cur,sql,args=()):return cur.execute(sql,args).fetchone()[0]
def read(cur,query,subject=None,role='authenticated'):
    """The public facade as an Auth subject (default: the fixture OWNER)."""
    auth.actor(cur,subject,role);r=one(cur,'select public.erp_cp7_get_customer_history_v1(%s)',(json.dumps(query),));b.api.admin(cur);return r
def money(text):
    assert isinstance(text,str) and MONEY.match(text),('CP17_R3_03_MONEY_TEXT',text)
    return D(text)

def fixture(cur,today,tag=None):
    """A posted invoice 4 pcs x Rp20 = Rp80 of its own customer (Native draft + post), its bank and return destination."""
    f=source.fixture(cur,today,tag=tag or 'R303-'+uuid.uuid4().hex[:10]);source.fg.post_sale(cur,f['draft']);b.api.admin(cur)
    f['destination']=returns.location(cur,'CP17 R3-03 retur');f['bank']=str(source.bc.bank_account(cur,'R303'+uuid.uuid4().hex[:8]))
    f['allocations']=returns.read(cur,f)['page']['rows'];b.api.admin(cur)
    return f
def second_draft(cur,f,minutes=5,qty=2):
    """Another draft of the same customer (Native erp.save_sale_draft_v2), qty x Rp20."""
    d=b.chain.production.rpc(cur,'erp.save_sale_draft_v2',dict(sale_number=f['tag']+'-D2',customer_id=f['customer'],source_location_id=f['location'],
        sale_date=(source.fg.ax.r1.now(cur)-timedelta(minutes=minutes)).isoformat(),reason='CP17 R3-03 draft of the same customer',
        items=[dict(product_id=f['product'],qty_pcs=qty,unit_price_snapshot='20',discount_amount='0')]),uuid.uuid4(),None)
    b.api.admin(cur);return d
def scenario(cur,today,tag=None):
    """Owner D16-1 oracle fixture: invoice Rp80, payment Rp30, return 1 pc Rp20, a second draft of the customer cancelled."""
    f=fixture(cur,today,tag)
    f['payment']=payments.pay(cur,f,'30')['payment_id']
    f['return']=returns.returned(cur,f,qty='1',refund='20')['return_id']
    d=second_draft(cur,f);source.fg.cancel(cur,d);b.api.admin(cur)
    f['draft2']=d['sale_id'];f['draft2_number']=f['tag']+'-D2'
    return f

def native(cur,customer):
    """The customer's documents straight from the Native tables; every total is summed here, the order is built here."""
    b.api.admin(cur)
    heads={}
    for ident,number,at,status,location in cur.execute("""select h.id::text,h.sale_number,h.sale_date,h.status,l.location_name from erp.sales_headers h
            left join erp.locations l on l.id=h.source_location_id where h.customer_id=%s""",(customer,)).fetchall():
        heads[ident]=dict(number=number,at=at,status=status,location=location,gross=D(0),qty=0,returned=D(0),paid=D(0))
    ids=list(heads)
    for sale,qty,price,discount in cur.execute('select sale_id::text,qty_pcs,unit_price_snapshot,discount_amount from erp.sales_items where sale_id=any(%s::uuid[])',(ids,)).fetchall():
        heads[sale]['gross']+=D(qty)*D(price)-D(discount);heads[sale]['qty']+=qty
    pays=[dict(id=i,sale=s,number=n,at=at,amount=D(a),status=st,method=m) for i,s,n,at,a,st,m in cur.execute(
        'select id::text,sale_id::text,payment_number,payment_date,amount,status,payment_method from erp.sales_payments where sale_id=any(%s::uuid[])',(ids,)).fetchall()]
    rets=[dict(id=i,sale=s,number=n,at=at,status=st,refund=D(0),qty=0) for i,s,n,at,st in cur.execute(
        'select id::text,sale_id::text,return_number,physical_at,status from erp.sales_returns where sale_id=any(%s::uuid[])',(ids,)).fetchall()]
    by_id={r['id']:r for r in rets}
    for ret,qty,refund in cur.execute('select return_id::text,qty_pcs,refund_amount from erp.sales_return_items where return_id=any(%s::uuid[])',(list(by_id),)).fetchall():
        by_id[ret]['qty']+=qty;by_id[ret]['refund']+=D(refund)
    for p in pays:
        if p['status']=='POSTED':heads[p['sale']]['paid']+=p['amount']
    for r in rets:
        if r['status']=='POSTED':heads[r['sale']]['returned']+=r['refund']
    for h in heads.values():
        h['net']=max(h['gross']-h['returned'],D(0));h['open']=h['net']-h['paid'] if h['status'] in ACTIVE else None
    def ended(kind,ident,status):
        # Native audit log: the status change to CANCELLED / REVERSED written by erp.audit_row_change.
        return one(cur,"""select min(changed_at) from erp.audit_logs where entity_type=%s and entity_id=%s and action='UPDATE'
            and new_data->>'status'=%s""",(TABLE[kind],ident,status))
    events=[]
    def add(kind,doc,ident,number,at,invoice,status,qty,amount,location=None,method=None):
        events.append(dict(kind=kind,document=doc,document_id=ident,number=number,at=at,invoice_id=invoice,invoice_number=heads[invoice]['number'],
                           status=status,qty=qty,amount=amount,location=location,method=method))
    for ident,h in heads.items():
        add('INVOICE','INVOICE',ident,h['number'],h['at'],ident,h['status'],h['qty'],h['gross'],h['location'])
        if h['status'] in('CANCELLED','REVERSED'):
            add('CANCELLATION','INVOICE',ident,h['number'],ended('INVOICE',ident,h['status']),ident,h['status'],h['qty'],h['gross'],h['location'])
    for p in pays:
        add('PAYMENT','PAYMENT',p['id'],p['number'],p['at'],p['sale'],p['status'],None,p['amount'],method=p['method'])
        if p['status']=='REVERSED':add('CANCELLATION','PAYMENT',p['id'],p['number'],ended('PAYMENT',p['id'],'REVERSED'),p['sale'],p['status'],None,p['amount'],method=p['method'])
    for r in rets:
        add('RETURN','RETURN',r['id'],r['number'],r['at'],r['sale'],r['status'],r['qty'],r['refund'])
        if r['status']=='REVERSED':add('CANCELLATION','RETURN',r['id'],r['number'],ended('RETURN',r['id'],'REVERSED'),r['sale'],r['status'],r['qty'],r['refund'])
    assert all(e['at'] is not None for e in events),('CP17_R3_03_NATIVE_CANCELLATION_TIME_MISSING',events)
    # Newest first; same time: cancellation, return, payment, invoice; then the document id.
    events.sort(key=lambda e:e['document_id']);events.sort(key=lambda e:RANK[e['kind']],reverse=True);events.sort(key=lambda e:e['at'],reverse=True)
    active=[h for h in heads.values() if h['status'] in ACTIVE]
    totals=dict(active=len(active),gross=sum((h['gross'] for h in active),D(0)),returned=sum((h['returned'] for h in active),D(0)),
                net=sum((h['net'] for h in active),D(0)),paid=sum((h['paid'] for h in active),D(0)),open=sum((h['open'] for h in active),D(0)))
    counts=dict(invoices=len(heads),payments=len(pays),returns=len(rets),cancellations=sum(1 for e in events if e['kind']=='CANCELLATION'))
    return dict(invoices=heads,events=events,totals=totals,counts=counts)

def same_events(rows,oracle,financial):
    """The facade's timeline rows equal the oracle's events one by one (kind, document, time, WIB date, status, pieces, money)."""
    assert len(rows)==len(oracle),(len(rows),len(oracle))
    for row,e in zip(rows,oracle):
        assert (row['kind'],row['document'],row['document_id'],row['number'],row['invoice_id'],row['invoice_number'],row['status'])==(
            e['kind'],e['document'],e['document_id'],e['number'],e['invoice_id'],e['invoice_number'],e['status']),(row,e)
        assert row['id']==e['kind']+':'+e['document_id'] and datetime.fromisoformat(row['at'])==e['at'],(row,e)
        assert row['wib_date']==e['at'].astimezone(WIB).date().isoformat(),(row,e)
        assert row['qty_pcs']==(None if e['qty'] is None else str(e['qty'])) and row['method']==e['method'] and row['location_name']==e['location'],(row,e)
        if financial:assert money(row['financial']['amount'])==e['amount'],(row,e)
        else:assert 'financial' not in row,row
    return True
def same_invoices(page,oracle,financial):
    """The invoices named on the page, once each, with the oracle's status and figures."""
    named=sorted({r['invoice_id'] for r in page['timeline']['rows']});named.sort(key=lambda i:oracle[i]['at'],reverse=True)
    assert [i['id'] for i in page['invoices']]==named,(named,page['invoices'])  # newest invoice first, then the id
    for i in page['invoices']:
        h=oracle[i['id']]
        assert (i['number'],i['status'],datetime.fromisoformat(i['physical_at']),i['qty_pcs'])==(h['number'],h['status'],h['at'],str(h['qty'])),(i,h)
        if not financial:assert 'financial' not in i,i;continue
        x=i['financial']
        assert x['basis']=='CURRENT_NATIVE_DOCUMENT' and x['state']==('ACTIVE_RECEIVABLE' if h['status'] in ACTIVE else 'DRAFT_PREVIEW' if h['status']=='DRAFT' else 'INACTIVE_DOCUMENT'),(x,h)
        assert [money(x[k]) for k in('gross_total','return_total','net_total','paid_total')]==[h['gross'],h['returned'],h['net'],h['paid']],(x,h)
        assert (x['open_balance'] is None)==(h['open'] is None) and(h['open'] is None or money(x['open_balance'])==h['open']),(x,h)
    return True
def same_customer(c,oracle,financial):
    assert c['counts']=={k:str(v) for k,v in oracle['counts'].items()},(c['counts'],oracle['counts'])
    if not financial:assert 'financial' not in c,c;return True
    t=c['financial'];o=oracle['totals']
    assert t['basis']=='CURRENT_NATIVE_DOCUMENT' and t['active_invoices']==str(o['active']),t
    assert [money(t[k]) for k in('invoice_total','return_total','net_total','paid_total','open_balance')]==[o['gross'],o['returned'],o['net'],o['paid'],o['open']],(t,o)
    return True
def no_money(answer):
    """No amount anywhere in the answer (only the flag financial_captured=false)."""
    text=json.dumps(answer)
    for key in('"financial":','"amount"','"open_balance"','"gross_total"','"paid_total"','"invoice_total"'):assert key not in text,(key,text[:400])
    assert answer['financial_captured'] is False,answer
    return True


def cases(cur,today):
    import cp7_cp17_fix_cases as c
    def events_and_balances():
        f=scenario(cur,today);oracle=native(cur,f['customer'])
        before=b.boundary.snapshot(cur);w=read(cur,dict(customer_id=f['customer']))
        c.unchanged(cur,before,'customer history read')
        assert (w['contract_version'],w['mode'],w['read_only'],w['business_DML'],w['financial_captured'],w['can_export'])==('cp7.customer-history.v1','CUSTOMER',True,False,True,True),w
        rows=w['timeline']['rows']
        # Exactly those events, newest first: the draft's cancellation, the return, the payment, the draft, the invoice.
        assert [(r['kind'],r['document_id']) for r in rows]==[('CANCELLATION',f['draft2']),('RETURN',f['return']),('PAYMENT',f['payment']),
                                                              ('INVOICE',f['draft2']),('INVOICE',f['sale'])],rows
        assert (w['timeline']['total'],w['timeline']['next_offset'])==('5',None)
        same_events(rows,oracle['events'],True);same_invoices(w,oracle['invoices'],True);same_customer(w['customer'],oracle,True)
        # The literal oracle of the fixture: 80 - 20 = 60 net, 30 paid, 30 open; the cancelled draft (2 x 20) is not a receivable.
        inv={i['id']:i for i in w['invoices']}
        assert [inv[f['sale']]['status']]+[inv[f['sale']]['financial'][k] for k in('gross_total','return_total','net_total','paid_total','open_balance')]==['PARTIAL_PAID','80.00','20.00','60.00','30.00','30.00'],inv
        assert (inv[f['draft2']]['status'],inv[f['draft2']]['financial']['state'],inv[f['draft2']]['financial']['open_balance'])==('CANCELLED','INACTIVE_DOCUMENT',None)
        assert w['customer']['financial']['open_balance']=='30.00' and w['customer']['counts']==dict(invoices='2',payments='1',returns='1',cancellations='1')
        # The receivables screen's reader gives the same figures for both invoices.
        for sale,number in((f['sale'],f['tag']),(f['draft2'],f['draft2_number'])):
            d=source.read(cur,dict(f,tag=number,sale=sale))['detail']
            assert d['financial']==inv[sale]['financial'] and d['status']==inv[sale]['status'],(d['financial'],inv[sale])
        return dict(status='PASS',events=[r['kind'] for r in rows],invoice=dict(total='80.00',returned='20.00',paid='30.00',balance='30.00'),
                    cancelled_draft='listed, not a receivable',customer_open_balance='30.00',same_as_receivables_reader=True,read_changed_nothing=True,
                    wib_dates=[r['wib_date'] for r in rows])
    def reversals():
        f=fixture(cur,today)
        p=payments.pay(cur,f,'10')['payment_id'];payments.inverse(cur,f,p)
        r=returns.returned(cur,f,qty='1',refund='20')['return_id'];returns.inverse(cur,f,r)
        returns.reverse_sale(cur,f);oracle=native(cur,f['customer'])
        w=read(cur,dict(customer_id=f['customer']))
        kinds=sorted((x['kind'],x['document']) for x in w['timeline']['rows'])
        assert kinds==sorted([('INVOICE','INVOICE'),('PAYMENT','PAYMENT'),('RETURN','RETURN'),('CANCELLATION','INVOICE'),('CANCELLATION','PAYMENT'),('CANCELLATION','RETURN')]),kinds
        same_events(w['timeline']['rows'],oracle['events'],True);same_invoices(w,oracle['invoices'],True);same_customer(w['customer'],oracle,True)
        assert w['timeline']['rows'][0]==next(x for x in w['timeline']['rows'] if x['kind']=='CANCELLATION' and x['document']=='INVOICE'),w['timeline']['rows'][0]
        assert {x['status'] for x in w['timeline']['rows']}=={'REVERSED'}
        assert w['customer']['financial']==dict(basis='CURRENT_NATIVE_DOCUMENT',active_invoices='0',invoice_total='0.00',return_total='0.00',net_total='0.00',
                                                paid_total='0.00',open_balance='0.00'),w['customer']['financial']
        assert w['invoices'][0]['financial']['open_balance'] is None and w['invoices'][0]['financial']['state']=='INACTIVE_DOCUMENT'
        return dict(status='PASS',events=[(x['kind'],x['document']) for x in w['timeline']['rows']],reversed_not_counted=True,customer_open_balance='0.00')
    def hidden_amounts():
        f=scenario(cur,today);oracle=native(cur,f['customer']);owner=read(cur,dict(customer_id=f['customer']))
        kasir=master.role_actor(cur,'SALES_KASIR');b.api.admin(cur)
        role=one(cur,'select role_id from erp.app_users where auth_user_id=%s',(kasir,))
        assert {x[0] for x in cur.execute('select permission_key from erp.app_role_permissions where role_id=%s',(role,)).fetchall()}>={'sales.history.view'}
        assert not one(cur,"select exists(select 1 from erp.app_role_permissions where role_id=%s and permission_key in('finance.ar.view','sales.history.export'))",(role,))
        w=read(cur,dict(customer_id=f['customer']),kasir);no_money(w);assert w['can_export'] is False
        assert [x['id'] for x in w['timeline']['rows']]==[x['id'] for x in owner['timeline']['rows']]
        same_events(w['timeline']['rows'],oracle['events'],False);same_invoices(w,oracle['invoices'],False);same_customer(w['customer'],oracle,False)
        lst=read(cur,dict(q=f['tag']),kasir);no_money(lst);assert [x['id'] for x in lst['page']['rows']]==[f['customer']] and lst['page']['rows'][0]['counts']==owner['customer']['counts']
        # Amounts with finance.ar.view, export only with sales.history.export (a custom role, one key at a time).
        subject,custom=auth.custom_actor(cur)
        cur.execute("insert into erp.app_role_permissions(role_id,permission_key) values(%s,'sales.history.view'),(%s,'finance.ar.view')",(custom,custom))
        x=read(cur,dict(customer_id=f['customer']),subject);assert x['financial_captured'] is True and x['can_export'] is False and x['customer']['financial']['open_balance']=='30.00'
        cur.execute("insert into erp.app_role_permissions(role_id,permission_key) values(%s,'sales.history.export')",(custom,))
        assert read(cur,dict(customer_id=f['customer']),subject)['can_export'] is True
        return dict(status='PASS',sales_kasir=dict(events=len(w['timeline']['rows']),amounts=False,export=False),
                    custom_role=dict(with_ar=True,export_only_with_key=True))
    def denied():
        f=scenario(cur,today);q=dict(customer_id=f['customer'])
        # GUDANG (seeded role without sales.history.view) and a custom role holding sales.invoice.view but not the history key.
        gudang=master.role_actor(cur,'GUDANG');subject,role=auth.custom_actor(cur);b.api.admin(cur)
        assert not one(cur,"select exists(select 1 from erp.app_role_permissions where role_id=%s and permission_key='sales.history.view')",(role,))
        before=b.boundary.snapshot(cur);out={}
        out['gudang']=refused(cur,lambda:read(cur,q,gudang),'CP7_CUSTOMER_HISTORY_DENIED')
        out['without_history_view']=refused(cur,lambda:read(cur,q,subject),'CP7_CUSTOMER_HISTORY_DENIED')
        out['list_without_history_view']=refused(cur,lambda:read(cur,dict(q=f['tag']),subject),'CP7_CUSTOMER_HISTORY_DENIED')
        out['service_role_jwt']=refused(cur,lambda:read(cur,q,None,'service_role'),'CP7_CUSTOMER_HISTORY_DENIED')
        out['anon_jwt']=refused(cur,lambda:read(cur,q,None,'anon'),'CP7_CUSTOMER_HISTORY_DENIED')
        out['unknown_subject']=refused(cur,lambda:read(cur,q,str(uuid.uuid4())),'CP7_CUSTOMER_HISTORY_DENIED')
        c.unchanged(cur,before,'customer history refusals')
        # The key is read at every call: granted -> events without amounts; taken away -> refused again.
        cur.execute("insert into erp.app_role_permissions(role_id,permission_key) values(%s,'sales.history.view')",(role,))
        allowed=read(cur,q,subject);no_money(allowed);assert len(allowed['timeline']['rows'])==5
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='sales.history.view'",(role,))
        before=b.boundary.snapshot(cur)
        out['revoked_now']=refused(cur,lambda:read(cur,q,subject),'CP7_CUSTOMER_HISTORY_DENIED')
        c.unchanged(cur,before,'customer history refusal after revoke')
        return dict(status='PASS',refused=out,granted_then_events_without_amounts=True,current_permission=True)
    def timeline_paging():
        f=scenario(cur,today);oracle=native(cur,f['customer']);pages=[]
        for off in(0,2,4):pages.append(read(cur,dict(customer_id=f['customer'],offset=off,limit=2)))
        assert [len(p['timeline']['rows']) for p in pages]==[2,2,1] and [p['timeline']['next_offset'] for p in pages]==[2,4,None]
        assert all(p['timeline']['total']=='5' and p['timeline']['limit']==2 for p in pages)
        joined=[r for p in pages for r in p['timeline']['rows']];same_events(joined,oracle['events'],True)
        assert len({r['id'] for r in joined})==5
        for p in pages:same_invoices(p,oracle['invoices'],True)
        past=read(cur,dict(customer_id=f['customer'],offset=5,limit=2))
        assert past['timeline']['rows']==[] and past['invoices']==[] and past['timeline']['next_offset'] is None and past['customer']==pages[0]['customer']
        return dict(status='PASS',pages=[[r['kind'] for r in p['timeline']['rows']] for p in pages],no_gap_no_duplicate=True,
                    invoices_per_page=[len(p['invoices']) for p in pages])
    def list_paging():
        f=scenario(cur,today);tag=f['tag']
        extra=[str(source.fg.base.create_customer(cur,tag+s)) for s in('X','Y')];b.api.admin(cur)
        expected=[x[0] for x in cur.execute("""select id::text from erp.customers where strpos(lower(concat_ws(' ',customer_code,customer_name)),lower(%s))>0
            order by customer_name,customer_code,id""",(tag,)).fetchall()]
        assert sorted(expected)==sorted([f['customer']]+extra),expected
        pages=[read(cur,dict(q=tag.lower(),offset=off,limit=1)) for off in(0,1,2)]
        assert [p['page']['rows'][0]['id'] for p in pages]==expected and [p['page']['next_offset'] for p in pages]==[1,2,None]
        assert all(p['mode']=='LIST' and p['page']['total']=='3' for p in pages)
        oracle=native(cur,f['customer'])
        for p in pages:
            row=p['page']['rows'][0]
            if row['id']==f['customer']:
                same_customer(row,oracle,True);assert row['financial']['open_balance']=='30.00' and datetime.fromisoformat(row['last_invoice_at'])==max(h['at'] for h in oracle['invoices'].values())
            else:
                assert row['counts']==dict(invoices='0',payments='0',returns='0',cancellations='0') and row['financial']['open_balance']=='0.00' and row['last_invoice_at'] is None,row
        assert read(cur,dict(q=uuid.uuid4().hex))['page']==dict(rows=[],total='0',offset=0,limit=25,next_offset=None)
        return dict(status='PASS',customers=3,pages_of_one=[p['page']['rows'][0]['code'] for p in pages],case_insensitive=True,
                    open_balance_per_customer=[p['page']['rows'][0]['financial']['open_balance'] for p in pages])
    def query_refusals():
        f=scenario(cur,today);before=b.boundary.snapshot(cur);out={}
        for label,q in dict(limit_101=dict(limit=101),limit_0=dict(limit=0),limit_text=dict(limit='5'),offset_negative=dict(offset=-1),offset_fraction=dict(offset=1.5),
                            unknown_key=dict(status='PAID'),bad_uuid=dict(customer_id='bukan-uuid'),q_with_customer=dict(customer_id=f['customer'],q='x'),
                            long_q=dict(q='x'*121),q_number=dict(q=5)).items():
            out[label]=refused(cur,lambda:read(cur,q),'CP7_CUSTOMER_HISTORY_QUERY')
        out['not_an_object']=refused(cur,lambda:(auth.actor(cur),one(cur,"select public.erp_cp7_get_customer_history_v1('[]'::jsonb)")),'CP7_CUSTOMER_HISTORY_QUERY')
        out['unknown_customer']=refused(cur,lambda:read(cur,dict(customer_id=str(uuid.uuid4()))),'CP7_CUSTOMER_HISTORY_NOT_FOUND')
        c.unchanged(cur,before,'customer history query refusals')
        return dict(status='PASS',refused=out)
    def private():
        import cp7_customer_history_bundle as bundle
        b.api.admin(cur);proof=bundle.verify(cur)
        f=scenario(cur,today);before=b.boundary.snapshot(cur)
        direct=refused(cur,lambda:(auth.actor(cur),one(cur,'select cp7_customer_history.workspace(%s)',(json.dumps(dict(customer_id=f['customer'])),))),'permission denied')
        helper=refused(cur,lambda:(auth.actor(cur),one(cur,'select count(*) from cp7_customer_history.events(%s)',(f['customer'],))),'permission denied')
        # The facade cannot write: the answer's own flags, and a read leaves every business table and the audit log as it was.
        audit=one(cur,'select count(*) from erp.audit_logs');w=read(cur,dict(customer_id=f['customer']));read(cur,dict(q=f['tag']))
        assert one(cur,'select count(*) from erp.audit_logs')==audit and w['read_only'] is True and w['business_DML'] is False
        c.unchanged(cur,before,'customer history reads')
        return dict(status='PASS',verify=proof,private_workspace_refused=direct,private_helper_refused=helper,audit_rows_unchanged=True)
    named=[events_and_balances,reversals,hidden_amounts,denied,timeline_paging,list_paging,query_refusals,private]
    assert len(named)==len(NATIVE)
    return list(zip(NATIVE,named))


def races(tools,today):
    def payment_during_read():
        """The reader is held on a real lock (erp.locations, read only by the timeline statement, never by the payment
        command) after it has read the customer's totals; a Rp10 payment commits through the Penjualan command meanwhile.
        The one answer is the state before the payment everywhere (totals, timeline, invoice); the next read has it."""
        with tools.connect()as conn,conn.cursor()as cur:
            f=scenario(cur,today);conn.commit()
            before=native(cur,f['customer']);p,v=payments.payment_payload(cur,f,'10');conn.commit()
        with tools.connect()as holder,holder.cursor()as held,tools.connect(autocommit=True)as watch,watch.cursor()as look:
            held.execute('lock table erp.locations in access exclusive mode')
            pid={}
            def reader():
                with tools.connect()as conn,conn.cursor()as cur:
                    pid['reader']=one(cur,'select pg_backend_pid()')
                    try:r=read(cur,dict(customer_id=f['customer']));conn.commit();return r
                    except psycopg.Error as e:conn.rollback();return 'REFUSED:'+str(e).splitlines()[0]
            with ThreadPoolExecutor(max_workers=1)as pool:
                job=pool.submit(reader);waiting=False;deadline=time.monotonic()+15
                try:
                    while time.monotonic()<deadline and not waiting:
                        waiting=bool(pid.get('reader'))and one(look,"""select exists(select 1 from pg_locks l join pg_stat_activity a on a.pid=l.pid
                            where l.pid=%s and not l.granted and l.relation='erp.locations'::regclass
                            and a.query like 'select public.erp_cp7_get_customer_history_v1%%')""",(pid['reader'],))
                        if not waiting:time.sleep(.03)
                    assert waiting,'CP17_R3_03_READER_LOCK_WAIT_NOT_OBSERVED'
                    with tools.connect()as conn,conn.cursor()as cur:
                        cur.execute("set local statement_timeout='20s'")
                        try:paid=cmd.command(cur,'PAYMENT',p,v);conn.commit()
                        except psycopg.Error as e:raise AssertionError(('CP17_R3_03_PAYMENT_DID_NOT_COMMIT_WHILE_READER_WAITED',str(e).splitlines()[0]))
                    with tools.connect()as conn,conn.cursor()as cur:
                        b.api.admin(cur);posted=one(cur,"select count(*) from erp.sales_payments where sale_id=%s and status='POSTED'",(f['sale'],))
                    assert posted==2,posted
                    still=one(look,"select exists(select 1 from pg_locks where pid=%s and not granted)",(pid['reader'],))
                    assert still,'CP17_R3_03_READER_FINISHED_BEFORE_THE_PAYMENT'
                finally:holder.rollback()
                answer=job.result(60)
        assert isinstance(answer,dict),answer
        # One snapshot: the totals, the timeline and the invoice are all the state before the payment.
        same_customer(answer['customer'],before,True);same_events(answer['timeline']['rows'],before['events'],True);same_invoices(answer,before['invoices'],True)
        assert answer['customer']['financial']['paid_total']=='30.00' and sum(1 for r in answer['timeline']['rows'] if r['kind']=='PAYMENT')==1
        assert sum(money(r['financial']['amount']) for r in answer['timeline']['rows'] if r['kind']=='PAYMENT' and r['status']=='POSTED')==money(answer['customer']['financial']['paid_total'])
        with tools.connect()as conn,conn.cursor()as cur:
            after_native=native(cur,f['customer']);after=read(cur,dict(customer_id=f['customer']))
        same_customer(after['customer'],after_native,True);same_events(after['timeline']['rows'],after_native['events'],True)
        assert after['customer']['financial']['paid_total']=='40.00' and after['customer']['financial']['open_balance']=='20.00'
        assert [r['document_id'] for r in after['timeline']['rows'] if r['kind']=='PAYMENT'][0]==paid['payment_id']
        return dict(status='PASS',reader_waited_on='erp.locations',payment_committed_meanwhile=paid['payment_id'],
                    answer_during=dict(paid='30.00',payments=1,open='30.00'),next_answer=dict(paid='40.00',payments=2,open='20.00'),one_snapshot=True)
    return list(zip(RACES,[payment_during_read]))


def http_cases(http,today):
    def owner_and_kasir():
        owner=http.login('OWNER','cp17-r3-03-owner');kasir=http.login('SALES_KASIR','cp17-r3-03-kasir');gudang=http.login('GUDANG','cp17-r3-03-gudang')
        with http.connect()as conn,conn.cursor()as cur:
            f=scenario(cur,today);conn.commit();oracle=native(cur,f['customer']);conn.commit()
        q=dict(customer_id=f['customer'])
        lst=owner.rpc('erp_cp7_get_customer_history_v1',dict(p_query=dict(q=f['tag'])));assert lst['status']==200,lst
        assert [x['id'] for x in lst['body']['page']['rows']]==[f['customer']] and lst['body']['page']['rows'][0]['financial']['open_balance']=='30.00',lst
        w=owner.rpc('erp_cp7_get_customer_history_v1',dict(p_query=q));assert w['status']==200,w;w=w['body']
        assert w['financial_captured'] is True and w['can_export'] is True
        same_events(w['timeline']['rows'],oracle['events'],True);same_invoices(w,oracle['invoices'],True);same_customer(w['customer'],oracle,True)
        k=kasir.rpc('erp_cp7_get_customer_history_v1',dict(p_query=q));assert k['status']==200,k;k=k['body']
        no_money(k);assert k['can_export'] is False and [x['id'] for x in k['timeline']['rows']]==[x['id'] for x in w['timeline']['rows']]
        same_events(k['timeline']['rows'],oracle['events'],False)
        g=gudang.rpc('erp_cp7_get_customer_history_v1',dict(p_query=q))
        assert g['status']==403 and 'CP7_CUSTOMER_HISTORY_DENIED' in json.dumps(g['body']),g
        a=http.anon_rpc('erp_cp7_get_customer_history_v1',dict(p_query=q));assert a['status'] in(401,403) and 'CP7_CUSTOMER_HISTORY' not in json.dumps(a['body']),a
        private=owner.rpc('workspace',dict(p_query=q));assert private['status']>=400,private
        with http.connect()as conn,conn.cursor()as cur:
            assert native(cur,f['customer'])==oracle
        return dict(status='PASS',real_Auth=True,owner=dict(events=len(w['timeline']['rows']),open_balance=w['customer']['financial']['open_balance']),
                    sales_kasir=dict(events=len(k['timeline']['rows']),amounts=False,export=False),gudang=403,anon=a['status'],read_changed_nothing=True)
    return list(zip(HTTP,[owner_and_kasir]))


# ---- browser fixture operations (wired by the writer into scripts/cp7_cp17_fix_browser_fixture.py)
def browser_fixture(cur,today):
    """The Native cases' scenario, committed by the caller; what the browser journey types and expects."""
    f=scenario(cur,today);oracle=native(cur,f['customer'])
    code,name=cur.execute('select customer_code,customer_name from erp.customers where id=%s',(f['customer'],)).fetchone()
    return dict(customer=f['customer'],tag=f['tag'],code=code,name=name,invoice=f['tag'],draft=f['draft2_number'],
                payment=one(cur,'select payment_number from erp.sales_payments where id=%s',(f['payment'],)),
                ret=one(cur,'select return_number from erp.sales_returns where id=%s',(f['return'],)),
                events=[[e['kind'],e['document'],e['number']] for e in oracle['events']],open_balance=str(oracle['totals']['open']))
def browser_state(cur,p):
    """Native rows only: the customer's documents with their status and figures, and the audit rows about them."""
    o=native(cur,p['customer'])
    ids=list(o['invoices'])+[e['document_id'] for e in o['events'] if e['document']!='INVOICE']
    return dict(invoices=sorted([h['number'],h['status'],str(h['gross']),str(h['returned']),str(h['paid'])] for h in o['invoices'].values()),
                events=[[e['kind'],e['document'],e['number'],e['status']] for e in o['events']],totals={k:str(v) for k,v in o['totals'].items()},
                audit_rows=one(cur,'select count(*) from erp.audit_logs where entity_id=any(%s::uuid[])',(ids,)))
