-- CP6 AN: independently paged PO/draft selectors with selected-row continuity.
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

do $lock_all_erp_v2620an$
declare v_table text;
begin
  for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in('r','p') and c.relname not in('schema_migrations','cp6_v2620an_rollback_capsule') order by c.relname loop
    execute format('lock table erp.%I in share row exclusive mode',v_table);
  end loop;
end
$lock_all_erp_v2620an$;


do $predecessor_v2620an$
declare r record;v_actual text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20am')
     or exists(select 1 from erp.schema_migrations where version='v2.6.20an')
     or to_regclass('erp.cp6_v2620an_rollback_capsule') is not null
     or to_regclass('erp.cp6_v2620am_rollback_capsule') is null
     or to_regprocedure('erp.get_cutting_workspace_v2(text,uuid,integer,integer,text,integer,integer,text,integer,integer,uuid,uuid)') is not null or to_regprocedure('public.erp_get_cutting_workspace_v2(text,uuid,integer,integer,text,integer,integer,text,integer,integer,uuid,uuid)') is not null then
    raise exception 'AN_REQUIRES_EXACT_AM_WITHOUT_AN_RESIDUE'; end if;
  if (select count(*) from supabase_migrations.schema_migrations where name='erp_v2_6_20am_cp6_transfer_integrity')<>1
     or not exists(select 1 from supabase_migrations.schema_migrations where version='20260921214120' and name='erp_v2_6_20am_cp6_transfer_integrity'
       and encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),'UTF8'),'sha256'),'hex')='d5b155edb19aa8ca949036ba8a9cf67090478083c2e1ae6cc5bbf00b445716a5')
     or exists(select 1 from supabase_migrations.schema_migrations where version>'20260921214120')
     or (select count(*) from erp.cp6_v2620am_rollback_capsule)<>6 then raise exception 'AN_REQUIRES_EXACT_AM_PLATFORM_CAPSULE'; end if;
  for r in select * from(values
    ('erp.get_cutting_workspace_v1(text,uuid,integer,integer)','36ca262701b1fd2f7b64be6fd48ed1aa990e856d668bc4f401760c789e1379d9',array['postgres=X/postgres']::text[])
  ) expected(identity,sha256,acl) loop
    select encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') into v_actual
    from pg_proc p where p.oid=to_regprocedure(r.identity) and pg_get_userbyid(p.proowner)='postgres'
      and array(select a::text from unnest(p.proacl) a order by a::text)=r.acl;
    if v_actual is distinct from r.sha256 then raise exception 'AN_PREDECESSOR_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity; end if;
  end loop;
end
$predecessor_v2620an$;


create table erp.cp6_v2620an_rollback_capsule(
  like erp.cp6_v2620am_rollback_capsule including all
);
alter table erp.cp6_v2620an_rollback_capsule enable row level security;
revoke all on erp.cp6_v2620an_rollback_capsule from public,anon,authenticated,service_role;
insert into erp.cp6_v2620an_rollback_capsule(
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
where p.oid='erp.get_cutting_workspace_v1(text,uuid,integer,integer)'::regprocedure;


do $canonical_reader_v2620an$
begin
  execute $definition$CREATE OR REPLACE FUNCTION erp.get_cutting_workspace_v2(p_roll_query text DEFAULT NULL::text, p_location_id uuid DEFAULT NULL::uuid, p_limit integer DEFAULT 100, p_offset integer DEFAULT 0, p_order_query text DEFAULT NULL::text, p_order_limit integer DEFAULT 50, p_order_offset integer DEFAULT 0, p_draft_query text DEFAULT NULL::text, p_draft_limit integer DEFAULT 25, p_draft_offset integer DEFAULT 0, p_selected_order_id uuid DEFAULT NULL::uuid, p_selected_draft_id uuid DEFAULT NULL::uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare v_query text:=lower(nullif(btrim(p_roll_query),''));
  v_order_query text:=lower(nullif(btrim(p_order_query),''));
  v_draft_query text:=lower(nullif(btrim(p_draft_query),''));
  v_order jsonb;
  v_draft jsonb;
begin
  perform erp.require_permission('production.cutting.view');
  if p_limit is null or p_limit<1 or p_limit>200 then raise exception 'limit must be between 1 and 200'; end if;
  if p_offset is null or p_offset<0 then raise exception 'offset must be nonnegative'; end if;
  if p_location_id is not null and not exists(
    select 1 from erp.locations l where l.id=p_location_id and l.is_active and l.location_type='RAW_MATERIAL_WAREHOUSE'
  ) then raise exception 'Active raw-material warehouse is required'; end if;

  if p_order_limit is null or p_order_limit<1 or p_order_limit>200
     or p_draft_limit is null or p_draft_limit<1 or p_draft_limit>100
     or p_order_offset is null or p_order_offset<0
     or p_draft_offset is null or p_draft_offset<0 then
    raise exception 'AN_INVALID_SELECTOR_PAGE';
  end if;
  if length(p_order_query)>200 or length(p_draft_query)>200 then
    raise exception 'AN_SELECTOR_QUERY_TOO_LONG';
  end if;

  with eligible as not materialized (
        select po.id,po.po_number,po.model_id,m.model_code,m.model_name,
          po.status,po.current_stage,po.contractor_id,c.contractor_name
        from erp.production_orders po
        join erp.product_models m on m.id=po.model_id
        left join erp.contractors c on c.id=po.contractor_id
        where po.status not in ('FINISHED','CANCELLED')
  ), page as (
    select * from eligible where (v_order_query is null or strpos(lower(concat_ws(' ',po_number,model_code,model_name,contractor_name)),v_order_query)>0)
    order by po_number,id limit p_order_limit offset p_order_offset
  ), targets as (
    select * from page union select * from eligible where id=p_selected_order_id
  ), serialized as (
    select x.id,x.po_number,
      jsonb_build_object(
        'id',x.id,'po_number',x.po_number,'model_id',x.model_id,
        'model_code',x.model_code,'model_name',x.model_name,
        'status',x.status,'current_stage',x.current_stage,
        'contractor_id',x.contractor_id,'contractor_name',x.contractor_name
      ) as datum from targets x
  )
  select jsonb_build_object(
    'query',v_order_query,'limit',p_order_limit,'offset',p_order_offset,
    'total',(select count(*) from eligible where (v_order_query is null or strpos(lower(concat_ws(' ',po_number,model_code,model_name,contractor_name)),v_order_query)>0)),
    'rows',coalesce((select jsonb_agg(s.datum order by s.po_number,s.id)
      from serialized s join page p on p.id=s.id),'[]'::jsonb),
    'selected',(select datum from serialized where id=p_selected_order_id)
  ) into v_order;

  with eligible as not materialized (
        select g.*,po.model_id,po.po_number,pm.model_code,pm.model_name,p.is_active pattern_is_active,
          erp.is_cutting_group_presewing_reversible(g.id) editable
        from erp.cutting_groups g
        join erp.production_orders po on po.id=g.po_id
        join erp.product_models pm on pm.id=po.model_id
        left join erp.production_patterns p on p.id=g.pattern_id
        where g.status='CUT' and g.picked_up_at is null and not g.material_issue_posted
  ), page as (
    select * from eligible where (v_draft_query is null or strpos(lower(concat_ws(' ',group_number,po_number,model_code,model_name,pattern_code_snapshot,pattern_revision_snapshot,pattern_name_snapshot)),v_draft_query)>0)
    order by updated_at desc,id desc limit p_draft_limit offset p_draft_offset
  ), targets as (
    select * from page union select * from eligible where id=p_selected_draft_id
  ), serialized as (
    select x.id,x.po_number,x.updated_at,
      jsonb_build_object(
        'cutting_group_id',x.id,'group_number',x.group_number,'row_version',x.row_version,
        'model_id',x.model_id,'po_id',x.po_id,'po_number',x.po_number,'model_code',x.model_code,'model_name',x.model_name,
        'cut_at',x.cut_at,'source_location_id',x.source_location_id,'notes',x.notes,
        'pattern_id',x.pattern_id,'pattern_code',x.pattern_code_snapshot,
        'pattern_revision',x.pattern_revision_snapshot,'pattern_name',x.pattern_name_snapshot,
        'pattern_is_active',x.pattern_is_active,'editable',x.editable,
        'size_slots',coalesce((
          select jsonb_agg(jsonb_build_object(
            'slot_no',ss.slot_no,'size_id',ss.size_id,'size_code',sz.size_code,
            'drawing_no',ss.drawing_no,'label_override',ss.label_override
          ) order by ss.slot_no,ss.id)
          from erp.cutting_group_size_slots ss join erp.sizes sz on sz.id=ss.size_id
          where ss.cutting_group_id=x.id
        ),'[]'::jsonb),
        'rolls',coalesce((
          select jsonb_agg(jsonb_build_object(
            'roll_id',r.roll_id,'roll_number',mr.roll_number,'material_id',mr.material_id,
            'material_sku',m.material_sku,'material_name',m.material_name,'unit_code',m.unit_code,
            'supplier_id',mr.supplier_id,'supplier_name',s.supplier_name,
            'original_qty',mr.original_qty,'qty_issued',r.qty_issued,
            'qty_consumed',coalesce(r.qty_consumed,r.qty_issued),
            'qty_reported_remaining',coalesce(r.qty_reported_remaining,greatest(r.qty_issued-coalesce(r.qty_consumed,r.qty_issued),0)),
            'yields',coalesce((
              select jsonb_agg(jsonb_build_object('slot_no',ss.slot_no,'qty_pcs',y.qty_pcs)
                order by ss.slot_no,y.id)
              from erp.cutting_roll_yields y
              join erp.cutting_group_size_slots ss on ss.id=y.size_slot_id
              where y.cutting_group_roll_id=r.id
            ),'[]'::jsonb)
          ) order by m.material_name,mr.roll_number,mr.id)
          from erp.cutting_group_rolls r
          join erp.material_rolls mr on mr.id=r.roll_id
          join erp.materials m on m.id=mr.material_id
          left join erp.suppliers s on s.id=mr.supplier_id
          where r.cutting_group_id=x.id
        ),'[]'::jsonb)
      ) as datum from targets x
  )
  select jsonb_build_object(
    'query',v_draft_query,'limit',p_draft_limit,'offset',p_draft_offset,
    'total',(select count(*) from eligible where (v_draft_query is null or strpos(lower(concat_ws(' ',group_number,po_number,model_code,model_name,pattern_code_snapshot,pattern_revision_snapshot,pattern_name_snapshot)),v_draft_query)>0)),
    'rows',coalesce((select jsonb_agg(s.datum order by s.updated_at desc,s.id desc)
      from serialized s join page p on p.id=s.id),'[]'::jsonb),
    'selected',(select datum from serialized where id=p_selected_draft_id)
  ) into v_draft;

  return jsonb_build_object(
    'contract_version',2,
    'order_page',v_order-'rows'-'selected','draft_page',v_draft-'rows'-'selected',
    'selected_order_id',p_selected_order_id,'selected_order',v_order->'selected',
    'selected_draft_id',p_selected_draft_id,'selected_draft',v_draft->'selected',
    'roll_query',v_query,'location_id',p_location_id,'limit',p_limit,'offset',p_offset,
    'orders',v_order->'rows',
    'sizes',coalesce((
      select jsonb_agg(jsonb_build_object(
          'id',s.id,'code',s.size_code,'sort_order',s.sort_order,
          'model_ids',coalesce((
            select jsonb_agg(pms.model_id order by pms.sort_order,pms.model_id)
            from erp.product_model_sizes pms where pms.size_id=s.id
          ),'[]'::jsonb)
        )
        order by s.sort_order,s.size_code,s.id)
      from erp.sizes s where s.is_active
    ),'[]'::jsonb),
    'locations',coalesce((
      select jsonb_agg(jsonb_build_object('id',l.id,'code',l.location_code,'name',l.location_name)
        order by l.location_code,l.id)
      from erp.locations l where l.is_active and l.location_type='RAW_MATERIAL_WAREHOUSE'
    ),'[]'::jsonb),
    'contractors',coalesce((
      select jsonb_agg(jsonb_build_object('id',c.id,'code',c.contractor_code,'name',c.contractor_name)
        order by c.contractor_name,c.contractor_code,c.id)
      from erp.contractors c where c.is_active and c.contractor_type='MANDOR'
    ),'[]'::jsonb),
    'drafts',v_draft->'rows',
    'roll_total',case when p_location_id is null then 0 else (
      with stock as (
        select msm.roll_id,sum(msm.qty_signed)::numeric available_qty
        from erp.material_stock_movements msm
        where msm.location_id=p_location_id and msm.roll_id is not null
        group by msm.roll_id having sum(msm.qty_signed)>0
      )
      select count(*) from stock st
      join erp.material_rolls r on r.id=st.roll_id
      join erp.materials m on m.id=r.material_id
      left join erp.suppliers s on s.id=r.supplier_id
      where r.status in ('AVAILABLE','HALF_USED')
        and (v_query is null or lower(concat_ws(' ',r.roll_number,m.material_sku,m.material_name,s.supplier_code,s.supplier_name)) like '%'||v_query||'%')
    ) end,
    'rolls',case when p_location_id is null then '[]'::jsonb else coalesce((
      with stock as (
        select msm.roll_id,sum(msm.qty_signed)::numeric available_qty
        from erp.material_stock_movements msm
        where msm.location_id=p_location_id and msm.roll_id is not null
        group by msm.roll_id having sum(msm.qty_signed)>0
      )
      select jsonb_agg(jsonb_build_object(
        'id',x.id,'roll_number',x.roll_number,'material_id',x.material_id,
        'material_sku',x.material_sku,'material_name',x.material_name,'unit_code',x.unit_code,
        'supplier_id',x.supplier_id,'supplier_code',x.supplier_code,'supplier_name',x.supplier_name,
        'original_qty',x.original_qty,'available_qty',x.available_qty,'status',x.status,
        'received_at',x.received_at
      ) order by x.material_name,x.roll_number,x.id)
      from (
        select r.id,r.roll_number,r.material_id,m.material_sku,m.material_name,m.unit_code,
          r.supplier_id,s.supplier_code,s.supplier_name,r.original_qty,st.available_qty,r.status,r.received_at
        from stock st
        join erp.material_rolls r on r.id=st.roll_id
        join erp.materials m on m.id=r.material_id
        left join erp.suppliers s on s.id=r.supplier_id
        where r.status in ('AVAILABLE','HALF_USED')
          and (v_query is null or lower(concat_ws(' ',r.roll_number,m.material_sku,m.material_name,s.supplier_code,s.supplier_name)) like '%'||v_query||'%')
        order by m.material_name,r.roll_number,r.id limit p_limit offset p_offset
      ) x
    ),'[]'::jsonb) end
  );
end
$function$
$definition$;
  execute $definition$CREATE OR REPLACE FUNCTION public.erp_get_cutting_workspace_v2(p_roll_query text DEFAULT NULL::text, p_location_id uuid DEFAULT NULL::uuid, p_limit integer DEFAULT 100, p_offset integer DEFAULT 0, p_order_query text DEFAULT NULL::text, p_order_limit integer DEFAULT 50, p_order_offset integer DEFAULT 0, p_draft_query text DEFAULT NULL::text, p_draft_limit integer DEFAULT 25, p_draft_offset integer DEFAULT 0, p_selected_order_id uuid DEFAULT NULL::uuid, p_selected_draft_id uuid DEFAULT NULL::uuid)
 RETURNS jsonb
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
  select erp.get_cutting_workspace_v2(p_roll_query, p_location_id, p_limit, p_offset, p_order_query, p_order_limit, p_order_offset, p_draft_query, p_draft_limit, p_draft_offset, p_selected_order_id, p_selected_draft_id);
$function$
$definition$;
end
$canonical_reader_v2620an$;
revoke all on function erp.get_cutting_workspace_v2(text,uuid,integer,integer,text,integer,integer,text,integer,integer,uuid,uuid),public.erp_get_cutting_workspace_v2(text,uuid,integer,integer,text,integer,integer,text,integer,integer,uuid,uuid) from public,anon,authenticated,service_role;
grant execute on function public.erp_get_cutting_workspace_v2(text,uuid,integer,integer,text,integer,integer,text,integer,integer,uuid,uuid) to authenticated,service_role;
do $new_readers_v2620an$
declare r record;v_actual text;
begin
  for r in select * from(values
    ('erp.get_cutting_workspace_v2(text,uuid,integer,integer,text,integer,integer,text,integer,integer,uuid,uuid)','','0720b6eaf531b3fa491ba26b665aa7844714e219b5670f4ef0fd89daf0dcd032',array['postgres=X/postgres']::text[]),
    ('public.erp_get_cutting_workspace_v2(text,uuid,integer,integer,text,integer,integer,text,integer,integer,uuid,uuid)','','d99901ec3e83ec80b4fa90f35c2565074318f61337e3ff3fec9c7fc6e43fe76b',array['authenticated=X/postgres','postgres=X/postgres','service_role=X/postgres']::text[])
  ) expected(identity,predecessor_sha256,installed_sha256,acl) loop
    select encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex') into v_actual
    from pg_proc p where p.oid=to_regprocedure(r.identity) and pg_get_userbyid(p.proowner)='postgres'
      and array(select a::text from unnest(p.proacl) a order by a::text)=r.acl;
    if v_actual is distinct from r.installed_sha256 then raise exception 'AN_NEW_READER_DRIFT: %',r.identity; end if;
  end loop;
end
$new_readers_v2620an$;


do $installed_v2620an$
declare r record;c record;
begin
  if (select count(*) from erp.cp6_v2620an_rollback_capsule)<>1 then
    raise exception 'AN_CAPSULE_CARDINALITY_MISMATCH';
  end if;
  update erp.cp6_v2620an_rollback_capsule cap set installed_definition_sha256=
    encode(extensions.digest(convert_to(pg_get_functiondef(
      to_regprocedure(cap.object_regidentity)),'UTF8'),'sha256'),'hex');
  for r in select * from(values
    ('erp.get_cutting_workspace_v1(text,uuid,integer,integer)','36ca262701b1fd2f7b64be6fd48ed1aa990e856d668bc4f401760c789e1379d9','36ca262701b1fd2f7b64be6fd48ed1aa990e856d668bc4f401760c789e1379d9',array['postgres=X/postgres']::text[])
  ) expected(identity,predecessor_sha256,installed_sha256,acl)
  loop
    select * into c from erp.cp6_v2620an_rollback_capsule
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
      raise exception 'AN_INSTALLED_FUNCTION_OWNER_ACL_MISMATCH: %',r.identity;
    end if;
  end loop;

end
$installed_v2620an$;

do $boundary_v2620an$
declare v_table text;v_hash text;v_snapshot jsonb:='{}';
begin
  for v_table in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in('r','p') and c.relname not in('schema_migrations','cp6_v2620an_rollback_capsule') order by c.relname loop
    execute format($sql$select encode(extensions.digest(convert_to(
      coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),'sha256'),'hex')
      from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,'UTF8'),
        'sha256'),'hex') row_hash from erp.%I t) rows$sql$,v_table) into v_hash;
    v_snapshot:=v_snapshot||jsonb_build_object(v_table,v_hash);
  end loop;
  if (select count(*) from jsonb_object_keys(v_snapshot))<>226 then
    raise exception 'AN_FULL_ERP_BOUNDARY_CARDINALITY expected226 actual%',
      (select count(*) from jsonb_object_keys(v_snapshot));
  end if;
  update erp.cp6_v2620an_rollback_capsule set boundary_snapshot=v_snapshot;
end
$boundary_v2620an$;

insert into erp.schema_migrations(version,description)
values('v2.6.20an','Independent PO and draft search pagination preserve selected rows without changing writes or financial policy');
commit;
