-- BF unused rollback. No posted history or master decisions are deleted after use.
begin;
set local search_path='';
set local lock_timeout='10s';
do $rollback$
declare capsule jsonb;r record;t text;n bigint;
begin
 perform pg_advisory_xact_lock(hashtextextended('BF:COMMERCIAL_SKUS',0));
 if not exists(select 1 from erp.schema_migrations where version='v2.6.20bf') then raise exception 'BF_NOT_INSTALLED';end if;
 select payload into strict capsule from erp.bf_rollback_v1;
 foreach t in array array['bf_laundry_delivery_sources_v1','bf_context_v1','bf_requests_v1','bf_po_boms_v1','bf_wave_skus_v1','bf_sku_members_v1','bf_sku_versions_v1','bf_skus_v1'] loop
   execute format('lock table erp.%I in access exclusive mode',t);
   execute format('select count(*) from erp.%I',t) into n;
   if n<>0 then raise exception 'BF_USED_ROLLBACK_REFUSED: % sudah dipakai',t;end if;
 end loop;
 for r in select key,value from jsonb_each_text(capsule->'installed') loop
   if to_regprocedure(r.key) is null or md5(pg_get_functiondef(to_regprocedure(r.key))) is distinct from r.value then
     raise exception 'BF_ROLLBACK_SOURCE_DRIFT: %',r.key;end if;
 end loop;
 for r in select value from jsonb_each_text(capsule->'functions') loop execute r.value;end loop;
 drop trigger bf_fg_member on erp.fg_lots;
 drop trigger bf_bs_member on erp.bs_cases;
 drop trigger bf_shared_price on erp.product_price_versions;
 drop trigger bf_shared_bom on erp.accessory_bom_versions;
 drop trigger bf_shared_bom_item on erp.accessory_bom_items;
 alter table erp.po_work_component_snapshots drop column bf_sku_version_id;
 execute 'alter table erp.po_work_component_snapshots add constraint po_work_component_snapshots_po_id_work_component_id_key '||(capsule->>'snapshot_constraint');
 alter table erp.rework_component_lines drop column bf_sku_version_id;
 alter table erp.rework_component_lines drop constraint rework_component_lines_rate_basis_check;
 execute 'alter table erp.rework_component_lines add constraint rework_component_lines_rate_basis_check '||(capsule->>'rework_constraint');
 alter table erp.bd_laundry_charge_lines_v1 drop column bf_sku_version_id;
 for r in select p.oid::regprocedure::text signature from pg_proc p join pg_namespace n on n.oid=p.pronamespace
   where n.nspname||'.'||p.proname=any(array['erp.bf_version_at_v1','erp.bf_guard_economic_v1','erp.bf_legacy_basis_v1','erp.bf_save_groups_v1','erp.bf_guard_new_member_v1','erp.bf_validate_rates_v1','erp.bf_work_rate_v1','erp.bf_context_rate_v1','erp.bf_bom_for_lot_v1','erp.bf_recipe_basis_v1','erp.bf_bind_wave_v1','erp.bf_work_capacity_v1','erp.bf_snapshot_sku_v1','erp.bf_wave_revision_v1','erp.bf_group_sku_v1','erp.bf_ensure_work_v1','erp.bf_snapshot_matches_v1','erp.bf_assert_work_scope_v1','erp.bf_delivery_invoiced_v1','erp.bf_laundry_rate_v1','erp.bf_merge_charges_v1','erp.bf_package_charges_v1','erp.bf_complete_shares_v1','erp.bf_component_charge_v1','public.erp_get_laundry_history_v1','erp.bf_resolve_import_product_v1','erp.save_sku_action_v1','erp.get_sku_workspace_v1','erp.get_sku_hpp_v1','public.erp_save_sku_action_v1','public.erp_get_sku_workspace_v1','public.erp_get_sku_hpp_v1']) loop execute 'drop function '||r.signature;end loop;
 foreach t in array array['bf_laundry_delivery_sources_v1','bf_context_v1','bf_requests_v1','bf_po_boms_v1','bf_wave_skus_v1','bf_sku_members_v1','bf_sku_versions_v1','bf_skus_v1'] loop execute format('drop table erp.%I',t);end loop;
 drop table erp.bf_rollback_v1;
 delete from erp.schema_migrations where version='v2.6.20bf';
end $rollback$;
commit;
