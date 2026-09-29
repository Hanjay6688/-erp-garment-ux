-- Private PostgreSQL kernels. No operational writes or public execution.
create schema cp7_wip authorization cp7_capture;
revoke all on schema cp7_wip from public,anon,authenticated,service_role;

create function cp7_wip.fields(v jsonb, names text[]) returns void
language plpgsql immutable security invoker set search_path='' as $$
begin
 if jsonb_typeof(v) is distinct from 'object'
    or (select count(*) from jsonb_object_keys(v))<>cardinality(names)
    or not v ?& names then
  raise exception using errcode='22023',message='CP7_WIP_FIELDS';
 end if;
end $$;
create function cp7_wip.key(v jsonb) returns text
language plpgsql immutable security invoker set search_path='' as $$
begin
 if jsonb_typeof(v) is distinct from 'string' or length(v#>>'{}') not between 1 and 200
    or btrim(v#>>'{}')<>(v#>>'{}') then
  raise exception using errcode='22023',message='CP7_WIP_KEY';
 end if;
 return v#>>'{}';
end $$;
create function cp7_wip.pcs(v jsonb) returns numeric
language plpgsql immutable security invoker set search_path='' as $$
begin
 if jsonb_typeof(v) is distinct from 'string' or (v#>>'{}') !~ '^(0|[1-9][0-9]{0,29})$' then
  raise exception using errcode='22023',message='CP7_WIP_PCS';
 end if;
 return (v#>>'{}')::numeric;
end $$;
create function cp7_wip.refs(v jsonb) returns void
language plpgsql immutable security invoker set search_path='' as $$
declare r jsonb;
begin
 if jsonb_typeof(v) is distinct from 'array' or jsonb_array_length(v) not between 1 and 1000 then
  raise exception using errcode='22023',message='CP7_WIP_REFS';
 end if;
 for r in select value from jsonb_array_elements(v) loop
  perform cp7_wip.fields(r,array['kind','id','revision']);
  perform cp7_wip.key(r->'kind');perform cp7_wip.key(r->'id');perform cp7_wip.key(r->'revision');
 end loop;
 if (select count(*) from jsonb_array_elements(v))<>(select count(distinct value) from jsonb_array_elements(v)) then
  raise exception using errcode='22023',message='CP7_WIP_DUPLICATE_REF';
 end if;
end $$;
