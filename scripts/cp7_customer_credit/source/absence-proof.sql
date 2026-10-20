-- SOURCE-ONLY typed absence facts. No amount==0 shortcut or arbitrary date.
do $not_an_installer$begin
 raise exception 'OW04_ABSENCE_PROOF_REQUIRES_COMPLETE_OWNING_INTEGRATION';
end $not_an_installer$;
create function ow04_source_proposal.sale_absence_fact_v1(p_sale uuid)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare h erp.sales_headers;items jsonb;allocations jsonb;moves jsonb;proof jsonb;
begin
 select *into strict h from erp.sales_headers where id=p_sale;
 if h.status not in('POSTED','PARTIAL_PAID','PAID','REVERSED')then raise exception 'OW04_ABSENT_SALE_NOT_POSTED';end if;
 if exists(select 1 from erp.journal_entries where source_type='SALE'and source_id=h.id)then
  raise exception 'OW04_ABSENT_SALE_HAS_ACTUAL_JOURNAL';end if;
 if not exists(select 1 from erp.sales_items where sale_id=h.id)or exists(select 1 from erp.sales_items i where i.sale_id=h.id and
  (i.qty_pcs<=0 or i.line_total<>0 or i.unit_price_snapshot<0 or i.discount_amount<0
   or(select sum(a.qty_pcs)from erp.sale_stock_allocations a where a.sale_item_id=i.id)is distinct from i.qty_pcs::bigint
   or(select count(*)from erp.fg_stock_movements m where m.source_type='SALE_ITEM'and m.source_id=i.id
     and m.movement_type='SALE'and m.reversal_of_id is null)<>
    (select count(*)from erp.sale_stock_allocations a where a.sale_item_id=i.id)))then
  raise exception 'OW04_ABSENT_SALE_ITEMS_OR_QUANTITIES_INVALID';end if;
 if exists(select 1 from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=h.id
  and(a.qty_pcs<=0 or a.unit_hpp_snapshot<>0 or(select count(*)from erp.fg_stock_movements m
    where m.source_type='SALE_ITEM'and m.source_id=i.id and m.movement_type='SALE'and m.reversal_of_id is null
     and m.product_id=i.product_id and m.lot_id=a.lot_id and m.location_id=a.location_id and m.quality_grade='GRADE_A'
     and m.qty_signed=-a.qty_pcs and m.unit_hpp_snapshot=0 and m.customer_id=h.customer_id and m.physical_at=h.sale_date)<>1))then
  raise exception 'OW04_ABSENT_SALE_ALLOCATION_OR_PHYSICAL_PROOF_INVALID';end if;
 select jsonb_agg(to_jsonb(i)order by i.id)into items from erp.sales_items i where i.sale_id=h.id;
 select jsonb_agg(to_jsonb(a)order by a.id)into allocations from erp.sale_stock_allocations a
  join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=h.id;
 select jsonb_agg(to_jsonb(m)-'book_order'order by m.id)into moves from erp.fg_stock_movements m
  where m.source_type='SALE_ITEM'and m.movement_type='SALE'and m.reversal_of_id is null
   and exists(select 1 from erp.sales_items i where i.sale_id=h.id and i.id=m.source_id);
 if exists(select 1 from jsonb_array_elements(moves)x where
  (h.status<>'REVERSED'and exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=(x->>'id')::uuid))
  or(h.status='REVERSED'and((select count(*)from erp.fg_stock_movements rv where rv.reversal_of_id=(x->>'id')::uuid)<>1
   or not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=(x->>'id')::uuid
    and rv.source_type='FG_MOVEMENT_REVERSAL'and rv.source_id=(x->>'id')::uuid and rv.movement_type='REVERSAL'
    and rv.product_id=(x->>'product_id')::uuid and rv.lot_id is not distinct from(x->>'lot_id')::uuid
    and rv.location_id=(x->>'location_id')::uuid and rv.quality_grade=x->>'quality_grade'
    and rv.qty_signed=-(x->>'qty_signed')::integer and rv.unit_hpp_snapshot=0
    and rv.customer_id is not distinct from(x->>'customer_id')::uuid and rv.physical_at>=(x->>'physical_at')::timestamptz))))then
  raise exception 'OW04_ABSENT_SALE_STOCK_REVERSAL_INVALID';end if;
 proof:=jsonb_build_object('contract_version','ow04.native-no-sale-journal-proof.v1','sale_id',h.id,
  'document',to_jsonb(h)-array['status','row_version','updated_at'],'items',items,'actual_allocations',allocations,
  'actual_original_fg_movements',moves,'financial_event','ABSENT');
 return proof;
end $$;

-- Call only after the owning source lock pass; this function takes NO locks.
-- PRESENT retains the scalar's actual causal-date proof. ABSENT is proven
-- against the complete real note family: every posted SALE/RETURN has its
-- typed absence proof, no payment history, no actual base journal anywhere.
-- Unknown registration or an HPP-only journal can never become ABSENT.
create function ow04_source_proposal.causal_book_info_v1(p_return uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare r erp.sales_returns;family jsonb;floor date;proofs jsonb:='[]';proof jsonb;doc record;ids uuid[];manifest jsonb;
 related uuid[];registered uuid[];
begin
 select *into strict r from erp.sales_returns where id=p_return;
 if r.status not in('POSTED','REVERSED')then raise exception 'OW04_CAUSAL_INFO_RETURN_NOT_COMPLETED';end if;
 family:=ow04_source_proposal.family_read_v1(r.sale_id);
 select array_agg(value::uuid)into ids from jsonb_array_elements_text(family->'sale_ids');
 begin
  floor:=ow04_source_proposal.return_causal_book_floor(p_return);
  with recursive connected(id)as(select p_return union select case when l.original_id=c.id then l.replacement_id else l.original_id end
   from connected c join cp7_sales_return_correction.links l on c.id in(l.original_id,l.replacement_id))
   select array_agg(id order by id)into related from connected;
  if to_regclass('cp7_credit.return_family_members')is not null then
   execute 'select array_agg(return_id order by return_id)from cp7_credit.return_family_members where family_id=(select family_id from cp7_credit.return_family_members where return_id=$1)'into registered using p_return;
   related:=coalesce(registered,related);
  end if;
  manifest:=jsonb_build_object('family',family,'causal_return_ids',related,'causal_journals',
   (select jsonb_agg(jsonb_build_object('id',j.id,'source_type',j.source_type,'source_id',j.source_id,
    'economic_date',j.economic_date,'transaction_date',j.transaction_date)order by j.id)from erp.journal_entries j
    where j.reversal_of_id is null and(j.source_type='SALE'and j.source_id=any(ids)
     or j.source_type='SALES_RETURN'and j.source_id=any(related))));
  return jsonb_build_object('contract_version','ow04.actual-causal-book-info.v1','state','DATED',
   'causal_book_floor',floor,'return_id',p_return,'proof_manifest',manifest,'proof_sha256',ow04_source_proposal.sha(manifest));
 exception when raise_exception then
  if sqlerrm<>'OW04_SOURCE_NO_DATED_CAUSAL_JOURNAL'then raise;end if;
 end;
 if exists(select 1 from erp.sales_payments where sale_id=any(ids)and status<>'DRAFT')or
  exists(select 1 from erp.journal_entries j where
   j.source_type='SALE'and j.source_id=any(ids)
   or j.source_type='SALES_RETURN'and exists(select 1 from erp.sales_returns sr where sr.id=j.source_id and sr.sale_id=any(ids))
   or j.source_type='SALES_PAYMENT'and exists(select 1 from erp.sales_payments sp where sp.id=j.source_id and sp.sale_id=any(ids)))then
  raise exception 'OW04_ABSENT_FAMILY_HAS_FINANCIAL_HISTORY';end if;
 for doc in select id from erp.sales_headers where id=any(ids)and status<>'DRAFT'order by id loop
  proof:=ow04_source_proposal.sale_absence_fact_v1(doc.id);proofs:=proofs||jsonb_build_array(proof);
 end loop;
 for doc in select id from erp.sales_returns where sale_id=any(ids)and status<>'DRAFT'order by id loop
  proof:=ow04_source_proposal.verify_return_member_v1(doc.id);
  if proof->>'financial_state'<>'NO_JOURNAL'then raise exception 'OW04_ABSENT_FAMILY_HAS_FINANCIAL_HISTORY';end if;
  proofs:=proofs||jsonb_build_array(jsonb_build_object('member',proof,'actual',ow04_source_proposal.return_fact_v1(doc.id)));
 end loop;
 manifest:=jsonb_build_object('family',family,'source_proofs',proofs);
 return jsonb_build_object('contract_version','ow04.actual-causal-book-info.v1','state','PROVEN_ABSENT',
  'causal_book_floor',null,'return_id',p_return,'proof_manifest',manifest,
  'proof_sha256',ow04_source_proposal.sha(manifest));
end $$;
revoke all on function ow04_source_proposal.sale_absence_fact_v1(uuid),ow04_source_proposal.causal_book_info_v1(uuid)
 from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write;
