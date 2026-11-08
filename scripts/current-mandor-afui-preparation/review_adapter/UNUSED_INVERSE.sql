lock table cp7_note_zero_effect.preparations, cp7_note_zero_effect.receipts in access exclusive mode;
do $guard$ begin
 if exists (select 1 from cp7_note_zero_effect.preparations) or exists (select 1 from cp7_note_zero_effect.receipts) then raise exception 'MANDOR_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE'; end if;
 if md5(pg_get_functiondef('cp7_credit.assert_current_source_plan_profile(uuid,uuid,uuid,jsonb)'::regprocedure)) is distinct from '8011f1995b6249d5d72fa98910c2bda3' then raise exception 'CP7_ZERO_EFFECT_INVERSE_DEFINITION_CHANGED:cp7_credit.assert_current_source_plan_profile(uuid,uuid,uuid,jsonb)'; end if;
 if md5(pg_get_functiondef('cp7_credit.assert_initial_return_closed_v1(uuid)'::regprocedure)) is distinct from 'bf3e85df164913ba6a10e3d90a0c9b0c' then raise exception 'CP7_ZERO_EFFECT_INVERSE_DEFINITION_CHANGED:cp7_credit.assert_initial_return_closed_v1(uuid)'; end if;
 if md5(pg_get_functiondef('cp7_credit_note_carry_de.assert_effect_v1(jsonb,jsonb,uuid,uuid,numeric)'::regprocedure)) is distinct from 'b228fb25e6208d5856c9f361bac72be2' then raise exception 'CP7_ZERO_EFFECT_INVERSE_DEFINITION_CHANGED:cp7_credit_note_carry_de.assert_effect_v1(jsonb,jsonb,uuid,uuid,numeric)'; end if;
 if md5(pg_get_functiondef('cp7_note.command(jsonb,uuid,text)'::regprocedure)) is distinct from '0712b785c0d44b46878e2cca642be71f' then raise exception 'CP7_ZERO_EFFECT_INVERSE_DEFINITION_CHANGED:cp7_note.command(jsonb,uuid,text)'; end if;
 if md5(pg_get_functiondef('cp7_note_zero_effect.assert_price_effect_v1(jsonb,jsonb,uuid,uuid,numeric)'::regprocedure)) is distinct from '0692f43fc8d09d0d0c3ba3238b0fb521' then raise exception 'CP7_ZERO_EFFECT_INVERSE_DEFINITION_CHANGED:cp7_note_zero_effect.assert_price_effect_v1(jsonb,jsonb,uuid,uuid,numeric)'; end if;
end $guard$;
CREATE OR REPLACE FUNCTION cp7_note.command(p_payload jsonb, p_request uuid, p_expected text)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare a jsonb;old cp7_note.requests%rowtype;h erp.sales_headers%rowtype;root uuid;leaf uuid;
 revision bigint;replaced uuid;native_request uuid;result jsonb;draft jsonb;line jsonb;payment record;returned record;
 paid jsonb;returns jsonb;returned_lines jsonb;new_payment uuid;new_return uuid;new_return_item uuid;allocation uuid;
 return_lineage jsonb:='{}'::jsonb;
 correction_id uuid:=gen_random_uuid();before_movements uuid[];origin record;new_move record;anchor uuid;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_note.access_now();perform cp7_sales.validate_draft(p_payload-'item_lineage',true);
 if p_request is null or p_expected is null or p_expected!~'^[1-9][0-9]{0,18}$'then raise exception 'CP7_NOTE_REQUEST_REQUIRED';end if;
 insert into cp7_note.requests values(auth.uid(),p_request,p_payload,p_expected,null)on conflict do nothing;
 select *into strict old from cp7_note.requests where actor=auth.uid()and request_id=p_request for update;
 if old.payload is distinct from p_payload or old.expected_version is distinct from p_expected then raise exception 'CP7_NOTE_REQUEST_CHANGED';end if;
 if cp7_note.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_NOTE_ACCESS_CHANGED';end if;
 if old.response is not null then return old.response;end if;
 perform cp7_mandor_shop.sale_change_preflight('CORRECT',(p_payload->>'sale_id')::uuid);
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 perform pg_advisory_xact_lock(hashtextextended('FGBOOK|GLOBAL',0));
 if cp7_note.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_NOTE_ACCESS_CHANGED';end if;
 leaf:=(p_payload->>'sale_id')::uuid;
 perform 1 from erp.sales_payments where sale_id=leaf order by id for update;
 perform 1 from erp.sales_returns where sale_id=leaf order by id for update;
 select *into h from erp.sales_headers where id=leaf for update;
 if h.id is null or h.status not in('POSTED','PARTIAL_PAID','PAID')then raise exception 'CP7_NOTE_ACTIVE_POSTED_ONLY';end if;
 if h.row_version::text<>p_expected or cp7_sales.review_token(h.id)<>p_payload->>'review_token'then raise exception 'CP7_NOTE_REVIEW_CHANGED';end if;
 -- Historical correction keeps the actual original event identity/time.
 if p_payload->>'sale_number'is distinct from h.sale_number
  or(p_payload->>'sale_date')::timestamptz is distinct from h.sale_date
  or(p_payload->>'customer_id')::uuid is distinct from h.customer_id
  or(p_payload->>'source_location_id')::uuid is distinct from h.source_location_id then raise exception 'CP7_NOTE_SOURCE_IDENTITY_CHANGED';end if;
 select root_sale_id into root from cp7_note.revisions where replacement_sale_id=leaf;
 root:=coalesce(root,leaf);
 select coalesce(max(r.revision),0)+1 into revision from cp7_note.revisions r where r.root_sale_id=root;
 if exists(select 1 from cp7_note.revisions where previous_sale_id=leaf)then raise exception 'CP7_NOTE_SOURCE_SUPERSEDED';end if;
 if exists(select 1 from erp.sales_payments where sale_id=leaf and status='DRAFT')
  or exists(select 1 from erp.sales_returns where sale_id=leaf and status='DRAFT')then
  raise exception 'CP7_NOTE_PENDING_CHILD_REVIEW_REQUIRED';end if;
 -- A native cash reallocation is journaled at its predecessor's reversal date.
 -- Replaying it here would move that cash back to the original receipt clock;
 -- like payment correction, such a payment stays outside this command.
 if exists(select 1 from erp.sales_payments where sale_id=leaf and status='POSTED'and replaces_payment_id is not null)then
  raise exception 'CP7_NOTE_REALLOCATED_PAYMENT_REVIEW_REQUIRED';end if;
 select coalesce(jsonb_agg(to_jsonb(p)||jsonb_build_object('advance_id',l.advance_id)order by p.payment_date,p.id),'[]')into paid
 from erp.sales_payments p left join erp.initial_import_prepayment_payments l on l.payment_id=p.id
 where p.sale_id=leaf and p.status='POSTED';
 select coalesce(jsonb_agg(to_jsonb(r)||jsonb_build_object('items',
  (select jsonb_agg(to_jsonb(i)||jsonb_build_object('allocation_location_id',x.location_id)order by i.id)
    from erp.sales_return_items i join erp.sale_stock_allocations x on x.id=i.sale_stock_allocation_id where i.return_id=r.id))order by r.physical_at,r.id),'[]')into returns
 from erp.sales_returns r where r.sale_id=leaf and r.status='POSTED';
 select array_agg(m.id)into before_movements from erp.fg_stock_movements m where
  (m.source_type='SALE_ITEM'and exists(select 1 from erp.sales_items i where i.id=m.source_id and i.sale_id=leaf)
   or m.source_type='SALES_RETURN_ITEM'and exists(select 1 from erp.sales_return_items i join erp.sales_returns r on r.id=i.return_id where i.id=m.source_id and r.sale_id=leaf and r.status='POSTED'))
  and m.movement_type in('SALE','SALE_RETURN')and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=m.id);
 insert into cp7_note.context values(pg_backend_pid(),txid_current(),auth.uid(),leaf);
 insert into cp7_sales.command_context values(pg_backend_pid(),txid_current(),auth.uid(),leaf,'SALE_REVERSE');
 perform set_config('app.change_reason',p_payload->>'change_reason',true);
 -- D15-1 / Sol SOL-R1-001: the cash guard judges the end state of inverse + replacement, not the half-way balance.
 if pg_catalog.to_regprocedure('cp7_guard.begin_compound(text)')is not null then perform cp7_guard.begin_compound('SALES_NOTE_CORRECTION');end if;
 -- Remove active children before reversing the invoice, then restore their
 -- immutable original physical inputs onto its replacement in one command.
 for payment in select *from jsonb_to_recordset(paid)as p(id uuid)loop
  perform cp7_sales.command_access('PAYMENT_REVERSE');perform cp7_note.reverse_sales_payment(payment.id,p_payload->>'change_reason');
 end loop;
 for returned in select *from jsonb_to_recordset(returns)as r(id uuid)loop
  perform cp7_sales.command_access('RETURN_REVERSE');perform cp7_note.reverse_sales_return(returned.id,p_payload->>'change_reason');
 end loop;
 perform cp7_note.reverse_sale(leaf,p_payload->>'change_reason');
 native_request:=md5(auth.uid()::text||':NOTE:'||p_request::text)::uuid;
 draft:=(p_payload-'sale_id'-'review_token'-'change_reason'-'item_lineage')||jsonb_build_object('sale_number',left((select sale_number from erp.sales_headers where id=root),38)||' · R'||revision::text||'-'||left(p_request::text,8),'reason',p_payload->>'change_reason');
 result:=erp.save_sale_draft_v2(draft,native_request,null);
 replaced:=(result->>'sale_id')::uuid;
 perform cp7_note.bind_items(leaf,replaced,correction_id,p_payload->'items',p_payload->'item_lineage');
 perform erp.post_sale(replaced);
 for returned in select value from jsonb_array_elements(returns)loop
  perform cp7_sales.command_access('RETURN');
  insert into erp.sales_returns(return_number,sale_id,customer_id,physical_at,notes,status,created_by)
  values(left(returned.value->>'return_number',38)||' · K-'||left(p_request::text,8),replaced,h.customer_id,
   (returned.value->>'physical_at')::timestamptz,returned.value->>'notes','DRAFT',erp.current_app_user_id())returning id into new_return;
  for line in select value from jsonb_array_elements(returned.value->'items')loop
   select x.id into allocation from erp.sale_stock_allocations x join erp.sales_items i on i.id=x.sale_item_id
    where i.sale_id=replaced and i.product_id=(line->>'product_id')::uuid and x.lot_id=(line->>'lot_id')::uuid
     and x.location_id=(line->>'allocation_location_id')::uuid
     and x.sale_item_id=(select l.replacement_item_id from cp7_note.item_lineage l
      join erp.sale_stock_allocations prior_allocation on prior_allocation.sale_item_id=l.previous_item_id
      where prior_allocation.id=(line->>'sale_stock_allocation_id')::uuid and l.replacement_item_id=x.sale_item_id)
     and not exists(select 1 from erp.sales_return_items z where z.return_id=new_return and z.sale_stock_allocation_id=x.id)
     and x.qty_pcs>=
      (line->>'qty_pcs')::integer+coalesce((select sum(z.qty_pcs)from erp.sales_return_items z where z.sale_stock_allocation_id=x.id),0)
    order by x.id limit 1;
   if allocation is null then raise exception 'CP7_NOTE_RETURN_ALLOCATION_CHANGED';end if;
   -- The refund was agreed for the old net price of each returned piece.
   -- Replaying it onto a line sold at another net price would overstate (or
   -- refuse) receivable without anyone seeing it: correct the return first.
   if exists(select 1 from erp.sale_stock_allocations old_x join erp.sales_items o on o.id=old_x.sale_item_id,
     erp.sale_stock_allocations new_x join erp.sales_items n on n.id=new_x.sale_item_id
    where old_x.id=(line->>'sale_stock_allocation_id')::uuid and new_x.id=allocation
     and(o.qty_pcs*o.unit_price_snapshot-coalesce(o.discount_amount,0))*n.qty_pcs
      <>(n.qty_pcs*n.unit_price_snapshot-coalesce(n.discount_amount,0))*o.qty_pcs)then
    raise exception 'CP7_NOTE_RETURNED_LINE_PRICE_CHANGED';end if;
   insert into erp.sales_return_items(return_id,sale_stock_allocation_id,product_id,lot_id,location_id,qty_pcs,quality_grade,refund_amount,notes)
   values(new_return,allocation,(line->>'product_id')::uuid,(line->>'lot_id')::uuid,(line->>'location_id')::uuid,
    (line->>'qty_pcs')::integer,line->>'quality_grade',(line->>'refund_amount')::numeric,line->>'notes')returning id into new_return_item;
   return_lineage:=return_lineage||jsonb_build_object(new_return_item::text,line->>'id');
  end loop;
  perform erp.post_sales_return(new_return);
 end loop;
 for payment in select value from jsonb_array_elements(paid)loop
  perform cp7_sales.command_access('PAYMENT');
  insert into erp.sales_payments(sale_id,payment_number,payment_date,amount,cash_account_id,payment_method,reference_number,notes,status,created_by)
  values(replaced,left(payment.value->>'payment_number',38)||' · K-'||left(p_request::text,8),
   (payment.value->>'payment_date')::timestamptz,(payment.value->>'amount')::numeric,(payment.value->>'cash_account_id')::uuid,
   payment.value->>'payment_method',payment.value->>'reference_number',payment.value->>'notes','DRAFT',erp.current_app_user_id())returning id into new_payment;
  if payment.value->>'advance_id'is not null then
   -- Same original wallet and amount. Accepted Native funding validation locks
   -- it, checks its actual remaining amount/customer/source snapshot and dates,
   -- and posts liability/AR rather than cash. No opening balance is edited.
   insert into erp.initial_import_prepayment_payments(payment_id,advance_id,sales_payment_id,payment_snapshot)
   select new_payment,(payment.value->>'advance_id')::uuid,new_payment,to_jsonb(p)-'status'
   from erp.sales_payments p where p.id=new_payment;
  end if;
  perform erp.post_sales_payment(new_payment);
  insert into cp7_note.payment_replays(previous_payment_id,replacement_payment_id,correction_id)
  values((payment.value->>'id')::uuid,new_payment,correction_id);
 end loop;
 if pg_catalog.to_regprocedure('cp7_guard.end_compound()')is not null then perform cp7_guard.end_compound();end if;
 -- Collapse compensating movements under their original source card. A newly
 -- added SKU gets its own Native card inserted beside this note's source,
 -- using the accepted move writer. Unrelated manual order is never reset.
 -- Original quantity, recorded clock and posted price are never edited.
 for new_move in select m.*from erp.fg_stock_movements m where m.reversal_of_id=any(coalesce(before_movements,'{}'::uuid[]))
  or m.source_type='SALE_ITEM'and exists(select 1 from erp.sales_items i where i.id=m.source_id and i.sale_id=replaced)
  or exists(select 1 from erp.fg_stock_movements reservation join erp.sales_items i on i.id=reservation.source_id
    where reservation.id=m.reversal_of_id and reservation.source_type='SALE_ITEM'and i.sale_id=replaced)
  or m.source_type='SALES_RETURN_ITEM'and exists(select 1 from erp.sales_return_items i join erp.sales_returns r on r.id=i.return_id where i.id=m.source_id and r.sale_id=replaced)
  order by case when m.movement_type='SALE'and m.reversal_of_id is null then 0
    when m.reversal_of_id is null then 1 else 2 end,m.system_created_at,m.id loop
  anchor:=null;
  if new_move.reversal_of_id is not null then
   select coalesce(l.origin_id,new_move.reversal_of_id)into anchor from(select 1)x left join cp7_fg.correction_movements l on l.member_id=new_move.reversal_of_id;
  elsif new_move.source_type='SALE_ITEM'and exists(select 1 from erp.sales_items where id=new_move.source_id and sale_id=replaced)then
   anchor:=cp7_note.line_origin(leaf,new_move.source_id,new_move.product_id,new_move.lot_id,new_move.location_id,new_move.quality_grade);
   if anchor is null then
    select coalesce(l.origin_id,m.id)into anchor from erp.fg_stock_movements m join erp.sales_items i on i.id=m.source_id
     left join cp7_fg.correction_movements l on l.member_id=m.id
     where i.sale_id=replaced and i.id=new_move.source_id and m.movement_type='SALE'and m.product_id=new_move.product_id
      and m.location_id=new_move.location_id and m.quality_grade=new_move.quality_grade
     order by(m.lot_id=new_move.lot_id)desc,m.book_order,m.id limit 1;
    if anchor=new_move.id then
     select coalesce(l.origin_id,m.id) as origin_id into origin from erp.fg_stock_movements m join erp.sales_items i on i.id=m.source_id
      left join cp7_fg.correction_movements l on l.member_id=m.id
      where i.sale_id=leaf and m.movement_type='SALE'order by m.book_order,m.id limit 1;
     if origin.origin_id is null then raise exception 'CP7_NOTE_ORIGINAL_BOOK_SOURCE_REQUIRED';end if;
     perform erp.move_fg_stock_card_row_to_position(new_move.id,cp7_fg.book_anchor(new_move.id,origin.origin_id,'AFTER'));
    end if;
   end if;
  elsif new_move.source_type='SALES_RETURN_ITEM'then
   select coalesce(l.origin_id,m.id)into anchor from erp.fg_stock_movements m join erp.sales_return_items i on i.id=m.source_id join erp.sales_returns r on r.id=i.return_id
    left join cp7_fg.correction_movements l on l.member_id=m.id where r.sale_id=leaf and i.id=(return_lineage->>new_move.source_id::text)::uuid and m.movement_type='SALE_RETURN'
     and m.product_id=new_move.product_id and m.lot_id is not distinct from new_move.lot_id and m.location_id=new_move.location_id
     and m.quality_grade=new_move.quality_grade and m.physical_at=new_move.physical_at order by m.book_order,m.id limit 1;
  end if;
  if anchor is not null and anchor<>new_move.id then insert into cp7_fg.correction_movements values(new_move.id,anchor,correction_id,clock_timestamp());end if;
 end loop;
 if cp7_note.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_NOTE_ACCESS_CHANGED';end if;
 insert into cp7_note.revisions(id,root_sale_id,previous_sale_id,replacement_sale_id,revision,actor,request_id,reason,effective_at)
 values(correction_id,root,leaf,replaced,revision,auth.uid(),p_request,p_payload->>'change_reason',h.sale_date);
 delete from cp7_sales.command_context where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 delete from cp7_note.context where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 result:=jsonb_build_object('contract_version','cp7.note-correction-outcome.v1','kind','COMMITTED_OUTCOME',
  'action','CORRECT','request_id',p_request,'root_sale_id',root,'previous_sale_id',leaf,
  'sale_id',replaced,'revision_id',correction_id,'revision',revision::text,'effective_at',h.sale_date);
 update cp7_note.requests set response=result where actor=auth.uid()and request_id=p_request;
 return result;
end $function$;
CREATE OR REPLACE FUNCTION cp7_credit.assert_current_source_plan_profile(p_sale uuid, p_root uuid, p_leaf uuid, p_actual jsonb)
 RETURNS void
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO ''
 SET "TimeZone" TO 'UTC'
AS $function$
declare root uuid;actual jsonb;e record;
begin
 if(p_actual->>'sale_id',p_actual->>'root_sale_id',p_actual->>'current_leaf_id')is distinct from
   (p_sale::text,p_root::text,p_leaf::text)then raise exception 'CP7_CREDIT_CURRENT_ASSIGNMENT_CHANGED';end if;
 if jsonb_typeof(p_actual->'upstream_root_ids')is distinct from'array'
  or not(p_actual->'upstream_root_ids')@>jsonb_build_array(p_root)then raise exception 'CP7_CREDIT_CURRENT_SOURCE_ROOT_SET_REQUIRED';end if;
 for root in select value::uuid from jsonb_array_elements_text(p_actual->'upstream_root_ids')order by value loop
  actual:=case when root=p_root then p_actual else cp7_credit.current_materialized_objects(root,root,root)end;
  for e in select ce.id from cp7_credit.consumption_events ce join cp7_credit.cohorts c on c.id=ce.cohort_id
   join cp7_credit.return_families f on f.id=c.family_id where f.family_root_sale_id=root order by ce.id loop
   perform cp7_credit.consumer_event_data_v1(e.id);
  end loop;
  if root=p_root and cp7_credit_note_carry_de.has_root_v1(root)then
   perform cp7_credit_note_carry_de.assert_profile_v1(p_sale,p_root,p_leaf,actual);
  else perform cp7_credit._consumer_root_source_profile_v1(root,root,root,actual);end if;
 end loop;
end $function$;
CREATE OR REPLACE FUNCTION cp7_credit.assert_initial_return_closed_v1(p_operation uuid)
 RETURNS void
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO ''
 SET "TimeZone" TO 'UTC'
AS $function$
declare m cp7_credit.initial_return_materializations;c cp7_credit.initial_return_completions;q cp7_sales.requests;a jsonb;h erp.sales_headers;net numeric;paid numeric;
begin
 select *into strict m from cp7_credit.initial_return_materializations where operation_id=p_operation;
 select *into strict q from cp7_sales.requests where actor=m.actor and request_id=m.request_id;
 if q.action<>'RETURN'or q.payload is distinct from m.legacy_payload or q.expected_version is distinct from m.expected_version
  or(q.response->>'sale_id',q.response->>'return_id',q.response->>'return_status',q.response->>'action',q.response->>'request_id')is distinct from
   (m.source_sale_id::text,m.source_return_id::text,'POSTED','RETURN',m.request_id::text)then raise exception 'CP7_CREDIT_FINAL_INNER_RECEIPT_REQUIRED';end if;
 if m.origin='REVIEWED_SETTLEMENT'then
  select *into strict c from cp7_credit.initial_return_completions where operation_id=m.operation_id;
  if c.inner_receipt is distinct from q.response or c.final_manifest_sha256 is distinct from ow04_source_proposal.sha(c.final_manifest)
   or not exists(select 1 from cp7_credit.return_requests o where o.actor=m.actor and o.request_id=m.request_id and o.expected_version=m.expected_version
    and cp7_credit.pg_jsonb_sha256(o.payload)=m.payload_sha256 and o.response=c.outer_receipt)then raise exception 'CP7_CREDIT_FINAL_OUTER_RECEIPT_REQUIRED';end if;
 end if;
 if exists(select 1 from cp7_credit.initial_return_work where operation_id=m.operation_id)
  or exists(select 1 from cp7_credit.execution_context where actor=m.actor and request_id=m.request_id)
  or exists(select 1 from cp7_credit.return_native_scope where actor=m.actor and return_id=m.source_return_id)
  or exists(select 1 from cp7_credit.return_command_scope where actor=m.actor and request_id=m.request_id)
  or exists(select 1 from cp7_credit.posting_scope where actor=m.actor and request_id=m.request_id)
  or exists(select 1 from cp7_credit.initial_refund_posting_scope where actor=m.actor and request_id=m.request_id)then raise exception 'CP7_CREDIT_FINAL_PRIVATE_SCOPE_LEAK';end if;
 select *into strict h from erp.sales_headers where id=m.source_sale_id;
 if h.status not in('POSTED','PARTIAL_PAID','PAID')then raise exception 'CP7_CREDIT_NEW_RETURN_FINAL_ACTIVE_SALE_REQUIRED';end if;
 a:=cp7_credit.inspect_current_materialized_profile(m.source_sale_id,m.source_sale_id,m.source_sale_id);
 perform cp7_credit.assert_current_source_plan_profile(m.source_sale_id,m.source_sale_id,m.source_sale_id,a);
 perform cp7_credit.assert_financial_materialization_provenance(a);
 net:=(select coalesce(sum(line_total),0)from erp.sales_items where sale_id=h.id)
  -(select coalesce(sum(i.refund_amount),0)from erp.sales_return_items i join erp.sales_returns r on r.id=i.return_id where r.sale_id=h.id and r.status='POSTED');
 paid:=(select coalesce(sum(amount),0)from erp.sales_payments where sale_id=h.id and status='POSTED')+(a->>'U')::numeric-(a->>'I')::numeric;
 if net<0 or paid<0 or paid>net or h.status<>(case when paid=net then'PAID'when paid>0 then'PARTIAL_PAID'else'POSTED'end)then
  raise exception 'CP7_CREDIT_FINAL_AR_OR_STATUS_MISMATCH';end if;
 if m.cohort_id is not null and m.settlement->>'mode'='REFUND'and not exists(select 1 from cp7_credit.consumption_events ce
  where ce.id=m.refund_operation_id and ce.cohort_id=m.cohort_id and ce.amount=(m.actual_kernel->>'net_current_k')::numeric)then
  raise exception 'CP7_CREDIT_FINAL_FULL_REFUND_MISSING';end if;
end $function$;
drop table cp7_note_zero_effect.receipts restrict;
drop table cp7_note_zero_effect.preparations restrict;
drop function cp7_note_zero_effect.owned_leaf_for_return_v1(uuid,uuid) restrict;
drop function cp7_note_zero_effect.assert_owned_profile_v1(uuid,uuid,uuid,jsonb) restrict;
drop function cp7_note_zero_effect.has_owned_root_v1(uuid) restrict;
drop function cp7_note_zero_effect.finish_v1(jsonb,jsonb) restrict;
drop function cp7_note_zero_effect.prepare_v1(jsonb,uuid,text,uuid,jsonb) restrict;
drop function cp7_note_zero_effect.reject_receipt_mutation_v1() restrict;
drop function cp7_note_zero_effect.assert_price_effect_v1(jsonb,jsonb,uuid,uuid,numeric) restrict;
drop function cp7_note_zero_effect.price_intent_v1(uuid,jsonb) restrict;
drop function cp7_note_zero_effect.ordinary_reversed_history_v1(uuid,uuid,jsonb) restrict;
drop schema cp7_note_zero_effect restrict;
do $guard$ begin
 if md5(pg_get_functiondef('cp7_credit.assert_current_source_plan_profile(uuid,uuid,uuid,jsonb)'::regprocedure)) is distinct from '23f7a593ad9484a463ffdc3c2aee2e0f' then raise exception 'CP7_ZERO_EFFECT_INVERSE_DEFINITION_CHANGED:cp7_credit.assert_current_source_plan_profile(uuid,uuid,uuid,jsonb)'; end if;
 if md5(pg_get_functiondef('cp7_credit.assert_initial_return_closed_v1(uuid)'::regprocedure)) is distinct from 'd5f83430dc3ff04fa4a969730940fcff' then raise exception 'CP7_ZERO_EFFECT_INVERSE_DEFINITION_CHANGED:cp7_credit.assert_initial_return_closed_v1(uuid)'; end if;
 if md5(pg_get_functiondef('cp7_credit_note_carry_de.assert_effect_v1(jsonb,jsonb,uuid,uuid,numeric)'::regprocedure)) is distinct from 'b228fb25e6208d5856c9f361bac72be2' then raise exception 'CP7_ZERO_EFFECT_INVERSE_DEFINITION_CHANGED:cp7_credit_note_carry_de.assert_effect_v1(jsonb,jsonb,uuid,uuid,numeric)'; end if;
 if md5(pg_get_functiondef('cp7_note.command(jsonb,uuid,text)'::regprocedure)) is distinct from '96bf6ad085630b7d689666e564900e87' then raise exception 'CP7_ZERO_EFFECT_INVERSE_DEFINITION_CHANGED:cp7_note.command(jsonb,uuid,text)'; end if;
end $guard$;
