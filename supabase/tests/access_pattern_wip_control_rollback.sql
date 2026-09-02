-- CP4.5 / ERP v2.6.17 access, Pola, WIP, and Final-SKU boundary acceptance.
-- All synthetic state is enclosed by this transaction and rolled back.
\set ON_ERROR_STOP on

begin;
set local timezone='UTC';
set local datestyle='ISO, MDY';
set local lock_timeout='8s';
set local statement_timeout='180s';

\ir cp3_r4_full_schema_seed.sql

do $test$
declare
  v_owner_app constant uuid:='c4500000-0000-4000-8000-000000000001';
  v_owner_auth constant uuid:='c4500000-0000-4000-8000-000000000101';
  v_custom_app constant uuid:='c4500000-0000-4000-8000-000000000002';
  v_custom_auth constant uuid:='c4500000-0000-4000-8000-000000000102';
  v_view_app constant uuid:='c4500000-0000-4000-8000-000000000003';
  v_view_auth constant uuid:='c4500000-0000-4000-8000-000000000103';
  v_inactive_app constant uuid:='c4500000-0000-4000-8000-000000000004';
  v_inactive_auth constant uuid:='c4500000-0000-4000-8000-000000000104';
  v_unmapped_auth constant uuid:='c4500000-0000-4000-8000-000000000105';
  v_req_role constant uuid:='c4510000-0000-4000-8000-000000000001';
  v_req_view constant uuid:='c4510000-0000-4000-8000-000000000002';
  v_custom jsonb;v_custom_replay jsonb;v_view jsonb;v_access jsonb;
  v_custom_role uuid;v_view_role uuid;v_custom_version bigint;v_user_version bigint;
  v_pattern jsonb;v_pattern_replay jsonb;v_pattern_b jsonb;v_pattern_revision jsonb;
  v_pattern_id uuid;v_pattern_b_id uuid;v_pattern_revision_id uuid;
  v_pattern_version bigint;v_group_version bigint;v_assignment jsonb;v_list jsonb;
  v_wip_active jsonb;v_wip_completed jsonb;v_wip_all jsonb;v_wip_before text;v_wip_after text;
  v_flag jsonb;v_flag_id uuid;
  v_brand uuid:='c4520000-0000-4000-8000-000000000001';
  v_product uuid:='c4520000-0000-4000-8000-000000000002';
  v_product_inactive uuid:='c4520000-0000-4000-8000-000000000003';
  v_location uuid:='c4520000-0000-4000-8000-000000000004';
  v_fg_payload jsonb;v_fg jsonb;v_fg_replay jsonb;v_fg_request uuid:='c4530000-0000-4000-8000-000000000001';
  v_qc_item uuid;
  v_vendor uuid:='c4540000-0000-4000-8000-000000000001';
  v_delivery_draft uuid:='c4540000-0000-4000-8000-000000000002';
  v_delivery_sent uuid:='c4540000-0000-4000-8000-000000000003';
  v_delivery_partial uuid:='c4540000-0000-4000-8000-000000000004';
  v_line_partial uuid:='c4540000-0000-4000-8000-000000000005';
  v_receipt uuid:='c4540000-0000-4000-8000-000000000006';
  v_receipt_line uuid:='c4540000-0000-4000-8000-000000000007';
  v_expected_failure boolean;
  v_original_owner_guard text:=md5(pg_get_functiondef('erp.require_owner_admin()'::regprocedure));
begin
  if v_original_owner_guard<>'965de305e5a381cfdf5588f2b9d4babc' then
    raise exception 'Frozen CP4 owner guard changed before CP4.5 acceptance';
  end if;

  insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active)
  select v_owner_app,v_owner_auth,'CP45 Synthetic Owner','OWNER',id,true
  from erp.app_roles where role_code='OWNER';

  perform set_config('request.jwt.claims',jsonb_build_object('sub',v_owner_auth,'role','authenticated')::text,true);
  execute 'set local role authenticated';
  v_access:=public.erp_get_my_access_v1();
  if not coalesce((v_access->>'allowed')::boolean,false)
     or v_access#>>'{profile,role_code}'<>'OWNER'
     or jsonb_array_length(v_access->'permissions')<90 then
    raise exception 'Protected OWNER did not resolve the complete permission bundle: %',v_access;
  end if;

  v_custom:=public.erp_save_role_v1(jsonb_build_object(
    'code','CP45_OPERATIONS','name','CP45 Operations','description','CP45 synthetic custom role',
    'change_reason','CP45 acceptance','confirm_high_risk',true,
    'permission_keys',jsonb_build_array(
      'production.cutting.view','production.wip.view','production.wip.adjust','production.final_sku.view',
      'master.pattern.view','warehouse.stock.view','finance.payroll.approve'
    )
  ),v_req_role,null);
  v_custom_replay:=public.erp_save_role_v1(jsonb_build_object(
    'code','CP45_OPERATIONS','name','CP45 Operations','description','CP45 synthetic custom role',
    'change_reason','CP45 acceptance','confirm_high_risk',true,
    'permission_keys',jsonb_build_array(
      'production.cutting.view','production.wip.view','production.wip.adjust','production.final_sku.view',
      'master.pattern.view','warehouse.stock.view','finance.payroll.approve'
    )
  ),v_req_role,null);
  if v_custom is distinct from v_custom_replay then raise exception 'Role idempotent replay diverged'; end if;
  v_custom_role:=(v_custom->>'role_id')::uuid;

  v_expected_failure:=false;
  begin
    perform public.erp_save_role_v1(jsonb_build_object(
      'code','CP45_OPERATIONS','name','Different payload','change_reason','must conflict',
      'confirm_high_risk',true,'permission_keys',jsonb_build_array('production.wip.view')
    ),v_req_role,null);
  exception when others then
    if sqlerrm like '%request_id%payload%' or sqlerrm like '%different payload%' then v_expected_failure:=true; else raise; end if;
  end;
  if not v_expected_failure then raise exception 'Same role request ID with a different payload was accepted'; end if;

  v_view:=public.erp_save_role_v1(jsonb_build_object(
    'code','CP45_VIEW_ONLY','name','CP45 View Only','description','CP45 synthetic view-only role',
    'change_reason','CP45 acceptance','permission_keys',jsonb_build_array(
      'production.wip.view','master.pattern.view','warehouse.stock.view','finance.payroll.view'
    )
  ),v_req_view,null);
  v_view_role:=(v_view->>'role_id')::uuid;
  execute 'reset role';

  insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active)
  values
    (v_custom_app,v_custom_auth,'CP45 Synthetic Custom','CP45_OPERATIONS',v_custom_role,true),
    (v_view_app,v_view_auth,'CP45 Synthetic View','CP45_VIEW_ONLY',v_view_role,true),
    (v_inactive_app,v_inactive_auth,'CP45 Synthetic Inactive','OWNER',(select id from erp.app_roles where role_code='OWNER'),false);

  -- Granular separation is exercised through the normalized matrix and real
  -- public facades in the continuation below; no test-only function is added.
end
$test$;

-- The main test is split so no test-only helper enters production. Everything
-- below continues inside the same transaction and uses real JWT claims.
do $test$
declare
  v_owner_app constant uuid:='c4500000-0000-4000-8000-000000000001';
  v_owner_auth constant uuid:='c4500000-0000-4000-8000-000000000101';
  v_custom_app constant uuid:='c4500000-0000-4000-8000-000000000002';
  v_custom_auth constant uuid:='c4500000-0000-4000-8000-000000000102';
  v_view_app constant uuid:='c4500000-0000-4000-8000-000000000003';
  v_view_auth constant uuid:='c4500000-0000-4000-8000-000000000103';
  v_inactive_auth constant uuid:='c4500000-0000-4000-8000-000000000104';
  v_unmapped_auth constant uuid:='c4500000-0000-4000-8000-000000000105';
  v_custom_role uuid:=(select id from erp.app_roles where role_code='CP45_OPERATIONS');
  v_view_role uuid:=(select id from erp.app_roles where role_code='CP45_VIEW_ONLY');
  v_access jsonb;v_response jsonb;v_expected_failure boolean;v_version bigint;v_user_version bigint;
  v_pattern jsonb;v_pattern_replay jsonb;v_pattern_b jsonb;v_pattern_revision jsonb;
  v_pattern_id uuid;v_pattern_b_id uuid;v_pattern_revision_id uuid;
  v_pattern_version bigint;v_group_version bigint;v_assignment jsonb;v_list jsonb;
  v_wip_active jsonb;v_wip_completed jsonb;v_wip_all jsonb;v_wip_before text;v_wip_after text;
  v_flag jsonb;v_flag_id uuid;
  v_brand uuid:='c4520000-0000-4000-8000-000000000001';
  v_product uuid:='c4520000-0000-4000-8000-000000000002';
  v_product_inactive uuid:='c4520000-0000-4000-8000-000000000003';
  v_location uuid:='c4520000-0000-4000-8000-000000000004';
  v_fg_payload jsonb;v_fg jsonb;v_fg_replay jsonb;v_fg_request uuid:='c4530000-0000-4000-8000-000000000001';
  v_qc_item uuid;
  v_vendor uuid:='c4540000-0000-4000-8000-000000000001';
  v_delivery_draft uuid:='c4540000-0000-4000-8000-000000000002';
  v_delivery_sent uuid:='c4540000-0000-4000-8000-000000000003';
  v_delivery_partial uuid:='c4540000-0000-4000-8000-000000000004';
  v_line_partial uuid:='c4540000-0000-4000-8000-000000000005';
  v_receipt uuid:='c4540000-0000-4000-8000-000000000006';
  v_receipt_line uuid:='c4540000-0000-4000-8000-000000000007';
begin
  if v_custom_role is null or v_view_role is null then raise exception 'Synthetic role setup did not persist inside transaction'; end if;

  if not exists(select 1 from erp.app_role_permissions where role_id=v_custom_role and permission_key='finance.payroll.approve')
     or exists(select 1 from erp.app_role_permissions where role_id=v_custom_role and permission_key='finance.payroll.pay')
     or exists(select 1 from erp.app_role_permissions where role_id=v_custom_role and permission_key='warehouse.stock.adjust')
     or exists(select 1 from erp.app_role_permissions where role_id=v_custom_role and permission_key='production.wip.reverse')
     or exists(select 1 from erp.app_role_permissions where role_id=v_custom_role and permission_key='master.pattern.manage')
     or exists(select 1 from erp.app_role_permissions where role_id=v_view_role and permission_key not like '%.view') then
    raise exception 'Granular custom/view-only role separation failed';
  end if;

  perform set_config('request.jwt.claims',jsonb_build_object('sub',v_custom_auth,'role','authenticated')::text,true);
  execute 'set local role authenticated';
  v_access:=public.erp_get_my_access_v1();
  if not (v_access->>'allowed')::boolean
     or not (v_access->'permissions' ? 'production.cutting.view')
     or not (v_access->'permissions' ? 'production.wip.view')
     or (v_access->'permissions' ? 'production.wip.reverse') then
    raise exception 'Custom multi-module bundle mismatch: %',v_access;
  end if;
  perform public.erp_get_wip_control_v1();
  v_expected_failure:=false;
  begin perform public.erp_save_pattern_v1(
    jsonb_build_object('code','DENIED','name','Denied','sort_order',1,'change_reason','denied'),gen_random_uuid(),null
  ); exception when sqlstate '42501' then v_expected_failure:=true; end;
  if not v_expected_failure then raise exception 'WIP access incorrectly implied Master Pola management'; end if;
  execute 'reset role';

  perform set_config('request.jwt.claims',jsonb_build_object('sub',v_view_auth,'role','authenticated')::text,true);
  execute 'set local role authenticated';
  perform public.erp_get_wip_control_v1();
  v_expected_failure:=false;
  begin perform public.erp_set_wip_control_flag_v1(
    jsonb_build_object('cutting_group_id','a3200000-0000-0000-0000-000000000001','flag_type','OPERATOR_ACTION','note','denied','change_reason','denied'),
    gen_random_uuid(),null
  ); exception when sqlstate '42501' then v_expected_failure:=true; end;
  if not v_expected_failure then raise exception 'View-only role changed WIP'; end if;
  execute 'reset role';

  perform set_config('request.jwt.claims',jsonb_build_object('sub',v_inactive_auth,'role','authenticated')::text,true);
  execute 'set local role authenticated';
  v_access:=public.erp_get_my_access_v1();
  if (v_access->>'allowed')::boolean or v_access->>'reason'<>'APP_USER_INACTIVE' then raise exception 'Inactive user did not fail closed: %',v_access; end if;
  execute 'reset role';

  perform set_config('request.jwt.claims',jsonb_build_object('sub',v_unmapped_auth,'role','authenticated')::text,true);
  execute 'set local role authenticated';
  v_access:=public.erp_get_my_access_v1();
  if (v_access->>'allowed')::boolean or v_access->>'reason'<>'APP_USER_NOT_FOUND' then raise exception 'Unmapped user did not fail closed: %',v_access; end if;
  execute 'reset role';

  perform set_config('request.jwt.claims','{"role":"anon"}',true);
  execute 'set local role anon';
  v_expected_failure:=false;
  begin perform public.erp_get_my_access_v1(); exception when sqlstate '42501' then v_expected_failure:=true; end;
  if not v_expected_failure then raise exception 'Anonymous caller executed access facade'; end if;
  execute 'reset role';

  -- OWNER updates the custom role; stale writers lose, and revocation is read
  -- on the very next server request rather than trusted from an old JWT.
  select row_version into v_version from erp.app_roles where id=v_custom_role;
  perform set_config('request.jwt.claims',jsonb_build_object('sub',v_owner_auth,'role','authenticated')::text,true);
  execute 'set local role authenticated';
  v_response:=public.erp_save_role_v1(jsonb_build_object(
    'id',v_custom_role,'code','CP45_OPERATIONS','name','CP45 Operations','description','revoked WIP view',
    'change_reason','next-request revocation','permission_keys',jsonb_build_array('master.pattern.view','warehouse.stock.view')
  ),gen_random_uuid(),v_version);
  v_expected_failure:=false;
  begin perform public.erp_save_role_v1(jsonb_build_object(
    'id',v_custom_role,'code','CP45_OPERATIONS','name','stale writer','change_reason','stale',
    'permission_keys',jsonb_build_array('production.wip.view')
  ),gen_random_uuid(),v_version); exception when others then
    if sqlerrm like 'STALE_VERSION%' then v_expected_failure:=true; else raise; end if;
  end;
  if not v_expected_failure then raise exception 'Concurrent stale role update was accepted'; end if;
  execute 'reset role';

  perform set_config('request.jwt.claims',jsonb_build_object('sub',v_custom_auth,'role','authenticated')::text,true);
  execute 'set local role authenticated';
  v_expected_failure:=false;
  begin perform public.erp_get_wip_control_v1(); exception when sqlstate '42501' then v_expected_failure:=true; end;
  if not v_expected_failure then raise exception 'Revoked WIP permission remained usable on next request'; end if;
  execute 'reset role';

  -- Assignment is row-version protected and cannot demote the last OWNER.
  select row_version into v_user_version from erp.app_users where id=v_custom_app;
  perform set_config('request.jwt.claims',jsonb_build_object('sub',v_owner_auth,'role','authenticated')::text,true);
  execute 'set local role authenticated';
  v_response:=public.erp_save_app_user_v3(jsonb_build_object(
    'id',v_custom_app,'full_name','CP45 Synthetic Custom','role_id',v_view_role,
    'is_active',true,'change_reason','assignment acceptance'
  ),gen_random_uuid(),v_user_version);
  v_expected_failure:=false;
  begin perform public.erp_save_app_user_v3(jsonb_build_object(
    'id',v_custom_app,'full_name','CP45 Synthetic Custom','role_id',v_custom_role,
    'is_active',true,'change_reason','stale assignment'
  ),gen_random_uuid(),v_user_version); exception when others then
    if sqlerrm like 'STALE_VERSION%' then v_expected_failure:=true; else raise; end if;
  end;
  if not v_expected_failure then raise exception 'Stale user assignment was accepted'; end if;

  execute 'reset role';
  select row_version into v_user_version from erp.app_users where id=v_owner_app;
  execute 'set local role authenticated';
  v_expected_failure:=false;
  begin perform public.erp_save_app_user_v3(jsonb_build_object(
    'id',v_owner_app,'full_name','CP45 Synthetic Owner','role_code','ADMIN',
    'is_active',true,'change_reason','must protect last owner'
  ),gen_random_uuid(),v_user_version); exception when sqlstate '42501' then
    if sqlerrm='LAST_ACTIVE_OWNER_PROTECTED' then v_expected_failure:=true; else raise; end if;
  end;
  if not v_expected_failure then raise exception 'Last active OWNER was demoted'; end if;
  v_expected_failure:=false;
  begin perform public.erp_save_app_user_v3(jsonb_build_object(
    'id',v_owner_app,'full_name','CP45 Synthetic Owner','role_code','OWNER',
    'is_active',false,'change_reason','must protect last owner deactivation'
  ),gen_random_uuid(),v_user_version); exception when sqlstate '42501' then
    if sqlerrm='LAST_ACTIVE_OWNER_PROTECTED' then v_expected_failure:=true; else raise; end if;
  end;
  if not v_expected_failure then raise exception 'Last active OWNER was deactivated'; end if;
  v_expected_failure:=false;
  begin perform public.erp_save_app_user_v3(jsonb_build_object(
    'id',v_owner_app,'auth_user_id',null,'full_name','CP45 Synthetic Owner','role_code','OWNER',
    'is_active',true,'change_reason','must protect last owner unmap'
  ),gen_random_uuid(),v_user_version); exception when sqlstate '42501' then
    if sqlerrm='LAST_ACTIVE_OWNER_PROTECTED' then v_expected_failure:=true; else raise; end if;
  end;
  if not v_expected_failure then raise exception 'Last active OWNER was unmapped'; end if;
  execute 'reset role';
  v_expected_failure:=false;
  begin delete from erp.app_users where id=v_owner_app; exception when sqlstate '42501' then
    if sqlerrm='LAST_ACTIVE_OWNER_PROTECTED' then v_expected_failure:=true; else raise; end if;
  end;
  if not v_expected_failure then raise exception 'Last active OWNER row was deleted'; end if;

  -- Grandfathered rows remain readable, but the first JWT-backed application
  -- update must bind a canonical pattern identity. Exercise the table trigger
  -- directly as postgres while preserving the real authenticated JWT claims.
  v_expected_failure:=false;
  begin
    update erp.cutting_groups set updated_at=updated_at
    where id='a3200000-0000-0000-0000-000000000002';
  exception when sqlstate '23502' then
    if sqlerrm='PATTERN_ID_REQUIRED_FOR_CUTTING_TRANSACTION' then v_expected_failure:=true; else raise; end if;
  end;
  if not v_expected_failure then raise exception 'JWT-backed Potongan update accepted a null pattern_id'; end if;

  -- Master Pola starts empty and grows only when business work needs it.
  -- Identity/revision, idempotency, snapshots, deactivation, and deterministic
  -- browse order are all enforced by the same source of truth.
  v_list:=public.erp_list_patterns_v1('ALL',null,100,0);
  if (v_list->>'total')::bigint<>0 or jsonb_array_length(v_list->'rows')<>0 then
    raise exception 'Master Pola did not support an empty operational start: %',v_list;
  end if;
  v_pattern:=public.erp_save_pattern_v1(jsonb_build_object(
    'code','A-LURUS','revision','R1','name','Pola Lurus','sort_order',20,'change_reason','CP45 create'
  ),'c4550000-0000-4000-8000-000000000001',null);
  v_pattern_replay:=public.erp_save_pattern_v1(jsonb_build_object(
    'code','A-LURUS','revision','R1','name','Pola Lurus','sort_order',20,'change_reason','CP45 create'
  ),'c4550000-0000-4000-8000-000000000001',null);
  if v_pattern is distinct from v_pattern_replay then raise exception 'Pattern idempotent replay diverged'; end if;
  v_pattern_id:=(v_pattern->>'pattern_id')::uuid;

  v_expected_failure:=false;
  begin perform public.erp_save_pattern_v1(jsonb_build_object(
    'code','A-LURUS','revision','R1','name','different','sort_order',20,'change_reason','conflict'
  ),'c4550000-0000-4000-8000-000000000001',null); exception when others then
    if sqlerrm like '%request_id%payload%' or sqlerrm like '%different payload%' then v_expected_failure:=true; else raise; end if;
  end;
  if not v_expected_failure then raise exception 'Pattern request ID payload mismatch was accepted'; end if;

  foreach v_response in array array[
    jsonb_build_object('code','','name','Blank','sort_order',1,'change_reason','invalid'),
    jsonb_build_object('code','BAD','name','','sort_order',1,'change_reason','invalid'),
    jsonb_build_object('code','BAD','revision','!','name','Bad revision','sort_order',1,'change_reason','invalid'),
    jsonb_build_object('code','BAD','name','Bad sort','sort_order',-1,'change_reason','invalid')
  ] loop
    v_expected_failure:=false;
    begin perform public.erp_save_pattern_v1(v_response,gen_random_uuid(),null); exception when others then v_expected_failure:=true; end;
    if not v_expected_failure then raise exception 'Invalid pattern payload was accepted: %',v_response; end if;
  end loop;

  v_expected_failure:=false;
  begin perform public.erp_save_pattern_v1(jsonb_build_object(
    'code','A-LURUS','revision','R1','name','Duplicate Code','sort_order',21,'change_reason','duplicate'
  ),gen_random_uuid(),null); exception when unique_violation then v_expected_failure:=true; end;
  if not v_expected_failure then raise exception 'Duplicate active pattern code/revision was accepted'; end if;

  v_expected_failure:=false;
  begin perform public.erp_save_pattern_v1(jsonb_build_object(
    'code','OTHER','revision','R1','name','Pola Lurus','sort_order',21,'change_reason','duplicate name/revision'
  ),gen_random_uuid(),null); exception when unique_violation then v_expected_failure:=true; end;
  if not v_expected_failure then raise exception 'Duplicate active pattern name/revision was accepted'; end if;

  v_pattern_revision:=public.erp_save_pattern_v1(jsonb_build_object(
    'code','A-LURUS','revision','R2','name','Pola Lurus R2','sort_order',21,
    'change_reason','New physical pattern revision'
  ),gen_random_uuid(),null);
  v_pattern_revision_id:=(v_pattern_revision->>'pattern_id')::uuid;

  v_pattern_b:=public.erp_save_pattern_v1(jsonb_build_object(
    'code','B-REG','revision','R1','name','Pola Regular','sort_order',20,'change_reason','tie sort'
  ),gen_random_uuid(),null);
  v_pattern_b_id:=(v_pattern_b->>'pattern_id')::uuid;
  v_pattern_version:=(v_pattern->>'row_version')::bigint;
  v_pattern:=public.erp_save_pattern_v1(jsonb_build_object(
    'id',v_pattern_id,'code','A-LURUS','revision','R1','name','Pola Lurus Revisi','sort_order',20,'change_reason','edit'
  ),gen_random_uuid(),v_pattern_version);
  v_expected_failure:=false;
  begin perform public.erp_save_pattern_v1(jsonb_build_object(
    'id',v_pattern_id,'code','A-LURUS','revision','R1','name','Stale','sort_order',20,'change_reason','stale'
  ),gen_random_uuid(),v_pattern_version); exception when others then
    if sqlerrm like 'STALE_VERSION%' then v_expected_failure:=true; else raise; end if;
  end;
  if not v_expected_failure then raise exception 'Stale pattern edit was accepted'; end if;

  v_list:=public.erp_list_patterns_v1('ACTIVE',null,100,0);
  if v_list#>>'{rows,0,code}'<>'A-LURUS' or v_list#>>'{rows,0,revision}'<>'R1'
     or v_list#>>'{rows,1,code}'<>'B-REG' or v_list#>>'{rows,2,revision}'<>'R2' then
    raise exception 'Pattern tie sorting is not deterministic: %',v_list;
  end if;
  select row_version into v_group_version from erp.cutting_groups where id='a3200000-0000-0000-0000-000000000001';
  v_assignment:=public.erp_assign_pattern_v1(
    'a3200000-0000-0000-0000-000000000001',v_pattern_id,'CP45 assignment',gen_random_uuid(),v_group_version
  );
  if not exists(
    select 1 from erp.cutting_groups
    where id='a3200000-0000-0000-0000-000000000001'
      and pattern_id=v_pattern_id and pattern_code_snapshot='A-LURUS'
      and pattern_revision_snapshot='R1' and pattern_name_snapshot='Pola Lurus Revisi'
  ) then raise exception 'Pattern identity/revision snapshot was not bound to Potongan'; end if;

  v_pattern:=public.erp_save_pattern_v1(jsonb_build_object(
    'id',v_pattern_id,'code','A-LURUS','revision','R1','name','Master Renamed Later',
    'sort_order',30,'change_reason','Prove historical snapshot isolation'
  ),gen_random_uuid(),(v_pattern->>'row_version')::bigint);
  if not exists(
    select 1 from erp.cutting_groups
    where id='a3200000-0000-0000-0000-000000000001'
      and pattern_name_snapshot='Pola Lurus Revisi' and pattern_revision_snapshot='R1'
  ) then raise exception 'Master edit rewrote a historical Potongan snapshot'; end if;
  v_expected_failure:=false;
  begin
    update erp.cutting_groups set pattern_revision_snapshot='TAMPERED'
    where id='a3200000-0000-0000-0000-000000000001';
  exception when sqlstate '42501' then v_expected_failure:=true; end;
  if not v_expected_failure then raise exception 'Historical pattern snapshot accepted direct mutation'; end if;

  v_pattern:=public.erp_deactivate_pattern_v1(
    v_pattern_id,'CP45 history-preserving deactivate',gen_random_uuid(),(v_pattern->>'row_version')::bigint
  );
  if not exists(select 1 from erp.cutting_groups where id='a3200000-0000-0000-0000-000000000001' and pattern_id=v_pattern_id)
     or not exists(select 1 from erp.production_patterns where id=v_pattern_id and not is_active) then
    raise exception 'Used pattern history was deleted or detached during deactivate';
  end if;
  v_expected_failure:=false;
  begin perform public.erp_save_pattern_v1(jsonb_build_object(
    'code','A-LURUS','revision','R1','name','Identity reuse forbidden','sort_order',40,
    'change_reason','must preserve stable historical identity'
  ),gen_random_uuid(),null); exception when unique_violation then v_expected_failure:=true; end;
  if not v_expected_failure then raise exception 'Inactive historical code/revision identity was reused'; end if;
  v_list:=public.erp_list_patterns_v1('ALL','A-LURUS R1',100,0);
  if not exists(select 1 from jsonb_array_elements(v_list->'rows') r
    where r->>'id'=v_pattern_id::text and r->>'is_active'='false') then
    raise exception 'Inactive used pattern disappeared from browse/history: %',v_list;
  end if;
  select row_version into v_group_version from erp.cutting_groups where id='a3200000-0000-0000-0000-000000000002';
  v_expected_failure:=false;
  begin perform public.erp_assign_pattern_v1(
    'a3200000-0000-0000-0000-000000000002',v_pattern_id,'inactive must fail',gen_random_uuid(),v_group_version
  ); exception when others then
    if sqlerrm like '%Active pattern is required%' or sqlerrm like '%ACTIVE_PATTERN_REQUIRED%' then v_expected_failure:=true; else raise; end if;
  end;
  if not v_expected_failure then raise exception 'Inactive pattern was selected for new work'; end if;
  if not exists(select 1 from erp.cutting_groups where id='a3200000-0000-0000-0000-000000000002' and pattern_id is null) then
    raise exception 'Grandfathered pre-CP4.5 Potongan history stopped being readable';
  end if;
  v_expected_failure:=false;
  begin perform public.erp_assign_pattern_v1(
    'a3200000-0000-0000-0000-000000000002',null,'canonical unassign must fail',gen_random_uuid(),v_group_version
  ); exception when sqlstate '23502' then
    if sqlerrm='PATTERN_ID_REQUIRED_FOR_CUTTING_TRANSACTION' then v_expected_failure:=true; else raise; end if;
  end;
  if not v_expected_failure then raise exception 'Canonical Potongan write accepted a null pattern_id'; end if;

  -- Final SKU mutates group 3 through an authenticated application request;
  -- bind its canonical pattern first so the transaction-level requirement is
  -- exercised rather than bypassed by the SQL fixture seed.
  select row_version into v_group_version from erp.cutting_groups where id='a3200000-0000-0000-0000-000000000003';
  perform public.erp_assign_pattern_v1(
    'a3200000-0000-0000-0000-000000000003',v_pattern_b_id,'Required pattern before Final SKU',gen_random_uuid(),v_group_version
  );

  -- The partial-Laundry fixture is also an application lifecycle write. Bind
  -- the same active canonical pattern before posting it; do not weaken the
  -- transaction guard merely to accommodate a direct SQL seed.
  select row_version into v_group_version from erp.cutting_groups where id='a3200000-0000-0000-0000-000000000006';
  perform public.erp_assign_pattern_v1(
    'a3200000-0000-0000-0000-000000000006',v_pattern_b_id,'Required pattern before Laundry lifecycle',gen_random_uuid(),v_group_version
  );

  -- Laundry facts cover draft, in-transit, partial, Stuck, and Missing without
  -- introducing brand anywhere before Final SKU.
  insert into erp.laundry_vendors(id,vendor_code,vendor_name)
  values(v_vendor,'CP45-LAUNDRY','CP45 Laundry');
  insert into erp.laundry_deliveries(id,delivery_number,po_id,vendor_id,target_dyeing_color,physical_at,status)
  values
    (v_delivery_draft,'CP45-DRAFT','a3000000-0000-0000-0000-000000000002',v_vendor,'N/A','2026-01-02 08:00+00','DRAFT'),
    (v_delivery_sent,'CP45-SENT','a3000000-0000-0000-0000-000000000001',v_vendor,'N/A','2026-01-02 09:00+00','DRAFT'),
    (v_delivery_partial,'CP45-PARTIAL','a3000000-0000-0000-0000-000000000006',v_vendor,'N/A','2026-04-02 09:00+00','DRAFT');
  insert into erp.laundry_delivery_lines(id,delivery_id,cutting_group_id,qty_sent_pcs)
  values
    ('c4540000-0000-4000-8000-000000000011',v_delivery_draft,'a3200000-0000-0000-0000-000000000002',10),
    ('c4540000-0000-4000-8000-000000000012',v_delivery_sent,'a3200000-0000-0000-0000-000000000001',20),
    (v_line_partial,v_delivery_partial,'a3200000-0000-0000-0000-000000000006',5);
  perform erp.post_laundry_delivery(v_delivery_sent);
  perform erp.post_laundry_delivery(v_delivery_partial);
  insert into erp.laundry_receipts(id,receipt_number,delivery_id,physical_at,status)
  values(v_receipt,'CP45-RECEIPT',v_delivery_partial,'2026-04-03 09:00+00','DRAFT');
  insert into erp.laundry_receipt_lines(
    id,receipt_id,delivery_line_id,qty_good_received,qty_bs_laundry,qty_stuck,qty_missing
  ) values(v_receipt_line,v_receipt,v_line_partial,2,0,1,1);
  perform erp.post_laundry_receipt_v2(v_receipt,gen_random_uuid(),1,'CP45 partial/Stuck/Missing fixture');

  v_flag:=public.erp_set_wip_control_flag_v1(jsonb_build_object(
    'cutting_group_id','a3200000-0000-0000-0000-000000000004',
    'flag_type','PENDING_CORRECTION','status','OPEN','note','CP45 pending correction',
    'change_reason','CP45 WIP acceptance'
  ),gen_random_uuid(),null);
  v_flag_id:=(v_flag->>'flag_id')::uuid;

  -- Final SKU is the first binding brand boundary. Two products prove that the
  -- posted product snapshot cannot be silently changed afterward.
  insert into erp.brands(id,brand_code,brand_name)
  values('c4520000-0000-4000-8000-000000000001','CP45-BRAND','CP45 Binding Brand');
  insert into erp.products(
    id,sku,model_id,brand_id,color_name,size_id,product_name,identity_root_id,effective_from,is_active
  ) values
    ('c4520000-0000-4000-8000-000000000002','CP45-SKU-A','a2000000-0000-0000-0000-000000000001',
     'c4520000-0000-4000-8000-000000000001','N/A','a2100000-0000-0000-0000-000000000001','CP45 Final SKU A',
     'c4520000-0000-4000-8000-000000000002','2025-01-01 00:00+00',true),
    ('c4520000-0000-4000-8000-000000000003','CP45-SKU-INACTIVE','a2000000-0000-0000-0000-000000000001',
     'c4520000-0000-4000-8000-000000000001','CP45-INACTIVE','a2100000-0000-0000-0000-000000000001','CP45 Final SKU Inactive',
     'c4520000-0000-4000-8000-000000000003','2025-01-01 00:00+00',false);
  insert into erp.accessory_bom_versions(product_id,version_label,effective_from,is_active,notes)
  values('c4520000-0000-4000-8000-000000000002','CP45-NO-ACCESSORY','2025-01-01 00:00+00',true,'Explicit empty CP45 test BOM');
  insert into erp.locations(id,location_code,location_name,location_type)
  values('c4520000-0000-4000-8000-000000000004','CP45-FG','CP45 FG','FG_WAREHOUSE');

  foreach v_response in array array[
    jsonb_build_object('good_qty_pcs',99,'lines',jsonb_build_array(jsonb_build_object('final_product_id',v_product,'qty_good_pcs',100,'qty_bs_pcs',0))),
    jsonb_build_object('good_qty_pcs',101,'lines',jsonb_build_array(jsonb_build_object('final_product_id',v_product,'qty_good_pcs',100,'qty_bs_pcs',0))),
    jsonb_build_object('good_qty_pcs',100,'lines',jsonb_build_array(jsonb_build_object('final_product_id',v_product,'qty_good_pcs',100,'qty_bs_pcs',-1))),
    jsonb_build_object('good_qty_pcs',1,'lines',jsonb_build_array(jsonb_build_object('qty_good_pcs',1,'qty_bs_pcs',0))),
    jsonb_build_object('good_qty_pcs',1,'lines',jsonb_build_array(jsonb_build_object('final_product_id',v_product_inactive,'qty_good_pcs',1,'qty_bs_pcs',0)))
  ] loop
    v_expected_failure:=false;
    begin perform public.erp_post_final_sku_allocation_v1(
      v_response||jsonb_build_object(
        'cutting_group_id','a3200000-0000-0000-0000-000000000003',
        'destination_location_id',v_location,'physical_at','2026-01-03 10:00:00+00','reason','CP45 invalid boundary'
      ),gen_random_uuid(),(select row_version from erp.cutting_groups where id='a3200000-0000-0000-0000-000000000003')
    ); exception when others then v_expected_failure:=true; end;
    if not v_expected_failure then raise exception 'Invalid Final SKU allocation was accepted: %',v_response; end if;
  end loop;

  v_fg_payload:=jsonb_build_object(
    'cutting_group_id','a3200000-0000-0000-0000-000000000003',
    'destination_location_id',v_location,'physical_at','2026-01-03 10:00:00+00',
    'reason','CP45 exact Final SKU allocation','completion_mode','ALL_READY','good_qty_pcs',100,
    'lines',jsonb_build_array(jsonb_build_object(
      'final_product_id',v_product,'qty_good_pcs',100,'qty_bs_pcs',0,'notes','CP45 exact'
    ))
  );
  v_fg:=public.erp_post_final_sku_allocation_v1(
    v_fg_payload,v_fg_request,(select row_version from erp.cutting_groups where id='a3200000-0000-0000-0000-000000000003')
  );
  v_fg_replay:=public.erp_post_final_sku_allocation_v1(v_fg_payload,v_fg_request,1);
  if v_fg is distinct from v_fg_replay then raise exception 'Final SKU double-click produced a second effect'; end if;
  if (select coalesce(sum(qty_signed),0) from erp.fg_stock_movements
      where source_id in(select id from erp.qc_inspection_items
        where cutting_group_id='a3200000-0000-0000-0000-000000000003'))<>100 then
    raise exception 'Exact Final SKU post did not create exactly 100 Good stock pieces';
  end if;
  select qi.id into v_qc_item from erp.qc_inspection_items qi
  where qi.cutting_group_id='a3200000-0000-0000-0000-000000000003' limit 1;
  v_expected_failure:=false;
  begin update erp.qc_inspection_items set final_product_id=v_product_inactive where id=v_qc_item;
  exception when others then v_expected_failure:=true; end;
  if not v_expected_failure then raise exception 'Posted Final SKU/product snapshot was silently edited'; end if;

  -- Authoritative WIP cases and filters. Group S is terminal/no-action;
  -- groups A/B/D/E independently expose unfinished, unsent, draft/transit,
  -- partial/Stuck/Missing, and explicit correction blockers.
  if (select control_status from erp.v_wip_control_status_v1 where cutting_group_id='a3200000-0000-0000-0000-000000000003')<>'COMPLETED' then
    raise exception 'Terminal/no-action WIP was not Completed';
  end if;
  if not (select unfinished_sewing_qty_pcs>0 from erp.v_wip_control_status_v1 where cutting_group_id='a3200000-0000-0000-0000-000000000001')
     or not (select laundry_in_transit_qty_pcs>0 from erp.v_wip_control_status_v1 where cutting_group_id='a3200000-0000-0000-0000-000000000001')
     or not (select laundry_draft_qty_pcs>0 from erp.v_wip_control_status_v1 where cutting_group_id='a3200000-0000-0000-0000-000000000002')
     or not (select unsent_ready_qty_pcs>0 from erp.v_wip_control_status_v1 where cutting_group_id='a3200000-0000-0000-0000-000000000004')
     or not (select open_flag_count>0 from erp.v_wip_control_status_v1 where cutting_group_id='a3200000-0000-0000-0000-000000000004')
     or not (select laundry_in_transit_qty_pcs>0 and unresolved_laundry_issue_qty_pcs=2
             from erp.v_wip_control_status_v1 where cutting_group_id='a3200000-0000-0000-0000-000000000006') then
    raise exception 'One or more authoritative Active WIP blockers were not represented';
  end if;
  if exists(select 1 from erp.v_wip_control_status_v1 where cutting_group_id in(
    'a3200000-0000-0000-0000-000000000001','a3200000-0000-0000-0000-000000000002',
    'a3200000-0000-0000-0000-000000000004','a3200000-0000-0000-0000-000000000006'
  ) and control_status<>'ACTIVE') then raise exception 'Open child quantity was hidden as Completed'; end if;

  select md5(coalesce(string_agg(format('%s:%s',id,row_version),',' order by id),'')) into v_wip_before from erp.cutting_groups;
  v_wip_active:=public.erp_get_wip_control_v1();
  v_wip_completed:=public.erp_get_wip_control_v1('COMPLETED',null,'PRODUCTION',null);
  v_wip_all:=public.erp_get_wip_control_v1('ALL',null,'UPDATED',null);
  select md5(coalesce(string_agg(format('%s:%s',id,row_version),',' order by id),'')) into v_wip_after from erp.cutting_groups;
  if v_wip_active->>'filter'<>'ACTIVE'
     or exists(select 1 from jsonb_array_elements(v_wip_active->'rows') r where r->>'control_status'<>'ACTIVE')
     or not exists(select 1 from jsonb_array_elements(v_wip_completed->'rows') r where r->>'cutting_group_id'='a3200000-0000-0000-0000-000000000003')
     or jsonb_array_length(v_wip_all->'rows')<>jsonb_array_length(v_wip_active->'rows')+jsonb_array_length(v_wip_completed->'rows')
     or v_wip_before is distinct from v_wip_after then
    raise exception 'WIP filter default/Completed/All contract failed or mutated state';
  end if;

  -- Resolve flag with row version; the remaining unsent quantity keeps the
  -- group Active, proving status is derived from all blockers, not one toggle.
  perform public.erp_set_wip_control_flag_v1(jsonb_build_object(
    'id',v_flag_id,'status','RESOLVED','note','CP45 resolved','change_reason','CP45 resolve acceptance'
  ),gen_random_uuid(),(v_flag->>'row_version')::bigint);
  if (select control_status from erp.v_wip_control_status_v1 where cutting_group_id='a3200000-0000-0000-0000-000000000004')<>'ACTIVE' then
    raise exception 'Resolving one flag hid other WIP work';
  end if;
  execute 'reset role';

  -- Static ownership/ACL boundary complements hosted HTTP/JWT proof.
  if has_function_privilege('public','erp.has_permission(text)','EXECUTE')
     or has_function_privilege('anon','erp.has_permission(text)','EXECUTE')
     or has_function_privilege('authenticated','erp.has_permission(text)','EXECUTE')
     or has_function_privilege('authenticated','erp.save_app_user_v2(jsonb,uuid,bigint)','EXECUTE')
     or has_function_privilege('authenticated','erp.guard_pattern_assignment_snapshot()','EXECUTE')
     or has_function_privilege('service_role','erp.guard_pattern_assignment_snapshot()','EXECUTE')
     or has_function_privilege('authenticated','erp.require_pattern_identity_on_app_write()','EXECUTE')
     or has_function_privilege('service_role','erp.require_pattern_identity_on_app_write()','EXECUTE')
     or has_table_privilege('authenticated','erp.app_roles','SELECT')
     or has_table_privilege('authenticated','erp.production_patterns','INSERT')
     or to_regprocedure('erp.guard_last_owner_auth_delete()') is null
     or not exists(select 1 from pg_trigger where tgrelid='auth.users'::regclass and tgname='trg_cp45_guard_last_owner_auth_delete' and not tgisinternal)
     or not exists(select 1 from pg_trigger where tgrelid='erp.cutting_groups'::regclass and tgname='trg_05_pattern_assignment_snapshot' and not tgisinternal)
     or not exists(select 1 from pg_trigger where tgrelid='erp.cutting_groups'::regclass and tgname='trg_06_require_pattern_identity' and not tgisinternal)
     or md5(pg_get_functiondef('erp.require_owner_admin()'::regprocedure))<>'965de305e5a381cfdf5588f2b9d4babc'
     or exists(select 1 from information_schema.columns where table_schema='erp'
       and table_name in('production_orders','cutting_groups','sewing_terminal_events','laundry_deliveries','laundry_receipts')
       and column_name='brand_id') then
    raise exception 'Private ACL, CP4 owner guard, or pre-Final-SKU brand boundary regressed';
  end if;

  raise notice 'CP4.5 access/Pola/WIP/Final-SKU acceptance PASS';
end
$test$;

rollback;
