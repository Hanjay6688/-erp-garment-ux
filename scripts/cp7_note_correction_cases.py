"""Predeclared owning-note oracles. All economic effects use Native writers.

Master identities, deliberate access/close changes and injected failure triggers
are isolated test controls. No fixture inserts posted stock, AR or HPP results.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal as D
import copy,json,threading,time,uuid
import psycopg
import cp7_sales_draft_cases as drafts
import cp7_sales_return_cases as returned
import cp7_f03_e01_cases as e01
import cp7_finance_cases as finance
import cp6_ao_ap_installed as imports
import cp6_initial_import_prepayment_trial as prepaid
import cp7_note_correction_verify as ownership
cmd,source,b,auth=drafts.cmd,drafts.source,drafts.b,drafts.auth
MANIFEST=json.loads((ownership.bundle.ROOT/'scripts/cp7_note_correction_manifest.json').read_text())
assert MANIFEST['schema']=='cp7-owning-note-correction-native-manifest-v1'
REQUIRED=MANIFEST['required_counts']
EXPECTED=MANIFEST['expected_case_executions']
assert EXPECTED==36==sum(REQUIRED.values())

def correct(cur,p,version,key=None,subject=None):
 auth.actor(cur,subject)
 out=cur.execute('select public.erp_cp7_correct_note_v1(%s,%s,%s)',(json.dumps(p),key or uuid.uuid4(),version)).fetchone()[0]
 b.api.admin(cur);return out

def history(cur,sale,subject=None):
 auth.actor(cur,subject);out=cur.execute('select public.erp_cp7_get_note_correction_v2(%s)',(sale,)).fetchone()[0];b.api.admin(cur);return out

def book(cur,f,**q):
 auth.actor(cur);out=cur.execute('select public.erp_cp7_get_fg_book_v2(%s)',(json.dumps(dict(q=f['sku'],limit=100,offset=0)|q),)).fetchone()[0];b.api.admin(cur);return out

def lot_card(cur,f,subject=None,**q):
 auth.actor(cur,subject);out=cur.execute('select public.erp_cp7_get_fg_ledger_v2(%s)',(json.dumps(dict(product_id=f['product'],lot_id=f['lot'],location_id=f['location'],quality_grade='GRADE_A',purpose='CARD',limit=100,offset=0)|q),)).fetchone()[0];b.api.admin(cur);return out

def complete_lot_card(cur,f):
 result={};off=0
 while True:
  w=lot_card(cur,f,offset=off)
  for r in w['page']['rows']:assert r['id']not in result;result[r['id']]=r
  if w['page']['next_offset']is None:break
  off=w['page']['next_offset']
 assert len(result)==int(w['page']['total'])
 return result

def edit(cur,f,qty=None,price=None):
 d=source.read(cur,f)['detail']
 p=dict(sale_id=d['id'],review_token=d['review_token'],sale_number=d['number'],customer_id=d['customer_id'],source_location_id=d['location_id'],sale_date=d['physical_at'],due_date=d['due_date'],payment_terms=d['payment_terms'],notes=d['notes'],change_reason='Correct the original physical note after checking all affected records',items=[dict(product_id=i['product_id'],qty_pcs=qty if qty is not None and n==0 else i['qty_pcs'],unit_price_snapshot=price if price is not None and n==0 else i['financial']['unit_price'],discount_amount=i['financial']['discount'],notes=i['notes'])for n,i in enumerate(d['items'])])
 return p,d['row_version']

def posted(cur,f,qty='4',price='20'):
 drafts.create(cur,f,drafts.payload(f,qty,price));p,v=cmd.review(cur,f);cmd.command(cur,'POST',p,v);return f

def stock(cur,today,qty=1200,at=None):
 at=at or source.fg.ax.r1.now(cur)-timedelta(hours=2)
 product,_=source.fg.ax.owner_only_model_product(cur,effective_from=at-timedelta(days=1))
 receipt=source.fg.ax.post(cur,dict(source_kind='FOUND_AT_OPNAME',product_id=product,location_id=source.fg.base.LOCATION,qty_pcs=qty,physical_at=at.isoformat(),reason='Declared isolated physical stock',owner_unit_value='10',owner_value_reason='Declared owner value; no inferred or fabricated production cost'))
 b.api.admin(cur)
 return dict(product=product,lot=str(cur.execute('select lot_id from erp.fg_unsourced_receipts_v1 where id=%s',(receipt['receipt_id'],)).fetchone()[0]),location=source.fg.base.LOCATION,at=at.isoformat(),sku=cur.execute('select sku from erp.products where id=%s',(product,)).fetchone()[0],tag='NOTE-'+uuid.uuid4().hex[:12],customer=str(source.fg.base.create_customer(cur,'NOTE-'+uuid.uuid4().hex[:12])),sale_at=(at+timedelta(hours=1)).isoformat())

def complete_book(cur,f):
 result=[];offset=0
 while True:
  page=book(cur,f,offset=offset)
  result+=page['page']['rows']
  if page['page']['next_offset']is None:break
  offset=page['page']['next_offset']
 assert len(result)==int(page['page']['total'])and len({r['id']for r in result})==len(result)
 return {r['id']:r for r in result}

def unchanged_facts(cur,sale):
 # Compare the exact Native microseconds in one canonical rendering. Browser
 # timezone changes only presentation; it must not alter this fact oracle.
 timezone=cur.execute('show TimeZone').fetchone()[0]
 cur.execute("select set_config('TimeZone','UTC',true)")
 try:return cur.execute("select jsonb_build_object('header',(select to_jsonb(h)-array['status','paid_total','row_version','updated_at']from erp.sales_headers h where id=%s),'items',(select jsonb_agg(to_jsonb(i)order by id)from erp.sales_items i where sale_id=%s))",(sale,sale)).fetchone()[0]
 finally:cur.execute("select set_config('TimeZone',%s,true)",(timezone,))

def snapshot(cur):
 b.api.admin(cur)
 return dict(native=b.boundary.snapshot(cur),metadata=cur.execute("select jsonb_build_object('requests',(select coalesce(jsonb_agg(to_jsonb(r)order by actor,request_id),'[]')from cp7_note.requests r),'revisions',(select coalesce(jsonb_agg(to_jsonb(r)order by id),'[]')from cp7_note.revisions r),'context',(select coalesce(jsonb_agg(to_jsonb(r)),'[]')from cp7_note.context r),'journal_restatements',(select coalesce(jsonb_agg(to_jsonb(r)order by inverse_journal_id),'[]')from cp7_note.journal_restatements r),'payment_replays',(select coalesce(jsonb_agg(to_jsonb(r)order by previous_payment_id),'[]')from cp7_note.payment_replays r),'links',(select coalesce(jsonb_agg(to_jsonb(r)order by member_id),'[]')from cp7_fg.correction_movements r))").fetchone()[0])

def inverse_date_truth(cur):
 rows=cur.execute("select check_name,issue_count from erp.run_v267_financial_truth_checks()where check_name='V2620U_JOURNAL_REVERSAL_BUSINESS_DATE'").fetchall()
 assert rows==[('V2620U_JOURNAL_REVERSAL_BUSINESS_DATE',0)],rows

def period_accounts(cur,start,end,clock):
 assert clock in ('economic_date','transaction_date')
 return {str(k):v for k,v in cur.execute('select l.account_id,sum(l.debit-l.credit)from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where j.status in(\'POSTED\',\'REVERSED\')and j.'+clock+' between %s and %s group by l.account_id having sum(l.debit-l.credit)<>0',(start,end))}

def wallet_note(cur,today,at=None,cash_at=None):
 f=stock(cur,today,10,at or source.fg.ax.r1.now(cur)-timedelta(days=2));posted(cur,f)
 w=prepaid.fixture(imports,cur,today,'CUSTOMER',party=f['customer'],bill=None)
 prepaid.manage(imports,cur,w,'APPLY',today-timedelta(days=1),target_id=f['sale'],amount='25')
 f['bank']=str(source.bc.bank_account(cur,'NOTE-WALLET-'+uuid.uuid4().hex[:8]))
 cash,cash_version=returned.payments.payment_payload(cur,f,'5')
 if cash_at is not None:cash['payment_date']=cash_at.isoformat()
 cmd.command(cur,'PAYMENT',cash,cash_version)
 assert source.read(cur,f)['detail']['financial']['paid_total']=='30.00'
 assert prepaid.state(imports,cur,w)['remaining_amount']=='42.25'and prepaid.bank(cur,w)==100
 return f,w

def year(cur,today,count):
 first=source.fg.ax.r1.now(cur)-timedelta(days=366,hours=1)
 f=stock(cur,today,max(1200,24+12*count+100),first-timedelta(days=1));f['sale_at']=first.isoformat();posted(cur,f,'24','20')
 root=f['sale'];facts=unchanged_facts(cur,root);ids=[]
 for n in range(count):
  later=dict(f,tag=f['tag']+'-L'+str(n+1),sale_at=(first+timedelta(days=n+1)).isoformat());posted(cur,later,'12','20')
  ids.append(str(cur.execute("select m.id from erp.fg_stock_movements m join erp.sales_items i on i.id=m.source_id where i.sale_id=%s and m.movement_type='SALE'",(later['sale'],)).fetchone()[0]))
 before_lot=complete_lot_card(cur,f);before=complete_book(cur,f);physical_before=cmd.available(cur,f);original_orders={r['id']:r['book_order']for r in before.values()}
 p,v=edit(cur,f,'12');out=correct(cur,p,v);f['sale']=out['sale_id'];after=complete_book(cur,f);after_lot=complete_lot_card(cur,f)
 for ident in ids:
  assert D(after_lot[ident]['physical_balance'])-D(before_lot[ident]['physical_balance'])==12
  assert D(after_lot[ident]['available_balance'])-D(before_lot[ident]['available_balance'])==12
  for field in ('official_physical_after','book_physical_after','official_available_after','book_available_after'):
   assert D(after[ident][field])-D(before[ident][field])==12,(ident,field,before[ident],after[ident])
  assert after[ident]['physical_delta']=='-12'and after[ident]['correction_count']=='0'
 assert all(after[i]['book_order']==rank for i,rank in original_orders.items())
 original=next(r for r in after.values()if r['source_type']=='SALE_ITEM'and r['correction_count']=='1'and r['original_physical_delta']=='-24')
 assert original['physical_delta']=='-12'and original['reservation_delta']=='0'
 assert cmd.available(cur,f)==physical_before+12 and unchanged_facts(cur,root)==facts
 assert history(cur,root)['current_sale_id']==out['sale_id']and len(history(cur,root)['history'])==1
 for query in (dict(offset=25,limit=5,movement_types=['SALE']),dict(**{'from':(first+timedelta(days=15)).isoformat()},movement_types=['SALE'])):
  page=book(cur,f,**query)
  for r in page['page']['rows']:assert r['book_physical_after']==after[r['id']]['book_physical_after']and r['official_physical_after']==after[r['id']]['official_physical_after']
 return dict(status='PASS',later_balances_checked=count,each_official_and_main_book_delta_pcs=12,source_quantity_pcs=24,effective_quantity_pcs=12,original_fact_rows_immutable=True,original_manual_ranks_unchanged=True,complete_prefix_before_pages_and_filters=True,one_owning_note_command=True,current_available_before=physical_before,current_available_after=physical_before+12)

def cases(cur,today):
 def repeat():
  f=posted(cur,drafts.fixture(cur,today,40),'24');root=f['sale'];first=unchanged_facts(cur,root);p,v=edit(cur,f,'12');key=uuid.uuid4();a=correct(cur,p,v,key);f['sale']=a['sale_id'];p2,v2=edit(cur,f,'18');z=correct(cur,p2,v2);f['sale']=z['sale_id']
  h=history(cur,root);assert h['current_sale_id']==z['sale_id']and[h['revision']for h in h['history']]==['1','2']and cmd.available(cur,f)==22 and unchanged_facts(cur,root)==first
  before=snapshot(cur);assert correct(cur,p,v,key)==a and snapshot(cur)==before
  r=next(r for r in complete_book(cur,f).values()if r['correction_count']=='2');assert r['physical_delta']=='-18'and r['original_physical_delta']=='-24'and r['reservation_delta']=='0'
  return dict(status='PASS',two_revisions_24_to12_to18=True,latest_correction_wins=True,old_request_receipt_replayed_without_second_effect=True,original_facts_preserved=True)
 def financial():
  f=e01.production(cur,today);before=cmd.accounts(cur);posted(cur,f,'20','25');paid=returned.payments.pay(cur,f,'200');f['allocations']=returned.read(cur,f)['page']['rows'];payload,v=returned.payload(cur,f,qty='5',refund='125',destination=f['location']);ret=cmd.command(cur,'RETURN',payload,v)
  original=f['sale'];facts=unchanged_facts(cur,original);p,v=edit(cur,f,'16');out=correct(cur,p,v);f['sale']=out['sale_id'];detail=source.read(cur,f)['detail'];assert detail['financial']['net_total']=='275.00'and detail['financial']['paid_total']=='200.00'and detail['financial']['open_balance']=='75.00'and detail['returned_qty']=='5'
  assert e01.physical(cur,f)==49;e01.expect_delta(cur,f,before,75,275,-165,165,200)
  assert unchanged_facts(cur,original)==facts and cur.execute('select status from erp.sales_payments where id=%s',(paid['payment_id'],)).fetchone()[0]=='REVERSED'and cur.execute('select status from erp.sales_returns where id=%s',(ret['return_id'],)).fetchone()[0]=='REVERSED'
  assert len(history(cur,original)['history'])==1
  inverse_date_truth(cur)
  return dict(status='PASS',actual_native_receipt_cut_sewing_accessory_laundry_QC_cost_source=True,invoice_500_to400=True,retur125_and_cash200_preserved=True,net275_AR75_cash200_COGS165_FG49_value735=True,original_posted_items_immutable=True,atomic_nota_stock_AR_journal_HPP=True)
 def other_warehouse():
  f=returned.fixture(cur,today);ret=returned.returned(cur,f,grade='GRADE_B');returned.payments.pay(cur,f,'30');p,v=edit(cur,f,'3');out=correct(cur,p,v);f['sale']=out['sale_id']
  assert source.read(cur,f)['detail']['financial']['open_balance']=='10.00'and returned.positions(cur,f)=={(f['location'],'GRADE_A'):7,(f['destination'],'GRADE_B'):1}
  active=returned.read(cur,f,'RETURNS')['page']['rows'];assert active[0]['items'][0]['location_id']==f['destination']and active[0]['items'][0]['quality_grade']=='GRADE_B'
  return dict(status='PASS',return_destination_separate_from_source_allocation=True,other_warehouse_grade_B_unchanged=True,cash30_return20_remaining10=True)
 def cents():
  f=drafts.fixture(cur,today,30);posted(cur,f,'13','10.01');p,v=edit(cur,f,'14','10.03');p['items'][0]['discount_amount']='0.04';out=correct(cur,p,v);f['sale']=out['sale_id'];assert source.read(cur,f)['detail']['financial']['gross_total']=='140.38'and cmd.available(cur,f)==16
  return dict(status='PASS',exact_decimal_qty_price_discount=True,invoice='140.38',available=16,no_client_HPP=True)
 def sku():
  f=drafts.fixture(cur,today,30);g=drafts.fixture(cur,today,30);posted(cur,f,'4');later=dict(g,sale_at=(source.fg.ax.r1.now(cur)-timedelta(minutes=2)).isoformat());posted(cur,later,'2');before=complete_book(cur,g);old_order=[str(r[0])for r in cur.execute('select id from erp.fg_stock_movements order by book_order,id')]
  p,v=edit(cur,f,'2');p['items'].append(drafts.payload(g,'3')['items'][0]);out=correct(cur,p,v);f['sale']=out['sale_id'];after=complete_book(cur,g)
  later_card=next(r for r in before.values()if r['movement_type']=='SALE');assert D(after[later_card['id']]['book_physical_after'])==D(later_card['book_physical_after'])-3 and D(after[later_card['id']]['official_physical_after'])==D(later_card['official_physical_after'])-3
  assert cmd.available(cur,f)==28 and cmd.available(cur,g)==25
  remaining=[str(r[0])for r in cur.execute('select id from erp.fg_stock_movements order by book_order,id')if str(r[0])in old_order];assert remaining==old_order
  return dict(status='PASS',added_physical_SKU_has_own_card_at_original_note=True,other_SKU_later_balances_shift_minus3=True,no_manual_book_reset_or_relative_order_loss=True)
 def negative():
  first=source.fg.ax.r1.now(cur)-timedelta(days=30);f=stock(cur,today,10,first);posted(cur,f,'8');later=source.fg.ax.post(cur,dict(source_kind='FOUND_AT_OPNAME',product_id=f['product'],location_id=f['location'],qty_pcs=10,physical_at=(first+timedelta(days=2)).isoformat(),reason='Later real stock is not available at the original time',owner_unit_value='10',owner_value_reason='Declared independent value for the later physical receipt; the future valuation model is not a historical cost source'))
  assert int(cur.execute('select sum(qty_signed)from erp.fg_stock_movements where product_id=%s',(f['product'],)).fetchone()[0])==12
  p,v=edit(cur,f,'12');before=snapshot(cur)
  denial=auth.refused(cur,lambda:correct(cur,p,v),'lebih awal dari tanggal barang/lot tersedia')
  assert denial.startswith('Tanggal mutasi FG ')and snapshot(cur)==before
  return dict(status='PASS',current_stock_positive12_but_original_time_only10=True,future_lot_cannot_supply_the_original_physical_time=True,historical_negative_refused_atomically=True,native_denial=denial)
 def closed():
  at=source.fg.ax.r1.now(cur)-timedelta(days=4);f=stock(cur,today,10,at);posted(cur,f,'4');original=f['sale'];original_journals=cur.execute("select id,economic_date,transaction_date from erp.journal_entries where source_type='SALE'and source_id=%s",(original,)).fetchall();closed_through=today-timedelta(days=1)
  source.fg.ax.boundary.historical.prior.set_open_period(cur,closed_through)
  p,v=edit(cur,f,'3');out=correct(cur,p,v);assert cur.execute("select id,economic_date,transaction_date from erp.journal_entries where source_type='SALE'and source_id=%s",(original,)).fetchall()==original_journals
  assert cur.execute('select closed_through from erp.accounting_period_control where singleton_id=1').fetchone()[0]==closed_through
  journals=cur.execute("select economic_date,transaction_date from erp.journal_entries where source_type='SALE'and source_id=%s",(out['sale_id'],)).fetchall();assert journals and all(e==cur.execute("select (%s::timestamptz at time zone 'Asia/Jakarta')::date",(f['sale_at'],)).fetchone()[0]and t>closed_through for e,t in journals)
  moved=cur.execute('select e.economic_date,e.transaction_date from cp7_note.journal_restatements r join erp.journal_entries e on e.id=r.effective_journal_id where r.previous_sale_id=%s',(original,)).fetchall()
  assert moved and all(e==original_journals[0][1]and t>closed_through for e,t in moved);inverse_date_truth(cur)
  report=finance.read(cur,today)
  assert report['snapshot']['performance']['sales_revenue_reconciled'],report['snapshot']['performance']
  return dict(status='PASS',accepted_native_economic_date_and_open_GL_date_rule_retained=True,no_closed_period_reopened=True,no_old_journal_date_rewritten=True)
 def injected():
  f=returned.fixture(cur,today);returned.returned(cur,f);returned.payments.pay(cur,f,'30');p,v=edit(cur,f,'3');before=snapshot(cur)
  cur.execute("create function cp7_note.test_fail_after_all_effects()returns trigger language plpgsql as $$begin if not exists(select 1 from erp.sales_headers where id=new.replacement_sale_id and status='PARTIAL_PAID')then raise exception 'NOTE_TEST_REPLACEMENT_NOT_POSTED';end if;if not exists(select 1 from cp7_fg.correction_movements where correction_id=new.id)then raise exception 'NOTE_TEST_METADATA_NOT_REACHED';end if;raise exception 'NOTE_TEST_INJECTED_AFTER_STOCK_CASH_JOURNAL_HPP';end$$;create trigger test_fail_after_all_effects before insert on cp7_note.revisions for each row execute function cp7_note.test_fail_after_all_effects()",prepare=False)
  auth.refused(cur,lambda:correct(cur,p,v),'NOTE_TEST_INJECTED_AFTER_STOCK_CASH_JOURNAL_HPP');assert snapshot(cur)==before
  cur.execute('drop trigger test_fail_after_all_effects on cp7_note.revisions;drop function cp7_note.test_fail_after_all_effects()',prepare=False)
  return dict(status='PASS',injected_after_replacement_payment_and_lineage=True,all_native_stock_cash_AR_journal_HPP_and_private_metadata_rolled_back=True)
 def overpaid():
  f=returned.payments.fixture(cur,today);returned.payments.pay(cur,f,'80');p,v=edit(cur,f,'3');before=snapshot(cur);auth.refused(cur,lambda:correct(cur,p,v),'exceeds exact remaining receivable');assert snapshot(cur)==before
  return dict(status='PASS',cash80_cannot_be_replayed_onto_invoice60=True,no_automatic_refund_or_credit_invented=True,all_effects_rolled_back=True)
 def allocation():
  f=returned.fixture(cur,today);returned.returned(cur,f,qty='2',refund='40');p,v=edit(cur,f,'1');before=snapshot(cur);auth.refused(cur,lambda:correct(cur,p,v),'CP7_NOTE_RETURN_ALLOCATION_CHANGED');assert snapshot(cur)==before
  return dict(status='PASS',active_return2_cannot_be_lost_on_replacement1=True,source_note_and_return_retained_on_refusal=True)
 def review():
  f=posted(cur,drafts.fixture(cur,today));p,v=edit(cur,f,'3');cur.execute("insert into erp.sales_returns(return_number,sale_id,customer_id,physical_at,status)values(%s,%s,%s,%s,'DRAFT')",('NOTE-PENDING-'+uuid.uuid4().hex,f['sale'],f['customer'],source.fg.ax.r1.now(cur)));before=snapshot(cur)
  assert source.read(cur,f)['detail']['row_version']==v;auth.refused(cur,lambda:correct(cur,p,v),'CP7_NOTE_REVIEW_CHANGED');assert snapshot(cur)==before
  p,v=edit(cur,f,'3');auth.refused(cur,lambda:correct(cur,p,v),'CP7_NOTE_PENDING_CHILD_REVIEW_REQUIRED');assert snapshot(cur)==before
  return dict(status='PASS',draft_child_invalidates_review_without_header_version_change=True,pending_child_never_silently_abandoned=True)
 def request_access():
  f=posted(cur,drafts.fixture(cur,today));p,v=edit(cur,f,'3');key=uuid.uuid4();out=correct(cur,p,v,key);before=snapshot(cur);bad=copy.deepcopy(p);bad['items'][0]['qty_pcs']='2';auth.refused(cur,lambda:correct(cur,bad,v,key),'CP7_NOTE_REQUEST_CHANGED');assert snapshot(cur)==before
  cur.execute("insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active)select %s,%s,'Note second owner fixture',role,role_id,true from erp.app_users where auth_user_id=%s",(uuid.uuid4(),uuid.uuid4(),auth.base.OPERATOR_AUTH));cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(auth.base.OPERATOR_AUTH,));after_deactivation=snapshot(cur);auth.refused(cur,lambda:correct(cur,p,v,key),'CP7_SALES_ACCESS_DENIED');assert snapshot(cur)==after_deactivation
  return dict(status='PASS',changed_intent_denied_after_commit=True,current_deactivation_denies_cached_outcome=True,original_committed_receipt=out['revision_id'])
 def private():
  ownership.verify(cur);f=posted(cur,drafts.fixture(cur,today));p,v=edit(cur,f,'3');before=snapshot(cur)
  for change in (dict(unit_hpp_snapshot='0'),dict(sale_date=source.fg.ax.r1.now(cur).isoformat()),dict(sale_number='ALTERED-ORIGINAL-NUMBER')):
   auth.refused(cur,lambda:correct(cur,dict(p,**change),v),'CP7_SALES_DRAFT_FIELDS'if'unit_hpp_snapshot'in change else'CP7_NOTE_SOURCE_IDENTITY_CHANGED')
  for extra in (dict(limit=0),dict(offset=-1),dict(q='x'*121),dict(history_complete=True),dict(brand_ids=None),dict(customer_ids=[3])):
   auth.refused(cur,lambda extra=extra:book(cur,f,**extra),'CP7_FG_BOOK_FILTER'if'brand_ids'in extra or'customer_ids'in extra else'CP7_FG_BOOK_QUERY')
  brand=str(cur.execute('select brand_id from erp.products where id=%s',(f['product'],)).fetchone()[0])
  low=book(cur,f,brand_ids=[brand]);upper=book(cur,f,brand_ids=[brand.upper()])
  assert low['page']['rows']and low['page']==upper['page']and low['book_token']==upper['book_token']
  assert snapshot(cur)==before
  return dict(status='PASS',no_injected_HPP_or_silent_date_number_change=True,no_extra_native_privilege=True,scoped_private_helpers_unreachable=True,shared_closed_book_query_refusals=True,uppercase_UUID_filter_same_complete_page_and_prefix=True)
 def same_day():
  f=stock(cur,today,100,source.fg.ax.r1.now(cur)-timedelta(days=2));posted(cur,f,'24');later=dict(f,tag=f['tag']+'-PM',sale_at=(source.fg.ax.r1.now(cur)-timedelta(days=2)+timedelta(hours=5)).isoformat());posted(cur,later,'12');before=complete_book(cur,f);p,v=edit(cur,f,'12');correct(cur,p,v);after=complete_book(cur,f)
  later_row=next(r for r in before.values()if r['movement_type']=='SALE'and r['physical_at']==source.read(cur,later)['detail']['physical_at']);assert after[later_row['id']]['physical_at']==later_row['physical_at']and D(after[later_row['id']]['book_physical_after'])==D(later_row['book_physical_after'])+12
  return dict(status='PASS',morning_and_afternoon_events_remain_distinct=True,later_same_day_balance_updated=True,recorded_clock_not_backdated=True)
 def wallet_replay():
  f,w=wallet_note(cur,today);root=f['sale'];old_wallet=cur.execute('select to_jsonb(a)from erp.initial_import_prepayments a where id=%s',(w['advance'],)).fetchone()[0]
  old_payment=cur.execute('select p.id,to_jsonb(p)-\'status\',to_jsonb(l),to_jsonb(j)from erp.initial_import_prepayment_payments l join erp.sales_payments p on p.id=l.payment_id join erp.sales_payment_posting_facts j on j.payment_id=p.id where l.advance_id=%s and p.status=\'POSTED\'',(w['advance'],)).fetchone()
  before=cmd.accounts(cur);p,v=edit(cur,f,'3');key=uuid.uuid4();out=correct(cur,p,v,key);f['sale']=out['sale_id'];d=source.read(cur,f)['detail']
  assert d['financial']['net_total']=='60.00'and d['financial']['paid_total']=='30.00'and d['financial']['open_balance']=='30.00'and cmd.available(cur,f)==7
  assert cmd.delta(before,cmd.accounts(cur))=={cmd.mapping(cur,'AR_CUSTOMER'):D('-20'),cmd.mapping(cur,'SALES_REVENUE'):D('20'),cmd.mapping(cur,'FG_INVENTORY'):D('10'),cmd.mapping(cur,'COGS'):D('-10')}
  assert prepaid.state(imports,cur,w)['remaining_amount']=='42.25'and prepaid.bank(cur,w)==100
  assert cur.execute('select to_jsonb(a)from erp.initial_import_prepayments a where id=%s',(w['advance'],)).fetchone()[0]==old_wallet
  retained=cur.execute('select to_jsonb(p)-\'status\',to_jsonb(l),to_jsonb(j)from erp.sales_payments p join erp.initial_import_prepayment_payments l on l.payment_id=p.id join erp.sales_payment_posting_facts j on j.payment_id=p.id where p.id=%s',(old_payment[0],)).fetchone();assert retained==old_payment[1:]
  new=cur.execute('select p.amount,p.payment_date,p.cash_account_id,p.payment_method,p.replaces_payment_id,l.advance_id from erp.sales_payments p join erp.initial_import_prepayment_payments l on l.payment_id=p.id where p.sale_id=%s and p.status=\'POSTED\'',(f['sale'],)).fetchone()
  assert new and new[0]==D('25')and new[2]is None and new[3]=='OPENING_ADVANCE'and new[4]is None and str(new[5])==str(w['advance'])
  lineage=cur.execute('select r.previous_payment_id,r.correction_id,f.replaces_payment_id,f.predecessor_reversal_journal_id from cp7_note.payment_replays r join erp.sales_payment_posting_facts f on f.payment_id=r.replacement_payment_id where f.sale_id=%s and r.previous_payment_id=%s',(f['sale'],old_payment[0])).fetchone()
  assert lineage and str(lineage[0])==str(old_payment[0])and str(lineage[1])==out['revision_id']and lineage[2:] == (None,None)
  assert new[1].isoformat()==old_payment[1]['payment_date']or new[1]==cur.execute('select payment_date from erp.sales_payments where id=%s',(old_payment[0],)).fetchone()[0]
  before_replay=snapshot(cur);assert correct(cur,p,v,key)==out and snapshot(cur)==before_replay;checks=prepaid.truth(cur)
  return dict(status='PASS',native_customer_advance67_25_applied25_cash5=True,corrected_invoice60_paid30_AR30=True,wallet_remaining42_25_unchanged=True,original_opening_payment_snapshot_posting_fact_immutable=True,reversal_and_fresh_native_use_same_wallet_private_immutable_note_lineage=True,no_invented_cash=True,same_UUID_once=True,truth_checks=checks,root_sale_id=root)
 def wallet_overpaid():
  f,w=wallet_note(cur,today);p,v=edit(cur,f,'1');before=snapshot(cur);wallet=prepaid.state(imports,cur,w)
  auth.refused(cur,lambda:correct(cur,p,v),'exceeds exact remaining receivable');assert snapshot(cur)==before and prepaid.state(imports,cur,w)==wallet and prepaid.bank(cur,w)==100
  return dict(status='PASS',prepaid25_and_cash5_cannot_fit_invoice20=True,all_stock_cash_wallet_AR_HPP_journal_lineage_rolled_back=True)
 def economic_report():
  month_start=today.replace(day=1);old_end=month_start-timedelta(days=1);old_start=old_end.replace(day=1)
  source.fg.ax.boundary.historical.prior.set_open_period(cur,old_start-timedelta(days=1))
  at=source.fg.ax.r1.now(cur).replace(year=old_start.year,month=old_start.month,day=4,hour=1,minute=0,second=0,microsecond=0)
  f=stock(cur,today,10,at);posted(cur,f);root=f['sale'];original=unchanged_facts(cur,root)
  prior_economic=period_accounts(cur,old_start,old_end,'economic_date');prior_GL=period_accounts(cur,old_start,old_end,'transaction_date');current=period_accounts(cur,month_start,today,'economic_date')
  old_report=finance.read(cur,old_end,**{'from':str(old_start),'as_of':str(today)});current_report=finance.read(cur,today,**{'from':str(month_start)})
  p,v=edit(cur,f,'3');correct(cur,p,v)
  wanted={cmd.mapping(cur,'AR_CUSTOMER'):D('-20'),cmd.mapping(cur,'SALES_REVENUE'):D('20'),cmd.mapping(cur,'FG_INVENTORY'):D('10'),cmd.mapping(cur,'COGS'):D('-10')}
  assert cmd.delta(prior_economic,period_accounts(cur,old_start,old_end,'economic_date'))==wanted
  assert cmd.delta(prior_GL,period_accounts(cur,old_start,old_end,'transaction_date'))==wanted
  assert period_accounts(cur,month_start,today,'economic_date')==current
  new_report=finance.read(cur,old_end,**{'from':str(old_start),'as_of':str(today)});now_report=finance.read(cur,today,**{'from':str(month_start)})
  assert finance.change(old_report,new_report,'performance','sales_revenue_gl')==D('-20')and finance.change(old_report,new_report,'performance','cogs_gl')==D('-10')
  assert finance.change(old_report,new_report,'performance','operational_net_sales')==D('-20')
  assert new_report['snapshot']['performance']['sales_revenue_reconciled']and now_report['snapshot']['performance']['sales_revenue_reconciled']
  assert now_report['snapshot']['performance']==current_report['snapshot']['performance']
  assert unchanged_facts(cur,root)==original;inverse_date_truth(cur)
  sums=cur.execute('select l.account_id,sum(l.debit-l.credit)from cp7_note.journal_restatements r join erp.journal_lines l on l.journal_entry_id in(r.neutral_journal_id,r.effective_journal_id)where r.previous_sale_id=%s group by l.account_id',(root,)).fetchall()
  assert sums and all(value==0 for _,value in sums)
  return dict(status='PASS',original_open_period_AR_minus20_revenue_minus20_FG_plus10_COGS_minus10=True,owner_native_report_reconciled=True,current_economic_period_no_repeat=True,exact_line_reclassification_pair_gl_neutral=True,native_generic_inverse_business_date_check_zero=True,original_fact_dates_not_rewritten=True)
 def exact_order():
  f=stock(cur,today,100,source.fg.ax.r1.now(cur)-timedelta(days=2));posted(cur,f,'24');later=dict(f,tag=f['tag']+'-EXACT');posted(cur,later,'12')
  before=complete_book(cur,f);p,v=edit(cur,f,'12');correct(cur,p,v);after=complete_book(cur,f)
  ident=str(cur.execute("select m.id from erp.fg_stock_movements m join erp.sales_items i on i.id=m.source_id where i.sale_id=%s and m.movement_type='SALE'",(later['sale'],)).fetchone()[0])
  assert after[ident]['physical_at']==before[ident]['physical_at']==source.read(cur,later)['detail']['physical_at']
  for field in ('book_physical_after','official_physical_after'):assert D(after[ident][field])-D(before[ident][field])==12
  assert all(after[i]['book_order']==r['book_order']for i,r in before.items())
  return dict(status='PASS',two_distinct_native_notes_same_exact_physical_time=True,original_recorded_order_and_manual_ranks_preserved=True,later_main_and_official_balances_plus12=True)
 def cross_period_funding(advance):
  start=today.replace(day=1);old_end=start-timedelta(days=1);old_start=old_end.replace(day=1)
  source.fg.ax.boundary.historical.prior.set_open_period(cur,old_start-timedelta(days=1))
  at=source.fg.ax.r1.now(cur).replace(year=old_end.year,month=old_end.month,day=old_end.day-2,hour=1,minute=0,second=0,microsecond=123456)
  cash_at=at+timedelta(days=1,hours=2)
  if advance:
   f,w=wallet_note(cur,old_end,at=at,cash_at=cash_at)
  else:
   f=posted(cur,stock(cur,today,10,at));f['bank']=str(source.bc.bank_account(cur,'NOTE-OLD-CASH-'+uuid.uuid4().hex[:8]));f['allocations']=returned.read(cur,f)['page']['rows']
   payload,version=returned.payload(cur,f,destination=f['location']);payload['physical_at']=(at+timedelta(days=1)).isoformat();cmd.command(cur,'RETURN',payload,version)
   payload,version=returned.payments.payment_payload(cur,f,'20');payload['payment_date']=cash_at.isoformat();cmd.command(cur,'PAYMENT',payload,version)
  root=f['sale'];old=finance.read(cur,old_end,**{'from':str(old_start),'as_of':str(today)});now=finance.read(cur,today,**{'from':str(start)})
  old_money=period_accounts(cur,old_start,old_end,'economic_date');new_money=period_accounts(cur,start,today,'economic_date')
  original_payments=cur.execute('select id,payment_date,amount,cash_account_id,payment_method from erp.sales_payments where sale_id=%s and status=\'POSTED\'order by id',(root,)).fetchall()
  payload,version=edit(cur,f,'3');out=correct(cur,payload,version);f['sale']=out['sale_id'];after=source.read(cur,f)['detail']
  assert after['financial']['open_balance']==('30.00'if advance else'20.00')and cmd.available(cur,f)==(7 if advance else 8)
  assert cmd.delta(old_money,period_accounts(cur,old_start,old_end,'economic_date'))=={cmd.mapping(cur,'AR_CUSTOMER'):D('-20'),cmd.mapping(cur,'SALES_REVENUE'):D('20'),cmd.mapping(cur,'FG_INVENTORY'):D('10'),cmd.mapping(cur,'COGS'):D('-10')}
  assert period_accounts(cur,start,today,'economic_date')==new_money
  replayed=cur.execute('select old.id,new.payment_date,new.amount,new.cash_account_id,new.payment_method,new.replaces_payment_id from cp7_note.payment_replays r join erp.sales_payments old on old.id=r.previous_payment_id join erp.sales_payments new on new.id=r.replacement_payment_id where r.correction_id=%s order by old.id',(out['revision_id'],)).fetchall()
  assert [row[:5]for row in replayed]==original_payments and all(row[5]is None for row in replayed)
  later=finance.read(cur,old_end,**{'from':str(old_start),'as_of':str(today)});current=finance.read(cur,today,**{'from':str(start)})
  assert finance.change(old,later,'performance','sales_revenue_gl')==D('-20')and finance.change(old,later,'performance','operational_net_sales')==D('-20')and finance.change(old,later,'performance','cogs_gl')==D('-10')
  assert later['snapshot']['performance']['sales_revenue_reconciled']and current['snapshot']['performance']==now['snapshot']['performance']
  checks=prepaid.truth(cur);inverse_date_truth(cur)
  if advance:assert prepaid.state(imports,cur,w)['remaining_amount']=='42.25'and prepaid.bank(cur,w)==100
  return dict(status='PASS',original_physical_microseconds_and_funding_preserved=True,original_period_cash_and_advance_liability_unchanged=True,current_period_all_accounts_and_performance_unchanged=True,old_period_revenue_and_operational_minus20_COGS_minus10=True,immutable_private_payment_replay_lineage=True,native_truth_zero=checks,advance=advance)
 def multi_lot():
  at=source.fg.ax.r1.now(cur)-timedelta(hours=4);f=stock(cur,today,3,at)
  receipt=source.fg.ax.post(cur,dict(source_kind='FOUND_AT_OPNAME',product_id=f['product'],location_id=f['location'],qty_pcs=5,physical_at=(at+timedelta(hours=1)).isoformat(),reason='Second independently valued physical lot for allocation oracle',owner_unit_value='10',owner_value_reason='Explicit value10 for this separate stock source'))
  b.api.admin(cur);lot_b=str(cur.execute('select lot_id from erp.fg_unsourced_receipts_v1 where id=%s',(receipt['receipt_id'],)).fetchone()[0]);f['sale_at']=(at+timedelta(hours=2)).isoformat();posted(cur,f,'2')
  original=f['sale'];facts=unchanged_facts(cur,original);initial=list(cur.execute('select lot_id,qty_pcs from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=%s',(original,)).fetchall())
  assert initial==[(uuid.UUID(f['lot']),D(2))],initial
  p,v=edit(cur,f,'6');out=correct(cur,p,v);f['sale']=out['sale_id'];a=lot_card(cur,f);z=lot_card(cur,dict(f,lot=lot_b))
  assert(a['balances']['physical_qty'],z['balances']['physical_qty'])==('0','2'),(a,z)
  effective_a=next(r for r in a['page']['rows']if r['correction_count']=='1');effective_b=next(r for r in z['page']['rows']if r['correction_count']=='1')
  assert(effective_a['physical_delta'],effective_a['original_physical_delta'])==('-3','-2')and(effective_b['physical_delta'],effective_b['original_physical_delta'])==('-3','0')
  assert all(r['lot_id']==f['lot']for r in effective_a['audit_movements'])and all(r['lot_id']==lot_b for r in effective_b['audit_movements'])
  alloc=cur.execute('select count(distinct a.lot_id),sum(a.qty_pcs)from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=%s',(out['sale_id'],)).fetchone()
  assert alloc==(2,D(6))and cmd.available(cur,f)==2 and unchanged_facts(cur,original)==facts
  assert source.read(cur,f)['detail']['financial']['gross_total']=='120.00'
  return dict(status='PASS',real_Native_two_lot_allocation_3plus3=True,original_lot_only2_preserved=True,new_lot_card_original0_effective_minus3=True,old_lot_card_original_minus2_effective_minus3=True,per_lot_balances0_and2_reconcile_to_current2=True,no_cross_lot_audit_or_money_mutation=True)
 def multi_line():
  f=drafts.fixture(cur,today,10);g=drafts.fixture(cur,today,10);p=drafts.payload(f,'4','20');p['items']+=drafts.payload(g,'3','10.01','0.02')['items'];drafts.create(cur,f,p);post,v=cmd.review(cur,f);cmd.command(cur,'POST',post,v)
  f['bank']=str(source.bc.bank_account(cur,'NOTE-MULTILINE-'+uuid.uuid4().hex[:8]));returned.payments.pay(cur,f,'30');original=f['sale'];facts=unchanged_facts(cur,original)
  p,v=edit(cur,f)
  for item in p['items']:item['qty_pcs']='5'if item['product_id']==f['product']else'1'
  out=correct(cur,p,v);f['sale']=out['sale_id'];d=source.read(cur,f)['detail']
  assert d['line_count']=='2'and d['financial']['gross_total']=='109.99'and d['financial']['paid_total']=='30.00'and d['financial']['open_balance']=='79.99'
  assert cmd.available(cur,f)==5 and cmd.available(cur,g)==9 and unchanged_facts(cur,original)==facts
  assert lot_card(cur,f)['balances']['physical_qty']=='5'and lot_card(cur,g)['balances']['physical_qty']=='9'
  inverse_date_truth(cur)
  return dict(status='PASS',two_actual_products_prices_discounts_and_lines_preserved=True,invoice110_01_to109_99_cash30_AR79_99=True,independent_lot_balances5_and9=True,one_owning_atomic_command=True,original_posted_note_immutable=True)
 def actor_name():
  f=posted(cur,drafts.fixture(cur,today));root=f['sale'];p,v=edit(cur,f,'3');out=correct(cur,p,v);h=history(cur,root);r=h['history'][0]
  expected=cur.execute('select full_name from erp.app_users where auth_user_id=%s',(auth.base.OPERATOR_AUTH,)).fetchone()[0]
  assert r['actor_id']==str(auth.base.OPERATOR_AUTH)and r['actor_display_name']==expected.strip()and r['actor_name_basis']=='CURRENT_PROFILE'
  before=cur.execute('select to_jsonb(r)from cp7_note.revisions r where r.id=%s',(out['revision_id'],)).fetchone()[0]
  cur.execute("update erp.app_users set full_name='Nama profil sesudah koreksi'where auth_user_id=%s",(auth.base.OPERATOR_AUTH,));renamed=history(cur,root)['history'][0]
  assert renamed['actor_display_name']=='Nama profil sesudah koreksi'and renamed['actor_id']==r['actor_id']
  assert cur.execute('select to_jsonb(r)from cp7_note.revisions r where r.id=%s',(out['revision_id'],)).fetchone()[0]==before
  return dict(status='PASS',immutable_actor_UUID=True,current_profile_label_explicit_not_fabricated_historical_name=True,renamed_profile_does_not_edit_revision=True)
 tests=[('YEAR_30',lambda:year(cur,today,30)),('YEAR_364',lambda:year(cur,today,364)),('REPEATED_REVISIONS',repeat),('FULL_NATIVE_FINANCIAL',financial),('RETURN_OTHER_WAREHOUSE',other_warehouse),('EXACT_CENTS',cents),('ADDED_SKU_MAIN_BOOK',sku),('HISTORICAL_NEGATIVE',negative),('CLOSED_PERIOD_NATIVE_RULE',closed),('LATE_FAILURE_ATOMIC',injected),('OVERPAYMENT_ATOMIC',overpaid),('RETURN_CAPACITY_ATOMIC',allocation),('CHILD_REVIEW_CHANGED',review),('REPLAY_CURRENT_AUTHORITY',request_access),('PRIVATE_CLOSED_FIELDS',private),('SAME_DAY_CHRONOLOGY',same_day)]
 tests=[('NOTE_'+name,fn)for name,fn in tests]
 tests += [('NOTE_PREPAYMENT_REPLAY',wallet_replay),('NOTE_PREPAYMENT_OVERPAYMENT_ATOMIC',wallet_overpaid),('NOTE_ECONOMIC_REPORT_RESTATEMENT',economic_report),('NOTE_EXACT_TIME_SOURCE_ORDER',exact_order)]
 tests += [('NOTE_OLD_CASH_RETURN_REPORT',lambda:cross_period_funding(False)),('NOTE_OLD_ADVANCE_CASH_REPORT',lambda:cross_period_funding(True))]
 tests += [('NOTE_MULTI_LOT_CARD',multi_lot),('NOTE_MULTI_LINE_ATOMIC',multi_line),('NOTE_CORRECTION_ACTOR',actor_name)]
 assert [name for name,_ in tests]==MANIFEST['groups']['native']
 return tests

def races(tools,today):
 def compete(same_uuid=False,payment=False):
  with tools.connect()as conn,conn.cursor()as cur:
   f=posted(cur,drafts.fixture(cur,today));f['bank']=str(source.bc.bank_account(cur,'NOTE-RACE-'+uuid.uuid4().hex[:8]));p,v=edit(cur,f,'3');pay,pay_v=returned.payments.payment_payload(cur,f,'20');conn.commit()
  barrier=threading.Barrier(2);key=uuid.uuid4()
  def send(n):
   with tools.connect()as conn,conn.cursor()as cur:
    barrier.wait()
    try:
     result=cmd.command(cur,'PAYMENT',pay,pay_v)if payment and n==1 else correct(cur,p,v,key if same_uuid else uuid.uuid4());conn.commit();return result
    except psycopg.Error as error:conn.rollback();return str(error).splitlines()[0]
  with ThreadPoolExecutor(max_workers=2)as pool:jobs=[pool.submit(send,n)for n in(0,1)];results=[j.result(60)for j in jobs]
  good=[r for r in results if isinstance(r,dict)];assert len(good)==(2 if same_uuid else 1),results
  with tools.connect()as conn,conn.cursor()as cur:
   h=history(cur,f['sale']);count=int(cur.execute('select count(*)from cp7_note.revisions where root_sale_id=%s',(f['sale'],)).fetchone()[0]);assert count==(0 if payment and good[0]['action']=='PAYMENT'else 1)
   leaf=dict(f,sale=h['current_sale_id']);d=source.read(cur,leaf)['detail'];assert(d['qty_pcs'],d['financial']['paid_total'])==(('4','20.00')if count==0 else('3','0.00'))
   if same_uuid:assert good[0]==good[1]
  return dict(status='PASS',real_concurrent_transactions=True,same_UUID=same_uuid,note_versus_payment=payment,one_economic_effect=True,loser_or_replay_has_no_second_effect=True)
 def revoked():
  with tools.connect()as conn,conn.cursor()as cur:
   f=posted(cur,drafts.fixture(cur,today));p,v=edit(cur,f,'3');cur.execute("insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active)select %s,%s,'Note second owner fixture',role,role_id,true from erp.app_users where auth_user_id=%s",(uuid.uuid4(),uuid.uuid4(),auth.base.OPERATOR_AUTH));conn.commit()
  with tools.connect()as holder,holder.cursor()as hold:
   hold.execute("select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0))")
   def send():
    with tools.connect()as conn,conn.cursor()as cur:
     try:correct(cur,p,v);conn.commit();return'UNEXPECTED_SUCCESS'
     except psycopg.Error as error:conn.rollback();return str(error).splitlines()[0]
   with ThreadPoolExecutor(max_workers=1)as pool:
    future=pool.submit(send);blocked=False
    try:
     with tools.connect(autocommit=True)as inspect,inspect.cursor()as cur:
      deadline=time.monotonic()+10
      while time.monotonic()<deadline:
       cur.execute('select pg_stat_clear_snapshot()');blocked=cur.execute("select exists(select 1 from pg_stat_activity where datname=current_database()and wait_event_type='Lock'and pid<>pg_backend_pid())").fetchone()[0]
       if blocked:break
       time.sleep(.03)
      assert blocked,'NOTE_EXPECTED_REAL_GLOBAL_LOCK_WAIT';cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(auth.base.OPERATOR_AUTH,))
    finally:holder.rollback()
    result=future.result(60)
  assert'CP7_SALES_ACCESS_DENIED'in result,result
  with tools.connect()as conn,conn.cursor()as cur:assert cur.execute('select status from erp.sales_headers where id=%s',(f['sale'],)).fetchone()[0]=='POSTED'and cmd.available(cur,f)==6 and cur.execute('select count(*)from cp7_note.revisions where root_sale_id=%s',(f['sale'],)).fetchone()[0]==0
  return dict(status='PASS',real_lock_wait_observed=True,revocation_during_wait_denies_before_stock_or_financial_effect=True)
 tests=[('NOTE_RACE_TWO_REQUESTS',lambda:compete()),('NOTE_RACE_SAME_UUID',lambda:compete(True)),('NOTE_RACE_PAYMENT',lambda:compete(payment=True)),('NOTE_RACE_REVOKE_DURING_WAIT',revoked)]
 assert [name for name,_ in tests]==MANIFEST['groups']['races']
 return tests

def http_cases(http,today):
 def correction():
  owner=http.login('OWNER','note-correction-owner')
  with http.connect()as conn,conn.cursor()as cur:f=posted(cur,drafts.fixture(cur,today));p,v=edit(cur,f,'3');conn.commit()
  args=dict(p_payload=p,p_request=str(uuid.uuid4()),p_expected=v)
  assert http.anon_rpc('erp_cp7_correct_note_v1',args)['status']in(401,403)
  out=owner.rpc('erp_cp7_correct_note_v1',args);assert out['status']==200,out;assert owner.rpc('erp_cp7_correct_note_v1',args)['body']==out['body']
  h=owner.rpc('erp_cp7_get_note_correction_v1',dict(p_sale=f['sale']));assert h['status']==200 and h['body']['current_sale_id']==out['body']['sale_id']and h['body']['current']['detail']['financial']['open_balance']=='60.00',h
  with http.connect()as conn,conn.cursor()as cur:assert cmd.available(cur,f)==7;cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
  assert owner.rpc('erp_cp7_correct_note_v1',args)['status']==403 and owner.rpc('erp_cp7_get_note_correction_v1',dict(p_sale=f['sale']))['status']==403
  return dict(status='PASS',real_Auth_PostgREST_owning_correction_and_history=True,one_UUID_one_effect=True,current_deactivation_hides_cached_outcome_and_history=True)
 def filtered_book():
  owner=http.login('OWNER','note-book-owner')
  with http.connect()as conn,conn.cursor()as cur:f=posted(cur,drafts.fixture(cur,today,40),'24');p,v=edit(cur,f,'12');correct(cur,p,v);conn.commit()
  args=dict(p_query=dict(q=f['sku'],limit=25,offset=0,movement_types=['SALE']))
  result=owner.rpc('erp_cp7_get_fg_book_v2',args);assert result['status']==200,result;r=result['body']['page']['rows'][0];assert r['physical_delta']=='-12'and r['original_physical_delta']=='-24'and r['reservation_delta']=='0'and r['correction_count']=='1'
  assert'unit_hpp'not in json.dumps(result['body'])and'unit_cost'not in json.dumps(result['body'])
  assert http.anon_rpc('erp_cp7_get_fg_book_v2',args)['status']in(401,403)
  return dict(status='PASS',real_Auth_corrected_main_card=True,immutable_original_and_corrected_quantity_visible=True,no_money_on_stock_book=True)
 def lot_actor_http():
  owner=http.login('OWNER','note-lot-actor-owner')
  with http.connect()as conn,conn.cursor()as cur:f=posted(cur,drafts.fixture(cur,today,40),'24');p,v=edit(cur,f,'12');conn.commit()
  result=owner.rpc('erp_cp7_correct_note_v1',dict(p_payload=p,p_request=str(uuid.uuid4()),p_expected=v));assert result['status']==200,result
  args=dict(p_query=dict(product_id=f['product'],lot_id=f['lot'],location_id=f['location'],quality_grade='GRADE_A',purpose='CARD',q=f['tag'],limit=1,offset=0))
  card=owner.rpc('erp_cp7_get_fg_ledger_v2',args);assert card['status']==200,card
  r=card['body']['page']['rows'][0];assert r['physical_delta']=='-12'and r['original_physical_delta']=='-24'and r['physical_balance']=='28'and r['correction_count']=='1'
  h=owner.rpc('erp_cp7_get_note_correction_v2',dict(p_sale=f['sale']));assert h['status']==200,h
  assert h['body']['history'][0]['actor_id']==owner.auth_user_id and h['body']['history'][0]['actor_display_name']and h['body']['history'][0]['actor_name_basis']=='CURRENT_PROFILE'
  assert http.anon_rpc('erp_cp7_get_fg_ledger_v2',args)['status']in(401,403)and http.anon_rpc('erp_cp7_get_note_correction_v2',dict(p_sale=f['sale']))['status']in(401,403)
  with http.connect()as conn,conn.cursor()as cur:cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
  assert owner.rpc('erp_cp7_get_fg_ledger_v2',args)['status']==403 and owner.rpc('erp_cp7_get_note_correction_v2',dict(p_sale=f['sale']))['status']==403
  return dict(status='PASS',real_Auth_grouped_lot_suffix_and_actor_labels=True,anonymous_and_current_revocation_both_deny=True)
 tests=[('NOTE_HTTP_COMMAND_REPLAY_AUTH',correction),('NOTE_HTTP_CORRECTED_BOOK',filtered_book),('NOTE_HTTP_LOT_AND_ACTOR',lot_actor_http)]
 assert [name for name,_ in tests]==MANIFEST['groups']['http']
 return tests
