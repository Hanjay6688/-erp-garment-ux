-- Pending complete owning consumer composition. Actual-data checks below are
-- not current authority, source-target reconciliation or transaction closure.
do $not_an_installer$begin
 raise exception 'OW04_CONSUMER_REQUIRES_COMPLETE_OWNING_COMPOSITION';
end $not_an_installer$;

-- Identify AR from the actual original SALE, never today's AR mapping. Native
-- SALE puts the sole gross customer debit on AR; ambiguous/missing candidates
-- refuse. HPP lines are outside this immutable monetary source payload.
create function cp7_credit.consumer_invoice_ar_source_v1(p_sale uuid)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare h erp.sales_headers;j erp.journal_entries;account uuid;gross numeric;
begin
 select *into strict h from erp.sales_headers where id=p_sale;
 select coalesce(sum(i.line_total),0)into gross from erp.sales_items i where i.sale_id=p_sale;
 select *into strict j from erp.journal_entries where source_type='SALE'and source_id=p_sale and reversal_of_id is null;
 if gross<=0 or gross::text in('NaN','Infinity','-Infinity')or gross*100<>trunc(gross*100)
  or j.status not in('POSTED','REVERSED')or j.economic_date is distinct from(h.sale_date at time zone'Asia/Jakarta')::date
  or j.transaction_date<j.economic_date then raise exception 'CP7_CREDIT_CONSUMER_TARGET_SALE_SOURCE_INVALID';end if;
 select l.account_id into strict account from erp.journal_lines l join erp.chart_accounts a on a.id=l.account_id
  where l.journal_entry_id=j.id and l.customer_id=h.customer_id and l.debit=gross and l.credit=0
   and l.vendor_id is null and l.contractor_id is null and l.po_id is null and l.product_id is null
   and a.account_type='ASSET'and a.normal_balance='DEBIT'
   and not exists(select 1 from erp.cash_accounts c where c.coa_account_id=a.id);
 if(select count(*)from erp.journal_lines l where l.journal_entry_id=j.id and l.account_id=account)<>1 then
  raise exception 'CP7_CREDIT_CONSUMER_TARGET_AR_SOURCE_AMBIGUOUS';end if;
 return jsonb_build_object('sale_id',h.id,'customer_id',h.customer_id,'account_id',account,
  'gross_amount',cp7_credit.cent_text(gross::cp7_credit.cent_amount),
  'sale_journal_id',j.id,'financial_source',ow04_source_proposal.financial_journal_payload(j.id,account));
end $$;

create function cp7_credit.consumer_operation_lines_v1(p_operation uuid)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare o cp7_credit.consumer_operations_v1;other_account uuid;label text;
begin
 select *into strict o from cp7_credit.consumer_operations_v1 where id=p_operation;
 other_account:=case o.event_kind when'APPLY'then o.target_ar_account_id else o.cash_coa_account_id end;
 if other_account is null or other_account=o.credit_account_id then
  raise exception 'CP7_CREDIT_CONSUMER_ACCOUNT_COLLISION';end if;
 label:=case o.action when'UNDO'then'Pembatalan pemakaian kredit pelanggan'
  when'APPLY'then'Pemakaian kredit pelanggan pada nota'else'Pengembalian kredit pelanggan'end;
 return cp7_credit.native_cent_lines(jsonb_build_array(
  jsonb_build_object('account_id',o.credit_account_id,'customer_id',o.customer_id,
   'description',label,'debit',greatest(o.amount,0),'credit',greatest(-o.amount,0)),
  jsonb_build_object('account_id',other_account,'customer_id',o.customer_id,
   'description',label,'debit',greatest(-o.amount,0),'credit',greatest(o.amount,0))));
end $$;

-- No whole-profile/current-E calls, session contexts, current account mapping,
-- clock, locks or actor rights. An inverse validates its one positive original;
-- positive originals never recurse. Cross-invoice application cycles therefore
-- cannot cause recursive financial-profile validation.
create function cp7_credit.consumer_event_data_v1(p_event uuid)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare e cp7_credit.consumption_events;o cp7_credit.consumer_operations_v1;
 ch cp7_credit.cohorts;rf cp7_credit.return_families;j erp.journal_entries;
 old cp7_credit.consumption_events;initial cp7_credit.initial_refund_operations;
 m cp7_credit.initial_return_materializations;expected jsonb;actual jsonb;
 source_kind text;line_hash text;old_data jsonb;node uuid;assignment record;
begin
 select *into strict e from cp7_credit.consumption_events where id=p_event;
 select *into strict ch from cp7_credit.cohorts where id=e.cohort_id;
 select *into strict rf from cp7_credit.return_families where id=ch.family_id;
 select *into strict j from erp.journal_entries where id=e.journal_id;
 select *into o from cp7_credit.consumer_operations_v1 where id=e.id;
 if o.id is null then
  -- The existing initial refund is retained as its original immutable fact.
  -- Later consumer history does not make that historical receipt expire.
  select *into strict initial from cp7_credit.initial_refund_operations where id=e.id;
  select *into strict m from cp7_credit.initial_return_materializations where refund_operation_id=initial.id;
  if (e.cohort_id,e.event_kind,e.amount,e.target_sale_id,e.cash_account_id,e.restores_event_id,
      e.actor,e.request_id,e.economic_date,e.transaction_date,e.source_sha256)
   is distinct from(initial.cohort_id,'REFUND',initial.full_amount,null::uuid,initial.cash_account_id,null::uuid,
      initial.actor,initial.request_id,(initial.physical_at at time zone'Asia/Jakarta')::date,
      initial.required_book_floor,cp7_credit.pg_jsonb_sha256(to_jsonb(initial)))
   or e.reason is distinct from initial.reason
   or m.cohort_id<>ch.id or initial.initial_plan_id<>ch.initial_plan_id
   or initial.full_amount<>ch.initial_net_amount
   or initial.book_floor_manifest is distinct from m.projection->'refund_book_plan'
   or e.lines_sha256_pg is distinct from cp7_credit.verify_initial_refund_journal(initial.id,j.id,e.transaction_date)then
   raise exception 'CP7_CREDIT_INITIAL_CONSUMER_DATA_CHANGED';end if;
  return jsonb_build_object('event_id',e.id,'operation_origin','INITIAL_REFUND',
   'event',to_jsonb(e),'journal_id',j.id,'credit_account_id',ch.credit_account_id,
   'other_account_id',(initial.cash_account_snapshot#>>'{account,id}')::uuid,
   'customer_id',ch.customer_id,'actual_data_verified',true,
   'complete_financial_operation_proven',false);
 end if;
 if (e.cohort_id,e.event_kind,e.amount,e.target_sale_id,e.cash_account_id,e.restores_event_id,
     e.actor,e.request_id,e.economic_date,e.transaction_date,e.reason,e.source_sha256)
  is distinct from(o.cohort_id,o.event_kind,o.amount,o.target_sale_id,o.cash_account_id,o.restores_event_id,
     o.actor,o.request_id,o.economic_date,o.transaction_date,o.reason,cp7_credit.pg_jsonb_sha256(to_jsonb(o)))
  or(o.customer_id,o.credit_account_id,o.source_sale_id,o.source_root_sale_id)is distinct from
    (ch.customer_id,ch.credit_account_id,ch.source_sale_id,rf.family_root_sale_id)
  or o.source_graph_sha256 is distinct from cp7_credit.pg_jsonb_sha256(o.source_graph)
  or o.locked_sources_sha256 is distinct from cp7_credit.pg_jsonb_sha256(o.locked_sources)
  or o.projection_sha256 is distinct from cp7_credit.pg_jsonb_sha256(o.projection)
  or o.credit_account_snapshot#>>'{account,id}'is distinct from o.credit_account_id::text
  or (o.action='UNDO')is distinct from(o.amount<0)
  or o.amount=0 or o.amount::text in('NaN','Infinity','-Infinity')or o.amount*100<>trunc(o.amount*100)
  or o.economic_date is distinct from(o.physical_at at time zone'Asia/Jakarta')::date
  or not isfinite(o.physical_at)or not isfinite(o.economic_date)or not isfinite(o.transaction_date)
  or o.transaction_date<o.economic_date then
  raise exception 'CP7_CREDIT_CONSUMER_OPERATION_DATA_CHANGED';end if;
 -- Root identity is stable history. A lawful later correction may change the
 -- current leaf; do not compare that new leaf with an old operation's leaf.
 foreach node in array array[o.source_sale_id,o.source_current_leaf_id]loop
  select *into strict assignment from cp7_credit.current_leaf_assignment(node);
  if(assignment.root_sale_id,assignment.customer_id)is distinct from(o.source_root_sale_id,o.customer_id)then
   raise exception 'CP7_CREDIT_CONSUMER_SOURCE_ROOT_CHANGED';end if;
 end loop;
 if o.event_kind='APPLY'then
  if o.target_sale_id is null or o.target_sale_id is distinct from o.target_current_leaf_id
   or o.target_root_sale_id=o.source_root_sale_id
   or o.target_ar_account_id=o.credit_account_id
   or o.target_ar_snapshot->>'account_id'is distinct from o.target_ar_account_id::text
   or o.target_ar_snapshot is distinct from cp7_credit.consumer_invoice_ar_source_v1(o.target_sale_id)
   or o.cash_account_id is not null or o.cash_coa_account_id is not null or o.cash_account_snapshot is not null then
   raise exception 'CP7_CREDIT_CONSUMER_TARGET_DATA_CHANGED';end if;
  foreach node in array array[o.target_sale_id,o.target_current_leaf_id]loop
   select *into strict assignment from cp7_credit.current_leaf_assignment(node);
   if(assignment.root_sale_id,assignment.customer_id)is distinct from(o.target_root_sale_id,o.customer_id)then
    raise exception 'CP7_CREDIT_CONSUMER_TARGET_ROOT_CHANGED';end if;
  end loop;
 else
  if o.cash_account_id is null or o.cash_coa_account_id is null or o.cash_coa_account_id=o.credit_account_id
   or o.cash_account_snapshot#>>'{cash,id}'is distinct from o.cash_account_id::text
   or o.cash_account_snapshot#>>'{cash,coa_account_id}'is distinct from o.cash_coa_account_id::text
   or o.cash_account_snapshot#>>'{account,id}'is distinct from o.cash_coa_account_id::text
   or o.target_sale_id is not null or o.target_root_sale_id is not null
   or o.target_current_leaf_id is not null or o.target_ar_account_id is not null or o.target_ar_snapshot is not null then
   raise exception 'CP7_CREDIT_CONSUMER_CASH_DATA_CHANGED';end if;
 end if;
 if o.action='UNDO'then
  select *into strict old from cp7_credit.consumption_events where id=o.restores_event_id;
  if old.amount<=0 or(e.cohort_id,e.event_kind,e.amount,e.target_sale_id,e.cash_account_id)
    is distinct from(old.cohort_id,old.event_kind,-old.amount,old.target_sale_id,old.cash_account_id)
   or e.economic_date<old.economic_date or e.transaction_date<old.transaction_date
   or(select count(*)from cp7_credit.consumption_events where restores_event_id=old.id)<>1 then
   raise exception 'CP7_CREDIT_CONSUMER_NAMED_UNDO_CHANGED';end if;
  old_data:=cp7_credit.consumer_event_data_v1(old.id);
  if(old_data->>'credit_account_id',old_data->>'other_account_id',old_data->>'customer_id')is distinct from
    (o.credit_account_id::text,coalesce(o.target_ar_account_id,o.cash_coa_account_id)::text,o.customer_id::text)then
   raise exception 'CP7_CREDIT_CONSUMER_UNDO_ACCOUNT_CHANGED';end if;
  source_kind:='CP7_CUSTOMER_CREDIT_EVENT_REVERSE';
 else
  if o.restores_event_id is not null or o.action is distinct from o.event_kind then
   raise exception 'CP7_CREDIT_CONSUMER_POSITIVE_DATA_CHANGED';end if;
  source_kind:=case o.event_kind when'APPLY'then'CP7_CUSTOMER_CREDIT_APPLY'else'CP7_CUSTOMER_CREDIT_REFUND'end;
 end if;
 if(j.source_type,j.source_id,j.status,j.reversal_of_id,j.economic_date,j.transaction_date)is distinct from
   (source_kind,o.id,'POSTED',null::uuid,o.economic_date,o.transaction_date)
  or(select count(*)from erp.journal_entries where source_type=source_kind and source_id=o.id)<>1
  or exists(select 1 from erp.journal_entries where reversal_of_id=j.id or(source_type='JOURNAL_REVERSAL'and source_id=j.id))
  or(select count(*)from erp.journal_lines where journal_entry_id=j.id)<>2
  or exists(select 1 from erp.journal_lines where journal_entry_id=j.id and(vendor_id is not null
   or contractor_id is not null or po_id is not null or product_id is not null))then
  raise exception 'CP7_CREDIT_CONSUMER_ACTUAL_JOURNAL_CHANGED';end if;
 select jsonb_agg(x order by x->>'account_id'collate"C")into expected
  from jsonb_array_elements(cp7_credit.consumer_operation_lines_v1(o.id))x;
 select jsonb_agg(jsonb_build_object('account_id',l.account_id,'customer_id',l.customer_id,'description',l.description,
  'debit',l.debit,'credit',l.credit)order by l.account_id::text collate"C")into actual
  from erp.journal_lines l where l.journal_entry_id=j.id;
 line_hash:=cp7_credit.native_lines_sha256(actual);
 if actual is distinct from expected or e.lines_sha256_pg is distinct from line_hash then
  raise exception 'CP7_CREDIT_CONSUMER_ACTUAL_LINES_CHANGED';end if;
 return jsonb_build_object('event_id',e.id,'operation_origin','CONSUMER_COMMAND',
  'event',to_jsonb(e),'journal_id',j.id,'credit_account_id',o.credit_account_id,
  'other_account_id',coalesce(o.target_ar_account_id,o.cash_coa_account_id),
  'customer_id',o.customer_id,'actual_data_verified',true,
  'complete_financial_operation_proven',false);
end $$;

-- Incoming U is signed FUNDING on the receiving document. It is never another
-- sales_payment P row, and source recognition I is never counted as incoming U.
create function cp7_credit.consumer_incoming_funding_v1(p_sale uuid)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare e cp7_credit.consumption_events;fact jsonb;events jsonb:='[]';
begin
 for e in select *from cp7_credit.consumption_events where event_kind='APPLY'and target_sale_id=p_sale order by id loop
  fact:=cp7_credit.consumer_event_data_v1(e.id);
  events:=events||jsonb_build_array(jsonb_build_object('id','journal:'||e.journal_id::text,'kind','FUNDING',
   'amount',cp7_credit.cent_text(e.amount),'economic_date',e.economic_date::text,
   'transaction_date',e.transaction_date::text,'source_sha256',ow04_source_proposal.sha(
    ow04_source_proposal.financial_journal_payload(e.journal_id,(fact->>'other_account_id')::uuid))));
 end loop;
 select coalesce(jsonb_agg(x order by x->>'id'collate"C"),'[]')into events from jsonb_array_elements(events)x;
 return events;
end $$;

-- Blocking active use is distinct from keeping historical evidence. Validate
-- every signed event first; an arbitrary negative row or a zero net sum cannot
-- stand in for the one exact named undo of a positive event.
create function cp7_credit.consumer_active_events_v1(p_cohort uuid)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare e cp7_credit.consumption_events;cohort uuid;answer jsonb:='[]';
begin
 select id into strict cohort from cp7_credit.cohorts where id=p_cohort;
 for e in select *from cp7_credit.consumption_events where cohort_id=cohort order by id loop
  perform cp7_credit.consumer_event_data_v1(e.id);
  if e.amount>0 and not exists(select 1 from cp7_credit.consumption_events u where u.restores_event_id=e.id)then
   answer:=answer||jsonb_build_array(to_jsonb(e));
  end if;
 end loop;
 return answer;
end $$;

do $private$declare sig text;begin
 foreach sig in array array['consumer_invoice_ar_source_v1(uuid)','consumer_operation_lines_v1(uuid)','consumer_event_data_v1(uuid)','consumer_incoming_funding_v1(uuid)','consumer_active_events_v1(uuid)']loop
  execute'alter function cp7_credit.'||sig||' owner to postgres';
  execute'revoke all on function cp7_credit.'||sig||' from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write,cp7_credit_write';
 end loop;
end $private$;
