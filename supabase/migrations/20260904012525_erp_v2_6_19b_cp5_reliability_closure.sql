begin;
set local lock_timeout='10s';
set local statement_timeout='180s';

do $guard$
declare
  r record;
  v_actual text;
  v_claim_constraint text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.19a') then
    raise exception 'ERP v2.6.19b requires recorded v2.6.19a first';
  end if;
  if exists(select 1 from erp.schema_migrations where version='v2.6.19b') then
    raise exception 'ERP v2.6.19b is already recorded; never replay or edit a recorded migration';
  end if;
  if to_regclass('erp.bs_resolution_v2619b_rollback_capsule') is not null
     or to_regprocedure('erp.set_rework_accessory_selection_basis_v2619b()') is not null
     or to_regprocedure('erp.guard_laundry_claim_delivery_source_v2619b()') is not null
     or to_regprocedure('erp.guard_laundry_claim_receipt_source_v2619b()') is not null
     or exists(
       select 1 from information_schema.columns
       where table_schema='erp' and table_name='rework_accessory_selection_lines'
         and column_name='selection_basis'
     ) then
    raise exception 'ERP v2.6.19b target guard: prior reliability-closure residue exists';
  end if;
  if exists(select 1 from erp.rework_accessory_selection_lines) then
    raise exception 'ERP v2.6.19b is a pre-use correction and refuses ambiguous accessory selections';
  end if;
  if exists(select 1 from erp.laundry_claims where claim_type='OTHER') then
    raise exception 'ERP v2.6.19b refuses existing OTHER claims; classify/correct them explicitly first';
  end if;

  select pg_get_constraintdef(oid) into v_claim_constraint
  from pg_constraint
  where conrelid='erp.laundry_claims'::regclass
    and conname='laundry_claims_claim_type_check';
  if v_claim_constraint is null or v_claim_constraint not like '%OTHER%' then
    raise exception 'ERP v2.6.19b target guard: expected pre-change claim constraint is absent';
  end if;

  for r in
    select * from (values
      ('erp.validate_laundry_claim_lineage()','8b4ade21137b5bc114da6ad650f25b5c'),
      ('erp.guard_laundry_claim_capacity_on_resolution()','2aacb3e2cbe905d9597490e52bdfd015'),
      ('erp.guard_laundry_receipt_source_capacity_on_post()','9c94ed5563fde67510edd4dfc53de098'),
      ('erp.save_laundry_claim_v2(jsonb,uuid,bigint)','3ce81f61adc7d56c5bd9d048dafda180'),
      ('erp.bs_accessory_bom_options_v1(uuid,timestamp with time zone)','37e457371ae8217ff5be098721f32acb'),
      ('erp.get_rework_accessory_decision_v1(uuid)','a81f8fedbc35f5566ea027bcbb4a4769'),
      ('public.erp_get_bs_resolution_workspace_v1(text,text,uuid,text,integer,integer)','0316fd7f5e2e3d0347fa1924c599a66c')
    ) expected(identity,expected_md5)
  loop
    if to_regprocedure(r.identity) is null then
      raise exception 'ERP v2.6.19b target guard: required function % is absent',r.identity;
    end if;
    select md5(pg_get_functiondef(to_regprocedure(r.identity))) into v_actual;
    if v_actual is distinct from r.expected_md5 then
      raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: % changed (% vs %)',
        r.identity,v_actual,r.expected_md5;
    end if;
  end loop;
end
$guard$;

create table erp.bs_resolution_v2619b_rollback_capsule(
  function_identity text primary key,
  function_regprocedure text not null unique,
  function_definition text not null,
  definition_sha256 text not null,
  installed_definition_sha256 text,
  acl_snapshot text[],
  owner_snapshot text not null,
  captured_at timestamptz not null default clock_timestamp()
);
alter table erp.bs_resolution_v2619b_rollback_capsule enable row level security;
revoke all on table erp.bs_resolution_v2619b_rollback_capsule
  from public,anon,authenticated,service_role;

insert into erp.bs_resolution_v2619b_rollback_capsule(
  function_identity,function_regprocedure,function_definition,
  definition_sha256,acl_snapshot,owner_snapshot
)
select format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)),
  p.oid::regprocedure::text,
  pg_get_functiondef(p.oid),
  encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
  case when p.proacl is null then null else array(select a::text from unnest(p.proacl) a) end,
  pg_get_userbyid(p.proowner)
from pg_proc p join pg_namespace n on n.oid=p.pronamespace
where p.oid in(
  'erp.validate_laundry_claim_lineage()'::regprocedure,
  'erp.guard_laundry_claim_capacity_on_resolution()'::regprocedure,
  'erp.guard_laundry_receipt_source_capacity_on_post()'::regprocedure,
  'erp.save_laundry_claim_v2(jsonb,uuid,bigint)'::regprocedure,
  'erp.bs_accessory_bom_options_v1(uuid,timestamp with time zone)'::regprocedure,
  'erp.get_rework_accessory_decision_v1(uuid)'::regprocedure,
  'public.erp_get_bs_resolution_workspace_v1(text,text,uuid,text,integer,integer)'::regprocedure
);

do $capsule_guard$
begin
  if (select count(*) from erp.bs_resolution_v2619b_rollback_capsule)<>7
     or exists(
       select 1 from erp.bs_resolution_v2619b_rollback_capsule
       where definition_sha256 is distinct from
         encode(extensions.digest(convert_to(function_definition,'UTF8'),'sha256'),'hex')
     ) then
    raise exception 'ERP v2.6.19b rollback capsule is incomplete or invalid';
  end if;
end
$capsule_guard$;

alter table erp.rework_accessory_selection_lines
  add column selection_basis varchar(30);
alter table erp.rework_accessory_selection_lines
  add constraint rework_accessory_selection_lines_selection_basis_check
  check(selection_basis in('UNPAID_BASELINE','MANUAL_REPLACEMENT'));
alter table erp.rework_accessory_selection_lines
  alter column selection_basis set not null;

create function erp.set_rework_accessory_selection_basis_v2619b()
returns trigger language plpgsql set search_path=''
as $function$
declare
  v_stage text;
  v_tracked boolean;
  v_case_qty integer;
  v_entitled_qty integer;
begin
  select b.detected_at_stage::text,
         b.po_id is not null and b.product_id is not null and b.untracked_type is null,
         b.qty_pcs,
         coalesce((
           select sum(s.good_qty_pcs)::integer
           from erp.rework_orders ro
           join erp.fg_accessory_cost_snapshots s on s.lot_id=ro.good_fg_lot_id
           where ro.bs_case_id=b.id and ro.status='COMPLETED' and ro.cost_posted
             and s.category_id=new.category_id
         ),0)
    into v_stage,v_tracked,v_case_qty,v_entitled_qty
  from erp.rework_accessory_decisions d
  join erp.bs_cases b on b.id=d.bs_case_id
  join erp.accessory_bom_items i
    on i.id=new.bom_item_id and i.bom_version_id=d.bom_version_id
      and i.category_id=new.category_id
  where d.id=new.decision_id and d.rework_order_id=new.rework_order_id;
  if not found then
    raise exception 'Accessory selection has no authoritative BS/BOM/category lineage';
  end if;
  new.selection_basis:=case
    when v_tracked and v_stage in('SEWING','LAUNDRY','QC')
      and v_entitled_qty<v_case_qty then 'UNPAID_BASELINE'
    else 'MANUAL_REPLACEMENT'
  end;
  return new;
end
$function$;

create trigger trg_00_set_rework_accessory_selection_basis_v2619b
before insert on erp.rework_accessory_selection_lines
for each row execute function erp.set_rework_accessory_selection_basis_v2619b();

alter table erp.laundry_claims drop constraint laundry_claims_claim_type_check;
alter table erp.laundry_claims add constraint laundry_claims_claim_type_check
  check(claim_type in('MISSING','STUCK','DAMAGE'));

create or replace function erp.validate_laundry_claim_lineage()
returns trigger language plpgsql set search_path=''
as $function$
declare
  v_delivery_vendor uuid;
  v_delivery_status text;
  v_delivery_at timestamptz;
  v_line_delivery uuid;
  v_receipt_status text;
  v_receipt_at timestamptz;
  v_bs bigint;
  v_sent bigint;
  v_returned bigint;
  v_other_claimed bigint;
begin
  if new.claim_type not in('MISSING','STUCK','DAMAGE') then
    raise exception 'Laundry claim type must be MISSING, STUCK, or DAMAGE';
  end if;
  if new.claim_type='DAMAGE' then
    if new.receipt_line_id is null then
      raise exception 'Laundry DAMAGE claim must reference the posted receipt line where BS returned';
    end if;
    -- Receipt first, delivery second. Receipt posting/reversal uses the same
    -- order so a concurrent claim cannot validate against a state being reversed.
    select lr.delivery_id,lr.status::text,lr.physical_at,lrl.qty_bs_laundry
      into v_line_delivery,v_receipt_status,v_receipt_at,v_bs
    from erp.laundry_receipt_lines lrl
    join erp.laundry_receipts lr on lr.id=lrl.receipt_id
    where lrl.id=new.receipt_line_id
    for update of lr,lrl;
    if not found then raise exception 'Laundry DAMAGE receipt line not found'; end if;
    if new.delivery_id is null then new.delivery_id:=v_line_delivery; end if;
  elsif new.delivery_id is null then
    raise exception 'Laundry MISSING/STUCK claim requires an authoritative delivery';
  end if;

  select ld.vendor_id,ld.status::text,ld.physical_at
    into v_delivery_vendor,v_delivery_status,v_delivery_at
  from erp.laundry_deliveries ld where ld.id=new.delivery_id for update;
  if not found then raise exception 'Laundry delivery not found'; end if;
  if v_delivery_status not in('SENT','PARTIAL_RETURN','RETURNED','CLOSED') then
    raise exception 'Laundry claim requires a sent authoritative delivery; current status %',v_delivery_status;
  end if;
  if new.vendor_id is distinct from v_delivery_vendor then
    raise exception 'Laundry claim vendor must match delivery vendor';
  end if;
  if new.opened_at<v_delivery_at then
    raise exception 'Laundry claim cannot predate its physical delivery';
  end if;

  if new.claim_type in('MISSING','STUCK') then
    if new.receipt_line_id is not null then
      raise exception 'Laundry MISSING/STUCK claim must reference the delivery, not a receipt line';
    end if;
    if new.status<>'REJECTED' then
      select coalesce(sum(ldl.qty_sent_pcs),0)::bigint into v_sent
      from erp.laundry_delivery_lines ldl where ldl.delivery_id=new.delivery_id;
      select coalesce(sum(lrl.qty_good_received+lrl.qty_bs_laundry),0)::bigint into v_returned
      from erp.laundry_receipt_lines lrl
      join erp.laundry_receipts lr on lr.id=lrl.receipt_id
      where lr.delivery_id=new.delivery_id and lr.status='POSTED';
      select coalesce(sum(lc.qty_claimed),0)::bigint into v_other_claimed
      from erp.laundry_claims lc
      where lc.delivery_id=new.delivery_id and lc.id<>new.id
        and lc.claim_type in('MISSING','STUCK') and lc.status<>'REJECTED';
      if v_other_claimed+new.qty_claimed>greatest(v_sent-v_returned,0) then
        raise exception 'Laundry MISSING/STUCK conservation failed. Sent %, returned %, other active claims %, requested %',
          v_sent,v_returned,v_other_claimed,new.qty_claimed;
      end if;
    end if;
  else
    if v_line_delivery is distinct from new.delivery_id then
      raise exception 'Laundry DAMAGE receipt line does not belong to delivery';
    end if;
    if v_receipt_status<>'POSTED' then
      raise exception 'Laundry DAMAGE claim requires a POSTED receipt; current status %',v_receipt_status;
    end if;
    if new.opened_at<v_receipt_at then
      raise exception 'Laundry DAMAGE claim cannot predate its physical receipt';
    end if;
    if new.status<>'REJECTED' then
      select coalesce(sum(lc.qty_claimed),0)::bigint into v_other_claimed
      from erp.laundry_claims lc
      where lc.receipt_line_id=new.receipt_line_id and lc.id<>new.id
        and lc.claim_type='DAMAGE' and lc.status<>'REJECTED';
      if v_other_claimed+new.qty_claimed>coalesce(v_bs,0) then
        raise exception 'Laundry DAMAGE conservation failed. Posted BS %, other active claims %, requested %',
          coalesce(v_bs,0),v_other_claimed,new.qty_claimed;
      end if;
    end if;
  end if;
  return new;
end
$function$;

create or replace function erp.guard_laundry_claim_capacity_on_resolution()
returns trigger language plpgsql set search_path=''
as $function$
declare
  v_delivery_status text;
  v_receipt_status text;
  v_sent bigint;
  v_returned bigint;
  v_claimed bigint;
  v_bs bigint;
begin
  if new.status in('SETTLED','WRITTEN_OFF') and old.status is distinct from new.status then
    if new.claim_type in('MISSING','STUCK') then
      select ld.status::text into v_delivery_status
      from erp.laundry_deliveries ld where ld.id=new.delivery_id for update;
      if not found or v_delivery_status not in('SENT','PARTIAL_RETURN','RETURNED','CLOSED') then
        raise exception 'Laundry claim resolution requires an authoritative sent delivery';
      end if;
      select coalesce(sum(ldl.qty_sent_pcs),0)::bigint into v_sent
      from erp.laundry_delivery_lines ldl where ldl.delivery_id=new.delivery_id;
      select coalesce(sum(lrl.qty_good_received+lrl.qty_bs_laundry),0)::bigint into v_returned
      from erp.laundry_receipt_lines lrl
      join erp.laundry_receipts lr on lr.id=lrl.receipt_id
      where lr.delivery_id=new.delivery_id and lr.status='POSTED';
      select coalesce(sum(lc.qty_claimed),0)::bigint into v_claimed
      from erp.laundry_claims lc
      where lc.delivery_id=new.delivery_id and lc.claim_type in('MISSING','STUCK')
        and lc.status<>'REJECTED';
      if v_returned+v_claimed>v_sent then
        raise exception 'Laundry claim resolution conservation failed. Sent %, returned %, active claims %',
          v_sent,v_returned,v_claimed;
      end if;
    elsif new.claim_type='DAMAGE' then
      if new.receipt_line_id is null then
        raise exception 'Laundry DAMAGE claim must reference a receipt line';
      end if;
      select lr.status::text,lrl.qty_bs_laundry
        into v_receipt_status,v_bs
      from erp.laundry_receipt_lines lrl
      join erp.laundry_receipts lr on lr.id=lrl.receipt_id
      where lrl.id=new.receipt_line_id for update of lrl;
      if not found or v_receipt_status<>'POSTED' then
        raise exception 'Laundry DAMAGE claim resolution requires a POSTED receipt';
      end if;
      select coalesce(sum(lc.qty_claimed),0)::bigint into v_claimed
      from erp.laundry_claims lc
      where lc.receipt_line_id=new.receipt_line_id and lc.claim_type='DAMAGE'
        and lc.status<>'REJECTED';
      if v_claimed>coalesce(v_bs,0) then
        raise exception 'Laundry DAMAGE resolution conservation failed. Posted BS %, active claims %',
          coalesce(v_bs,0),v_claimed;
      end if;
    else
      raise exception 'Laundry claim resolution type is not supported';
    end if;
  end if;
  return new;
end
$function$;

create or replace function erp.guard_laundry_receipt_source_capacity_on_post()
returns trigger language plpgsql set search_path=''
as $function$
declare
  r record;
  v_delivery_status text;
  v_sent bigint;
  v_sent_total bigint;
  v_prior bigint;
  v_prior_total bigint;
  v_current bigint;
  v_current_total bigint;
  v_claimed bigint;
  v_source_delivery uuid;
begin
  if new.status='POSTED' and old.status is distinct from 'POSTED' then
    select ld.status::text into v_delivery_status
    from erp.laundry_deliveries ld where ld.id=new.delivery_id for update;
    if not found or v_delivery_status not in('SENT','PARTIAL_RETURN','RETURNED','CLOSED') then
      raise exception 'Laundry receipt posting requires an authoritative sent delivery';
    end if;

    select coalesce(sum(ldl.qty_sent_pcs),0)::bigint into v_sent_total
    from erp.laundry_delivery_lines ldl where ldl.delivery_id=new.delivery_id;
    select coalesce(sum(lrl.qty_good_received+lrl.qty_bs_laundry),0)::bigint into v_prior_total
    from erp.laundry_receipt_lines lrl
    join erp.laundry_receipts lr on lr.id=lrl.receipt_id
    where lr.delivery_id=new.delivery_id and lr.id<>new.id and lr.status='POSTED';
    select coalesce(sum(lrl.qty_good_received+lrl.qty_bs_laundry),0)::bigint into v_current_total
    from erp.laundry_receipt_lines lrl where lrl.receipt_id=new.id;
    select coalesce(sum(lc.qty_claimed),0)::bigint into v_claimed
    from erp.laundry_claims lc
    where lc.delivery_id=new.delivery_id and lc.claim_type in('MISSING','STUCK')
      and lc.status<>'REJECTED';
    if v_prior_total+v_current_total+v_claimed>v_sent_total then
      raise exception 'Laundry return plus active MISSING/STUCK claims exceed sent quantity. Sent %, prior returns %, this return %, active claims %',
        v_sent_total,v_prior_total,v_current_total,v_claimed;
    end if;

    for r in
      select lrl.delivery_line_id,
             sum(lrl.qty_good_received+lrl.qty_bs_laundry)::bigint current_qty
      from erp.laundry_receipt_lines lrl where lrl.receipt_id=new.id
      group by lrl.delivery_line_id order by lrl.delivery_line_id
    loop
      select ldl.qty_sent_pcs,ldl.delivery_id into v_sent,v_source_delivery
      from erp.laundry_delivery_lines ldl where ldl.id=r.delivery_line_id for update;
      if v_sent is null or v_source_delivery is distinct from new.delivery_id then
        raise exception 'Laundry receipt line source does not belong to this delivery at posting time';
      end if;
      select coalesce(sum(x.qty_good_received+x.qty_bs_laundry),0)::bigint into v_prior
      from erp.laundry_receipt_lines x
      join erp.laundry_receipts xr on xr.id=x.receipt_id
      where x.delivery_line_id=r.delivery_line_id and xr.id<>new.id and xr.status='POSTED';
      v_current:=coalesce(r.current_qty,0);
      if v_prior+v_current>v_sent then
        raise exception 'Laundry physical return exceeds quantity sent at posting. Sent %, already returned %, this receipt %',
          v_sent,v_prior,v_current;
      end if;
    end loop;
  end if;
  return new;
end
$function$;

create function erp.guard_laundry_claim_delivery_source_v2619b()
returns trigger language plpgsql set search_path=''
as $function$
begin
  if tg_op='DELETE' then
    if exists(select 1 from erp.laundry_claims c where c.delivery_id=old.id and c.status<>'REJECTED') then
      raise exception 'Laundry delivery with an active/final claim cannot be deleted';
    end if;
    return old;
  end if;
  if old.status is distinct from new.status and new.status in('DRAFT','REVERSED')
     and exists(select 1 from erp.laundry_claims c where c.delivery_id=old.id and c.status<>'REJECTED') then
    raise exception 'Reject or reverse/correct dependent Laundry claims before invalidating their delivery';
  end if;
  return new;
end
$function$;

create trigger trg_guard_laundry_claim_delivery_source_v2619b
before update or delete on erp.laundry_deliveries
for each row execute function erp.guard_laundry_claim_delivery_source_v2619b();

create function erp.guard_laundry_claim_receipt_source_v2619b()
returns trigger language plpgsql set search_path=''
as $function$
begin
  -- UPDATE/DELETE already owns the receipt row. Lock its delivery second,
  -- matching DAMAGE claim validation, before observing dependent claims.
  perform 1 from erp.laundry_deliveries d where d.id=old.delivery_id for update;
  if not found then raise exception 'Laundry receipt source delivery not found'; end if;
  if tg_op='DELETE' then
    if exists(
      select 1 from erp.laundry_claims c
      join erp.laundry_receipt_lines l on l.id=c.receipt_line_id
      where l.receipt_id=old.id and c.claim_type='DAMAGE' and c.status<>'REJECTED'
    ) then raise exception 'Laundry receipt with an active/final DAMAGE claim cannot be deleted'; end if;
    return old;
  end if;
  if old.status is distinct from new.status and new.status='REVERSED'
     and exists(
       select 1 from erp.laundry_claims c
       join erp.laundry_receipt_lines l on l.id=c.receipt_line_id
       where l.receipt_id=old.id and c.claim_type='DAMAGE' and c.status<>'REJECTED'
     ) then
    raise exception 'Reject or reverse/correct dependent DAMAGE claims before reversing their receipt';
  end if;
  return new;
end
$function$;

create trigger trg_guard_laundry_claim_receipt_source_v2619b
before update or delete on erp.laundry_receipts
for each row execute function erp.guard_laundry_claim_receipt_source_v2619b();

create or replace function erp.save_laundry_claim_v2(
  p_payload jsonb,p_client_request_id uuid,p_expected_version bigint default null
)
returns jsonb language plpgsql security definer set search_path=''
as $function$
declare
  v_hash text;v_cached jsonb;v_response jsonb;
  v_id uuid;
  v_action text;
  v_reason text;
  v_claim erp.laundry_claims%rowtype;
  v_target_status text;
  v_unknown text;
  v_claim_type text;
begin
  perform erp.require_internal();
  if p_payload is null or jsonb_typeof(p_payload)<>'object' then
    raise exception 'Claim payload must be a JSON object';
  end if;
  select string_agg(k,',' order by k) into v_unknown
  from jsonb_object_keys(p_payload) k
  where not(k=any(array[
    'id','action','claim_number','vendor_id','delivery_id','receipt_line_id',
    'qty_claimed','claim_type','compensation_amount','status','opened_at',
    'resolution_date','notes','change_reason'
  ]::text[]));
  if v_unknown is not null then raise exception 'Unknown Laundry claim payload keys: %',v_unknown; end if;

  v_id:=nullif(p_payload->>'id','')::uuid;
  v_action:=upper(coalesce(nullif(p_payload->>'action',''),'SAVE'));
  v_reason:=nullif(btrim(p_payload->>'change_reason'),'');
  if v_action not in('SAVE','REJECT','REOPEN') then
    raise exception 'Claim action must be SAVE, REJECT, or REOPEN';
  end if;
  if v_reason is null then raise exception 'change_reason is required'; end if;
  if p_payload?'claim_type' then
    v_claim_type:=upper(coalesce(nullif(p_payload->>'claim_type',''),''));
    if v_claim_type not in('MISSING','STUCK','DAMAGE') then
      raise exception 'Laundry claim type must be MISSING, STUCK, or DAMAGE';
    end if;
  end if;
  if p_payload?'opened_at'
     and nullif(p_payload->>'opened_at','')::timestamptz>clock_timestamp()+interval '5 minutes' then
    raise exception 'Claim opened_at cannot be in the future';
  end if;

  v_hash:=erp._request_hash(jsonb_build_object('payload',p_payload,'expected_version',p_expected_version));
  v_cached:=erp._idempotency_begin('save_laundry_claim_v2',p_client_request_id,v_hash);
  if v_cached is not null then return v_cached; end if;
  perform set_config('app.change_reason',v_reason,true);

  if v_id is null then
    if v_action<>'SAVE' then raise exception 'Create a claim with SAVE first'; end if;
    if p_expected_version is not null then raise exception 'expected_version must be null when creating a claim'; end if;
    if coalesce(btrim(p_payload->>'claim_number'),'')='' then raise exception 'claim_number is required'; end if;
    if not(p_payload?'vendor_id') or not(p_payload?'qty_claimed') or not(p_payload?'claim_type') then
      raise exception 'vendor_id, qty_claimed, and claim_type are required';
    end if;
    insert into erp.laundry_claims(
      claim_number,vendor_id,delivery_id,receipt_line_id,qty_claimed,claim_type,
      compensation_amount,status,opened_at,resolution_date,notes
    ) values(
      btrim(p_payload->>'claim_number'),(p_payload->>'vendor_id')::uuid,
      nullif(p_payload->>'delivery_id','')::uuid,nullif(p_payload->>'receipt_line_id','')::uuid,
      (p_payload->>'qty_claimed')::integer,v_claim_type,
      coalesce(nullif(p_payload->>'compensation_amount','')::numeric,0),'OPEN',
      coalesce(nullif(p_payload->>'opened_at','')::timestamptz,now()),
      nullif(p_payload->>'resolution_date','')::date,nullif(btrim(p_payload->>'notes'),'')
    ) returning * into v_claim;
  else
    if p_expected_version is null then raise exception 'expected_version is required'; end if;
    select * into v_claim from erp.laundry_claims where id=v_id for update;
    if not found then raise exception 'Laundry claim not found'; end if;
    if v_claim.row_version<>p_expected_version then
      raise exception 'STALE_VERSION expected %, current %',p_expected_version,v_claim.row_version;
    end if;
    if v_claim.status in('SETTLED','WRITTEN_OFF') then
      raise exception 'Final claim is locked; use reverse_laundry_claim_resolution first';
    end if;
    if v_action<>'SAVE' and p_payload ?| array[
      'claim_number','vendor_id','delivery_id','receipt_line_id','qty_claimed',
      'claim_type','compensation_amount','status','opened_at','resolution_date','notes'
    ] then raise exception 'REJECT/REOPEN may not edit claim facts'; end if;
    if v_claim.status<>'OPEN' and p_payload ?| array[
      'vendor_id','delivery_id','receipt_line_id','qty_claimed','claim_type','opened_at'
    ] then raise exception 'Accepted claim source, type, quantity, and physical time are immutable'; end if;

    if v_action='REOPEN' then
      perform erp.require_owner_admin();v_target_status:='OPEN';
    elsif v_action='REJECT' then
      v_target_status:='REJECTED';
    else
      if v_claim.status='REJECTED' then raise exception 'Rejected claim requires REOPEN by OWNER/ADMIN'; end if;
      v_target_status:=upper(coalesce(nullif(p_payload->>'status',''),v_claim.status));
      if v_target_status not in('OPEN','ACCEPTED') then
        raise exception 'SAVE claim status must be OPEN or ACCEPTED';
      end if;
    end if;
    update erp.laundry_claims
    set claim_number=coalesce(nullif(btrim(p_payload->>'claim_number'),''),v_claim.claim_number),
        vendor_id=case when p_payload?'vendor_id' then (p_payload->>'vendor_id')::uuid else v_claim.vendor_id end,
        delivery_id=case when p_payload?'delivery_id' then nullif(p_payload->>'delivery_id','')::uuid else v_claim.delivery_id end,
        receipt_line_id=case when p_payload?'receipt_line_id' then nullif(p_payload->>'receipt_line_id','')::uuid else v_claim.receipt_line_id end,
        qty_claimed=case when p_payload?'qty_claimed' then (p_payload->>'qty_claimed')::integer else v_claim.qty_claimed end,
        claim_type=coalesce(v_claim_type,v_claim.claim_type),
        compensation_amount=case when p_payload?'compensation_amount' then (p_payload->>'compensation_amount')::numeric else v_claim.compensation_amount end,
        status=v_target_status,
        opened_at=case when p_payload?'opened_at' then (p_payload->>'opened_at')::timestamptz else v_claim.opened_at end,
        resolution_date=case when p_payload?'resolution_date' then nullif(p_payload->>'resolution_date','')::date else v_claim.resolution_date end,
        notes=case when p_payload?'notes' then nullif(btrim(p_payload->>'notes'),'') else v_claim.notes end
    where id=v_claim.id returning * into v_claim;
  end if;
  v_response:=jsonb_build_object(
    'laundry_claim_id',v_claim.id,'claim_number',v_claim.claim_number,
    'status',v_claim.status,'row_version',v_claim.row_version,
    'qty_claimed',v_claim.qty_claimed,'compensation_amount',v_claim.compensation_amount
  );
  return erp._idempotency_complete('save_laundry_claim_v2',p_client_request_id,v_response);
end
$function$;

create or replace function erp.bs_accessory_bom_options_v1(
  p_bs_case_id uuid,p_basis_at timestamptz default statement_timestamp()
)
returns jsonb language plpgsql stable security definer set search_path=''
as $function$
declare
  v_bom uuid;
  v_stage text;
  v_pre_fg_tracked boolean;
  v_case_qty integer;
  v_resolved integer;
  v_active integer;
  v_available integer;
begin
  select b.detected_at_stage::text,
         b.po_id is not null and b.product_id is not null and b.untracked_type is null,
         b.qty_pcs
    into v_stage,v_pre_fg_tracked,v_case_qty
  from erp.bs_cases b where b.id=p_bs_case_id;
  if not found then raise exception 'BS case not found for accessory decision'; end if;
  select coalesce(sum(r.qty_pcs),0)::integer into v_resolved
  from erp.bs_resolutions r where r.bs_case_id=p_bs_case_id;
  select coalesce(sum(o.qty_sent),0)::integer into v_active
  from erp.rework_orders o where o.bs_case_id=p_bs_case_id
    and o.status in('OPEN','IN_PROGRESS','PARTIAL');
  v_available:=greatest(v_case_qty-v_resolved-v_active,0);
  v_pre_fg_tracked:=v_pre_fg_tracked and v_stage in('SEWING','LAUNDRY','QC');

  v_bom:=erp.resolve_rework_accessory_bom_v1(p_bs_case_id,p_basis_at);
  if v_bom is null then
    return jsonb_build_object(
      'state','UNAVAILABLE','bom_version_id',null,
      'default_policy','SERVER_ENTITLEMENT_V2619B','available_qty_pcs',v_available,
      'items','[]'::jsonb
    );
  end if;
  return jsonb_build_object(
    'state',case when exists(select 1 from erp.accessory_bom_items where bom_version_id=v_bom)
      then 'AVAILABLE' else 'NONE' end,
    'bom_version_id',v_bom,
    'default_policy','SERVER_ENTITLEMENT_V2619B','available_qty_pcs',v_available,
    'items',coalesce((
      select jsonb_agg(jsonb_build_object(
        'id',i.id,'category_id',i.category_id,'code',c.category_code,
        'name',c.category_name,'base_uom_code',c.base_uom_code,
        'qty_per_good_fg_base',i.qty_per_good_fg_base,
        'reimbursement_rate',i.reimbursement_rate,
        'reimbursement_uom_code',i.reimbursement_uom_code,
        'default_selected',ent.remaining_unentitled_good_qty_pcs>0,
        'default_selection_basis',case when ent.remaining_unentitled_good_qty_pcs>0
          then 'UNPAID_BASELINE' else 'MANUAL_REPLACEMENT' end,
        'default_reason',case
          when v_available<=0 then 'NO_AVAILABLE_QUANTITY'
          when not v_pre_fg_tracked then 'POST_FG_OR_UNPROVEN_BASELINE'
          when ent.remaining_unentitled_good_qty_pcs<=0 then 'BASELINE_ENTITLEMENT_EXHAUSTED'
          when v_pre_fg_tracked then 'PRE_FG_UNPAID_BASELINE'
          else 'POST_FG_OR_UNPROVEN_BASELINE' end,
        'already_entitled_good_qty_pcs',ent.already_entitled_good_qty_pcs,
        'already_cash_settled_good_qty_pcs',ent.already_cash_settled_good_qty_pcs,
        'remaining_unentitled_good_qty_pcs',ent.remaining_unentitled_good_qty_pcs
      ) order by c.category_code,i.id)
      from erp.accessory_bom_items i
      join erp.accessory_categories c on c.id=i.category_id
      cross join lateral(
        select already_entitled_good_qty_pcs,already_cash_settled_good_qty_pcs,
          case when v_pre_fg_tracked then least(
            v_available,greatest(v_case_qty-already_entitled_good_qty_pcs,0)
          ) else 0 end::integer remaining_unentitled_good_qty_pcs
        from(
          select
            coalesce((
              select sum(s.good_qty_pcs)::integer
              from erp.rework_orders ro
              join erp.fg_accessory_cost_snapshots s on s.lot_id=ro.good_fg_lot_id
              where ro.bs_case_id=p_bs_case_id and ro.status='COMPLETED'
                and ro.cost_posted and s.category_id=i.category_id
            ),0)::integer already_entitled_good_qty_pcs,
            coalesce((
              select sum(s.good_qty_pcs)::integer
              from erp.rework_orders ro
              join erp.fg_accessory_cost_snapshots s on s.lot_id=ro.good_fg_lot_id
              join erp.contractor_accessory_reimbursement_entitlements e
                on e.snapshot_id=s.id and e.payroll_status='SETTLED'
              where ro.bs_case_id=p_bs_case_id and ro.status='COMPLETED'
                and ro.cost_posted and s.category_id=i.category_id
            ),0)::integer already_cash_settled_good_qty_pcs
        ) counters
      ) ent
      where i.bom_version_id=v_bom
    ),'[]'::jsonb)
  );
end
$function$;

create or replace function erp.get_rework_accessory_decision_v1(p_rework_order_id uuid)
returns jsonb language sql stable security definer set search_path=''
as $function$
  select jsonb_build_object(
    'state',d.decision_state,'bom_version_id',d.bom_version_id,
    'reimbursement_contractor_id',d.reimbursement_contractor_id,
    'selected_item_count',d.selected_item_count,
    'selection_sha256',d.selection_sha256,'basis_at',d.basis_at,
    'selected_items',coalesce((
      select jsonb_agg(jsonb_build_object(
        'id',l.id,'bom_item_id',l.bom_item_id,'category_id',l.category_id,
        'code',c.category_code,'name',c.category_name,
        'qty_per_good_fg_base',l.qty_per_good_fg_base_snapshot,
        'reimbursement_unit_rate_base',l.reimbursement_unit_rate_base_snapshot,
        'selection_basis',l.selection_basis
      ) order by c.category_code,l.id)
      from erp.rework_accessory_selection_lines l
      join erp.accessory_categories c on c.id=l.category_id
      where l.decision_id=d.id
    ),'[]'::jsonb)
  )
  from erp.rework_accessory_decisions d
  where d.rework_order_id=p_rework_order_id
$function$;

create or replace function public.erp_get_bs_resolution_workspace_v1(
  p_filter text default 'ACTIVE',p_kind text default 'ALL',
  p_pattern_id uuid default null,p_query text default null,
  p_limit integer default 50,p_offset integer default 0
)
returns jsonb language plpgsql stable security definer set search_path=''
as $function$
declare
  v_workspace jsonb;
  v_rows jsonb;
begin
  v_workspace:=erp.get_bs_resolution_workspace_v1(
    p_filter,p_kind,p_pattern_id,p_query,p_limit,p_offset
  );
  select coalesce(jsonb_agg(
    case when q.value->>'kind'='BS' then
      jsonb_set(
        jsonb_set(
          q.value||jsonb_build_object(
            'accessory_bom',erp.bs_accessory_bom_options_v1(
              (q.value->>'id')::uuid,statement_timestamp()
            )
          ),
          '{components}',coalesce((
            select jsonb_agg(
              c.value||jsonb_build_object(
                'remaining_new_work_qty_pcs',greatest(least(
                  (q.value->>'available_qty')::integer,
                  (q.value->>'qty_pcs')::integer
                    -(c.value->>'completed_before_bs_qty')::integer
                    -(c.value->>'lifetime_newly_completed_qty')::integer
                ),0),
                'default_selected',greatest(least(
                  (q.value->>'available_qty')::integer,
                  (q.value->>'qty_pcs')::integer
                    -(c.value->>'completed_before_bs_qty')::integer
                    -(c.value->>'lifetime_newly_completed_qty')::integer
                ),0)>0,
                'default_selection_basis','UNPAID_COMPONENT_ENTITLEMENT'
              ) order by c.ord
            )
            from jsonb_array_elements(q.value->'components')
              with ordinality as c(value,ord)
          ),'[]'::jsonb),true
        ),
        '{rework_orders}',coalesce((
          select jsonb_agg(
            o.value||jsonb_build_object(
              'accessory_decision',erp.get_rework_accessory_decision_v1(
                (o.value->>'id')::uuid
              )
            ) order by o.ord
          )
          from jsonb_array_elements(q.value->'rework_orders')
            with ordinality as o(value,ord)
        ),'[]'::jsonb),true
      )
    else q.value||jsonb_build_object('accessory_bom',null) end
    order by q.ord
  ),'[]'::jsonb) into v_rows
  from jsonb_array_elements(v_workspace->'rows') with ordinality as q(value,ord);
  return jsonb_set(v_workspace,'{rows}',v_rows,true);
end
$function$;

alter table erp.bs_resolution_v2619b_rollback_capsule owner to postgres;
alter function erp.set_rework_accessory_selection_basis_v2619b() owner to postgres;
alter function erp.guard_laundry_claim_delivery_source_v2619b() owner to postgres;
alter function erp.guard_laundry_claim_receipt_source_v2619b() owner to postgres;
alter function erp.validate_laundry_claim_lineage() owner to postgres;
alter function erp.guard_laundry_claim_capacity_on_resolution() owner to postgres;
alter function erp.guard_laundry_receipt_source_capacity_on_post() owner to postgres;
alter function erp.save_laundry_claim_v2(jsonb,uuid,bigint) owner to postgres;
alter function erp.bs_accessory_bom_options_v1(uuid,timestamp with time zone) owner to postgres;
alter function erp.get_rework_accessory_decision_v1(uuid) owner to postgres;
alter function public.erp_get_bs_resolution_workspace_v1(text,text,uuid,text,integer,integer) owner to postgres;

revoke all on function
  erp.set_rework_accessory_selection_basis_v2619b(),
  erp.guard_laundry_claim_delivery_source_v2619b(),
  erp.guard_laundry_claim_receipt_source_v2619b(),
  erp.validate_laundry_claim_lineage(),
  erp.guard_laundry_claim_capacity_on_resolution(),
  erp.guard_laundry_receipt_source_capacity_on_post(),
  erp.save_laundry_claim_v2(jsonb,uuid,bigint),
  erp.bs_accessory_bom_options_v1(uuid,timestamp with time zone),
  erp.get_rework_accessory_decision_v1(uuid)
  from public,anon,authenticated,service_role;
revoke all on function
  public.erp_get_bs_resolution_workspace_v1(text,text,uuid,text,integer,integer)
  from public,anon,authenticated,service_role;
grant execute on function
  public.erp_get_bs_resolution_workspace_v1(text,text,uuid,text,integer,integer)
  to authenticated,service_role;

comment on column erp.rework_accessory_selection_lines.selection_basis is
  'Server-derived immutable provenance: unpaid pre-FG baseline or explicit manual replacement.';
comment on function public.erp_get_bs_resolution_workspace_v1(text,text,uuid,text,integer,integer) is
  'CP5 guarded workspace with server-derived unpaid defaults, immutable replacement provenance, and conserved Laundry claim sources.';

update erp.bs_resolution_v2619b_rollback_capsule c
set installed_definition_sha256=encode(extensions.digest(
  convert_to(pg_get_functiondef(to_regprocedure(c.function_regprocedure)),'UTF8'),'sha256'
),'hex');

do $post_guard$
declare
  v_bad text;
  v_claim_constraint text;
begin
  if (select count(*) from erp.bs_resolution_v2619b_rollback_capsule)<>7
     or exists(
       select 1 from erp.bs_resolution_v2619b_rollback_capsule c
       where c.definition_sha256 is distinct from encode(extensions.digest(
         convert_to(c.function_definition,'UTF8'),'sha256'),'hex')
          or c.installed_definition_sha256 is null
          or c.installed_definition_sha256 is distinct from encode(extensions.digest(
            convert_to(pg_get_functiondef(to_regprocedure(c.function_regprocedure)),'UTF8'),'sha256'
          ),'hex')
     ) then raise exception 'ERP v2.6.19b post guard: rollback capsule drift'; end if;

  select pg_get_constraintdef(oid) into v_claim_constraint
  from pg_constraint where conrelid='erp.laundry_claims'::regclass
    and conname='laundry_claims_claim_type_check';
  if v_claim_constraint is null or v_claim_constraint like '%OTHER%'
     or v_claim_constraint not like '%MISSING%'
     or v_claim_constraint not like '%STUCK%'
     or v_claim_constraint not like '%DAMAGE%' then
    raise exception 'ERP v2.6.19b post guard: claim type constraint is not closed';
  end if;
  if not exists(
    select 1 from information_schema.columns
    where table_schema='erp' and table_name='rework_accessory_selection_lines'
      and column_name='selection_basis' and is_nullable='NO'
  ) then raise exception 'ERP v2.6.19b post guard: immutable selection basis is absent'; end if;
  if not exists(
    select 1 from pg_trigger where tgrelid='erp.rework_accessory_selection_lines'::regclass
      and tgname='trg_00_set_rework_accessory_selection_basis_v2619b'
      and tgenabled<>'D' and not tgisinternal
  ) or not exists(
    select 1 from pg_trigger where tgrelid='erp.laundry_deliveries'::regclass
      and tgname='trg_guard_laundry_claim_delivery_source_v2619b'
      and tgenabled<>'D' and not tgisinternal
  ) or not exists(
    select 1 from pg_trigger where tgrelid='erp.laundry_receipts'::regclass
      and tgname='trg_guard_laundry_claim_receipt_source_v2619b'
      and tgenabled<>'D' and not tgisinternal
  ) then raise exception 'ERP v2.6.19b post guard: source/basis trigger is missing'; end if;

  if pg_get_functiondef('erp.validate_laundry_claim_lineage()'::regprocedure)
       not like '%requires a sent authoritative delivery%'
     or pg_get_functiondef('erp.validate_laundry_claim_lineage()'::regprocedure)
       not like '%requires a POSTED receipt%'
     or pg_get_functiondef('erp.guard_laundry_receipt_source_capacity_on_post()'::regprocedure)
       not like '%return plus active MISSING/STUCK claims exceed sent quantity%'
     or pg_get_functiondef('erp.save_laundry_claim_v2(jsonb,uuid,bigint)'::regprocedure)
       not like '%MISSING, STUCK, or DAMAGE%'
     or pg_get_functiondef('erp.bs_accessory_bom_options_v1(uuid,timestamp with time zone)'::regprocedure)
       not like '%SERVER_ENTITLEMENT_V2619B%'
     or pg_get_functiondef('erp.bs_accessory_bom_options_v1(uuid,timestamp with time zone)'::regprocedure)
       not like '%remaining_unentitled_good_qty_pcs%'
     or pg_get_functiondef('erp.set_rework_accessory_selection_basis_v2619b()'::regprocedure)
       not like '%fg_accessory_cost_snapshots%'
     or pg_get_functiondef('public.erp_get_bs_resolution_workspace_v1(text,text,uuid,text,integer,integer)'::regprocedure)
       not like '%UNPAID_COMPONENT_ENTITLEMENT%' then
    raise exception 'ERP v2.6.19b post guard: reliability runtime contract is incomplete';
  end if;

  if has_function_privilege('anon','public.erp_get_bs_resolution_workspace_v1(text,text,uuid,text,integer,integer)','EXECUTE')
     or not has_function_privilege('authenticated','public.erp_get_bs_resolution_workspace_v1(text,text,uuid,text,integer,integer)','EXECUTE')
     or has_function_privilege('authenticated','erp.save_laundry_claim_v2(jsonb,uuid,bigint)','EXECUTE')
     or has_function_privilege('authenticated','erp.bs_accessory_bom_options_v1(uuid,timestamp with time zone)','EXECUTE') then
    raise exception 'ERP v2.6.19b post guard: facade/private ACL failed';
  end if;

  select string_agg(c.function_identity,',' order by c.function_identity) into v_bad
  from erp.bs_resolution_v2619b_rollback_capsule c
  join pg_proc p on p.oid=to_regprocedure(c.function_regprocedure)
  where not(coalesce(p.proconfig,array[]::text[])@>array['search_path=""']::text[]);
  if v_bad is not null then
    raise exception 'ERP v2.6.19b post guard: empty search_path missing: %',v_bad;
  end if;
end
$post_guard$;

insert into erp.schema_migrations(version,description)
values(
  'v2.6.19b',
  'CP5 reliability closure: server-derived unpaid defaults, explicit replacement provenance, authoritative Laundry source states, shared physical/claim conservation, and stale-UI writer freeze contract'
);

select pg_notify('pgrst','reload schema');
commit;
