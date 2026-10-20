-- SOURCE-ONLY pure factual proof proposal. No writer/authority/backfill API.
do $not_an_installer$begin
 raise exception 'OW04_MEMBER_PROOF_REQUIRES_PROTECTED_OWNING_REGISTRATION';
end $not_an_installer$;

create function ow04_source_proposal.family_read_v1(p_sale uuid)returns jsonb
language plpgsql stable security invoker set search_path=''as $$
declare roots uuid[];root uuid;ids uuid[];previous uuid;r record;n bigint:=0;customer uuid;
begin
 select array_agg(distinct root_sale_id)into roots from cp7_note.revisions
  where p_sale in(root_sale_id,previous_sale_id,replacement_sale_id);
 if cardinality(roots)>1 then raise exception 'OW04_MEMBER_ROOT_AMBIGUOUS';end if;
 root:=coalesce(roots[1],p_sale);previous:=root;ids:=array[root];
 for r in select *from cp7_note.revisions where root_sale_id=root order by revision loop
  n:=n+1;
  if r.revision<>n or r.previous_sale_id<>previous or r.replacement_sale_id=any(ids)then
   raise exception 'OW04_MEMBER_NOTE_CHAIN_INVALID';end if;
  ids:=ids||r.replacement_sale_id;previous:=r.replacement_sale_id;
 end loop;
 select customer_id into strict customer from erp.sales_headers where id=root;
 if not p_sale=any(ids)or exists(select 1 from unnest(ids)x left join erp.sales_headers h on h.id=x
  where h.id is null or h.customer_id is distinct from customer)then raise exception 'OW04_MEMBER_SALE_FAMILY_INVALID';end if;
 return jsonb_build_object('root_sale_id',root,'sale_ids',ids,'customer_id',customer,'current_leaf_id',previous);
end $$;

-- Complete original RETURN monetary identity, read in the caller's snapshot.
-- Mutable document status/HPP cost/current masters are not event identity.
-- A real zero-AR HPP journal is JOURNAL, never a fabricated NO_JOURNAL event.
create function ow04_source_proposal.return_fact_v1(p_return uuid)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare r erp.sales_returns;family jsonb;monetary jsonb;items jsonb;proof jsonb;j erp.journal_entries;
 amount numeric;n bigint;candidate uuid;ar uuid;ar_accounts uuid[];originals jsonb;allocations jsonb;financial jsonb;state text;
begin
 select *into strict r from erp.sales_returns where id=p_return;
 if r.status not in('POSTED','REVERSED')then raise exception 'OW04_MEMBER_RETURN_NOT_FINISHED';end if;
 family:=ow04_source_proposal.family_read_v1(r.sale_id);
 if r.customer_id is distinct from(family->>'customer_id')::uuid then raise exception 'OW04_MEMBER_CUSTOMER_CHANGED';end if;
 select sum(refund_amount),jsonb_agg(jsonb_build_object('id',i.id,'return_id',i.return_id,'product_id',i.product_id,
  'sale_stock_allocation_id',i.sale_stock_allocation_id,'lot_id',i.lot_id,'location_id',i.location_id,
  'quality_grade',i.quality_grade,'qty_pcs',i.qty_pcs,'refund_amount',i.refund_amount)order by i.id)
 into amount,items from erp.sales_return_items i where i.return_id=r.id;
 if amount is null or amount<0 or exists(select 1 from erp.sales_return_items i where i.return_id=r.id
  and(i.qty_pcs<=0 or i.refund_amount<0))then raise exception 'OW04_MEMBER_RETURN_LINES_INVALID';end if;
 perform ow04_source_proposal.cents(amount);
 monetary:=jsonb_build_object('kind','RETURN','document',jsonb_build_object('id',r.id,'sale_id',r.sale_id,
  'customer_id',r.customer_id,'physical_at',r.physical_at),'items',items);
 select count(*),(array_agg(id order by id))[1]into n,candidate from erp.journal_entries
  where source_type='SALES_RETURN'and source_id=r.id and reversal_of_id is null;
 if n>1 or amount<>0 and n<>1 then raise exception 'OW04_MEMBER_ORIGINAL_JOURNAL_MISSING_OR_DUPLICATE';end if;
 if n=1 then
  state:='JOURNAL';select *into strict j from erp.journal_entries where id=candidate;
  if j.economic_date is distinct from(r.physical_at at time zone'Asia/Jakarta')::date or j.transaction_date<j.economic_date
   or j.status is distinct from(case when r.status='REVERSED'then'REVERSED'else'POSTED'end)then
   raise exception 'OW04_MEMBER_ORIGINAL_JOURNAL_PAIR_OR_STATE_CHANGED';end if;
  select count(*)into n from erp.journal_entries inverse where inverse.source_type='JOURNAL_REVERSAL'
   and(inverse.source_id=j.id or inverse.reversal_of_id=j.id);
  if j.status='POSTED'and n<>0 or j.status='REVERSED'and(n<>1 or not exists(select 1 from erp.journal_entries inverse
    where inverse.source_type='JOURNAL_REVERSAL'and inverse.source_id=j.id and inverse.reversal_of_id=j.id
     and inverse.economic_date>=j.economic_date and inverse.transaction_date>=j.transaction_date))then
   raise exception 'OW04_MEMBER_ORIGINAL_INVERSE_HISTORY_INCOMPLETE';end if;
  if amount<>0 then
   select count(*),(array_agg(l.account_id order by l.id))[1]into n,ar from erp.journal_lines l
    where l.journal_entry_id=j.id and l.customer_id=r.customer_id and l.debit=0 and l.credit=amount
     and l.vendor_id is null and l.contractor_id is null and l.po_id is null and l.product_id is null;
   if n<>1 or(select sum(l.debit-l.credit)from erp.journal_lines l where l.journal_entry_id=j.id and l.account_id=ar)<>-amount
    or(select count(*)from erp.journal_lines l where l.journal_entry_id=j.id and l.account_id=ar)<>1 then
    raise exception 'OW04_MEMBER_ORIGINAL_AR_CHANGED';end if;
  else
   -- Derive historical AR from the actual family's nonzero SALE origins.
   select array_agg(distinct l.account_id)into ar_accounts from erp.sales_headers h
    join erp.journal_entries sj on sj.source_type='SALE'and sj.source_id=h.id and sj.reversal_of_id is null
    join erp.journal_lines l on l.journal_entry_id=sj.id and l.customer_id=h.customer_id
     and l.credit=0 and l.debit=(select sum(si.line_total)from erp.sales_items si where si.sale_id=h.id)
     and l.debit>0 and l.vendor_id is null and l.contractor_id is null and l.po_id is null and l.product_id is null
    where h.id in(select value::uuid from jsonb_array_elements_text(family->'sale_ids'));
   if cardinality(ar_accounts)>1 then raise exception 'OW04_MEMBER_AR_ACCOUNT_AMBIGUOUS';end if;
   ar:=ar_accounts[1];
   if exists(select 1 from erp.journal_lines where journal_entry_id=j.id and account_id=ar)then
    raise exception 'OW04_MEMBER_ZERO_RETURN_HAS_AR_LINES';end if;
  end if;
  if not exists(select 1 from erp.journal_lines where journal_entry_id=j.id group by journal_entry_id
   having sum(debit)=sum(credit)and sum(debit)>0)then raise exception 'OW04_MEMBER_ORIGINAL_UNBALANCED';end if;
  financial:=ow04_source_proposal.financial_journal_payload(j.id,ar);
 else
  state:='NO_JOURNAL';
  if exists(select 1 from erp.sales_return_items i where i.return_id=r.id and(i.refund_amount<>0 or i.unit_hpp_snapshot<>0
   or not exists(select 1 from erp.sale_stock_allocations a join erp.sales_items si on si.id=a.sale_item_id
    where a.id=i.sale_stock_allocation_id and si.sale_id=r.sale_id and si.product_id=i.product_id
     and a.lot_id=i.lot_id and i.qty_pcs<=a.qty_pcs)
   or(select count(*)from erp.fg_stock_movements m where m.source_type='SALES_RETURN_ITEM'and m.source_id=i.id
    and m.reversal_of_id is null)<>1
   or not exists(select 1 from erp.fg_stock_movements m where m.source_type='SALES_RETURN_ITEM'and m.source_id=i.id
    and m.reversal_of_id is null and m.movement_type='SALE_RETURN'and m.product_id=i.product_id and m.lot_id=i.lot_id
    and m.location_id=i.location_id and m.quality_grade=i.quality_grade and m.customer_id=r.customer_id
    and m.qty_signed=i.qty_pcs and m.unit_hpp_snapshot=0 and m.physical_at=r.physical_at)))then
   raise exception 'OW04_MEMBER_NO_JOURNAL_PHYSICAL_PROOF_INVALID';end if;
  select coalesce(jsonb_agg(to_jsonb(m)-'book_order'order by m.id),'[]')into originals from erp.fg_stock_movements m
   where m.source_type='SALES_RETURN_ITEM'and m.reversal_of_id is null
    and exists(select 1 from erp.sales_return_items i where i.return_id=r.id and i.id=m.source_id);
  if exists(select 1 from jsonb_array_elements(originals)x where
   (r.status='POSTED'and exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=(x->>'id')::uuid))
   or(r.status='REVERSED'and((select count(*)from erp.fg_stock_movements rv where rv.reversal_of_id=(x->>'id')::uuid)<>1
    or not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=(x->>'id')::uuid
     and rv.source_type='FG_MOVEMENT_REVERSAL'and rv.source_id=(x->>'id')::uuid and rv.movement_type='REVERSAL'
     and rv.product_id=(x->>'product_id')::uuid and rv.lot_id is not distinct from(x->>'lot_id')::uuid
     and rv.location_id=(x->>'location_id')::uuid and rv.quality_grade=x->>'quality_grade'
     and rv.qty_signed=-(x->>'qty_signed')::integer and rv.unit_hpp_snapshot=0
     and rv.customer_id is not distinct from(x->>'customer_id')::uuid and rv.physical_at>=(x->>'physical_at')::timestamptz))))then
   raise exception 'OW04_MEMBER_NO_JOURNAL_STOCK_REVERSAL_INVALID';end if;
  select jsonb_agg(to_jsonb(a)order by a.id)into allocations from erp.sale_stock_allocations a
   where exists(select 1 from erp.sales_return_items i where i.return_id=r.id and i.sale_stock_allocation_id=a.id);
  proof:=jsonb_build_object('contract_version','ow04.native-no-return-journal-proof.v1','return_id',r.id,
   'document',to_jsonb(r)-'status','items',(select jsonb_agg(to_jsonb(i)order by i.id)from erp.sales_return_items i where i.return_id=r.id),
   'actual_original_fg_movements',originals,'actual_allocations',allocations,'financial_event','ABSENT');
 end if;
 return jsonb_build_object('return_id',r.id,'sale_id',r.sale_id,'family_root_sale_id',family->'root_sale_id',
  'customer_id',r.customer_id,'financial_state',state,'source_journal_id',candidate,
  'financial_source_sha256',ow04_source_proposal.sha(jsonb_build_object('base_source',monetary,'financial_payload',financial)),
  'no_journal_proof',proof);
end $$;

create function ow04_source_proposal.require_restatement_v1(p_source uuid,p_owner text)returns void
language plpgsql stable security invoker set search_path=''as $$
declare original erp.journal_entries;inverse erp.journal_entries;recorded boolean;
begin
 select *into strict original from erp.journal_entries where id=p_source;
 select *into strict inverse from erp.journal_entries where source_type='JOURNAL_REVERSAL'
  and source_id=original.id and reversal_of_id=original.id;
 if p_owner='NOTE'then
  select exists(select 1 from cp7_note.journal_restatements x where x.source_journal_id=original.id
   and x.inverse_journal_id=inverse.id and x.native_economic_date=inverse.economic_date
   and x.corrected_economic_date=original.economic_date)into recorded;
 elsif p_owner='RETURN'then
  select exists(select 1 from cp7_sales_return_correction.journal_restatements x where x.source_journal_id=original.id
   and x.inverse_journal_id=inverse.id and x.native_economic_date=inverse.economic_date
   and x.corrected_economic_date=original.economic_date)into recorded;
 else raise exception 'OW04_MEMBER_RESTATEMENT_OWNER_INVALID';end if;
 if recorded is distinct from(original.economic_date<>inverse.economic_date)then
  raise exception 'OW04_MEMBER_REQUIRED_RESTATEMENT_MISSING_OR_UNEXPECTED';end if;
end $$;

create function ow04_source_proposal.verify_return_member_v1(p_return uuid)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare member jsonb;registration jsonb;parent jsonb;family_rows jsonb;members jsonb;fact jsonb;proof jsonb;
 expected jsonb;assignment jsonb;actual_assignment jsonb;item_lineage jsonb;member_kind text;predecessor uuid;lineage_id uuid;
 r erp.sales_returns;old erp.sales_returns;link cp7_sales_return_correction.links;revision cp7_note.revisions;
 previous_family uuid;family_id uuid;root uuid;ordinal bigint;seen uuid[];cursor uuid;cursor_row jsonb;n bigint;one record;
 source_family jsonb;causal_sales uuid[];sale_position bigint;causal_floor date;source_book date;
begin
 if to_regclass('cp7_credit.return_families')is null or to_regclass('cp7_credit.return_family_members')is null then
  raise exception 'OW04_MEMBER_REGISTRY_MISSING';end if;
 execute 'select to_jsonb(m)from cp7_credit.return_family_members m where m.return_id=$1'into member using p_return;
 if member is null then raise exception 'OW04_MEMBER_UNREGISTERED_RETURN';end if;
 family_id:=(member->>'family_id')::uuid;
 execute 'select to_jsonb(f)from cp7_credit.return_families f where f.id=$1'into registration using family_id;
 if registration is null then raise exception 'OW04_MEMBER_REGISTRATION_MISSING';end if;
 root:=(registration->>'family_root_sale_id')::uuid;ordinal:=(registration->>'family_ordinal')::bigint;
 execute 'select coalesce(jsonb_agg(to_jsonb(f)order by f.family_ordinal),''[]'')from cp7_credit.return_families f where f.family_root_sale_id=$1'into family_rows using root;
 execute 'select coalesce(jsonb_agg(to_jsonb(m)order by m.return_id),''[]'')from cp7_credit.return_family_members m where m.family_id=$1'into members using family_id;
 if registration->>'assignment_kind'is distinct from'NEW_POST'then
  raise exception 'OW04_MEMBER_HISTORICAL_ORDER_NOT_QUALIFIED';end if;
 -- This checks protected persisted assignment facts. Only the owning writer
 -- can attest NEW_POST under FG. It cannot retroactively manufacture order.
 n:=0;
 for one in select value from jsonb_array_elements(family_rows)loop
  n:=n+1;
  if(one.value->>'family_ordinal')::bigint<>n then raise exception 'OW04_MEMBER_ORDINAL_CHAIN_INVALID';end if;
 end loop;
 if ordinal<1 then raise exception 'OW04_MEMBER_ORDINAL_CHAIN_INVALID';end if;
 select(x->>'id')::uuid into previous_family from jsonb_array_elements(family_rows)x where(x->>'family_ordinal')::bigint=ordinal-1;
 assignment:=jsonb_build_object('contract_version','ow04.return-family-assignment.v1','family_id',family_id,
  'family_root_sale_id',root,'family_ordinal',ordinal::text,'first_return_id',registration->'first_return_id',
  'previous_family_id',previous_family,'actor',registration->'actor','request_id',registration->'request_id');
 actual_assignment:=registration->'assignment_proof';
 if actual_assignment is distinct from assignment or registration->>'source_sha256'is distinct from ow04_source_proposal.sha(assignment)then
  raise exception 'OW04_MEMBER_ASSIGNMENT_PROOF_CHANGED';end if;
 select *into strict r from erp.sales_returns where id=p_return;
 fact:=ow04_source_proposal.return_fact_v1(p_return);
 if(fact->>'family_root_sale_id')::uuid<>root then raise exception 'OW04_MEMBER_WRONG_ROOT';end if;
 proof:=member->'actual_lineage_snapshot';member_kind:=member->>'member_kind';
 predecessor:=(proof->>'predecessor_return_id')::uuid;lineage_id:=(proof->>'native_lineage_id')::uuid;
 item_lineage:=proof->'return_item_lineage';
 if member_kind='ORIGINAL'then
  if p_return is distinct from(registration->>'first_return_id')::uuid or predecessor is not null or lineage_id is not null
   or member->>'actor'is distinct from registration->>'actor'or member->>'request_id'is distinct from registration->>'request_id'
   or item_lineage is distinct from'{}'::jsonb then raise exception 'OW04_MEMBER_ORIGINAL_BINDING_INVALID';end if;
 elsif member_kind in('RETURN_CORRECTION','NOTE_REPLAY')then
  select value into parent from jsonb_array_elements(members)where(value->>'return_id')::uuid=predecessor;
  if parent is null or predecessor=p_return then raise exception 'OW04_MEMBER_PREDECESSOR_INVALID';end if;
  select *into strict old from erp.sales_returns where id=predecessor;
  if old.status<>'REVERSED'or old.customer_id<>r.customer_id then raise exception 'OW04_MEMBER_PREDECESSOR_STATE_INVALID';end if;
  if member_kind='RETURN_CORRECTION'then
   select *into strict link from cp7_sales_return_correction.links where id=lineage_id;
   if link.original_id<>predecessor or link.replacement_id<>p_return or link.sale_id<>r.sale_id or old.sale_id<>r.sale_id
    or member->>'actor'is distinct from link.actor::text or member->>'request_id'is distinct from link.request_id::text
    or item_lineage is distinct from'{}'::jsonb then raise exception 'OW04_MEMBER_RETURN_CORRECTION_BINDING_INVALID';end if;
   perform ow04_source_proposal.require_restatement_v1(j.id,'RETURN')from erp.journal_entries j
    where j.source_type='SALES_RETURN'and j.source_id=predecessor and j.reversal_of_id is null;
  else
   select *into strict revision from cp7_note.revisions where id=lineage_id;
   if revision.root_sale_id<>root or revision.previous_sale_id<>old.sale_id or revision.replacement_sale_id<>r.sale_id
    or member->>'actor'is distinct from revision.actor::text or member->>'request_id'is distinct from revision.request_id::text
    or r.physical_at<>old.physical_at or jsonb_typeof(item_lineage)is distinct from'object'
    or(select count(*)from jsonb_object_keys(item_lineage))<>(select count(*)from erp.sales_return_items where return_id=p_return)
    or(select count(*)from erp.sales_return_items where return_id=p_return)<>(select count(*)from erp.sales_return_items where return_id=predecessor)
    or(select count(distinct value)from jsonb_each_text(item_lineage))<>(select count(*)from jsonb_each_text(item_lineage))then
    raise exception 'OW04_MEMBER_NOTE_HEADER_OR_ITEMS_INVALID';end if;
   if exists(select 1 from jsonb_each_text(item_lineage)m left join erp.sales_return_items ni on ni.id=m.key::uuid and ni.return_id=p_return
    left join erp.sales_return_items oi on oi.id=m.value::uuid and oi.return_id=predecessor
    left join erp.sale_stock_allocations na on na.id=ni.sale_stock_allocation_id
    left join erp.sale_stock_allocations oa on oa.id=oi.sale_stock_allocation_id
    where ni.id is null or oi.id is null or(ni.product_id,ni.lot_id,ni.location_id,ni.quality_grade,ni.qty_pcs,ni.refund_amount)
      is distinct from(oi.product_id,oi.lot_id,oi.location_id,oi.quality_grade,oi.qty_pcs,oi.refund_amount)
     or not exists(select 1 from cp7_note.item_lineage il where il.correction_id=revision.id
      and il.previous_item_id=oa.sale_item_id and il.replacement_item_id=na.sale_item_id))then
    raise exception 'OW04_MEMBER_NOTE_ITEM_LINEAGE_INVALID';end if;
   perform ow04_source_proposal.require_restatement_v1(j.id,'NOTE')from erp.journal_entries j
    where j.source_type='SALES_RETURN'and j.source_id=predecessor and j.reversal_of_id is null;
  end if;
 else raise exception 'OW04_MEMBER_KIND_INVALID';end if;
 -- Every member follows one persisted, cycle-free chain to this family's
 -- original. The same old header cannot be claimed by two replay branches.
 if exists(select 1 from jsonb_array_elements(members)x where x->>'member_kind'<>'ORIGINAL'
  group by x->'actual_lineage_snapshot'->>'predecessor_return_id'having count(*)<>1)then
  raise exception 'OW04_MEMBER_RETURN_LINEAGE_FORK';end if;
 cursor:=p_return;seen:='{}';
 loop
  if cursor=any(seen)then raise exception 'OW04_MEMBER_RETURN_LINEAGE_CYCLE';end if;seen:=seen||cursor;
  select value into cursor_row from jsonb_array_elements(members)where(value->>'return_id')::uuid=cursor;
  if cursor_row is null then raise exception 'OW04_MEMBER_RETURN_LINEAGE_GAP';end if;
  if cursor_row->>'member_kind'='ORIGINAL'then
   if cursor is distinct from(registration->>'first_return_id')::uuid then raise exception 'OW04_MEMBER_MULTIPLE_ORIGINALS';end if;exit;
  end if;
  cursor:=(cursor_row->'actual_lineage_snapshot'->>'predecessor_return_id')::uuid;
  if cursor is null then raise exception 'OW04_MEMBER_RETURN_LINEAGE_GAP';end if;
 end loop;
 source_family:=ow04_source_proposal.family_read_v1(r.sale_id);
 select x.ordinal into strict sale_position from jsonb_array_elements_text(source_family->'sale_ids')with ordinality as x(value,ordinal)
  where value::uuid=r.sale_id;
 select array_agg(value::uuid order by position)into causal_sales from
  jsonb_array_elements_text(source_family->'sale_ids')with ordinality as x(value,position)where position<=sale_position;
 select max(j.transaction_date)into causal_floor from erp.journal_entries j where j.reversal_of_id is null
  and(j.source_type='SALE'and j.source_id=any(causal_sales)or j.source_type='SALES_RETURN'and j.source_id=any(seen));
 if fact->>'financial_state'='JOURNAL'then
  select transaction_date into strict source_book from erp.journal_entries where id=(fact->>'source_journal_id')::uuid;
  if causal_floor is null or source_book<causal_floor then raise exception 'OW04_MEMBER_RETURN_PRECEDES_CAUSAL_BOOK_FLOOR';end if;
 end if;
 expected:=jsonb_build_object('contract_version','ow04.actual-return-family-member.v1','family_id',family_id,
  'family_root_sale_id',root,'return_id',p_return,'sale_id',r.sale_id,'member_kind',member_kind,
  'predecessor_return_id',predecessor,'native_lineage_id',lineage_id,'return_item_lineage',item_lineage,
  'financial_state',fact->'financial_state','source_journal_id',fact->'source_journal_id',
  'financial_source_sha256',fact->'financial_source_sha256','no_journal_proof',fact->'no_journal_proof');
 if proof is distinct from expected or member->>'source_sha256'is distinct from ow04_source_proposal.sha(expected)
  or member->>'financial_state'is distinct from fact->>'financial_state'
  or member->'source_journal_id'is distinct from fact->'source_journal_id'
  or(member->>'financial_state'='NO_JOURNAL'and member->'financial_source_proof'is distinct from fact->'no_journal_proof')then
  raise exception using message='OW04_MEMBER_IMMUTABLE_SOURCE_BINDING_CHANGED',detail=jsonb_build_object(
   'snapshot_matches',proof is not distinct from expected,
   'snapshot_digest_matches',member->>'source_sha256'is not distinct from ow04_source_proposal.sha(expected),
   'financial_state_matches',member->>'financial_state'is not distinct from fact->>'financial_state',
   'journal_matches',member->'source_journal_id'is not distinct from fact->'source_journal_id',
   'no_journal_proof_matches',member->'financial_source_proof'is not distinct from fact->'no_journal_proof')::text;end if;
 return jsonb_build_object('contract_version','ow04.verified-return-member.v1','family_id',family_id,
  'family_root_sale_id',root,'family_ordinal',ordinal::text,'return_id',p_return,'sale_id',r.sale_id,
  'member_kind',member_kind,'predecessor_return_id',predecessor,'native_lineage_id',lineage_id,
  'financial_state',fact->'financial_state','source_journal_id',fact->'source_journal_id',
  'financial_source_sha256',fact->'financial_source_sha256','member_sha256',member->'source_sha256',
  'registration_sha256',registration->'source_sha256','causal_book_floor',causal_floor);
end $$;
revoke all on function ow04_source_proposal.family_read_v1(uuid),ow04_source_proposal.return_fact_v1(uuid),
 ow04_source_proposal.require_restatement_v1(uuid,text),ow04_source_proposal.verify_return_member_v1(uuid)
 from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write;
