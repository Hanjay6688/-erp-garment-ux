-- ERP v2.6.19a / CP5 selected-accessory, partial-return, accounting, and reversal proof.
-- Every synthetic row and journal is enclosed by this transaction.
\set ON_ERROR_STOP on

begin;
set local timezone='UTC';
set local datestyle='ISO, MDY';
set local lock_timeout='8s';
set local statement_timeout='180s';

\ir cp3_r4_full_schema_seed.sql

do $test$
declare
  v_owner_app constant uuid:='c9000000-0000-4000-8000-000000000001';
  v_owner_auth constant uuid:='c9000000-0000-4000-8000-000000000101';
  v_production_app constant uuid:='c9000000-0000-4000-8000-000000000002';
  v_production_auth constant uuid:='c9000000-0000-4000-8000-000000000102';
  v_brand constant uuid:='c9010000-0000-4000-8000-000000000001';
  v_product constant uuid:='c9010000-0000-4000-8000-000000000002';
  v_location constant uuid:='c9010000-0000-4000-8000-000000000003';
  v_vendor constant uuid:='c9010000-0000-4000-8000-000000000004';
  v_po constant uuid:='c9020000-0000-4000-8000-000000000001';
  v_batch constant uuid:='c9020000-0000-4000-8000-000000000002';
  v_group constant uuid:='c9020000-0000-4000-8000-000000000003';
  v_work_snapshot constant uuid:='c9020000-0000-4000-8000-000000000004';
  v_bom constant uuid:='c9030000-0000-4000-8000-000000000001';
  v_category_a constant uuid:='c9030000-0000-4000-8000-000000000002';
  v_category_b constant uuid:='c9030000-0000-4000-8000-000000000003';
  v_item_a constant uuid:='c9030000-0000-4000-8000-000000000004';
  v_item_b constant uuid:='c9030000-0000-4000-8000-000000000005';
  v_rework_bs constant uuid:='c9040000-0000-4000-8000-000000000001';
  v_none_bs constant uuid:='c9040000-0000-4000-8000-000000000002';
  v_rewash_bs constant uuid:='c9040000-0000-4000-8000-000000000003';
  v_manual_replacement_bs constant uuid:='c9040000-0000-4000-8000-000000000004';
  v_complete_request constant uuid:='c9050000-0000-4000-8000-000000000001';
  v_response jsonb;
  v_replay jsonb;
  v_payload jsonb;
  v_workspace jsonb;
  v_component uuid;
  v_rework uuid;
  v_rework_version bigint;
  v_lot uuid;
  v_none_rework uuid;
  v_none_version bigint;
  v_none_lot uuid;
  v_rewash uuid;
  v_rewash_version bigint;
  v_rewash_lot uuid;
  v_failed boolean;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.19a')
     or not exists(select 1 from erp.schema_migrations where version='v2.6.19b')
     or to_regclass('erp.rework_accessory_decisions') is null
     or to_regclass('erp.rework_accessory_selection_lines') is null
     or to_regclass('erp.bs_resolution_v2619b_rollback_capsule') is null
     or to_regprocedure('erp.resolve_rework_accessory_bom_v1(uuid,timestamp with time zone)') is null then
    raise exception 'CP5 v2.6.19a selected-accessory boundary is not installed';
  end if;
  if has_table_privilege('authenticated','erp.rework_accessory_decisions','SELECT,INSERT,UPDATE,DELETE')
     or has_function_privilege('authenticated','erp.resolve_rework_accessory_bom_v1(uuid,timestamp with time zone)','EXECUTE') then
    raise exception 'CP5 v2.6.19a private lineage boundary is open';
  end if;

  insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active)
  select v_owner_app,v_owner_auth,'CP5 Lineage Owner','OWNER',id,true
  from erp.app_roles where role_code='OWNER';
  insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active)
  select v_production_app,v_production_auth,'CP5 Lineage Production','PRODUKSI_QC',id,true
  from erp.app_roles where role_code='PRODUKSI_QC';
  insert into erp.brands(id,brand_code,brand_name)
  values(v_brand,'CP5-LINEAGE','CP5 Accessory Lineage Brand');
  insert into erp.locations(id,location_code,location_name,location_type)
  values(v_location,'CP5-LINEAGE-FG','CP5 Lineage FG','FG_WAREHOUSE');
  insert into erp.laundry_vendors(id,vendor_code,vendor_name,is_active,notes)
  values(v_vendor,'CP5-LINEAGE-LDR','CP5 Lineage Laundry',true,'Zero-fee rewash proof');
  insert into erp.products(
    id,sku,model_id,brand_id,color_name,size_id,product_name,
    identity_root_id,effective_from,is_active
  ) values(
    v_product,'CP5-LINEAGE-SKU','a2000000-0000-0000-0000-000000000001',
    v_brand,'LINEAGE','a2100000-0000-0000-0000-000000000001',
    'CP5 Lineage Product',v_product,'2026-01-01 00:00:00+00',true
  );
  insert into erp.production_orders(
    id,po_number,model_id,contractor_id,target_qty_pcs,status,current_stage,
    physical_start_at,notes
  ) values(
    v_po,'CP5-LINEAGE-PO','a2000000-0000-0000-0000-000000000001',
    'a1000000-0000-0000-0000-000000000001',8,'CUTTING','CUTTING',
    '2026-08-24 07:00:00+00','CP5 selected accessory proof'
  );
  insert into erp.cutting_batches(id,po_id,batch_number,cut_at,status,notes)
  values(v_batch,v_po,'CP5-LINEAGE-BATCH','2026-08-24 07:30:00+00','OPEN','CP5 proof');
  insert into erp.cutting_groups(
    id,po_id,group_number,cut_at,status,cutting_batch_id,notes
  ) values(
    v_group,v_po,'CP5-LINEAGE-GROUP','2026-08-24 07:30:00+00','CUT',
    v_batch,'CP5 selected accessory proof'
  );
  insert into erp.po_work_component_snapshots(
    id,po_id,work_component_id,sequence_no,rate_per_pcs_snapshot,committed_at
  ) values(
    v_work_snapshot,v_po,'a4000000-0000-0000-0000-000000000001',1,5,
    '2026-08-24 07:45:00+00'
  );
  insert into erp.accessory_categories(
    id,category_code,category_name,base_uom_code,is_active,notes
  ) values
    (v_category_a,'CP5-BUTTON','Button','PCS',true,'Selected in contractor rework'),
    (v_category_b,'CP5-LABEL','Label','PCS',true,'Selected only in rewash');
  insert into erp.accessory_bom_versions(
    id,product_id,version_label,effective_from,is_active,notes,created_by
  ) values(
    v_bom,v_product,'CP5-LINEAGE-V1','2026-01-01 00:00:00+00',true,
    'Two-line immutable choice proof',v_owner_app
  );
  insert into erp.accessory_bom_items(
    id,bom_version_id,category_id,qty_per_good_fg_base,hpp_method,
    hpp_standard_rate,hpp_uom_code,reimbursement_rate,
    reimbursement_uom_code,notes
  ) values
    (v_item_a,v_bom,v_category_a,2,'BOM_STANDARD',10,'PCS',15,'PCS','Selected A'),
    (v_item_b,v_bom,v_category_b,1,'BOM_STANDARD',4,'PCS',7,'PCS','Unselected B');

  perform set_config('app.change_reason','CP5 v2.6.19a synthetic BS cases',true);
  insert into erp.bs_cases(
    id,bs_number,po_id,cutting_group_id,product_id,detected_at_stage,
    cause_source,responsible_contractor_id,responsible_vendor_id,
    qty_pcs,status,physical_at,notes
  ) values
    (v_rework_bs,'CP5-LINEAGE-REWORK-BS',v_po,v_group,v_product,'QC','SEWING',
     'a1000000-0000-0000-0000-000000000001',null,4,'OPEN','2026-08-24 08:00:00+00','Mixed positive GOOD'),
    (v_none_bs,'CP5-LINEAGE-NONE-BS',v_po,v_group,v_product,'QC','SEWING',
     'a1000000-0000-0000-0000-000000000001',null,2,'OPEN','2026-08-24 08:01:00+00','Explicit no accessory'),
    (v_rewash_bs,'CP5-LINEAGE-REWASH-BS',v_po,v_group,v_product,'LAUNDRY','LAUNDRY',
     null,v_vendor,2,'OPEN','2026-08-24 08:02:00+00','Rewash selected accessory'),
    (v_manual_replacement_bs,'CP5-MANUAL-REPLACEMENT-BS',v_po,v_group,v_product,'WAREHOUSE','UNKNOWN',
     null,null,1,'OPEN','2026-08-24 08:03:00+00','Post-FG baseline is not automatically reimbursable');

  perform set_config('request.jwt.claims',jsonb_build_object(
    'sub',v_production_auth,'role','authenticated'
  )::text,true);
  execute 'set local role authenticated';

  v_workspace:=public.erp_get_bs_resolution_workspace_v1(
    'ACTIVE','BS',null,'CP5-LINEAGE-REWORK-BS',50,0
  );
  if v_workspace#>>'{rows,0,accessory_bom,state}'<>'AVAILABLE'
     or v_workspace#>>'{rows,0,accessory_bom,bom_version_id}'<>v_bom::text
     or v_workspace#>>'{rows,0,accessory_bom,default_policy}'<>'SERVER_ENTITLEMENT_V2619B'
     or jsonb_array_length(v_workspace#>'{rows,0,accessory_bom,items}')<>2
     or exists(
       select 1 from jsonb_array_elements(v_workspace#>'{rows,0,accessory_bom,items}') x
       where (x->>'default_selected')::boolean is not true
         or x->>'default_selection_basis'<>'UNPAID_BASELINE'
         or (x->>'remaining_unentitled_good_qty_pcs')::integer<>4
     )
     or v_workspace#>>'{rows,0,components,0,default_selection_basis}'<>'UNPAID_COMPONENT_ENTITLEMENT'
     or (v_workspace#>>'{rows,0,components,0,remaining_new_work_qty_pcs}')::integer<>4
     or (v_workspace#>>'{rows,0,components,0,default_selected}')::boolean is not true then
    raise exception 'Workspace did not expose the authoritative two-line accessory BOM: %',v_workspace;
  end if;

  v_workspace:=public.erp_get_bs_resolution_workspace_v1(
    'ACTIVE','BS',null,'CP5-MANUAL-REPLACEMENT-BS',50,0
  );
  if (v_workspace->>'total')::integer<>1
     or exists(
       select 1 from jsonb_array_elements(v_workspace#>'{rows,0,accessory_bom,items}') x
       where (x->>'default_selected')::boolean is not false
         or x->>'default_selection_basis'<>'MANUAL_REPLACEMENT'
         or (x->>'remaining_unentitled_good_qty_pcs')::integer<>0
     ) then
    raise exception 'Post-FG/warehouse accessory baseline was silently auto-selected: %',v_workspace;
  end if;
  v_response:=public.erp_save_bs_resolution_action_v1(
    'SAVE_REWORK',jsonb_build_object(
      'rework_number','CP5-MANUAL-REPLACEMENT','bs_case_id',v_manual_replacement_bs,
      'destination_type','LAUNDRY','contractor_id',null,'vendor_id',v_vendor,
      'qty_sent',1,'physical_sent_at','2026-08-24 08:30:00+00','status','IN_PROGRESS',
      'return_fg_location_id',v_location,'accessory_bom_version_id',v_bom,
      'accessory_bom_item_ids',jsonb_build_array(v_item_a),
      'components',jsonb_build_array(),
      'change_reason','Operator confirms a real post-FG Button replacement'
    ),gen_random_uuid(),null
  );
  if v_response#>>'{result,accessory_decision,selected_items,0,selection_basis}'<>'MANUAL_REPLACEMENT' then
    raise exception 'Explicit post-FG replacement lost its immutable manual provenance: %',v_response;
  end if;

  v_workspace:=public.erp_get_bs_resolution_workspace_v1(
    'ACTIVE','BS',null,'CP5-LINEAGE-REWORK-BS',50,0
  );
  select (x->>'id')::uuid into v_component
  from jsonb_array_elements(v_workspace#>'{rows,0,components}') x limit 1;
  if v_component is null then raise exception 'Rework labor component baseline is missing'; end if;

  v_response:=public.erp_save_bs_resolution_action_v1(
    'SAVE_REWORK',jsonb_build_object(
      'rework_number','CP5-LINEAGE-RW-1','bs_case_id',v_rework_bs,
      'destination_type','CONTRACTOR',
      'contractor_id','a1000000-0000-0000-0000-000000000001','vendor_id',null,
      'qty_sent',4,'qty_good_returned',0,'qty_bs_returned',0,
      'physical_sent_at','2026-08-24 09:00:00+00','status','IN_PROGRESS',
      'return_fg_location_id',v_location,
      'accessory_bom_version_id',v_bom,
      'accessory_bom_item_ids',jsonb_build_array(v_item_a),
      'components',jsonb_build_array(jsonb_build_object(
        'bs_case_component_id',v_component,'qty_performed',4,
        'notes','All four pieces received physical sewing rework'
      )),
      'change_reason','Only Button was newly installed; Label remained unchecked'
    ),gen_random_uuid(),null
  );
  v_rework:=(v_response#>>'{result,rework_order_id}')::uuid;
  v_rework_version:=(v_response#>>'{result,row_version}')::bigint;
  if v_response#>>'{result,accessory_decision,state}'<>'SELECTED'
     or v_response#>>'{result,accessory_decision,selected_items,0,bom_item_id}'<>v_item_a::text
     or v_response#>>'{result,accessory_decision,selected_items,0,selection_basis}'<>'UNPAID_BASELINE'
     or (v_response#>>'{result,accessory_decision,selected_item_count}')::integer<>1 then
    raise exception 'Rework creation lost the immutable one-item accessory choice: %',v_response;
  end if;

  v_response:=public.erp_save_bs_resolution_action_v1(
    'SAVE_REWORK',jsonb_build_object(
      'id',v_rework,'action','SAVE','qty_good_returned',1,'qty_bs_returned',1,
      'return_fg_location_id',v_location,
      'change_reason','First two of four pieces physically returned'
    ),gen_random_uuid(),v_rework_version
  );
  v_rework_version:=(v_response#>>'{result,row_version}')::bigint;
  execute 'reset role';
  if v_response#>>'{result,status}'<>'PARTIAL'
     or (v_response#>>'{result,qty_good_returned}')::integer<>1
     or (v_response#>>'{result,qty_bs_returned}')::integer<>1
     or exists(select 1 from erp.fg_lots where lot_number like 'RW-CP5-LINEAGE-RW-1%')
     or exists(select 1 from erp.journal_entries where source_id=v_rework)
     or exists(
       select 1 from erp.contractor_accessory_reimbursement_entitlements e
       join erp.rework_orders ro on ro.good_fg_lot_id=e.lot_id where ro.id=v_rework
     ) then
    raise exception 'Partial return posted FG/accounting or lost cumulative custody: %',v_response;
  end if;

  execute 'set local role authenticated';
  v_failed:=false;
  begin
    perform public.erp_save_bs_resolution_action_v1(
      'SAVE_REWORK',jsonb_build_object(
        'id',v_rework,'action','SAVE','qty_good_returned',0,'qty_bs_returned',1,
        'change_reason','Forbidden cumulative quantity decrease'
      ),gen_random_uuid(),v_rework_version
    );
  exception when others then
    if sqlerrm like '%cannot decrease%' then v_failed:=true; else raise; end if;
  end;
  if not v_failed then raise exception 'Partial cumulative quantity decrease was accepted'; end if;

  v_failed:=false;
  begin
    perform public.erp_save_bs_resolution_action_v1(
      'SAVE_REWORK',jsonb_build_object(
        'id',v_rework,'action','SAVE','qty_good_returned',2,'qty_bs_returned',1,
        'accessory_bom_item_ids',jsonb_build_array(v_item_b),
        'change_reason','Forbidden accessory selection rewrite'
      ),gen_random_uuid(),v_rework_version
    );
  exception when others then
    if sqlerrm like '%accessory choice are immutable%' then v_failed:=true; else raise; end if;
  end;
  if not v_failed then raise exception 'Immutable accessory choice accepted an update'; end if;

  v_payload:=jsonb_build_object(
    'rework_order_id',v_rework,'qty_good',3,'qty_bs',1,
    'completed_at','2026-08-24 10:00:00+00','return_fg_location_id',v_location,
    'change_reason','All four pieces reconciled; three GOOD and one remains BS'
  );
  v_response:=public.erp_save_bs_resolution_action_v1(
    'COMPLETE_REWORK',v_payload,v_complete_request,v_rework_version
  );
  v_replay:=public.erp_save_bs_resolution_action_v1(
    'COMPLETE_REWORK',v_payload,v_complete_request,v_rework_version
  );
  if v_response is distinct from v_replay then
    raise exception 'Positive GOOD completion idempotent replay diverged';
  end if;
  v_rework_version:=(v_response#>>'{result,row_version}')::bigint;
  v_lot:=(v_response#>>'{result,good_fg_lot_id}')::uuid;
  if v_response#>>'{result,status}'<>'COMPLETED'
     or v_response#>>'{result,bs_case_status}'<>'PARTIAL'
     or (v_response#>>'{result,cost_posted}')::boolean is not true
     or v_lot is null then
    raise exception 'Positive mixed GOOD/BS completion did not post exactly once: %',v_response;
  end if;
  v_failed:=false;
  begin
    perform public.erp_save_bs_resolution_action_v1(
      'COMPLETE_REWORK',v_payload||jsonb_build_object('qty_good',4,'qty_bs',0),
      v_complete_request,v_rework_version
    );
  exception when others then
    if sqlerrm like '%different payload%' then v_failed:=true; else raise; end if;
  end;
  if not v_failed then raise exception 'Completion request ID accepted a different payload'; end if;

  execute 'reset role';
  if (select count(*) from erp.fg_accessory_cost_snapshots where lot_id=v_lot)<>1
     or not exists(
       select 1 from erp.fg_accessory_cost_snapshots s
       where s.lot_id=v_lot and s.bom_item_id=v_item_a
         and s.good_qty_pcs=3 and s.total_hpp_cost=60 and s.total_reimbursement=90
     )
     or exists(
       select 1 from erp.fg_accessory_cost_snapshots s
       where s.lot_id=v_lot and s.bom_item_id=v_item_b
     ) then
    raise exception 'GOOD rework snapshot did not stay on the checked Button only';
  end if;
  if not exists(
    select 1 from erp.contractor_accessory_reimbursement_entitlements e
    where e.lot_id=v_lot
      and e.contractor_id='a1000000-0000-0000-0000-000000000001'
      and e.category_id=v_category_a and e.amount=90 and e.payroll_status='UNALLOCATED'
  ) then raise exception 'Selected Button reimbursement did not accrue to the authoritative Mandor'; end if;
  if not exists(
    select 1 from erp.fg_stock_movements m
    where m.lot_id=v_lot and m.movement_type='REWORK_IN'
      and m.source_type='REWORK_ORDER' and m.source_id=v_rework and m.qty_signed=3
  ) then raise exception 'Positive GOOD rework did not create the exact FG movement'; end if;
  if (select round(coalesce(sum(case
        when jl.account_id=erp.account_id('WIP') then jl.debit-jl.credit else 0 end),0),2)
      from erp.journal_entries je join erp.journal_lines jl on jl.journal_entry_id=je.id
      where je.source_type='ACCESSORY_REIMBURSE_ACCRUAL' and je.source_id=v_lot
        and je.status='POSTED')<>60
     or (select round(coalesce(sum(case
        when jl.account_id=erp.account_id('ACCESSORY_REIMBURSE_VARIANCE') then jl.debit-jl.credit else 0 end),0),2)
      from erp.journal_entries je join erp.journal_lines jl on jl.journal_entry_id=je.id
      where je.source_type='ACCESSORY_REIMBURSE_ACCRUAL' and je.source_id=v_lot
        and je.status='POSTED')<>30
     or (select round(coalesce(sum(case
        when jl.account_id=erp.account_id('CONTRACTOR_PAYABLE') then jl.credit-jl.debit else 0 end),0),2)
      from erp.journal_entries je join erp.journal_lines jl on jl.journal_entry_id=je.id
      where je.source_type='ACCESSORY_REIMBURSE_ACCRUAL' and je.source_id=v_lot
        and je.status='POSTED')<>90 then
    raise exception 'Selected accessory accrual did not post exact WIP/variance/payable amounts';
  end if;
  if (select round(coalesce(sum(case
        when jl.account_id=erp.account_id('CONTRACTOR_PAYABLE') then jl.credit-jl.debit else 0 end),0),2)
      from erp.journal_entries je join erp.journal_lines jl on jl.journal_entry_id=je.id
      where je.source_type='REWORK_COMPLETION' and je.source_id=v_rework
        and je.status='POSTED')<>20 then
    raise exception 'Contractor rework labor did not post its separately selected work component';
  end if;

  execute 'set local role authenticated';
  v_workspace:=public.erp_get_bs_resolution_workspace_v1(
    'ACTIVE','BS',null,'CP5-LINEAGE-REWORK-BS',50,0
  );
  execute 'reset role';
  if (v_workspace#>>'{rows,0,available_qty}')::integer<>1
     or exists(
       select 1 from jsonb_array_elements(v_workspace#>'{rows,0,accessory_bom,items}') x
       where (x->>'default_selected')::boolean is not true
         or x->>'default_selection_basis'<>'UNPAID_BASELINE'
         or (x->>'remaining_unentitled_good_qty_pcs')::integer<>1
     )
     or not exists(
       select 1 from jsonb_array_elements(v_workspace#>'{rows,0,accessory_bom,items}') x
       where (x->>'id')::uuid=v_item_a
         and (x->>'already_entitled_good_qty_pcs')::integer=3
         and (x->>'already_cash_settled_good_qty_pcs')::integer=0
     ) then
    raise exception 'Remaining physical BS did not keep exactly one unpaid baseline entitlement: %',v_workspace;
  end if;

  perform set_config('request.jwt.claims',jsonb_build_object(
    'sub',v_owner_auth,'role','authenticated'
  )::text,true);
  execute 'set local role authenticated';
  v_response:=public.erp_save_bs_resolution_action_v1(
    'REVERSE_REWORK_COMPLETION',jsonb_build_object(
      'rework_order_id',v_rework,
      'change_reason','Owner reverses positive GOOD lineage proof'
    ),gen_random_uuid(),v_rework_version
  );
  execute 'reset role';
  if v_response#>>'{result,status}'<>'CANCELLED'
     or not exists(
       select 1 from erp.rework_accessory_selection_lines l
       where l.rework_order_id=v_rework and l.bom_item_id=v_item_a
         and l.selection_basis='UNPAID_BASELINE'
     )
     or not exists(
       select 1 from erp.contractor_accessory_reimbursement_entitlements e
       where e.lot_id=v_lot and e.payroll_status='CANCELLED'
     )
     or not exists(
       select 1 from erp.fg_lots where id=v_lot and lot_origin='VOIDED_PRODUCTION'
     )
     or not exists(
       select 1 from erp.fg_stock_movements original
       join erp.fg_stock_movements reversal on reversal.reversal_of_id=original.id
       where original.lot_id=v_lot and original.movement_type='REWORK_IN'
     ) then raise exception 'Reversal did not unwind money/stock while preserving immutable selection'; end if;

  perform set_config('request.jwt.claims',jsonb_build_object(
    'sub',v_production_auth,'role','authenticated'
  )::text,true);
  select id into v_component from erp.bs_case_components
  where bs_case_id=v_none_bs order by id limit 1;
  execute 'set local role authenticated';
  v_response:=public.erp_save_bs_resolution_action_v1(
    'SAVE_REWORK',jsonb_build_object(
      'rework_number','CP5-LINEAGE-NONE','bs_case_id',v_none_bs,
      'destination_type','CONTRACTOR',
      'contractor_id','a1000000-0000-0000-0000-000000000001','vendor_id',null,
      'qty_sent',2,'physical_sent_at','2026-08-24 11:00:00+00','status','IN_PROGRESS',
      'return_fg_location_id',v_location,'accessory_bom_version_id',v_bom,
      'accessory_bom_item_ids',jsonb_build_array(),
      'components',jsonb_build_array(jsonb_build_object(
        'bs_case_component_id',v_component,'qty_performed',2,'notes','Work only'
      )),
      'change_reason','No accessory was installed; explicit empty choice'
    ),gen_random_uuid(),null
  );
  v_none_rework:=(v_response#>>'{result,rework_order_id}')::uuid;
  v_none_version:=(v_response#>>'{result,row_version}')::bigint;
  v_response:=public.erp_save_bs_resolution_action_v1(
    'COMPLETE_REWORK',jsonb_build_object(
      'rework_order_id',v_none_rework,'qty_good',2,'qty_bs',0,
      'completed_at','2026-08-24 12:00:00+00','return_fg_location_id',v_location,
      'change_reason','Two GOOD with an explicit empty accessory decision'
    ),gen_random_uuid(),v_none_version
  );
  v_none_lot:=(v_response#>>'{result,good_fg_lot_id}')::uuid;
  execute 'reset role';
  if exists(select 1 from erp.fg_accessory_cost_snapshots where lot_id=v_none_lot)
     or exists(select 1 from erp.contractor_accessory_reimbursement_entitlements where lot_id=v_none_lot)
     or exists(
       select 1 from erp.journal_entries
       where source_type='ACCESSORY_REIMBURSE_ACCRUAL' and source_id=v_none_lot
     ) then raise exception 'Explicit empty accessory choice fell back to the full BOM'; end if;
  if exists(select 1 from erp.fg_accessory_cost_snapshots where lot_id=v_none_lot) then
    raise exception 'Completion/HPP rebuild reintroduced unselected accessories';
  end if;

  execute 'set local role authenticated';
  v_response:=public.erp_save_bs_resolution_action_v1(
    'SAVE_REWORK',jsonb_build_object(
      'rework_number','CP5-LINEAGE-REWASH','bs_case_id',v_rewash_bs,
      'destination_type','LAUNDRY','contractor_id',null,'vendor_id',v_vendor,
      'qty_sent',2,'physical_sent_at','2026-08-24 13:00:00+00','status','IN_PROGRESS',
      'return_fg_location_id',v_location,'accessory_bom_version_id',v_bom,
      'accessory_bom_item_ids',jsonb_build_array(v_item_b),
      'components',jsonb_build_array(),
      'change_reason','Rewash installed only Label; vendor fee remains zero'
    ),gen_random_uuid(),null
  );
  v_rewash:=(v_response#>>'{result,rework_order_id}')::uuid;
  v_rewash_version:=(v_response#>>'{result,row_version}')::bigint;
  v_response:=public.erp_save_bs_resolution_action_v1(
    'COMPLETE_REWORK',jsonb_build_object(
      'rework_order_id',v_rewash,'qty_good',1,'qty_bs',1,
      'completed_at','2026-08-24 14:00:00+00','return_fg_location_id',v_location,
      'change_reason','One rewash GOOD with Label; one remains BS'
    ),gen_random_uuid(),v_rewash_version
  );
  v_rewash_lot:=(v_response#>>'{result,good_fg_lot_id}')::uuid;
  execute 'reset role';
  if not exists(
    select 1 from erp.fg_accessory_cost_snapshots s
    where s.lot_id=v_rewash_lot and s.bom_item_id=v_item_b
      and s.total_hpp_cost=4 and s.total_reimbursement=7
  ) or exists(
    select 1 from erp.fg_accessory_cost_snapshots s
    where s.lot_id=v_rewash_lot and s.bom_item_id=v_item_a
  ) or not exists(
    select 1 from erp.contractor_accessory_reimbursement_entitlements e
    where e.lot_id=v_rewash_lot
      and e.contractor_id='a1000000-0000-0000-0000-000000000001'
      and e.amount=7
  ) or exists(
    select 1 from erp.journal_entries
    where source_type='REWORK_COMPLETION' and source_id=v_rewash
  ) then raise exception 'REWASH did not pay only Label to the PO Mandor with zero vendor work fee'; end if;

  execute 'set local role authenticated';
  v_workspace:=public.erp_get_bs_resolution_workspace_v1(
    'ALL','BS',null,'CP5-LINEAGE-REWASH-BS',50,0
  );
  if v_workspace#>>'{rows,0,rework_orders,0,accessory_decision,state}'<>'SELECTED'
     or v_workspace#>>'{rows,0,rework_orders,0,accessory_decision,selected_items,0,bom_item_id}'<>v_item_b::text
     or v_workspace#>>'{rows,0,rework_orders,0,accessory_decision,selected_items,0,selection_basis}'<>'UNPAID_BASELINE' then
    raise exception 'Workspace lost the frozen REWASH accessory decision: %',v_workspace;
  end if;

  execute 'reset role';
  if exists(select 1 from erp.bs_resolution_execution_context) then
    raise exception 'CP5 v2.6.19a execution capability leaked';
  end if;
  v_failed:=false;
  begin
    update erp.rework_accessory_selection_lines
    set reimbursement_unit_rate_base_snapshot=999
    where rework_order_id=v_rewash;
  exception when others then
    if sqlerrm like '%immutable%' then v_failed:=true; else raise; end if;
  end;
  if not v_failed then raise exception 'Accessory selection history accepted an in-place rewrite'; end if;
end
$test$;

rollback;
