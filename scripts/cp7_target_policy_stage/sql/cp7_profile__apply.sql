create or replace function cp7_profile.apply(p_payload jsonb,p_request uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;old cp7_profile.commands%rowtype;p cp7_profile.profiles%rowtype;
 sid uuid;pid uuid;sz uuid;expected bigint;current_revision bigint;config jsonb;reason text;
 mode text;minimum numeric;lead numeric;review numeric;buffer numeric;source jsonb;outcome jsonb;k text;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_identity.access_now(true);
 if p_request is null then raise exception 'CP7_PROFILE_REQUEST_REQUIRED';end if;
 perform cp7_wip.fields(p_payload,array['root_id','product_version_id','expected_revision','config','reason']);
 perform pg_advisory_xact_lock(hashtextextended('CP7:PROFILE:REQUEST:'||auth.uid()::text||':'||p_request::text,0));
 if cp7_identity.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_PROFILE_ACCESS_CHANGED';end if;
 select *into old from cp7_profile.commands where actor=auth.uid()and request_id=p_request;
 if found then
  if old.payload<>p_payload then raise exception 'CP7_PROFILE_REQUEST_CHANGED';end if;
  return old.result;
 end if;
 sid:=(p_payload->>'root_id')::uuid;pid:=(p_payload->>'product_version_id')::uuid;
 if sid is null or pid is null or jsonb_typeof(p_payload->'expected_revision')is distinct from 'string'
  or p_payload->>'expected_revision'!~'^(0|[1-9][0-9]{0,18})$'then raise exception 'CP7_PROFILE_REVIEW';end if;
 expected:=(p_payload->>'expected_revision')::bigint;
 perform pg_advisory_xact_lock(hashtextextended('CP7:PROFILE:ROOT:'||sid::text,0));
 if cp7_identity.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_PROFILE_ACCESS_CHANGED';end if;
 source:=cp7_profile.source(array[sid],clock_timestamp());
 if jsonb_array_length(source)<>1 or source->0->>'product_version_id'<>pid::text
  or source->0->>'quality'='IDENTITY_CONFLICT'then raise exception 'CP7_PROFILE_SOURCE_CHANGED';end if;
 sz:=(source->0->>'size_id')::uuid;
 select coalesce(max(revision),0)into current_revision from cp7_profile.profiles where root_id=sid;
 if expected<>current_revision then raise exception 'CP7_PROFILE_REVISION_CHANGED';end if;
 config:=p_payload->'config';reason:=btrim(p_payload->>'reason');
 perform cp7_wip.fields(config-'rounding_multiple'-'buffer_mode'-'service_level',array['mean_mode','daily_pcs','minimum_available_days','lead_days','review_days','buffer_days']);
 -- Optional additive field: old immutable profiles and pending six-key
 -- payloads stay byte-identical. Null/absence means unreviewed, never 1 PCS.
 if config?'rounding_multiple'and config->'rounding_multiple'<>'null'::jsonb then
  if jsonb_typeof(config->'rounding_multiple')is distinct from 'string'
   or config->>'rounding_multiple'!~'^[1-9][0-9]{0,29}$'then raise exception 'CP7_PROFILE_ROUNDING_MULTIPLE';end if;
 end if;
 -- OW10 additive explicit mode: legacy payloads remain byte-identical.
 if(config?'buffer_mode')is distinct from(config?'service_level')then raise exception 'CP7_PROFILE_BUFFER_MODE';end if;
 if config?'buffer_mode'then
  if jsonb_typeof(config->'buffer_mode')is distinct from'string'or config->>'buffer_mode'not in('DAYS','STATISTICAL')then
   raise exception 'CP7_PROFILE_BUFFER_MODE';end if;
  if config->>'buffer_mode'='STATISTICAL'then
   if config->'buffer_days'is distinct from'null'::jsonb or config->>'mean_mode'is distinct from'OWN_AVAILABLE_HISTORY'
    or jsonb_typeof(config->'service_level')is distinct from'string'or config->>'service_level'not in('0.90','0.95','0.99')then
    raise exception 'CP7_PROFILE_STATISTICAL_BUFFER';end if;
  elsif config->'service_level'is distinct from'null'::jsonb then raise exception 'CP7_PROFILE_DOUBLE_BUFFER';
  elsif config->'buffer_days'='null'::jsonb then raise exception 'CP7_PROFILE_DAYS_BUFFER';end if;
 end if;
 mode:=config->>'mean_mode';
 if mode is null or mode not in('OWN_AVAILABLE_HISTORY','SELECTED_MANUAL')or jsonb_typeof(p_payload->'reason')is distinct from 'string'or reason is null
  or length(reason)not between 1 and 1000 then raise exception 'CP7_PROFILE_CONFIG';end if;
 if jsonb_typeof(config->'minimum_available_days')is distinct from 'string'
  or config->>'minimum_available_days'!~'^[1-9][0-9]{0,3}$'then raise exception 'CP7_PROFILE_MINIMUM_DAYS';end if;
 minimum:=cp7_demand.decimal(config->'minimum_available_days');
 if minimum<>trunc(minimum)or minimum not between 1 and 3660 then raise exception 'CP7_PROFILE_MINIMUM_DAYS';end if;
 if mode='SELECTED_MANUAL'then perform cp7_demand.decimal(config->'daily_pcs');
 elsif config->'daily_pcs'is distinct from 'null'::jsonb then raise exception 'CP7_PROFILE_DOUBLE_MEAN';end if;
 foreach k in array array['lead_days','review_days','buffer_days']loop
  if config->k is distinct from 'null'::jsonb then
   if cp7_demand.decimal(config->k)>3660 then raise exception 'CP7_PROFILE_DAY_LIMIT';end if;
  end if;
 end loop;
 if config->'lead_days'<>'null'::jsonb and config->'review_days'<>'null'::jsonb then
  lead:=cp7_demand.decimal(config->'lead_days');review:=cp7_demand.decimal(config->'review_days');
  if lead+review<=0 or lead+review>3660 then raise exception 'CP7_PROFILE_HORIZON';end if;
 end if;
 insert into cp7_profile.profiles(root_id,product_version_id,size_id,revision,config,reason,actor,request_id)
 values(sid,pid,sz,current_revision+1,config,reason,auth.uid(),p_request)returning *into p;
 if cp7_identity.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_PROFILE_ACCESS_CHANGED';end if;
 if cp7_profile.source(array[sid],clock_timestamp())->0->>'product_version_id'<>pid::text then raise exception 'CP7_PROFILE_SOURCE_CHANGED';end if;
 outcome:=jsonb_build_object('contract_version','cp7.planning-profile-outcome.v1','request_id',p_request,
  'profile_id',p.id,'root_id',sid,'revision',p.revision::text,'quality','SELECTED_ASSUMPTION');
 insert into cp7_profile.commands(actor,request_id,payload,result)values(auth.uid(),p_request,p_payload,outcome);
 return outcome;
end $$;
