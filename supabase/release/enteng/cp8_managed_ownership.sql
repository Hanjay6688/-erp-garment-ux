-- Normalize privately owned objects created by either supported Supabase installer.
-- Applies to the modules already installed. Reapplying preserves their existing grants and rows.
do $migration$
declare
  feature record;
  table_name text;
  asset record;
  actual_owner name;
  original_body text;
  matches_contract boolean;
begin
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('cp8-managed-ownership-v1', 0));
  for feature in select * from (values
    ('dyeing', 'cp8-laundry-dyeing-master-v1', 'cp8-dyeing-managed-owner-v1', 'erp.save_laundry_bd_action_v1(text,jsonb,uuid)',
     array['erp.laundry_dyeing_types_v1', 'erp.laundry_dyeing_sku_links_v1']),
    ('wip', 'cp8-wip-batch-v1', 'cp8-wip-batch-managed-owner-v1', 'erp.record_sewing_terminal_v1(jsonb,uuid)',
     array['erp.wip_batch_reversals_v1', 'erp.wip_batch_replacements_v1'])
  ) as modules(id, version, repair_version, native_writer, tables)
  where exists (select 1 from erp.schema_migrations m where m.version = modules.version)
  order by modules.id loop
    if (select pg_catalog.pg_get_userbyid(proowner) from pg_catalog.pg_proc
        where oid = feature.native_writer::regprocedure) is distinct from 'postgres' then
      raise exception 'Unexpected owner of native writer %', feature.native_writer;
    end if;

    foreach table_name in array feature.tables loop
      select pg_catalog.pg_get_userbyid(relowner), relkind = 'r' and relrowsecurity
        into strict actual_owner, matches_contract from pg_catalog.pg_class where oid = table_name::regclass;
      if actual_owner not in ('postgres','supabase_admin') or not matches_contract then
        raise exception 'Unexpected relation or owner at %', table_name;
      end if;
      if actual_owner = 'supabase_admin' then
        execute pg_catalog.format('alter table %s owner to postgres', table_name);
      end if;
    end loop;

    for asset in select * from (values
      ('wip', 'erp.cp8_distribution_version_v1(uuid)', '9012c1c36936c0bd6bb6a6e16dac065e8bbf32f38672989f452c2dceec1f1386'),
      ('wip', 'erp.cp8_save_wip_batch_v1(text,jsonb,uuid,bigint)', 'f1503e855df5f5444f5dacf77688ccef7017dd61df9d2b04ffdfc4fccae3e4b6'),
      ('wip', 'erp.cp8_split_returned_batch_v1(uuid,uuid,jsonb,uuid,timestamptz,text)', '2f95188e5f8bff1a7ffc23e607a5440f48762581899893f57ccf858447f4451b'),
      ('wip', 'erp.cp8_wip_batch_active_v1(uuid,timestamptz)', '84ed8e5503649cccb5e6f412d55aa07f53acfa6479ba047bb28c1109fd943a57'),
      ('wip', 'erp.cp8_wip_pending_batches_v1(uuid,timestamptz)', 'd3bf70f3925f620fb0e54fb49ad605edb65090a8e0150bc0c2e6a89197209e7e'),
      ('wip', 'erp.cp8_wip_pending_pickup_v1(uuid,timestamptz)', '5799d4081a5e27ce19de8c2df7912b5882e7c5b37a5a26b2e5c29640b115e8bb'),
      ('wip', 'erp.cp8_wip_returned_batch_payload_v1(uuid)', '79c4b279b3d358b4b658f34f9de0f7debb559f861f1a1a83b1f4db21ab3cb725'),
      ('wip', 'erp.cp8_wip_returned_pieces_v1(uuid,timestamptz)', 'ca7840417c98bdfdbe66df5dd66cc907bc407767eeb911a70c1a02d24f2db5a8'),
      ('wip', 'erp.cp8_wip_work_completion_guard_v1()', 'fd8bcc683e54f4d3afbfe47be573ed77778ba42f804cf716b8405d9800378f79'),
      ('dyeing', 'erp.cp8_laundry_dyeing_label_v1(uuid,uuid)', '26c8febfdb0d3f06edfaa9952e628037b419464c1515e603cdf4a920d5aeb086'),
      ('dyeing', 'erp.cp8_save_laundry_dyeing_master_v1(text,jsonb)', '4c3c930c65f673c37c350c76d5f9d3bf9f553c366e66e0dece3831a63bd65757'),
      ('dyeing', 'public.erp_get_laundry_dyeing_types_v1(uuid,uuid,boolean)', '8e9fbd2892cd7e6cacea90f10de319ebc1a8e8b0808cf096b554275ab7799899')
    ) as sources(module, signature, expected_body) where sources.module = feature.id loop
      select pg_catalog.pg_get_userbyid(proowner),
             pg_catalog.encode(pg_catalog.sha256(pg_catalog.convert_to(prosrc,'UTF8')), 'hex'),
             prosecdef and coalesce('search_path=""' = any(proconfig), false)
        into strict actual_owner, original_body, matches_contract
        from pg_catalog.pg_proc where oid = asset.signature::regprocedure;
      if actual_owner not in ('postgres','supabase_admin') or not matches_contract then
        raise exception 'Unexpected routine or owner at %', asset.signature;
      end if;
      if actual_owner = 'supabase_admin' then
        if original_body <> asset.expected_body then
          raise exception 'Original routine body differs at %', asset.signature;
        end if;
        execute pg_catalog.format('alter function %s owner to postgres', asset.signature);
      end if;
    end loop;
    insert into erp.schema_migrations(version, description)
      values (feature.repair_version, 'Align object ownership with native ERP writer')
      on conflict (version) do nothing;
  end loop;
end
$migration$;
