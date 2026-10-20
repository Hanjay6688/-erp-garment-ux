"""Unexecuted OW04 Native source fixture/probe proposal, not a product module.

Only retained Native/CP7 sale, payment, found-stock and reopen writers are used.
The initial period cutoff and party/location/cash masters are explicitly labelled
administrative disposable fixtures. No settlement API payload/action is invented.
All setup/reads require the closed harness; importing this module never connects.
"""
from contextlib import contextmanager
from datetime import datetime, time, timedelta
from decimal import Decimal as D
from pathlib import Path
from zoneinfo import ZoneInfo
import hashlib
import json
import uuid

import cp7_sales_return_cases as returns
import cp7_note_correction_cases as note
import cp7_period_cases as period

payments,cmd,source,b,auth=returns.payments,returns.cmd,returns.source,returns.b,returns.auth
ERP_ZONE=ZoneInfo('Asia/Jakarta')
EXPECTED_SHA='f6d7efdde1a409094b8c5485fb7942209175bce1d869e8c05f1a1d097b7cadde'
QUOTE_SIGNATURE='public.erp_cp7_get_sales_return_settlement_quote_v1(jsonb)'
SOURCE_FIXTURE_IDS=tuple('OW04_SOURCE_'+p+'_'+t for p in ('1000','900') for t in ('OPEN','CLOSED','REOPENED'))


def expected(path=None):
    p=Path(path) if path else Path(__file__).with_name('EXPECTED.json')
    data=p.read_bytes()
    assert hashlib.sha256(data).hexdigest()==EXPECTED_SHA,'OW04_FROZEN_EXPECTED_CHANGED'
    return json.loads(data)


def _raw(cur,query,args=()):
    """Preserve actual PostgreSQL JSON text for exact equality and hashing.

    The parsed document is for navigation. Never hash a float-roundtripped copy.
    SQL must return one JSON/JSONB value, not arbitrary dynamically chosen SQL.
    """
    text=cur.execute('select ('+query+')::text',args).fetchone()[0]
    assert text is not None
    return dict(raw_json=text,sha256=hashlib.sha256(text.encode()).hexdigest(),document=json.loads(text,parse_float=str))


def _array(cur,table,predicate,args):
    # table/predicate only come from the fixed call sites below, never RPC input.
    return _raw(cur,"select coalesce(jsonb_agg(to_jsonb(t) order by to_jsonb(t)::text),'[]'::jsonb) from "+table+' t where '+predicate,args)


def _optional(cur,table,predicate,args):
    installed=cur.execute('select to_regclass(%s) is not null',(table,)).fetchone()[0]
    if not installed:
        return dict(installed=False,rows=None)
    return dict(installed=True,rows=_array(cur,table,predicate,args))


def journal(cur,ident):
    return _raw(cur,"select jsonb_build_object('header',(select to_jsonb(j) from erp.journal_entries j where j.id=%s),"
        "'lines',(select coalesce(jsonb_agg(to_jsonb(l) order by l.id),'[]'::jsonb) from erp.journal_lines l where l.journal_entry_id=%s))",(ident,ident))


def payment_snapshot(cur,ident):
    """Settlement/consumer undo must leave this WHOLE snapshot byte-identical.

    It includes POSTED status, exact microseconds, full posting fact, original
    journal header/status/dates and every full original line; reversal facts stay
    empty. Explicit PAYMENT_REVERSE/CORRECT has a different history contract.
    """
    b.api.admin(cur)
    fact=_raw(cur,"select jsonb_build_object('header',(select to_jsonb(p) from erp.sales_payments p where p.id=%s),"
        "'posting_facts',(select coalesce(jsonb_agg(to_jsonb(f) order by f.payment_id),'[]'::jsonb) from erp.sales_payment_posting_facts f where f.payment_id=%s),"
        "'reversal_facts',(select coalesce(jsonb_agg(to_jsonb(r) order by r.payment_id),'[]'::jsonb) from erp.sales_payment_reversal_facts r where r.payment_id=%s))",(ident,ident,ident))
    facts=fact['document']['posting_facts']
    assert len(facts)==1 and fact['document']['header'] is not None,(ident,fact)
    return dict(payment=fact,original_journal=journal(cur,facts[0]['original_journal_entry_id']))


def assert_payment_unchanged(cur,x):
    assert payment_snapshot(cur,x['f']['payment'])==x['payment_before'],'OW04_SOURCE_PAYMENT_WAS_MUTATED'


def _family_sales(cur,sale):
    available=cur.execute("select to_regclass('cp7_note.revisions') is not null").fetchone()[0]
    if not available:
        return [sale],dict(installed=False,rows=None)
    roots=[r[0] for r in cur.execute('select distinct root_sale_id::text from cp7_note.revisions '
        'where %s::uuid in(root_sale_id,previous_sale_id,replacement_sale_id)',(sale,)).fetchall()]
    assert len(roots)<=1,'OW04_NOTE_FAMILY_AMBIGUOUS'
    root=roots[0] if roots else sale
    revisions=_array(cur,'cp7_note.revisions','root_sale_id=%s',(root,))
    ids={sale,root}
    for r in revisions['document']:
        ids.update((r['root_sale_id'],r['previous_sale_id'],r['replacement_sale_id']))
    return sorted(ids),dict(installed=True,rows=revisions)


def source_manifest(cur,x):
    """Raw full history, never a POSTED-only source filter or current-leaf claim.

    This is an administrative fixture proof reader, not the product quote's
    authority collector. Absent optional schema is explicit, never empty history.
    New Native credit/apply/refund source classification is deferred to its API.
    """
    b.api.admin(cur)
    f=x['f'];sales_ids,note_revisions=_family_sales(cur,f['sale'])
    payment_headers=_array(cur,'erp.sales_payments','sale_id=any(%s::uuid[])',(sales_ids,))
    payment_ids=[r['id'] for r in payment_headers['document']]
    return_headers=_array(cur,'erp.sales_returns','sale_id=any(%s::uuid[])',(sales_ids,))
    return_ids=[r['id'] for r in return_headers['document']]
    facts=_array(cur,'erp.sales_payment_posting_facts','payment_id=any(%s::uuid[])',(payment_ids,))
    reversal_facts=_array(cur,'erp.sales_payment_reversal_facts','payment_id=any(%s::uuid[])',(payment_ids,))
    links={
        'note_revisions':note_revisions,
        'payment_links':_optional(cur,'cp7_payment_correction.links','sale_id=any(%s::uuid[])',(sales_ids,)),
        'return_links':_optional(cur,'cp7_sales_return_correction.links','sale_id=any(%s::uuid[])',(sales_ids,)),
        'return_restatements':_optional(cur,'cp7_sales_return_correction.journal_restatements','original_return_id=any(%s::uuid[])',(return_ids,)),
        'note_restatements':_optional(cur,'cp7_note.journal_restatements','previous_sale_id=any(%s::uuid[])',(sales_ids,)),
        'note_payment_replays':_optional(cur,'cp7_note.payment_replays','previous_payment_id=any(%s::uuid[]) or replacement_payment_id=any(%s::uuid[])',(payment_ids,payment_ids)),
    }
    ids=sales_ids+payment_ids+return_ids
    journal_ids={str(r[0]) for r in cur.execute('select id from erp.journal_entries where source_id=any(%s::uuid[])',(ids,)).fetchall()}
    for r in facts['document']:
        journal_ids.add(r['original_journal_entry_id'])
    for r in reversal_facts['document']:
        journal_ids.add(r['reversal_journal_entry_id'])
    for link in links.values():
        if link['installed']:
            for row in link['rows']['document']:
                for k in ('source_journal_id','inverse_journal_id','neutral_journal_id','effective_journal_id','time_neutral_id','effective_inverse_id'):
                    if row.get(k): journal_ids.add(row[k])
    # Retain recursively linked journal inverses even when originals/documents
    # are REVERSED. IDs/status are not used as a substitute for causal lineage.
    while True:
        inverses={str(r[0]) for r in cur.execute('select id from erp.journal_entries where reversal_of_id=any(%s::uuid[])',(sorted(journal_ids),)).fetchall()}
        if inverses<=journal_ids:break
        journal_ids.update(inverses)
    journals={j:journal(cur,j) for j in sorted(journal_ids)}
    # Capture customer journal headers/lines as an additional accounting witness;
    # do not guess that every new source is funding or classify credit issuance P.
    customer_ids=[str(r[0]) for r in cur.execute('select distinct j.id from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id where l.customer_id=%s order by j.id',(f['customer'],)).fetchall()]
    return dict(classification='RAW_NATIVE_FIXTURE_SOURCE_MANIFEST_NOT_QUOTE_AUTHORITY',fixture_id=x['fixture_id'],
        execution_context=cur.execute("select jsonb_build_object('current_user',current_user,'session_user',session_user,'postgres_rolsuper',(select rolsuper from pg_roles where rolname='postgres'))").fetchone()[0],
        sales_ids=sales_ids,
        sales=_array(cur,'erp.sales_headers','id=any(%s::uuid[])',(sales_ids,)),
        items=_array(cur,'erp.sales_items','sale_id=any(%s::uuid[])',(sales_ids,)),
        allocations=_raw(cur,"select coalesce(jsonb_agg(to_jsonb(a) order by a.id),'[]'::jsonb) from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=any(%s::uuid[])",(sales_ids,)),
        payment_headers=payment_headers,payment_facts=facts,payment_reversal_facts=reversal_facts,
        returns=return_headers,return_items=_array(cur,'erp.sales_return_items','return_id=any(%s::uuid[])',(return_ids,)),
        correction_lineage=links,journals=journals,customer_journals={j:journal(cur,j) for j in customer_ids},
        product=_array(cur,'erp.products','id=%s',(f['product'],)),
        found_receipt=_array(cur,'erp.fg_unsourced_receipts_v1','lot_id=%s',(f['lot'],)),
        stock=_array(cur,'erp.fg_stock_movements','lot_id=%s',(f['lot'],)),
        lot=_array(cur,'erp.fg_lots','id=%s',(f['lot'],)),
        period=_array(cur,'erp.accounting_period_control','singleton_id=1',()),
        quote_api_installed=cur.execute('select to_regprocedure(%s) is not null',(QUOTE_SIGNATURE,)).fetchone()[0])


def _calendar(cur):
    today=cur.execute("select (clock_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
    anchor=today-timedelta(days=7)
    dates={name:anchor+timedelta(days=offset) for name,offset in expected()['dates']['literal_offsets_days'].items()}
    def at(name,hour):
        return datetime.combine(dates[name],time(hour,0,0,123456),ERP_ZONE)
    return dates,dict(stock=at('D-1',8),sale=at('D0',10),payment=at('D1',11),returned=at('D2',12))


def prepared(cur,today,paid='1000.00',profile='OPEN'):
    assert paid in ('1000.00','900.00') and profile in ('OPEN','CLOSED','REOPENED')
    b.api.admin(cur);cur.execute("set local timezone='UTC'");dates,physical=_calendar(cur)
    ident='OW04_SOURCE_'+paid.split('.')[0]+'_'+profile
    exp=next(c for c in expected()['fixtures'] if c['fixture_id']==ident)
    # ADMINISTRATIVE_PERIOD_FIXTURE: retained disposable setup only; this is
    # not a Native close/filing proof and does not fabricate stock/journal rows.
    source.fg.ax.boundary.historical.prior.set_open_period(cur,dates['D-2'])
    f=note.stock(cur,today,10,physical['stock'])
    f['sale_at']=physical['sale'].isoformat()
    f['destination']=returns.location(cur,'OW04 actual return destination')
    f['bank']=str(source.bc.bank_account(cur,'OW04-'+uuid.uuid4().hex[:10]))
    before_sale=cmd.accounts(cur)
    if profile!='OPEN':
        source.fg.ax.boundary.historical.prior.set_open_period(cur,dates['D2'])
    note.posted(cur,f,'5','200')  # public CREATE/POST, invoking accepted Native sale
    f['allocations']=returns.read(cur,f)['page']['rows']
    assert len(f['allocations'])==1 and f['allocations'][0]['allocated_qty']=='5'
    assert cur.execute('select qty_pcs=5 and unit_hpp_snapshot=10 from erp.sale_stock_allocations where id=%s',
        (f['allocations'][0]['allocation_id'],)).fetchone()[0], 'OW04_KNOWN_SOURCE_HPP10_REQUIRED'
    assert cur.execute('select effective_from<=%s and (effective_to is null or %s<effective_to) from erp.products where id=%s',
        (physical['stock'],physical['returned'],f['product'])).fetchone()[0], 'OW04_PHYSICAL_DATES_OUTSIDE_PRODUCT_EFFECTIVE_RANGE'
    p,v=payments.payment_payload(cur,f,paid);p['payment_date']=physical['payment'].isoformat()
    f['payment']=cmd.command(cur,'PAYMENT',p,v)['payment_id']
    x=dict(fixture_id=ident,f=f,expected=exp,profile=profile,dates={k:str(v) for k,v in dates.items()},
        physical={k:v.isoformat() for k,v in physical.items()},before_sale_accounts=before_sale,
        payment_before=payment_snapshot(cur,f['payment']),period_setup='ADMINISTRATIVE_PERIOD_FIXTURE')
    ps=x['payment_before']['payment']['document']
    assert ps['header']['status']=='POSTED' and D(str(ps['header']['amount']))==D(paid)
    assert ps['reversal_facts']==[]
    j=x['payment_before']['original_journal']['document']['header']
    sale_journals=[r[0] for r in cur.execute("select id::text from erp.journal_entries where source_type='SALE' and source_id=%s and reversal_of_id is null",(f['sale'],)).fetchall()]
    assert len(sale_journals)==1,sale_journals
    sj=journal(cur,sale_journals[0]);s=sj['document']['header']
    book_sale=dates['D0'] if profile=='OPEN' else dates['D3']
    book_pay=dates['D1'] if profile=='OPEN' else dates['D3']
    assert (s['economic_date'],s['transaction_date'])==(str(dates['D0']),str(book_sale)),s
    assert (j['economic_date'],j['transaction_date'])==(str(dates['D1']),str(book_pay)),j
    assert ps['header']['payment_date']==cur.execute('select to_jsonb(%s::timestamptz)',(physical['payment'],)).fetchone()[0]
    if profile=='REOPENED':
        # Current public owner facade calls the actual Native reopen writer;
        # no public legacy grant or production bypass is added by this fixture.
        filing_before=period.filings(cur)
        w=period.read(cur,dates['D2'])
        x['reopen_outcome']=period.command(cur,'REOPEN',period.intent(w,'REOPEN',str(dates['D-2'])))
        assert period.filings(cur)==filing_before
        assert_payment_unchanged(cur,x)
        assert journal(cur,sale_journals[0])==sj,'OW04_REOPEN_MUTATED_ORIGINAL_SALE_JOURNAL'
    resolver=cur.execute('select erp.resolve_accounting_transaction_date(%s)',(dates['D2'],)).fetchone()[0]
    resolver_label=expected()['date_profiles'][profile]['current_return_resolver']
    assert resolver==dates[resolver_label],(profile,resolver,dates[resolver_label])
    x['current_return_resolver']=str(resolver)
    p,v=return_intent(cur,x)
    x.update(return_payload=p,return_version=v)
    d=source.read(cur,f)['detail']
    assert d['status']==exp['pre_return']['sale_status']
    assert {k:d['financial'][k] for k in ('gross_total','return_total','net_total','paid_total','open_balance')}=={
        'gross_total':'1000.00','return_total':'0.00','net_total':'1000.00','paid_total':paid,'open_balance':exp['pre_return']['AR']}
    assert returns.positions(cur,f)=={(f['location'],'GRADE_A'):5}
    x['source_events_before']=initial_source_events(cur,x,sale_journals[0])
    x['source_before']=source_manifest(cur,x)
    x['boundary_before']=b.boundary.snapshot(cur)
    return x



def initial_source_events(cur,x,sale_journal_id):
    """Two explicit source events from STORED journal amounts and date pairs.

    Only this fixture's initial SALE/PAYMENT are classified here. This is not
    the future full correction/credit collector. The full raw history remains
    in source_manifest, including every reversed original and linked restatement.
    """
    b.api.admin(cur)
    f=x['f'];result=[]
    original=x['payment_before']['payment']['document']['posting_facts'][0]['original_journal_entry_id']
    for kind,ident,mapping_key,amount in (('NET',sale_journal_id,'SALES_REVENUE','1000.00'),
                                       ('FUNDING',original,'AR_CUSTOMER',x['expected']['payment_amount'])):
        raw=journal(cur,ident);h=raw['document']['header']
        value=cur.execute('select coalesce(sum(l.credit-l.debit),0) from erp.journal_lines l '
            'where l.journal_entry_id=%s and l.account_id=%s and l.customer_id=%s',
            (ident,cmd.mapping(cur,mapping_key),f['customer'])).fetchone()[0]
        assert D(value)==D(amount),(kind,value,amount)
        result.append(dict(id=ident,kind=kind,amount=format(D(value),'.2f'),
            economic_date=h['economic_date'],transaction_date=h['transaction_date'],
            source_sha256=raw['sha256'],journal_status=h['status'],
            classification='ACTUAL_INITIAL_NATIVE_FIXTURE_JOURNAL_ONLY'))
    return result


def liability_account_review(cur):
    """Read actual candidates, never create/pick a default or bless old BB reuse.

    Shape/exclusion flags are evidence only; the future Native source reconciler
    must additionally explain every existing journal on a selected account.
    """
    b.api.admin(cur)
    return _raw(cur,"select coalesce(jsonb_agg(jsonb_build_object('account',to_jsonb(a),"
        "'is_cash',exists(select 1 from erp.cash_accounts c where c.coa_account_id=a.id),"
        "'is_mapping',exists(select 1 from erp.accounting_account_mappings m where m.account_id=a.id),"
        "'is_prepayment',exists(select 1 from erp.initial_import_prepayments p where p.coa_account_id=a.id),"
        "'has_any_journal',exists(select 1 from erp.journal_lines l where l.account_id=a.id),"
        "'has_BB_credit_lineage',exists(select 1 from erp.bb_customer_credits_v1 c where c.coa_account_id=a.id))"
        "order by a.account_code,a.id),'[]'::jsonb) from erp.chart_accounts a "
        "where a.account_type='LIABILITY' and a.normal_balance='CREDIT' and a.is_active and a.is_postable")


def assert_first_settlement_gl(cur,x,mode,liability_account_id):
    """Independent RAW GL/stock oracle for one future initial settlement.

    Call only AFTER an actual defined writer succeeds, before creating any other
    invoice/consumer in the same fixture. No new writer is called here. This
    assertion is not a substitute for future cohort/source/date/account checks.
    """
    assert mode in ('CREDIT','REFUND') and liability_account_id is not None
    b.api.admin(cur);f=x['f'];gold=x['expected']
    shape=cur.execute("select a.account_type='LIABILITY' and a.normal_balance='CREDIT' and a.is_active and a.is_postable "
        "and not exists(select 1 from erp.cash_accounts c where c.coa_account_id=a.id) "
        "and not exists(select 1 from erp.accounting_account_mappings m where m.account_id=a.id) "
        "and not exists(select 1 from erp.initial_import_prepayments p where p.coa_account_id=a.id) "
        "from erp.chart_accounts a where a.id=%s",(liability_account_id,)).fetchone()
    assert shape is not None and shape[0] is True,'OW04_EXPLICIT_VALID_LIABILITY_ACCOUNT_REQUIRED'
    assert_payment_unchanged(cur,x)
    assert returns.positions(cur,f)=={(f['location'],'GRADE_A'):5,(f['destination'],'GRADE_A'):1}
    rows=cur.execute('select i.qty_pcs,i.unit_hpp_snapshot,i.refund_amount,i.sale_stock_allocation_id,i.location_id,i.quality_grade '
        'from erp.sales_return_items i join erp.sales_returns h on h.id=i.return_id '
        "where h.sale_id=%s and h.status='POSTED' order by i.id",(f['sale'],)).fetchall()
    assert len(rows)==1 and rows[0][:3]==(1,D('10.00'),D('200.00')),rows
    assert str(rows[0][3])==f['allocations'][0]['allocation_id'] and str(rows[0][4])==f['destination'] and rows[0][5]=='GRADE_A',rows
    # debit-positive signs, measured relative to the actual before-sale GL.
    cash=D(gold['future_credit']['bank_from_fixture'] if mode=='CREDIT' else gold['future_full_refund']['bank_from_fixture'])
    credit=D(gold['future_credit']['liability_credit'] if mode=='CREDIT' else '0.00')
    want={cmd.mapping(cur,'SALES_REVENUE'):D('-800.00'),cmd.mapping(cur,'FG_INVENTORY'):D('-40.00'),
          cmd.mapping(cur,'COGS'):D('40.00'),payments.bank_account(cur,f):cash,str(liability_account_id):-credit}
    # AR is exactly0 relative to baseline; including no zero key makes a hidden
    # residual debit/credit fail the whole delta equality.
    want={k:v for k,v in want.items() if v!=0}
    assert cmd.delta(x['before_sale_accounts'],cmd.accounts(cur))==want
    d=source.read(cur,f)['detail']
    assert d['status']=='PAID' and d['returned_qty']=='1',d
    assert {k:d['financial'][k] for k in ('gross_total','return_total','net_total','paid_total','open_balance')}=={
        'gross_total':'1000.00','return_total':'200.00','net_total':'800.00','paid_total':'800.00','open_balance':'0.00'},d
    # Existing P11 financial paid_total becomes E; the payment header/fact above
    # still proves the original P1000/P900 exactly, including POSTED status.


def return_intent(cur,x):
    p,v=returns.payload(cur,x['f'],qty='1',refund='200',grade='GRADE_A')
    p['physical_at']=x['physical']['returned']
    p['notes']='OW04 independently expected source return1/value200; no settlement choice supplied'
    return p,v


def legacy_omitted_choice_refused(cur,x):
    p,v=return_intent(cur,x)
    before=b.boundary.snapshot(cur);manifest=source_manifest(cur,x)
    error=auth.refused(cur,lambda:cmd.command(cur,'RETURN',p,v),'membuat pembayaran customer melebihi nilai penjualan tersisa')
    assert b.boundary.snapshot(cur)==before and source_manifest(cur,x)==manifest
    assert_payment_unchanged(cur,x)
    return dict(classification='LEGACY_NEGATIVE_ONLY_NOT_SETTLEMENT_SUCCESS',error=error)



def source_definitions(cur):
    """Capture actual source bodies/owner/ACL/config for the disposable receipt.

    Resolve actual overloads from the catalog, including the private inverse;
    no approximate body/hash from old documentation is treated as runtime proof.
    """
    b.api.admin(cur)
    names=['post_sale','post_sale_v2','post_sales_payment','reverse_sales_payment',
        'post_sales_return','reverse_sales_return','reverse_sale','post_journal',
        'reverse_journal','_cp3_r4_reverse_journal_internal','reopen_accounting_through','resolve_accounting_transaction_date',
        'erp_cp7_get_sales_return_settlement_quote_v1']
    rows=cur.execute("select p.oid::regprocedure::text,pg_get_functiondef(p.oid),pg_get_userbyid(p.proowner),"
        "p.proacl::text,p.proconfig,p.prosecdef,p.provolatile from pg_proc p join pg_namespace n on n.oid=p.pronamespace "
        "where n.nspname in('erp','public') and p.proname=any(%s::text[]) order by p.oid::regprocedure::text",(names,)).fetchall()
    return {signature:dict(definition=body,definition_sha256=hashlib.sha256(body.encode()).hexdigest(),
        owner=owner,acl=acl,config=config,security_definer=definer,volatility=volatility)
        for signature,body,owner,acl,config,definer,volatility in rows}


def call_quote(cur,quote_payload,subject=None):
    """Positional tentative signature only; caller supplies the eventual payload.

    No p_query field, mode, request token, permission name, or positive outcome
    schema is guessed here. Missing API fails explicitly rather than skipping.
    This is authenticated SQL, not real Auth/PostgREST proof.
    """
    b.api.admin(cur)
    exists=cur.execute('select to_regprocedure(%s) is not null',(QUOTE_SIGNATURE,)).fetchone()[0]
    if not exists:raise RuntimeError('OW04_SETTLEMENT_QUOTE_API_NOT_INSTALLED')
    assert isinstance(quote_payload,dict)
    auth.actor(cur,subject)
    # Match retained facades: on SQL error the caller's refusal/transaction
    # boundary rolls back before restoring admin, preserving the original error.
    result=cur.execute('select public.erp_cp7_get_sales_return_settlement_quote_v1(%s::jsonb)',(json.dumps(quote_payload),)).fetchone()[0]
    b.api.admin(cur)
    return result


@contextmanager
def isolated(cur):
    b.api.admin(cur);name='ow04_source_'+uuid.uuid4().hex
    cur.execute('savepoint '+name)
    try:yield
    finally:
        cur.execute('rollback to savepoint '+name);b.api.admin(cur);cur.execute('release savepoint '+name)


def source_probes(cur,today):
    """When explicitly run, capture actual source evidence, never feature PASS.

    The caller owns the outer disposable DB transaction and serializes these
    period-global fixtures. Every variant rolls back completely before the next.
    """
    definitions=source_definitions(cur)
    evidence=[]
    for paid in ('1000.00','900.00'):
        for profile in ('OPEN','CLOSED','REOPENED'):
            with isolated(cur):
                x=prepared(cur,today,paid,profile)
                negative=legacy_omitted_choice_refused(cur,x)
                evidence.append(dict(fixture_id=x['fixture_id'],source=x['source_before'],legacy_negative=negative,
                    physical=x['physical'],dates=x['dates'],current_return_resolver=x['current_return_resolver'],initial_source_events=x['source_events_before'],
                    classification='SOURCE_FIXTURE_ONLY_FEATURE_NOT_EXECUTED'))
    assert [x['fixture_id'] for x in evidence]==list(SOURCE_FIXTURE_IDS)
    return dict(classification='ACTUAL_SOURCE_PROBE_ONLY_IF_THIS_FUNCTION_WAS_RUN',feature_action_executed=False,native_source_definitions=definitions,evidence=evidence)
