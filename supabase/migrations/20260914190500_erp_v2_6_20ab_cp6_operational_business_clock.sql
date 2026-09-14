-- CP6 AB: operational Jakarta business clock for recost, posting and reversal.
-- Native 186/187 qualified six AA counterexamples with seventeen controls.
-- Five functions change. Admitted SQL through AA remains immutable.
begin;
set local lock_timeout='10s';set local statement_timeout='240s';set local timezone='UTC';
lock table erp.schema_migrations,supabase_migrations.schema_migrations in share row exclusive mode;
lock table erp.app_users in access exclusive mode;
lock table erp.idempotency_requests in share row exclusive mode;
select pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
lock table erp.products,erp.audit_logs,erp.journal_entries,erp.journal_lines,
  erp.account_daily_balances,erp.sales_headers,erp.sales_items,
  erp.sale_stock_allocations,erp.sales_returns,erp.sales_return_items,
  erp.sales_payments,erp.fg_lots,erp.fg_stock_movements,
  erp.fg_inventory_balances,erp.hpp_versions,erp.product_conversions,
  erp.product_conversion_allocations,erp.laundry_deliveries,
  erp.laundry_delivery_lines,erp.laundry_receipts,
  erp.laundry_failed_wash_attempts,erp.wip_stage_events,
  erp.cp6_v2620g_rollback_capsule,erp.cp6_v2620h_rollback_capsule,
  erp.cp6_v2620i_rollback_capsule,erp.sales_payment_posting_facts,
  erp.sales_payment_reversal_facts,erp.cp6_v2620j_rollback_capsule,
  erp.cp6_v2620k_rollback_capsule,erp.accounting_period_control,
  erp.accounting_account_mappings,erp.cash_accounts,erp.chart_accounts,
  erp.laundry_claims,erp.laundry_vendors,erp.cp6_v2620l_rollback_capsule,
  erp.opening_balance_headers,erp.opening_balance_items,
  erp.opening_subledger_balances,erp.opening_subledger_settlements,
  erp.opening_financial_corrections,erp.supplier_payments,
  erp.material_purchase_headers,erp.material_purchase_items,
  erp.material_supplier_invoices,erp.material_supplier_invoice_lines,
  erp.material_supplier_returns,erp.material_supplier_return_items,
  erp.material_purchase_cost_corrections,
  erp.material_purchase_cost_correction_items,erp.material_stock_movements,
  erp.material_rolls,erp.cost_recalc_queue,erp.cost_adjustments,
  erp.suppliers,erp.materials,erp.cp6_v2620m_rollback_capsule,
  erp.supplier_cent_posting_facts,erp.material_cost_history,
  erp.material_cost_revaluation_state,erp.material_cost_revaluation_events,
  erp.material_cost_checkpoints,erp.cp6_v2620n_rollback_capsule,
  erp.cp6_v2620o_rollback_capsule,erp.cp6_v2620p_rollback_capsule,
  erp.cp6_v2620q_rollback_capsule,erp.cp6_v2620r_rollback_capsule,
  erp.cp6_v2620s_rollback_capsule,erp.material_adjustments,
  erp.material_adjustment_items,erp.material_adjustment_revaluation_facts,
  erp.cp6_v2620t_rollback_capsule,erp.cp6_v2620u_rollback_capsule,
  erp.misc_finance_transactions,erp.misc_finance_categories,
  erp.cp6_v2620v_rollback_capsule,erp.scrap_batches,erp.scrap_sales,
  erp.cp6_v2620w_rollback_capsule,erp.app_roles,erp.app_role_permissions,erp.app_permissions,erp.cutting_bridge_execution_context,erp.bs_resolution_execution_context,erp.cp6_laundry_qc_execution_context
in share row exclusive mode;

do $lock_all_erp_v2620ab$
declare v_table text;
begin
  for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in('r','p') and c.relname not in('schema_migrations','cp6_v2620ab_rollback_capsule') order by c.relname loop
    execute format('lock table erp.%I in share row exclusive mode',v_table);
  end loop;
end
$lock_all_erp_v2620ab$;


do $predecessor_v2620ab$
declare r record;c record;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20aa')
     or exists(select 1 from erp.schema_migrations where version='v2.6.20ab')
     or to_regclass('erp.cp6_v2620ab_rollback_capsule') is not null then
    raise exception 'AB_REQUIRES_EXACT_AA_WITHOUT_AB_RESIDUE';
  end if;
  if (select count(*) from supabase_migrations.schema_migrations where name='erp_v2_6_20aa_cp6_material_cost_business_day')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations
       where version='20260914163608' and name='erp_v2_6_20aa_cp6_material_cost_business_day'
         and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')
         in('2ada33f0d04da6589b92646652a482290ef614e500c6abb026011823f6ebcfc7',
            '63c1b52a4e1ab8c329135ba0c4502c303be0cde0bb28bbc9f34413f191eb13fc'))
     or exists(select 1 from supabase_migrations.schema_migrations where version>'20260914163608')
     or (select count(*) from erp.cp6_v2620aa_rollback_capsule)<>2
     or (select count(*) from erp.cp6_v2620z_rollback_capsule)<>1
     or (select count(*) from erp.cp6_v2620y_rollback_capsule)<>6 then
    raise exception 'AB_PREDECESSOR_PLATFORM_OR_CAPSULE_MISMATCH';
  end if;
  for r in select * from(values
    ('erp.post_opening_subledger_settlement(uuid)','c56b387a8593b19cd3b92e6dc20ac95459d2aedeb2b616b6fb1e4d812e729393','b709ed64c78b09c113e6e0541eb757b5367dfbf7dd51752a26827207fc12e97e',array['authenticated=X/postgres','postgres=X/postgres']::text[]),
    ('erp.post_vendor_payment(uuid)','05b067af75c8691c4e012ff719f8793dbe597ee5f0e451db665d4baab1427316','cf8c1105cb6426583464d7516eb70693c28d668702ae3eb23c22f4029f07f763',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.post_sales_payment(uuid)','362e4266718275af5af6efcded3c85cd7a7a7f1faba7241979114fe6e57ffd6c','605db7b1ce7bea6b54e70625092f8e98365d3966dc09d220be7dff81014a1f1d',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.run_v267_financial_truth_checks()','845b9868bb0b0e25443c4e75c77cfcf815e34c4fac78b8bd38038b0476e2944a','7ead45b0a09258adcf1b9a9dae44b5627c2ba6fec36767f513706d282f076a9c',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp._v268_financial_report_checks_pre_scope()','c77df75873558f96425b8e6b9591903259e5d985a9bd534ab96466799610e507','f95aeb7875cd2a7de603ad33c86cff7c7b0849b7d7f401e9280962b4733c7d45',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.run_v268_financial_report_checks()','48d60613970b015d1afb30a2f8a7cec0e5d56d1f692c6a1acfa0ffd48684fda1','416b8c53665c4c2b814d4621935a9291797fdbf49067deb0a910d16dc90685fd',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[])
  ) expected(identity,predecessor_sha256,installed_sha256,acl)
  loop
    select cap.*,
      encode(extensions.digest(convert_to(cap.object_definition,'UTF8'),'sha256'),'hex') definition_actual,
      encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') installed_actual,
      pg_get_userbyid(p.proowner) installed_owner,
      case when p.proacl is null then null else
        array(select a::text from unnest(p.proacl) a order by a::text) end installed_acl
    into c
    from erp.cp6_v2620y_rollback_capsule cap
    left join pg_proc p on p.oid=to_regprocedure(cap.object_regidentity)
    where cap.object_regidentity=r.identity;
    if c.object_regidentity is null
       or c.definition_sha256 is distinct from r.predecessor_sha256
       or c.definition_actual is distinct from r.predecessor_sha256
       or c.installed_definition_sha256 is distinct from r.installed_sha256
       or c.installed_actual is distinct from r.installed_sha256
       or c.owner_snapshot is distinct from 'postgres'
       or c.acl_snapshot is distinct from r.acl
       or c.installed_owner is distinct from 'postgres'
       or c.installed_acl is distinct from r.acl then
      raise exception 'AB_TRUSTED_Y_PREDECESSOR_PIN_MISMATCH: %',r.identity;
    end if;
  end loop;
  -- Pin the shared authorization guard and inherited private helpers/facts.
  for r in select * from(values
    ('erp.post_scrap_sale(uuid)','cb573efa942bbf65e770dd645cc0636ea4142633241af16842b532f36ce32131',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.require_internal()','5dffcd53c0a5de609ae41482ca246d2afc806b9d92241253d680cf5c7fe1612e',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.current_app_role()','ca1a9e2bb44aa8c5f80911728175f923f82472ca170e68b7c21d759601da4022',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.current_app_user_id()','b65a4c13983626e8c7a218a2cb68ca24a809f511b8bf20c1f3aa2116b3fd2a10',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.has_permission(text)','a9942661396f6c1f3f535720e806a5431db10a11dc1399787a30af733a882d2b',array['postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp._idempotency_actor_key()','63f9ecea25c22be59917d9153d6686e1cdf6da5a1cf3ede839287aa08c582a92',array['postgres=X/postgres']::text[]),
    ('erp._cp3_business_date(timestamp with time zone)','adf1fb87dd9f0b6a856bcb109b5118f9c4aac5da0ac32554ecbbc009f6d88248',array['postgres=X/postgres']::text[]),
    ('erp._cp6_material_adjustment_revaluation_state(uuid)','47a2c15955a682040d2c0c6b72f2941eaae8467e2b16fa5c4bbc10dff27a3c2e',array['postgres=X/postgres']::text[]),
    ('erp._cp6_sync_material_adjustment_revaluation(uuid,uuid)','355246b52dc88e5d91643485fe796f24e7975d0629824c5b28c31074469ed7ba',array['postgres=X/postgres']::text[]),
    ('erp.guard_material_adjustment_revaluation_fact_v2620t()','c2cc7ddb076f557d0f71df9170b9d02425fc17c2f33e471bd1af48e61729829e',array['postgres=X/postgres']::text[])
  ) expected(identity,sha256,acl) loop
    if encode(extensions.digest(convert_to(pg_get_functiondef(
        to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex') is distinct from r.sha256
       or (select pg_get_userbyid(proowner) from pg_proc
         where oid=to_regprocedure(r.identity)) is distinct from 'postgres'
       or (select array(select a::text from unnest(proacl) a order by a::text)
         from pg_proc where oid=to_regprocedure(r.identity)) is distinct from r.acl then
      raise exception 'AB_TRUSTED_U_INPUT_OWNER_ACL_MISMATCH: %',r.identity;
    end if;
  end loop;
  if not exists(select 1 from pg_class
      where oid='erp.material_adjustment_revaluation_facts'::regclass
        and relrowsecurity and relowner='postgres'::regrole)
     or exists(select 1 from information_schema.role_table_grants
       where table_schema='erp' and table_name='material_adjustment_revaluation_facts'
         and grantee in('PUBLIC','anon','authenticated','service_role'))
     or (select count(*) from pg_trigger
       where tgrelid='erp.material_adjustment_revaluation_facts'::regclass
         and not tgisinternal and tgenabled='O'
         and tgfoid='erp.guard_material_adjustment_revaluation_fact_v2620t()'::regprocedure
         and tgname in('trg_material_adjustment_revaluation_fact_append_only',
           'trg_material_adjustment_revaluation_fact_no_truncate'))<>2 then
    raise exception 'AB_INHERITED_T_SECURITY_MISMATCH';
  end if;

  for r in select * from(values
    ('erp.close_accounting_through(date,text)','c9517690638ac40bb8914e0613b7d5bdf92256274e9c5551747060d09a79536b','7f20b0a381b049391fc3e33dce00b3b8c517b0b77ae8f2b2756cac5e0a021b42',array['authenticated=X/postgres','postgres=X/postgres']::text[])
  ) expected(identity,predecessor_sha256,installed_sha256,acl)
  loop
    select cap.*,
      encode(extensions.digest(convert_to(cap.object_definition,'UTF8'),'sha256'),'hex') definition_actual,
      encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') installed_actual,
      pg_get_userbyid(p.proowner) installed_owner,
      case when p.proacl is null then null else
        array(select a::text from unnest(p.proacl) a order by a::text) end installed_acl
    into c
    from erp.cp6_v2620z_rollback_capsule cap
    left join pg_proc p on p.oid=to_regprocedure(cap.object_regidentity)
    where cap.object_regidentity=r.identity;
    if c.object_regidentity is null
       or c.definition_sha256 is distinct from r.predecessor_sha256
       or c.definition_actual is distinct from r.predecessor_sha256
       or c.installed_definition_sha256 is distinct from r.installed_sha256
       or c.installed_actual is distinct from r.installed_sha256
       or c.owner_snapshot is distinct from 'postgres'
       or c.acl_snapshot is distinct from r.acl
       or c.installed_owner is distinct from 'postgres'
       or c.installed_acl is distinct from r.acl then
      raise exception 'AB_TRUSTED_Z_PREDECESSOR_PIN_MISMATCH: %',r.identity;
    end if;
  end loop;
  for r in select * from(values
    ('erp.refresh_material_cost_checkpoint(uuid,date)','cbb3d27608c720380b099a020a2f54b639ffc9626d3a09fd258402eb15511978','7eea402dec46b03d5425ef9c1c052ca409de7fafa72000b7abef5fda6849b30a',array['postgres=X/postgres']::text[]),
    ('erp._recalculate_material_cost_core(uuid,timestamp with time zone,boolean)','e70bce5bc64114ac0dad5c0ccbc374a63590089d9f481007d6c609f82f323399','c1f74ab9e855bf354d62f0e9053883c7cc0efdfeb329de8f2e081e46852f50b6',array['postgres=X/postgres']::text[])
  ) expected(identity,predecessor_sha256,installed_sha256,acl)
  loop
    select cap.*,
      encode(extensions.digest(convert_to(cap.object_definition,'UTF8'),'sha256'),'hex') definition_actual,
      encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') installed_actual,
      pg_get_userbyid(p.proowner) installed_owner,
      case when p.proacl is null then null else
        array(select a::text from unnest(p.proacl) a order by a::text) end installed_acl
    into c
    from erp.cp6_v2620aa_rollback_capsule cap
    left join pg_proc p on p.oid=to_regprocedure(cap.object_regidentity)
    where cap.object_regidentity=r.identity;
    if c.object_regidentity is null
       or c.definition_sha256 is distinct from r.predecessor_sha256
       or c.definition_actual is distinct from r.predecessor_sha256
       or c.installed_definition_sha256 is distinct from r.installed_sha256
       or c.installed_actual is distinct from r.installed_sha256
       or c.owner_snapshot is distinct from 'postgres'
       or c.acl_snapshot is distinct from r.acl
       or c.installed_owner is distinct from 'postgres'
       or c.installed_acl is distinct from r.acl then
      raise exception 'AB_TRUSTED_AA_PREDECESSOR_PIN_MISMATCH: %',r.identity;
    end if;
  end loop;
  for r in select * from(values
    ('erp.sync_material_cost_revaluation(uuid)','3334800b5888000a4388dda4362ebd0db4c5f0dcdc0bbf3e41acfcf629d720f0',array['postgres=X/postgres']::text[]),
    ('erp.process_cost_recalc_queue(integer)','4b0b4841ad3a6b4d72b86f8e4fb1958ba2dda0dad4ddb65c9c085c7c2358cc3f',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.resolve_accounting_transaction_date(date)','92e6c30c60bce3406178bd661ca5df2e5d12e17380fad2a8730be0c91d86bf48',array['postgres=X/postgres']::text[]),
    ('erp._cp3_r4_reverse_journal_internal(uuid,text)','2d54bfdf9bf0912e6b13e558ddbc4cb419020f191c3ce626a26f2c27b814b20c',array['postgres=X/postgres']::text[]),
    ('erp.post_journal(text,uuid,date,text,jsonb)','1ae479c9c32b9489e659d83d99a9829ef88876643f3e8f8aa276fee6d96a9cdf',array['postgres=X/postgres','service_role=X/postgres']::text[])
  ) expected(identity,sha256,acl) loop
    if encode(extensions.digest(convert_to(pg_get_functiondef(
        to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex') is distinct from r.sha256
       or (select pg_get_userbyid(proowner) from pg_proc
         where oid=to_regprocedure(r.identity)) is distinct from 'postgres'
       or (select array(select a::text from unnest(proacl) a order by a::text)
         from pg_proc where oid=to_regprocedure(r.identity)) is distinct from r.acl then
      raise exception 'AB_PREDECESSOR_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity;
    end if;
  end loop;
  if exists(select 1 from erp.accounting_period_control where closed_through>=erp._cp3_business_date(current_timestamp)) then
    raise exception 'AB_PREEXISTING_PERIOD_CLOSE_REVIEW_REQUIRED';
  end if;
  -- Historical recost/reversal dates may already be wrong while READY.
  -- Installation must not certify or rewrite those earlier business rows.
  if exists(select 1 from erp.material_cost_revaluation_events) then
    raise exception 'AB_PREEXISTING_MATERIAL_RECOST_REVIEW_REQUIRED';
  end if;
  if exists(select 1 from erp.journal_entries where source_type='JOURNAL_REVERSAL') then
    raise exception 'AB_PREEXISTING_JOURNAL_REVERSAL_REVIEW_REQUIRED';
  end if;
end
$predecessor_v2620ab$;

create table erp.cp6_v2620ab_rollback_capsule(
  like erp.cp6_v2620aa_rollback_capsule including all
);
alter table erp.cp6_v2620ab_rollback_capsule enable row level security;
revoke all on erp.cp6_v2620ab_rollback_capsule from public,anon,authenticated,service_role;
insert into erp.cp6_v2620ab_rollback_capsule(
  object_identity,object_regidentity,object_definition,definition_sha256,
  acl_snapshot,owner_snapshot
)
select format('%I.%I(%s)',n.nspname,p.proname,
    pg_get_function_identity_arguments(p.oid)),
  p.oid::regprocedure::text,pg_get_functiondef(p.oid),
  encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
  array(select a::text from unnest(p.proacl) a order by a::text),
  pg_get_userbyid(p.proowner)
from pg_proc p join pg_namespace n on n.oid=p.pronamespace
where p.oid in(
  to_regprocedure('erp.sync_material_cost_revaluation(uuid)'),
  to_regprocedure('erp.process_cost_recalc_queue(integer)'),
  to_regprocedure('erp.resolve_accounting_transaction_date(date)'),
  to_regprocedure('erp._cp3_r4_reverse_journal_internal(uuid,text)'),
  to_regprocedure('erp.post_journal(text,uuid,date,text,jsonb)'));


do $operational_business_clock_v2620ab$
declare d text;r record;
begin
  -- statement_timestamp is constant for the current command, including its
  -- nested journal calls, and advances between commands in a long transaction.
  for r in select * from(values
    ('erp.sync_material_cost_revaluation(uuid)','current_date','erp._cp3_business_date(statement_timestamp())',2),
    ('erp.process_cost_recalc_queue(integer)','current_date','erp._cp3_business_date(statement_timestamp())',2),
    ('erp.resolve_accounting_transaction_date(date)','current_timestamp','statement_timestamp()',2),
    ('erp._cp3_r4_reverse_journal_internal(uuid,text)','current_timestamp','statement_timestamp()',1),
    ('erp.post_journal(text,uuid,date,text,jsonb)','values(v_number,p_transaction_date,v_gl_date,now(),','values(v_number,p_transaction_date,v_gl_date,statement_timestamp(),',1)
  ) expected(identity,anchor,replacement,hits) loop
    select pg_get_functiondef(to_regprocedure(r.identity)) into d;
    if (length(d)-length(replace(d,r.anchor,'')))/length(r.anchor)<>r.hits then
      raise exception 'AB_OPERATIONAL_CLOCK_ANCHOR: %',r.identity;
    end if;
    execute replace(d,r.anchor,r.replacement);
  end loop;
end
$operational_business_clock_v2620ab$;

do $installed_v2620ab$
declare r record;c record;
begin
  if (select count(*) from erp.cp6_v2620ab_rollback_capsule)<>5 then
    raise exception 'AB_CAPSULE_CARDINALITY_MISMATCH';
  end if;
  update erp.cp6_v2620ab_rollback_capsule cap set installed_definition_sha256=
    encode(extensions.digest(convert_to(pg_get_functiondef(
      to_regprocedure(cap.object_regidentity)),'UTF8'),'sha256'),'hex');
  for r in select * from(values
    ('erp.sync_material_cost_revaluation(uuid)','3334800b5888000a4388dda4362ebd0db4c5f0dcdc0bbf3e41acfcf629d720f0','af752a5cb068d71af90c646718b55ef2b6eabd9319021202a0d8f92042892f91',array['postgres=X/postgres']::text[]),
    ('erp.process_cost_recalc_queue(integer)','4b0b4841ad3a6b4d72b86f8e4fb1958ba2dda0dad4ddb65c9c085c7c2358cc3f','7fe85b6739fa5684171cffd26d028eabd35efe3bb2691e2daa9e52cf40892a13',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[]),
    ('erp.resolve_accounting_transaction_date(date)','92e6c30c60bce3406178bd661ca5df2e5d12e17380fad2a8730be0c91d86bf48','656ac4cd3ae6a2df24bd11f4c1c044c3e9bf423cc6c7343ab863bad16eee6803',array['postgres=X/postgres']::text[]),
    ('erp._cp3_r4_reverse_journal_internal(uuid,text)','2d54bfdf9bf0912e6b13e558ddbc4cb419020f191c3ce626a26f2c27b814b20c','2996d1c16396768097306556b5916ba93996d2ff451f3c5e7cd35deea7a3ac6f',array['postgres=X/postgres']::text[]),
    ('erp.post_journal(text,uuid,date,text,jsonb)','1ae479c9c32b9489e659d83d99a9829ef88876643f3e8f8aa276fee6d96a9cdf','0a84003a5e6a27cc445e835673d4f5030cbc19cb6b130037eaed922340d34d77',array['postgres=X/postgres','service_role=X/postgres']::text[])
  ) expected(identity,predecessor_sha256,installed_sha256,acl)
  loop
    select * into c from erp.cp6_v2620ab_rollback_capsule
      where object_regidentity=r.identity;
    if c.object_regidentity is null
       or c.definition_sha256 is distinct from r.predecessor_sha256
       or encode(extensions.digest(convert_to(c.object_definition,'UTF8'),'sha256'),'hex')
            is distinct from r.predecessor_sha256
       or c.installed_definition_sha256 is distinct from r.installed_sha256
       or c.owner_snapshot is distinct from 'postgres' or c.acl_snapshot is distinct from r.acl
       or encode(extensions.digest(convert_to(pg_get_functiondef(
            to_regprocedure(r.identity)),'UTF8'),'sha256'),'hex') is distinct from r.installed_sha256
       or (select pg_get_userbyid(proowner) from pg_proc
            where oid=to_regprocedure(r.identity)) is distinct from 'postgres'
       or (select array(select a::text from unnest(proacl) a order by a::text)
            from pg_proc where oid=to_regprocedure(r.identity)) is distinct from r.acl then
      raise exception 'AB_INSTALLED_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity;
    end if;
  end loop;

end
$installed_v2620ab$;

do $boundary_v2620ab$
declare v_table text;v_hash text;v_snapshot jsonb:='{}';
begin
  for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in('r','p') and c.relname not in('schema_migrations','cp6_v2620ab_rollback_capsule') order by c.relname loop
    execute format($sql$select encode(extensions.digest(convert_to(
      coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),'sha256'),'hex')
      from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,'UTF8'),
        'sha256'),'hex') row_hash from erp.%I t) rows$sql$,v_table) into v_hash;
    v_snapshot:=v_snapshot||jsonb_build_object(v_table,v_hash);
  end loop;
  if (select count(*) from jsonb_object_keys(v_snapshot))<>213 then
    raise exception 'AB_FULL_ERP_BOUNDARY_CARDINALITY expected213 actual%',
      (select count(*) from jsonb_object_keys(v_snapshot));
  end if;
  update erp.cp6_v2620ab_rollback_capsule set boundary_snapshot=v_snapshot;
end
$boundary_v2620ab$;

insert into erp.schema_migrations(version,description)
values('v2.6.20ab','Command-time Jakarta recost and posting dates; linked reversal date and journal posting timestamp remain consistent across long transactions');
commit;
