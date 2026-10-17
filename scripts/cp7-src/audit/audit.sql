-- R3-03 (owner D16-1, "selesain biar gausa sembunyiin"): the Audit Trail screen reads the Native audit log
-- (erp.audit_logs) through one closed, bounded, read-only facade. Access is the access catalog's: settings.audit.view to
-- read; settings.audit.export (answered as can_export) to download the rows shown. Nothing is written: no business DML
-- and no private state.
-- Paging holds while writes commit. The first page fixes a cutoff, as_of = the highest log id visible then; every later
-- page reads only rows with id <= as_of, after a keyset cursor (the last row shown, newest first by changed_at, then id).
-- Log ids come from the Native sequence (erp.audit_logs_id_seq), so a write that starts after the first page always takes
-- a higher id and stays out of that listing; a row never moves between pages, so none is shown twice or skipped. The
-- answer says when newer rows exist (snapshot.newer); "Muat ulang" starts a new listing that includes them.
-- Rows carry only the names of the changed keys; the old and new data are read only in the detail of one id, bounded.
create role cp7_audit_read nologin noinherit nosuperuser nocreatedb nocreaterole noreplication;
create schema cp7_audit authorization cp7_audit_read;
revoke all on schema cp7_audit from public,anon,authenticated,service_role,cp7_capture;
grant usage on schema cp7_audit to postgres;

-- The caller is signed in (Auth role authenticated) with an active app profile holding settings.audit.view.
-- Returns whether the caller may also export (settings.audit.export).
create function cp7_audit.access_now()returns boolean
language plpgsql stable security definer set search_path=''as $$
declare v_access jsonb;
begin
 if auth.uid()is null or auth.jwt()->>'role'is distinct from'authenticated'then
  raise exception using errcode='42501',message='CP7_AUDIT_DENIED';end if;
 v_access:=erp.get_my_access_v1();
 if v_access->'allowed'is distinct from'true'::jsonb or not erp.has_permission('settings.audit.view')then
  raise exception using errcode='42501',message='CP7_AUDIT_DENIED';end if;
 return erp.has_permission('settings.audit.export');
end $$;

-- The object view of a stored data column; anything else (null, array, scalar) has no keys.
create function cp7_audit.object_of(p_value jsonb)returns jsonb
language sql immutable set search_path=''as $$
 select case when jsonb_typeof(p_value)='object'then p_value else'{}'::jsonb end$$;

-- A stored value as display text: a string as itself, any other JSON value as its exact JSON text, absent or null as null.
create function cp7_audit.value_text(p_value jsonb)returns text
language sql immutable set search_path=''as $$
 select case when p_value is null or jsonb_typeof(p_value)='null'then null when jsonb_typeof(p_value)='string'then p_value#>>'{}'
  else p_value::text end$$;

-- The keys whose value differs between the old and the new data (every key of a created or deleted row), in byte order;
-- at most 30 named, with the full count.
create function cp7_audit.changed_keys(p_old jsonb,p_new jsonb)returns jsonb
language sql immutable set search_path=''as $$
 with d as(
  select u.k from(select jsonb_object_keys(cp7_audit.object_of(p_old))k union select jsonb_object_keys(cp7_audit.object_of(p_new)))u
  where(cp7_audit.object_of(p_old)->u.k)is distinct from(cp7_audit.object_of(p_new)->u.k))
 select jsonb_build_object(
  'keys',coalesce((select jsonb_agg(f.k order by f.k collate "C")from(select d.k from d order by d.k collate "C" limit 30)f),'[]'::jsonb),
  'count',(select count(*)from d))$$;

-- The detail of one row's data: per key (byte order, at most 500) the value before and after and whether it changed.
create function cp7_audit.fields(p_old jsonb,p_new jsonb)returns jsonb
language sql immutable set search_path=''as $$
 with k as(select u.k from(select jsonb_object_keys(cp7_audit.object_of(p_old))k union select jsonb_object_keys(cp7_audit.object_of(p_new)))u)
 select jsonb_build_object(
  'rows',coalesce((select jsonb_agg(jsonb_build_object('key',f.k,'before',cp7_audit.value_text(cp7_audit.object_of(p_old)->f.k),
     'after',cp7_audit.value_text(cp7_audit.object_of(p_new)->f.k),
     'changed',(cp7_audit.object_of(p_old)->f.k)is distinct from(cp7_audit.object_of(p_new)->f.k))order by f.k collate "C")
   from(select k.k from k order by k.k collate "C" limit 500)f),'[]'::jsonb),
  'total',(select count(*)from k))$$;

-- One log row as the screen shows it (no data, only the changed keys).
create function cp7_audit.entry(p_log erp.audit_logs,p_actor text)returns jsonb
language sql stable set search_path=''set TimeZone='UTC'as $$
 select jsonb_build_object('id',p_log.id::text,'at',p_log.changed_at,'entity_type',p_log.entity_type,'entity_id',p_log.entity_id::text,
  'action',p_log.action,'actor_id',p_log.changed_by,'actor_name',p_actor,'reason',p_log.change_reason,
  'changed_keys',c.v->'keys','changed_key_count',(c.v->>'count')::integer,
  'has_before',p_log.old_data is not null,'has_after',p_log.new_data is not null)
 from(select cp7_audit.changed_keys(p_log.old_data,p_log.new_data)v)c$$;

create function cp7_audit.workspace(p_query jsonb)returns jsonb
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare
 v_export boolean;v_from date;v_to date;v_lo timestamptz;v_hi timestamptz;v_type text;v_action text;v_actor uuid;v_q text;
 v_id bigint;v_after bigint;v_after_at timestamptz;v_as_of bigint;v_offset integer;v_limit integer;
 v_total bigint;v_before bigint:=0;v_rows jsonb;v_shown integer;v_more boolean;v_next_after text:=null;v_next_offset integer:=null;
 v_newer boolean;v_types jsonb;v_actions jsonb;v_actors jsonb;v_detail jsonb:=null;v_log erp.audit_logs;v_name text;v_bytes bigint;
 v_large boolean;v_fields jsonb;
begin
 v_export:=cp7_audit.access_now();
 -- A closed query: known keys only; text keys string or null; offset and limit plain whole numbers.
 if jsonb_typeof(p_query)is distinct from'object'
  or exists(select 1 from jsonb_object_keys(p_query)x(k)
   where x.k not in('from','to','entity_type','action','actor_id','q','id','after','as_of','offset','limit'))
  or exists(select 1 from jsonb_each(p_query)e where e.key not in('offset','limit')and jsonb_typeof(e.value)not in('string','null'))
  or exists(select 1 from jsonb_each(p_query)e where e.key in('offset','limit')and(jsonb_typeof(e.value)<>'number'or e.value::text!~'^[0-9]{1,7}$'))
  or exists(select 1 from jsonb_each_text(p_query)e where e.value is not null and e.key not in('offset','limit')and(
    (e.key in('from','to')and e.value!~'^[0-9]{4}-[0-9]{2}-[0-9]{2}$')
    or(e.key in('id','after','as_of')and e.value!~'^[0-9]{1,18}$')
    or(e.key='actor_id'and e.value!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
    or(e.key='q'and length(btrim(e.value))>120)
    or(e.key in('entity_type','action')and length(e.value)>100)))then
  raise exception 'CP7_AUDIT_QUERY';end if;
 begin
  v_from:=(p_query->>'from')::date;v_to:=(p_query->>'to')::date;
 exception when others then raise exception 'CP7_AUDIT_QUERY';end;
 if v_from<date'2000-01-01'or v_from>date'2100-12-31'or v_to<date'2000-01-01'or v_to>date'2100-12-31'or v_from>v_to then
  raise exception 'CP7_AUDIT_QUERY';end if;
 -- WIB dates: [from 00:00 WIB, to + 1 day 00:00 WIB).
 v_lo:=v_from::timestamp at time zone'Asia/Jakarta';v_hi:=(v_to+1)::timestamp at time zone'Asia/Jakarta';
 v_type:=nullif(p_query->>'entity_type','');v_action:=nullif(p_query->>'action','');v_actor:=(p_query->>'actor_id')::uuid;
 v_q:=nullif(btrim(coalesce(p_query->>'q','')),'');
 v_id:=(p_query->>'id')::bigint;v_after:=(p_query->>'after')::bigint;
 v_offset:=coalesce((p_query->>'offset')::integer,0);v_limit:=coalesce((p_query->>'limit')::integer,25);
 if v_offset>1000000 or v_limit not between 1 and 100 then raise exception 'CP7_AUDIT_QUERY';end if;
 -- The cutoff of this listing: given by the first page's answer, or the highest id visible now.
 v_as_of:=(p_query->>'as_of')::bigint;
 if v_as_of is null then select coalesce(max(l.id),0)into v_as_of from erp.audit_logs l;end if;
 if v_after is not null then
  select coalesce(l.changed_at,'-infinity'::timestamptz)into v_after_at from erp.audit_logs l where l.id=v_after;
  if not found then raise exception 'CP7_AUDIT_CURSOR_GONE';end if;
 end if;

 select count(*)into v_total from erp.audit_logs l
  where l.id<=v_as_of and(v_lo is null or l.changed_at>=v_lo)and(v_hi is null or l.changed_at<v_hi)
   and(v_type is null or l.entity_type=v_type)and(v_action is null or l.action=v_action)and(v_actor is null or l.changed_by=v_actor)
   and(v_q is null or strpos(lower(coalesce(l.entity_id::text,'')),lower(v_q))>0 or strpos(lower(coalesce(l.change_reason,'')),lower(v_q))>0);
 -- Rows of the earlier pages (newest first, up to and including the cursor row).
 if v_after is not null then
  select count(*)into v_before from erp.audit_logs l
   where l.id<=v_as_of and(v_lo is null or l.changed_at>=v_lo)and(v_hi is null or l.changed_at<v_hi)
    and(v_type is null or l.entity_type=v_type)and(v_action is null or l.action=v_action)and(v_actor is null or l.changed_by=v_actor)
    and(v_q is null or strpos(lower(coalesce(l.entity_id::text,'')),lower(v_q))>0 or strpos(lower(coalesce(l.change_reason,'')),lower(v_q))>0)
    and(coalesce(l.changed_at,'-infinity'::timestamptz),l.id)>=(v_after_at,v_after);
 end if;
 -- This page: one row more than asked tells whether another page follows.
 select coalesce(jsonb_agg(cp7_audit.entry(a,u.full_name)order by p.k_at desc,p.id desc),'[]'::jsonb),count(*)into v_rows,v_shown
  from(select l.id,coalesce(l.changed_at,'-infinity'::timestamptz)k_at from erp.audit_logs l
   where l.id<=v_as_of and(v_lo is null or l.changed_at>=v_lo)and(v_hi is null or l.changed_at<v_hi)
    and(v_type is null or l.entity_type=v_type)and(v_action is null or l.action=v_action)and(v_actor is null or l.changed_by=v_actor)
    and(v_q is null or strpos(lower(coalesce(l.entity_id::text,'')),lower(v_q))>0 or strpos(lower(coalesce(l.change_reason,'')),lower(v_q))>0)
    and(v_after is null or(coalesce(l.changed_at,'-infinity'::timestamptz),l.id)<(v_after_at,v_after))
   order by 2 desc,1 desc limit v_limit+1 offset v_offset)p
  join erp.audit_logs a on a.id=p.id left join erp.app_users u on u.id=a.changed_by;
 v_more:=v_shown>v_limit;
 if v_more then
  v_rows:=v_rows-v_limit;v_next_after:=v_rows->(v_limit-1)->>'id';v_next_offset:=v_offset+v_limit;
 end if;
 select exists(select 1 from erp.audit_logs l
  where l.id>v_as_of and(v_lo is null or l.changed_at>=v_lo)and(v_hi is null or l.changed_at<v_hi)
   and(v_type is null or l.entity_type=v_type)and(v_action is null or l.action=v_action)and(v_actor is null or l.changed_by=v_actor)
   and(v_q is null or strpos(lower(coalesce(l.entity_id::text,'')),lower(v_q))>0 or strpos(lower(coalesce(l.change_reason,'')),lower(v_q))>0))
  into v_newer;
 -- Filter pickers of this listing (each ignores its own filter and the search), at most 200 values each.
 select coalesce(jsonb_agg(t.v order by t.v collate "C"),'[]'::jsonb)into v_types from(
  select d.v from(select distinct l.entity_type v from erp.audit_logs l
   where l.id<=v_as_of and l.entity_type is not null and(v_lo is null or l.changed_at>=v_lo)and(v_hi is null or l.changed_at<v_hi)
    and(v_action is null or l.action=v_action)and(v_actor is null or l.changed_by=v_actor))d
  order by d.v collate "C" limit 200)t;
 select coalesce(jsonb_agg(t.v order by t.v collate "C"),'[]'::jsonb)into v_actions from(
  select d.v from(select distinct l.action v from erp.audit_logs l
   where l.id<=v_as_of and l.action is not null and(v_lo is null or l.changed_at>=v_lo)and(v_hi is null or l.changed_at<v_hi)
    and(v_type is null or l.entity_type=v_type)and(v_actor is null or l.changed_by=v_actor))d
  order by d.v collate "C" limit 200)t;
 select coalesce(jsonb_agg(jsonb_build_object('id',t.id,'name',t.name)order by t.name collate "C" nulls last,t.id),'[]'::jsonb)into v_actors from(
  select d.id,d.name from(select distinct l.changed_by id,u.full_name name from erp.audit_logs l left join erp.app_users u on u.id=l.changed_by
   where l.id<=v_as_of and l.changed_by is not null and(v_lo is null or l.changed_at>=v_lo)and(v_hi is null or l.changed_at<v_hi)
    and(v_type is null or l.entity_type=v_type)and(v_action is null or l.action=v_action))d
  order by d.name collate "C" nulls last,d.id limit 200)t;
 -- The detail of one row: its data per key, refused when the row is gone, withheld when larger than 512 KB.
 if v_id is not null then
  select*into v_log from erp.audit_logs l where l.id=v_id;
  if not found then raise exception 'CP7_AUDIT_NOT_FOUND';end if;
  select u.full_name into v_name from erp.app_users u where u.id=v_log.changed_by;
  v_bytes:=coalesce(octet_length(v_log.old_data::text),0)+coalesce(octet_length(v_log.new_data::text),0);
  v_large:=v_bytes>524288;
  v_fields:=case when v_large then jsonb_build_object('rows','[]'::jsonb,'total',0)else cp7_audit.fields(v_log.old_data,v_log.new_data)end;
  v_detail:=cp7_audit.entry(v_log,v_name)||jsonb_build_object('data_bytes',v_bytes,'too_large',v_large,
   'fields',v_fields->'rows','fields_total',(v_fields->>'total')::integer,
   'raw_before',case when not v_large and jsonb_typeof(v_log.old_data)<>'object'then v_log.old_data::text end,
   'raw_after',case when not v_large and jsonb_typeof(v_log.new_data)<>'object'then v_log.new_data::text end);
 end if;
 return jsonb_build_object('contract_version','cp7.audit-trail.v1','read_at',statement_timestamp(),'business_DML',false,'can_export',v_export,
  'query',jsonb_build_object('from',v_from,'to',v_to,'entity_type',v_type,'action',v_action,'actor_id',v_actor,'q',v_q),
  'snapshot',jsonb_build_object('as_of',v_as_of::text,'newer',v_newer),
  'page',jsonb_build_object('rows',v_rows,'total',v_total::text,'before',v_before::text,'offset',v_offset,'limit',v_limit,
   'after',v_after::text,'next_after',v_next_after,'next_offset',v_next_offset),
  'options',jsonb_build_object('entity_types',v_types,'actions',v_actions,'actors',v_actors),
  'detail',v_detail);
end $$;

create function public.erp_cp7_get_audit_trail_v1(p_query jsonb)returns jsonb
language sql stable security definer set search_path=''as $$select cp7_audit.workspace(p_query)$$;
alter function cp7_audit.access_now()owner to postgres;
alter function cp7_audit.object_of(jsonb)owner to postgres;
alter function cp7_audit.value_text(jsonb)owner to postgres;
alter function cp7_audit.changed_keys(jsonb,jsonb)owner to postgres;
alter function cp7_audit.fields(jsonb,jsonb)owner to postgres;
alter function cp7_audit.entry(erp.audit_logs,text)owner to postgres;
alter function cp7_audit.workspace(jsonb)owner to postgres;
grant create on schema public to cp7_audit_read;
alter function public.erp_cp7_get_audit_trail_v1(jsonb)owner to cp7_audit_read;
revoke create on schema public from cp7_audit_read;
revoke all on function cp7_audit.access_now(),cp7_audit.object_of(jsonb),cp7_audit.value_text(jsonb),cp7_audit.changed_keys(jsonb,jsonb),
 cp7_audit.fields(jsonb,jsonb),cp7_audit.entry(erp.audit_logs,text),cp7_audit.workspace(jsonb)
 from public,anon,authenticated,service_role,cp7_capture,cp7_audit_read;
grant execute on function cp7_audit.workspace(jsonb)to cp7_audit_read;
revoke all on function public.erp_cp7_get_audit_trail_v1(jsonb)from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_get_audit_trail_v1(jsonb)to authenticated;
