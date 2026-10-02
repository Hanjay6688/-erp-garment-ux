-- Native cutting observations. Pickup/output stages never create new slices.
-- Source lengths and yields remain decimal strings in their actual Native unit.
create schema cp7_cutting_yield authorization cp7_capture;
revoke all on schema cp7_cutting_yield from public,anon,authenticated,service_role;
grant select(id,material_id)on erp.material_rolls to cp7_capture;
grant select(id,material_sku,unit_code)on erp.materials to cp7_capture;
create table cp7_cutting_yield.runs(
 id uuid primary key default gen_random_uuid(),actor uuid not null,request_id uuid not null,
 query jsonb not null,captured_at timestamptz not null,access_at_capture jsonb not null,
 source jsonb not null,source_hash text not null,engine_hash text not null,result jsonb not null,
 unique(actor,request_id)
);
alter table cp7_cutting_yield.runs owner to cp7_capture;
alter table cp7_cutting_yield.runs enable row level security;
create policy cutting_yield_private on cp7_cutting_yield.runs for all to public using(false)with check(false);
revoke all on cp7_cutting_yield.runs from public,anon,authenticated,service_role;
create trigger cutting_yield_original_immutable before update or delete on cp7_cutting_yield.runs
 for each row execute function cp7_private.immutable_run();

create function cp7_cutting_yield.engine_hash()returns text
language sql stable security invoker set search_path=''as $$
 select encode(extensions.digest(convert_to(string_agg(pg_get_functiondef(p.oid),E'\n'
  order by p.oid::regprocedure::text),'UTF8'),'sha256'),'hex')
 from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_cutting_yield'
$$;

create function cp7_cutting_yield.access_now()returns jsonb
language plpgsql stable security invoker set search_path=''as $$
declare a jsonb;
begin
 a:=cp7_private.access_now();
 if coalesce(a->'profile'->>'role_code','')not in('OWNER','ADMIN')
  or erp.has_permission('production.cutting.view')is distinct from true then
  raise exception using errcode='42501',message='CP7_CUTTING_YIELD_ACCESS_DENIED';end if;
 return a;
end $$;

create function cp7_cutting_yield.query(q jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''as $$
declare ids uuid[];value jsonb;
begin
 perform cp7_wip.fields(q,array['group_ids']);
 if jsonb_typeof(q->'group_ids')is distinct from'array'or jsonb_array_length(q->'group_ids')not between 1 and 50 then
  raise exception 'CP7_CUTTING_YIELD_QUERY';end if;
 for value in select x from jsonb_array_elements(q->'group_ids')x loop
  if jsonb_typeof(value)is distinct from'string'or(value#>>'{}')!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'then
   raise exception 'CP7_CUTTING_YIELD_QUERY';end if;
 end loop;
 select array_agg(id order by id)into ids from(select distinct(x#>>'{}')::uuid id from jsonb_array_elements(q->'group_ids')x)a;
 if cardinality(ids)<>jsonb_array_length(q->'group_ids')then raise exception 'CP7_CUTTING_YIELD_DUPLICATE';end if;
 return jsonb_build_object('group_ids',to_jsonb(ids));
end $$;

create function cp7_cutting_yield.source(q jsonb)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 with groups as materialized(
  select g.id,g.po_id,g.row_version::text revision,g.cut_at,g.created_at,g.material_issue_posted,
   g.pattern_id,g.pattern_revision_snapshot
  from erp.cutting_groups g where g.id in(select(x#>>'{}')::uuid from jsonb_array_elements(q->'group_ids')x)
 ),slices as(
  select r.id slice_id,g.id group_id,g.po_id,g.revision,g.cut_at,g.created_at,g.material_issue_posted,
   g.pattern_id,g.pattern_revision_snapshot,r.roll_id,roll.material_id,m.material_sku,m.unit_code,
   r.qty_issued::text issued_native,r.qty_consumed::text consumed_native,
   r.qty_reported_remaining::text calculated_remaining_native,
   (select coalesce(jsonb_agg(jsonb_build_object('yield_id',y.id,'size_id',s.size_id,'qty_pcs',y.qty_pcs::text)
     order by s.size_id,y.id),'[]')from erp.cutting_roll_yields y
     join erp.cutting_group_size_slots s on s.id=y.size_slot_id where y.cutting_group_roll_id=r.id)outputs
  from groups g join erp.cutting_group_rolls r on r.cutting_group_id=g.id
  join erp.material_rolls roll on roll.id=r.roll_id join erp.materials m on m.id=roll.material_id
 )select jsonb_build_object('requested_group_count',jsonb_array_length(q->'group_ids'),
  'found_group_count',(select count(*)from groups),'slices',coalesce(jsonb_agg(to_jsonb(s)order by slice_id),'[]'))
 from slices s
$$;

create function cp7_cutting_yield.build(s jsonb,at timestamptz)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare slice jsonb;rows jsonb:='[]';observed jsonb;reason text;count bigint;
begin
 if s->'requested_group_count'is distinct from s->'found_group_count'then raise exception 'CP7_CUTTING_YIELD_GROUP_UNAVAILABLE';end if;
 if jsonb_array_length(s->'slices')>1000 then raise exception 'CP7_CUTTING_YIELD_SCOPE_LIMIT';end if;
 for slice in select x from jsonb_array_elements(s->'slices')x loop
  select sum((x->>'qty_pcs')::bigint)into count from jsonb_array_elements(slice->'outputs')x;
  reason:=case when slice->'material_issue_posted'is distinct from'true'::jsonb then'NATIVE_CUTTING_NOT_POSTED'
   when slice->>'consumed_native'is null or(slice->>'consumed_native')::numeric<=0 or count is null or count<=0 then'NATIVE_OUTPUT_OR_CONSUMPTION_INCOMPLETE'
   else'PROSPECTIVE_FAMILY_MIX_AND_VALIDATED_INTERVAL_REQUIRED'end;
  observed:=case when reason='PROSPECTIVE_FAMILY_MIX_AND_VALIDATED_INTERVAL_REQUIRED'then jsonb_build_object(
   'consumed',slice->>'consumed_native','unit',slice->>'unit_code','total_pcs',count::text,'by_size',slice->'outputs')else'null'::jsonb end;
  rows:=rows||jsonb_build_array(jsonb_build_object('slice_id',slice->'slice_id','group_id',slice->'group_id',
   'roll_id',slice->'roll_id','material_id',slice->'material_id','material_sku',slice->>'material_sku',
   'pattern_id',slice->'pattern_id','pattern_revision',slice->'pattern_revision_snapshot',
   'physical_at',slice->'cut_at','known_at',cp7_planning.utc(at),
   'actual',observed,'family',null,'planned_mix',null,'recorded_width_cm',null,'measured_remaining',null,
   'interval',null,'assessment','UNAVAILABLE','reason',reason,
   'calculated_remaining_is_not_physical_measurement',true,
   'output_mix_is_not_preknown_planned_mix',true,'later_laundry_BS_is_not_cutting_cause',true));
 end loop;
 return jsonb_build_object('contract_version','cp7.native-cutting-yield-source.v1',
  'rows',rows,'knowledge_basis','CURRENT_CAPTURE_ONLY','model_qualified',false,
  'automatic_activation',false,'business_write',false,'production_go',false);
end $$;

create function cp7_cutting_yield.serve(p_run uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;r cp7_cutting_yield.runs%rowtype;fresh jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_cutting_yield.access_now();select *into r from cp7_cutting_yield.runs where id=p_run and actor=(a->>'actor')::uuid;
 if r.id is null then raise exception using errcode='42501',message='CP7_CUTTING_YIELD_ORIGINAL_UNAVAILABLE';end if;
 fresh:=cp7_cutting_yield.source(r.query);
 if cp7_cutting_yield.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_CUTTING_YIELD_ACCESS_CHANGED';end if;
 return r.result||jsonb_build_object('run_id',r.id,'request_id',r.request_id,'source_hash',r.source_hash,
  'captured_at',cp7_planning.utc(r.captured_at),'source_state',
   case when fresh=r.source and cp7_cutting_yield.engine_hash()=r.engine_hash then'UNCHANGED'else'ARCHIVED_STALE'end);
end $$;

create function cp7_cutting_yield.capture(p_query jsonb,p_request uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;q jsonb;r cp7_cutting_yield.runs%rowtype;at timestamptz;source jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_cutting_yield.access_now();q:=cp7_cutting_yield.query(p_query);
 if p_request is null then raise exception 'CP7_CUTTING_YIELD_REQUEST_REQUIRED';end if;
 perform pg_advisory_xact_lock(hashtextextended('CP7:CUTTING_YIELD:'||auth.uid()::text||':'||p_request::text,0));
 if cp7_cutting_yield.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_CUTTING_YIELD_ACCESS_CHANGED';end if;
 select *into r from cp7_cutting_yield.runs where actor=(a->>'actor')::uuid and request_id=p_request;
 if found then
  if r.query<>q then raise exception 'CP7_CUTTING_YIELD_REQUEST_CHANGED';end if;return cp7_cutting_yield.serve(r.id);end if;
 at:=clock_timestamp();source:=cp7_cutting_yield.source(q);
 insert into cp7_cutting_yield.runs(actor,request_id,query,captured_at,access_at_capture,source,source_hash,engine_hash,result)
 values((a->>'actor')::uuid,p_request,q,at,a,source,
  encode(extensions.digest(convert_to(source::text,'UTF8'),'sha256'),'hex'),
  cp7_cutting_yield.engine_hash(),cp7_cutting_yield.build(source,at))returning *into r;
 if cp7_cutting_yield.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_CUTTING_YIELD_ACCESS_CHANGED';end if;
 return cp7_cutting_yield.serve(r.id);
end $$;

create function public.erp_cp7_capture_cutting_yield_v1(p_query jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_cutting_yield.capture(p_query,p_request)$$;
create function public.erp_cp7_read_cutting_yield_v1(p_run uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_cutting_yield.serve(p_run)$$;

alter function cp7_cutting_yield.access_now()owner to cp7_capture;
alter function cp7_cutting_yield.engine_hash()owner to cp7_capture;
alter function cp7_cutting_yield.query(jsonb)owner to cp7_capture;
alter function cp7_cutting_yield.source(jsonb)owner to cp7_capture;
alter function cp7_cutting_yield.build(jsonb,timestamptz)owner to cp7_capture;
alter function cp7_cutting_yield.serve(uuid)owner to cp7_capture;
alter function cp7_cutting_yield.capture(jsonb,uuid)owner to cp7_capture;
alter function public.erp_cp7_capture_cutting_yield_v1(jsonb,uuid)owner to cp7_capture;
alter function public.erp_cp7_read_cutting_yield_v1(uuid)owner to cp7_capture;
revoke all on all functions in schema cp7_cutting_yield from public,anon,authenticated,service_role;
revoke all on function public.erp_cp7_capture_cutting_yield_v1(jsonb,uuid),public.erp_cp7_read_cutting_yield_v1(uuid)from public,anon,service_role;
grant execute on function public.erp_cp7_capture_cutting_yield_v1(jsonb,uuid),public.erp_cp7_read_cutting_yield_v1(uuid)to authenticated;
