"""Predeclared actual Native return correction oracles, not synthetic stock.
Old histories, every later prefix, Native money/HPP, current permission and
source races, committed Auth replay and owning desktop/mobile are separate.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal as D
import copy,json,threading,time,uuid
import psycopg
import cp7_sales_return_cases as returns
import cp7_note_correction_cases as note
import cp7_transaction_source_cases as navigation
import cp7_sales_return_correction_bundle as bundle
cmd,source,b,auth=returns.cmd,returns.source,returns.b,returns.auth
RPC='erp_cp7_correct_sales_return_v1'
READ='erp_cp7_get_sales_return_correction_v1'
REQUIRED=dict(native=16,races=4,http=3,browser=2)
EXPECTED=sum(REQUIRED.values())
NAMES=('EXACT','INCREASE','FULLY_RETURNED','TWO_ALLOCATIONS','GRADES_LOCATION','MICROSECONDS',
       'DATE_MOVE','YEAR_364','FINAL_POST_FAILURE','STALE_SOURCE_STOCK','CURRENT_PERMISSIONS',
       'CLOSED_FIELDS_NATIVE_CAPS','REPLAY_RESTORE','IMMUTABLE_HISTORY_SOURCE','DOWNSTREAM_STOCK','CLOSED_BOOKS')

def workspace(cur,f,return_id=None,subject=None,**query):
    auth.actor(cur,subject)
    r=cur.execute('select public.erp_cp7_get_sales_return_correction_v1(%s)',
        (json.dumps(dict(sale_id=f['sale'],return_id=return_id or f['return'],**query)),)).fetchone()[0]
    b.api.admin(cur);return r

def correct(cur,p,version,key=None,subject=None):
    auth.actor(cur,subject)
    r=cur.execute('select public.erp_cp7_correct_sales_return_v1(%s,%s,%s)',(json.dumps(p),key or uuid.uuid4(),version)).fetchone()[0]
    b.api.admin(cur);return r

def private_state(cur):
    b.api.admin(cur)
    tables=[bundle.SCHEMA+'.'+t for t in bundle.TABLES]+['cp7_fg.correction_movements','cp7_sales.requests','cp7_sales.command_context']
    return {t:cur.execute("select md5(coalesce(jsonb_agg(to_jsonb(x)order by to_jsonb(x)::text),'[]')::text)from "+t+' x').fetchone()[0]for t in tables}

def original_fact(cur,ident):
    b.api.admin(cur)
    return cur.execute("select jsonb_build_object('header',(select to_jsonb(h)-array['status','row_version','updated_at']from erp.sales_returns h where id=%s),"
      "'physical_items',(select jsonb_agg(jsonb_build_object('id',i.id,'return_id',i.return_id,'allocation_id',i.sale_stock_allocation_id,"
      "'product_id',i.product_id,'lot_id',i.lot_id,'location_id',i.location_id,'qty_pcs',i.qty_pcs,'quality_grade',i.quality_grade,"
      "'refund_amount',i.refund_amount,'notes',i.notes)order by i.id)from erp.sales_return_items i where i.return_id=%s))",(ident,ident)).fetchone()[0]

def fixture(cur,today,historical=False,two=False,qty='2',refund='40',sale_qty='4'):
    if historical:
        at=(source.fg.ax.r1.now(cur)-timedelta(days=366,hours=3)).replace(microsecond=123456)
        source.fg.ax.boundary.historical.prior.set_open_period(cur,at.date()-timedelta(days=2))
        f=note.stock(cur,today,1000,at);note.posted(cur,f,sale_qty,'20')
        f['destination']=f['location'];f['bank']=str(source.bc.bank_account(cur,'RETEDIT-'+uuid.uuid4().hex[:8]))
        f['allocations']=returns.read(cur,f)['page']['rows'];physical=at+timedelta(hours=2)
    else:
        f=returns.fixture(cur,today,two);physical=source.fg.ax.r1.now(cur).replace(microsecond=123456)
    p,v=returns.payload(cur,f,qty=qty,refund=refund);p['physical_at']=physical.isoformat()
    if two:
        p['items'].append(dict(p['items'][0],allocation_id=f['allocations'][1]['allocation_id']))
    f['return']=cmd.command(cur,'RETURN',p,v)['return_id']
    f['original']=workspace(cur,f)['document'];f['original_fact']=original_fact(cur,f['return'])
    f['positions']={str(k):v for k,v in returns.positions(cur,f).items()}
    f['accounts']=cmd.accounts(cur);f['sale_fact']=note.unchanged_facts(cur,f['sale'])
    return f

def payload(cur,f,qty='1',refund='20',return_id=None,subject=None,**changes):
    w=workspace(cur,f,return_id,subject);d=w['document']
    lines=[{k:row[k]for k in ('allocation_id','location_id','qty_pcs','quality_grade','refund_amount','notes')}for row in d['items']]
    lines[0].update(qty_pcs=str(qty),refund_amount=str(refund))
    replacement=dict(physical_at=d['physical_at'],notes=d['notes'],items=lines);replacement.update(changes)
    return dict(sale_id=f['sale'],return_id=d['id'],review_token=w['source']['review_token'],return_review_token=w['return_review_token'],
        change_reason='Retur asal dan barang fisik diperiksa sebelum pembetulan',replacement=replacement),w['source']['row_version']

def check(cur,f,p,r,key=None):
    assert r['contract_version']=='cp7.sales-return-correction.v1'and r['kind']=='COMMITTED_OUTCOME'and r['action']=='RETURN_CORRECT'
    assert r['sale_id']==f['sale']and r['original_return_id']==p['return_id']and r['original_return_status']=='REVERSED'
    assert r['return_id']!=p['return_id']and r['return_status']=='POSTED'and r['production_go']is False
    resolved=navigation.read(cur,'SALES_RETURN',r['return_id'])
    assert resolved['document']['focus']==dict(kind='SALES_RETURN',id=r['return_id'],page_offset=r['return_page_offset'])
    l=r['link'];assert l['original_id']==p['return_id']and l['replacement_id']==r['return_id']and l['sale_id']==f['sale']
    if key is not None:assert r['request_id']==l['request_id']==str(key)
    w=workspace(cur,f,r['return_id']);old=workspace(cur,f,p['return_id']);d=w['document']
    assert d['status']=='POSTED'and old['document']['status']=='REVERSED'
    assert w['previous']['document']==old['document']and old['next']['document']==d
    assert d['notes']==p['replacement']['notes']and cur.execute('select physical_at=%s::timestamptz from erp.sales_returns where id=%s',(p['replacement']['physical_at'],r['return_id'])).fetchone()[0]
    actual=sorted(({k:line[k]for k in('allocation_id','location_id','qty_pcs','quality_grade','refund_amount','notes')}for line in d['items']),key=lambda x:x['allocation_id'])
    expected=sorted(copy.deepcopy(p['replacement']['items']),key=lambda x:x['allocation_id'])
    for x in expected:x['refund_amount']=f"{D(x['refund_amount']):.2f}"
    assert actual==expected,(actual,expected)
    assert original_fact(cur,f['return'])==f['original_fact']and note.unchanged_facts(cur,f['sale'])==f['sale_fact']
    assert not cur.execute('select exists(select 1 from cp7_sales.command_context)or exists(select 1 from '+bundle.SCHEMA+'.context)').fetchone()[0]
    assert w['eligible']and w['can_correct']and not old['eligible']
    if l['time_restatement']:
        t=l['time_restatement']
        def lines(ident):return sorted(cur.execute('select account_id,debit,credit,description,customer_id,vendor_id,contractor_id,po_id,product_id from erp.journal_lines where journal_entry_id=%s',(ident,)).fetchall(),key=str)
        inverse=lines(t['inverse_journal_id']);neutral=lines(t['neutral_journal_id']);effective=lines(t['effective_journal_id'])
        assert effective==inverse and neutral==sorted([(a,c,de,*dims)for a,de,c,*dims in inverse],key=str)
    return w

def year_fixture(cur,today):
    first=(source.fg.ax.r1.now(cur)-timedelta(days=366,hours=1)).replace(microsecond=123456)
    source.fg.ax.boundary.historical.prior.set_open_period(cur,first.date()-timedelta(days=2))
    f=note.stock(cur,today,48+12*364+100,first-timedelta(days=1));f['sale_at']=first.isoformat();note.posted(cur,f,'48','10')
    f['destination']=f['location'];f['allocations']=returns.read(cur,f)['page']['rows']
    p,v=returns.payload(cur,f,qty='24',refund='240');p['physical_at']=(first+timedelta(hours=1)).isoformat()
    f['return']=cmd.command(cur,'RETURN',p,v)['return_id'];f['later_ids']=[]
    f['original']=workspace(cur,f)['document'];f['original_fact']=original_fact(cur,f['return']);f['sale_fact']=note.unchanged_facts(cur,f['sale'])
    for n in range(364):
        later=dict(f,tag=f['tag']+'-L'+str(n+1),sale_at=(first+timedelta(days=n+1)).isoformat());note.posted(cur,later,'12','10')
        f['later_ids'].append(str(cur.execute("select m.id from erp.fg_stock_movements m join erp.sales_items i on i.id=m.source_id where i.sale_id=%s and m.movement_type='SALE'",(later['sale'],)).fetchone()[0]))
    f['before_book']=note.complete_book(cur,f);f['before_lot']=note.complete_lot_card(cur,f);f['available_before']=cmd.available(cur,f)
    return f

def year_check(cur,f,p,r,before_book=None,before_lot=None,after_book=None,after_lot=None):
    check(cur,f,p,r)
    bb=before_book if before_book is not None else f['before_book'];bl=before_lot if before_lot is not None else f['before_lot']
    ab=after_book if after_book is not None else note.complete_book(cur,f);al=after_lot if after_lot is not None else note.complete_lot_card(cur,f)
    assert set(bb)==set(ab)==set(bl)==set(al)and len(bb)==367
    for ident in f['later_ids']:
        for field in('official_physical_after','book_physical_after','official_available_after','book_available_after'):
            assert D(ab[ident][field])-D(bb[ident][field])==12,(ident,field)
        for field in('physical_balance','available_balance'):assert D(al[ident][field])-D(bl[ident][field])==12,(ident,field)
        assert ab[ident]['physical_delta']==bb[ident]['physical_delta']=='-12'and ab[ident]['book_order']==bb[ident]['book_order']
    assert all(ab[i]['book_order']==bb[i]['book_order']and ab[i]['physical_at']==bb[i]['physical_at']and ab[i]['source_id']==bb[i]['source_id']for i in bb)
    origin=[row for row in ab.values()if row['source_type']=='SALES_RETURN_ITEM'and row['correction_count']=='1']
    assert len(origin)==1 and origin[0]['original_physical_delta']=='24'and origin[0]['physical_delta']=='36'
    assert cmd.available(cur,f)==f['available_before']+12
    for query in(dict(offset=25,limit=5,movement_types=['SALE']),dict(**{'from':f['sale_at']},movement_types=['SALE'])):
        for row in note.book(cur,f,**query)['page']['rows']:
            assert row['official_physical_after']==ab[row['id']]['official_physical_after']and row['book_physical_after']==ab[row['id']]['book_physical_after']
    return dict(status='PASS',all364_later_prefixes_plus12=True,current_available_before=f['available_before'],current_available_after=f['available_before']+12,
      Original_return_inputs_sale_inputs_and_unrelated_manual_ranks_unchanged=True,raw_before_book=list(bb.values()),raw_after_book=list(ab.values()),
      raw_before_lot=list(bl.values()),raw_after_lot=list(al.values()),production_SLA=False)

def cases(cur,today):
    def exact():
        f=fixture(cur,today);p,v=payload(cur,f);w=check(cur,f,p,correct(cur,p,v))
        assert returns.positions(cur,f)=={(f['location'],'GRADE_A'):6,(f['destination'],'GRADE_A'):1}
        assert cmd.delta(f['accounts'],cmd.accounts(cur))=={cmd.mapping(cur,'AR_CUSTOMER'):D(20),cmd.mapping(cur,'SALES_REVENUE'):D(-20),cmd.mapping(cur,'FG_INVENTORY'):D(-10),cmd.mapping(cur,'COGS'):D(10)}
        assert w['financial']['open_balance']=='60.00'
        return dict(status='PASS',Native_return2_to1_stock_minus1_AR_plus20_COGS_plus10=True,original_inputs_unchanged=True)
    def increase():
        f=fixture(cur,today);p,v=payload(cur,f,'3','60');w=check(cur,f,p,correct(cur,p,v));assert w['financial']['open_balance']=='20.00'and returns.positions(cur,f)[(f['destination'],'GRADE_A')]==3
        return dict(status='PASS',Native_return2_to3_with_current_capacity=True)
    def full():
        f=fixture(cur,today,qty='4',refund='80');w=workspace(cur,f);assert w['financial']['net_total']=='0.00'and w['allocations']['total']=='1'and w['current_allocations'][0]['replacement_capacity']=='4'
        p,v=payload(cur,f,'3','60');check(cur,f,p,correct(cur,p,v));return dict(status='PASS',fully_returned_source_includes_own_capacity_and_corrects=True)
    def two():
        f=fixture(cur,today,two=True,qty='1',refund='20');p,v=payload(cur,f,'2','40');w=check(cur,f,p,correct(cur,p,v))
        assert len(w['document']['items'])==2 and sorted(x['qty_pcs']for x in w['document']['items'])==['1','2']
        assert w['financial']['return_total']=='60.00';return dict(status='PASS',duplicate_product_lot_independent_allocation_rows_preserved=True)
    def grade():
        f=fixture(cur,today);destination=returns.location(cur,'Checked replacement return warehouse');p,v=payload(cur,f)
        p['replacement']['items'][0].update(location_id=destination,quality_grade='GRADE_B');check(cur,f,p,correct(cur,p,v))
        assert returns.positions(cur,f)=={(f['location'],'GRADE_A'):6,(destination,'GRADE_B'):1}
        return dict(status='PASS',Native_grade_A_to_B_and_checked_destination_without_folding_different_scope=True)
    def micros():
        f=fixture(cur,today,historical=True);p,v=payload(cur,f);w=check(cur,f,p,correct(cur,p,v));assert w['document']['physical_at']==f['original']['physical_at']and '123456'in w['document']['physical_at']
        return dict(status='PASS',original_physical_microseconds_preserved_in_inverse_replacement=True)
    def date():
        f=fixture(cur,today,historical=True)
        original=cur.execute('select physical_at from erp.sales_returns where id=%s',(f['return'],)).fetchone()[0]
        p,v=payload(cur,f,physical_at=(original+timedelta(days=1)).isoformat());check(cur,f,p,correct(cur,p,v))
        assert cur.execute("select economic_date=(%s::timestamptz at time zone 'Asia/Jakarta')::date from erp.journal_entries where source_type='SALES_RETURN'and source_id=%s",(p['replacement']['physical_at'],workspace(cur,f)['next']['document']['id'])).fetchone()[0]
        return dict(status='PASS',actual_return_economic_date_plus_one_original_old_card_zero_new_dated_row=True)
    def year():
        f=year_fixture(cur,today);p,v=payload(cur,f,'36','360');return year_check(cur,f,p,correct(cur,p,v))
    def failure():
        f=fixture(cur,today,historical=True);p,v=payload(cur,f)
        cur.execute("create function public.cp7_return_last_fail()returns trigger language plpgsql as $$begin if new.source_type='SALES_RETURN'and new.source_id<>'"+f['return']+"'::uuid then raise exception 'CP7_TEST_RETURN_LAST_POST_FAILURE';end if;return new;end$$;create trigger cp7_return_last_fail before insert on erp.journal_entries for each row execute function public.cp7_return_last_fail()",prepare=False)
        before=b.boundary.snapshot(cur);private=private_state(cur);auth.refused(cur,lambda:correct(cur,p,v),'CP7_TEST_RETURN_LAST_POST_FAILURE')
        assert b.boundary.snapshot(cur)==before and private_state(cur)==private and workspace(cur,f)['document']['status']=='POSTED'
        return dict(status='PASS',actual_last_Native_post_failure_rolls_back_original_inverse_stock_HPP_journals_lineage_and_request=True)
    def stale():
        f=fixture(cur,today);other=fixture(cur,today);p,v=payload(cur,f);bad=copy.deepcopy(p);bad['sale_id']=other['sale'];before=b.boundary.snapshot(cur)
        auth.refused(cur,lambda:correct(cur,bad,v),'CP7_RETURN_CORRECTION_NOT_FOUND');assert b.boundary.snapshot(cur)==before
        later=dict(f,tag=f['tag']+'-OTHER',sale_at=source.fg.ax.r1.now(cur).isoformat());note.posted(cur,later,'1','20');before=b.boundary.snapshot(cur)
        auth.refused(cur,lambda:correct(cur,p,v),'CP7_RETURN_CORRECTION_STALE_REVIEW');assert b.boundary.snapshot(cur)==before
        return dict(status='PASS',foreign_parent_and_actual_same_lot_other_sale_stock_change_refused_before_inverse=True)
    def authority():
        f=fixture(cur,today);subject,_=auth.custom_actor(cur);role=cur.execute("select id from erp.app_roles where role_code='ADMIN'").fetchone()[0]
        cur.execute('update erp.app_users set role_id=%s where auth_user_id=%s',(role,subject));p,v=payload(cur,f,subject=subject);key=uuid.uuid4();r=correct(cur,p,v,key,subject);check(cur,f,p,r,key)
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.hpp.view'",(role,));before=b.boundary.snapshot(cur)
        auth.refused(cur,lambda:correct(cur,p,v,key,subject),'CP7_RETURN_CORRECTION_DENIED');assert b.boundary.snapshot(cur)==before
        bundle.verify(cur);return dict(status='PASS',current_HPP_permission_rechecked_before_cached_outcome=True,exact_private_caps_and_all4_frozen_Native_helpers=True)
    def fields():
        f=fixture(cur,today);p,v=payload(cur,f);before=b.boundary.snapshot(cur)
        for key,value in [('qty_pcs','0'),('refund_amount','20.001'),('unit_hpp_snapshot','0')]:
            bad=copy.deepcopy(p);bad['replacement']['items'][0][key]=value;auth.refused(cur,lambda:correct(cur,bad,v),'CP7_SALES_RETURN_LINES');assert b.boundary.snapshot(cur)==before
        bad=copy.deepcopy(p);bad['replacement']['items']*=2;auth.refused(cur,lambda:correct(cur,bad,v),'CP7_SALES_RETURN_DUPLICATE_ALLOCATION');assert b.boundary.snapshot(cur)==before
        unchanged,ver=payload(cur,f,'2','40');auth.refused(cur,lambda:correct(cur,unchanged,ver),'CP7_RETURN_CORRECTION_UNCHANGED');assert b.boundary.snapshot(cur)==before
        too_much,ver=payload(cur,f,'5','100');auth.refused(cur,lambda:correct(cur,too_much,ver),'');assert b.boundary.snapshot(cur)==before
        returns.payments.pay(cur,f,'40');bad,ver=payload(cur,f,'3','60');before=b.boundary.snapshot(cur);private=private_state(cur)
        auth.refused(cur,lambda:correct(cur,bad,ver),'');assert b.boundary.snapshot(cur)==before and private_state(cur)==private
        return dict(status='PASS',closed_fields_exact_cents_unique_allocation_noop_Native_quantity_and_paid_refund_caps=True)
    def chain():
        f=fixture(cur,today);p,v=payload(cur,f);key=uuid.uuid4();r=correct(cur,p,v,key);check(cur,f,p,r,key);before=b.boundary.snapshot(cur);private=private_state(cur)
        assert correct(cur,p,v,key)==r and b.boundary.snapshot(cur)==before and private_state(cur)==private
        changed=copy.deepcopy(p);changed['replacement']['items'][0]['refund_amount']='19.99';auth.refused(cur,lambda:correct(cur,changed,v,key),'CP7_RETURN_CORRECTION_REQUEST_CHANGED');assert b.boundary.snapshot(cur)==before
        restore,version=payload(cur,f,'2','40',return_id=r['return_id']);restored=correct(cur,restore,version);check(cur,f,restore,restored)
        assert cmd.accounts(cur)==f['accounts']and {str(k):x for k,x in returns.positions(cur,f).items()}==f['positions']
        assert cur.execute('select count(*)from '+bundle.SCHEMA+'.links where sale_id=%s',(f['sale'],)).fetchone()[0]==2
        return dict(status='PASS',exact_UUID_one_effect_changed_intent_refused_reviewed_restore_new_document_two_links=True)
    def history():
        f=fixture(cur,today,historical=True,sale_qty='40')
        for _ in range(26):
            peer,ver=returns.payload(cur,f,qty='1',refund='0');cmd.command(cur,'RETURN',peer,ver)
        p,v=payload(cur,f);r=correct(cur,p,v);check(cur,f,p,r)
        assert r['return_page_offset']==25
        page=returns.read(cur,f,'RETURNS',offset=25)['page'];assert r['return_id']in[x['id']for x in page['rows']]
        before=b.boundary.snapshot(cur);private=private_state(cur)
        for sql in('update '+bundle.SCHEMA+'.links set reason=reason','delete from '+bundle.SCHEMA+'.links','truncate '+bundle.SCHEMA+'.links'):
            auth.refused(cur,lambda:cur.execute(sql),'CP7_RETURN_CORRECTION_HISTORY_IMMUTABLE')
        t=r['link']['time_restatement'];assert t
        for kind in('RETURN_CORRECTION_TIME_NEUTRAL','RETURN_CORRECTION_EFFECTIVE'):
            navigation.exact(cur,kind,t['inverse_journal_id'],'SALE',f['sale'],('SALES_RETURN',f['return']))
        auth.refused(cur,lambda:navigation.read(cur,'RETURN_CORRECTION_EFFECTIVE',f['return']),'CP7_TRANSACTION_SOURCE_UNAVAILABLE')
        original_movement=str(cur.execute("select m.id from erp.fg_stock_movements m join erp.sales_return_items i on i.id=m.source_id where i.return_id=%s and m.movement_type='SALE_RETURN'",(f['return'],)).fetchone()[0])
        navigation.exact(cur,'FG_MOVEMENT_REVERSAL',original_movement,'SALE',f['sale'],('SALES_RETURN',f['return']))
        assert b.boundary.snapshot(cur)==before and private_state(cur)==private
        return dict(status='PASS',immutable_links_update_delete_truncate_exact_journal_and_FG_inverse_sources_readonly_fake_UUID_refused=True,
          actual26_Native_peer_returns_replacement_source_and_outcome_page25=True)
    def downstream():
        f=fixture(cur,today);later=dict(f,tag=f['tag']+'-USED',location=f['destination'],sale_at=source.fg.ax.r1.now(cur).isoformat());note.posted(cur,later,'2','20')
        assert (f['destination'],'GRADE_A')not in returns.positions(cur,f)
        p,v=payload(cur,f);before=b.boundary.snapshot(cur);private=private_state(cur);auth.refused(cur,lambda:correct(cur,p,v),'')
        assert b.boundary.snapshot(cur)==before and private_state(cur)==private and workspace(cur,f)['document']['status']=='POSTED'
        return dict(status='PASS',accepted_Native_already_used_return_stock_refusal_preserved_complete_no_effect=True)
    def closed():
        import cp7_p13_finance_probe as finance
        f=fixture(cur,today,historical=True);through=today-timedelta(days=1);source.fg.ax.boundary.historical.prior.set_open_period(cur,through)
        before=cur.execute('select balance_date,account_id,debit_total,credit_total from erp.account_daily_balances where balance_date<=%s order by balance_date,account_id',(through,)).fetchall()
        p,v=payload(cur,f);r=correct(cur,p,v);check(cur,f,p,r)
        assert cur.execute('select balance_date,account_id,debit_total,credit_total from erp.account_daily_balances where balance_date<=%s order by balance_date,account_id',(through,)).fetchall()==before
        assert cur.execute('select closed_through from erp.accounting_period_control where singleton_id=1').fetchone()[0]==through
        t=r['link']['time_restatement'];assert t and cur.execute('select transaction_date>%s from erp.journal_entries where id=%s',(through,t['effective_journal_id'])).fetchone()[0]
        report=finance.read(cur,today);assert report['snapshot']['performance']['sales_revenue_reconciled']
        return dict(status='PASS',closed_daily_GL_unchanged_original_economic_date_Native_open_posting_date_and_owner_report_reconciled=True)
    functions=(exact,increase,full,two,grade,micros,date,year,failure,stale,authority,fields,chain,history,downstream,closed)
    assert len(functions)==len(NAMES)==REQUIRED['native'];return [('CP7_RETURN_CORRECTION_'+n,f)for n,f in zip(NAMES,functions)]

def races(tools,today):
    def compete(same=False):
        with tools.connect()as conn,conn.cursor()as cur:f=fixture(cur,today);p,v=payload(cur,f);conn.commit()
        gate=threading.Barrier(2);keys=[uuid.uuid4(),uuid.uuid4()]
        if same:keys[1]=keys[0]
        def send(key):
            with tools.connect()as conn,conn.cursor()as cur:
                gate.wait()
                try:r=correct(cur,p,v,key);conn.commit();return r
                except psycopg.Error as e:conn.rollback();return str(e)
        with ThreadPoolExecutor(max_workers=2)as pool:rows=[j.result(60)for j in[pool.submit(send,k)for k in keys]]
        wins=[r for r in rows if isinstance(r,dict)];losses=[r for r in rows if isinstance(r,str)]
        if same:assert len(wins)==2 and wins[0]==wins[1]
        else:assert len(wins)==len(losses)==1 and'CP7_RETURN_CORRECTION_STALE_REVIEW'in losses[0],rows
        with tools.connect()as conn,conn.cursor()as cur:
            check(cur,f,p,wins[0]);assert cur.execute('select count(*)from '+bundle.SCHEMA+'.links where original_id=%s',(f['return'],)).fetchone()[0]==1
            assert cur.execute('select count(*)from '+bundle.SCHEMA+'.requests where request_id=any(%s::uuid[])',(keys,)).fetchone()[0]==1
        return dict(status='PASS',real_concurrent_requests=True,same_UUID=same,one_Native_effect_and_history_link=True)
    def changed_wait(stock=False):
        with tools.connect()as conn,conn.cursor()as cur:
            f=fixture(cur,today);subject=None;role=None
            if not stock:
                subject,_=auth.custom_actor(cur);role=cur.execute("select id from erp.app_roles where role_code='ADMIN'").fetchone()[0]
                cur.execute('update erp.app_users set role_id=%s where auth_user_id=%s',(role,subject))
            p,v=payload(cur,f,subject=subject);key=uuid.uuid4();conn.commit()
        with tools.connect()as holder,holder.cursor()as held:
            held.execute("select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0))");holder_pid=held.execute('select pg_backend_pid()').fetchone()[0];pid=[];started=threading.Event()
            def send():
                with tools.connect()as conn,conn.cursor()as cur:
                    pid.append(cur.execute('select pg_backend_pid()').fetchone()[0]);started.set()
                    try:r=correct(cur,p,v,key,subject);conn.commit();return r
                    except psycopg.Error as e:conn.rollback();return str(e)
            with ThreadPoolExecutor(max_workers=1)as pool:
                job=pool.submit(send);assert started.wait(5);observed=False
                try:
                    deadline=time.monotonic()+8
                    while time.monotonic()<deadline:
                        held.execute('select pg_stat_clear_snapshot()')
                        if holder_pid in held.execute('select pg_blocking_pids(%s)',(pid[0],)).fetchone()[0]:observed=True;break
                        time.sleep(.02)
                    assert observed,'RETURN_CORRECTION_ACTUAL_FG_LOCK_WAIT_NOT_OBSERVED'
                    if stock:
                        later=dict(f,tag=f['tag']+'-RACE',sale_at=source.fg.ax.r1.now(held).isoformat());note.posted(held,later,'1','20')
                    else:held.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='sales.return.post'",(role,))
                    b.api.admin(held);before=b.boundary.snapshot(held);private=private_state(held);holder.commit()
                finally:holder.rollback()
                result=job.result(60)
        assert isinstance(result,str)and('CP7_RETURN_CORRECTION_STALE_REVIEW'if stock else'CP7_SALES_WRITE_DENIED')in result,result
        with tools.connect()as conn,conn.cursor()as cur:
            assert b.boundary.snapshot(cur)==before and private_state(cur)==private
            assert workspace(cur,f)['document']==f['original']
        return dict(status='PASS',exact_holder_worker_FG_lock_wait_observed=True,actual_Native_same_lot_stock_change=stock,current_permission_revoke=not stock,complete_post_change_boundary_unchanged=True)
    return [('CP7_RETURN_CORRECTION_RACE_SAME_UUID',lambda:compete(True)),('CP7_RETURN_CORRECTION_RACE_COMPETING',compete),
      ('CP7_RETURN_CORRECTION_RACE_AUTH_RETIRE',changed_wait),('CP7_RETURN_CORRECTION_RACE_STOCK_CHANGE',lambda:changed_wait(True))]

def http_cases(http,today):
    def flow():
        owner=http.login('OWNER','return-correction-owner')
        with http.connect()as conn,conn.cursor()as cur:f=fixture(cur,today,historical=True);p,v=payload(cur,f);conn.commit()
        key=uuid.uuid4();args=dict(p_payload=p,p_request=str(key),p_expected=v);assert http.anon_rpc(RPC,args)['status']in(401,403)
        response=owner.rpc(RPC,args);assert response['status']==200,response;r=response['body'];assert owner.rpc(RPC,args)['body']==r
        w=owner.rpc(READ,dict(p_query=dict(sale_id=f['sale'],return_id=r['return_id'])));assert w['status']==200 and w['body']['previous']['document']['id']==f['return'],w
        with http.connect()as conn,conn.cursor()as cur:check(cur,f,p,r,key);conn.rollback()
        changed=copy.deepcopy(args);changed['p_payload']['replacement']['items'][0]['refund_amount']='19.99';assert owner.rpc(RPC,changed)['status']>=400
        return dict(status='PASS',actual_Auth_atomic_return_UUID_replay_adjacent_history_anonymous_and_changed_intent_refused=True)
    def year():
        owner=http.login('OWNER','return-correction-year-owner')
        with http.connect()as conn,conn.cursor()as cur:f=year_fixture(cur,today);p,v=payload(cur,f,'36','360');before=b.boundary.snapshot(cur);private=private_state(cur);conn.commit()
        observations=[];bb=note.complete_actual_http_history(owner,f,'BOOK','BEFORE_COMMIT',observations);bl=note.complete_actual_http_history(owner,f,'LOT','BEFORE_COMMIT',observations)
        args=dict(p_payload=p,p_request=str(uuid.uuid4()),p_expected=v);start=time.monotonic_ns();response=owner.rpc(RPC,args);elapsed=round((time.monotonic_ns()-start)/1_000_000,3)
        if response['status']!=200:
            with http.connect()as conn,conn.cursor()as cur:rollback=b.boundary.snapshot(cur)==before and private_state(cur)==private;conn.rollback()
            return dict(status='INCOMPLETE',actual_HTTP_status=response['status'],original_failed_body=response['body'],command_attempts=1,no_retry=True,complete_rollback=rollback,actual_HTTP_ms=elapsed,actual_read_pages=observations,production_SLA=False)
        ab=note.complete_actual_http_history(owner,f,'BOOK','AFTER_SEPARATE_REQUESTS',observations);al=note.complete_actual_http_history(owner,f,'LOT','AFTER_SEPARATE_REQUESTS',observations)
        with http.connect()as conn,conn.cursor()as cur:r=year_check(cur,f,p,response['body'],bb,bl,ab,al);after=b.boundary.snapshot(cur);saved=private_state(cur);conn.rollback()
        assert owner.rpc(RPC,args)['body']==response['body']
        with http.connect()as conn,conn.cursor()as cur:assert b.boundary.snapshot(cur)==after and private_state(cur)==saved;conn.rollback()
        return dict(r,actual_Auth_committed_year_readback=True,actual_HTTP_ms=elapsed,actual_read_pages=observations,confirmed_UUID_replay_no_second_effect=True)
    def revoke():
        admin=http.login('ADMIN','return-correction-admin')
        with http.connect()as conn,conn.cursor()as cur:f=fixture(cur,today);p,v=payload(cur,f);conn.commit()
        args=dict(p_payload=p,p_request=str(uuid.uuid4()),p_expected=v);response=admin.rpc(RPC,args);assert response['status']==200,response
        with http.connect()as conn,conn.cursor()as cur:cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(admin.auth_user_id,));conn.commit()
        assert admin.rpc(RPC,args)['status']==403 and admin.rpc(READ,dict(p_query=dict(sale_id=f['sale'],return_id=response['body']['return_id'])))['status']==403
        return dict(status='PASS',current_actual_Auth_deactivation_denies_cached_writer_and_history=True)
    return [('CP7_RETURN_CORRECTION_HTTP_ATOMIC_REPLAY',flow),('CP7_RETURN_CORRECTION_HTTP_YEAR_364',year),('CP7_RETURN_CORRECTION_HTTP_CURRENT_RETIRE',revoke)]
