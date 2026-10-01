-- Saved episode history only. Native complete current domain scope authorizes
-- the source; no balance, forecast, stock, HPP or monitoring write is added.
create function cp7_reminder_native.obligation_history(p jsonb)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
#variable_conflict use_variable
declare a jsonb;again jsonb;source jsonb;domain text;source_id uuid;source_label text;
 before_number bigint;through_number bigint;latest_number bigint;page_limit integer;
 total bigint;items jsonb;next_before text;access_payload jsonb;
begin
 if jsonb_typeof(p)is distinct from'object'or not p?&array['run_id','domain','source_id','before_episode','through_episode','limit']
  or(select count(*)from jsonb_object_keys(p))<>6
  or jsonb_typeof(p->'source_id')is distinct from'string'
  or p->>'source_id'!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or jsonb_typeof(p->'limit')is distinct from'number'or p->>'limit'!~'^[1-9][0-9]?$'
  or(p->>'limit')::integer not between 1 and 50
  or jsonb_typeof(p->'before_episode')not in('string','null')
  or jsonb_typeof(p->'through_episode')not in('string','null')
  or (p->>'before_episode'is null)<>(p->>'through_episode'is null)
  or p->>'before_episode'is not null and (p->>'before_episode'!~'^[1-9][0-9]{0,18}$'or p->>'through_episode'!~'^[1-9][0-9]{0,18}$')
 then raise exception 'CP7_OBLIGATION_HISTORY_PAYLOAD';end if;
 domain:=p->>'domain';source_id:=(p->>'source_id')::uuid;page_limit:=(p->>'limit')::integer;
 access_payload:=jsonb_build_object('run_id',p->'run_id','domain',p->'domain');
 a:=cp7_reminder_native.obligation_access(access_payload);
 source:=case domain when'AR'then cp7_reminder_native.receivable_source()else cp7_reminder_native.payable_source()end;
 if domain='AR'then
  select h.value->>'number'into source_label from jsonb_array_elements(source->'pages')s(value)
   cross join lateral jsonb_array_elements(s.value->'page'->'rows')h(value)where h.value->>'id'=source_id::text;
 else
  select r.value->'liability'->>'purchase_number'into source_label from jsonb_array_elements(source->'rows')r(value)
   where r.value->'liability'->>'purchase_id'=source_id::text;
 end if;
 if source_label is null then raise exception using errcode='42501',message='CP7_OBLIGATION_HISTORY_SOURCE_UNAVAILABLE';end if;
 select coalesce(max(e.episode_number),0)into latest_number from cp7_reminder_native.obligation_episodes e where e.domain=domain and e.source_id=source_id;
 if p->>'before_episode'is not null and ((p->>'before_episode')::numeric>9223372036854775807 or (p->>'through_episode')::numeric>9223372036854775807)then raise exception 'CP7_OBLIGATION_HISTORY_CURSOR';end if;
 before_number:=(p->>'before_episode')::bigint;through_number:=coalesce((p->>'through_episode')::bigint,latest_number);
 if through_number>latest_number or before_number is not null and (before_number::numeric>through_number::numeric+1)
 then raise exception 'CP7_OBLIGATION_HISTORY_CURSOR';end if;
 with all_rows as(
  select e.*from cp7_reminder_native.obligation_episodes e where e.domain=domain and e.source_id=source_id and e.episode_number<=through_number),
 page_rows as(select *from all_rows e where before_number is null or e.episode_number<before_number order by e.episode_number desc limit page_limit)
 select(select count(*)from all_rows),coalesce(jsonb_agg(jsonb_build_object(
  'source_label',e.source_label,'condition_state',e.condition_state,'reason',e.reason,'source_revision',e.source_revision,'native_source_hash',e.native_source_hash,
  'episode',jsonb_build_object('id',e.id,'number',e.episode_number::text,'previous_episode_id',e.previous_episode_id,'state',e.state,'freshness',e.freshness,
   'first_observed_at',e.first_observed_at,'last_observed_at',e.last_observed_at,'last_known_observed_at',e.last_known_observed_at,'closed_at',e.closed_at,'revision',e.revision::text))
  order by e.episode_number desc),'[]'::jsonb),
 case when exists(select 1 from all_rows old where old.episode_number<(select min(w.episode_number)from page_rows w))
  then(select min(w.episode_number)::text from page_rows w)else null end
 into total,items,next_before from page_rows e;
 if total>10000 then raise exception 'CP7_OBLIGATION_HISTORY_SCOPE_INCOMPLETE';end if;
 again:=cp7_reminder_native.obligation_access(access_payload);
 if again->'access'is distinct from a->'access'then raise exception using errcode='42501',message='CP7_OBLIGATION_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.native-obligation-history.v1','actor_scope_id',auth.uid(),'analysis',again->'analysis',
  'read_kind','SAVED_EPISODE_HISTORY','domain',domain,'source_id',source_id,'source_label',source_label,
  'source_scope_hash',source->'source_hash','source_scope_read_at',source->'read_at','through_episode',through_number::text,
  'before_episode',before_number::text,'limit',page_limit,'total',total::text,'rows',items,'next_before_episode',next_before,'page_complete',true,'read_at',clock_timestamp());
end $$;
alter function cp7_reminder_native.obligation_history(jsonb)owner to cp7_reminder;
revoke all on function cp7_reminder_native.obligation_history(jsonb)from public,anon,authenticated,service_role;
grant create on schema public to cp7_reminder;
create function public.erp_cp7_get_obligation_episode_history_v1(p_payload jsonb)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_reminder_native.obligation_history(p_payload)$$;
alter function public.erp_cp7_get_obligation_episode_history_v1(jsonb)owner to cp7_reminder;
revoke create on schema public from cp7_reminder;
revoke all on function public.erp_cp7_get_obligation_episode_history_v1(jsonb)from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_get_obligation_episode_history_v1(jsonb)to authenticated;
