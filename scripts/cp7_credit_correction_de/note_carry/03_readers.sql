create function cp7_credit_note_carry_de.operation_v1(p_root uuid)returns uuid
language sql stable security definer set search_path=''as $$
 select coalesce((select operation_id from cp7_credit_note_carry_de.operations_v1 where source_sale_id=p_root),
  (select operation_id from cp7_credit_note_carry_de.work_v1 where source_sale_id=p_root and phase='MATERIALIZED'))
$$;
create function cp7_credit_note_carry_de.root_v1(p_sale uuid)returns uuid
language sql stable security definer set search_path=''as $$
 select case when exists(select 1 from cp7_note.revisions r where r.root_sale_id=a.root_sale_id
  and r.replacement_sale_id=a.current_leaf_id and cp7_credit_note_carry_de.has_root_v1(r.root_sale_id))then a.root_sale_id else p_sale end
 from cp7_credit.current_leaf_assignment(p_sale)a
$$;
create function cp7_credit_note_carry_de.is_current_v1(p_sale uuid)returns boolean
language sql stable security definer set search_path=''as $$
 select a.current_leaf_id=p_sale and a.requested_status in('POSTED','PARTIAL_PAID','PAID')
  and cp7_credit_note_carry_de.has_root_v1(a.root_sale_id)from cp7_credit.current_leaf_assignment(p_sale)a
$$;
create function cp7_credit_note_carry_de.assert_chain_v1(p_root uuid)returns void
language plpgsql stable security definer set search_path=''as $$
declare p jsonb:=cp7_credit_note_carry_de.proof_v1(p_root);r cp7_note.revisions;begin
 if p is null then raise exception 'CP7_CREDIT_NOTE_CARRY_OWNED_CHAIN_REQUIRED';end if;
 select *into strict r from cp7_note.revisions where root_sale_id=p_root;
 if(r.root_sale_id,r.previous_sale_id,r.replacement_sale_id,r.id,r.revision,r.actor,r.request_id)is distinct from
  (p_root,p_root,(p->>'replacement_sale_id')::uuid,(p->>'revision_id')::uuid,1::bigint,(p->>'actor')::uuid,(p->>'request_id')::uuid)
  or not exists(select 1 from erp.sales_headers old_h join erp.sales_headers new_h on new_h.id=r.replacement_sale_id
   where old_h.id=p_root and old_h.status='REVERSED'and new_h.status in('POSTED','PARTIAL_PAID','PAID')and old_h.customer_id=new_h.customer_id)then
  raise exception 'CP7_CREDIT_NOTE_CARRY_NOTE_ASSIGNMENT_CHANGED';end if;
end $$;
create function cp7_credit_note_carry_de.same_target_v1(p_original uuid,p_target uuid)returns boolean
language plpgsql stable security definer set search_path=''as $$
declare a record;b record;begin
 if p_original is not distinct from p_target then return true;end if;
 if p_original is null or p_target is null then return false;end if;
 select *into strict a from cp7_credit.current_leaf_assignment(p_original);
 select *into strict b from cp7_credit.current_leaf_assignment(p_target);
 if(a.root_sale_id,a.customer_id)is distinct from(b.root_sale_id,b.customer_id)
  or not cp7_credit_note_carry_de.has_root_v1(a.root_sale_id)then return false;end if;
 perform cp7_credit_note_carry_de.assert_chain_v1(a.root_sale_id);return true;
end $$;
create function cp7_credit_note_carry_de.effective_target_v1(p_event uuid)returns uuid
language plpgsql stable security definer set search_path=''as $$
declare e cp7_credit.consumption_events;a record;proof jsonb;assignment cp7_credit_note_carry_de.assignments_v1;begin
 select *into strict e from cp7_credit.consumption_events where id=p_event;
 if e.event_kind<>'APPLY'then return e.target_sale_id;end if;
 if not exists(select 1 from cp7_credit_note_carry_de.assignments_v1 where event_id=e.id)then
  if cp7_credit_note_carry_de.has_root_v1(e.target_sale_id)then raise exception 'CP7_CREDIT_NOTE_CARRY_EVENT_ASSIGNMENT_MISSING';end if;
  return e.target_sale_id;end if;
 select *into strict a from cp7_credit.current_leaf_assignment(e.target_sale_id);
 if a.current_leaf_id=e.target_sale_id then return e.target_sale_id;end if;
 if not cp7_credit_note_carry_de.has_root_v1(a.root_sale_id)then return e.target_sale_id;end if;
 perform cp7_credit_note_carry_de.assert_chain_v1(a.root_sale_id);
 select *into strict assignment from cp7_credit_note_carry_de.assignments_v1 where event_id=e.id and replacement_sale_id=a.current_leaf_id;
 if(assignment.historical_target_id,assignment.root_sale_id,assignment.event_snapshot,assignment.event_sha256,assignment.journal_snapshot,assignment.journal_sha256)is distinct from
  (e.target_sale_id,a.root_sale_id,to_jsonb(e),cp7_credit.pg_jsonb_sha256(to_jsonb(e)),cp7_credit.materialized_journal_payload(e.journal_id),
   cp7_credit.pg_jsonb_sha256(cp7_credit.materialized_journal_payload(e.journal_id)))
  or assignment.operation_id is distinct from cp7_credit_note_carry_de.operation_v1(a.root_sale_id)then
  raise exception 'CP7_CREDIT_NOTE_CARRY_EVENT_ASSIGNMENT_CHANGED';end if;
 return a.current_leaf_id;
end $$;
create function cp7_credit_note_carry_de.active_sales_v1(p_graph jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''as $$
declare leaves jsonb;begin
 -- Read the CAPTURED graph's leaf set. An old receipt retains its old active
 -- nodes; a later correction must not rewrite that historical completion.
 if p_graph#>'{source,current_leaf_ids}'is null then return p_graph->'sale_ids';end if;
 select coalesce(jsonb_agg(v order by v),'[]')into leaves from(select distinct value v from jsonb_array_elements_text(
  (p_graph#>'{source,current_leaf_ids}')||coalesce(p_graph#>'{target,current_leaf_ids}','[]'::jsonb)))q;
 if exists(select 1 from jsonb_array_elements(leaves)v where not(p_graph->'sale_ids')@>jsonb_build_array(v))then
  raise exception 'CP7_CREDIT_NOTE_CARRY_CAPTURED_LEAF_SET_CHANGED';end if;
 return leaves;
end $$;
-- A Native-only document snapshot, useful both before the correction and after
-- it. It includes every original/inverse/restatement leg belonging to this
-- exact invoice, without assigning consumer money to an inactive header.
create function cp7_credit_note_carry_de.native_events_v1(p_sale uuid)returns jsonb
language sql stable security definer set search_path=''as $$
 with recursive seeds(id)as(
  select id from erp.journal_entries where source_type='SALE'and source_id=p_sale and reversal_of_id is null
  union select j.id from cp7_note.journal_restatements s join erp.journal_entries j on j.id in(s.neutral_journal_id,s.effective_journal_id)
   where s.previous_sale_id=p_sale and exists(select 1 from erp.journal_entries original where original.id=s.source_journal_id and original.source_type='SALE'and original.source_id=p_sale)
 ),walk(id)as(select id from seeds union select j.id from walk w join erp.journal_entries j on j.reversal_of_id=w.id or(j.source_type='JOURNAL_REVERSAL'and j.source_id=w.id))
 select coalesce(jsonb_agg(jsonb_build_object('id','journal:'||j.id::text,'kind','NET',
  'amount',cp7_credit.cent_text((select coalesce(sum(l.debit-l.credit),0)from erp.journal_lines l where l.journal_entry_id=j.id
   and l.account_id=cp7_credit.account_by_mapping_v1('AR_CUSTOMER'))),'economic_date',j.economic_date::text,'transaction_date',j.transaction_date::text,
  'source_sha256',ow04_source_proposal.sha(ow04_source_proposal.financial_journal_payload(j.id,cp7_credit.account_by_mapping_v1('AR_CUSTOMER'))))order by j.id),'[]')
 from walk w join erp.journal_entries j on j.id=w.id where j.status in('POSTED','REVERSED')
$$;
create function cp7_credit_note_carry_de.raw_document_v1(p_sale uuid)returns jsonb
language sql stable security definer set search_path=''as $$
 select jsonb_build_object('sale',(select to_jsonb(h)from erp.sales_headers h where id=p_sale),
  'items',(select coalesce(jsonb_agg(to_jsonb(i)order by i.id),'[]')from erp.sales_items i where i.sale_id=p_sale),
  'allocations',(select coalesce(jsonb_agg(to_jsonb(a)order by a.id),'[]')from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=p_sale),
  'payments',(select coalesce(jsonb_agg(to_jsonb(p)order by p.id),'[]')from erp.sales_payments p where p.sale_id=p_sale),
  'returns',(select coalesce(jsonb_agg(to_jsonb(r)order by r.id),'[]')from erp.sales_returns r where r.sale_id=p_sale),
  'base_events',cp7_credit_note_carry_de.native_events_v1(p_sale),
  'journals',(select coalesce(jsonb_agg(jsonb_build_object('id',j.id,'status',j.status,'immutable_payload',cp7_credit.materialized_journal_payload(j.id))order by j.id),'[]')
   from erp.journal_entries j where j.id in(select substring(e->>'id'from 9)::uuid from jsonb_array_elements(cp7_credit_note_carry_de.native_events_v1(p_sale))e)))
$$;
create function cp7_credit_note_carry_de.current_events_v1(p_sale uuid)returns jsonb
language plpgsql stable security definer set search_path=''as $$
declare root uuid:=cp7_credit_note_carry_de.root_v1(p_sale);answer jsonb;begin
 perform cp7_credit_note_carry_de.assert_chain_v1(root);
 answer:=cp7_credit_note_carry_de.native_events_v1(root)||cp7_credit_note_carry_de.native_events_v1(p_sale)||cp7_credit.consumer_incoming_funding_v1(p_sale);
 return(select coalesce(jsonb_agg(v order by v->>'id'collate"C"),'[]')from jsonb_array_elements(answer)v);
end $$;
create function cp7_credit_note_carry_de.ordinal_v1(p_sale uuid)returns jsonb
language sql stable security definer set search_path=''as $$
 select jsonb_build_object('contract_version','ow04.ordinal-input.v1','family_root_sale_id',cp7_credit_note_carry_de.root_v1(p_sale),
  'base_events',cp7_credit_note_carry_de.current_events_v1(p_sale),'families','[]'::jsonb)
$$;
