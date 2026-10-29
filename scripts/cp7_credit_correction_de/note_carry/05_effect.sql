create function cp7_credit_note_carry_de.assert_effect_v1(p_before jsonb,p_after jsonb,p_original uuid,p_replacement uuid,p_new_net numeric)returns jsonb
language plpgsql stable security definer set search_path=''set timezone='UTC'as $$
declare k text;row_value jsonb;next_value jsonb;item record;old_alloc jsonb;new_alloc jsonb;old_j erp.journal_entries;
 inverse erp.journal_entries;new_j erp.journal_entries;statement_row cp7_note.journal_restatements;old_ar jsonb;new_ar jsonb;
 old_lines jsonb;new_lines jsonb;old_sales uuid;revenue uuid;ar uuid;before_moves jsonb;added_moves jsonb;old_move jsonb;back jsonb;fresh jsonb;
begin
 old_ar:=cp7_credit.consumer_invoice_ar_source_v1(p_original);new_ar:=cp7_credit.consumer_invoice_ar_source_v1(p_replacement);
 if(old_ar->>'customer_id',old_ar->>'account_id')is distinct from(new_ar->>'customer_id',new_ar->>'account_id')
  or(new_ar->>'gross_amount')::numeric is distinct from p_new_net then raise exception 'CP7_CREDIT_NOTE_CARRY_ACTUAL_AR_SOURCE_CHANGED';end if;
 ar:=(old_ar->>'account_id')::uuid;revenue:=cp7_credit.account_by_mapping_v1('SALES_REVENUE');
 select *into strict old_j from erp.journal_entries where id=(old_ar->>'sale_journal_id')::uuid;
 select *into strict new_j from erp.journal_entries where id=(new_ar->>'sale_journal_id')::uuid;
 select *into strict inverse from erp.journal_entries where source_type='JOURNAL_REVERSAL'and source_id=old_j.id and reversal_of_id=old_j.id;
 if old_j.status<>'REVERSED'or inverse.status<>'POSTED'or new_j.status<>'POSTED'
  or(new_j.economic_date,new_j.transaction_date)is distinct from(old_j.economic_date,old_j.transaction_date)
  or inverse.economic_date<old_j.economic_date or inverse.transaction_date<old_j.transaction_date
  or cp7_credit.source_inverse_vector_v1(cp7_credit.materialized_journal_payload(inverse.id)->'lines')is distinct from
   cp7_credit.source_inverse_vector_v1(cp7_credit.materialized_journal_payload(old_j.id)->'lines',true)then raise exception 'CP7_CREDIT_NOTE_CARRY_NATIVE_INVERSE_CHANGED';end if;
 select *into statement_row from cp7_note.journal_restatements where source_journal_id=old_j.id;
 if inverse.economic_date<>old_j.economic_date then
  if(statement_row.inverse_journal_id,statement_row.previous_sale_id,statement_row.native_economic_date,statement_row.corrected_economic_date)is distinct from
   (inverse.id,p_original,inverse.economic_date,old_j.economic_date)
   or not exists(select 1 from erp.journal_entries n join erp.journal_entries e on e.id=statement_row.effective_journal_id
    where n.id=statement_row.neutral_journal_id and(n.source_type,n.source_id,n.economic_date,n.transaction_date,n.status)is not distinct from
     ('NOTE_REVERSAL_TIME_NEUTRAL',inverse.id,inverse.economic_date,inverse.transaction_date,'POSTED')
     and(e.source_type,e.source_id,e.economic_date,e.transaction_date,e.status)is not distinct from('NOTE_REVERSAL_EFFECTIVE',inverse.id,old_j.economic_date,old_j.transaction_date,'POSTED'))
   or cp7_credit.source_inverse_vector_v1(cp7_credit.materialized_journal_payload(statement_row.neutral_journal_id)->'lines')is distinct from
    cp7_credit.source_inverse_vector_v1(cp7_credit.materialized_journal_payload(inverse.id)->'lines',true)
   or cp7_credit.source_inverse_vector_v1(cp7_credit.materialized_journal_payload(statement_row.effective_journal_id)->'lines')is distinct from
    cp7_credit.source_inverse_vector_v1(cp7_credit.materialized_journal_payload(inverse.id)->'lines')then raise exception 'CP7_CREDIT_NOTE_CARRY_RESTATEMENT_CHANGED';end if;
 elsif statement_row.inverse_journal_id is not null then raise exception 'CP7_CREDIT_NOTE_CARRY_UNEXPECTED_RESTATEMENT';end if;
 -- Native still creates every line. Prove the price-only delta and preserve
 -- each cost dimension/sign; no aggregate can hide a changed HPP mapping.
 select coalesce(jsonb_agg(v),'[]')into old_lines from jsonb_array_elements(cp7_credit.materialized_journal_payload(old_j.id)->'lines')v where(v->>'account_id')::uuid not in(ar,revenue);
 select coalesce(jsonb_agg(v),'[]')into new_lines from jsonb_array_elements(cp7_credit.materialized_journal_payload(new_j.id)->'lines')v where(v->>'account_id')::uuid not in(ar,revenue);
 if cp7_credit.source_inverse_vector_v1(old_lines)is distinct from cp7_credit.source_inverse_vector_v1(new_lines)
  or not exists(select 1 from erp.journal_lines where journal_entry_id=new_j.id and account_id=revenue and credit=p_new_net and debit=0
    and customer_id=(new_ar->>'customer_id')::uuid and vendor_id is null and contractor_id is null and product_id is null and po_id is null)
  or(select count(*)from erp.journal_lines where journal_entry_id=new_j.id and account_id=revenue)<>1 then raise exception 'CP7_CREDIT_NOTE_CARRY_PRICE_HPP_VECTOR_CHANGED';end if;
 foreach k in array array['fg_lots','hpp_versions','opening_hpp_states','opening_hpp_corrections','po_hpp_states','nonpo_hpp_events','po_hpp_events','hpp_balances','hpp_accounts','period_snapshot']loop
  if p_before->k is distinct from p_after->k then raise exception 'CP7_CREDIT_NOTE_CARRY_UNQUALIFIED_NATIVE_DELTA:%',k;end if;
 end loop;
 if exists(select 1 from erp.sales_payments where sale_id in(p_original,p_replacement))or exists(select 1 from erp.sales_returns where sale_id in(p_original,p_replacement))then
  raise exception 'CP7_CREDIT_NOTE_CARRY_CHILD_REPLAY_ADAPTER_REQUIRED';end if;
 for item in select l.previous_item_id,l.replacement_item_id from cp7_note.item_lineage l where l.correction_id=(select id from cp7_note.revisions where previous_sale_id=p_original and replacement_sale_id=p_replacement)loop
  select cp7_credit.source_rows_v1(coalesce(jsonb_agg(to_jsonb(a)-array['id','sale_item_id']),'[]'))into old_alloc from erp.sale_stock_allocations a where sale_item_id=item.previous_item_id;
  select cp7_credit.source_rows_v1(coalesce(jsonb_agg(to_jsonb(a)-array['id','sale_item_id']),'[]'))into new_alloc from erp.sale_stock_allocations a where sale_item_id=item.replacement_item_id;
  if old_alloc is distinct from new_alloc then raise exception 'CP7_CREDIT_NOTE_CARRY_ALLOCATION_HPP_CHANGED';end if;
 end loop;
 before_moves:=p_before->'stock_movements';
 for row_value in select value from jsonb_array_elements(before_moves)loop
  if not exists(select 1 from jsonb_array_elements(p_after->'stock_movements')v where v=row_value)then raise exception 'CP7_CREDIT_NOTE_CARRY_ORIGINAL_MOVEMENT_CHANGED';end if;
 end loop;
 select coalesce(jsonb_agg(v),'[]')into added_moves from jsonb_array_elements(p_after->'stock_movements')v where not exists(select 1 from jsonb_array_elements(before_moves)o where o->>'id'=v->>'id');
 for old_move in select value from jsonb_array_elements(before_moves)where value->>'source_type'='SALE_ITEM'and value->>'movement_type'='SALE'
  and exists(select 1 from erp.sales_items i where i.id=(value->>'source_id')::uuid and i.sale_id=p_original)loop
  select v into strict back from jsonb_array_elements(added_moves)v where v->>'reversal_of_id'=old_move->>'id';
  select v into strict fresh from jsonb_array_elements(added_moves)v where v->>'source_type'='SALE_ITEM'and v->>'movement_type'='SALE'and v->>'reversal_of_id'is null
   and v->>'source_id'=(select l.replacement_item_id::text from cp7_note.item_lineage l where l.previous_item_id=(old_move->>'source_id')::uuid)
   and v->>'lot_id'is not distinct from old_move->>'lot_id'and v->>'location_id'=old_move->>'location_id';
  if(back->>'product_id',back->>'lot_id',back->>'location_id',back->>'quality_grade',(back->>'qty_signed')::numeric,(back->>'unit_hpp_snapshot')::numeric,(back->>'physical_at')::timestamptz) is distinct from
   (old_move->>'product_id',old_move->>'lot_id',old_move->>'location_id',old_move->>'quality_grade',-(old_move->>'qty_signed')::numeric,(old_move->>'unit_hpp_snapshot')::numeric,(old_move->>'physical_at')::timestamptz)
   or(fresh->>'product_id',fresh->>'lot_id',fresh->>'location_id',fresh->>'quality_grade',(fresh->>'qty_signed')::numeric,(fresh->>'unit_hpp_snapshot')::numeric,(fresh->>'physical_at')::timestamptz) is distinct from
   (old_move->>'product_id',old_move->>'lot_id',old_move->>'location_id',old_move->>'quality_grade',(old_move->>'qty_signed')::numeric,(old_move->>'unit_hpp_snapshot')::numeric,(old_move->>'physical_at')::timestamptz)then
   raise exception 'CP7_CREDIT_NOTE_CARRY_PHYSICAL_BIJECTION_CHANGED';end if;
 end loop;
 if jsonb_array_length(added_moves)<>2*(select count(*)from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=p_original)then
  raise exception 'CP7_CREDIT_NOTE_CARRY_EXTRA_STOCK_EFFECT';end if;
 for row_value in select value from jsonb_array_elements(p_before->'inventory_balances')loop
  select v into strict next_value from jsonb_array_elements(p_after->'inventory_balances')v where(v->>'product_id',v->>'location_id',v->>'quality_grade')=
   (row_value->>'product_id',row_value->>'location_id',row_value->>'quality_grade');
  if row_value-'updated_at'is distinct from next_value-'updated_at'then raise exception 'CP7_CREDIT_NOTE_CARRY_INVENTORY_FINAL_DELTA';end if;
 end loop;
 if jsonb_array_length(p_before->'inventory_balances')<>jsonb_array_length(p_after->'inventory_balances')then raise exception 'CP7_CREDIT_NOTE_CARRY_INVENTORY_SET_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.note-credit-carry-actual-effect.v1','original_document',cp7_credit_note_carry_de.raw_document_v1(p_original),
  'replacement_document',cp7_credit_note_carry_de.raw_document_v1(p_replacement),'original_journal',cp7_credit.materialized_journal_payload(old_j.id),
  'inverse_journal',cp7_credit.materialized_journal_payload(inverse.id),'replacement_journal',cp7_credit.materialized_journal_payload(new_j.id),
  'restatement',to_jsonb(statement_row),'no_consumer_money_created',true,'same_physical_and_HPP',true);
end $$;
