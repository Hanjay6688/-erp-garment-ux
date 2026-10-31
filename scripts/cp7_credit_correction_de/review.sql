-- Closed arithmetic review, shared by preview and actual owning reconciliation.
create schema cp7_credit_correction_de authorization postgres;
revoke all on schema cp7_credit_correction_de from public,anon,authenticated,service_role;

create function cp7_credit_correction_de.vector_v1(p_components jsonb)returns jsonb
language sql immutable security invoker set search_path=''as $$
 select coalesce(jsonb_agg(jsonb_build_object('amount',round((v->>'amount')::numeric,2)::text,
  'economic_date',v->'economic_date','transaction_date',v->'transaction_date')
  order by v->>'economic_date',v->>'transaction_date'),'[]'::jsonb)
 from jsonb_array_elements(p_components)v where(v->>'amount')::numeric<>0
$$;

create function cp7_credit_correction_de.review_vectors_v1(p_before jsonb,p_after jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''as $$
declare b jsonb;a jsonb;br jsonb;ar jsonb;f jsonb;old jsonb;source_family jsonb;out_rows jsonb:='[]';
 before_i numeric:=0;after_i numeric:=0;consumed numeric:=0;delta numeric;blocked boolean:=false;
begin
 b:=ow04_ordinal_wrapper.normalize_input_v1(p_before);a:=ow04_ordinal_wrapper.normalize_input_v1(p_after);
 if b->>'family_root_sale_id'is distinct from a->>'family_root_sale_id'
  or jsonb_array_length(b->'families')<>jsonb_array_length(a->'families')then raise exception 'CP7_CREDIT_DE_FAMILY_IDENTITY_CHANGED';end if;
 for source_family in select value from jsonb_array_elements(b->'families')loop
  select v into strict old from jsonb_array_elements(a->'families')v where v->>'family_id'=source_family->>'family_id';
  if old-array['events']is distinct from source_family-array['events']then
   raise exception 'CP7_CREDIT_DE_RETAINED_HISTORY_CHANGED';end if;
 end loop;
 br:=ow04_ordinal_wrapper.reconcile_v1(b);
 if br->'arithmetic_supported'is distinct from'true'::jsonb or exists(select 1 from jsonb_array_elements(br->'families')v
  where(v->>'has_reconciliation_effect')::boolean)then raise exception 'CP7_CREDIT_DE_BEFORE_UNRECONCILED';end if;
 ar:=ow04_ordinal_wrapper.reconcile_v1(a);
 for f in select value from jsonb_array_elements(ar->'families')loop
  select v into strict old from jsonb_array_elements(br->'families')v
   where v#>>'{registration,family_id}'=f#>>'{registration,family_id}';
  delta:=(f->>'reconciliation_net_current')::numeric;
  blocked:=blocked or (f->'arithmetic_supported'is distinct from'true'::jsonb);
  before_i:=before_i+(old->>'target_net_current')::numeric;after_i:=after_i+(f->>'target_net_current')::numeric;
  out_rows:=out_rows||jsonb_build_array(jsonb_build_object('family_id',f#>'{registration,family_id}',
   'ordinal',f#>'{registration,ordinal}','before_credit',old->'target_net_current','after_credit',f->'target_net_current',
   'delta',round(delta,2)::text,'capacity_ok',f->'arithmetic_supported',
   'needs_cohort_configuration',f->'needs_cohort_configuration','vector',cp7_credit_correction_de.vector_v1(f->'reconciliation_components')));
 end loop;
 select coalesce(sum((e->>'amount')::numeric),0)into consumed from jsonb_array_elements(a->'families')ff,
  lateral jsonb_array_elements(ff->'consumptions')e;
 return jsonb_build_object('contract_version','cp7.credit-correction-de.v1','before_credit',round(before_i,2)::text,
  'after_credit',round(after_i,2)::text,'credit_delta',round(after_i-before_i,2)::text,
  'before_available',round(before_i-consumed,2)::text,'after_available',round(after_i-consumed,2)::text,
  'requires_undo',blocked,'families',out_rows,'actual_result',ar,'source_authority_proven',false,
  'increase_policy','AUTO_CREDIT_INCREMENT','shortfall_policy','UNDO_ACTIVE_CONSUMERS_FIRST',
  'replacement_invoice_policy','AUTO_TRANSFER_TO_REPLACEMENT');
end $$;
