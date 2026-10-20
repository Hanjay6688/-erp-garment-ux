-- SOURCE-ONLY OW04 PROPOSAL. No installer, authority API, or Native proof.
do $not_an_installer$begin
 raise exception 'OW04_SOURCE_PROPOSAL_REQUIRES_COMPLETE_OWNING_INTEGRATION';
end $not_an_installer$;
create schema ow04_source_proposal authorization postgres;
revoke all on schema ow04_source_proposal from public,anon,authenticated,service_role;

-- Canonical proof codec: normalize JSON numeric display scales recursively.
-- SQL jsonb equality treats 0 and 0.000000 equal; the digest must agree.
-- Native payment-fact digests deliberately keep their ORIGINAL raw codec.
create function ow04_source_proposal.canonical_json_v1(p jsonb)returns jsonb
language plpgsql immutable strict security invoker set search_path=''as $$
declare answer jsonb;one record;
begin
 case jsonb_typeof(p)
 when'number'then return to_jsonb(trim_scale((p#>>'{}')::numeric));
 when'array'then
  select coalesce(jsonb_agg(ow04_source_proposal.canonical_json_v1(value)order by ordinal),'[]')into answer
   from jsonb_array_elements(p)with ordinality as x(value,ordinal);return answer;
 when'object'then
  select coalesce(jsonb_object_agg(key,ow04_source_proposal.canonical_json_v1(value)),'{}')into answer from jsonb_each(p);return answer;
 else return p;end case;
end $$;
create function ow04_source_proposal.sha(p jsonb)returns text
language sql immutable strict security invoker set search_path=''as $$
 select encode(pg_catalog.sha256(convert_to(ow04_source_proposal.canonical_json_v1(p)::text,'UTF8')),'hex')
$$;
create function ow04_source_proposal.native_sha(p jsonb)returns text
language sql immutable strict security invoker set search_path=''as $$
 select encode(pg_catalog.sha256(convert_to(p::text,'UTF8')),'hex')
$$;
create function ow04_source_proposal.cents(p numeric)returns text
language plpgsql immutable strict security invoker set search_path=''as $$
begin
 if p::text in('NaN','Infinity','-Infinity')or p*100<>trunc(p*100)then
  raise exception 'OW04_SOURCE_EXACT_CENTS_REQUIRED';end if;
 return(case when p<0 then'-'else''end)||trunc(abs(p))::text||'.'||
  lpad(trunc((abs(p)-trunc(abs(p)))*100)::text,2,'0');
end $$;

-- Actual immutable monetary payload, separate from mutable POSTED->REVERSED.
-- Native journal_entries has no updated clock; status is its changing fact.
create function ow04_source_proposal.journal_payload(p_journal uuid)returns jsonb
language sql volatile security invoker set search_path=''as $$
 select jsonb_build_object('journal',to_jsonb(j)-'status','lines',
  coalesce((select jsonb_agg(to_jsonb(l)order by l.id)from erp.journal_lines l where l.journal_entry_id=j.id),'[]'))
 from erp.journal_entries j where j.id=p_journal
$$;
create function ow04_source_proposal.line_vector(p_journal uuid,p_flip boolean)returns jsonb
language sql volatile security invoker set search_path=''as $$
 select coalesce(jsonb_agg(x.v order by x.v::text collate"C"),'[]')from(
  select jsonb_build_object('account_id',l.account_id,'customer_id',l.customer_id,'vendor_id',l.vendor_id,
   'contractor_id',l.contractor_id,'po_id',l.po_id,'product_id',l.product_id,
   'debit',ow04_source_proposal.cents(case when p_flip then l.credit else l.debit end),
   'credit',ow04_source_proposal.cents(case when p_flip then l.debit else l.credit end))v
  from erp.journal_lines l where l.journal_entry_id=p_journal)x
$$;
-- Monetary identity is separate from mutable HPP snapshots/cost lineage.
-- The full actual journal remains in the current-state manifest below.
create function ow04_source_proposal.financial_journal_payload(p_journal uuid,p_ar uuid)returns jsonb
language sql stable security invoker set search_path=''as $$
 select jsonb_build_object('journal_id',j.id,'source_type',j.source_type,'source_id',j.source_id,
  'reversal_of_id',j.reversal_of_id,'economic_date',j.economic_date,'transaction_date',j.transaction_date,
  'posting_at',j.posting_at,'ar_lines',coalesce((select jsonb_agg(jsonb_build_object('id',l.id,
   'account_id',l.account_id,'customer_id',l.customer_id,'debit',ow04_source_proposal.cents(l.debit),
   'credit',ow04_source_proposal.cents(l.credit))order by l.id)from erp.journal_lines l
   where l.journal_entry_id=j.id and l.account_id=p_ar),'[]'))
 from erp.journal_entries j where j.id=p_journal
$$;

-- Resolve the real linear note revision graph. IDs sorted for locks only,
-- NEVER used as historical return ordinals. A detached/forked chain refuses.
create function ow04_source_proposal.sale_family(p_sale uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''as $$
declare root uuid;roots uuid[];sales uuid[];r record;previous uuid;n bigint:=0;customer uuid;revisions jsonb;
begin
 select array_agg(distinct x.root_sale_id)into roots from cp7_note.revisions x
  where p_sale in(x.root_sale_id,x.previous_sale_id,x.replacement_sale_id);
 if cardinality(roots)>1 then raise exception 'OW04_SOURCE_NOTE_FAMILY_AMBIGUOUS';end if;
 root:=coalesce(roots[1],p_sale);previous:=root;sales:=array[root];
 for r in select *from cp7_note.revisions where root_sale_id=root order by revision loop
  n:=n+1;
  if r.revision<>n or r.previous_sale_id<>previous or r.replacement_sale_id=any(sales)then
   raise exception 'OW04_SOURCE_NOTE_CHAIN_INVALID';end if;
  sales:=sales||r.replacement_sale_id;previous:=r.replacement_sale_id;
 end loop;
 if not p_sale=any(sales)or exists(select 1 from unnest(sales)x left join erp.sales_headers h on h.id=x where h.id is null)then
  raise exception 'OW04_SOURCE_SALE_NOT_FOUND';end if;
 select customer_id into strict customer from erp.sales_headers where id=root;
 if customer is null or exists(select 1 from erp.sales_headers where id=any(sales)and customer_id is distinct from customer)then
  raise exception 'OW04_SOURCE_NOTE_CUSTOMER_CHANGED';end if;
 select coalesce(jsonb_agg(to_jsonb(x)order by x.revision),'[]')into revisions from cp7_note.revisions x where x.root_sale_id=root;
 return jsonb_build_object('root_sale_id',root,'current_leaf_id',previous,'sale_ids',to_jsonb(sales),
  'customer_id',customer,'note_revisions',revisions);
end $$;

-- One actual financial journal has one base document owner. Capture all Native
-- reversal descendants and both recorded neutral/effective restatement rows.
create function ow04_source_proposal.journal_scope(p_sales uuid[],p_returns uuid[],p_payments uuid[])
returns table(journal_id uuid,origin_journal_id uuid,document_kind text,document_id uuid,role text)
language sql volatile security invoker set search_path=''as $$
 with recursive originals as materialized(
  select j.id,'SALE'::text kind,j.source_id doc from erp.journal_entries j
   where j.source_type='SALE'and j.source_id=any(p_sales)and j.reversal_of_id is null
  union all select j.id,'RETURN',j.source_id from erp.journal_entries j
   where j.source_type='SALES_RETURN'and j.source_id=any(p_returns)and j.reversal_of_id is null
  union all select j.id,'PAYMENT',j.source_id from erp.journal_entries j
   where j.source_type='SALES_PAYMENT'and j.source_id=any(p_payments)and j.reversal_of_id is null
 ),restatements as materialized(
  select x.source_journal_id original,x.inverse_journal_id inverse,x.neutral_journal_id neutral,
   x.effective_journal_id effective,'NOTE'::text owner from cp7_note.journal_restatements x where x.previous_sale_id=any(p_sales)
  union all select x.source_journal_id,x.inverse_journal_id,x.neutral_journal_id,x.effective_journal_id,'RETURN'
   from cp7_sales_return_correction.journal_restatements x where x.original_return_id=any(p_returns)
  union all select f.original_journal_entry_id,r.reversal_journal_entry_id,x.time_neutral_id,x.effective_inverse_id,'PAYMENT'
   from cp7_payment_correction.links x join erp.sales_payment_posting_facts f on f.payment_id=x.original_id
   join erp.sales_payment_reversal_facts r on r.payment_id=x.original_id
   where x.original_id=any(p_payments)and x.time_neutral_id is not null
 ),walk(jid,origin,kind,doc,role)as(
  select id,id,kind,doc,'ORIGINAL'::text from originals
  union
  select child.id,w.origin,w.kind,w.doc,
   case when child.source_type='JOURNAL_REVERSAL'then'INVERSE'
    when child.id=x.neutral then x.owner||'_NEUTRAL'else x.owner||'_EFFECTIVE'end
   from walk w join erp.journal_entries child on child.reversal_of_id=w.jid
    or(child.source_type='JOURNAL_REVERSAL'and child.source_id=w.jid)
    or exists(select 1 from restatements rr where rr.original=w.jid and child.id in(rr.neutral,rr.effective))
   left join restatements x on x.original=w.jid and child.id in(x.neutral,x.effective)
 )select jid,origin,kind,doc,role from walk
$$;

create function ow04_source_proposal.locked_source_family(p_sale uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare family jsonb;check_family jsonb;sales uuid[];returns uuid[];payments uuid[];locked_payments uuid[];
 customer uuid;root uuid;doc record;j record;f erp.sales_payment_posting_facts;rf erp.sales_payment_reversal_facts;
 original erp.journal_entries;candidate uuid;ar uuid;accounts uuid[]:='{}';ar_delta numeric;amount numeric;n bigint;
 documents jsonb:='[]';journals jsonb:='[]';events jsonb:='[]';bindings jsonb:='[]';blockers jsonb:='[]';
 snapshot jsonb;payload jsonb;lineage jsonb;registration jsonb:='[]';members jsonb:='[]';proof jsonb;stock_state jsonb;
 jf jsonb;state jsonb;vectors jsonb;source_hash text;unknown_returns uuid[];financial_state text;src_type text;
 inverse_id uuid;expected_type text;expected_source uuid;predecessors_now uuid[];financial_payload jsonb;
 expected_amount numeric;source_cash uuid;advance_row jsonb;
 member_row jsonb;verified_members jsonb:='[]';verified jsonb;sale_absence jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'OW04_SOURCE_READ_COMMITTED_REQUIRED';end if;
 if p_sale is null then raise exception 'OW04_SOURCE_SALE_REQUIRED';end if;
 -- Owning writers must all take this FIRST. No new permission/context is minted.
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 family:=ow04_source_proposal.sale_family(p_sale);
 select array_agg(value::uuid)into sales from jsonb_array_elements_text(family->'sale_ids');
 root:=(family->>'root_sale_id')::uuid;customer:=(family->>'customer_id')::uuid;
 select coalesce(array_agg(id order by id),'{}')into payments from erp.sales_payments where sale_id=any(sales);
 select coalesce(array_agg(id order by id),'{}')into returns from erp.sales_returns where sale_id=any(sales);
 -- External reallocation predecessor is provenance only, not this invoice's P.
 with recursive predecessors(id)as(
  select unnest(payments)union select p.replaces_payment_id from predecessors x join erp.sales_payments p on p.id=x.id where p.replaces_payment_id is not null
 )select coalesce(array_agg(id order by id),'{}')into locked_payments from predecessors;
 perform 1 from erp.sales_payments where id=any(locked_payments)order by id for share;
 perform 1 from erp.sales_returns where id=any(returns)order by id for share;
 perform 1 from erp.sales_headers where id=any(sales)order by id for share;
 -- Re-read after waits. Never discover and lock an earlier-order new row here.
 check_family:=ow04_source_proposal.sale_family(p_sale);
 if check_family is distinct from family or payments is distinct from
  (select coalesce(array_agg(id order by id),'{}')from erp.sales_payments where sale_id=any(sales))
  or returns is distinct from(select coalesce(array_agg(id order by id),'{}')from erp.sales_returns where sale_id=any(sales))then
  raise exception 'OW04_SOURCE_LOCK_SET_CHANGED';end if;
 with recursive predecessors(id)as(select unnest(payments)union select p.replaces_payment_id
  from predecessors x join erp.sales_payments p on p.id=x.id where p.replaces_payment_id is not null)
 select coalesce(array_agg(id order by id),'{}')into predecessors_now from predecessors;
 if predecessors_now is distinct from locked_payments then raise exception 'OW04_SOURCE_PREDECESSOR_LOCK_SET_CHANGED';end if;
 perform 1 from erp.sales_items where sale_id=any(sales)order by id for share;
 perform 1 from erp.sales_return_items where return_id=any(returns)order by id for share;
 perform 1 from erp.sale_stock_allocations a where exists(select 1 from erp.sales_items i
  where i.id=a.sale_item_id and i.sale_id=any(sales))order by a.id for share;
 perform 1 from erp.fg_stock_movements m where
  (m.source_type='SALE_ITEM'and exists(select 1 from erp.sales_items i where i.id=m.source_id and i.sale_id=any(sales)))
  or(m.source_type='SALES_RETURN_ITEM'and exists(select 1 from erp.sales_return_items i where i.id=m.source_id and i.return_id=any(returns)))
  or exists(select 1 from erp.fg_stock_movements o where o.id=m.reversal_of_id and
   (o.source_type='SALE_ITEM'and exists(select 1 from erp.sales_items i where i.id=o.source_id and i.sale_id=any(sales))
    or o.source_type='SALES_RETURN_ITEM'and exists(select 1 from erp.sales_return_items i where i.id=o.source_id and i.return_id=any(returns))))
  order by m.id for share;
 perform 1 from erp.sales_payment_posting_facts where payment_id=any(locked_payments)order by payment_id for share;
 perform 1 from erp.sales_payment_reversal_facts where payment_id=any(locked_payments)order by payment_id for share;
 perform 1 from erp.initial_import_prepayment_payments where payment_id=any(locked_payments)order by payment_id for share;
 perform 1 from erp.initial_import_prepayments where id in(select advance_id from erp.initial_import_prepayment_payments where payment_id=any(locked_payments))order by id for share;
 perform 1 from cp7_note.revisions where root_sale_id=root order by revision for share;
 perform 1 from cp7_note.payment_replays where previous_payment_id=any(payments)or replacement_payment_id=any(payments)order by previous_payment_id for share;
 perform 1 from cp7_sales_return_correction.links where original_id=any(returns)or replacement_id=any(returns)order by original_id for share;
 perform 1 from cp7_payment_correction.links where original_id=any(payments)or replacement_id=any(payments)order by original_id for share;
 perform 1 from cp7_note.journal_restatements where previous_sale_id=any(sales)order by source_journal_id for share;
 perform 1 from cp7_sales_return_correction.journal_restatements where original_return_id=any(returns)order by source_journal_id for share;
 if to_regclass('cp7_credit.return_families')is not null and to_regclass('cp7_credit.return_family_members')is not null then
  execute 'select 1 from cp7_credit.return_families where family_root_sale_id=$1 order by family_ordinal for share'using root;
  execute 'select 1 from cp7_credit.return_family_members where return_id=any($1)or family_id in(select id from cp7_credit.return_families where family_root_sale_id=$2)order by return_id for share'using returns,root;
 end if;
 perform 1 from erp.customers where id=customer for share;
 perform 1 from erp.cash_accounts where id in(select cash_account_id from erp.sales_payments where id=any(locked_payments))order by id for share;
 lock table erp.accounting_account_mappings in share mode;
 perform 1 from erp.journal_entries where id in(select journal_id from ow04_source_proposal.journal_scope(sales,returns,payments))order by id for share;
 perform 1 from erp.journal_lines where journal_entry_id in(select journal_id from ow04_source_proposal.journal_scope(sales,returns,payments))order by id for share;
 perform 1 from erp.chart_accounts where id in(select l.account_id from erp.journal_lines l
  where l.journal_entry_id in(select journal_id from ow04_source_proposal.journal_scope(sales,returns,payments)))order by id for share;

 -- Actual base document proof. No created/physical/UUID ordering is interpreted
 -- as an immutable family posting ordinal. DRAFT rows are dependencies only.
 for doc in
  select 'SALE'::text kind,h.id,h.id sale_id,h.status,h.customer_id,
   round(coalesce((select sum(i.line_total)from erp.sales_items i where i.sale_id=h.id),0),2)amount,to_jsonb(h)row
   from erp.sales_headers h where h.id=any(sales)
  union all select 'RETURN',r.id,r.sale_id,r.status,r.customer_id,
   round(coalesce((select sum(i.refund_amount)from erp.sales_return_items i where i.return_id=r.id),0),2),to_jsonb(r)
   from erp.sales_returns r where r.id=any(returns)
  union all select 'PAYMENT',p.id,p.sale_id,p.status,customer,round(p.amount,2),to_jsonb(p)
   from erp.sales_payments p where p.id=any(payments)
 loop
  f:=null;rf:=null;original:=null;candidate:=null;stock_state:=null;advance_row:=null;sale_absence:=null;
  if doc.customer_id is distinct from customer then raise exception 'OW04_SOURCE_CUSTOMER_MISMATCH';end if;
  perform ow04_source_proposal.cents(doc.amount);
  if doc.amount<0 then raise exception 'OW04_SOURCE_NEGATIVE_BASE_DOCUMENT';end if;
  src_type:=case doc.kind when'RETURN'then'SALES_RETURN'when'PAYMENT'then'SALES_PAYMENT'else'SALE'end;
  select count(*),(array_agg(id order by id))[1]into n,candidate from erp.journal_entries where source_type=src_type and source_id=doc.id and reversal_of_id is null;
  if n>1 then raise exception 'OW04_SOURCE_MULTIPLE_BASE_JOURNALS';end if;
  if doc.status='DRAFT'then
   if n<>0 then raise exception 'OW04_SOURCE_DRAFT_HAS_FINANCIAL_JOURNAL';end if;
   financial_state:='DRAFT';
  elsif doc.status not in('POSTED','PARTIAL_PAID','PAID','REVERSED')then raise exception 'OW04_SOURCE_DOCUMENT_STATUS_UNSUPPORTED';
  elsif n=0 then
   if doc.amount<>0 or doc.kind='PAYMENT'then raise exception 'OW04_SOURCE_MONETARY_JOURNAL_MISSING';end if;
   if doc.kind='SALE'and to_regprocedure('ow04_source_proposal.sale_absence_fact_v1(uuid)')is null then
    raise exception 'OW04_SOURCE_NO_JOURNAL_SALE_REQUIRES_EXACT_NATIVE_TARGET_PROOF';end if;
   financial_state:='NO_JOURNAL';
  else
   financial_state:='JOURNAL';select *into strict original from erp.journal_entries where id=candidate;
   if original.status is distinct from(case when doc.status='REVERSED'then'REVERSED'else'POSTED'end)then
    raise exception 'OW04_SOURCE_DOCUMENT_JOURNAL_STATUS_MISMATCH';end if;
   if doc.amount<>0 then
    -- Native base AR line has no HPP product/PO dimensions. HPP and revenue
    -- ALSO carry customer_id, so a customer-only sum would be corrupt.
    select count(*),(array_agg(l.account_id order by l.id))[1]into n,ar from erp.journal_lines l
     where l.journal_entry_id=candidate and l.customer_id=customer
      and l.vendor_id is null and l.contractor_id is null and l.po_id is null and l.product_id is null
      and l.debit-l.credit=case doc.kind when'SALE'then doc.amount else-doc.amount end
      and(case when doc.kind='SALE'then l.credit=0 else l.debit=0 end);
    if n<>1 then raise exception 'OW04_SOURCE_AR_LINE_AMBIGUOUS';end if;
    if not ar=any(accounts)then accounts:=accounts||ar;end if;
   end if;
  end if;
  snapshot:=jsonb_build_object('kind',doc.kind,'document',case doc.kind
   when'SALE'then jsonb_build_object('id',doc.id,'customer_id',customer,'sale_date',doc.row->'sale_date')
   when'RETURN'then jsonb_build_object('id',doc.id,'sale_id',doc.sale_id,'customer_id',customer,'physical_at',doc.row->'physical_at')
   else doc.row-'status'end,
   'items',case doc.kind when'SALE'then(select coalesce(jsonb_agg(jsonb_build_object('id',i.id,'sale_id',i.sale_id,
    'product_id',i.product_id,'qty_pcs',i.qty_pcs,'unit_price_snapshot',i.unit_price_snapshot,
    'discount_amount',i.discount_amount,'line_total',i.line_total)order by i.id),'[]')from erp.sales_items i where i.sale_id=doc.id)
   when'RETURN'then(select coalesce(jsonb_agg(jsonb_build_object('id',i.id,'return_id',i.return_id,'product_id',i.product_id,
    'sale_stock_allocation_id',i.sale_stock_allocation_id,'lot_id',i.lot_id,'location_id',i.location_id,
    'quality_grade',i.quality_grade,'qty_pcs',i.qty_pcs,'refund_amount',i.refund_amount)order by i.id),'[]')
    from erp.sales_return_items i where i.return_id=doc.id)else'[]'::jsonb end);
  if doc.kind='SALE'and financial_state='NO_JOURNAL'then
   execute 'select ow04_source_proposal.sale_absence_fact_v1($1)'into sale_absence using doc.id;
   stock_state:=sale_absence->'actual_original_fg_movements';
  end if;
  if doc.kind='RETURN'then
   proof:=(select coalesce(jsonb_agg(to_jsonb(m)-'book_order'order by m.id),'[]')from erp.fg_stock_movements m
    where exists(select 1 from erp.sales_return_items i where i.return_id=doc.id and i.id=m.source_id and m.source_type='SALES_RETURN_ITEM')
     or exists(select 1 from erp.fg_stock_movements o join erp.sales_return_items i on i.id=o.source_id and i.return_id=doc.id
      where o.source_type='SALES_RETURN_ITEM'and m.reversal_of_id=o.id));
   stock_state:=proof;
   if financial_state='NO_JOURNAL'and(
    not exists(select 1 from erp.sales_return_items where return_id=doc.id)
    or exists(select 1 from erp.sales_return_items i where i.return_id=doc.id and(i.qty_pcs<=0 or i.refund_amount<>0 or i.unit_hpp_snapshot<>0
     or not exists(select 1 from erp.sale_stock_allocations a join erp.sales_items si on si.id=a.sale_item_id
      where a.id=i.sale_stock_allocation_id and si.sale_id=doc.sale_id and si.product_id=i.product_id
       and a.lot_id=i.lot_id and i.qty_pcs<=a.qty_pcs)
     or(select count(*)from erp.fg_stock_movements m where m.source_type='SALES_RETURN_ITEM'and m.source_id=i.id
      and m.movement_type='SALE_RETURN'and m.reversal_of_id is null and m.product_id=i.product_id
      and m.lot_id is not distinct from i.lot_id and m.location_id=i.location_id and m.quality_grade=i.quality_grade
      and m.qty_signed=i.qty_pcs and m.customer_id=customer and m.physical_at=(doc.row->>'physical_at')::timestamptz
      and m.unit_hpp_snapshot=0)<>1
     or(select count(*)from erp.fg_stock_movements m where m.source_type='SALES_RETURN_ITEM'and m.source_id=i.id and m.reversal_of_id is null)<>1)))
    then raise exception 'OW04_SOURCE_NO_JOURNAL_PROOF_UNSUPPORTED';end if;
   if financial_state='NO_JOURNAL'and exists(select 1 from erp.fg_stock_movements m
    join erp.sales_return_items i on i.id=m.source_id and i.return_id=doc.id
    where m.source_type='SALES_RETURN_ITEM'and m.reversal_of_id is null and
     (doc.status='POSTED'and exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=m.id)
      or doc.status='REVERSED'and((select count(*)from erp.fg_stock_movements rv where rv.reversal_of_id=m.id)<>1
       or not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=m.id
        and rv.source_type='FG_MOVEMENT_REVERSAL'and rv.source_id=m.id and rv.movement_type='REVERSAL'
        and rv.product_id=m.product_id and rv.lot_id is not distinct from m.lot_id
        and rv.location_id=m.location_id and rv.quality_grade=m.quality_grade and rv.qty_signed=-m.qty_signed
        and rv.unit_hpp_snapshot=m.unit_hpp_snapshot and rv.customer_id is not distinct from m.customer_id
        and rv.physical_at>=m.physical_at))))then raise exception 'OW04_SOURCE_NO_JOURNAL_STOCK_REVERSAL_INCOMPLETE';end if;
  end if;
  if doc.kind='PAYMENT'and financial_state='JOURNAL'then
   select *into strict f from erp.sales_payment_posting_facts where payment_id=doc.id;
   if f.payment_snapshot is distinct from doc.row-'status'or f.sale_id<>doc.sale_id or f.customer_id<>customer
    or f.amount<>doc.amount or f.original_journal_entry_id<>candidate or f.payment_number is distinct from doc.row->>'payment_number'
    or f.payment_date is distinct from(doc.row->>'payment_date')::timestamptz
    or f.cash_account_id is distinct from(doc.row->>'cash_account_id')::uuid
    or f.replaces_payment_id is distinct from(doc.row->>'replaces_payment_id')::uuid
    or(f.journal_economic_date,f.journal_transaction_date,f.journal_posting_at)is distinct from
     (original.economic_date,original.transaction_date,original.posting_at)
    or f.lineage_sha256 is distinct from ow04_source_proposal.native_sha(jsonb_build_array(f.payment_id,f.sale_id,f.customer_id,
     f.payment_number,f.payment_date,f.amount,f.cash_account_id,f.original_journal_entry_id,f.journal_economic_date,
     f.journal_transaction_date,f.journal_posting_at,f.replaces_payment_id,f.predecessor_reversal_journal_id,f.payment_snapshot))then
    raise exception 'OW04_SOURCE_PAYMENT_FACT_INVALID';end if;
   if(f.replaces_payment_id is null)<>(f.predecessor_reversal_journal_id is null)or
    (f.replaces_payment_id is not null and not exists(select 1 from erp.sales_payment_posting_facts pf
     join erp.sales_payment_reversal_facts pr on pr.payment_id=pf.payment_id
     where pf.payment_id=f.replaces_payment_id and pf.sale_id<>f.sale_id and pf.customer_id=f.customer_id
      and pf.amount=f.amount and pf.cash_account_id is not distinct from f.cash_account_id and pf.payment_date=f.payment_date
      and pr.reversal_journal_entry_id=f.predecessor_reversal_journal_id
      and(original.economic_date,original.transaction_date)=(pr.reversal_economic_date,pr.reversal_transaction_date)
      and original.posting_at>=pr.reversal_posting_at))then raise exception 'OW04_SOURCE_PAYMENT_PREDECESSOR_INVALID';end if;
   if f.replaces_payment_id is null and original.economic_date is distinct from(f.payment_date at time zone'Asia/Jakarta')::date then
    raise exception 'OW04_SOURCE_PAYMENT_ORIGINAL_DATE_INVALID';end if;
   select *into rf from erp.sales_payment_reversal_facts where payment_id=doc.id;
   if(doc.status='REVERSED')<>(rf.payment_id is not null)then raise exception 'OW04_SOURCE_PAYMENT_REVERSAL_FACT_MISSING';end if;
   if rf.payment_id is not null and not exists(select 1 from erp.journal_entries q where q.id=rf.reversal_journal_entry_id
    and q.source_type='JOURNAL_REVERSAL'and q.source_id=candidate and q.reversal_of_id=candidate and q.status='POSTED'
    and(q.economic_date,q.transaction_date,q.posting_at)=(rf.reversal_economic_date,rf.reversal_transaction_date,rf.reversal_posting_at)
    and rf.original_journal_entry_id=candidate and rf.lineage_sha256=ow04_source_proposal.native_sha(jsonb_build_array(
     rf.payment_id,rf.original_journal_entry_id,rf.reversal_journal_entry_id,rf.reversal_economic_date,rf.reversal_transaction_date,rf.reversal_posting_at)))then
    raise exception 'OW04_SOURCE_PAYMENT_REVERSAL_FACT_INVALID';end if;
   select jsonb_build_object('link',to_jsonb(l),'wallet',to_jsonb(a))into advance_row
    from erp.initial_import_prepayment_payments l join erp.initial_import_prepayments a on a.id=l.advance_id where l.payment_id=doc.id;
   if advance_row is not null and not coalesce(((advance_row->'link'->>'sales_payment_id')::uuid=doc.id
    and advance_row->'link'->'payment_snapshot'=doc.row-'status'
    and advance_row->'wallet'->>'party_type'='CUSTOMER'and(advance_row->'wallet'->>'party_id')::uuid=customer
    and doc.row->>'payment_method'='OPENING_ADVANCE'and f.cash_account_id is null),false)then
    raise exception 'OW04_SOURCE_ADVANCE_LINK_INVALID';end if;
   select(array_agg(l.account_id order by l.id))[1],count(*)into source_cash,n from erp.journal_lines l
    where l.journal_entry_id=candidate and l.customer_id=customer and l.debit=f.amount and l.credit=0
     and l.vendor_id is null and l.contractor_id is null and l.po_id is null and l.product_id is null;
   if n<>1 or(select count(*)from erp.journal_lines where journal_entry_id=candidate)<>2 then
    raise exception 'OW04_SOURCE_PAYMENT_FUNDING_LINES_INVALID';end if;
   if advance_row is not null and source_cash is distinct from(advance_row->'wallet'->>'coa_account_id')::uuid then
    raise exception 'OW04_SOURCE_ADVANCE_FUNDING_ACCOUNT_INVALID';end if;
   if advance_row is null and(source_cash is distinct from(select coa_account_id from erp.cash_accounts where id=f.cash_account_id)
    or doc.row->>'payment_method'='OPENING_ADVANCE')then raise exception 'OW04_SOURCE_CASH_FUNDING_ACCOUNT_INVALID';end if;
   snapshot:=snapshot||jsonb_build_object('posting_fact',to_jsonb(f),
    'funding_channel',case when advance_row is not null then'ADVANCE_NATIVE_PAYMENT'else'CASH_NATIVE_PAYMENT'end,
    'actual_funding_account_id',source_cash,'advance_link',advance_row->'link');
  end if;
  documents:=documents||jsonb_build_array(jsonb_build_object('kind',doc.kind,'id',doc.id,'sale_id',doc.sale_id,
   'status',doc.status,'current_document_state',doc.row,'current_stock_lineage',stock_state,
   'current_items',case doc.kind when'SALE'then(select coalesce(jsonb_agg(to_jsonb(i)order by i.id),'[]')from erp.sales_items i where i.sale_id=doc.id)
    when'RETURN'then(select coalesce(jsonb_agg(to_jsonb(i)order by i.id),'[]')from erp.sales_return_items i where i.return_id=doc.id)else'[]'::jsonb end,
   'current_allocations',(select coalesce(jsonb_agg(to_jsonb(a)order by a.id),'[]')from erp.sale_stock_allocations a
    join erp.sales_items si on si.id=a.sale_item_id where si.sale_id=doc.sale_id),
   'current_reversal_fact',case when doc.kind='PAYMENT'and rf.payment_id is not null then to_jsonb(rf)end,
   'current_advance',case when doc.kind='PAYMENT'and financial_state='JOURNAL'then advance_row end,
   'current_no_journal_proof',case when doc.kind='SALE'and financial_state='NO_JOURNAL'then sale_absence
    when doc.kind='RETURN'and financial_state='NO_JOURNAL'then
    jsonb_build_object('contract_version','ow04.native-no-return-journal-proof.v1','return_id',doc.id,
     'document',doc.row-'status','items',(select coalesce(jsonb_agg(to_jsonb(i)order by i.id),'[]')from erp.sales_return_items i where i.return_id=doc.id),
     'actual_original_fg_movements',(select coalesce(jsonb_agg(x order by x->>'id'),'[]')from jsonb_array_elements(stock_state)x where x->>'reversal_of_id'is null),
     'actual_allocations',(select coalesce(jsonb_agg(to_jsonb(a)order by a.id),'[]')from erp.sale_stock_allocations a
      where exists(select 1 from erp.sales_return_items i where i.return_id=doc.id and i.sale_stock_allocation_id=a.id)),
     'financial_event','ABSENT')end,
   'amount',ow04_source_proposal.cents(doc.amount),'financial_state',financial_state,
   'original_journal_id',candidate,'source',snapshot,'source_sha256',ow04_source_proposal.sha(snapshot)));
 end loop;
 if cardinality(accounts)>1 then raise exception 'OW04_SOURCE_MIXED_AR_ACCOUNTS';end if;
 ar:=accounts[1];
 if ar is not null and not exists(select 1 from erp.accounting_account_mappings m join erp.chart_accounts a on a.id=m.account_id
  where m.mapping_key='AR_CUSTOMER'and m.account_id=ar and a.account_type='ASSET'and a.normal_balance='DEBIT')then
  blockers:=blockers||jsonb_build_array(jsonb_build_object('code','AR_MAPPING_OR_ACCOUNT_CHANGED','actual_ar_account_id',ar));end if;
 if exists(select 1 from ow04_source_proposal.journal_scope(sales,returns,payments)group by journal_id having count(*)<>1)then
  raise exception 'OW04_SOURCE_JOURNAL_OWNER_AMBIGUOUS';end if;
 -- Never silently omit a registered correction leg, an unregistered known
 -- restatement, or a Native original's required inverse.
 if exists(select 1 from cp7_note.journal_restatements x left join erp.journal_entries o on o.id=x.source_journal_id
  where x.previous_sale_id=any(sales)and not coalesce((o.id is not null and
   (o.source_type='SALE'and o.source_id=x.previous_sale_id
    or o.source_type='SALES_RETURN'and exists(select 1 from erp.sales_returns r where r.id=o.source_id and r.sale_id=x.previous_sale_id)
    or o.source_type='SALES_PAYMENT'and exists(select 1 from erp.sales_payments p where p.id=o.source_id and p.sale_id=x.previous_sale_id))
   and exists(select 1 from erp.journal_entries i where i.id=x.inverse_journal_id and i.source_type='JOURNAL_REVERSAL'and i.source_id=o.id and i.reversal_of_id=o.id)
   and exists(select 1 from erp.journal_entries where id=x.neutral_journal_id)
   and exists(select 1 from erp.journal_entries where id=x.effective_journal_id)),false))then
  raise exception 'OW04_SOURCE_NOTE_RESTATEMENT_INCOMPLETE';end if;
 if exists(select 1 from cp7_sales_return_correction.journal_restatements x
  where x.original_return_id=any(returns)and not exists(select 1 from erp.journal_entries o
   join erp.journal_entries i on i.id=x.inverse_journal_id and i.source_type='JOURNAL_REVERSAL'and i.source_id=o.id and i.reversal_of_id=o.id
   join erp.journal_entries n on n.id=x.neutral_journal_id join erp.journal_entries e on e.id=x.effective_journal_id
   where o.id=x.source_journal_id and o.source_type='SALES_RETURN'and o.source_id=x.original_return_id))then
  raise exception 'OW04_SOURCE_RETURN_RESTATEMENT_INCOMPLETE';end if;
 if exists(select 1 from cp7_payment_correction.links x where(x.original_id=any(payments)or x.replacement_id=any(payments))and
  (not exists(select 1 from erp.sales_payments a join erp.sales_payments b on b.id=x.replacement_id
    where a.id=x.original_id and a.sale_id=x.sale_id and b.sale_id=x.sale_id and a.status='REVERSED')
   or(x.time_neutral_id is not null and(not exists(select 1 from erp.journal_entries where id=x.time_neutral_id)
    or not exists(select 1 from erp.journal_entries where id=x.effective_inverse_id)))))then
  raise exception 'OW04_SOURCE_PAYMENT_CORRECTION_INCOMPLETE';end if;
 if exists(select 1 from cp7_payment_correction.links x join erp.sales_payment_posting_facts pf on pf.payment_id=x.original_id
   join erp.sales_payment_reversal_facts pr on pr.payment_id=x.original_id
   join erp.journal_entries original_j on original_j.id=pf.original_journal_entry_id
   join erp.journal_entries inverse_j on inverse_j.id=pr.reversal_journal_entry_id
   where x.original_id=any(payments)and(x.time_neutral_id is not null)is distinct from(original_j.economic_date<>inverse_j.economic_date))then
  raise exception 'OW04_SOURCE_PAYMENT_CORRECTION_RESTATEMENT_MISSING_OR_UNEXPECTED';end if;
 if exists(select 1 from cp7_note.revisions revision join erp.journal_entries original_j
   on original_j.source_type='SALE'and original_j.source_id=revision.previous_sale_id and original_j.reversal_of_id is null
   join erp.journal_entries inverse_j on inverse_j.source_type='JOURNAL_REVERSAL'and inverse_j.source_id=original_j.id and inverse_j.reversal_of_id=original_j.id
   where revision.root_sale_id=root and(original_j.economic_date<>inverse_j.economic_date)is distinct from
    exists(select 1 from cp7_note.journal_restatements x where x.source_journal_id=original_j.id and x.inverse_journal_id=inverse_j.id))then
  raise exception 'OW04_SOURCE_NOTE_SALE_RESTATEMENT_MISSING_OR_UNEXPECTED';end if;
 if exists(select 1 from cp7_note.payment_replays replay join cp7_note.revisions revision on revision.id=replay.correction_id
   join erp.sales_payments previous_p on previous_p.id=replay.previous_payment_id
   join erp.sales_payments replacement_p on replacement_p.id=replay.replacement_payment_id
   where(replay.previous_payment_id=any(payments)or replay.replacement_payment_id=any(payments))and
    (previous_p.sale_id<>revision.previous_sale_id or replacement_p.sale_id<>revision.replacement_sale_id
     or previous_p.status<>'REVERSED'or(previous_p.amount,previous_p.payment_date,previous_p.cash_account_id,previous_p.payment_method)
      is distinct from(replacement_p.amount,replacement_p.payment_date,replacement_p.cash_account_id,replacement_p.payment_method)
     or(select advance_id from erp.initial_import_prepayment_payments where payment_id=previous_p.id)is distinct from
      (select advance_id from erp.initial_import_prepayment_payments where payment_id=replacement_p.id)))then
  raise exception 'OW04_SOURCE_NOTE_PAYMENT_REPLAY_SOURCE_CHANGED';end if;
 if exists(select 1 from cp7_note.payment_replays replay join erp.sales_payment_posting_facts pf on pf.payment_id=replay.previous_payment_id
   join erp.sales_payment_reversal_facts pr on pr.payment_id=replay.previous_payment_id
   join erp.journal_entries original_j on original_j.id=pf.original_journal_entry_id
   join erp.journal_entries inverse_j on inverse_j.id=pr.reversal_journal_entry_id
   where replay.previous_payment_id=any(payments)and(original_j.economic_date<>inverse_j.economic_date)is distinct from
    exists(select 1 from cp7_note.journal_restatements x where x.source_journal_id=original_j.id and x.inverse_journal_id=inverse_j.id))then
  raise exception 'OW04_SOURCE_NOTE_PAYMENT_RESTATEMENT_MISSING_OR_UNEXPECTED';end if;
 if exists(select 1 from erp.journal_entries orphan where orphan.source_type in('NOTE_REVERSAL_TIME_NEUTRAL','NOTE_REVERSAL_EFFECTIVE',
  'RETURN_CORRECTION_TIME_NEUTRAL','RETURN_CORRECTION_EFFECTIVE','PAYMENT_CORRECTION_TIME_NEUTRAL','PAYMENT_CORRECTION_EFFECTIVE')
  and(orphan.source_id=any(payments)or orphan.source_id in(select journal_id from ow04_source_proposal.journal_scope(sales,returns,payments)))
  and orphan.id not in(select journal_id from ow04_source_proposal.journal_scope(sales,returns,payments)))then
  raise exception 'OW04_SOURCE_UNREGISTERED_RESTATEMENT';end if;
 for j in select s.*,q.*from ow04_source_proposal.journal_scope(sales,returns,payments)s join erp.journal_entries q on q.id=s.journal_id order by q.id loop
  if j.role is null then raise exception 'OW04_SOURCE_UNCLASSIFIED_JOURNAL_DESCENDANT';end if;
  if j.status not in('POSTED','REVERSED')or j.transaction_date<j.economic_date then raise exception 'OW04_SOURCE_JOURNAL_STATE_OR_PAIR_INVALID';end if;
  if exists(select 1 from erp.journal_lines l where l.journal_entry_id=j.id and(l.debit<0 or l.credit<0
   or l.debit::text in('NaN','Infinity','-Infinity')or l.credit::text in('NaN','Infinity','-Infinity')))
   or not exists(select 1 from erp.journal_lines l where l.journal_entry_id=j.id group by l.journal_entry_id
    having sum(l.debit)=sum(l.credit)and sum(l.debit)>0)then raise exception 'OW04_SOURCE_JOURNAL_LINES_INVALID';end if;
  if j.role='INVERSE'and not exists(select 1 from erp.journal_entries o where o.id=j.reversal_of_id and o.id=j.source_id
   and j.source_type='JOURNAL_REVERSAL'and o.status='REVERSED'and j.economic_date>=o.economic_date and j.transaction_date>=o.transaction_date)then
   blockers:=blockers||jsonb_build_array(jsonb_build_object('code','INVERSE_SOURCE_FLOOR_OR_LINK_INVALID','journal_id',j.id));end if;
  if j.role='INVERSE'and ow04_source_proposal.line_vector(j.id,false)is distinct from ow04_source_proposal.line_vector(j.reversal_of_id,true)then
   raise exception 'OW04_SOURCE_INVERSE_LINES_CHANGED';end if;
  if j.role like'%_NEUTRAL'or j.role like'%_EFFECTIVE'then
   inverse_id:=null;
   if j.role like'NOTE_%'then select x.inverse_journal_id into strict inverse_id from cp7_note.journal_restatements x where x.source_journal_id=j.origin_journal_id;
   elsif j.role like'RETURN_%'then select x.inverse_journal_id into strict inverse_id from cp7_sales_return_correction.journal_restatements x where x.source_journal_id=j.origin_journal_id;
   else select r.reversal_journal_entry_id into strict inverse_id from erp.sales_payment_reversal_facts r where r.original_journal_entry_id=j.origin_journal_id;end if;
   expected_type:=case j.role when'NOTE_NEUTRAL'then'NOTE_REVERSAL_TIME_NEUTRAL'when'NOTE_EFFECTIVE'then'NOTE_REVERSAL_EFFECTIVE'
    when'RETURN_NEUTRAL'then'RETURN_CORRECTION_TIME_NEUTRAL'when'RETURN_EFFECTIVE'then'RETURN_CORRECTION_EFFECTIVE'
    when'PAYMENT_NEUTRAL'then'PAYMENT_CORRECTION_TIME_NEUTRAL'else'PAYMENT_CORRECTION_EFFECTIVE'end;
   expected_source:=case when j.role like'PAYMENT_%'then j.document_id else inverse_id end;
   if inverse_id is null or j.source_type<>expected_type or j.source_id is distinct from expected_source
    or ow04_source_proposal.line_vector(j.id,false)is distinct from ow04_source_proposal.line_vector(inverse_id,j.role like'%_NEUTRAL')then
    raise exception 'OW04_SOURCE_RESTATEMENT_LINES_OR_LINK_INVALID';end if;
   if j.role like'%_NEUTRAL'and(j.economic_date,j.transaction_date)is distinct from
    (select(q.economic_date,q.transaction_date)from erp.journal_entries q where q.id=inverse_id)then
    raise exception 'OW04_SOURCE_NEUTRAL_PAIR_CHANGED';end if;
   if j.role like'%_EFFECTIVE'and j.economic_date is distinct from(select economic_date from erp.journal_entries where id=j.origin_journal_id)then
    raise exception 'OW04_SOURCE_EFFECTIVE_ECONOMIC_DATE_CHANGED';end if;
  end if;
  if j.role like'%_EFFECTIVE'and j.transaction_date<(select transaction_date from erp.journal_entries where id=j.origin_journal_id)then
   blockers:=blockers||jsonb_build_array(jsonb_build_object('code','RESTATEMENT_PRECEDES_ORIGINAL_BOOK','journal_id',j.id));end if;
  payload:=ow04_source_proposal.journal_payload(j.id);
  select coalesce(sum(l.debit-l.credit),0)into ar_delta from erp.journal_lines l where l.journal_entry_id=j.id and l.account_id=ar;
  if exists(select 1 from erp.journal_lines l where l.journal_entry_id=j.id and l.account_id=ar and l.customer_id is distinct from customer)then raise exception 'OW04_SOURCE_AR_CUSTOMER_CHANGED';end if;
  amount:=case when j.document_kind='PAYMENT'then-ar_delta else ar_delta end;
  if j.role='ORIGINAL'then
   expected_amount:=(select(x->>'amount')::numeric from jsonb_array_elements(documents)x
    where x->>'kind'=j.document_kind and(x->>'id')::uuid=j.document_id);
   if ar_delta is distinct from(case when j.document_kind='SALE'then expected_amount else-expected_amount end)
    or(select count(*)from erp.journal_lines l where l.journal_entry_id=j.id and l.account_id=ar)<>
     (case when expected_amount=0 then 0 else 1 end)then raise exception 'OW04_SOURCE_BASE_AR_TOTAL_MISMATCH';end if;
   if j.document_kind in('SALE','RETURN')and j.economic_date is distinct from
    (select(case when j.document_kind='SALE'then(x->'source'->'document'->>'sale_date')::timestamptz
     else(x->'source'->'document'->>'physical_at')::timestamptz end at time zone'Asia/Jakarta')::date
     from jsonb_array_elements(documents)x where x->>'kind'=j.document_kind and(x->>'id')::uuid=j.document_id)then
    raise exception 'OW04_SOURCE_ORIGINAL_DOCUMENT_DATE_MISMATCH';end if;
  end if;
  select count(*)into n from erp.journal_entries i where i.source_type='JOURNAL_REVERSAL'
   and(i.source_id=j.id or i.reversal_of_id=j.id);
  if j.status='REVERSED'and(n<>1 or not exists(select 1 from erp.journal_entries i
    where i.source_type='JOURNAL_REVERSAL'and i.source_id=j.id and i.reversal_of_id=j.id))
   or j.status='POSTED'and n<>0 then raise exception 'OW04_SOURCE_JOURNAL_REVERSAL_HISTORY_INCOMPLETE';end if;
  snapshot:=(select x->'source'from jsonb_array_elements(documents)x where x->>'kind'=j.document_kind and(x->>'id')::uuid=j.document_id);
  financial_payload:=ow04_source_proposal.financial_journal_payload(j.id,ar);
  source_hash:=ow04_source_proposal.sha(jsonb_build_object('financial_payload',financial_payload,'base_source',snapshot,'origin_journal_id',j.origin_journal_id,'role',j.role));
  events:=events||jsonb_build_array(jsonb_build_object('id','journal:'||j.id::text,'kind',case when j.document_kind='PAYMENT'then'FUNDING'else'NET'end,
   'amount',ow04_source_proposal.cents(amount),'economic_date',j.economic_date::text,'transaction_date',j.transaction_date::text,'source_sha256',source_hash));
  bindings:=bindings||jsonb_build_array(jsonb_build_object('id','journal:'||j.id::text,'document_kind',j.document_kind,'document_id',j.document_id,
   'origin_journal_id',j.origin_journal_id,'role',j.role,'ar_account_id',ar));
  journals:=journals||jsonb_build_array(jsonb_build_object('id',j.id,'status',j.status,'payload',payload,
   'financial_payload',financial_payload,'source_sha256',source_hash));
 end loop;
 select coalesce(jsonb_agg(x order by x->>'id'collate"C"),'[]')into events from jsonb_array_elements(events)x;
 -- No authority/default/fake historical ordinal is supplied by this reader.
 if to_regclass('cp7_credit.return_families')is not null and to_regclass('cp7_credit.return_family_members')is not null then
  execute 'select coalesce(jsonb_agg(to_jsonb(f)order by f.family_ordinal),''[]'')from cp7_credit.return_families f where f.family_root_sale_id=$1'into registration using root;
  execute 'select coalesce(jsonb_agg(to_jsonb(m)order by m.return_id),''[]'')from cp7_credit.return_family_members m where m.return_id=any($1)or m.family_id in(select id from cp7_credit.return_families where family_root_sale_id=$2)'into members using returns,root;
  if exists(select 1 from jsonb_array_elements(members)m where not exists(select 1 from jsonb_array_elements(registration)registered
    where registered->>'id'=m->>'family_id'))then raise exception 'OW04_SOURCE_RETURN_MEMBER_WRONG_ROOT';end if;
  if exists(select 1 from jsonb_array_elements(registration)registered where
   not exists(select 1 from jsonb_array_elements(members)m where m->>'family_id'=registered->>'id'
    and m->>'return_id'=registered->>'first_return_id'and m->>'member_kind'='ORIGINAL')
   or(select count(*)from jsonb_array_elements(members)m where m->>'family_id'=registered->>'id'and m->>'member_kind'='ORIGINAL')<>1)then
   raise exception 'OW04_SOURCE_RETURN_REGISTRATION_FIRST_MEMBER_MISSING';end if;
  if exists(select 1 from jsonb_array_elements(members)m join jsonb_array_elements(documents)d
    on d->>'kind'='RETURN'and d->>'id'=m->>'return_id'
    where(m->>'source_journal_id')::uuid is distinct from(d->>'original_journal_id')::uuid
     or m->>'financial_state'is distinct from d->>'financial_state')then
   raise exception 'OW04_SOURCE_RETURN_MEMBER_FINANCIAL_SOURCE_MISMATCH';end if;
  if jsonb_array_length(members)>0 then
   if to_regprocedure('ow04_source_proposal.verify_return_member_v1(uuid)')is null then
    blockers:=blockers||jsonb_build_array(jsonb_build_object('code','RETURN_REGISTRY_FACTUAL_VERIFIER_MISSING'));
   else
    for member_row in select value from jsonb_array_elements(members)loop
     execute 'select ow04_source_proposal.verify_return_member_v1($1)'into verified using(member_row->>'return_id')::uuid;
     if(verified->>'family_root_sale_id')::uuid<>root then raise exception 'OW04_SOURCE_RETURN_MEMBER_WRONG_ROOT';end if;
     verified_members:=verified_members||jsonb_build_array(verified);
    end loop;
   end if;
  end if;
 end if;
 select coalesce(array_agg(r.id order by r.id),'{}')into unknown_returns from erp.sales_returns r where r.id=any(returns)and r.status<>'DRAFT'
  and not exists(select 1 from jsonb_array_elements(members)m where(m->>'return_id')::uuid=r.id);
 if cardinality(unknown_returns)>0 then blockers:=blockers||jsonb_build_array(jsonb_build_object('code','IMMUTABLE_RETURN_FAMILY_OR_ORDER_MISSING','return_ids',unknown_returns));end if;
 if jsonb_array_length(family->'note_revisions')>0 and cardinality(unknown_returns)>0 then blockers:=blockers||jsonb_build_array(jsonb_build_object('code','NOTE_RETURN_REPLAY_HEADER_LINK_UNPROVEN'));end if;
 lineage:=jsonb_build_object('note_revisions',family->'note_revisions',
  'note_restatements',(select coalesce(jsonb_agg(to_jsonb(x)order by x.source_journal_id),'[]')from cp7_note.journal_restatements x where x.previous_sale_id=any(sales)),
  'payment_replays',(select coalesce(jsonb_agg(to_jsonb(x)order by x.previous_payment_id),'[]')from cp7_note.payment_replays x where x.previous_payment_id=any(payments)or x.replacement_payment_id=any(payments)),
  'return_corrections',(select coalesce(jsonb_agg(to_jsonb(x)order by x.original_id),'[]')from cp7_sales_return_correction.links x where x.original_id=any(returns)or x.replacement_id=any(returns)),
  'return_restatements',(select coalesce(jsonb_agg(to_jsonb(x)order by x.source_journal_id),'[]')from cp7_sales_return_correction.journal_restatements x where x.original_return_id=any(returns)),
  'payment_corrections',(select coalesce(jsonb_agg(to_jsonb(x)order by x.original_id),'[]')from cp7_payment_correction.links x where x.original_id=any(payments)or x.replacement_id=any(payments)),
  'family_registration',registration,'family_members',members,'verified_members',verified_members);
 select coalesce(jsonb_agg(x order by x->>'kind',x->>'id'),'[]')into documents from jsonb_array_elements(documents)x;
 select coalesce(jsonb_agg(x order by x->>'id'),'[]')into bindings from jsonb_array_elements(bindings)x;
 state:=jsonb_build_object('family',family,'documents',documents,'journals',journals,'lineage',lineage,
  'customer',(select to_jsonb(c)from erp.customers c where c.id=customer),
  'ar_account',(select to_jsonb(a)from erp.chart_accounts a where a.id=ar),
  'ar_mapping',(select to_jsonb(m)from erp.accounting_account_mappings m where m.mapping_key='AR_CUSTOMER'),
  'source_cash_accounts',(select coalesce(jsonb_agg(to_jsonb(c)order by c.id),'[]')from erp.cash_accounts c where c.id in(
   select cash_account_id from erp.sales_payments where id=any(locked_payments))),
  'external_predecessor_facts',(select coalesce(jsonb_agg(jsonb_build_object('payment',to_jsonb(p),'posting',to_jsonb(ppf),'reversal',to_jsonb(r))order by p.id),'[]')
   from erp.sales_payments p left join erp.sales_payment_posting_facts ppf on ppf.payment_id=p.id
   left join erp.sales_payment_reversal_facts r on r.payment_id=p.id where p.id=any(locked_payments)and not p.id=any(payments)),
  'source_lock_ids',jsonb_build_object('sales',sales,'returns',returns,'payments',locked_payments));
 return state||jsonb_build_object('contract_version','ow04.actual-base-source-family.v1','source_status',case when jsonb_array_length(blockers)=0 then'BASE_COLLECTED'else'BLOCKED'end,
  'blockers',blockers,'events',events,'event_bindings',bindings,'events_sha256',ow04_source_proposal.sha(events),
  'state_sha256',ow04_source_proposal.sha(state),'raw_funding_basis','ALL_NATIVE_PAYMENT_AR_JOURNALS_INCLUDING_ADVANCES_ONCE_NO_U_DUPLICATION',
  'scope','ACTUAL_EXISTING_BASE_JOURNALS_ONLY_NO_PROJECTION_AUTHORITY_OR_COHORT_RECONCILIATION');
end $$;

-- Read after locked_source_family has acquired source locks BEFORE period
-- SHARE. This function discovers no new locks and confers no write authority.
-- A replacement not yet linked must use the owning sealed projection binding
-- from its ACTUAL original return; it may not masquerade as an ordinary return.
create function ow04_source_proposal.return_causal_book_floor(p_return uuid)returns date
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare r erp.sales_returns;family jsonb;sales uuid[];related uuid[];root uuid;members jsonb:='[]';floor date;member jsonb;verified jsonb;
begin
 select *into strict r from erp.sales_returns where id=p_return;
 family:=ow04_source_proposal.sale_family(r.sale_id);root:=(family->>'root_sale_id')::uuid;
 select array_agg(value::uuid)into sales from jsonb_array_elements_text(family->'sale_ids');
 with recursive connected(id)as(select p_return union select
  case when l.original_id=p.id then l.replacement_id else l.original_id end from connected p
  join cp7_sales_return_correction.links l on p.id in(l.original_id,l.replacement_id))
 select array_agg(id)into related from connected;
 if exists(select 1 from cp7_sales_return_correction.links l where(l.original_id=any(related)or l.replacement_id=any(related))
  and not exists(select 1 from erp.sales_returns o join erp.sales_returns n on n.id=l.replacement_id
   where o.id=l.original_id and o.sale_id=l.sale_id and n.sale_id=l.sale_id and o.status='REVERSED'))then
  raise exception 'OW04_SOURCE_RETURN_CORRECTION_LINEAGE_INVALID';end if;
 if to_regclass('cp7_credit.return_family_members')is not null then
  execute 'select coalesce(jsonb_agg(to_jsonb(m)),''[]'')from cp7_credit.return_family_members m where m.family_id=(select family_id from cp7_credit.return_family_members where return_id=$1)'into members using p_return;
  if jsonb_array_length(members)>0 then
   if to_regprocedure('ow04_source_proposal.verify_return_member_v1(uuid)')is null then
    raise exception 'OW04_SOURCE_RETURN_REGISTRY_CAUSAL_PROOF_REQUIRED';end if;
   for member in select value from jsonb_array_elements(members)loop
    execute 'select ow04_source_proposal.verify_return_member_v1($1)'into verified using(member->>'return_id')::uuid;
    if(verified->>'family_root_sale_id')::uuid<>root then raise exception 'OW04_SOURCE_RETURN_MEMBER_WRONG_ROOT';end if;
   end loop;
   select array_agg((x->>'return_id')::uuid)into related from jsonb_array_elements(members)x;
  end if;
 end if;
 if jsonb_array_length(family->'note_revisions')>0 and jsonb_array_length(members)=0 then
  raise exception 'OW04_SOURCE_NOTE_RETURN_FAMILY_UNPROVEN';end if;
 if exists(select 1 from cp7_sales_return_correction.context c where c.sale_id=r.sale_id and c.return_id<>p_return
  and c.backend_pid=pg_backend_pid()and c.transaction_id=txid_current())and jsonb_array_length(members)=0 then
  raise exception 'OW04_SOURCE_PROJECTION_FAMILY_BINDING_REQUIRED';end if;
 select max(j.transaction_date)into floor from erp.journal_entries j where j.reversal_of_id is null and j.status in('POSTED','REVERSED')
  and(j.source_type='SALE'and j.source_id=any(sales)or j.source_type='SALES_RETURN'and j.source_id=any(related));
 if floor is null then raise exception 'OW04_SOURCE_NO_DATED_CAUSAL_JOURNAL';end if;
 return floor;
end $$;
revoke all on all functions in schema ow04_source_proposal from public,anon,authenticated,service_role,
 cp7_capture,cp7_sales_read,cp7_sales_write;
