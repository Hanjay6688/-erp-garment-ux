-- Explicit append-only analog choices. Opt-in; no forecast caller is replaced.
create schema cp7_product_analog_choice authorization cp7_capture;
revoke all on schema cp7_product_analog_choice from public,anon,authenticated,service_role;
create table cp7_product_analog_choice.choices(
 id uuid primary key default gen_random_uuid(),target_key text not null,
 revision bigint not null check(revision>0),action text not null check(action in('CONFIRM','CLEAR')),
 evidence jsonb not null,reason text not null,actor uuid not null,request_id uuid not null,
 recorded_at timestamptz not null default clock_timestamp(),unique(target_key,revision)
);
create table cp7_product_analog_choice.commands(
 actor uuid not null,request_id uuid not null,payload jsonb not null,result jsonb not null,
 recorded_at timestamptz not null default clock_timestamp(),primary key(actor,request_id)
);
alter table cp7_product_analog_choice.choices owner to cp7_capture;
alter table cp7_product_analog_choice.commands owner to cp7_capture;
alter table cp7_product_analog_choice.choices enable row level security;
alter table cp7_product_analog_choice.commands enable row level security;
create policy no_access on cp7_product_analog_choice.choices for all to public using(false)with check(false);
create policy no_access on cp7_product_analog_choice.commands for all to public using(false)with check(false);
revoke all on cp7_product_analog_choice.choices,cp7_product_analog_choice.commands from public,anon,authenticated,service_role;
create trigger immutable_choice before update or delete on cp7_product_analog_choice.choices
 for each row execute function cp7_private.immutable_run();
create trigger immutable_command before update or delete on cp7_product_analog_choice.commands
 for each row execute function cp7_private.immutable_run();

create function cp7_product_analog_choice.material(c jsonb,p_target text,p_source text)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare prepared jsonb;envelope jsonb;target_product jsonb;source_product jsonb;history_row jsonb;
 n integer;days numeric;total numeric;minimum numeric;
begin
 prepared:=cp7_bounded_analysis_stage.require_inputs(c,c->'bounded_query');
 -- Reuse the advisory's target/profile validation and explicit minimum.
 envelope:=cp7_product_analog_stage.candidates(c,p_target,0,1);
 if envelope->>'state'='PLANNING_CONFIG_REQUIRED'then raise exception 'CP7_ANALOG_CHOICE_PROFILE_REQUIRED';end if;
 minimum:=cp7_wip.pcs(envelope->'minimum_available_days');
 perform cp7_wip.key(to_jsonb(p_source));
 if p_source=p_target then raise exception 'CP7_ANALOG_CHOICE_SELF';end if;
 select count(*),(jsonb_agg(p))->0 into n,source_product from jsonb_array_elements(c->'facts'->'products')p
  where(p->>'root_id')||':'||(p->>'size_id')=p_source;
 if n<>1 then raise exception 'CP7_ANALOG_CHOICE_SOURCE';end if;
 select p into target_product from jsonb_array_elements(c->'facts'->'products')p
  where(p->>'root_id')||':'||(p->>'size_id')=p_target;
 if source_product->'size_id'is distinct from target_product->'size_id'then raise exception 'CP7_ANALOG_CHOICE_SIZE';end if;
 select count(*),(jsonb_agg(h))->0 into n,history_row from jsonb_array_elements(prepared->'history')h
  where h->>'target_key'=p_source;
 if n<>1 then raise exception 'CP7_ANALOG_CHOICE_HISTORY';end if;
 days:=cp7_wip.pcs(to_jsonb(history_row->>'available_days'));
 if days<minimum or history_row->>'available_sales_mean'is null then raise exception 'CP7_ANALOG_CHOICE_INSUFFICIENT';end if;
 select count(*),coalesce(sum(cp7_wip.pcs(d->'gross_observed_pcs')),0)into n,total
  from jsonb_array_elements(history_row->'days')d where d->>'state'='AVAILABLE';
 if n<>days then raise exception 'CP7_ANALOG_CHOICE_AVAILABLE_COUNT';end if;
 -- The exact integer numerator comes from AVAILABLE day facts, never mean*days.
 return jsonb_build_object('contract_version','cp7.product-analog-material.v1',
  'target_key',p_target,'source_key',p_source,'target_product',target_product,'source_product',source_product,
  'profile_id',envelope->'profile_id','profile_revision',envelope->'profile_revision',
  'minimum_available_days',minimum::text,'available_total_pcs',total::text,'available_days',days::text,
  'history_hash',prepared->'history_hash','source_hash',prepared->'source_hash',
  'captured_at',c->'captured_at','query',c->'bounded_query','refs',history_row->'refs');
end $$;

create function cp7_product_analog_choice.source_at(p_targets text[],p_at timestamptz)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select coalesce(jsonb_agg(jsonb_build_object('target_key',q.target_key,'choice_id',v.id,
  'revision',coalesce(v.revision,0)::text,'action',v.action,'evidence',v.evidence,'reason',v.reason,
  'actor_scope_id',v.actor,'recorded_at',v.recorded_at,'request_id',v.request_id,
  'state',case when v.id is null then'UNREVIEWED'when v.action='CLEAR'then'CLEARED'else'CONFIRMED_ASSUMPTION'end)
  order by q.target_key collate"C"),'[]')
 from unnest(p_targets)q(target_key)left join lateral(
  select x.*from cp7_product_analog_choice.choices x where x.target_key=q.target_key and x.recorded_at<=p_at
  order by x.revision desc limit 1)v on true
$$;

create function cp7_product_analog_choice.workspace(p_targets text[])returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;result jsonb;k text;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(false);
 if p_targets is null or array_ndims(p_targets)<>1 or cardinality(p_targets)not between 1 and 200
  or(select count(distinct x)from unnest(p_targets)x)<>cardinality(p_targets)then raise exception 'CP7_ANALOG_CHOICE_SCOPE';end if;
 foreach k in array p_targets loop perform cp7_wip.key(to_jsonb(k));end loop;
 result:=jsonb_build_object('contract_version','cp7.product-analog-choices.v1','actor_scope_id',a->'actor',
  'access_epoch',encode(pg_catalog.sha256(convert_to(a::text,'UTF8')),'hex'),
  'rows',cp7_product_analog_choice.source_at(p_targets,clock_timestamp()),'forecast_applied',false,'production_go',false);
 if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
 return result;
end $$;

create function cp7_product_analog_choice.apply(p_payload jsonb,p_request uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;old cp7_product_analog_choice.commands%rowtype;saved cp7_product_analog_choice.choices%rowtype;
 j cp7_analysis_stage.jobs%rowtype;target text;action text;reason text;expected bigint;rev bigint;
 reviewed jsonb;material jsonb;current_source jsonb;outcome jsonb;scale numeric;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_schedule_native.access_now(true);
 if p_request is null then raise exception 'CP7_ANALOG_CHOICE_REQUEST_REQUIRED';end if;
 perform cp7_wip.fields(p_payload,array['contract_version','source_request','source_hash','access_epoch',
  'target_key','source_key','scale_factor','reason','reviewed','expected_revision','action']);
 if p_payload->>'contract_version'is distinct from'cp7.product-analog-choice-command.v1' then raise exception 'CP7_ANALOG_CHOICE_CONTRACT';end if;
 -- Take the Native envelope before either metadata lock; recheck access after waits.
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 if cp7_schedule_native.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7:ANALOG:REQUEST:'||(a->>'actor')||':'||p_request::text,0));
 if cp7_schedule_native.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
 select *into old from cp7_product_analog_choice.commands where actor=(a->>'actor')::uuid and request_id=p_request;
 if found then
  if old.payload<>p_payload then raise exception 'CP7_ANALOG_CHOICE_REQUEST_CHANGED';end if;
  return old.result;
 end if;
 if p_payload->>'access_epoch'is distinct from encode(pg_catalog.sha256(convert_to(cp7_schedule_native.access_now(false)::text,'UTF8')),'hex')then
  raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
 target:=cp7_wip.key(p_payload->'target_key');action:=p_payload->>'action';reason:=btrim(p_payload->>'reason');
 if action is null or action not in('CONFIRM','CLEAR')or p_payload->'reviewed'is distinct from'true'::jsonb
  or jsonb_typeof(p_payload->'reason')is distinct from'string'or reason is null or length(reason)not between 1 and 1000
  or jsonb_typeof(p_payload->'expected_revision')is distinct from'string'
  or p_payload->>'expected_revision'!~'^(0|[1-9][0-9]{0,18})$'then raise exception 'CP7_ANALOG_CHOICE_REVIEW';end if;
 expected:=(p_payload->>'expected_revision')::bigint;
 perform pg_advisory_xact_lock(hashtextextended('CP7:ANALOG:TARGET:'||target,0));
 if cp7_schedule_native.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
 select coalesce(max(x.revision),0)into rev from cp7_product_analog_choice.choices x where x.target_key=target;
 if expected<>rev then raise exception 'CP7_ANALOG_CHOICE_REVISION_CHANGED';end if;
 if action='CONFIRM'then
  scale:=cp7_demand.decimal(p_payload->'scale_factor');
  if scale<=0 then raise exception 'CP7_ANALOG_CHOICE_SCALE';end if;
  reviewed:=cp7_product_analog_stage.read_candidates((p_payload->>'source_request')::uuid,target,0,1,p_payload->>'access_epoch');
  if reviewed#>>'{reference,source_hash}'is distinct from p_payload->>'source_hash'then raise exception 'CP7_ANALOG_CHOICE_REFERENCE_CHANGED';end if;
  select *into j from cp7_analysis_stage.jobs where run_id=(reviewed->>'run_id')::uuid;
  current_source:=cp7_bounded_analysis_stage.source_for(j.reference,j.query);
  if cp7_analysis_native.fingerprint(current_source)is distinct from j.source_hash then
   raise exception using errcode='40001',message='CP7_ANALOG_CHOICE_SOURCE_CHANGED';end if;
  material:=cp7_product_analog_choice.material(j.reference,target,p_payload->>'source_key')||jsonb_build_object(
   'source_request',p_payload->'source_request','source_run',j.run_id,'analysis_source_hash',j.source_hash,
   'identity_hash',reviewed->'identity_hash','producer_hash',reviewed->'producer_hash',
   'scale_factor',scale::text,'reviewed',true);
 else
  if rev=0 then raise exception 'CP7_ANALOG_CHOICE_NOT_SELECTED';end if;
  if p_payload->'source_request'is distinct from'null'::jsonb or p_payload->'source_hash'is distinct from'null'::jsonb
   or p_payload->'source_key'is distinct from'null'::jsonb or p_payload->'scale_factor'is distinct from'null'::jsonb then
   raise exception 'CP7_ANALOG_CHOICE_CLEAR_FIELDS';end if;
  material:='null'::jsonb;
 end if;
 insert into cp7_product_analog_choice.choices(target_key,revision,action,evidence,reason,actor,request_id)
 values(target,rev+1,action,material,reason,(a->>'actor')::uuid,p_request)returning *into saved;
 outcome:=jsonb_build_object('contract_version','cp7.product-analog-choice-outcome.v1','choice_id',saved.id,
  'target_key',target,'revision',saved.revision::text,'action',action,'request_id',p_request,
  'recorded_at',saved.recorded_at,'evidence',material,'reason',reason,'actor_scope_id',a->'actor',
  'state',case when action='CLEAR'then'CLEARED'else'CONFIRMED_ASSUMPTION'end,
  'forecast_applied',false,'production_go',false);
 insert into cp7_product_analog_choice.commands(actor,request_id,payload,result)values((a->>'actor')::uuid,p_request,p_payload,outcome);
 if action='CONFIRM'and cp7_analysis_native.fingerprint(cp7_bounded_analysis_stage.source_for(j.reference,j.query))is distinct from j.source_hash then
  raise exception using errcode='40001',message='CP7_ANALOG_CHOICE_SOURCE_CHANGED';end if;
 if cp7_schedule_native.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;
 return outcome;
end $$;

alter function cp7_product_analog_choice.material(jsonb,text,text)owner to cp7_capture;
alter function cp7_product_analog_choice.source_at(text[],timestamptz)owner to cp7_capture;
alter function cp7_product_analog_choice.workspace(text[])owner to cp7_capture;
alter function cp7_product_analog_choice.apply(jsonb,uuid)owner to cp7_capture;
revoke all on all functions in schema cp7_product_analog_choice from public,anon,authenticated,service_role;
create function public.erp_cp7_get_product_analog_choices_v1(p_targets text[])returns jsonb
language sql volatile security definer set search_path=''set TimeZone='UTC'as $$select cp7_product_analog_choice.workspace(p_targets)$$;
create function public.erp_cp7_save_product_analog_choice_v1(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''set TimeZone='UTC'as $$select cp7_product_analog_choice.apply(p_payload,p_request)$$;
grant create on schema public to cp7_capture;
alter function public.erp_cp7_get_product_analog_choices_v1(text[])owner to cp7_capture;
alter function public.erp_cp7_save_product_analog_choice_v1(jsonb,uuid)owner to cp7_capture;
revoke create on schema public from cp7_capture;
revoke all on function public.erp_cp7_get_product_analog_choices_v1(text[]),public.erp_cp7_save_product_analog_choice_v1(jsonb,uuid)from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_get_product_analog_choices_v1(text[]),public.erp_cp7_save_product_analog_choice_v1(jsonb,uuid)to authenticated;
