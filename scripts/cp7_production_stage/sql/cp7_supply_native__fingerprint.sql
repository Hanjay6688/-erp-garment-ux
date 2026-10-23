create or replace function cp7_supply_native.fingerprint(c jsonb)returns text
language sql immutable security invoker set search_path=''set TimeZone='UTC'as $$
 select encode(extensions.digest(convert_to(jsonb_build_object('target_kernel','target-unified-2','native',c->'facts',
  'profiles',c->'profiles','production_policies',c->'production_policies'->'rows',
  'production_scope',c->'production_sources'->'scope',
  'production',c->'production_sources'->'facts')::text,'UTF8'),'sha256'),'hex')
$$;
