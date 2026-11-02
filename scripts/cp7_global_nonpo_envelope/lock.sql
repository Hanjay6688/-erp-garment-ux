-- Private primitive only: final-parent gate, source binding, owning operation
-- scope, no-op inspector/review and outside completion are separate obligations.
create function cp7_global_nonpo_envelope.lock_v1(p_profile text)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare profile_ cp7_global_nonpo_envelope.profiles;catalogs_ jsonb;actual_ jsonb;
 entry_ jsonb;item_ record;transactions_ jsonb;authority_ jsonb;authority_hash_ text;
 required_ text[]:=array[
  'cp7_credit.cohorts','cp7_credit.consumption_events','cp7_credit.return_families','cp7_note.revisions',
  'erp.accounting_account_mappings','erp.accounting_period_control',
  'erp.app_permissions','erp.app_role_permissions','erp.app_roles','erp.app_users',
  'erp.bc_adjustment_purposes_v1','erp.bc_document_links_v1','erp.bc_documents_v1','erp.bc_lot_events_v1',
  'erp.bc_outstanding_returns_v1','erp.bc_return_lots_v1','erp.be_conversion_cost_events_v1',
  'erp.be_conversion_cost_sources_v1','erp.be_conversion_returns_v1','erp.be_conversion_sources_v1',
  'erp.be_execution_context_v1','erp.be_nonpo_transfer_events_v1','erp.chart_accounts',
  'erp.fg_inventory_balances','erp.fg_lots','erp.fg_stock_movements','erp.hpp_version_components',
  'erp.hpp_versions','erp.journal_entries','erp.journal_lines','erp.material_adjustments',
  'erp.non_po_hpp_gl_sync_events_v2620f','erp.opening_hpp_corrections','erp.opening_lot_hpp_gl_state',
  'erp.po_hpp_gl_state','erp.product_conversion_allocations','erp.product_conversions',
  'erp.sale_stock_allocations','erp.sales_headers','erp.sales_items','erp.sales_return_items','erp.sales_returns'];
begin
 if current_setting('transaction_isolation')<>'read committed'then
  raise exception 'CP7_GLOBAL_FRESH_CURRENT_READ_COMMITTED_REQUIRED';end if;
 select *into profile_ from cp7_global_nonpo_envelope.profiles where id=p_profile;
 if profile_.id is null then raise exception 'CP7_GLOBAL_ACTUAL_FINAL_PARENT_PROFILE_PENDING';end if;
 if jsonb_array_length(profile_.expected_relations)<>(select count(distinct (e->>0)||'.'||(e->>1))
   from jsonb_array_elements(profile_.expected_relations)e)
  or exists(select 1 from unnest(required_)name_ where not exists(
   select 1 from jsonb_array_elements(profile_.expected_relations)e where (e->>0)||'.'||(e->>1)=name_))then
  raise exception 'CP7_GLOBAL_COMPLETE_EXACT_RELATION_PROFILE_REQUIRED';end if;

 -- First freeze the identity universe used to enumerate all actual catalog
 -- tables. Old uncommitted catalog writers are checked by permanent XID locks.
 lock table pg_catalog.pg_class,pg_catalog.pg_namespace in share mode nowait;
 select coalesce(jsonb_agg(jsonb_build_array(n.nspname,c.relname,c.relkind::text,
   c.relpersistence::text,pg_get_userbyid(c.relowner),c.relrowsecurity,c.relforcerowsecurity,
   case when c.relacl is null then null else to_jsonb(array(
    select a::text from unnest(c.relacl)a order by a::text collate "C"))end)
   order by n.nspname collate "C",c.relname collate "C"),'[]'::jsonb)
 into catalogs_ from pg_catalog.pg_class c join pg_catalog.pg_namespace n on n.oid=c.relnamespace
 where n.nspname='pg_catalog'and c.relkind in('r','p');
 if catalogs_ is distinct from profile_.expected_catalogs then
  raise exception 'CP7_GLOBAL_SYSTEM_CATALOG_IDENTITY_OR_AUTHORITY_CHANGED';end if;
 for entry_ in select value from jsonb_array_elements(catalogs_)loop
  execute format('lock table %I.%I in share mode nowait',entry_->>0,entry_->>1);
 end loop;

 -- EXCLUSIVE also conflicts with existing FK/SELECT FOR UPDATE RowShareLock.
 -- Ordinary SELECT remains available. All acquisition is NOWAIT; callers keep
 -- their existing request/CAS, pocket TRY, FG and FGBOOK order before this call.
 for entry_ in select value from jsonb_array_elements(profile_.expected_relations)
  order by (value->>0) collate "C",(value->>1) collate "C"loop
  if jsonb_typeof(entry_)<>'array'or jsonb_array_length(entry_)<>8
   or entry_->>2 not in('r','p')then raise exception 'CP7_GLOBAL_TYPED_RELATION_PROFILE_REQUIRED';end if;
  execute format('lock table %I.%I in exclusive mode nowait',entry_->>0,entry_->>1);
  select jsonb_build_array(n.nspname,c.relname,c.relkind::text,c.relpersistence::text,
   pg_get_userbyid(c.relowner),c.relrowsecurity,c.relforcerowsecurity,
   case when c.relacl is null then null else to_jsonb(array(
    select a::text from unnest(c.relacl)a order by a::text collate "C"))end)
  into actual_ from pg_catalog.pg_class c join pg_catalog.pg_namespace n on n.oid=c.relnamespace
  where n.nspname=entry_->>0 and c.relname=entry_->>1;
  if actual_ is distinct from entry_ then raise exception 'CP7_GLOBAL_RELATION_IDENTITY_OR_AUTHORITY_CHANGED';end if;
 end loop;

 -- Snapshot xip is NOT a complete enumeration of unfinished transactions.
 -- Permanent transaction-ID ExclusiveLocks last until transaction completion,
 -- are non-fastpath regular lock-manager rows, and include prepared pid=NULL.
 select coalesce(jsonb_agg(jsonb_build_array(pid,transactionid::text,mode,granted,fastpath)
   order by pid nulls first,transactionid::text),'[]'::jsonb)into transactions_
 from pg_catalog.pg_locks where locktype='transactionid'and mode='ExclusiveLock'and granted
  and pid is distinct from pg_backend_pid();
 if transactions_<>'[]'::jsonb then
  raise exception using errcode='55P03',message='CP7_GLOBAL_PREEXISTING_TRANSACTION_REVIEW_AGAIN';end if;

 -- Preserve the exact Native nonPO/nonvoided visit order. No cost propagation,
 -- transfer, global sync, journal, audit sequence, UUID or speculative write.
 for item_ in select id from erp.fg_lots where po_id is null
  and lot_origin<>'VOIDED_PRODUCTION'order by id for update nowait loop null;end loop;
 authority_:=cp7_global_nonpo_native_graph.authority_v1();
 if authority_->'known_functions_exact'is distinct from'true'::jsonb
  or authority_#>'{view,exact_known_source}'is distinct from'true'::jsonb
  or authority_->'new_private_acl_closed'is distinct from'true'::jsonb then
  raise exception 'CP7_GLOBAL_EXACT_CURRENT_NATIVE_AUTHORITY_REQUIRED';end if;
 authority_hash_:=encode(extensions.digest(convert_to((authority_-array[
  'session_user','current_user','runtime_entry','required_final_parent',
  'actual_Native_qualification_credit','production_go'])::text,'UTF8'),'sha256'),'hex');
 if authority_hash_ is distinct from profile_.native_authority_sha256 then
  raise exception 'CP7_GLOBAL_FINAL_NATIVE_AUTHORITY_PROFILE_CHANGED';end if;
 return jsonb_build_object('contract','cp7.global-nonpo-envelope-lock.v1','profile',profile_.id,
  'parent_head',profile_.parent_head,'parent_tree',profile_.parent_tree,
  'catalog_tables',jsonb_array_length(catalogs_),'relation_tables',jsonb_array_length(profile_.expected_relations),
  'catalog_mode','SHARE','relation_mode','EXCLUSIVE','all_acquisition_NOWAIT',true,
  'other_permanent_transaction_ID_locks',transactions_,'native_authority_sha256',authority_hash_,
  'owning_scope_and_review_and_noop_and_completion_still_required',true);
end $$;
alter function cp7_global_nonpo_envelope.lock_v1(text)owner to postgres;
revoke all on function cp7_global_nonpo_envelope.lock_v1(text)from public,anon,authenticated,service_role;
