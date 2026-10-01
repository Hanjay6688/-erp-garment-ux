-- Metadata only. This opens no maintenance window and changes no ERP data.
begin transaction read only;
select jsonb_build_object(
  'checked_at',clock_timestamp(),
  'database',current_database(),
  'postgres_version',current_setting('server_version'),
  'transaction_read_only',current_setting('transaction_read_only'),
  'objects',(select jsonb_object_agg(object_name,installed) from (values
    ('app_ledger',to_regclass('erp.schema_migrations') is not null),
    ('accessory_policies',to_regclass('erp.bc_policy_settings_v1') is not null),
    ('laundry_policies',to_regclass('erp.bd_policy_settings_v1') is not null),
    ('sku_versions',to_regclass('erp.bf_sku_versions_v1') is not null),
    ('accessory_workspace',to_regprocedure('public.erp_get_accessory_service_workspace_v1(jsonb)') is not null),
    ('laundry_workspace',to_regprocedure('public.erp_get_laundry_bd_workspace_v1(jsonb)') is not null),
    ('sku_hpp',to_regprocedure('public.erp_get_sku_hpp_v1(jsonb)') is not null)
  ) required(object_name,installed)),
  'other_client_sessions',(select count(*) from pg_stat_activity where datname=current_database() and pid<>pg_backend_pid() and backend_type='client backend'),
  'other_open_transactions',(select count(*) from pg_stat_activity where datname=current_database() and pid<>pg_backend_pid() and backend_type='client backend' and xact_start is not null),
  'maintenance_started',false,
  'production_go',false
) as cp6_readiness;
rollback;
