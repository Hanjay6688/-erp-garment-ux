-- ERP v2.6.19 / CP5 authoritative BS Resolution acceptance.
-- Every fixture and posted accounting fact is enclosed by this transaction.
\set ON_ERROR_STOP on

begin;
set local timezone='UTC';
set local datestyle='ISO, MDY';
set local lock_timeout='8s';
set local statement_timeout='180s';

\ir cp3_r4_full_schema_seed.sql

do $test$
declare
  v_owner_app constant uuid:='c6000000-0000-4000-8000-000000000001';
  v_owner_auth constant uuid:='c6000000-0000-4000-8000-000000000101';
  v_production_app constant uuid:='c6000000-0000-4000-8000-000000000002';
  v_production_auth constant uuid:='c6000000-0000-4000-8000-000000000102';
  v_vendor constant uuid:='c6010000-0000-4000-8000-000000000001';
  v_pattern constant uuid:='c6020000-0000-4000-8000-000000000001';
  v_other_pattern constant uuid:='c6020000-0000-4000-8000-000000000002';
  v_po constant uuid:='c6030000-0000-4000-8000-000000000001';
  v_batch constant uuid:='c6040000-0000-4000-8000-000000000001';
  v_group constant uuid:='c6040000-0000-4000-8000-000000000002';
  v_size_slot constant uuid:='c6040000-0000-4000-8000-000000000003';
  v_snapshot constant uuid:='c6050000-0000-4000-8000-000000000001';
  v_pattern_bs constant uuid:='c6060000-0000-4000-8000-000000000001';
  v_delivery constant uuid:='c6070000-0000-4000-8000-000000000001';
  v_delivery_line constant uuid:='c6070000-0000-4000-8000-000000000002';
  v_receipt constant uuid:='c6070000-0000-4000-8000-000000000003';
  v_receipt_line constant uuid:='c6070000-0000-4000-8000-000000000004';
  v_brand constant uuid:='c6070000-0000-4000-8000-000000000005';
  v_product constant uuid:='c6070000-0000-4000-8000-000000000006';
  v_receipt_allocation constant uuid:='c6070000-0000-4000-8000-000000000007';
  v_manual_request constant uuid:='c6080000-0000-4000-8000-000000000001';
  v_manual_payload jsonb;
  v_response jsonb;
  v_replay jsonb;
  v_workspace jsonb;
  v_manual_bs uuid;
  v_manual_version bigint;
  v_manual_rework uuid;
  v_manual_rework_version bigint;
  v_cancel_rework uuid;
  v_cancel_rework_version bigint;
  v_pattern_rework uuid;
  v_pattern_rework_version bigint;
  v_receipt_bs uuid;
  v_component uuid;
  v_disposition uuid;
  v_cash_disposition uuid;
  v_claim uuid;
  v_claim_version bigint;
  v_damage_claim uuid;
  v_damage_claim_version bigint;
  v_failed boolean;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.18a')
     or not exists(select 1 from erp.schema_migrations where version='v2.6.19')
     or to_regprocedure('public.erp_get_bs_resolution_workspace_v1(text,text,uuid,text,integer,integer)') is null
     or to_regprocedure('public.erp_save_bs_resolution_action_v1(text,jsonb,uuid,bigint)') is null
     or to_regclass('erp.bs_case_hold_events') is null
     or to_regclass('erp.bs_resolution_execution_context') is null
     or to_regclass('erp.cutting_bridge_execution_context') is null
     or to_regclass('erp.cutting_bridge_v2618a_rollback_capsule') is null
     or (select count(*) from erp.bs_resolution_v2619_rollback_capsule where object_kind='FUNCTION')<>20
     or (select count(*) from erp.bs_resolution_v2619_rollback_capsule where object_kind='RELATION')<>10 then
    raise exception 'CP5 v2.6.19 boundary/capsule is not installed completely';
  end if;
  if has_function_privilege('anon','public.erp_get_bs_resolution_workspace_v1(text,text,uuid,text,integer,integer)','EXECUTE')
     or has_function_privilege('anon','public.erp_save_bs_resolution_action_v1(text,jsonb,uuid,bigint)','EXECUTE')
     or has_table_privilege('authenticated','erp.bs_cases','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('authenticated','erp.bs_case_hold_events','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('authenticated','erp.bs_resolution_execution_context','SELECT,INSERT,UPDATE,DELETE') then
    raise exception 'CP5 browser ACL boundary is open';
  end if;
  if pg_get_functiondef('erp.require_internal()'::regprocedure) not like '%bs_resolution_execution_context%'
     or pg_get_functiondef('erp.require_internal()'::regprocedure) not like '%cutting_bridge_execution_context%'
     or pg_get_functiondef('erp.save_bs_resolution_action_v1(text,jsonb,uuid,bigint)'::regprocedure)
          not like '%delete from erp.bs_resolution_execution_context%' then
    raise exception 'CP5 transaction-scoped internal delegation is missing';
  end if;
  if pg_get_functiondef('erp.resolve_laundry_claim_v2(uuid,text,text,uuid,bigint)'::regprocedure)
       not like '%require_owner_admin%'
     or pg_get_functiondef('erp.reverse_rework_completion(uuid,text)'::regprocedure)
       not like '%require_owner_admin%' then
    raise exception 'CP5 Owner/Admin finalization boundary was weakened';
  end if;

  insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active)
  select v_owner_app,v_owner_auth,'CP5 Synthetic Owner','OWNER',id,true
  from erp.app_roles where role_code='OWNER';
  insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active)
  select v_production_app,v_production_auth,'CP5 Synthetic Production','PRODUKSI_QC',id,true
  from erp.app_roles where role_code='PRODUKSI_QC';
  insert into erp.laundry_vendors(id,vendor_code,vendor_name,is_active,notes)
  values(v_vendor,'CP5-LDR','CP5 Laundry Recovery',true,'CP5 transactional fixture');
  insert into erp.production_patterns(
    id,pattern_code,revision,pattern_name,sort_order,is_active,created_by,updated_by
  ) values
    (v_pattern,'CP5-PATTERN','R1','CP5 Recovery Pattern',9101,true,v_owner_app,v_owner_app),
    (v_other_pattern,'CP5-OTHER','R1','CP5 Negative Filter',9102,true,v_owner_app,v_owner_app);
  insert into erp.production_orders(
    id,po_number,model_id,contractor_id,target_qty_pcs,status,current_stage,physical_start_at,notes
  ) values(
    v_po,'CP5-PO-001','a2000000-0000-0000-0000-000000000001',
    'a1000000-0000-0000-0000-000000000001',12,'CUTTING','CUTTING',
    '2026-08-20 07:00:00+00','CP5 transactional fixture'
  );
  insert into erp.cutting_batches(id,po_id,batch_number,cut_at,status,notes)
  values(v_batch,v_po,'CP5-BATCH-001','2026-08-20 08:00:00+00','OPEN','CP5 fixture');
  insert into erp.cutting_groups(
    id,po_id,group_number,cut_at,status,cutting_batch_id,pattern_id,notes
  ) values(
    v_group,v_po,'CP5-GROUP-001','2026-08-20 08:00:00+00','CUT',v_batch,v_pattern,
    'CP5 immutable Pattern fixture'
  );
  insert into erp.cutting_group_size_slots(
    id,cutting_group_id,slot_no,size_id,drawing_no
  ) values(
    v_size_slot,v_group,1,'a2100000-0000-0000-0000-000000000001',1
  );
  insert into erp.po_work_component_snapshots(
    id,po_id,work_component_id,sequence_no,rate_per_pcs_snapshot,committed_at
  ) values(
    v_snapshot,v_po,'a4000000-0000-0000-0000-000000000001',1,2,
    '2026-08-20 08:15:00+00'
  );
  insert into erp.laundry_deliveries(
    id,delivery_number,po_id,vendor_id,target_dyeing_color,
    physical_at,status,portal_visible,created_by,special_instruction
  ) values(
    v_delivery,'CP5-PATTERN-DELIVERY',v_po,v_vendor,'CP5 BLUE',
    '2026-08-22 08:00:00+00','SENT',true,v_owner_app,'CP5 sent source'
  );
  insert into erp.laundry_delivery_lines(
    id,delivery_id,cutting_group_id,qty_sent_pcs,estimated_rate_snapshot,
    estimated_cost_status,notes
  ) values(
    v_delivery_line,v_delivery,v_group,12,0,'FINAL','CP5 source line'
  );
  perform erp.post_journal(
    'CP5_VENDOR_PAYABLE',v_delivery,'2026-08-22','CP5 vendor payable for settlement proof',
    jsonb_build_array(
      jsonb_build_object('mapping_key','WIP','debit',100,'credit',0,'vendor_id',v_vendor,'po_id',v_po),
      jsonb_build_object('mapping_key','AP_VENDOR','debit',0,'credit',100,'vendor_id',v_vendor,'po_id',v_po)
    )
  );
  perform set_config('app.change_reason','CP5 tracked Pattern fixture',true);
  insert into erp.bs_cases(
    id,bs_number,po_id,cutting_group_id,detected_at_stage,cause_source,
    responsible_contractor_id,qty_pcs,status,physical_at,notes
  ) values(
    v_pattern_bs,'CP5-PATTERN-BS',v_po,v_group,'SEWING','SEWING',
    'a1000000-0000-0000-0000-000000000001',7,'OPEN',
    '2026-08-20 09:00:00+00','CP5 Pattern-filtered contractor BS'
  );
  insert into erp.laundry_receipts(id,receipt_number,delivery_id,physical_at,status)
  values(v_receipt,'CP5-PATTERN-RECEIPT',v_delivery,'2026-08-22 08:30:00+00','DRAFT');
  insert into erp.laundry_receipt_lines(
    id,receipt_id,delivery_line_id,qty_good_received,qty_bs_laundry,qty_stuck,qty_missing
  ) values(v_receipt_line,v_receipt,v_delivery_line,5,3,0,0);
  insert into erp.brands(id,brand_code,brand_name)
  values(v_brand,'CP5-BRAND','CP5 Final Product Brand');
  insert into erp.products(
    id,sku,model_id,brand_id,color_name,size_id,product_name,
    identity_root_id,effective_from,is_active
  ) values(
    v_product,'CP5-SKU-BLUE-S','a2000000-0000-0000-0000-000000000001',
    v_brand,'CP5 BLUE','a2100000-0000-0000-0000-000000000001',
    'CP5 Blue Small',v_product,'2026-01-01 00:00:00+00',true
  );
  insert into erp.laundry_receipt_bs_product_allocations(
    id,receipt_line_id,product_id,qty_bs,notes,created_by
  ) values(
    v_receipt_allocation,v_receipt_line,v_product,3,
    'CP5 exact Laundry BS product lineage',v_owner_app
  );
  v_response:=erp.post_laundry_receipt_v2(
    v_receipt,gen_random_uuid(),1,'CP5 physical Laundry return with three damaged pieces'
  );
  if v_response->>'status'<>'POSTED' or (v_response->>'bs_case_count')::integer<>1 then
    raise exception 'CP5 Laundry receipt did not create its authoritative BS case: %',v_response;
  end if;
  select id into v_receipt_bs from erp.bs_cases
  where source_laundry_receipt_line_id=v_receipt_line
    and source_laundry_bs_allocation_id=v_receipt_allocation
    and product_id=v_product;
  if v_receipt_bs is null then
    raise exception 'CP5 Laundry DAMAGE lineage has no source BS case';
  end if;

  perform set_config('request.jwt.claims',jsonb_build_object(
    'sub',v_production_auth,'role','authenticated'
  )::text,true);
  execute 'set local role authenticated';

  v_workspace:=public.erp_get_bs_resolution_workspace_v1('ACTIVE','ALL',v_pattern,null,50,0);
  if (v_workspace->>'total')::integer<>2
     or not exists(
       select 1 from jsonb_array_elements(v_workspace->'rows') x
       where x->>'id'=v_pattern_bs::text and x#>>'{patterns,0,code}'='CP5-PATTERN'
     )
     or not exists(
       select 1 from jsonb_array_elements(v_workspace->'rows') x
       where x->>'id'=v_receipt_bs::text
         and x->>'laundry_receipt_line_id'=v_receipt_line::text
         and x#>>'{patterns,0,id}'=v_pattern::text
     )
     or not exists(
       select 1 from jsonb_array_elements(v_workspace#>'{lookups,laundry_sources}') x
       where x->>'id'=v_delivery::text and (x->>'qty_sent_pcs')::integer=12
         and (x->>'qty_claimable_pcs')::integer=4
     )
     or not exists(
       select 1 from jsonb_array_elements(v_workspace#>'{lookups,laundry_receipt_sources}') x
       where x->>'id'=v_receipt_line::text and x->>'delivery_id'=v_delivery::text
         and (x->>'qty_bs_laundry')::integer=3
         and (x->>'qty_claimable_pcs')::integer=3
     ) then
    raise exception 'CP5 Pattern workspace or Laundry delivery/receipt lineage is incomplete: %',v_workspace;
  end if;
  v_workspace:=public.erp_get_bs_resolution_workspace_v1('ALL','ALL',v_other_pattern,null,50,0);
  if (v_workspace->>'total')::integer<>0 then
    raise exception 'CP5 server-side Pattern filter returned a row for a different Pattern';
  end if;

  v_manual_payload:=jsonb_build_object(
    'untracked_type','LEGACY','legacy_reference','CP5-LEGACY-BOOK-17',
    'qty_pcs',11,'physical_at','2026-08-21 07:00:00+00',
    'change_reason','CP5 manual BS physical reconciliation',
    'notes','CP5 manual lifecycle fixture','components',jsonb_build_array()
  );
  v_response:=public.erp_save_bs_resolution_action_v1(
    'CREATE_MANUAL_BS',v_manual_payload,v_manual_request,null
  );
  v_replay:=public.erp_save_bs_resolution_action_v1(
    'CREATE_MANUAL_BS',v_manual_payload,v_manual_request,null
  );
  if v_response is distinct from v_replay then
    raise exception 'CP5 manual BS double-click replay diverged';
  end if;
  v_manual_bs:=(v_response#>>'{result,bs_case_id}')::uuid;
  v_manual_version:=(v_response#>>'{result,row_version}')::bigint;

  v_failed:=false;
  begin
    perform public.erp_save_bs_resolution_action_v1(
      'CREATE_MANUAL_BS',v_manual_payload||jsonb_build_object('qty_pcs',12),
      v_manual_request,null
    );
  exception when others then
    if sqlerrm like '%different payload%' then v_failed:=true; else raise; end if;
  end;
  if not v_failed then raise exception 'CP5 reused request ID accepted a different payload'; end if;

  v_response:=public.erp_save_bs_resolution_action_v1(
    'CLASSIFY_BS',jsonb_build_object(
      'bs_case_id',v_manual_bs,'cause_source','LAUNDRY',
      'responsible_contractor_id',null,'responsible_vendor_id',v_vendor,
      'notes','CP5 classified to Laundry','components',jsonb_build_array(),
      'change_reason','CP5 physical inspection classified Laundry cause'
    ),gen_random_uuid(),v_manual_version
  );
  v_manual_version:=(v_response#>>'{result,row_version}')::bigint;

  v_response:=public.erp_save_bs_resolution_action_v1(
    'SAVE_REWORK',jsonb_build_object(
      'rework_number','CP5-CANCEL-001','bs_case_id',v_manual_bs,
      'destination_type','LAUNDRY','contractor_id',null,'vendor_id',v_vendor,
      'qty_sent',1,'qty_good_returned',0,'qty_bs_returned',0,
      'physical_sent_at','2026-08-21 07:30:00+00','status','IN_PROGRESS',
      'change_reason','CP5 temporary rewash entered for cancellation proof',
      'components',jsonb_build_array()
    ),gen_random_uuid(),null
  );
  v_cancel_rework:=(v_response#>>'{result,rework_order_id}')::uuid;
  v_cancel_rework_version:=(v_response#>>'{result,row_version}')::bigint;
  v_response:=public.erp_save_bs_resolution_action_v1(
    'SAVE_REWORK',jsonb_build_object(
      'id',v_cancel_rework,'action','CANCEL',
      'change_reason','CP5 operator cancels untouched rewash order'
    ),gen_random_uuid(),v_cancel_rework_version
  );
  if v_response#>>'{result,status}'<>'CANCELLED' then
    raise exception 'CP5 active rework cancellation path failed: %',v_response;
  end if;
  v_workspace:=public.erp_get_bs_resolution_workspace_v1(
    'ACTIVE','BS',null,'CP5-LEGACY-BOOK-17',50,0
  );
  v_manual_version:=(v_workspace#>>'{rows,0,row_version}')::bigint;

  v_response:=public.erp_save_bs_resolution_action_v1(
    'HOLD_BS',jsonb_build_object(
      'bs_case_id',v_manual_bs,'physical_at','2026-08-21 08:00:00+00',
      'change_reason','CP5 waiting for physical vendor confirmation'
    ),'c6080000-0000-4000-8000-000000000002',v_manual_version
  );
  v_replay:=public.erp_save_bs_resolution_action_v1(
    'HOLD_BS',jsonb_build_object(
      'bs_case_id',v_manual_bs,'physical_at','2026-08-21 08:00:00+00',
      'change_reason','CP5 waiting for physical vendor confirmation'
    ),'c6080000-0000-4000-8000-000000000002',v_manual_version
  );
  if v_response is distinct from v_replay
     or v_response#>>'{result,status}'<>'ON_HOLD'
     or coalesce(current_setting('app.bs_hold_transition',true),'')<>'' then
    raise exception 'CP5 HOLD was not idempotent or leaked its transition capability';
  end if;
  v_manual_version:=(v_response#>>'{result,row_version}')::bigint;
  v_workspace:=public.erp_get_bs_resolution_workspace_v1(
    'ACTIVE','BS',null,'CP5-LEGACY-BOOK-17',50,0
  );
  if v_workspace#>>'{rows,0,status}'<>'ON_HOLD'
     or jsonb_array_length(v_workspace#>'{rows,0,hold_events}')<>1 then
    raise exception 'CP5 workspace lost authoritative HOLD history: %',v_workspace;
  end if;

  v_failed:=false;
  begin
    perform public.erp_save_bs_resolution_action_v1(
      'RELEASE_HOLD',jsonb_build_object(
        'bs_case_id',v_manual_bs,'physical_at','2026-08-21 09:00:00+00',
        'change_reason','CP5 stale release must fail'
      ),gen_random_uuid(),v_manual_version-1
    );
  exception when others then
    if sqlerrm like '%STALE_VERSION%' then v_failed:=true; else raise; end if;
  end;
  if not v_failed then raise exception 'CP5 stale HOLD release was accepted'; end if;

  v_response:=public.erp_save_bs_resolution_action_v1(
    'RELEASE_HOLD',jsonb_build_object(
      'bs_case_id',v_manual_bs,'physical_at','2026-08-21 09:00:00+00',
      'change_reason','CP5 vendor confirmation received'
    ),gen_random_uuid(),v_manual_version
  );
  if v_response#>>'{result,status}'<>'OPEN'
     or coalesce(current_setting('app.bs_hold_transition',true),'')<>'' then
    raise exception 'CP5 HOLD release did not reduce to OPEN or leaked capability: %',v_response;
  end if;
  v_manual_version:=(v_response#>>'{result,row_version}')::bigint;

  v_response:=public.erp_save_bs_resolution_action_v1(
    'SAVE_REWORK',jsonb_build_object(
      'rework_number','CP5-REWASH-001','bs_case_id',v_manual_bs,
      'destination_type','LAUNDRY','contractor_id',null,'vendor_id',v_vendor,
      'qty_sent',5,'qty_good_returned',0,'qty_bs_returned',0,
      'physical_sent_at','2026-08-21 10:00:00+00','status','IN_PROGRESS',
      'change_reason','CP5 send five pieces to rewash','notes','CP5 rewash',
      'components',jsonb_build_array()
    ),gen_random_uuid(),null
  );
  v_manual_rework:=(v_response#>>'{result,rework_order_id}')::uuid;
  v_manual_rework_version:=(v_response#>>'{result,row_version}')::bigint;
  v_response:=public.erp_save_bs_resolution_action_v1(
    'COMPLETE_REWORK',jsonb_build_object(
      'rework_order_id',v_manual_rework,'qty_good',0,'qty_bs',5,
      'completed_at','2026-08-21 11:00:00+00','return_fg_location_id',null,
      'change_reason','CP5 rewash returned all five pieces still BS'
    ),gen_random_uuid(),v_manual_rework_version
  );
  if v_response#>>'{result,bs_case_status}'<>'OPEN'
     or (v_response#>>'{result,cost_posted}')::boolean is not true then
    raise exception 'All-BS rewash leaked the legacy PARTIAL status bug: %',v_response;
  end if;
  v_manual_rework_version:=(v_response#>>'{result,row_version}')::bigint;
  v_manual_version:=(v_response#>>'{result,bs_case_row_version}')::bigint;

  v_response:=public.erp_save_bs_resolution_action_v1(
    'DISPOSE_BS',jsonb_build_object(
      'bs_case_id',v_manual_bs,'resolution_type','SCRAP','qty_pcs',4,
      'compensation_amount',0,'source_laundry_claim_id',null,
      'physical_at','2026-08-21 12:00:00+00',
      'change_reason','CP5 four pieces physically destroyed'
    ),gen_random_uuid(),v_manual_version
  );
  if v_response#>>'{result,status}'<>'PARTIAL' then
    raise exception 'Partial CP5 disposition did not leave the case PARTIAL: %',v_response;
  end if;
  v_disposition:=(v_response#>>'{result,bs_resolution_id}')::uuid;
  v_manual_version:=(v_response#>>'{result,row_version}')::bigint;

  v_workspace:=public.erp_get_bs_resolution_workspace_v1(
    'ACTIVE','BS',v_pattern,'CP5-PATTERN-BS',50,0
  );
  select (x#>>'{components,0,id}')::uuid into v_component
  from jsonb_array_elements(v_workspace->'rows') x
  where x->>'id'=v_pattern_bs::text;
  if v_component is null then raise exception 'Tracked BS component baseline is missing'; end if;
  v_response:=public.erp_save_bs_resolution_action_v1(
    'SAVE_REWORK',jsonb_build_object(
      'rework_number','CP5-REWORK-001','bs_case_id',v_pattern_bs,
      'destination_type','CONTRACTOR',
      'contractor_id','a1000000-0000-0000-0000-000000000001','vendor_id',null,
      'qty_sent',7,'qty_good_returned',0,'qty_bs_returned',0,
      'physical_sent_at','2026-08-21 13:00:00+00','status','IN_PROGRESS',
      'change_reason','CP5 contractor rework with canonical component rate',
      'components',jsonb_build_array(jsonb_build_object(
        'bs_case_component_id',v_component,'qty_performed',7,'notes','CP5 sewing retry'
      ))
    ),gen_random_uuid(),null
  );
  v_pattern_rework:=(v_response#>>'{result,rework_order_id}')::uuid;
  v_pattern_rework_version:=(v_response#>>'{result,row_version}')::bigint;
  v_response:=public.erp_save_bs_resolution_action_v1(
    'COMPLETE_REWORK',jsonb_build_object(
      'rework_order_id',v_pattern_rework,'qty_good',0,'qty_bs',7,
      'completed_at','2026-08-21 14:00:00+00','return_fg_location_id',null,
      'change_reason','CP5 contractor returned all seven pieces still BS'
    ),gen_random_uuid(),v_pattern_rework_version
  );
  if v_response#>>'{result,bs_case_status}'<>'OPEN'
     or (v_response#>>'{result,cost_posted}')::boolean is not true then
    raise exception 'All-BS contractor completion failed recovery/accounting boundary: %',v_response;
  end if;
  v_pattern_rework_version:=(v_response#>>'{result,row_version}')::bigint;

  v_response:=public.erp_save_bs_resolution_action_v1(
    'SAVE_CLAIM',jsonb_build_object(
      'action','SAVE','claim_number','CP5-DAMAGE-CLAIM','vendor_id',v_vendor,
      'delivery_id',v_delivery,'receipt_line_id',v_receipt_line,
      'qty_claimed',2,'claim_type','DAMAGE','compensation_amount',20,
      'opened_at','2026-08-22 08:45:00+00',
      'notes','CP5 two damaged pieces received from Laundry',
      'change_reason','CP5 receipt-line DAMAGE lineage proof'
    ),gen_random_uuid(),null
  );
  v_damage_claim:=(v_response#>>'{result,laundry_claim_id}')::uuid;
  v_damage_claim_version:=(v_response#>>'{result,row_version}')::bigint;
  v_workspace:=public.erp_get_bs_resolution_workspace_v1('ALL','ALL',v_pattern,null,50,0);
  if not exists(
    select 1 from jsonb_array_elements(v_workspace#>'{lookups,laundry_receipt_sources}') x
    where x->>'id'=v_receipt_line::text and (x->>'qty_claimable_pcs')::integer=1
  ) or not exists(
    select 1 from jsonb_array_elements(v_workspace->'rows') x
    where x->>'id'=v_damage_claim::text and x->>'kind'='LAUNDRY_CLAIM'
      and x->>'claim_type'='DAMAGE' and x->>'laundry_receipt_line_id'=v_receipt_line::text
      and x#>>'{patterns,0,id}'=v_pattern::text
  ) then
    raise exception 'CP5 DAMAGE claim did not reserve receipt capacity or preserve Pattern lineage: %',v_workspace;
  end if;

  v_failed:=false;
  begin
    perform public.erp_save_bs_resolution_action_v1(
      'SAVE_CLAIM',jsonb_build_object(
        'action','SAVE','claim_number','CP5-DAMAGE-OVER-CAPACITY','vendor_id',v_vendor,
        'delivery_id',v_delivery,'receipt_line_id',v_receipt_line,
        'qty_claimed',2,'claim_type','DAMAGE','compensation_amount',0,
        'opened_at','2026-08-22 08:46:00+00',
        'change_reason','CP5 over-capacity DAMAGE must fail'
      ),gen_random_uuid(),null
    );
  exception when others then
    if sqlerrm like '%DAMAGE claim exceeds BS quantity%' then v_failed:=true; else raise; end if;
  end;
  if not v_failed then raise exception 'CP5 DAMAGE claim exceeded receipt-line capacity'; end if;

  v_response:=public.erp_save_bs_resolution_action_v1(
    'SAVE_CLAIM',jsonb_build_object(
      'id',v_damage_claim,'action','REJECT',
      'change_reason','CP5 physical DAMAGE evidence rejected by production'
    ),gen_random_uuid(),v_damage_claim_version
  );
  if v_response#>>'{result,status}'<>'REJECTED' then
    raise exception 'CP5 explicit claim REJECT action failed: %',v_response;
  end if;
  v_workspace:=public.erp_get_bs_resolution_workspace_v1('ALL','ALL',v_pattern,null,50,0);
  if not exists(
    select 1 from jsonb_array_elements(v_workspace#>'{lookups,laundry_receipt_sources}') x
    where x->>'id'=v_receipt_line::text and (x->>'qty_claimable_pcs')::integer=3
  ) then
    raise exception 'CP5 rejected DAMAGE claim did not restore receipt-line capacity: %',v_workspace;
  end if;

  v_response:=public.erp_save_bs_resolution_action_v1(
    'SAVE_CLAIM',jsonb_build_object(
      'action','SAVE','claim_number','CP5-PATTERN-CLAIM','vendor_id',v_vendor,
      'delivery_id',v_delivery,'qty_claimed',4,'claim_type','STUCK',
      'compensation_amount',50,'opened_at','2026-08-22 09:00:00+00',
      'notes','CP5 four pieces outstanding',
      'change_reason','CP5 physical delivery reconciliation'
    ),gen_random_uuid(),null
  );
  v_claim:=(v_response#>>'{result,laundry_claim_id}')::uuid;
  v_claim_version:=(v_response#>>'{result,row_version}')::bigint;
  v_response:=public.erp_save_bs_resolution_action_v1(
    'SAVE_CLAIM',jsonb_build_object(
      'id',v_claim,'action','SAVE','status','ACCEPTED',
      'change_reason','CP5 vendor accepted the physical claim'
    ),gen_random_uuid(),v_claim_version
  );
  v_claim_version:=(v_response#>>'{result,row_version}')::bigint;

  v_workspace:=public.erp_get_bs_resolution_workspace_v1('ALL','ALL',v_pattern,null,50,0);
  if (v_workspace->>'total')::integer<>4
     or not exists(
       select 1 from jsonb_array_elements(v_workspace->'rows') x
       where x->>'kind'='BS' and x->>'id'=v_pattern_bs::text
     )
     or not exists(
       select 1 from jsonb_array_elements(v_workspace->'rows') x
       where x->>'kind'='BS' and x->>'id'=v_receipt_bs::text
     )
     or not exists(
       select 1 from jsonb_array_elements(v_workspace->'rows') x
       where x->>'kind'='LAUNDRY_CLAIM' and x->>'id'=v_claim::text
         and x#>>'{patterns,0,id}'=v_pattern::text
     )
     or not exists(
       select 1 from jsonb_array_elements(v_workspace->'rows') x
       where x->>'kind'='LAUNDRY_CLAIM' and x->>'id'=v_damage_claim::text
         and x->>'status'='REJECTED' and x#>>'{patterns,0,id}'=v_pattern::text
     ) then
    raise exception 'CP5 Pattern filter did not span tracked/receipt BS and STUCK/DAMAGE claims exactly: %',v_workspace;
  end if;

  v_failed:=false;
  begin
    perform public.erp_save_bs_resolution_action_v1(
      'REVERSE_DISPOSITION',jsonb_build_object(
        'resolution_id',v_disposition,'change_reason','CP5 production must not reverse'
      ),gen_random_uuid(),v_manual_version
    );
  exception when sqlstate '42501' then v_failed:=true;
  end;
  if not v_failed then raise exception 'Production permission illegally reversed a CP5 disposition'; end if;

  perform set_config('request.jwt.claims',jsonb_build_object(
    'sub',v_owner_auth,'role','authenticated'
  )::text,true);

  v_response:=public.erp_save_bs_resolution_action_v1(
    'RESOLVE_CLAIM',jsonb_build_object(
      'laundry_claim_id',v_claim,'resolution','SETTLED',
      'change_reason','CP5 Owner offsets claim against vendor payable'
    ),gen_random_uuid(),v_claim_version
  );
  if v_response#>>'{result,status}'<>'SETTLED' then
    raise exception 'CP5 Laundry claim did not reach SETTLED: %',v_response;
  end if;
  v_claim_version:=(v_response#>>'{result,row_version}')::bigint;
  v_workspace:=public.erp_get_bs_resolution_workspace_v1(
    'CLOSED','LAUNDRY_CLAIM',v_pattern,'CP5-PATTERN-CLAIM',50,0
  );
  if (v_workspace->>'total')::integer<>1
     or v_workspace#>>'{rows,0,status}'<>'SETTLED'
     or not exists(
       select 1 from jsonb_array_elements(v_workspace#>'{lookups,settled_claims}') x
       where x->>'id'=v_claim::text and (x->>'available_qty')::integer=4
         and (x->>'available_amount')::numeric=50
     ) then
    raise exception 'CP5 CLOSED/Pattern/search filters lost the resolved claim: %',v_workspace;
  end if;

  v_response:=public.erp_save_bs_resolution_action_v1(
    'DISPOSE_BS',jsonb_build_object(
      'bs_case_id',v_manual_bs,'resolution_type','CASH_COMPENSATION','qty_pcs',2,
      'compensation_amount',50,'source_laundry_claim_id',v_claim,
      'physical_at','2026-08-22 10:00:00+00',
      'change_reason','CP5 two BS pieces covered by settled Laundry claim'
    ),gen_random_uuid(),v_manual_version
  );
  if v_response#>>'{result,status}'<>'PARTIAL' then
    raise exception 'CP5 cash-compensation disposition did not preserve partial balance: %',v_response;
  end if;
  v_cash_disposition:=(v_response#>>'{result,bs_resolution_id}')::uuid;
  v_manual_version:=(v_response#>>'{result,row_version}')::bigint;
  v_response:=public.erp_save_bs_resolution_action_v1(
    'REVERSE_DISPOSITION',jsonb_build_object(
      'resolution_id',v_cash_disposition,'change_reason','CP5 Owner corrects claim allocation'
    ),gen_random_uuid(),v_manual_version
  );
  if v_response#>>'{result,bs_case_status}'<>'PARTIAL' then
    raise exception 'CP5 cash-compensation reversal did not restore the prior BS balance: %',v_response;
  end if;
  v_manual_version:=(v_response#>>'{result,row_version}')::bigint;

  v_response:=public.erp_save_bs_resolution_action_v1(
    'REVERSE_CLAIM_RESOLUTION',jsonb_build_object(
      'laundry_claim_id',v_claim,'change_reason','CP5 Owner settlement reversal proof'
    ),gen_random_uuid(),v_claim_version
  );
  if v_response#>>'{result,status}'<>'REJECTED' then
    raise exception 'CP5 claim reversal did not preserve explicit REJECTED history state: %',v_response;
  end if;
  v_claim_version:=(v_response#>>'{result,row_version}')::bigint;
  v_response:=public.erp_save_bs_resolution_action_v1(
    'SAVE_CLAIM',jsonb_build_object(
      'id',v_claim,'action','REOPEN','change_reason','CP5 Owner reopened corrected claim'
    ),gen_random_uuid(),v_claim_version
  );
  if v_response#>>'{result,status}'<>'OPEN' then
    raise exception 'CP5 claim REOPEN failed: %',v_response;
  end if;
  v_claim_version:=(v_response#>>'{result,row_version}')::bigint;

  v_response:=public.erp_save_bs_resolution_action_v1(
    'SAVE_CLAIM',jsonb_build_object(
      'id',v_claim,'action','SAVE','status','ACCEPTED','compensation_amount',0,
      'change_reason','CP5 corrected claim has no monetary compensation'
    ),gen_random_uuid(),v_claim_version
  );
  v_claim_version:=(v_response#>>'{result,row_version}')::bigint;
  v_response:=public.erp_save_bs_resolution_action_v1(
    'RESOLVE_CLAIM',jsonb_build_object(
      'laundry_claim_id',v_claim,'resolution','WRITTEN_OFF',
      'change_reason','CP5 Owner confirms zero-value write-off'
    ),gen_random_uuid(),v_claim_version
  );
  if v_response#>>'{result,status}'<>'WRITTEN_OFF' then
    raise exception 'CP5 Laundry claim did not reach WRITTEN_OFF: %',v_response;
  end if;
  v_claim_version:=(v_response#>>'{result,row_version}')::bigint;
  v_response:=public.erp_save_bs_resolution_action_v1(
    'REVERSE_CLAIM_RESOLUTION',jsonb_build_object(
      'laundry_claim_id',v_claim,'change_reason','CP5 Owner write-off reversal proof'
    ),gen_random_uuid(),v_claim_version
  );
  v_claim_version:=(v_response#>>'{result,row_version}')::bigint;
  v_response:=public.erp_save_bs_resolution_action_v1(
    'SAVE_CLAIM',jsonb_build_object(
      'id',v_claim,'action','REOPEN','change_reason','CP5 Owner leaves corrected claim open'
    ),gen_random_uuid(),v_claim_version
  );
  if v_response#>>'{result,status}'<>'OPEN' then
    raise exception 'CP5 write-off reverse/reopen failed: %',v_response;
  end if;

  v_response:=public.erp_save_bs_resolution_action_v1(
    'REVERSE_DISPOSITION',jsonb_build_object(
      'resolution_id',v_disposition,'change_reason','CP5 Owner corrected scrap count'
    ),gen_random_uuid(),v_manual_version
  );
  if v_response#>>'{result,bs_case_status}'<>'OPEN' then
    raise exception 'CP5 disposition reversal did not restore OPEN: %',v_response;
  end if;
  v_manual_version:=(v_response#>>'{result,row_version}')::bigint;

  v_response:=public.erp_save_bs_resolution_action_v1(
    'REVERSE_REWORK_COMPLETION',jsonb_build_object(
      'rework_order_id',v_pattern_rework,
      'change_reason','CP5 Owner reverses contractor result and its journal'
    ),gen_random_uuid(),v_pattern_rework_version
  );
  if v_response#>>'{result,status}'<>'CANCELLED'
     or v_response#>>'{result,bs_case_status}'<>'OPEN' then
    raise exception 'CP5 contractor completion reversal failed: %',v_response;
  end if;
  v_response:=public.erp_save_bs_resolution_action_v1(
    'REVERSE_REWORK_COMPLETION',jsonb_build_object(
      'rework_order_id',v_manual_rework,
      'change_reason','CP5 Owner reverses rewash result'
    ),gen_random_uuid(),v_manual_rework_version
  );
  if v_response#>>'{result,status}'<>'CANCELLED'
     or v_response#>>'{result,bs_case_status}'<>'OPEN' then
    raise exception 'CP5 rewash completion reversal failed: %',v_response;
  end if;

  execute 'reset role';
  if exists(select 1 from erp.bs_resolution_execution_context) then
    raise exception 'CP5 execution capability leaked after a completed action';
  end if;
  if (select count(*) from erp.bs_case_hold_events where bs_case_id=v_manual_bs)<>2
     or exists(select 1 from erp.bs_resolutions where bs_case_id=v_manual_bs)
     or not exists(select 1 from erp.bs_cases where id=v_manual_bs and status='OPEN')
     or not exists(select 1 from erp.bs_cases where id=v_pattern_bs and status='OPEN')
     or (select count(*) from erp.rework_orders
         where id in(v_manual_rework,v_pattern_rework) and status='CANCELLED')<>2
     or not exists(select 1 from erp.rework_orders where id=v_cancel_rework and status='CANCELLED')
     or not exists(select 1 from erp.laundry_claims where id=v_claim and status='OPEN') then
    raise exception 'CP5 final state does not reconcile after reversal/reopen';
  end if;
  if exists(
    select 1 from erp.journal_entries
    where source_type='REWORK_COMPLETION' and source_id=v_pattern_rework and status='POSTED'
  ) then raise exception 'CP5 contractor reversal left an active rework journal'; end if;
  if exists(
    select 1 from erp.journal_entries
    where source_type='LAUNDRY_CLAIM_SETTLEMENT' and source_id=v_claim and status='POSTED'
  ) then raise exception 'CP5 claim reversal left an active settlement journal'; end if;

  v_failed:=false;
  begin
    update erp.bs_case_hold_events
    set reason='CP5 forbidden history rewrite'
    where bs_case_id=v_manual_bs;
  exception when sqlstate '42501' then v_failed:=true;
  end;
  if not v_failed then raise exception 'CP5 HOLD history accepted an in-place rewrite'; end if;
end
$test$;

rollback;
