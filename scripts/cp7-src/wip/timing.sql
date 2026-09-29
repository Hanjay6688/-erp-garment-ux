-- Explicit remaining work and working intervals only. Missing timing stays unknown.
-- This computes one source's earliest working-calendar finish, not a capacity promise.
create function cp7_wip.remaining_eta(p_ready timestamptz, p_deadline timestamptz, work jsonb) returns jsonb
language plpgsql immutable security invoker set search_path='' set timezone='UTC' as $$
declare st jsonb; slot jsonb; ready timestamptz:=p_ready; starts timestamptz; ends timestamptz;
 last_end timestamptz; minutes numeric; available numeric; used numeric; assumptions jsonb:='[]';
 stages jsonb:='[]'; seen jsonb:='{}'; k text; uncertain boolean:=false;
begin
 if p_ready is null or not isfinite(p_ready) or p_deadline is null or not isfinite(p_deadline)
  or jsonb_typeof(work) is distinct from 'array' or jsonb_array_length(work)>20 then raise exception 'CP7_WIP_TIMING_SHAPE';end if;
 for st in select value from jsonb_array_elements(work) loop
  perform cp7_wip.fields(st,array['stage','remaining_minutes','basis','assumption_id','calendar_version','windows','refs']);
  k:=cp7_wip.key(st->'stage');perform cp7_wip.refs(st->'refs');
  if seen ? k or st->>'basis' is null or st->>'basis' not in ('CONFIRMED_PLAN','HISTORY','ASSUMED','UNKNOWN') then raise exception 'CP7_WIP_TIMING_STAGE';end if;
  seen:=seen||jsonb_build_object(k,true);
  if st->>'basis'='UNKNOWN' or st->'remaining_minutes'='null'::jsonb or st->'calendar_version'='null'::jsonb or st->'windows'='null'::jsonb then
   return jsonb_build_object('status','UNKNOWN','eta',null,'on_time',null,'reason','REMAINING_STAGE_OR_CALENDAR_UNKNOWN','stage',k);
  end if;
  perform cp7_wip.key(st->'calendar_version');minutes:=cp7_wip.pcs(st->'remaining_minutes');
  if st->>'basis'='ASSUMED' then
   perform cp7_wip.key(st->'assumption_id');assumptions:=assumptions||jsonb_build_array(st->'assumption_id');
  elsif st->'assumption_id'<>'null'::jsonb then raise exception 'CP7_WIP_TIMING_ASSUMPTION';end if;
  uncertain:=uncertain or st->>'basis'<>'CONFIRMED_PLAN';
  if jsonb_typeof(st->'windows') is distinct from 'array' or jsonb_array_length(st->'windows')>1000 then raise exception 'CP7_WIP_TIMING_WINDOWS';end if;
  last_end:=null;
  for slot in select value from jsonb_array_elements(st->'windows') loop
   perform cp7_wip.fields(slot,array['start','end']);
   if jsonb_typeof(slot->'start') is distinct from 'string' or jsonb_typeof(slot->'end') is distinct from 'string'
     or (slot->>'start') !~ '(Z|[+-][0-9]{2}:[0-9]{2})$' or (slot->>'end') !~ '(Z|[+-][0-9]{2}:[0-9]{2})$' then raise exception 'CP7_WIP_TIMING_ZONE';end if;
   starts:=(slot->>'start')::timestamptz;ends:=(slot->>'end')::timestamptz;
   if not isfinite(starts) or not isfinite(ends) or starts>=ends or (last_end is not null and starts<last_end) then raise exception 'CP7_WIP_TIMING_OVERLAP';end if;
   last_end:=ends;
   if minutes>0 and ends>ready then
    starts:=greatest(starts,ready);available:=extract(epoch from ends-starts)/60;
    used:=least(available,minutes);ready:=starts+(used::text||' minutes')::interval;minutes:=minutes-used;
   end if;
  end loop;
  if minutes>0 then return jsonb_build_object('status','UNKNOWN','eta',null,'on_time',null,'reason','CALENDAR_HORIZON_EXHAUSTED','stage',k);end if;
  stages:=stages||jsonb_build_array(jsonb_build_object('stage',k,'eta',ready,'calendar_version',st->'calendar_version','basis',st->'basis','refs',st->'refs'));
 end loop;
 return jsonb_build_object('status',case when uncertain then 'CONDITIONAL' else 'KNOWN' end,'eta',ready,
  'on_time',ready<=p_deadline,'assumption_ids',assumptions,'remaining_stages',stages,
  'basis','WORKING_CALENDAR_ONLY_CAPACITY_CHECK_REQUIRED');
end $$;
