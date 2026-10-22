create or replace function cp7_netting_native.fingerprint(c jsonb)returns text
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select encode(extensions.digest(convert_to(jsonb_build_object('net_kernel','net-dual-horizon-2','work_source',cp7_schedule_native.fingerprint(c),
  'matching_products',c->'matching_products')::text,'UTF8'),'sha256'),'hex')
$$;
