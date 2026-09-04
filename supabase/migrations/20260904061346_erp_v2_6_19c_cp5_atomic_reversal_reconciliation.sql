-- ERP Garment v2.6.19c / CP5 atomic claim-to-BS reversal closure.
--
-- Reliability Data adalah Dewa; keuangan, stok, dan HPP adalah Raja.
-- A settled Laundry claim and every CASH_COMPENSATION disposition funded by
-- it must tell one atomic story under normal execution, retries, and races.

begin;
set local lock_timeout='10s';
set local statement_timeout='180s';

do $guard$
declare
  v_actual text;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.19b') then
    raise exception 'ERP v2.6.19c requires v2.6.19b first';
  end if;
  if exists(select 1 from erp.schema_migrations where version='v2.6.19c') then
    raise exception 'ERP v2.6.19c is already recorded; never replay or edit a recorded migration';
  end if;
  if to_regclass('erp.bs_resolution_v2619c_rollback_capsule') is not null
     or to_regprocedure('erp.guard_bs_resolution_claim_state_v2619c()') is not null
     or to_regprocedure('erp.guard_laundry_claim_bs_dependency_v2619c()') is not null
     or exists(
       select 1 from pg_constraint
       where conrelid='erp.bs_resolutions'::regclass
         and conname='bs_resolutions_cash_claim_contract_v2619c'
     ) then
    raise exception 'ERP v2.6.19c target guard: prior atomic-reversal residue exists';
  end if;
  if to_regprocedure('erp.reverse_laundry_claim_resolution(uuid,text)') is null
     or to_regclass('erp.bs_resolutions') is null
     or to_regclass('erp.laundry_claims') is null then
    raise exception 'ERP v2.6.19c target guard: CP5 claim/disposition runtime is incomplete';
  end if;
  select md5(pg_get_functiondef(
    'erp.reverse_laundry_claim_resolution(uuid,text)'::regprocedure
  )) into v_actual;
  if v_actual is distinct from '685a8ff668c28b5673cd24a2a89c6f7f' then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: reverse_laundry_claim_resolution changed (%)',v_actual;
  end if;
  if exists(
    select 1
    from erp.bs_resolutions r
    left join erp.laundry_claims c on c.id=r.source_laundry_claim_id
    where(
      r.resolution_type='CASH_COMPENSATION'
      and(
        r.source_laundry_claim_id is null
        or r.compensation_amount is null
        or r.compensation_amount<=0
        or c.status is distinct from 'SETTLED'
      )
    ) or(
      r.resolution_type<>'CASH_COMPENSATION'
      and(r.source_laundry_claim_id is not null or r.compensation_amount is distinct from 0)
    )
  ) then
    raise exception 'ERP v2.6.19c refused: existing BS/claim financial lineage is contradictory';
  end if;
end
$guard$;

create table erp.bs_resolution_v2619c_rollback_capsule(
  function_identity text primary key,
  function_regprocedure text not null unique,
  function_definition text not null,
  definition_sha256 text not null,
  installed_definition_sha256 text,
  acl_snapshot text[],
  owner_snapshot text not null,
  captured_at timestamptz not null default clock_timestamp()
);
alter table erp.bs_resolution_v2619c_rollback_capsule enable row level security;
revoke all on table erp.bs_resolution_v2619c_rollback_capsule
  from public,anon,authenticated,service_role;

insert into erp.bs_resolution_v2619c_rollback_capsule(
  function_identity,function_regprocedure,function_definition,
  definition_sha256,acl_snapshot,owner_snapshot
)
select
  format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)),
  format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)),
  pg_get_functiondef(p.oid),
  encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
  case when p.proacl is null then null else array(select a::text from unnest(p.proacl) a) end,
  pg_get_userbyid(p.proowner)
from pg_proc p join pg_namespace n on n.oid=p.pronamespace
where p.oid='erp.reverse_laundry_claim_resolution(uuid,text)'::regprocedure;

do $capsule_guard$
begin
  if (select count(*) from erp.bs_resolution_v2619c_rollback_capsule)<>1
     or exists(
       select 1 from erp.bs_resolution_v2619c_rollback_capsule c
       where c.definition_sha256 is distinct from encode(extensions.digest(
         convert_to(c.function_definition,'UTF8'),'sha256'
       ),'hex')
     ) then
    raise exception 'ERP v2.6.19c rollback capsule is incomplete or invalid';
  end if;
end
$capsule_guard$;

alter table erp.bs_resolutions
  add constraint bs_resolutions_cash_claim_contract_v2619c check(
    (
      resolution_type='CASH_COMPENSATION'
      and source_laundry_claim_id is not null
      and compensation_amount is not null
      and compensation_amount>0
    ) or(
      resolution_type<>'CASH_COMPENSATION'
      and source_laundry_claim_id is null
      and compensation_amount is not distinct from 0
    )
  ) not valid;
alter table erp.bs_resolutions
  validate constraint bs_resolutions_cash_claim_contract_v2619c;

create function erp.guard_bs_resolution_claim_state_v2619c()
returns trigger
language plpgsql
set search_path=''
as $function$
declare
  v_status text;
begin
  if new.resolution_type='CASH_COMPENSATION' then
    select c.status into v_status
    from erp.laundry_claims c
    where c.id=new.source_laundry_claim_id
    for update;
    if v_status is distinct from 'SETTLED' then
      raise exception using
        errcode='23514',
        message='BS_CASH_COMPENSATION_REQUIRES_ACTIVE_SETTLED_CLAIM';
    end if;
  end if;
  return new;
end
$function$;

create function erp.guard_laundry_claim_bs_dependency_v2619c()
returns trigger
language plpgsql
set search_path=''
as $function$
declare
  v_leaves_settled boolean;
begin
  if tg_op='DELETE' then
    v_leaves_settled:=old.status='SETTLED';
  else
    v_leaves_settled:=old.status='SETTLED' and new.status is distinct from 'SETTLED';
  end if;
  if v_leaves_settled and exists(
    select 1 from erp.bs_resolutions r
    where r.source_laundry_claim_id=old.id
      and r.resolution_type='CASH_COMPENSATION'
  ) then
    raise exception using
      errcode='23503',
      message='CLAIM_RESOLUTION_IN_USE_BY_ACTIVE_BS_CASH_COMPENSATION',
      detail='Reverse the dependent BS CASH_COMPENSATION disposition before reversing or deleting its settled Laundry claim.';
  end if;
  if tg_op='DELETE' then return old; else return new; end if;
end
$function$;

alter function erp.guard_bs_resolution_claim_state_v2619c() owner to postgres;
alter function erp.guard_laundry_claim_bs_dependency_v2619c() owner to postgres;
revoke all on function erp.guard_bs_resolution_claim_state_v2619c()
  from public,anon,authenticated,service_role;
revoke all on function erp.guard_laundry_claim_bs_dependency_v2619c()
  from public,anon,authenticated,service_role;

create trigger trg_00_guard_bs_resolution_claim_state_v2619c
before insert or update of resolution_type,source_laundry_claim_id,compensation_amount
on erp.bs_resolutions
for each row execute function erp.guard_bs_resolution_claim_state_v2619c();

create trigger trg_00_guard_laundry_claim_bs_dependency_v2619c
before update of status or delete
on erp.laundry_claims
for each row execute function erp.guard_laundry_claim_bs_dependency_v2619c();

create or replace function erp.reverse_laundry_claim_resolution(p_claim_id uuid,p_reason text)
returns void
language plpgsql
security definer
set search_path=''
as $function$
declare
  c erp.laundry_claims%rowtype;
  v_journal uuid;
  v_po uuid;
  v_po_status text;
begin
  perform erp.require_owner_admin();
  if nullif(pg_catalog.btrim(p_reason),'') is null then
    raise exception 'Alasan pembatalan resolusi claim laundry wajib diisi';
  end if;

  -- CASH_COMPENSATION creators lock this same claim row before inserting.
  -- Therefore the dependency check and creation serialize in both orders.
  select * into c from erp.laundry_claims where id=p_claim_id for update;
  if c.id is null then raise exception 'Laundry claim tidak ditemukan'; end if;
  if c.status='REJECTED' then return; end if;
  if c.status not in('SETTLED','WRITTEN_OFF') then
    raise exception 'Hanya claim yang sudah SETTLED/WRITTEN_OFF yang dapat dibatalkan resolusinya';
  end if;
  if exists(
    select 1 from erp.bs_resolutions r
    where r.source_laundry_claim_id=c.id
      and r.resolution_type='CASH_COMPENSATION'
  ) then
    raise exception using
      errcode='23503',
      message='CLAIM_RESOLUTION_IN_USE_BY_ACTIVE_BS_CASH_COMPENSATION',
      detail='Reverse the dependent BS CASH_COMPENSATION disposition first; claim money and BS status cannot diverge.';
  end if;

  select je.id into v_journal
  from erp.journal_entries je
  where je.source_type='LAUNDRY_CLAIM_SETTLEMENT'
    and je.source_id=c.id and je.status='POSTED'
  order by je.posting_at desc,je.id desc limit 1;

  if c.status='SETTLED' and c.compensation_amount>0 and v_journal is null then
    raise exception 'Jurnal settlement claim tidak ditemukan; pembatalan dihentikan agar AP vendor tidak rusak';
  end if;
  if v_journal is not null then perform erp.reverse_journal(v_journal,p_reason); end if;

  if c.delivery_id is not null and c.claim_type in('MISSING','STUCK') then
    select ld.po_id into v_po from erp.laundry_deliveries ld where ld.id=c.delivery_id;
    if v_po is not null then
      select po.status into v_po_status
      from erp.production_orders po where po.id=v_po for update;
      if v_po_status='FINISHED' then
        perform erp.reopen_production_order(v_po,'Laundry claim resolution reversed: '||p_reason);
        update erp.production_orders
        set status='LAUNDRY',current_stage='LAUNDRY',updated_at=now()
        where id=v_po;
      end if;
    end if;
  end if;

  update erp.laundry_claims
  set status='REJECTED',
      notes=pg_catalog.concat_ws(E'\n',notes,'Resolution reversed/cancelled: '||p_reason)
  where id=c.id;

  insert into erp.audit_logs(entity_type,entity_id,action,new_data,changed_by,change_reason)
  values('laundry_claims',c.id,'REVERSE',jsonb_build_object(
    'previous_status',c.status,
    'new_status','REJECTED',
    'settlement_journal_reversed',v_journal is not null,
    'finished_po_reopened',v_po_status='FINISHED'
  ),erp.current_app_user_id(),p_reason);
end
$function$;

alter function erp.reverse_laundry_claim_resolution(uuid,text) owner to postgres;
revoke all on function erp.reverse_laundry_claim_resolution(uuid,text)
  from public,anon,authenticated,service_role;
comment on function erp.reverse_laundry_claim_resolution(uuid,text) is
  'CP5 v2.6.19c: refuses claim reversal while an active BS CASH_COMPENSATION disposition depends on it; serialized by the claim row lock.';

update erp.bs_resolution_v2619c_rollback_capsule c
set installed_definition_sha256=encode(extensions.digest(
  convert_to(pg_get_functiondef(to_regprocedure(c.function_regprocedure)),'UTF8'),'sha256'
),'hex');

do $post_guard$
declare
  v_constraint text;
begin
  if (select count(*) from erp.bs_resolution_v2619c_rollback_capsule)<>1
     or exists(
       select 1 from erp.bs_resolution_v2619c_rollback_capsule c
       where c.definition_sha256 is distinct from encode(extensions.digest(
         convert_to(c.function_definition,'UTF8'),'sha256'
       ),'hex')
          or c.installed_definition_sha256 is null
          or c.installed_definition_sha256 is distinct from encode(extensions.digest(
            convert_to(pg_get_functiondef(to_regprocedure(c.function_regprocedure)),'UTF8'),'sha256'
          ),'hex')
     ) then
    raise exception 'ERP v2.6.19c post guard: rollback capsule drift';
  end if;
  select pg_get_constraintdef(oid,true) into v_constraint
  from pg_constraint
  where conrelid='erp.bs_resolutions'::regclass
    and conname='bs_resolutions_cash_claim_contract_v2619c'
    and convalidated;
  if v_constraint is null
     or v_constraint not like '%CASH_COMPENSATION%source_laundry_claim_id IS NOT NULL%compensation_amount >%'
     or not exists(
       select 1 from pg_trigger
       where tgrelid='erp.bs_resolutions'::regclass
         and tgname='trg_00_guard_bs_resolution_claim_state_v2619c'
         and tgenabled<>'D' and not tgisinternal
     )
     or not exists(
       select 1 from pg_trigger
       where tgrelid='erp.laundry_claims'::regclass
         and tgname='trg_00_guard_laundry_claim_bs_dependency_v2619c'
         and tgenabled<>'D' and not tgisinternal
     ) then
    raise exception 'ERP v2.6.19c post guard: cross-ledger invariant is incomplete';
  end if;
  if pg_get_functiondef('erp.reverse_laundry_claim_resolution(uuid,text)'::regprocedure)
       not like '%CLAIM_RESOLUTION_IN_USE_BY_ACTIVE_BS_CASH_COMPENSATION%'
     or not coalesce((
       select p.prosecdef
         and pg_get_userbyid(p.proowner)='postgres'
         and coalesce(p.proconfig,array[]::text[])@>array['search_path=""']::text[]
       from pg_proc p
       where p.oid='erp.reverse_laundry_claim_resolution(uuid,text)'::regprocedure
     ),false)
     or has_function_privilege('authenticated','erp.reverse_laundry_claim_resolution(uuid,text)','EXECUTE')
     or has_function_privilege('anon','erp.reverse_laundry_claim_resolution(uuid,text)','EXECUTE') then
    raise exception 'ERP v2.6.19c post guard: reversal function security/lineage contract failed';
  end if;
  if exists(
    select 1
    from erp.bs_resolutions r
    left join erp.laundry_claims c on c.id=r.source_laundry_claim_id
    where r.resolution_type='CASH_COMPENSATION'
      and(
        r.source_laundry_claim_id is null
        or r.compensation_amount is null
        or r.compensation_amount<=0
        or c.status is distinct from 'SETTLED'
      )
  ) then
    raise exception 'ERP v2.6.19c post guard: contradictory claim/BS state remains';
  end if;
end
$post_guard$;

insert into erp.schema_migrations(version,description)
values(
  'v2.6.19c',
  'CP5 atomic reversal closure: claim-to-BS cash dependency invariant, shared row-lock serialization, durable browser ambiguity reconciliation, and statement-digest-bound rollback'
);

select pg_notify('pgrst','reload schema');
commit;
