-- Pre-CP5 Cutting Bridge / ERP v2.6.18 persistence, pickup distribution, and WIP acceptance.
-- Every synthetic fact is enclosed by this transaction and rolled back.
\set ON_ERROR_STOP on

begin;
set local timezone='UTC';
set local datestyle='ISO, MDY';
set local lock_timeout='8s';
set local statement_timeout='180s';

\ir cp3_r4_full_schema_seed.sql

do $test$
declare
  v_owner_app constant uuid:='c5000000-0000-4000-8000-000000000001';
  v_owner_auth constant uuid:='c5000000-0000-4000-8000-000000000101';
  v_production_app constant uuid:='c5000000-0000-4000-8000-000000000002';
  v_production_auth constant uuid:='c5000000-0000-4000-8000-000000000102';
  v_customer_app constant uuid:='c5000000-0000-4000-8000-000000000003';
  v_customer_auth constant uuid:='c5000000-0000-4000-8000-000000000103';
  v_distribution_role constant uuid:='c5000000-0000-4000-8000-000000000010';
  v_distribution_app constant uuid:='c5000000-0000-4000-8000-000000000004';
  v_distribution_auth constant uuid:='c5000000-0000-4000-8000-000000000104';
  v_bs_lookup_role constant uuid:='c5000000-0000-4000-8000-000000000011';
  v_bs_lookup_app constant uuid:='c5000000-0000-4000-8000-000000000005';
  v_bs_lookup_auth constant uuid:='c5000000-0000-4000-8000-000000000105';
  v_pattern constant uuid:='c5010000-0000-4000-8000-000000000001';
  v_size_s constant uuid:='c5010000-0000-4000-8000-000000000011';
  v_size_m constant uuid:='c5010000-0000-4000-8000-000000000012';
  v_location constant uuid:='c5020000-0000-4000-8000-000000000001';
  v_supplier constant uuid:='c5020000-0000-4000-8000-000000000002';
  v_material constant uuid:='c5020000-0000-4000-8000-000000000003';
  v_roll constant uuid:='c5020000-0000-4000-8000-000000000004';
  v_opening constant uuid:='c5020000-0000-4000-8000-000000000005';
  v_po constant uuid:='c5030000-0000-4000-8000-000000000001';
  v_cut_request constant uuid:='c5040000-0000-4000-8000-000000000001';
  v_pickup_request constant uuid:='c5040000-0000-4000-8000-000000000002';
  v_pickup_recreate_request constant uuid:='c5040000-0000-4000-8000-000000000003';
  v_component_snapshot constant uuid:='c5050000-0000-4000-8000-000000000001';
  v_work_completion constant uuid:='c5050000-0000-4000-8000-000000000002';
  v_work_line constant uuid:='c5050000-0000-4000-8000-000000000003';
  v_cut_payload jsonb;
  v_pickup_payload jsonb;
  v_cut jsonb;
  v_replay jsonb;
  v_queue jsonb;
  v_pickup jsonb;
  v_posted jsonb;
  v_wip jsonb;
  v_group uuid;
  v_pickup_id uuid;
  v_group_version bigint;
  v_pickup_version bigint;
  v_yield_s uuid;
  v_yield_m uuid;
  v_allocation_id uuid;
  v_failed boolean;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.18')
     or not exists(select 1 from erp.schema_migrations where version='v2.6.18a')
     or (select count(*) from erp.cutting_bridge_v2618_rollback_capsule)<>17
     or (select count(*) from erp.cutting_bridge_v2618a_rollback_capsule)<>8
     or to_regclass('erp.cutting_pickups') is null
     or to_regclass('erp.cutting_bridge_execution_context') is null
     or to_regprocedure('public.erp_save_cutting_group_before_sewing_v2(jsonb,uuid,bigint)') is null then
    raise exception 'Cutting Bridge v2.6.18 boundary is not installed';
  end if;
  if position('production.distribution.view' in pg_get_functiondef('erp.list_patterns_v1(text,text,integer,integer)'::regprocedure))=0
     or position('production.bs_rework.view' in pg_get_functiondef('erp.list_patterns_v1(text,text,integer,integer)'::regprocedure))=0 then
    raise exception 'Production Pattern filter permissions are incomplete';
  end if;

  insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active)
  select v_owner_app,v_owner_auth,'Bridge Synthetic Owner','OWNER',id,true
  from erp.app_roles where role_code='OWNER';
  insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active)
  select v_production_app,v_production_auth,'Bridge Synthetic Production','PRODUKSI_QC',id,true
  from erp.app_roles where role_code='PRODUKSI_QC';
  insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active)
  select v_customer_app,v_customer_auth,'Bridge Synthetic Customer','CUSTOMER',id,true
  from erp.app_roles where role_code='CUSTOMER';
  insert into erp.app_roles(id,role_code,role_name,description)
  values
    (v_distribution_role,'CBR_DIST_VIEW','Bridge Distribution View','Pattern lookup permission acceptance'),
    (v_bs_lookup_role,'CBR_BS_VIEW','Bridge BS View','Pattern lookup permission acceptance');
  insert into erp.app_role_permissions(role_id,permission_key) values
    (v_distribution_role,'production.distribution.view'),
    (v_bs_lookup_role,'production.bs_rework.view');
  insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active) values
    (v_distribution_app,v_distribution_auth,'Bridge Distribution Lookup','CBR_DIST_VIEW',v_distribution_role,true),
    (v_bs_lookup_app,v_bs_lookup_auth,'Bridge BS Lookup','CBR_BS_VIEW',v_bs_lookup_role,true);

  insert into erp.production_patterns(
    id,pattern_code,revision,pattern_name,sort_order,is_active,created_by,updated_by
  ) values(v_pattern,'CBR-REG','R1','Bridge Regular Original',10,true,v_owner_app,v_owner_app);
  insert into erp.sizes(id,size_code,sort_order) values
    (v_size_s,'CBR-S',9101),(v_size_m,'CBR-M',9102);
  insert into erp.product_model_sizes(model_id,size_id,sort_order) values
    ('a2000000-0000-0000-0000-000000000001',v_size_s,101),
    ('a2000000-0000-0000-0000-000000000001',v_size_m,102);
  insert into erp.production_orders(
    id,po_number,model_id,target_qty_pcs,status,current_stage,physical_start_at,notes
  ) values(
    v_po,'CBR-PO-CUT-001','a2000000-0000-0000-0000-000000000001',90,
    'CUTTING','CUTTING','2026-08-15 07:00+00','Cutting Bridge acceptance'
  );
  insert into erp.locations(id,location_code,location_name,location_type)
  values(v_location,'CBR-RM','Bridge Raw Material','RAW_MATERIAL_WAREHOUSE');
  insert into erp.suppliers(id,supplier_code,supplier_name,supplier_type)
  values(v_supplier,'CBR-SUP','Bridge Supplier','MATERIAL');
  insert into erp.materials(id,material_sku,material_name,material_type,unit_code)
  values(v_material,'CBR-FAB','Bridge Fabric','FABRIC','yd');
  insert into erp.material_rolls(
    id,material_id,supplier_id,roll_number,original_qty,cached_qty,status,received_at
  ) values(v_roll,v_material,v_supplier,'CBR-ROLL-001',100,100,'AVAILABLE','2026-08-14 07:00+00');
  insert into erp.material_stock_movements(
    id,material_id,roll_id,location_id,movement_type,qty_signed,input_unit_cost,
    unit_cost_snapshot,source_type,source_id,physical_at
  ) values(
    v_opening,v_material,v_roll,v_location,'OPENING',100,50000,50000,
    'CUTTING_BRIDGE_TEST_OPENING',v_roll,'2026-08-14 07:00+00'
  );
  perform erp.recalculate_material_cost(v_material);

  perform set_config('request.jwt.claims',jsonb_build_object(
    'sub',v_distribution_auth,'role','authenticated'
  )::text,true);
  execute 'set local role authenticated';
  v_queue:=public.erp_list_patterns_v1('ALL','CBR-REG',50,0);
  if (v_queue->>'total')::integer<>1 then
    raise exception 'Distribution-view Pattern filter lookup is empty: %',v_queue;
  end if;
  perform set_config('request.jwt.claims',jsonb_build_object(
    'sub',v_bs_lookup_auth,'role','authenticated'
  )::text,true);
  v_queue:=public.erp_list_patterns_v1('ALL','CBR-REG',50,0);
  if (v_queue->>'total')::integer<>1 then
    raise exception 'BS-view Pattern filter lookup is empty: %',v_queue;
  end if;
  perform set_config('request.jwt.claims',jsonb_build_object(
    'sub',v_production_auth,'role','authenticated'
  )::text,true);

  v_queue:=public.erp_get_cutting_workspace_v1(null,v_location,100,0);
  if v_queue->>'location_id'<>v_location::text
     or (v_queue->>'roll_total')::integer<>1
     or not exists(
       select 1 from jsonb_array_elements(v_queue->'orders') x
       where x->>'id'=v_po::text
     )
     or not exists(
       select 1 from jsonb_array_elements(v_queue->'rolls') x
       where x->>'id'=v_roll::text and (x->>'available_qty')::numeric=100
     )
     or not exists(
       select 1 from jsonb_array_elements(v_queue->'sizes') x
       where x->>'id'=v_size_s::text
         and (x->'model_ids') @> jsonb_build_array('a2000000-0000-0000-0000-000000000001')
     ) then
    raise exception 'Connected cutting workspace lost canonical order/location/roll facts: %',v_queue;
  end if;

  v_cut_payload:=jsonb_build_object(
    'action','SAVE_DRAFT','po_id',v_po,'pattern_id',v_pattern,'source_location_id',v_location,
    'cut_at','2026-08-15 08:00:00+00','change_reason','Cutting Bridge exact cutting draft',
    'notes','Cutting Bridge authoritative Potongan',
    'size_slots',jsonb_build_array(
      jsonb_build_object('slot_no',1,'size_id',v_size_s,'drawing_no',1),
      jsonb_build_object('slot_no',2,'size_id',v_size_m,'drawing_no',1)
    ),
    'rolls',jsonb_build_array(jsonb_build_object(
      'roll_id',v_roll,'qty_issued',100,'qty_consumed',94,'qty_reported_remaining',6,
      'yields',jsonb_build_array(
        jsonb_build_object('slot_no',1,'qty_pcs',40),
        jsonb_build_object('slot_no',2,'qty_pcs',50)
      )
    ))
  );
  v_cut:=public.erp_save_cutting_group_before_sewing_v2(v_cut_payload,v_cut_request,null);
  v_replay:=public.erp_save_cutting_group_before_sewing_v2(v_cut_payload,v_cut_request,null);
  if v_cut is distinct from v_replay then
    raise exception 'Cutting double-click/idempotent replay diverged';
  end if;
  v_group:=(v_cut->>'cutting_group_id')::uuid;
  v_group_version:=(v_cut->>'row_version')::bigint;
  execute 'reset role';
  if (v_cut->>'material_issue_posted')::boolean
     or exists(
       select 1 from erp.material_stock_movements
       where source_type='CUTTING_GROUP' and source_id=v_group
     ) then
    raise exception 'Cutting draft moved stock before POST: %',v_cut;
  end if;

  -- Updating a draft replaces its child roll/slot/yield graph atomically.
  -- This catches stale child rows and validates the draft-edit path separately
  -- from idempotent double-click replay.
  v_cut_payload:=v_cut_payload||jsonb_build_object(
    'id',v_group,'action','SAVE_DRAFT','notes','Cutting Bridge revised draft',
    'change_reason','Cutting Bridge draft edit'
  );
  execute 'set local role authenticated';
  v_cut:=public.erp_save_cutting_group_before_sewing_v2(
    v_cut_payload,gen_random_uuid(),v_group_version
  );
  v_group_version:=(v_cut->>'row_version')::bigint;
  execute 'reset role';
  if not exists(
    select 1 from erp.cutting_groups
    where id=v_group and notes='Cutting Bridge revised draft'
  ) or (select count(*) from erp.cutting_group_rolls where cutting_group_id=v_group)<>1
     or (select count(*) from erp.cutting_group_size_slots where cutting_group_id=v_group)<>2
     or (select count(*) from erp.cutting_roll_yields y
         join erp.cutting_group_rolls r on r.id=y.cutting_group_roll_id
         where r.cutting_group_id=v_group)<>2 then
    raise exception 'Cutting draft update left stale or duplicate child facts';
  end if;

  v_cut_payload:=v_cut_payload||jsonb_build_object(
    'action','POST','change_reason','Cutting Bridge exact cutting post'
  );
  execute 'set local role authenticated';
  v_cut:=public.erp_save_cutting_group_before_sewing_v2(
    v_cut_payload,gen_random_uuid(),v_group_version
  );
  v_group_version:=(v_cut->>'row_version')::bigint;
  if v_cut->>'pattern_id'<>v_pattern::text
     or v_cut->>'pattern_code'<>'CBR-REG'
     or v_cut->>'pattern_revision'<>'R1'
     or (v_cut->>'total_rolls')::integer<>1
     or (v_cut->>'total_qty_issued')::numeric<>100
     or (v_cut->>'total_qty_consumed')::numeric<>94
     or (v_cut->>'total_qty_reported_remaining')::numeric<>6
     or (v_cut->>'total_pieces')::integer<>90
     or (v_cut->>'material_issue_posted')::boolean is not true then
    raise exception 'Atomic cutting response did not reconcile: %',v_cut;
  end if;
  execute 'reset role';
  if not exists(
    select 1 from erp.cutting_groups
    where id=v_group and po_id=v_po and source_location_id=v_location
      and pattern_id=v_pattern and pattern_code_snapshot='CBR-REG'
      and pattern_revision_snapshot='R1' and pattern_name_snapshot='Bridge Regular Original'
      and status='CUT' and picked_up_at is null and material_issue_posted
  ) or not exists(
    select 1 from erp.cutting_group_rolls
    where cutting_group_id=v_group and roll_id=v_roll
      and qty_issued=100 and qty_consumed=94 and qty_reported_remaining=6
      and qty_physically_returned=0 and return_destination='NONE'
  ) then
    raise exception 'Canonical cutting rows or immutable pattern snapshot are incomplete';
  end if;
  if (select count(*) from erp.material_stock_movements
      where source_type='CUTTING_GROUP' and source_id=v_group and movement_type='CUTTING_ISSUE')<>1
     or (select coalesce(sum(qty_signed),0) from erp.material_stock_movements
         where roll_id=v_roll and location_id=v_location)<>0
     or not exists(select 1 from erp.material_rolls where id=v_roll and cached_qty=0 and status='EXHAUSTED')
     or (select count(*) from erp.journal_entries
         where source_type='CUTTING_MATERIAL_ISSUE' and source_id=v_group and status='POSTED')<>1 then
    raise exception 'Cutting post did not atomically move/cost/journal exactly once';
  end if;

  execute 'set local role authenticated';
  v_failed:=false;
  begin
    perform public.erp_save_cutting_group_before_sewing_v2(
      v_cut_payload||jsonb_build_object('id',v_group,'action','SAVE_DRAFT','change_reason','must reject late edit'),
      gen_random_uuid(),v_group_version
    );
  exception when others then
    if sqlerrm like '%sudah diposting%' then v_failed:=true; else raise; end if;
  end;
  if not v_failed then raise exception 'Posted Potongan accepted an in-place edit'; end if;

  v_queue:=public.erp_get_cutting_pickup_queue_v1('WAITING',v_pattern,'CBR-REG',50,0);
  if (v_queue->>'total')::integer<>1
     or v_queue#>>'{rows,0,cutting_group_id}'<>v_group::text
     or v_queue#>>'{rows,0,pattern_name}'<>'Bridge Regular Original'
     or (v_queue#>>'{rows,0,total_qty_issued}')::numeric<>100
     or (v_queue#>>'{rows,0,total_pieces}')::integer<>90
     or (v_queue#>>'{rows,0,rolls,0,qty_consumed}')::numeric<>94
     or (v_queue#>>'{rows,0,rolls,0,qty_reported_remaining}')::numeric<>6 then
    raise exception 'Pickup queue lost cutting, Pola, roll, or size lineage: %',v_queue;
  end if;
  v_queue:=public.erp_get_cutting_pickup_queue_v1(
    'ALL','c5010000-0000-4000-8000-000000000099','CBR',50,0
  );
  if (v_queue->>'total')::integer<>0 or jsonb_array_length(v_queue->'rows')<>0 then
    raise exception 'Pickup queue ignored exact server-side pattern_id filter: %',v_queue;
  end if;
  execute 'reset role';
  select y.id into v_yield_s
  from erp.cutting_roll_yields y
  join erp.cutting_group_rolls r on r.id=y.cutting_group_roll_id
  join erp.cutting_group_size_slots s on s.id=y.size_slot_id
  where r.cutting_group_id=v_group and s.slot_no=1;
  select y.id into v_yield_m
  from erp.cutting_roll_yields y
  join erp.cutting_group_rolls r on r.id=y.cutting_group_roll_id
  join erp.cutting_group_size_slots s on s.id=y.size_slot_id
  where r.cutting_group_id=v_group and s.slot_no=2;

  v_pickup_payload:=jsonb_build_object(
    'action','SAVE_DRAFT','cutting_group_id',v_group,
    'contractor_id','a1000000-0000-0000-0000-000000000001',
    'picked_up_at','2026-08-15 10:00:00+00','allocation_mode','ROLL',
    'expected_group_version',v_group_version,'change_reason','Cutting Bridge exact pickup draft',
    'batches',jsonb_build_array(
      jsonb_build_object('batch_no',1,'notes','Bridge Batch S','allocations',jsonb_build_array(
        jsonb_build_object('cutting_roll_yield_id',v_yield_s,'qty_pcs',40)
      )),
      jsonb_build_object('batch_no',2,'notes','Bridge Batch M','allocations',jsonb_build_array(
        jsonb_build_object('cutting_roll_yield_id',v_yield_m,'qty_pcs',50)
      ))
    )
  );
  execute 'set local role authenticated';
  v_pickup:=public.erp_save_cutting_pickup_v1(v_pickup_payload,v_pickup_request,null);
  v_replay:=public.erp_save_cutting_pickup_v1(v_pickup_payload,v_pickup_request,null);
  if v_pickup is distinct from v_replay then
    raise exception 'Pickup double-click/idempotent replay diverged';
  end if;
  v_pickup_id:=(v_pickup->>'pickup_id')::uuid;
  v_pickup_version:=(v_pickup->>'row_version')::bigint;
  if v_pickup->>'status'<>'DRAFT' or (v_pickup->>'allocated_pieces')::integer<>90
     or (v_pickup->>'batch_count')::integer<>2 then
    raise exception 'Pickup draft did not preserve exact distribution: %',v_pickup;
  end if;

  v_failed:=false;
  begin
    perform public.erp_save_cutting_pickup_v1(
      v_pickup_payload||jsonb_build_object('change_reason','same request id, different payload'),
      v_pickup_request,null
    );
  exception when others then
    if sqlerrm='client_request_id was already used with a different payload' then v_failed:=true; else raise; end if;
  end;
  if not v_failed then raise exception 'Pickup idempotency key accepted a different payload'; end if;

  v_pickup:=public.erp_save_cutting_pickup_v1(
    v_pickup_payload||jsonb_build_object(
      'id',v_pickup_id,'action','DELETE','change_reason','Cutting Bridge draft delete'
    ),gen_random_uuid(),v_pickup_version
  );
  execute 'reset role';
  if v_pickup->>'status'<>'DELETED'
     or exists(select 1 from erp.cutting_pickups where id=v_pickup_id)
     or exists(
       select 1 from erp.cutting_distribution_batches where pickup_id=v_pickup_id
     ) then raise exception 'Pickup draft delete left orphan rows: %',v_pickup; end if;

  execute 'set local role authenticated';
  v_pickup:=public.erp_save_cutting_pickup_v1(
    v_pickup_payload||jsonb_build_object('change_reason','Cutting Bridge pickup recreate'),
    v_pickup_recreate_request,null
  );
  v_pickup_id:=(v_pickup->>'pickup_id')::uuid;
  v_pickup_version:=(v_pickup->>'row_version')::bigint;

  v_failed:=false;
  begin
    perform public.erp_save_cutting_pickup_v1(
      v_pickup_payload||jsonb_build_object(
        'id',v_pickup_id,'action','SAVE_DRAFT','change_reason','must reject stale pickup'
      ),gen_random_uuid(),v_pickup_version-1
    );
  exception when others then
    if sqlerrm like 'STALE_VERSION expected %, current %' then v_failed:=true; else raise; end if;
  end;
  if not v_failed then raise exception 'Pickup draft accepted a stale row version'; end if;

  v_failed:=false;
  begin
    perform public.erp_save_cutting_pickup_v1(
      v_pickup_payload||jsonb_build_object(
        'id',v_pickup_id,'action','POST','change_reason','must reject incomplete distribution',
        'batches',jsonb_build_array(
          jsonb_build_object('batch_no',1,'notes','Bridge Batch S','allocations',jsonb_build_array(
            jsonb_build_object('cutting_roll_yield_id',v_yield_s,'qty_pcs',39)
          )),
          jsonb_build_object('batch_no',2,'notes','Bridge Batch M','allocations',jsonb_build_array(
            jsonb_build_object('cutting_roll_yield_id',v_yield_m,'qty_pcs',50)
          ))
        )
      ),gen_random_uuid(),v_pickup_version
    );
  exception when sqlstate '23514' then
    if sqlerrm='POSTED_DISTRIBUTION_MUST_EXACTLY_RECONCILE_EVERY_SOURCE_YIELD' then v_failed:=true; else raise; end if;
  end;
  if not v_failed then raise exception 'Pickup POST accepted an under-allocation'; end if;

  v_pickup_payload:=v_pickup_payload||jsonb_build_object(
    'id',v_pickup_id,'action','POST','change_reason','Cutting Bridge exact pickup post'
  );
  v_posted:=public.erp_save_cutting_pickup_v1(
    v_pickup_payload,gen_random_uuid(),v_pickup_version
  );
  v_group_version:=(v_posted->>'group_row_version')::bigint;
  v_pickup_version:=(v_posted->>'row_version')::bigint;
  execute 'reset role';
  if v_posted->>'status'<>'POSTED'
     or (v_posted->>'allocated_pieces')::integer<>90
     or not exists(
       select 1 from erp.cutting_groups
       where id=v_group and status='PICKED_UP' and picked_up_at='2026-08-15 10:00:00+00'
         and executor_name='CP3 R3 Normal A'
     )
     or not exists(select 1 from erp.production_orders
       where id=v_po and status='SEWING' and current_stage='SEWING'
         and contractor_id='a1000000-0000-0000-0000-000000000001')
     or (select sum(a.qty_pcs) from erp.cutting_distribution_allocations a
         join erp.cutting_distribution_batches b on b.id=a.batch_id
         where b.pickup_id=v_pickup_id)<>90 then
    raise exception 'Posted pickup did not advance exact canonical state: %',v_posted;
  end if;

  execute 'set local role authenticated';
  v_wip:=public.erp_get_wip_control_v1('ALL',v_pattern,'PRODUCTION','CBR-PO-CUT-001');
  if not exists(
    select 1 from jsonb_array_elements(v_wip->'rows') x
    where x->>'cutting_group_id'=v_group::text
      and (x->>'effective_qty_pcs')::integer=90
      and x#>>'{distribution,pickup_id}'=v_pickup_id::text
      and x#>>'{distribution,contractor_name}'='CP3 R3 Normal A'
      and jsonb_array_length(x#>'{distribution,batches}')=2
  ) then
    raise exception 'Connected WIP did not carry pickup/batch/size continuity: %',v_wip;
  end if;

  -- A fully sewn quantity is still ACTIVE until it has a downstream handoff.
  -- This is the regression that prevents completed_qty=batch_qty from making
  -- a live WIP row disappear before Laundry/QC/BS resolution is complete.
  execute 'reset role';
  insert into erp.po_work_component_snapshots(
    id,po_id,work_component_id,sequence_no,rate_per_pcs_snapshot,committed_at
  ) values(
    v_component_snapshot,v_po,'a4000000-0000-0000-0000-000000000001',1,0,
    '2026-08-15 10:30:00+00'
  );
  insert into erp.work_completion_events(
    id,completion_number,po_id,contractor_id,cutting_group_id,
    physical_at,status,notes,created_by
  ) values(
    v_work_completion,'WC-CBR-FULL-001',v_po,
    'a1000000-0000-0000-0000-000000000001',v_group,
    '2026-08-15 11:00:00+00','DRAFT',
    'Cutting Bridge fully sewn but not handed off',v_production_app
  );
  insert into erp.work_completion_lines(
    id,completion_id,po_component_snapshot_id,work_component_id,
    qty_completed,qty_payable,rate_snapshot,notes
  ) values(
    v_work_line,v_work_completion,v_component_snapshot,
    'a4000000-0000-0000-0000-000000000001',90,90,0,
    'Cutting Bridge canonical sewing completion'
  );
  perform erp.post_work_completion(v_work_completion);

  perform set_config('request.jwt.claims',jsonb_build_object(
    'sub',v_owner_auth,'role','authenticated'
  )::text,true);
  execute 'set local role authenticated';
  perform public.erp_record_sewing_terminal_v1(jsonb_build_object(
    'work_completion_id',v_work_completion,
    'qty_pcs',90,
    'reason','Cutting Bridge fully sewn but not handed off'
  ),gen_random_uuid());

  perform set_config('request.jwt.claims',jsonb_build_object(
    'sub',v_production_auth,'role','authenticated'
  )::text,true);
  v_wip:=public.erp_get_wip_control_v1('ALL',v_pattern,'PRODUCTION','CBR-PO-CUT-001');
  if not exists(
    select 1 from jsonb_array_elements(v_wip->'rows') x
    where x->>'cutting_group_id'=v_group::text
      and (x->>'sewn_qty_pcs')::integer=90
      and (x->>'unsent_ready_qty_pcs')::integer=90
      and x->>'control_status'='ACTIVE'
  ) then raise exception 'Fully sewn but unsent WIP was hidden as Completed: %',v_wip; end if;

  v_wip:=public.erp_get_wip_control_v1(
    'ALL','c5010000-0000-4000-8000-000000000099','PRODUCTION','CBR'
  );
  if jsonb_array_length(v_wip->'rows')<>0 then
    raise exception 'Connected WIP ignored exact server-side pattern_id filter: %',v_wip;
  end if;

  v_failed:=false;
  begin
    perform public.erp_save_cutting_pickup_v1(
      v_pickup_payload||jsonb_build_object('change_reason','must reject posted edit'),
      gen_random_uuid(),v_pickup_version
    );
  exception when sqlstate '42501' then
    if sqlerrm='POSTED_CUTTING_PICKUP_IS_IMMUTABLE' then v_failed:=true; else raise; end if;
  end;
  if not v_failed then raise exception 'Posted pickup accepted an in-place edit'; end if;
  execute 'reset role';
  perform set_config('request.jwt.claims','{}',true);

  update erp.production_patterns set pattern_name='Bridge Master Renamed Later' where id=v_pattern;
  if not exists(
    select 1 from erp.cutting_groups
    where id=v_group and pattern_name_snapshot='Bridge Regular Original'
  ) then raise exception 'Master Pola rename rewrote historical cutting/pickup identity'; end if;

  select a.id into v_allocation_id
  from erp.cutting_distribution_allocations a
  join erp.cutting_distribution_batches b on b.id=a.batch_id
  where b.pickup_id=v_pickup_id order by b.batch_no limit 1;
  v_failed:=false;
  begin update erp.cutting_distribution_allocations set qty_pcs=qty_pcs-1 where id=v_allocation_id;
  exception when sqlstate '42501' then
    if sqlerrm='POSTED_CUTTING_DISTRIBUTION_IS_IMMUTABLE' then v_failed:=true; else raise; end if;
  end;
  if not v_failed then raise exception 'Posted distribution allocation accepted direct update'; end if;
  v_failed:=false;
  begin delete from erp.cutting_distribution_allocations where id=v_allocation_id;
  exception when sqlstate '42501' then
    if sqlerrm='POSTED_CUTTING_DISTRIBUTION_IS_IMMUTABLE' then v_failed:=true; else raise; end if;
  end;
  if not v_failed then raise exception 'Posted distribution allocation accepted direct delete'; end if;

  perform set_config('request.jwt.claims',jsonb_build_object(
    'sub',v_customer_auth,'role','authenticated'
  )::text,true);
  execute 'set local role authenticated';
  v_failed:=false;
  begin perform public.erp_get_cutting_workspace_v1(null,null,100,0);
  exception when sqlstate '42501' then v_failed:=true; end;
  if not v_failed then raise exception 'Unauthorized user read the cutting workspace'; end if;
  v_failed:=false;
  begin perform public.erp_save_cutting_pickup_v1(v_pickup_payload,gen_random_uuid(),v_pickup_version);
  exception when sqlstate '42501' then v_failed:=true; end;
  if not v_failed then raise exception 'Unauthorized user wrote pickup state'; end if;
  execute 'reset role';
  perform set_config('request.jwt.claims','{}',true);

  if has_function_privilege('anon','public.erp_get_cutting_workspace_v1(text,uuid,integer,integer)','EXECUTE')
     or has_function_privilege('anon','public.erp_save_cutting_group_before_sewing_v2(jsonb,uuid,bigint)','EXECUTE')
     or has_function_privilege('anon','public.erp_get_cutting_pickup_queue_v1(text,uuid,text,integer,integer)','EXECUTE')
     or has_function_privilege('anon','public.erp_save_cutting_pickup_v1(jsonb,uuid,bigint)','EXECUTE')
     or has_function_privilege('authenticated','erp.save_cutting_group_before_sewing_v2(jsonb,uuid,bigint)','EXECUTE')
     or has_function_privilege('authenticated','erp.post_cutting_material_issue(uuid,uuid)','EXECUTE')
     or has_function_privilege('authenticated','erp.post_journal(text,uuid,date,text,jsonb)','EXECUTE')
     or has_function_privilege('authenticated','erp.require_internal()','EXECUTE')
     or has_table_privilege('authenticated','erp.cutting_groups','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('authenticated','erp.cutting_pickups','SELECT,INSERT,UPDATE,DELETE')
     or has_table_privilege('authenticated','erp.cutting_bridge_execution_context','SELECT,INSERT,UPDATE,DELETE')
     or exists(select 1 from erp.cutting_bridge_execution_context)
     or not (select relrowsecurity from pg_class where oid='erp.cutting_bridge_v2618_rollback_capsule'::regclass)
     or not (select relrowsecurity from pg_class where oid='erp.cutting_bridge_v2618a_rollback_capsule'::regclass)
     or pg_get_functiondef('erp.require_internal()'::regprocedure) not like '%cutting_bridge_execution_context%'
     or pg_get_functiondef('erp._recalculate_material_cost_core(uuid,timestamp with time zone,boolean)'::regprocedure)
          not like '%require_internal%'
     or md5(pg_get_functiondef('erp.require_owner_admin()'::regprocedure))<>'965de305e5a381cfdf5588f2b9d4babc' then
    raise exception 'Cutting Bridge facade/private-table/CP4 owner boundary regressed';
  end if;

  raise notice 'Pre-CP5 Cutting Bridge persistence, pickup, and WIP acceptance PASS';
end
$test$;

rollback;
