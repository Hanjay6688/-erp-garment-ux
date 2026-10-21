do $not_an_installer$begin raise exception 'OW04_RECONCILIATION_REQUIRES_COMPLETE_ATOMIC_COMPOSITION';end $not_an_installer$;

-- Factual public-reader path always includes every actual signed I. Only the
-- exact current owning operation can ask a private rebuilder to exclude ALL
-- its own new plans, including parts posted earlier in the same transaction.
create function cp7_credit.source_reconciliation_input_v1(p_sale uuid,p_own_operation uuid default null)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare answer jsonb;family jsonb;families jsonb:='[]';retained jsonb;excluded text[]:='{}';w cp7_credit.source_operation_work_v1;
begin
 answer:=cp7_credit.initial_ordinal_input_v1(p_sale);
 if p_own_operation is null then return answer;end if;
 select *into strict w from cp7_credit.source_operation_work_v1 where operation_id=p_own_operation
  and backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid();
 if w.sale_id<>p_sale or w.phase<>'RECONCILING'or w.plan_manifest is null then
  raise exception 'CP7_CREDIT_EXACT_SOURCE_OPERATION_BASELINE_REQUIRED';end if;
 perform cp7_credit.assert_source_operation_plan_set_v1(w.operation_id);
 select coalesce(array_agg('part:'||pp.id::text order by pp.id),'{}')into excluded
  from cp7_credit.source_operation_plans_v1 sp join cp7_credit.recognition_plans p on p.id=sp.plan_id
  join cp7_credit.recognition_components cc on cc.plan_id=p.id join cp7_credit.component_parts pp on pp.component_id=cc.id
  where sp.operation_id=w.operation_id;
 for family in select value from jsonb_array_elements(answer->'families')loop
  select coalesce(jsonb_agg(e order by e->>'id'collate"C"),'[]')into retained
   from jsonb_array_elements(family->'retained_recognition')e where not(e->>'id'=any(excluded));
  families:=families||jsonb_build_array(jsonb_set(family,'{retained_recognition}',retained));
 end loop;
 return jsonb_set(answer,'{families}',families);
end $$;

-- The full wrapper result remains in the immutable sidecar. Stored component
-- shape stays exactly the six fields expected by the mechanical GL inspector.
create function cp7_credit.source_adjustment_components_v1(p_family jsonb)returns jsonb
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select coalesce(jsonb_agg(jsonb_build_object('amount',x->'amount','economic_date',x->'economic_date',
  'transaction_date',x->'transaction_date','previous_economic_date',x->'previous_economic_date',
  'previous_transaction_date',x->'previous_transaction_date','corners',x->'corners')order by n),'[]')
 from jsonb_array_elements(p_family->'reconciliation_components')with ordinality e(x,n)
$$;

create function cp7_credit.source_adjustment_kernel_v1(p_family jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare target jsonb:=p_family->'source_target';components jsonb;amount numeric;
begin
 if p_family->>'component_basis'is distinct from'FAMILY_TARGET_MINUS_ALL_SUPPLIED_RETAINED_RECOGNITION'
  or not coalesce((p_family->>'arithmetic_supported')::boolean,false)
  or p_family->>'plan_kind'is distinct from'ADJUSTMENT'then
  raise exception 'CP7_CREDIT_SIGNED_FAMILY_ADJUSTMENT_REQUIRED';end if;
 components:=cp7_credit.source_adjustment_components_v1(p_family);
 select coalesce(sum((x->>'amount')::numeric),0)into amount from jsonb_array_elements(components)x;
 if amount is distinct from(p_family->>'reconciliation_net_current')::numeric then
  raise exception 'CP7_CREDIT_SIGNED_FAMILY_ADJUSTMENT_TOTAL_CHANGED';end if;
 return jsonb_build_object('contract_version','ow04.family-adjustment-plan.v1','kernel_version',target->'kernel_version',
  'before_source_sha256',target->'before_source_sha256','after_source_sha256',target->'after_source_sha256',
  'before_events',target->'before_events','added_events',target->'added_events','support',target->'support',
  'components',components,'net_current_k',cp7_credit.cent_text(amount::cp7_credit.cent_amount),
  'has_recognition_effect',jsonb_array_length(components)>0,'full_family_binding',p_family);
end $$;

do $private_source_inputs$declare sig text;begin
 foreach sig in array array['source_reconciliation_input_v1(uuid,uuid)','source_adjustment_components_v1(jsonb)','source_adjustment_kernel_v1(jsonb)']loop
  execute 'alter function cp7_credit.'||sig||' owner to postgres';
  execute 'revoke all on function cp7_credit.'||sig||' from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write';
 end loop;
end $private_source_inputs$;
