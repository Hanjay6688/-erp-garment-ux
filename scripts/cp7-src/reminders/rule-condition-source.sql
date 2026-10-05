-- Closed domain routing also guards cached facts after narrower rights revoke.
create function cp7_reminder_native.condition_domain(p_key text)returns text
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
begin
 if p_key like'PRODUCTION_GAP:%'then return'PRODUCTION';end if;
 if p_key like'ACCESSORY_NEED:%'then return'ACCESSORY';end if;
 if p_key like'AR_DUE:OPENING_AR:%'then return'OPENING_AR';end if;
 if p_key like'AR_DUE:%'and split_part(p_key,':',2)~'^[0-9a-f-]{36}$'then return'SALES_AR';end if;
 if p_key like'AP_DUE:MATERIAL:%'then return'MATERIAL_AP';end if;
 if p_key like'AP_DUE:%'and split_part(p_key,':',2)in('OPENING_AP','PAYROLL_AP','ACCESSORY_AP','LAUNDRY_AP','LAUNDRY_RECEIPT','LAUNDRY_OPENING_UNINVOICED')then return split_part(p_key,':',2);end if;
 raise exception 'CP7_RULE_CONDITION_DOMAIN_INVALID';
end $$;
create function cp7_reminder_native.condition_domain_access(p_domain text)returns boolean
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
begin
 if p_domain in('PRODUCTION','ACCESSORY')then return true;end if;
 if p_domain in('SALES_AR','OPENING_AR')then return erp.has_permission('finance.ar.view');end if;
 if p_domain in('MATERIAL_AP','OPENING_AP')then return erp.has_permission('finance.ap.view');end if;
 if p_domain='PAYROLL_AP'then return erp.has_permission('finance.ap.view')and erp.has_permission('finance.payroll.view');end if;
 if p_domain='ACCESSORY_AP'then return erp.has_permission('finance.ap.view')and erp.has_permission('warehouse.accessory.view')and(erp.has_permission('finance.hpp.view')or erp.has_permission('finance.hpp.manage'));end if;
 if p_domain in('LAUNDRY_AP','LAUNDRY_RECEIPT','LAUNDRY_OPENING_UNINVOICED')then return erp.has_permission('finance.ap.view')and erp.has_permission('production.laundry.view')and(erp.has_permission('finance.hpp.view')or erp.has_permission('finance.hpp.manage'));end if;
 raise exception 'CP7_RULE_CONDITION_DOMAIN_INVALID';
end $$;

-- Current conditions use the same authorized Native facts. No task, policy or
-- delivery flag can resolve a business condition. No business DML is added.
create function cp7_reminder_native.condition_policy(row_source jsonb,policies jsonb,p_at timestamptz)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare binding jsonb:=cp7_reminder_native.policy_resolve(policies,row_source->>'rule_id',row_source->>'target_key');
 chosen jsonb:=binding->'policy';timing jsonb;eligibility text;v text:=row_source->'value'->>'value';
begin
 timing:=cp7_reminder_native.policy_timing(case when chosen='null'::jsonb then null else chosen->'config'end,p_at,null);
 if row_source->>'state'in('DATA_REVIEW','SOURCE_CHANGED')then eligibility:='SOURCE_REVIEW_REQUIRED';
 elsif row_source->>'state'<>'ACTIVE'then eligibility:='NO_CURRENT_ALERT';
 elsif timing->>'status'<>'READY'then eligibility:=timing->>'status';
 elsif chosen->'config'->>'threshold_unit'is distinct from row_source->'value'->>'unit'then eligibility:='UNIT_REVIEW_REQUIRED';
 elsif v is null then eligibility:='SOURCE_REVIEW_REQUIRED';
 elsif v::numeric<(chosen->'config'->>'threshold_value')::numeric then eligibility:='BELOW_SELECTED_THRESHOLD';
 else eligibility:='LOCAL_PREVIEW_ELIGIBLE';end if;
 return row_source||jsonb_build_object('policy_binding',binding,'policy_timing',timing,'eligibility',eligibility,
  'delivery_sent',false,'eligibility_meaning','LOCAL_PREVIEW_ONLY_NOT_BUSINESS_RESOLUTION');
end $$;

create function cp7_reminder_native.condition_rows(e jsonb,ar jsonb,ap jsonb,policies jsonb,p_at timestamptz)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare out_rows jsonb:='[]';r jsonb;c jsonb;d jsonb;value jsonb;row_source jsonb;label text;
 state text;reason text;source_key text;due date;as_of date;days text;known boolean;resolved boolean;
begin
 for r in select x.value from jsonb_array_elements(e->'analysis'->'recommendations')x loop
  value:=r->'q_conditional';known:=value->>'state'in('KNOWN','ASSUMED');resolved:=false;
  if e->>'source_state'<>'UNCHANGED'then state:='SOURCE_CHANGED';reason:='IMMUTABLE_ORIGINAL_REQUIRES_NEW_CAPTURE';
  elsif not known then state:='DATA_REVIEW';reason:='COMPLETE_TIMELINE_GAP_NOT_PROVEN';
  elsif(value->>'value')::numeric>0 then state:='ACTIVE';reason:='CURRENT_EXACT_SIZE_GAP';
  elsif value->>'state'='ASSUMED'then state:='NO_CURRENT_GAP';reason:='SELECTED_SCENARIO_COVERAGE_NOT_PHYSICAL_RESOLUTION';
  else state:='RESOLVED';reason:='KNOWN_CURRENT_ZERO_GAP';resolved:=true;end if;
  select x->>'sku'||' · '||(x->>'product_name')into label from jsonb_array_elements(e->'product_labels')x where x->>'target_key'=r->'target'->>'key';
  row_source:=jsonb_build_object('key','PRODUCTION_GAP:'||(r->'target'->>'key'),'rule_id','PRODUCTION_GAP',
   'target_key',r->'target'->'key','source_id',r->'target'->'product_id','material_key',null,
   'source_hash',e->'analysis'->>'semantic_hash','state',state,'reason',reason,'value',value,
   'production_state',r->'production_state','business_resolved',resolved,'domain','PRODUCTION','financial_source',null,'economic_state','NOT_APPLICABLE','scope','CURRENT_EXACT_SIZE_ANALYSIS','label',label);
  out_rows:=out_rows||jsonb_build_array(cp7_reminder_native.condition_policy(row_source,policies,p_at));
 end loop;
 -- This existing rule is the accessory oracle. Fabric inputs are displayed
 -- through shared analysis, not relabelled as Native accessory proof.
 for r in select x.value from jsonb_array_elements(e->'analysis'->'material_needs')x
  where left(coalesce(x.value->>'material_key',''),7)<>'FABRIC_'loop
  value:=r->'additional_external';known:=value->>'state'in('KNOWN','ASSUMED');resolved:=false;
  if e->>'source_state'<>'UNCHANGED'then state:='SOURCE_CHANGED';reason:='IMMUTABLE_ORIGINAL_REQUIRES_NEW_CAPTURE';
  elsif not known then state:='DATA_REVIEW';reason:='INSTALLATION_AND_ELIGIBLE_UNUSED_SUPPLY_NOT_PROVEN';
  elsif(value->>'value')::numeric>0 then state:='ACTIVE';reason:='SOURCE_BOUND_ADDITIONAL_EXTERNAL_NEED';
  elsif value->>'state'='ASSUMED'then state:='NO_CURRENT_GAP';reason:='SELECTED_MATERIAL_SCENARIO_NOT_PHYSICAL_RESOLUTION';
  else state:='RESOLVED';reason:='KNOWN_CURRENT_ZERO_ACCESSORY_NEED';resolved:=true;end if;
  select x->>'sku'||' · '||(x->>'product_name')into label from jsonb_array_elements(e->'product_labels')x where x->>'target_key'=r->>'target_key';
  row_source:=jsonb_build_object('key','ACCESSORY_NEED:'||(r->>'target_key')||':'||coalesce(r->>'material_key','UNKNOWN_BOM'),
   'rule_id','ACCESSORY_NEED','target_key',r->'target_key','source_id',split_part(r->>'target_key',':',1),
   'material_key',r->'material_key','source_hash',e->'analysis'->>'semantic_hash','state',state,'reason',reason,
   'value',value,'production_state',null,'business_resolved',resolved,'domain','ACCESSORY','financial_source',null,'economic_state','NOT_APPLICABLE','scope','CURRENT_NATIVE_ACCESSORY_BOM_INSTALLATION_AND_ALLOCATION','label',label);
  out_rows:=out_rows||jsonb_build_array(cp7_reminder_native.condition_policy(row_source,policies,p_at));
 end loop;
 if ar is not null and ar<>'null'::jsonb then
  as_of:=(ar->>'as_of')::date;
  for c in select x.value from jsonb_array_elements(ar->'conditions')x loop
   select x into d from jsonb_array_elements(ar->'pages')page cross join lateral jsonb_array_elements(page->'page'->'rows')x where x->>'id'=c->>'source_id';
   if d is null then raise exception 'CP7_RULE_CONDITION_AR_INCOMPLETE';end if;
   due:=(d->>'due_date')::date;days:=case when due is null then null else(as_of-due)::text end;
   state:=case when c->>'state'in('OVERDUE','DUE_TODAY')then'ACTIVE'when c->>'state'='ZERO_BALANCE'then'RESOLVED'
    when c->>'state'in('NOT_DUE_YET','DRAFT_ONLY','INACTIVE_DOCUMENT')then'NO_CURRENT_GAP'else'DATA_REVIEW'end;
   value:=jsonb_build_object('state',case when state='DATA_REVIEW'or days is null then'UNKNOWN'else'KNOWN'end,'unit','DAY',
    'refs',jsonb_build_array(jsonb_build_object('kind','ACCEPTED_P11_NATIVE_SALE','id',c->'source_id','revision',c->'source_revision')));
   if value->>'state'='KNOWN'then value:=value||jsonb_build_object('value',greatest(0,days::integer)::text);else value:=value||jsonb_build_object('reason',c->>'state');end if;
   row_source:=jsonb_build_object('key','AR_DUE:'||(c->>'source_id'),'rule_id','AR_DUE','target_key',null,'source_id',c->'source_id',
    'material_key',null,'source_hash',c->'native_source_hash','state',state,'reason',c->'state','value',value,'production_state',null,
    'business_resolved',c->'business_resolved','domain','SALES_AR','economic_state',case when c->>'state'in('DRAFT_ONLY','INACTIVE_DOCUMENT')then'INACTIVE'when c->'business_resolved'='true'::jsonb then'SETTLED'when d->'financial'->>'open_balance'is not null and(d->'financial'->>'open_balance')::numeric>0 then'OPEN'else'UNKNOWN'end,
    'financial_source',jsonb_build_object('remaining',jsonb_build_object('state',case when d->'financial'->>'open_balance'is null then'UNKNOWN'else'KNOWN'end,'unit','IDR','refs',value->'refs')||case when d->'financial'->>'open_balance'is null then jsonb_build_object('reason','ACCEPTED_NATIVE_REMAINING_NOT_AVAILABLE')else jsonb_build_object('value',d->'financial'->>'open_balance')end,
     'recorded_due_date',due,'document',cp7_reminder_native.exact_numbers(d),'document_sha256',encode(pg_catalog.sha256(convert_to(d::text,'UTF8')),'hex'),'revision_basis','NATIVE_ROW_VERSION'),
    'scope','NATIVE_SALES_RECEIVABLE_ONLY','label',d->>'number'||' · '||(d->>'customer_name'));
   out_rows:=out_rows||jsonb_build_array(cp7_reminder_native.condition_policy(row_source,policies,p_at));
  end loop;
 end if;
 if ap is not null and ap<>'null'::jsonb then
  as_of:=(ap->>'as_of')::date;
  for d in select x.value from jsonb_array_elements(ap->'rows')x loop
   c:=d->'condition';source_key:=d->'liability'->>'purchase_id';due:=(d->>'due_date')::date;days:=case when due is null then null else(as_of-due)::text end;
   state:=case when c->>'state'in('OVERDUE','DUE_TODAY')then'ACTIVE'when c->>'state'='ZERO_BALANCE'then'RESOLVED'
    when c->>'state'in('NOT_DUE_YET','DRAFT_ONLY','INACTIVE_DOCUMENT')then'NO_CURRENT_GAP'else'DATA_REVIEW'end;
   value:=jsonb_build_object('state',case when state='DATA_REVIEW'or days is null then'UNKNOWN'else'KNOWN'end,'unit','DAY',
    'refs',jsonb_build_array(jsonb_build_object('kind','ACCEPTED_BF_NATIVE_MATERIAL_PAYABLE','id',source_key,'revision',c->'source_revision')));
   if value->>'state'='KNOWN'then value:=value||jsonb_build_object('value',greatest(0,days::integer)::text);else value:=value||jsonb_build_object('reason',c->>'state');end if;
   row_source:=jsonb_build_object('key','AP_DUE:MATERIAL:'||source_key,'rule_id','AP_DUE','target_key',null,'source_id',source_key,
    'material_key',null,'source_hash',c->'native_source_hash','state',state,'reason',c->'state','value',value,'production_state',null,
    'business_resolved',c->'business_resolved','domain','MATERIAL_AP','economic_state',case when c->>'state'in('DRAFT_ONLY','INACTIVE_DOCUMENT')then'INACTIVE'when c->'business_resolved'='true'::jsonb then'SETTLED'when c->>'state'='INVOICE_PENDING'then'UNKNOWN'when d->'balance'->>'remaining'is not null and(d->'balance'->>'remaining')::numeric>0 then'OPEN'else'UNKNOWN'end,
    'financial_source',jsonb_build_object('remaining',jsonb_build_object('state',case when c->>'state'='INVOICE_PENDING'or d->'balance'->>'remaining'is null then'UNKNOWN'else'KNOWN'end,'unit','IDR','refs',value->'refs')||case when c->>'state'='INVOICE_PENDING'or d->'balance'->>'remaining'is null then jsonb_build_object('reason','ACCEPTED_FINAL_NATIVE_REMAINING_NOT_AVAILABLE')else jsonb_build_object('value',d->'balance'->>'remaining')end,
     'recorded_due_date',due,'document',cp7_reminder_native.exact_numbers(d),'document_sha256',encode(pg_catalog.sha256(convert_to(d::text,'UTF8')),'hex'),'revision_basis','NATIVE_ROW_VERSION'),
    'scope','NATIVE_MATERIAL_PAYABLE_ONLY','label',d->'liability'->>'purchase_number'||' · '||coalesce(d->'liability'->>'supplier_name','Pemasok'));
   out_rows:=out_rows||jsonb_build_array(cp7_reminder_native.condition_policy(row_source,policies,p_at));
  end loop;
 end if;
 if jsonb_array_length(out_rows)>15000 or octet_length(out_rows::text)>8000000
  or(select count(distinct x->>'key')from jsonb_array_elements(out_rows)x)<>jsonb_array_length(out_rows)then raise exception 'CP7_RULE_CONDITION_SCOPE_INCOMPLETE';end if;
 return out_rows;
end $$;

create function cp7_reminder_native.condition_source(p_run uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb:=cp7_reminder_native.original_authority(p_run);again jsonb;source jsonb;policies jsonb;rows jsonb;at timestamptz;coverage jsonb;stable_rows jsonb;definitions jsonb;
begin
 perform cp7_reminder_native.recheck(a);
 -- One statement/MVCC snapshot supplies all financial pages and policy rows.
 -- The existing accepted readers retain their own current domain checks.
 select jsonb_build_object('ar',case when erp.has_permission('finance.ar.view')then cp7_reminder_native.receivable_source()else null end,
  'ap',case when erp.has_permission('finance.ap.view')then cp7_reminder_native.payable_source()else null end,
  'other',cp7_reminder_native.other_obligation_source(),'policies',cp7_reminder_native.policy_rows(a),'captured_at',clock_timestamp())into source;
 at:=(source->>'captured_at')::timestamptz;policies:=source->'policies';
 again:=cp7_reminder_native.access_now(p_run);perform cp7_reminder_native.recheck(a);
 if cp7_reminder_native.policy_rows(again)is distinct from policies then raise exception using errcode='40001',message='CP7_RULE_CONDITION_POLICY_CHANGED';end if;
 rows:=cp7_reminder_native.condition_rows(again->'analysis',source->'ar',source->'ap',policies,at);
 select rows||coalesce(jsonb_agg(cp7_reminder_native.condition_policy(x.value,policies,at)order by x.value->>'key'),'[]')into rows from jsonb_array_elements(source->'other'->'rows')x;
 coverage:=jsonb_build_object('production','COMPLETE_AUTHORIZED_ORIGINAL','accessory','COMPLETE_AUTHORIZED_ORIGINAL_UNKNOWN_INSTALLATION_RETAINED',
  'sales_ar',case when source->'ar'='null'::jsonb then'EXCLUDED_BY_CURRENT_RIGHTS'else'COMPLETE_NATIVE_DOCUMENT_SCOPE'end,
  'material_ap',case when source->'ap'='null'::jsonb then'EXCLUDED_BY_CURRENT_RIGHTS'else'COMPLETE_NATIVE_DOCUMENT_SCOPE'end,
  'opening_ar',source->'other'->'coverage'->'opening_ar','opening_ap',source->'other'->'coverage'->'opening_ap',
  'payroll_ap',source->'other'->'coverage'->'payroll_ap','accessory_ap',source->'other'->'coverage'->'accessory_ap','laundry_ap',source->'other'->'coverage'->'laundry_ap');
 if jsonb_array_length(rows)>15000 or octet_length(rows::text)>8000000 or(select count(distinct x->>'key')from jsonb_array_elements(rows)x)<>jsonb_array_length(rows)then raise exception 'CP7_RULE_CONDITION_SCOPE_INCOMPLETE';end if;
 if exists(select 1 from jsonb_array_elements(rows)x where not cp7_reminder_native.condition_domain_access(x->>'domain'))then raise exception using errcode='42501',message='CP7_RULE_CONDITION_DOMAIN_CHANGED';end if;
 select coalesce(jsonb_agg(x.value-'policy_timing'-'eligibility'order by x.value->>'key'),'[]')into stable_rows from jsonb_array_elements(rows)x;
 select jsonb_object_agg(sig,encode(pg_catalog.sha256(convert_to(pg_get_functiondef(sig::regprocedure),'UTF8')),'hex'))into definitions
  from unnest(array['cp7_reminder_native.original_authority(uuid)','cp7_reminder_native.condition_source(uuid)','cp7_reminder_native.condition_rows(jsonb,jsonb,jsonb,jsonb,timestamp with time zone)',
   'cp7_reminder_native.condition_policy(jsonb,jsonb,timestamp with time zone)','cp7_reminder_native.policy_resolve(jsonb,text,text)',
   'cp7_reminder_native.policy_timing(jsonb,timestamp with time zone,timestamp with time zone)',
   'cp7_reminder_native.receivable_source()','cp7_reminder_native.payable_source()',
   'cp7_reminder_native.condition_domain(text)','cp7_reminder_native.condition_domain_access(text)',
   'cp7_reminder_native.other_access()','cp7_reminder_native.other_money(text,uuid,text)',
   'cp7_reminder_native.other_document(text,uuid,text,date,jsonb,text,jsonb,date)',
   'cp7_reminder_native.other_opening(boolean,boolean,date)','cp7_reminder_native.other_payroll(date)',
   'cp7_reminder_native.other_accessory(date)','cp7_reminder_native.other_laundry(date)',
   'cp7_reminder_native.other_laundry_pending(date)','cp7_reminder_native.other_obligation_source()'])sig;
 return jsonb_build_object('contract_version','cp7.native-rule-conditions.v2','actor_scope_id',auth.uid(),'analysis',again->'analysis',
  'policy_rows',policies,'rows',rows,'page_complete',true,'total',jsonb_array_length(rows)::text,'coverage',coverage,
  'source_hash',encode(pg_catalog.sha256(convert_to(jsonb_build_object('analysis_hash',again->'analysis'->'analysis'->'semantic_hash',
   'analysis_source_state',again->'analysis'->'source_state','ar_hash',source->'ar'->'source_hash','ap_hash',source->'ap'->'source_hash',
   'other_hash',source->'other'->'source_hash','policies',policies,'coverage',coverage,'conditions',stable_rows,'source_definitions',definitions)::text,'UTF8')),'hex'),'read_at',at,'external_delivery_enabled',false,
  'full_family_acceptance',false,'meaning','CURRENT_SOURCE_CONDITION_SEPARATE_FROM_ATTENTION_DELIVERY_AND_ORIGINAL');
end $$;

alter function cp7_reminder_native.condition_domain(text)owner to cp7_reminder;
alter function cp7_reminder_native.condition_domain_access(text)owner to cp7_reminder;
alter function cp7_reminder_native.condition_policy(jsonb,jsonb,timestamptz)owner to cp7_reminder;
alter function cp7_reminder_native.condition_rows(jsonb,jsonb,jsonb,jsonb,timestamptz)owner to cp7_reminder;
alter function cp7_reminder_native.condition_source(uuid)owner to cp7_reminder;
revoke all on function cp7_reminder_native.condition_domain(text),cp7_reminder_native.condition_domain_access(text),cp7_reminder_native.condition_policy(jsonb,jsonb,timestamptz),cp7_reminder_native.condition_rows(jsonb,jsonb,jsonb,jsonb,timestamptz),
 cp7_reminder_native.condition_source(uuid)from public,anon,authenticated,service_role;
grant create on schema public to cp7_reminder;
create function public.erp_cp7_get_rule_conditions_v1(p_run uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_reminder_native.condition_source(p_run)$$;
alter function public.erp_cp7_get_rule_conditions_v1(uuid)owner to cp7_reminder;
revoke create on schema public from cp7_reminder;
revoke all on function public.erp_cp7_get_rule_conditions_v1(uuid)from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_get_rule_conditions_v1(uuid)to authenticated;
