-- CP4.5 v2.6.17a immutable pattern assignment acceptance.
-- Every synthetic row is enclosed by this transaction and rolled back.
\set ON_ERROR_STOP on

begin;
set local timezone='UTC';
set local datestyle='ISO, MDY';
set local lock_timeout='8s';
set local statement_timeout='180s';

\ir cp3_r4_full_schema_seed.sql

do $test$
declare
  v_owner_app constant uuid:='c4570000-0000-4000-8000-000000000001';
  v_owner_auth constant uuid:='c4570000-0000-4000-8000-000000000101';
  v_customer_app constant uuid:='c4570000-0000-4000-8000-000000000002';
  v_customer_auth constant uuid:='c4570000-0000-4000-8000-000000000102';
  v_pattern_a constant uuid:='c4570000-0000-4000-8000-000000000201';
  v_pattern_b constant uuid:='c4570000-0000-4000-8000-000000000202';
  v_group_first constant uuid:='c4570000-0000-4000-8000-000000000301';
  v_group_unauthorized constant uuid:='c4570000-0000-4000-8000-000000000302';
  v_group_status constant uuid:='c4570000-0000-4000-8000-000000000303';
  v_group_material constant uuid:='c4570000-0000-4000-8000-000000000304';
  v_group_sewing constant uuid:='c4570000-0000-4000-8000-000000000310';
  v_group_laundry constant uuid:='c4570000-0000-4000-8000-000000000311';
  v_group_qc constant uuid:='c4570000-0000-4000-8000-000000000312';
  v_group_fg constant uuid:='c4570000-0000-4000-8000-000000000313';
  v_group_inactive constant uuid:='c4570000-0000-4000-8000-000000000314';
  v_request constant uuid:='c4570000-0000-4000-8000-000000000401';
  v_product constant uuid:='c4570000-0000-4000-8000-000000000501';
  v_first jsonb;
  v_replay jsonb;
  v_version bigint;
  v_expected_failure boolean;
  v_gid uuid;
  v_guard_def text:=pg_get_functiondef('erp.assert_pattern_initial_assignment_allowed(uuid)'::regprocedure);
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.17a')
     or (select count(*) from erp.cp45_v2617a_rollback_capsule)<>2
     or to_regprocedure('erp.assert_pattern_initial_assignment_allowed(uuid)') is null then
    raise exception 'v2.6.17a correction boundary is not installed';
  end if;
  if v_guard_def like '%cutting_group_rolls%'
     or v_guard_def like '%cutting_group_size_slots%' then
    raise exception 'Initial composition rows were incorrectly classified as downstream facts';
  end if;
  if has_function_privilege('public','erp.assert_pattern_initial_assignment_allowed(uuid)','EXECUTE')
     or has_function_privilege('anon','erp.assert_pattern_initial_assignment_allowed(uuid)','EXECUTE')
     or has_function_privilege('authenticated','erp.assert_pattern_initial_assignment_allowed(uuid)','EXECUTE')
     or has_function_privilege('service_role','erp.assert_pattern_initial_assignment_allowed(uuid)','EXECUTE') then
    raise exception 'Private assignment guard is directly executable';
  end if;

  insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active)
  select v_owner_app,v_owner_auth,'CP45A Synthetic Owner','OWNER',id,true
  from erp.app_roles where role_code='OWNER';
  insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active)
  select v_customer_app,v_customer_auth,'CP45A Synthetic Customer','CUSTOMER',id,true
  from erp.app_roles where role_code='CUSTOMER';

  insert into erp.production_patterns(
    id,pattern_code,revision,pattern_name,sort_order,is_active,created_by,updated_by
  ) values
    (v_pattern_a,'CP45A-A','R1','CP45A Pattern A',10,true,v_owner_app,v_owner_app),
    (v_pattern_b,'CP45A-B','R1','CP45A Pattern B',20,true,v_owner_app,v_owner_app);

  insert into erp.cutting_groups(
    id,po_id,group_number,cut_at,picked_up_at,status,material_issue_posted,
    material_return_posted,cutting_batch_id,notes
  ) values
    (v_group_first,'a3000000-0000-0000-0000-000000000001','CP45A-FIRST','2026-01-02 08:00+00',null,'CUT',false,false,'a3100000-0000-0000-0000-000000000001','first assignment'),
    (v_group_unauthorized,'a3000000-0000-0000-0000-000000000001','CP45A-UNAUTH','2026-01-02 08:01+00',null,'CUT',false,false,'a3100000-0000-0000-0000-000000000001','unauthorized'),
    (v_group_status,'a3000000-0000-0000-0000-000000000001','CP45A-STATUS','2026-01-02 08:02+00','2026-01-02 08:03+00','SEWING',false,false,'a3100000-0000-0000-0000-000000000001','status blocker'),
    (v_group_material,'a3000000-0000-0000-0000-000000000001','CP45A-MATERIAL','2026-01-02 08:04+00',null,'CUT',true,false,'a3100000-0000-0000-0000-000000000001','material blocker'),
    (v_group_sewing,'a3000000-0000-0000-0000-000000000001','CP45A-SEW','2026-01-02 08:05+00',null,'CUT',false,false,'a3100000-0000-0000-0000-000000000001','sewing fact blocker'),
    (v_group_laundry,'a3000000-0000-0000-0000-000000000001','CP45A-LAUNDRY','2026-01-02 08:06+00',null,'CUT',false,false,'a3100000-0000-0000-0000-000000000001','laundry fact blocker'),
    (v_group_qc,'a3000000-0000-0000-0000-000000000001','CP45A-QC','2026-01-02 08:07+00',null,'CUT',false,false,'a3100000-0000-0000-0000-000000000001','QC fact blocker'),
    (v_group_fg,'a3000000-0000-0000-0000-000000000001','CP45A-FG','2026-01-02 08:08+00',null,'CUT',false,false,'a3100000-0000-0000-0000-000000000001','FG fact blocker'),
    (v_group_inactive,'a3000000-0000-0000-0000-000000000001','CP45A-INACTIVE','2026-01-02 08:09+00',null,'CUT',false,false,'a3100000-0000-0000-0000-000000000001','inactive target');

  v_expected_failure:=false;
  begin
    insert into erp.cutting_groups(
      id,po_id,group_number,cut_at,picked_up_at,status,cutting_batch_id,pattern_id,notes
    ) values(
      'c4570000-0000-4000-8000-000000000315',
      'a3000000-0000-0000-0000-000000000001','CP45A-INSERT-BYPASS',
      '2026-01-02 08:10+00','2026-01-02 08:11+00','SEWING',
      'a3100000-0000-0000-0000-000000000001',v_pattern_a,'must fail'
    );
  exception when sqlstate '23514' then
    if sqlerrm='PATTERN_INITIAL_ASSIGNMENT_REQUIRES_PRISTINE_CUTTING' then
      v_expected_failure:=true;
    else raise;
    end if;
  end;
  if not v_expected_failure then raise exception 'Non-pristine direct insert bypassed initial binding guard'; end if;

  -- A size slot is draft composition, not a downstream fact. First assignment
  -- must still succeed with this structural child already present.
  insert into erp.cutting_group_size_slots(id,cutting_group_id,slot_no,size_id,drawing_no)
  values('c4570000-0000-4000-8000-000000000601',v_group_first,1,
    'a2100000-0000-0000-0000-000000000001',1);

  insert into erp.work_completion_events(
    id,completion_number,po_id,contractor_id,cutting_group_id,physical_at,status,notes
  ) values(
    'c4570000-0000-4000-8000-000000000610','CP45A-WC',
    'a3000000-0000-0000-0000-000000000001','a1000000-0000-0000-0000-000000000001',
    v_group_sewing,'2026-01-02 09:00+00','DRAFT','CP45A sewing fact'
  );

  insert into erp.laundry_vendors(id,vendor_code,vendor_name)
  values('c4570000-0000-4000-8000-000000000620','CP45A-L','CP45A Laundry');
  insert into erp.laundry_deliveries(
    id,delivery_number,po_id,vendor_id,target_dyeing_color,physical_at,status
  ) values(
    'c4570000-0000-4000-8000-000000000621','CP45A-DELIVERY',
    'a3000000-0000-0000-0000-000000000001','c4570000-0000-4000-8000-000000000620',
    'N/A','2026-01-02 09:01+00','DRAFT'
  );
  insert into erp.laundry_delivery_lines(id,delivery_id,cutting_group_id,qty_sent_pcs)
  values('c4570000-0000-4000-8000-000000000622',
    'c4570000-0000-4000-8000-000000000621',v_group_laundry,1);

  insert into erp.brands(id,brand_code,brand_name)
  values('c4570000-0000-4000-8000-000000000630','CP45A-BRAND','CP45A Brand');
  insert into erp.products(
    id,sku,model_id,brand_id,color_name,size_id,product_name,
    identity_root_id,effective_from,is_active
  ) values(
    v_product,'CP45A-SKU','a2000000-0000-0000-0000-000000000001',
    'c4570000-0000-4000-8000-000000000630','N/A',
    'a2100000-0000-0000-0000-000000000001','CP45A Product',
    v_product,'2025-01-01 00:00+00',true
  );
  insert into erp.qc_inspections(id,inspection_number,po_id,physical_at,status,notes)
  values('c4570000-0000-4000-8000-000000000631','CP45A-QC',
    'a3000000-0000-0000-0000-000000000001','2026-01-02 09:02+00','DRAFT','CP45A QC');
  insert into erp.qc_inspection_items(
    id,inspection_id,cutting_group_id,final_product_id,qty_good_pcs,qty_bs_pcs,notes
  ) values(
    'c4570000-0000-4000-8000-000000000632','c4570000-0000-4000-8000-000000000631',
    v_group_qc,v_product,1,0,'CP45A QC fact'
  );
  insert into erp.fg_lots(
    id,lot_number,po_id,product_id,initial_qty_pcs,cached_qty_pcs,produced_at,cutting_group_id
  ) values(
    'c4570000-0000-4000-8000-000000000633','CP45A-FG',
    'a3000000-0000-0000-0000-000000000001',v_product,1,1,'2026-01-02 09:03+00',v_group_fg
  );

  select row_version into v_version from erp.cutting_groups where id=v_group_first;
  perform set_config('request.jwt.claims',jsonb_build_object('sub',v_owner_auth,'role','authenticated')::text,true);
  execute 'set local role authenticated';
  v_first:=public.erp_assign_pattern_v1(v_group_first,v_pattern_a,'CP45A first binding',v_request,v_version);
  v_replay:=public.erp_assign_pattern_v1(v_group_first,v_pattern_a,'CP45A first binding',v_request,v_version);
  if v_first is distinct from v_replay then
    raise exception 'First assignment idempotent replay diverged';
  end if;
  if v_first->>'pattern_id'<>v_pattern_a::text
     or v_first->>'code_snapshot'<>'CP45A-A'
     or v_first->>'revision_snapshot'<>'R1'
     or v_first->>'name_snapshot'<>'CP45A Pattern A' then
    raise exception 'First assignment did not bind the canonical snapshot: %',v_first;
  end if;

  v_version:=(v_first->>'row_version')::bigint;
  v_expected_failure:=false;
  begin
    perform public.erp_assign_pattern_v1(v_group_first,v_pattern_b,'forbidden second binding',gen_random_uuid(),v_version);
  exception when sqlstate '23514' then
    if sqlerrm='PATTERN_IDENTITY_ALREADY_BOUND' then v_expected_failure:=true; else raise; end if;
  end;
  if not v_expected_failure then raise exception 'Second assignment was accepted'; end if;
  execute 'reset role';
  perform set_config('request.jwt.claims','{}',true);

  foreach v_gid in array array[v_group_first] loop
    v_expected_failure:=false;
    begin update erp.cutting_groups set pattern_id=v_pattern_b where id=v_gid;
    exception when sqlstate '42501' then
      if sqlerrm='PATTERN_ASSIGNMENT_SNAPSHOT_IMMUTABLE' then v_expected_failure:=true; else raise; end if;
    end;
    if not v_expected_failure then raise exception 'Direct pattern rebind was accepted'; end if;

    v_expected_failure:=false;
    begin update erp.cutting_groups set pattern_id=null where id=v_gid;
    exception when sqlstate '42501' then
      if sqlerrm='PATTERN_ASSIGNMENT_SNAPSHOT_IMMUTABLE' then v_expected_failure:=true; else raise; end if;
    end;
    if not v_expected_failure then raise exception 'Direct pattern unbind was accepted'; end if;

    v_expected_failure:=false;
    begin update erp.cutting_groups set pattern_name_snapshot='TAMPERED' where id=v_gid;
    exception when sqlstate '42501' then
      if sqlerrm='PATTERN_ASSIGNMENT_SNAPSHOT_IMMUTABLE' then v_expected_failure:=true; else raise; end if;
    end;
    if not v_expected_failure then raise exception 'Direct pattern snapshot tamper was accepted'; end if;
  end loop;

  update erp.production_patterns set pattern_name='CP45A Master Renamed' where id=v_pattern_a;
  if not exists(
    select 1 from erp.cutting_groups
    where id=v_group_first and pattern_id=v_pattern_a
      and pattern_name_snapshot='CP45A Pattern A'
      and pattern_code_snapshot='CP45A-A'
      and pattern_revision_snapshot='R1'
  ) then raise exception 'Master edit rewrote the historical Potongan snapshot'; end if;
  if (select count(*) from erp.production_pattern_audit
      where entity_type='ASSIGNMENT' and entity_id=v_group_first and action='ASSIGN')<>1 then
    raise exception 'First assignment did not produce exactly one immutable audit fact';
  end if;

  perform set_config('request.jwt.claims',jsonb_build_object('sub',v_customer_auth,'role','authenticated')::text,true);
  execute 'set local role authenticated';
  v_version:=1;
  v_expected_failure:=false;
  begin
    perform public.erp_assign_pattern_v1(v_group_unauthorized,v_pattern_a,'unauthorized',gen_random_uuid(),v_version);
  exception when sqlstate '42501' then
    if sqlerrm like 'PERMISSION_DENIED:%' then v_expected_failure:=true; else raise; end if;
  end;
  if not v_expected_failure then raise exception 'Unauthorized assignment was accepted'; end if;
  execute 'reset role';
  perform set_config('request.jwt.claims','{}',true);

  perform set_config('request.jwt.claims',jsonb_build_object('sub',v_owner_auth,'role','authenticated')::text,true);
  execute 'set local role authenticated';
  foreach v_gid in array array[
    v_group_status,v_group_material,v_group_sewing,v_group_laundry,v_group_qc,v_group_fg
  ] loop
    v_version:=1;
    v_expected_failure:=false;
    begin
      perform public.erp_assign_pattern_v1(v_gid,v_pattern_a,'downstream/state must block',gen_random_uuid(),v_version);
    exception when sqlstate '23514' then
      if sqlerrm='PATTERN_INITIAL_ASSIGNMENT_REQUIRES_PRISTINE_CUTTING' then
        v_expected_failure:=true;
      else raise;
      end if;
    end;
    if not v_expected_failure then
      raise exception 'Non-pristine/downstream Potongan accepted initial pattern: %',v_gid;
    end if;
  end loop;
  execute 'reset role';
  perform set_config('request.jwt.claims','{}',true);

  update erp.production_patterns set is_active=false where id=v_pattern_b;
  perform set_config('request.jwt.claims',jsonb_build_object('sub',v_owner_auth,'role','authenticated')::text,true);
  execute 'set local role authenticated';
  v_version:=1;
  v_expected_failure:=false;
  begin
    perform public.erp_assign_pattern_v1(v_group_inactive,v_pattern_b,'inactive must fail',gen_random_uuid(),v_version);
  exception when others then
    if sqlerrm like '%Active pattern is required%' or sqlerrm like '%ACTIVE_PATTERN_REQUIRED%' then
      v_expected_failure:=true;
    else raise;
    end if;
  end;
  if not v_expected_failure then raise exception 'Inactive pattern was accepted for first assignment'; end if;
  execute 'reset role';
  perform set_config('request.jwt.claims','{}',true);

  if exists(
    select 1 from erp.cutting_groups
    where id in (
      v_group_unauthorized,v_group_status,v_group_material,v_group_sewing,
      v_group_laundry,v_group_qc,v_group_fg,v_group_inactive
    ) and pattern_id is not null
  ) then raise exception 'A rejected assignment left a pattern residue'; end if;
end
$test$;

rollback;
\echo 'CP4.5 v2.6.17a immutable initial pattern assignment acceptance passed'
