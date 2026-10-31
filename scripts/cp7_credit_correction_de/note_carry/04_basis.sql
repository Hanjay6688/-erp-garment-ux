create function cp7_credit_note_carry_de.basis_v1(p_sale uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set timezone='UTC'as $$
declare authority jsonb;a record;events jsonb;event_facts jsonb;profile jsonb;native jsonb;ar jsonb;period jsonb;basis jsonb;graph jsonb;sources jsonb;
 amount numeric;minimum_net numeric;issues jsonb:='[]';lots uuid[];begin
 authority:=cp7_note.access_now();select *into strict a from cp7_credit.current_leaf_assignment(p_sale);
 if a.current_leaf_id<>p_sale or a.requested_status not in('POSTED','PARTIAL_PAID','PAID')then raise exception 'CP7_CREDIT_NOTE_CARRY_ACTIVE_TARGET_REQUIRED';end if;
 if not exists(select 1 from cp7_credit.consumption_events e where e.event_kind='APPLY'and cp7_credit_note_carry_de.effective_target_v1(e.id)=p_sale)then return null;end if;
 perform cp7_credit.assert_current_materialized_profile(p_sale,a.root_sale_id,p_sale);
 profile:=cp7_credit.inspect_current_materialized_profile(p_sale,a.root_sale_id,p_sale);
 events:=cp7_credit.consumer_incoming_funding_v1(p_sale);
 select coalesce(sum((v->>'amount')::numeric),0)into amount from jsonb_array_elements(events)v;
 minimum_net:=cp7_credit_note_carry_de.minimum_net_v1(events);
 select coalesce(jsonb_agg(jsonb_build_object('event',to_jsonb(e),'journal',cp7_credit.materialized_journal_payload(e.journal_id),
  'actual_data',cp7_credit.consumer_event_data_v1(e.id))order by e.id),'[]')into event_facts
  from cp7_credit.consumption_events e where e.event_kind='APPLY'and cp7_credit_note_carry_de.effective_target_v1(e.id)=p_sale;
 ar:=cp7_credit.consumer_invoice_ar_source_v1(p_sale);native:=cp7_credit_note_carry_de.raw_native_snapshot_v1(p_sale);
 -- A source correction can leave target U and every incoming event unchanged.
 -- Bind every connected current source as well, so an old target review never
 -- silently adopts a changed source credit/return/HPP/permission context.
 graph:=cp7_credit.consumer_joined_graph_v1(p_sale,null);
 sources:=cp7_credit.consumer_capture_sources_v1(graph);
 select to_jsonb(p)into strict period from erp.accounting_period_control p where singleton_id=1;
 if a.root_sale_id<>p_sale or exists(select 1 from cp7_note.revisions where root_sale_id=a.root_sale_id)then issues:=issues||'"NEXT_NOTE_REVISION_ADAPTER_REQUIRED"'::jsonb;end if;
 if exists(select 1 from erp.sales_payments where sale_id=p_sale)then issues:=issues||'"NATIVE_PAYMENT_REPLAY_ADAPTER_REQUIRED"'::jsonb;end if;
 if exists(select 1 from erp.sales_returns where sale_id=p_sale)or exists(select 1 from cp7_credit.return_families where family_root_sale_id=a.root_sale_id)
  or(profile->>'I')::numeric<>0 then issues:=issues||'"RETURN_FAMILY_NOTE_ADAPTER_REQUIRED"'::jsonb;end if;
 if amount<=0 then issues:=issues||'"ZERO_INCOMING_NOTE_ADAPTER_REQUIRED"'::jsonb;end if;
 if(ar#>>'{financial_source,transaction_date}')::date is distinct from erp.resolve_accounting_transaction_date((ar#>>'{financial_source,economic_date}')::date)then
  issues:=issues||'"ORIGINAL_NOTE_BOOK_PAIR_ADAPTER_REQUIRED"'::jsonb;end if;
 lots:=cp7_credit.source_hpp_lot_ids_v1(p_sale);
 if exists(select 1 from erp.fg_lots where id=any(lots)and(po_id is not null or lot_origin='CONVERSION'))
  or exists(select 1 from erp.opening_lot_hpp_gl_state where lot_id=any(lots))
  or exists(select 1 from erp.opening_hpp_corrections where lot_id=any(lots))
  or exists(select 1 from erp.fg_lots l where l.id=any(lots)and((select count(*)from erp.hpp_versions h where h.lot_id=l.id)<>1
   or(select count(*)from erp.hpp_versions h where h.lot_id=l.id and h.is_current)<>1))
  or exists(select 1 from erp.be_conversion_sources_v1 c join erp.fg_lots l on l.id=c.source_lot_id where l.po_id is null)then
  issues:=issues||'"NOTE_HPP_CLASS_ADAPTER_REQUIRED"'::jsonb;end if;
 basis:=jsonb_build_object('contract_version','cp7.note-credit-carry-basis.v1','sale_id',p_sale,'root_sale_id',a.root_sale_id,
  'customer_id',a.customer_id,'row_version',native#>>'{sale,row_version}','review_token',cp7_sales.review_token(p_sale),
  'transfer_amount',cp7_credit.cent_text(amount),'minimum_replacement_net',cp7_credit.cent_text(minimum_net),
  'original_net',ar->'gross_amount','incoming_events',events,'incoming_facts',event_facts,'ar_source',ar,'native',native,
  'materialized',profile,'connected_graph',graph,'connected_sources',sources,'authority',authority,'period',period,'issues',issues);
 return basis||jsonb_build_object('basis_sha256',cp7_credit.pg_jsonb_sha256(basis));
end $$;
create function cp7_credit_note_carry_de.public_basis_v1(p_basis jsonb)returns jsonb
language sql immutable security invoker set search_path=''as $$
 select case when p_basis is null then null else jsonb_build_object('contract_version','cp7.note-credit-carry-basis.v1',
  'sale_id',p_basis->'sale_id','root_sale_id',p_basis->'root_sale_id','row_version',p_basis->'row_version','review_token',p_basis->'review_token',
  'basis_sha256',p_basis->'basis_sha256','transfer_amount',p_basis->'transfer_amount','minimum_replacement_net',p_basis->'minimum_replacement_net',
  'original_net',p_basis->'original_net','policy','AUTO_TRANSFER_TO_REPLACEMENT','issues',p_basis->'issues',
  'consumers',(select coalesce(jsonb_agg(jsonb_build_object('event_id',v#>'{event,id}','amount',cp7_credit.cent_text((v#>>'{event,amount}')::numeric),
   'cohort_id',v#>'{event,cohort_id}','journal_id',v#>'{event,journal_id}','historical_target_id',v#>'{event,target_sale_id}',
   'economic_date',v#>'{event,economic_date}','transaction_date',v#>'{event,transaction_date}')order by v#>>'{event,id}'),'[]')
   from jsonb_array_elements(p_basis->'incoming_facts')v))end
$$;
create function cp7_credit_note_carry_de.workspace_v1(p_sale uuid)returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare w jsonb;basis jsonb;begin
 w:=cp7_note.workspace_with_actors(p_sale);basis:=cp7_credit_note_carry_de.basis_v1((w->>'current_sale_id')::uuid);
 if basis is null then return w;end if;
 return w||jsonb_build_object('credit_carry',cp7_credit_note_carry_de.public_basis_v1(basis));
end $$;
create function cp7_credit_note_carry_de.assert_price_only_v1(p jsonb)returns numeric
language plpgsql stable security definer set search_path=''as $$
declare sale uuid:=(p->>'sale_id')::uuid;row_value jsonb;position int;source_id uuid;i erp.sales_items;net numeric:=0;begin
 if jsonb_typeof(p->'item_lineage')is distinct from'array'or jsonb_array_length(p->'item_lineage')<>jsonb_array_length(p->'items')
  or jsonb_array_length(p->'items')<>(select count(*)from erp.sales_items where sale_id=sale)
  or exists(select 1 from jsonb_array_elements_text(p->'item_lineage')v where v is null)
  or exists(select 1 from jsonb_array_elements_text(p->'item_lineage')v group by v having count(*)<>1)then raise exception 'CP7_CREDIT_NOTE_CARRY_PRICE_ONLY_REQUIRED';end if;
 for row_value,position in select value,ordinality::int from jsonb_array_elements(p->'items')with ordinality loop
  source_id:=(p->'item_lineage'->>(position-1))::uuid;
  select *into strict i from erp.sales_items where id=source_id and sale_id=sale;
  if(i.product_id,i.qty_pcs)is distinct from((row_value->>'product_id')::uuid,(row_value->>'qty_pcs')::int)then raise exception 'CP7_CREDIT_NOTE_CARRY_PRICE_ONLY_REQUIRED';end if;
  net:=net+round((row_value->>'qty_pcs')::numeric*(row_value->>'unit_price_snapshot')::numeric-(row_value->>'discount_amount')::numeric,2);
 end loop;
 return net;
end $$;
