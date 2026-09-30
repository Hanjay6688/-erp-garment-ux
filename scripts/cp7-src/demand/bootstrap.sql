-- F04 development kernels; install transactionally after the pinned P04 helpers.
-- Private snapshot inputs are NOT a public API or an authoritative source reader.
create schema cp7_demand authorization cp7_capture;
create schema cp7_baseline authorization cp7_capture;
create schema cp7_models authorization cp7_capture;
revoke all on schema cp7_demand,cp7_baseline,cp7_models from public,anon,authenticated,service_role;

create function cp7_demand.decimal(v jsonb) returns numeric
language plpgsql immutable security invoker set search_path='' as $$
begin
 if jsonb_typeof(v) is distinct from 'string' or (v#>>'{}') !~ '^(0|[1-9][0-9]{0,29})(\.[0-9]{1,12})?$' then
  raise exception using errcode='22023',message='CP7_F04_DECIMAL';
 end if;
 return (v#>>'{}')::numeric;
end $$;

create function cp7_demand.day(v jsonb) returns date
language plpgsql immutable security invoker set search_path='' as $$
declare d date;
begin
 if jsonb_typeof(v) is distinct from 'string' or (v#>>'{}') !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' then raise exception 'CP7_F04_DATE';end if;
 d:=(v#>>'{}')::date;
 if to_char(d,'YYYY-MM-DD')<>v#>>'{}' then raise exception 'CP7_F04_DATE';end if;
 return d;
end $$;

create function cp7_demand.instant(v jsonb) returns timestamptz
language plpgsql immutable security invoker set search_path='' as $$
begin
 if jsonb_typeof(v) is distinct from 'string' or (v#>>'{}') !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,6})?Z$' then raise exception 'CP7_F04_INSTANT_UTC';end if;
 perform cp7_demand.day(to_jsonb(left(v#>>'{}',10)));
 if substring(v#>>'{}',12,2)::int>23 or substring(v#>>'{}',15,2)::int>59 or substring(v#>>'{}',18,2)::int>59 then raise exception 'CP7_F04_INSTANT_UTC';end if;
 return (v#>>'{}')::timestamptz;
end $$;

create function cp7_demand.items(v jsonb,lim integer) returns void
language plpgsql immutable security invoker set search_path='' as $$
begin
 if jsonb_typeof(v) is distinct from 'array' or jsonb_array_length(v)>lim then raise exception 'CP7_F04_ARRAY_LIMIT';end if;
end $$;

create function cp7_demand.context(v jsonb,version text) returns void
language plpgsql immutable security invoker set search_path='' as $$
begin
 if v->>'contract_version' is distinct from version then raise exception 'CP7_F04_CONTRACT';end if;
 perform cp7_wip.key(v->'snapshot_id');perform cp7_wip.key(v->'scope_id');
end $$;
