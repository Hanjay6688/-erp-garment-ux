create function cp7_identity.apply_policy(p_changes jsonb,p_request uuid) returns jsonb
language plpgsql volatile security invoker set search_path='' set timezone='Asia/Jakarta' as $$
declare a jsonb; v_actor uuid; hash text; old cp7_identity.commands%rowtype;
 change jsonb; member jsonb; at timestamptz; sid uuid; members uuid[]; expected bigint;
 current_revision bigint; state text; reason text; review timestamptz; applied jsonb:='[]';
 row cp7_identity.production_policy%rowtype; result jsonb; seen uuid[]:='{}';
begin
 if current_setting('transaction_isolation')<>'read committed' then
  raise exception using errcode='25001',message='CP7_FRESH_ACCESS_TRANSACTION_REQUIRED';
 end if;
 a:=cp7_identity.access_now(true);v_actor:=auth.uid();
 if p_request is null or p_changes is null or jsonb_typeof(p_changes)<>'array' then
  raise exception using errcode='22023',message='CP7_POLICY_REQUEST_INVALID';
 end if;
 if jsonb_array_length(p_changes) not between 1 and 100 then
  raise exception using errcode='22023',message='CP7_POLICY_REQUEST_INVALID';
 end if;
 hash:=encode(extensions.digest(convert_to(p_changes::text,'UTF8'),'sha256'),'hex');
 perform pg_advisory_xact_lock(hashtextextended('CP7_POLICY_REQUEST:'||v_actor::text||':'||p_request::text,0));
 -- Recheck before a cached outcome and again after the commercial lock.
 if cp7_identity.access_now(true)<>a then
  raise exception using errcode='42501',message='CP7_POLICY_ACCESS_CHANGED';
 end if;
 select * into old from cp7_identity.commands where commands.actor=v_actor and request_id=p_request;
 if found then
  if old.payload_hash<>hash then raise exception using errcode='22023',message='CP7_POLICY_REQUEST_REUSED';end if;
  if cp7_identity.access_now(true)<>a then
   raise exception using errcode='42501',message='CP7_POLICY_ACCESS_CHANGED';
  end if;
  return old.result||jsonb_build_object('replayed',true);
 end if;
 perform pg_advisory_xact_lock(hashtextextended('BF:COMMERCIAL_SKUS',0));
 if cp7_identity.access_now(true)<>a then
  raise exception using errcode='42501',message='CP7_POLICY_ACCESS_CHANGED';
 end if;
 at:=clock_timestamp();
 for change in select value from jsonb_array_elements(p_changes) loop
  if jsonb_typeof(change)<>'object' or (select array_agg(k order by k) from jsonb_object_keys(change) k)
   is distinct from array['commercial_revision','commercial_version_id','members','policy_revision','reason','review_at','sku_id','state']::text[] then
   raise exception using errcode='22023',message='CP7_POLICY_FIELDS_INVALID';
  end if;
  if exists(select 1 from unnest(array['sku_id','commercial_version_id','commercial_revision','policy_revision','state','reason']) k
   where jsonb_typeof(change->k) is distinct from 'string')
   or jsonb_typeof(change->'review_at') not in ('null','string') then
   raise exception using errcode='22023',message='CP7_POLICY_FIELDS_INVALID';
  end if;
  sid:=(change->>'sku_id')::uuid;
  if sid is null or sid=any(seen) then raise exception using errcode='22023',message='CP7_POLICY_DUPLICATE_SCOPE';end if;
  seen:=array_append(seen,sid);
  if jsonb_typeof(change->'members')<>'array' or jsonb_array_length(change->'members') not between 1 and 500 then
   raise exception using errcode='22023',message='CP7_POLICY_MEMBERS_INVALID';
  end if;
  select array_agg(value::uuid order by value::uuid) into members from jsonb_array_elements_text(change->'members');
  if (select count(distinct m) from unnest(members) m)<>cardinality(members) then
   raise exception using errcode='22023',message='CP7_POLICY_MEMBERS_INVALID';
  end if;
  if coalesce(change->>'commercial_revision','')!~'^(0|[1-9][0-9]*)$'
     or coalesce(change->>'policy_revision','')!~'^(0|[1-9][0-9]*)$' then
   raise exception using errcode='22023',message='CP7_POLICY_REVISION_INVALID';
  end if;
  member:=cp7_identity.membership(sid,at);
  if member is null or member->>'commercial_version_id' is distinct from change->>'commercial_version_id'
     or member->>'commercial_revision' is distinct from change->>'commercial_revision'
     or member->'members' is distinct from to_jsonb(members) then
   raise exception using errcode='40001',message='CP7_POLICY_MEMBERSHIP_STALE';
  end if;
  expected:=(change->>'policy_revision')::bigint;
  select coalesce(max(revision),0) into current_revision from cp7_identity.production_policy where sku_id=sid;
  if current_revision<>expected then raise exception using errcode='40001',message='CP7_POLICY_VERSION_STALE';end if;
  state:=change->>'state';reason:=btrim(change->>'reason');review:=(change->>'review_at')::timestamptz;
  if (review is not null and not isfinite(review)) or state is null or state not in ('ACTIVE','PAUSED','STOPPED') or reason is null or length(reason) not between 1 and 1000 then
   raise exception using errcode='22023',message='CP7_POLICY_VALUE_INVALID';
  end if;
  insert into cp7_identity.production_policy(sku_id,revision,state,reason,review_at,actor,request_id,
   reviewed_commercial_version,reviewed_commercial_revision,reviewed_members,recorded_at)
  values(sid,current_revision+1,state,reason,review,v_actor,p_request,
   (member->>'commercial_version_id')::uuid,(member->>'commercial_revision')::bigint,members,at) returning * into row;
  applied:=applied||jsonb_build_array(jsonb_build_object('sku_id',sid,'revision',row.revision::text,'state',row.state,'policy_id',row.id));
 end loop;
 if cp7_identity.access_now(true)<>a then
  raise exception using errcode='42501',message='CP7_POLICY_ACCESS_CHANGED';
 end if;
 result:=jsonb_build_object('contract_version','cp7.production-policy-outcome.v1','kind','COMMITTED_OUTCOME',
  'request_id',p_request,'recorded_at',at,'applied',applied,'replayed',false);
 insert into cp7_identity.commands(actor,request_id,payload_hash,result) values(v_actor,p_request,hash,result);
 return result;
end $$;

create function public.erp_cp7_get_production_policy_v1(p_skus uuid[]) returns jsonb
language sql volatile security definer set search_path='' as $$select cp7_identity.workspace(p_skus)$$;
create function public.erp_cp7_set_production_policy_v1(p_changes jsonb,p_request uuid) returns jsonb
language sql volatile security definer set search_path='' as $$select cp7_identity.apply_policy(p_changes,p_request)$$;
grant create on schema public to cp7_capture,cp7_policy;
alter function public.erp_cp7_get_production_policy_v1(uuid[]) owner to cp7_capture;
alter function public.erp_cp7_set_production_policy_v1(jsonb,uuid) owner to cp7_policy;
revoke create on schema public from cp7_capture,cp7_policy;
revoke all on all functions in schema cp7_identity from public,anon,authenticated,service_role,cp7_capture,cp7_policy;
grant execute on function cp7_identity.access_now(boolean),cp7_identity.membership(uuid,timestamptz),
 cp7_identity.workspace_data(uuid[],timestamptz),cp7_identity.workspace(uuid[]) to cp7_capture;
grant execute on function cp7_identity.access_now(boolean),cp7_identity.membership(uuid,timestamptz),
 cp7_identity.apply_policy(jsonb,uuid) to cp7_policy;
revoke all on function public.erp_cp7_get_production_policy_v1(uuid[]),public.erp_cp7_set_production_policy_v1(jsonb,uuid)
 from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_get_production_policy_v1(uuid[]),public.erp_cp7_set_production_policy_v1(jsonb,uuid) to authenticated;
