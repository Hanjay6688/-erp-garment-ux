create function cp7_credit_correction_de.proof_v1(p_operation uuid)returns jsonb
language sql stable security definer set search_path=''as $$
 select coalesce((select proof from cp7_credit_correction_de.operations_v1 where operation_id=p_operation),
  (select to_jsonb(w)from cp7_credit_correction_de.work_v1 w where operation_id=p_operation and phase='MATERIALIZED'))
$$;
create function cp7_credit_correction_de.marker_owned_v1(p_marker uuid)returns boolean
language sql stable security definer set search_path=''as $$
 select exists(select 1 from cp7_credit_correction_de.operations_v1 o where o.operation_id=p_marker)
 or exists(select 1 from cp7_credit_correction_de.work_v1 where operation_id=p_marker and phase='MATERIALIZED')
$$;
create function cp7_credit_correction_de.assert_owned_links_v1(p_sale uuid)returns void
language plpgsql stable security definer set search_path=''as $$
declare l cp7_sales_return_correction.links;s cp7_sales_return_correction.journal_restatements;
 j erp.journal_entries;inverse erp.journal_entries;neutral erp.journal_entries;effective erp.journal_entries;begin
 for l in select *from cp7_sales_return_correction.links where sale_id=p_sale loop
  if not exists(select 1 from cp7_credit_correction_de.operations_v1 o where
   (o.sale_id,o.return_id,o.replacement_id,o.actor,o.request_id)=(l.sale_id,l.original_id,l.replacement_id,l.actor,l.request_id))
   and not exists(select 1 from cp7_credit_correction_de.work_v1 w where(w.sale_id,w.return_id,w.replacement_id,w.actor,w.request_id)=
    (l.sale_id,l.original_id,l.replacement_id,l.actor,l.request_id)and w.phase in('POSTED','RECONCILING','MATERIALIZED'))then
   raise exception 'CP7_CREDIT_DE_UNOWNED_CORRECTION_LINK';end if;
  select *into strict j from erp.journal_entries where source_type='SALES_RETURN'and source_id=l.original_id and reversal_of_id is null;
  select *into strict inverse from erp.journal_entries where source_type='JOURNAL_REVERSAL'and source_id=j.id and reversal_of_id=j.id;
  if j.status<>'REVERSED'or inverse.status<>'POSTED'or inverse.economic_date<j.economic_date or inverse.transaction_date<j.transaction_date
   or cp7_credit.source_inverse_vector_v1(cp7_credit.materialized_journal_payload(inverse.id)->'lines')is distinct from
    cp7_credit.source_inverse_vector_v1(cp7_credit.materialized_journal_payload(j.id)->'lines',true)then
   raise exception 'CP7_CREDIT_DE_ACTUAL_INVERSE_CHANGED';end if;
  select *into s from cp7_sales_return_correction.journal_restatements where source_journal_id=j.id;
  if inverse.economic_date=j.economic_date then
   if s.source_journal_id is not null then raise exception 'CP7_CREDIT_DE_UNEXPECTED_RESTATEMENT';end if;
  else
   if s.source_journal_id is null then raise exception 'CP7_CREDIT_DE_RESTATEMENT_REQUIRED';end if;
   select *into strict neutral from erp.journal_entries where id=s.neutral_journal_id;
   select *into strict effective from erp.journal_entries where id=s.effective_journal_id;
   if(s.original_return_id,s.inverse_journal_id,s.native_economic_date,s.corrected_economic_date)is distinct from
    (l.original_id,inverse.id,inverse.economic_date,j.economic_date)
    or(neutral.source_type,neutral.source_id,neutral.reversal_of_id,neutral.economic_date,neutral.transaction_date,neutral.status)is distinct from
     ('RETURN_CORRECTION_TIME_NEUTRAL',inverse.id,null::uuid,inverse.economic_date,neutral.transaction_date,'POSTED')
    or(effective.source_type,effective.source_id,effective.reversal_of_id,effective.economic_date,effective.transaction_date,effective.status)is distinct from
     ('RETURN_CORRECTION_EFFECTIVE',inverse.id,null::uuid,j.economic_date,j.transaction_date,'POSTED')
    or neutral.transaction_date<inverse.transaction_date or effective.transaction_date<j.transaction_date
    or cp7_credit.source_inverse_vector_v1(cp7_credit.materialized_journal_payload(neutral.id)->'lines')is distinct from
     cp7_credit.source_inverse_vector_v1(cp7_credit.materialized_journal_payload(inverse.id)->'lines',true)
    or cp7_credit.source_inverse_vector_v1(cp7_credit.materialized_journal_payload(effective.id)->'lines')is distinct from
     cp7_credit.source_inverse_vector_v1(cp7_credit.materialized_journal_payload(inverse.id)->'lines')then
    raise exception 'CP7_CREDIT_DE_ACTUAL_RESTATEMENT_CHANGED';end if;
  end if;
 end loop;
end $$;

create function cp7_credit_correction_de.extra_events_v1(p_sale uuid,p_exclude uuid)returns jsonb
language sql stable security definer set search_path=''as $$
 select coalesce(jsonb_agg(jsonb_build_object('id','journal:'||j.id::text,'kind','NET',
  'amount',cp7_credit.cent_text(coalesce((select sum(l.debit-l.credit)from erp.journal_lines l where l.journal_entry_id=j.id
   and l.account_id=cp7_credit.account_by_mapping_v1('AR_CUSTOMER')),0)),
  'economic_date',j.economic_date::text,'transaction_date',j.transaction_date::text,
  'source_sha256',ow04_source_proposal.sha(ow04_source_proposal.financial_journal_payload(j.id,cp7_credit.account_by_mapping_v1('AR_CUSTOMER'))))order by j.id),'[]')
 from cp7_sales_return_correction.journal_restatements s join erp.sales_returns r on r.id=s.original_return_id
 join cp7_sales_return_correction.links l on l.original_id=r.id
 join erp.journal_entries j on j.id in(s.neutral_journal_id,s.effective_journal_id)
 where r.sale_id=p_sale and r.id is distinct from p_exclude and j.status='POSTED'and(
  exists(select 1 from cp7_credit_correction_de.operations_v1 o where o.return_id=r.id and o.replacement_id=l.replacement_id)
  or exists(select 1 from cp7_credit_correction_de.work_v1 w where w.return_id=r.id and w.replacement_id=l.replacement_id and w.phase in('POSTED','RECONCILING','MATERIALIZED')))
$$;

create function cp7_credit_correction_de.assert_source_change_v1(p_before jsonb,p_actual jsonb,p_return uuid,p_replacement uuid)returns void
language plpgsql stable security definer set search_path=''set timezone='UTC'as $$
declare key text;x jsonb;y jsonb;old_j uuid;new_j uuid;inverse uuid;allowed uuid[];item jsonb;fresh jsonb;m jsonb;back jsonb;replacement_move jsonb;begin
 if (p_before->'sale')-array['status','row_version','updated_at']is distinct from (p_actual->'sale')-array['status','row_version','updated_at']then
  raise exception 'CP7_CREDIT_DE_NATIVE_HEADER_IDENTITY_CHANGED';end if;
 foreach key in array array['items','allocations','payments','payment_posting_facts','payment_reversal_facts','advance_links',
  'fg_lots','hpp_versions','opening_hpp_states','opening_hpp_corrections','po_hpp_states','po_hpp_events','nonpo_hpp_events','hpp_balances','hpp_accounts','period_snapshot']loop
  if p_before->key is distinct from p_actual->key then raise exception 'CP7_CREDIT_DE_UNQUALIFIED_NATIVE_DELTA:%',key;end if;
 end loop;
 for x in select value from jsonb_array_elements(p_before->'inventory_balances')loop
  select v into strict y from jsonb_array_elements(p_actual->'inventory_balances')v where(v->>'product_id',v->>'location_id',v->>'quality_grade')=
   (x->>'product_id',x->>'location_id',x->>'quality_grade');
  if x-'updated_at'is distinct from y-'updated_at'then raise exception 'CP7_CREDIT_DE_INVENTORY_FINAL_DELTA';end if;
 end loop;
 if jsonb_array_length(p_before->'inventory_balances')<>jsonb_array_length(p_actual->'inventory_balances')then raise exception 'CP7_CREDIT_DE_INVENTORY_SET_CHANGED';end if;
 for x in select value from jsonb_array_elements(p_before->'returns')loop
  select v into strict y from jsonb_array_elements(p_actual->'returns')v where v->>'id'=x->>'id';
  if (case when x->>'id'=p_return::text then x||'{"status":"REVERSED"}'::jsonb else x end)is distinct from y then
   raise exception 'CP7_CREDIT_DE_ORIGINAL_RETURN_CHANGED';end if;
 end loop;
 if jsonb_array_length(p_actual->'returns')<>jsonb_array_length(p_before->'returns')+1 then raise exception 'CP7_CREDIT_DE_REPLACEMENT_SET_CHANGED';end if;
 if jsonb_array_length(p_actual->'return_items')<>jsonb_array_length(p_before->'return_items')+(select count(*)from jsonb_array_elements(p_before->'return_items')v where v->>'return_id'=p_return::text)then raise exception 'CP7_CREDIT_DE_EXTRA_RETURN_ITEM';end if;
 for x in select value from jsonb_array_elements(p_before->'return_items')loop
  if not exists(select 1 from jsonb_array_elements(p_actual->'return_items')v where v=x)then raise exception 'CP7_CREDIT_DE_ORIGINAL_ITEM_CHANGED';end if;
 end loop;
 for item in select value from jsonb_array_elements(p_before->'return_items')where value->>'return_id'=p_return::text loop
  select v into strict fresh from jsonb_array_elements(p_actual->'return_items')v where v->>'return_id'=p_replacement::text and v->>'sale_stock_allocation_id'=item->>'sale_stock_allocation_id';
  if item-array['id','return_id','refund_amount','notes']is distinct from fresh-array['id','return_id','refund_amount','notes']then
   raise exception 'CP7_CREDIT_DE_REPLACEMENT_PHYSICAL_ITEM_CHANGED';end if;
  select v into strict m from jsonb_array_elements(p_before->'stock_movements')v where v->>'source_type'='SALES_RETURN_ITEM'and v->>'source_id'=item->>'id'and v->>'reversal_of_id'is null;
  select v into strict back from jsonb_array_elements(p_actual->'stock_movements')v where v->>'reversal_of_id'=m->>'id';
  select v into strict replacement_move from jsonb_array_elements(p_actual->'stock_movements')v where v->>'source_type'='SALES_RETURN_ITEM'and v->>'source_id'=fresh->>'id'and v->>'reversal_of_id'is null;
  if(back->>'product_id',back->>'lot_id',back->>'location_id',back->>'quality_grade',back->>'customer_id',(back->>'qty_signed')::numeric,
    (back->>'unit_hpp_snapshot')::numeric,(back->>'physical_at')::timestamptz,back->>'source_type',back->>'source_id',back->>'movement_type')is distinct from
   (m->>'product_id',m->>'lot_id',m->>'location_id',m->>'quality_grade',m->>'customer_id',-(m->>'qty_signed')::numeric,
    (m->>'unit_hpp_snapshot')::numeric,(m->>'physical_at')::timestamptz,'FG_MOVEMENT_REVERSAL',m->>'id','REVERSAL')
   or(replacement_move->>'product_id',replacement_move->>'lot_id',replacement_move->>'location_id',replacement_move->>'quality_grade',replacement_move->>'customer_id',
    (replacement_move->>'qty_signed')::numeric,(replacement_move->>'unit_hpp_snapshot')::numeric,(replacement_move->>'physical_at')::timestamptz,replacement_move->>'movement_type')is distinct from
   (m->>'product_id',m->>'lot_id',m->>'location_id',m->>'quality_grade',m->>'customer_id',(m->>'qty_signed')::numeric,
    (m->>'unit_hpp_snapshot')::numeric,(m->>'physical_at')::timestamptz,'SALE_RETURN')then raise exception 'CP7_CREDIT_DE_STOCK_BIJECTION_CHANGED';end if;
 end loop;
 for x in select value from jsonb_array_elements(p_before->'stock_movements')loop
  if not exists(select 1 from jsonb_array_elements(p_actual->'stock_movements')v where v=x)then raise exception 'CP7_CREDIT_DE_ORIGINAL_MOVEMENT_CHANGED';end if;
 end loop;
 if jsonb_array_length(p_actual->'stock_movements')<>jsonb_array_length(p_before->'stock_movements')+2*(select count(*)from jsonb_array_elements(p_before->'return_items')v where v->>'return_id'=p_return::text)then
  raise exception 'CP7_CREDIT_DE_EXTRA_STOCK_EFFECT';end if;
 select id into strict old_j from erp.journal_entries where source_type='SALES_RETURN'and source_id=p_return and reversal_of_id is null;
 select id into strict new_j from erp.journal_entries where source_type='SALES_RETURN'and source_id=p_replacement and reversal_of_id is null;
 select id into strict inverse from erp.journal_entries where source_type='JOURNAL_REVERSAL'and source_id=old_j and reversal_of_id=old_j;
 allowed:=array[new_j,inverse]||(select array_agg(id)from erp.journal_entries where id in(select neutral_journal_id from cp7_sales_return_correction.journal_restatements where source_journal_id=old_j
  union select effective_journal_id from cp7_sales_return_correction.journal_restatements where source_journal_id=old_j));
 if allowed is null then allowed:=array[new_j,inverse];end if;
 foreach key in array array['journals','hpp_journals']loop
  for x in select value from jsonb_array_elements(p_before->key)loop
   select v into strict y from jsonb_array_elements(p_actual->key)v where v->>'id'=x->>'id';
   if x->'immutable_payload'is distinct from y->'immutable_payload'or y->>'status'is distinct from(case when x->>'id'=old_j::text then'REVERSED'else x->>'status'end)then
    raise exception 'CP7_CREDIT_DE_ORIGINAL_JOURNAL_CHANGED';end if;
  end loop;
  if exists(select 1 from jsonb_array_elements(p_actual->key)v where not exists(select 1 from jsonb_array_elements(p_before->key)b where b->>'id'=v->>'id')and not((v->>'id')::uuid=any(allowed)))then
   raise exception 'CP7_CREDIT_DE_EXTRA_JOURNAL_EFFECT';end if;
 end loop;
 perform cp7_credit_correction_de.assert_owned_links_v1((p_before#>>'{sale,id}')::uuid);
end $$;

create function cp7_credit_correction_de.assert_marker_v1(p_marker uuid)returns void
language plpgsql stable security definer set search_path=''as $$
declare proof jsonb:=cp7_credit_correction_de.proof_v1(p_marker);f cp7_credit.financial_materializations;begin
 select *into strict f from cp7_credit.financial_materializations where id=p_marker;
 if proof is null or(f.root_sale_id,f.actor,f.request_id,f.request_ordinal,f.owning_action,f.payload_sha256,f.source_plan_sha256,f.actual_objects)is distinct from
  ((proof->>'sale_id')::uuid,(proof->>'actor')::uuid,(proof->>'request_id')::uuid,1,'RETURN_CORRECT',
   cp7_credit.pg_jsonb_sha256(proof->'payload'),proof#>>'{review,review_token}',proof->'actual_objects')
  or f.actual_objects_sha256 is distinct from cp7_credit.pg_jsonb_sha256(f.actual_objects)then raise exception 'CP7_CREDIT_DE_MARKER_PROVENANCE_CHANGED';end if;
end $$;

create function cp7_credit_correction_de.assert_profile_v1(p_sale uuid,p_root uuid,p_leaf uuid,p_actual jsonb)returns void
language plpgsql stable security definer set search_path=''set timezone='UTC'as $$
declare proof jsonb;op uuid;current_source jsonb;result jsonb;item jsonb;begin
 if p_sale<>p_root or p_root<>p_leaf or(p_actual->>'sale_id',p_actual->>'root_sale_id',p_actual->>'current_leaf_id')is distinct from
  (p_sale::text,p_root::text,p_leaf::text)then raise exception 'CP7_CREDIT_DE_CURRENT_ROOT_ASSIGNMENT_CHANGED';end if;
 select operation_id into op from cp7_credit_correction_de.work_v1 where sale_id=p_sale and phase='MATERIALIZED';
 if op is null then select operation_id into strict op from cp7_credit_correction_de.operations_v1 where sale_id=p_sale order by operation_ordinal desc limit 1;end if;
 proof:=cp7_credit_correction_de.proof_v1(op);current_source:=cp7_credit.source_document_snapshot_v1(p_sale);
 if current_source-'sale'is distinct from(proof->'actual_source')-array['sale','fg_lots','hpp_versions','stock_movements','inventory_balances','opening_hpp_states',
  'opening_hpp_corrections','po_hpp_states','nonpo_hpp_events','po_hpp_events','hpp_journals','hpp_balances','hpp_accounts','period_snapshot','hpp_support']
  or (current_source->'sale')-array['status','row_version','updated_at']is distinct from (proof#>'{actual_source,sale}')-array['status','row_version','updated_at']then
  raise exception 'CP7_CREDIT_DE_CURRENT_NATIVE_SOURCE_CHANGED';end if;
 perform cp7_credit_correction_de.assert_native_base_v1(p_sale);
 result:=ow04_ordinal_wrapper.reconcile_v1(cp7_credit.initial_ordinal_input_v1(p_sale));
 if result->'arithmetic_supported'is distinct from'true'::jsonb or exists(select 1 from jsonb_array_elements(result->'families')v where(v->>'has_reconciliation_effect')::boolean)then
  raise exception 'CP7_CREDIT_DE_CURRENT_PREFIX_RECONCILIATION_REQUIRED';end if;
 for item in select value from jsonb_array_elements(proof#>'{before_profile,actual_objects}')loop
  if not exists(select 1 from jsonb_array_elements(p_actual->'actual_objects')v where v=item)then raise exception 'CP7_CREDIT_DE_RETAINED_ACTUAL_OBJECT_CHANGED';end if;
 end loop;
 perform cp7_credit_correction_de.assert_marker_v1(op);
 perform cp7_credit.assert_source_final_ar_status_v1(p_sale,current_source,p_actual);
end $$;
