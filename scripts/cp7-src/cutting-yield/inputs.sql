-- Prospective operator input candidate. This file is not installed until its
-- Native adapter/consumer controls are qualified. It writes private metadata
-- only; every physical identity, unit and revision is read from Native ERP.
create schema cp7_cutting_inputs authorization cp7_capture;
revoke all on schema cp7_cutting_inputs from public,anon,authenticated,service_role;
grant select(id,size_code)on erp.sizes to cp7_capture;

create table cp7_cutting_inputs.plans(
 id uuid primary key default gen_random_uuid(),actor uuid not null,group_id uuid not null,
 version bigint not null check(version>0),previous_id uuid references cp7_cutting_inputs.plans(id),
 request_id uuid not null,known_at timestamptz not null,access_at_capture jsonb not null,
 payload jsonb not null,native_source jsonb not null,native_anchor jsonb not null,
 features jsonb not null,unique(actor,request_id),unique(actor,group_id,version));
create table cp7_cutting_inputs.requests(
 actor uuid not null,request_id uuid not null,payload jsonb not null,result jsonb not null,
 recorded_at timestamptz not null,primary key(actor,request_id));
alter table cp7_cutting_inputs.plans owner to cp7_capture;
alter table cp7_cutting_inputs.requests owner to cp7_capture;
alter table cp7_cutting_inputs.plans enable row level security;
alter table cp7_cutting_inputs.requests enable row level security;
create policy cutting_inputs_no_access on cp7_cutting_inputs.plans for all to public using(false)with check(false);
create policy cutting_requests_no_access on cp7_cutting_inputs.requests for all to public using(false)with check(false);
revoke all on cp7_cutting_inputs.plans,cp7_cutting_inputs.requests from public,anon,authenticated,service_role;
create trigger cutting_plan_immutable before update or delete on cp7_cutting_inputs.plans
 for each row execute function cp7_private.immutable_run();
create trigger cutting_input_request_immutable before update or delete on cp7_cutting_inputs.requests
 for each row execute function cp7_private.immutable_run();

create function cp7_cutting_inputs.access_now(writing boolean default false)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_cutting_yield.access_now();
 if writing and erp.has_permission('production.cutting.edit_draft')is distinct from true then
  raise exception using errcode='42501',message='CP7_CUTTING_INPUT_WRITE_DENIED';end if;
 return a;
end $$;

create function cp7_cutting_inputs.source(group_id uuid)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select jsonb_build_object('group',jsonb_build_object('id',g.id,'po_id',g.po_id,'version',g.row_version::text,
  'physical_at',cp7_planning.utc(g.cut_at),'posted',g.material_issue_posted,
  'pattern_id',g.pattern_id,'pattern_revision',g.pattern_revision_snapshot),
  'cutting',cp7_cutting_yield.source(jsonb_build_object('group_ids',jsonb_build_array(g.id))),
  'size_labels',(select coalesce(jsonb_object_agg(s.id::text,s.size_code),'{}')from erp.sizes s
   where s.id in(select z.size_id from erp.cutting_group_size_slots z where z.cutting_group_id=g.id)))
 from erp.cutting_groups g where g.id=group_id
$$;

create function cp7_cutting_inputs.anchor(s jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare rolls jsonb;sizes jsonb;
begin
 if s is null or jsonb_typeof(s->'group')is distinct from'object'or jsonb_array_length(s->'cutting'->'slices')not between 1 and 1000 then
  raise exception 'CP7_CUTTING_INPUT_NATIVE_SCOPE';end if;
 if s->'group'->>'pattern_id'is null or s->'group'->>'pattern_revision'is null then
  raise exception 'CP7_CUTTING_INPUT_NATIVE_PATTERN_REQUIRED';end if;
 select jsonb_agg(jsonb_build_object('roll_id',x->'roll_id','material_id',x->'material_id','unit',x->'unit_code')
  order by x->>'roll_id'collate "C")into rolls from jsonb_array_elements(s->'cutting'->'slices')x;
 if exists(select 1 from jsonb_array_elements(rolls)x group by x->>'roll_id'having count(*)<>1)then
  raise exception 'CP7_CUTTING_INPUT_DUPLICATE_NATIVE_ROLL';end if;
 select coalesce(jsonb_agg(to_jsonb(size_id)order by size_id collate "C"),'[]')into sizes
 from jsonb_object_keys(s->'size_labels')size_id;
 if jsonb_array_length(sizes)not between 1 and 1000 then raise exception 'CP7_CUTTING_INPUT_NATIVE_SIZE_SCOPE';end if;
 return jsonb_build_object('group_id',s->'group'->'id','po_id',s->'group'->'po_id',
  'pattern_id',s->'group'->'pattern_id','pattern_revision',s->'group'->'pattern_revision','rolls',rolls,'size_ids',sizes);
end $$;

create function cp7_cutting_inputs.payload(p jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare item jsonb;k text;
begin
 perform cp7_wip.fields(p,array['group_id','expected_group_version','expected_input_version','marker_key','planned_mix','roll_inputs','explicit_review']);
 if not(p?&array['group_id','expected_group_version','expected_input_version','marker_key','planned_mix','roll_inputs','explicit_review'])
  or p->'explicit_review'is distinct from'true'::jsonb or jsonb_typeof(p->'group_id')is distinct from'string'
  or(p->>'group_id')!~*'^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$'
  or jsonb_typeof(p->'expected_group_version')is distinct from'string'or(p->>'expected_group_version')!~'^[1-9][0-9]{0,18}$'
  or(p->>'expected_group_version')::numeric>9223372036854775807
  or p->'expected_input_version'<>'null'::jsonb and(jsonb_typeof(p->'expected_input_version')is distinct from'string'
    or(p->>'expected_input_version')!~'^[1-9][0-9]{0,18}$'or(p->>'expected_input_version')::numeric>9223372036854775807)
  or jsonb_typeof(p->'marker_key')is distinct from'string'or length(btrim(p->>'marker_key'))not between 1 and 200
  or jsonb_typeof(p->'roll_inputs')is distinct from'array'or jsonb_array_length(p->'roll_inputs')not between 1 and 1000
  then raise exception 'CP7_CUTTING_INPUT_PAYLOAD';end if;
 perform cp7_cutting_learning.mix(p->'planned_mix');
 for item in select v from jsonb_array_elements(p->'roll_inputs')v loop
  perform cp7_wip.fields(item,array['roll_id','family','width_cm']);
  if not(item?&array['roll_id','family','width_cm'])or jsonb_typeof(item->'roll_id')is distinct from'string'
   or(item->>'roll_id')!~*'^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$'
   or jsonb_typeof(item->'family')is distinct from'object'or not(item->'family'?&array['brand','mill','variant','spec_revision'])
   or(select count(*)from jsonb_object_keys(item->'family'))<>4 then raise exception 'CP7_CUTTING_INPUT_PAYLOAD';end if;
  foreach k in array array['brand','mill','variant','spec_revision']loop
   if jsonb_typeof(item->'family'->k)is distinct from'string'or length(btrim(item->'family'->>k))not between 1 and 200 then
    raise exception 'CP7_CUTTING_INPUT_FAMILY_REQUIRED';end if;
  end loop;
  if cp7_cutting_learning.number(item->'width_cm',true)<=0 then raise exception 'CP7_CUTTING_INPUT_WIDTH';end if;
 end loop;
 if exists(select 1 from jsonb_array_elements(p->'roll_inputs')x group by lower(x->>'roll_id')having count(*)<>1)then
  raise exception 'CP7_CUTTING_INPUT_DUPLICATE_ROLL';end if;
 -- Exact submitted bytes/decimal representation are retained for UUID replay.
 return p;
end $$;

create function cp7_cutting_inputs.build_values(p jsonb,a jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare rows jsonb;mix jsonb;
begin
 mix:=cp7_cutting_learning.mix(p->'planned_mix');
 if exists(select 1 from jsonb_array_elements(mix)x where not(a->'size_ids'?lower(x->>'size_id')))then
  raise exception 'CP7_CUTTING_INPUT_NATIVE_SIZE_MISMATCH';end if;
 if(select jsonb_agg(to_jsonb(lower(x->>'roll_id'))order by lower(x->>'roll_id'))from jsonb_array_elements(p->'roll_inputs')x)
  is distinct from(select jsonb_agg(x->'roll_id'order by x->>'roll_id')from jsonb_array_elements(a->'rolls')x)then
  raise exception 'CP7_CUTTING_INPUT_NATIVE_ROLL_MISMATCH';end if;
 select jsonb_agg(jsonb_build_object('roll_id',n->'roll_id','material_id',n->'material_id','context',
  cp7_cutting_learning.context(jsonb_build_object('family',x->'family','pattern_id',a->>'pattern_id',
   'pattern_revision',a->>'pattern_revision','marker_key',p->>'marker_key','unit',n->>'unit','planned_mix',mix)),
  'width_cm',x->'width_cm','width_basis',case when x->>'width_cm'is null then'UNKNOWN'else'OPERATOR_RECORDED_NOT_INFERRED'end)
  order by n->>'roll_id')into rows
  from jsonb_array_elements(a->'rolls')n join jsonb_array_elements(p->'roll_inputs')x on lower(x->>'roll_id')=n->>'roll_id';
 return jsonb_build_object('rolls',rows,'planned_mix',mix,'provenance','EXPLICIT_OPERATOR_INPUT_BOUND_TO_NATIVE_IDENTITIES',
  'output_mix_is_not_preknown_planned_mix',true,'automatic_activation',false,'business_write',false,'production_go',false);
end $$;

create function cp7_cutting_inputs.record_view(r cp7_cutting_inputs.plans)returns jsonb
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select jsonb_build_object('id',r.id,'actor_scope_id',r.actor,'group_id',r.group_id,'request_id',r.request_id,
  'version',r.version::text,'previous_id',r.previous_id,'known_at',cp7_planning.utc(r.known_at),'values',r.features,
  'native_anchor',r.native_anchor,'original_native_group',r.native_source->'group')
$$;

create function cp7_cutting_inputs.workspace(p_group uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;s jsonb;r cp7_cutting_inputs.plans%rowtype;current_anchor jsonb;
begin
 a:=cp7_cutting_inputs.access_now();s:=cp7_cutting_inputs.source(p_group);
 if s is not null and s->'group'->>'pattern_id'is not null and s->'group'->>'pattern_revision'is not null
  and jsonb_array_length(s->'cutting'->'slices')between 1 and 1000 then current_anchor:=cp7_cutting_inputs.anchor(s);end if;
 select *into r from cp7_cutting_inputs.plans where actor=(a->>'actor')::uuid and group_id=p_group order by version desc limit 1;
 if cp7_cutting_inputs.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_CUTTING_INPUT_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.native-cutting-input-workspace.v1','actor_scope_id',a->'actor',
  'requested_group_id',p_group,
  'size_labels',coalesce(s->'size_labels','{}'),
  'roll_labels',(select coalesce(jsonb_object_agg(x->>'roll_id',x->>'material_sku'),'{}')from jsonb_array_elements(s->'cutting'->'slices')x),
  'group',s->'group','anchor',current_anchor,'record',case when r.id is null then null else cp7_cutting_inputs.record_view(r)end,
  'record_matches_native_identity',r.id is not null and coalesce(r.native_anchor=current_anchor,false),
  'preknown_before_physical',r.id is not null and coalesce(r.known_at<(s->'group'->>'physical_at')::timestamptz,false),
  'can_record',current_anchor is not null and erp.has_permission('production.cutting.edit_draft')is true,
  'model_qualified',false,'automatic_activation',false,'business_write',false,'production_go',false);
end $$;

create function cp7_cutting_inputs.command(p_payload jsonb,p_request uuid,p_lookup boolean)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
#variable_conflict use_variable
declare a jsonb;p jsonb;actor uuid;source jsonb;fresh jsonb;anchor jsonb;r cp7_cutting_inputs.plans%rowtype;
 previous cp7_cutting_inputs.plans%rowtype;cached cp7_cutting_inputs.requests%rowtype;result jsonb;at timestamptz;
begin
 a:=cp7_cutting_inputs.access_now(true);actor:=(a->>'actor')::uuid;p:=cp7_cutting_inputs.payload(p_payload);
 if p_request is null or p_lookup is null then raise exception 'CP7_CUTTING_INPUT_REQUEST_REQUIRED';end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7:CUTTING_INPUT_REQUEST:'||actor::text||':'||p_request::text,0));
 if cp7_cutting_inputs.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_CUTTING_INPUT_ACCESS_CHANGED';end if;
 select *into cached from cp7_cutting_inputs.requests where requests.actor=actor and request_id=p_request;
 if cached.request_id is not null then
  if cached.payload<>p then raise exception 'CP7_CUTTING_INPUT_REQUEST_CHANGED';end if;result:=cached.result;
 elsif p_lookup then
  result:=jsonb_build_object('status','NOT_COMMITTED','request_id',p_request,'record',null);
  insert into cp7_cutting_inputs.requests values(actor,p_request,p,result,clock_timestamp());
 else
  perform pg_advisory_xact_lock(hashtextextended('CP7:CUTTING_INPUT_GROUP:'||actor::text||':'||(p->>'group_id'),0));
  if cp7_cutting_inputs.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_CUTTING_INPUT_ACCESS_CHANGED';end if;
  source:=cp7_cutting_inputs.source((p->>'group_id')::uuid);anchor:=cp7_cutting_inputs.anchor(source);
  if source->'group'->>'version'<>p->>'expected_group_version'then raise exception using errcode='40001',message='CP7_CUTTING_INPUT_NATIVE_VERSION_CHANGED';end if;
  select *into previous from cp7_cutting_inputs.plans q where q.actor=actor and q.group_id=(p->>'group_id')::uuid order by version desc limit 1;
  if p->>'expected_input_version'is distinct from previous.version::text then raise exception using errcode='40001',message='CP7_CUTTING_INPUT_VERSION_CHANGED';end if;
  at:=clock_timestamp();
  insert into cp7_cutting_inputs.plans(actor,group_id,version,previous_id,request_id,known_at,access_at_capture,payload,native_source,native_anchor,features)
   values(actor,(p->>'group_id')::uuid,coalesce(previous.version,0)+1,previous.id,p_request,at,a,p,source,anchor,cp7_cutting_inputs.build_values(p,anchor))returning *into r;
  fresh:=cp7_cutting_inputs.source(r.group_id);
  if fresh is distinct from source then raise exception using errcode='40001',message='CP7_CUTTING_INPUT_NATIVE_SOURCE_CHANGED';end if;
  result:=jsonb_build_object('status','COMMITTED','request_id',p_request,'record',cp7_cutting_inputs.record_view(r));
  insert into cp7_cutting_inputs.requests values(actor,p_request,p,result,clock_timestamp());
 end if;
 if cp7_cutting_inputs.access_now(true)is distinct from a then raise exception using errcode='42501',message='CP7_CUTTING_INPUT_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.native-cutting-input-command.v1','result',result,
  'current',cp7_cutting_inputs.workspace((p->>'group_id')::uuid),'business_write',false,'automatic_activation',false,'production_go',false);
end $$;

create function public.erp_cp7_get_cutting_input_workspace_v1(p_group uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_cutting_inputs.workspace(p_group)$$;
create function public.erp_cp7_record_cutting_inputs_v1(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_cutting_inputs.command(p_payload,p_request,false)$$;
create function public.erp_cp7_get_cutting_input_request_v1(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_cutting_inputs.command(p_payload,p_request,true)$$;

alter function cp7_cutting_inputs.access_now(boolean)owner to cp7_capture;
alter function cp7_cutting_inputs.source(uuid)owner to cp7_capture;
alter function cp7_cutting_inputs.anchor(jsonb)owner to cp7_capture;
alter function cp7_cutting_inputs.payload(jsonb)owner to cp7_capture;
alter function cp7_cutting_inputs.build_values(jsonb,jsonb)owner to cp7_capture;
alter function cp7_cutting_inputs.record_view(cp7_cutting_inputs.plans)owner to cp7_capture;
alter function cp7_cutting_inputs.workspace(uuid)owner to cp7_capture;
alter function cp7_cutting_inputs.command(jsonb,uuid,boolean)owner to cp7_capture;
alter function public.erp_cp7_get_cutting_input_workspace_v1(uuid)owner to cp7_capture;
alter function public.erp_cp7_record_cutting_inputs_v1(jsonb,uuid)owner to cp7_capture;
alter function public.erp_cp7_get_cutting_input_request_v1(jsonb,uuid)owner to cp7_capture;
revoke all on all functions in schema cp7_cutting_inputs from public,anon,authenticated,service_role;
revoke all on function public.erp_cp7_get_cutting_input_workspace_v1(uuid),public.erp_cp7_record_cutting_inputs_v1(jsonb,uuid),public.erp_cp7_get_cutting_input_request_v1(jsonb,uuid)from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_get_cutting_input_workspace_v1(uuid),public.erp_cp7_record_cutting_inputs_v1(jsonb,uuid),public.erp_cp7_get_cutting_input_request_v1(jsonb,uuid)to authenticated;
