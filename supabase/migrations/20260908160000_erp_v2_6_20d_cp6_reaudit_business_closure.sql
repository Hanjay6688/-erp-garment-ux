-- ERP Garment v2.6.20d / CP6 independent re-audit business closure.
--
-- Reliable data adalah DEWA. Keuangan termasuk laporan, stok, dan HPP adalah RAJA.
-- Forward-only: preserve every recorded migration and posted business fact.

begin;
set local lock_timeout='10s';
set local statement_timeout='240s';

lock table erp.schema_migrations,
  supabase_migrations.schema_migrations,
  erp.audit_logs,
  erp.journal_entries,
  erp.journal_lines,
  erp.fg_lots,
  erp.fg_stock_movements,
  erp.hpp_versions,
  erp.hpp_version_components,
  erp.po_hpp_gl_events,
  erp.po_hpp_gl_state,
  erp.po_wip_close_events,
  erp.sales_headers,
  erp.sales_items,
  erp.sale_stock_allocations,
  erp.sales_returns,
  erp.sales_return_items,
  erp.laundry_deliveries,
  erp.laundry_delivery_lines,
  erp.laundry_delivery_batch_size_lines,
  erp.laundry_receipts,
  erp.laundry_receipt_lines,
  erp.laundry_receipt_batch_size_lines,
  erp.laundry_failed_wash_attempts,
  erp.laundry_failed_wash_batch_size_lines
in share row exclusive mode;

do $guard$
declare
  r record;
  v_actual text;
  v_platform_match_count integer;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20c') then
    raise exception 'ERP v2.6.20d requires immutable v2.6.20c first';
  end if;
  if exists(select 1 from erp.schema_migrations where version='v2.6.20d') then
    raise exception 'ERP v2.6.20d is already recorded; never replay or edit a recorded migration';
  end if;
  if to_regclass('erp.cp6_v2620d_rollback_capsule') is not null
     or to_regclass('erp.laundry_redispatch_participant_allocations') is not null
     or to_regprocedure('erp.allocate_laundry_redispatch_participants_v2620d(uuid)') is not null
     or to_regprocedure('erp.guard_laundry_redispatch_participant_v2620d()') is not null
     or to_regprocedure('erp.cp6_lot_failed_wash_cost_v2620d(uuid)') is not null
     or to_regprocedure('erp.compute_po_hpp_gl_targets_v2620d(uuid)') is not null
     or to_regprocedure('erp.sale_lifecycle_po_hpp_amount_v2620d(uuid,uuid)') is not null
     or to_regprocedure('erp.compute_po_hpp_gl_book_v2620d(uuid)') is not null
     or to_regprocedure('erp.assert_po_hpp_target_book_v2620d(uuid)') is not null then
    raise exception 'ERP v2.6.20d target guard: prior repair residue exists';
  end if;
  if exists(select 1 from erp.cp6_laundry_qc_execution_context) then
    raise exception 'ERP v2.6.20d refuses installation while a CP6 execution context exists';
  end if;

  select count(*) into v_platform_match_count
  from supabase_migrations.schema_migrations m
  where m.name='erp_v2_6_20c_cp6_deep_business_reliability'
    and coalesce(encode(extensions.digest(
      convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'
    ),'hex'),'') in(
      '1571c09b7a36c2bed7eee35c5c964e5d0a36b1cae08c58e0c74d028911430250',
      'b90cd6c4aa535eb97226d001fdfb5a5bfed783be28ef38dc7c121a7020368aba'
    );
  if v_platform_match_count<>1 then
    raise exception 'ERP v2.6.20d requires one exact v2.6.20c platform-ledger row; found %',
      v_platform_match_count;
  end if;

  -- Runtime hashes are pg_get_functiondef() bytes from the independently
  -- reproduced v2.6.20c boundary, not hashes copied from source text.
  for r in select * from (values
    ('erp.save_laundry_qc_action_v1(text,jsonb,uuid,bigint)','7f6b360a18c0194e7c2cca324e890bbf3326654e2ab216ac6832188b51aa32c3'),
    ('erp.rebuild_po_hpp(uuid,text)','ecae98d5f25ac93ea7a5f74a4700b91912cf4c9aa35869a35964125ee2c46244'),
    ('erp.compute_po_hpp_gl_targets(uuid)','3141556f4ac3d68bc55ca2f25182a41ec7d4e7565e5b12daffb38e53dffdf018'),
    ('erp.refresh_po_hpp_gl_baseline(uuid)','5dad63c848cf428b6e68681cb72affdd1faaffbe7115064b4e830989379af6e4'),
    ('erp.sync_po_hpp_to_gl(uuid,date)','d74d22f71936115cfc7386edfd6fc9247dc7ce0cb6c7ffa6ef6cf3e354321c1f'),
    ('erp.post_sale(uuid)','2104193b9d9f14f5ea92e253ab35f22e58444fab2e0776ebf1ebe8878a9ddd4b'),
    ('erp.post_sales_return(uuid)','e500ead356fa47a31e4a8d9d6fbe8a89167a41554890aa235250268b2ae5e6c6'),
    ('erp.reverse_sale(uuid,text)','af2e2b72311afed61bfdd6a632408feda4e47443c53dabf29215c06ebe997bbb'),
    ('erp.reverse_sales_return(uuid,text)','32e6241dafc270c1040a372ce6fd4fe3697ab59cdac3bc1e632a18124b5876cf'),
    ('erp.run_v268_financial_report_checks()','0128d7d11ca0dcc10c303a6ad2c7b6b4ecc7215133a2d9a0d6dfec80642eec04'),
    ('erp.get_owner_financial_snapshot_v2(date,date,date)','cdf3bc3f60fa34346e0c441bb0982373e08714aaf15f44f1b163e15ac2a27845')
  ) expected(object_identity,sha256)
  loop
    if to_regprocedure(r.object_identity) is null then
      raise exception 'ERP v2.6.20d predecessor function is missing: %',r.object_identity;
    end if;
    select encode(extensions.digest(convert_to(
      pg_get_functiondef(to_regprocedure(r.object_identity)),'UTF8'
    ),'sha256'),'hex') into v_actual;
    if v_actual is distinct from r.sha256 then
      raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: % changed (%)',r.object_identity,v_actual;
    end if;
  end loop;
end
$guard$;

create table erp.cp6_v2620d_rollback_capsule(
  object_identity text primary key,
  object_regidentity text not null unique,
  object_definition text not null,
  definition_sha256 text not null,
  installed_definition_sha256 text,
  acl_snapshot text[],
  owner_snapshot text not null,
  captured_at timestamptz not null default clock_timestamp()
);
alter table erp.cp6_v2620d_rollback_capsule enable row level security;
revoke all on table erp.cp6_v2620d_rollback_capsule
  from public,anon,authenticated,service_role;

insert into erp.cp6_v2620d_rollback_capsule(
  object_identity,object_regidentity,object_definition,definition_sha256,
  acl_snapshot,owner_snapshot
)
select
  format('%I.%I(%s)',n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)),
  p.oid::regprocedure::text,
  pg_get_functiondef(p.oid),
  encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
  case when p.proacl is null then null else array(
    select a::text from unnest(p.proacl) a order by a::text
  ) end,
  pg_get_userbyid(p.proowner)
from pg_proc p join pg_namespace n on n.oid=p.pronamespace
where p.oid in(
  'erp.save_laundry_qc_action_v1(text,jsonb,uuid,bigint)'::regprocedure,
  'erp.rebuild_po_hpp(uuid,text)'::regprocedure,
  'erp.refresh_po_hpp_gl_baseline(uuid)'::regprocedure,
  'erp.sync_po_hpp_to_gl(uuid,date)'::regprocedure,
  'erp.post_sale(uuid)'::regprocedure,
  'erp.post_sales_return(uuid)'::regprocedure,
  'erp.reverse_sale(uuid,text)'::regprocedure,
  'erp.reverse_sales_return(uuid,text)'::regprocedure,
  'erp.run_v268_financial_report_checks()'::regprocedure,
  'erp.get_owner_financial_snapshot_v2(date,date,date)'::regprocedure
);

do $capsule_guard$
begin
  if (select count(*) from erp.cp6_v2620d_rollback_capsule)<>10
     or exists(
       select 1 from erp.cp6_v2620d_rollback_capsule c
       where c.definition_sha256 is distinct from encode(extensions.digest(
         convert_to(c.object_definition,'UTF8'),'sha256'
       ),'hex')
     ) then
    raise exception 'ERP v2.6.20d exact rollback capsule is incomplete or corrupt';
  end if;
end
$capsule_guard$;

-- A physical participant that comes back unprocessed may move through a new
-- delivery document. Preserve the exact source/destination interval instead
-- of trying to infer cost ownership from the new document UUID later.
create table erp.laundry_redispatch_participant_allocations(
  id uuid primary key default gen_random_uuid(),
  source_delivery_batch_size_line_id uuid not null
    references erp.laundry_delivery_batch_size_lines(id) on delete restrict,
  successor_delivery_batch_size_line_id uuid not null
    references erp.laundry_delivery_batch_size_lines(id) on delete restrict,
  source_offset_pcs integer not null check(source_offset_pcs>=0),
  successor_offset_pcs integer not null check(successor_offset_pcs>=0),
  qty_pcs integer not null check(qty_pcs>0),
  allocation_basis text not null default 'LIVE_FIFO'
    check(allocation_basis in('MIGRATION_BACKFILL','LIVE_FIFO')),
  created_by uuid not null references erp.app_users(id) on delete restrict,
  created_at timestamptz not null default clock_timestamp(),
  check(source_delivery_batch_size_line_id<>successor_delivery_batch_size_line_id),
  unique(source_delivery_batch_size_line_id,source_offset_pcs),
  unique(successor_delivery_batch_size_line_id,successor_offset_pcs)
);
create index idx_laundry_redispatch_successor_v2620d
  on erp.laundry_redispatch_participant_allocations(
    successor_delivery_batch_size_line_id,successor_offset_pcs,id
  );
create index idx_laundry_redispatch_source_v2620d
  on erp.laundry_redispatch_participant_allocations(
    source_delivery_batch_size_line_id,source_offset_pcs,id
  );
alter table erp.laundry_redispatch_participant_allocations enable row level security;
revoke all on table erp.laundry_redispatch_participant_allocations
  from public,anon,authenticated,service_role;

create function erp.guard_laundry_redispatch_participant_v2620d()
returns trigger
language plpgsql
security definer
set search_path=''
as $function$
declare
  v_source record;
  v_successor record;
  v_source_return_at timestamptz;
  v_source_allocated integer;
  v_successor_allocated integer;
begin
  perform erp.require_internal();
  if tg_op<>'INSERT' then
    raise exception using errcode='42501',
      message='REDISPATCH_PARTICIPANT_LINEAGE_IS_APPEND_ONLY';
  end if;

  select sx.*,dl.cutting_group_id,d.id delivery_id,d.status delivery_status,
    d.physical_at delivery_at,d.created_at delivery_created_at
  into v_source
  from erp.laundry_delivery_batch_size_lines sx
  join erp.laundry_delivery_lines dl on dl.id=sx.delivery_line_id
  join erp.laundry_deliveries d on d.id=dl.delivery_id
  where sx.id=new.source_delivery_batch_size_line_id
  for update of sx,d;
  select sx.*,dl.cutting_group_id,d.id delivery_id,d.status delivery_status,
    d.physical_at delivery_at,d.created_at delivery_created_at
  into v_successor
  from erp.laundry_delivery_batch_size_lines sx
  join erp.laundry_delivery_lines dl on dl.id=sx.delivery_line_id
  join erp.laundry_deliveries d on d.id=dl.delivery_id
  where sx.id=new.successor_delivery_batch_size_line_id
  for update of sx,d;

  select min(r.physical_at) into v_source_return_at
  from erp.laundry_failed_wash_attempts a
  join erp.laundry_failed_wash_batch_size_lines ax
    on ax.attempt_id=a.id
   and ax.delivery_batch_size_line_id=v_source.id
  join erp.laundry_receipts r on r.id=a.receipt_id and r.status='POSTED'
  where a.delivery_id=v_source.delivery_id
    and a.custody_outcome='RETURN_UNPROCESSED'
    and ax.qty_attempted_pcs=v_source.qty_sent_pcs;
  select coalesce(sum(a.qty_pcs),0)::integer into v_source_allocated
  from erp.laundry_redispatch_participant_allocations a
  where a.source_delivery_batch_size_line_id=v_source.id;
  select coalesce(sum(a.qty_pcs),0)::integer into v_successor_allocated
  from erp.laundry_redispatch_participant_allocations a
  where a.successor_delivery_batch_size_line_id=v_successor.id;

  if v_source.id is null or v_successor.id is null
     or v_source.distribution_batch_id<>v_successor.distribution_batch_id
     or v_source.size_id<>v_successor.size_id
     or v_source.cutting_group_id<>v_successor.cutting_group_id
     or v_source.delivery_status<>'REVERSED'
     or v_successor.delivery_status<>'DRAFT'
     or v_source_return_at is null
     or v_source_return_at>v_successor.delivery_at
     or (v_source.delivery_at,v_source.delivery_created_at,v_source.delivery_id)
        >=(v_successor.delivery_at,v_successor.delivery_created_at,v_successor.delivery_id)
     or new.source_offset_pcs+new.qty_pcs>v_source.qty_sent_pcs
     or new.successor_offset_pcs+new.qty_pcs>v_successor.qty_sent_pcs
     or new.source_offset_pcs is distinct from v_source_allocated
     or new.successor_offset_pcs is distinct from v_successor_allocated
     or new.allocation_basis<>'LIVE_FIFO'
     or new.created_by is distinct from erp.current_app_user_id()
     then
    raise exception 'Redispatch participant allocation requires one exact returned source interval and a same-source Draft successor';
  end if;
  if exists(
       select 1 from erp.laundry_redispatch_participant_allocations a
       where a.source_delivery_batch_size_line_id=new.source_delivery_batch_size_line_id
         and int4range(a.source_offset_pcs,a.source_offset_pcs+a.qty_pcs,'[)')
             && int4range(new.source_offset_pcs,new.source_offset_pcs+new.qty_pcs,'[)')
     ) or exists(
       select 1 from erp.laundry_redispatch_participant_allocations a
       where a.successor_delivery_batch_size_line_id=new.successor_delivery_batch_size_line_id
         and int4range(a.successor_offset_pcs,a.successor_offset_pcs+a.qty_pcs,'[)')
             && int4range(new.successor_offset_pcs,new.successor_offset_pcs+new.qty_pcs,'[)')
     ) then
    raise exception 'Redispatch participant intervals may not overlap';
  end if;
  return new;
end
$function$;
alter function erp.guard_laundry_redispatch_participant_v2620d() owner to postgres;
revoke all on function erp.guard_laundry_redispatch_participant_v2620d()
  from public,anon,authenticated,service_role;

-- Reconstruct earlier return -> redispatch chains from immutable custody facts
-- using the same oldest-returned-participant-first policy as future writes.
-- The table is still trigger-free here so already-posted successor documents
-- can be derived without weakening the live DRAFT-only guard below.
do $backfill_redispatch_participants_v2620d$
declare
  d record;
  s record;
  v_remaining integer;
  v_take integer;
  v_successor_offset integer;
begin
  for d in
    select sx.*,dl.cutting_group_id successor_group_id,
      ld.id successor_delivery_id,ld.physical_at successor_at,
      ld.created_at successor_created_at,ld.created_by
    from erp.laundry_delivery_batch_size_lines sx
    join erp.laundry_delivery_lines dl on dl.id=sx.delivery_line_id
    join erp.laundry_deliveries ld on ld.id=dl.delivery_id
    order by ld.physical_at,ld.created_at,ld.id,sx.size_id,sx.id
  loop
    v_remaining:=d.qty_sent_pcs;
    v_successor_offset:=0;
    for s in
      select sx.id,sx.qty_sent_pcs,returned.return_at,returned.attempt_id,
        coalesce((select sum(a.qty_pcs)
          from erp.laundry_redispatch_participant_allocations a
          where a.source_delivery_batch_size_line_id=sx.id),0)::integer allocated_qty
      from erp.laundry_delivery_batch_size_lines sx
      join erp.laundry_delivery_lines dl on dl.id=sx.delivery_line_id
      join erp.laundry_deliveries ld on ld.id=dl.delivery_id and ld.status='REVERSED'
      join lateral(
        select fr.physical_at return_at,fa.id attempt_id
        from erp.laundry_failed_wash_attempts fa
        join erp.laundry_failed_wash_batch_size_lines fx
          on fx.attempt_id=fa.id and fx.delivery_batch_size_line_id=sx.id
         and fx.qty_attempted_pcs=sx.qty_sent_pcs
        join erp.laundry_receipts fr on fr.id=fa.receipt_id and fr.status='POSTED'
        where fa.delivery_id=ld.id and fa.custody_outcome='RETURN_UNPROCESSED'
        order by fr.physical_at,fa.id limit 1
      ) returned on returned.return_at<=d.successor_at
      where sx.id<>d.id
        and (ld.physical_at,ld.created_at,ld.id)
            <(d.successor_at,d.successor_created_at,d.successor_delivery_id)
        and sx.distribution_batch_id=d.distribution_batch_id
        and sx.size_id=d.size_id
        and dl.cutting_group_id=d.successor_group_id
        and sx.qty_sent_pcs>coalesce((select sum(a.qty_pcs)
          from erp.laundry_redispatch_participant_allocations a
          where a.source_delivery_batch_size_line_id=sx.id),0)
      order by returned.return_at,returned.attempt_id,sx.id
    loop
      exit when v_remaining<=0;
      v_take:=least(v_remaining,s.qty_sent_pcs-s.allocated_qty);
      insert into erp.laundry_redispatch_participant_allocations(
        source_delivery_batch_size_line_id,successor_delivery_batch_size_line_id,
        source_offset_pcs,successor_offset_pcs,qty_pcs,allocation_basis,created_by
      ) values(
        s.id,d.id,s.allocated_qty,v_successor_offset,v_take,
        'MIGRATION_BACKFILL',d.created_by
      );
      v_remaining:=v_remaining-v_take;
      v_successor_offset:=v_successor_offset+v_take;
    end loop;
  end loop;
end
$backfill_redispatch_participants_v2620d$;

create trigger trg_guard_laundry_redispatch_participant_v2620d
before insert or update or delete on erp.laundry_redispatch_participant_allocations
for each row execute function erp.guard_laundry_redispatch_participant_v2620d();
create trigger trg_audit_laundry_redispatch_participant_v2620d
after insert on erp.laundry_redispatch_participant_allocations
for each row execute function erp.audit_row_change();

create function erp.allocate_laundry_redispatch_participants_v2620d(p_delivery_line_id uuid)
returns void
language plpgsql
security definer
set search_path=''
as $function$
declare
  d record;
  s record;
  v_remaining integer;
  v_take integer;
  v_successor_offset integer;
begin
  perform erp.require_internal();
  for d in
    select sx.*,dl.cutting_group_id successor_group_id,ld.id successor_delivery_id,
      ld.physical_at successor_at,ld.created_at successor_created_at
    from erp.laundry_delivery_batch_size_lines sx
    join erp.laundry_delivery_lines dl on dl.id=sx.delivery_line_id
    join erp.laundry_deliveries ld on ld.id=dl.delivery_id and ld.status='DRAFT'
    where sx.delivery_line_id=p_delivery_line_id
    order by sx.size_id,sx.id
  loop
    perform pg_advisory_xact_lock(hashtextextended(
      'CP6_REDISPATCH_V2620D:'||d.distribution_batch_id::text||':'||d.size_id::text,0
    ));
    v_remaining:=d.qty_sent_pcs;
    v_successor_offset:=0;
    for s in
      select sx.id,sx.qty_sent_pcs,returned.return_at,returned.attempt_id,
        coalesce((select sum(a.qty_pcs)
          from erp.laundry_redispatch_participant_allocations a
          where a.source_delivery_batch_size_line_id=sx.id),0)::integer allocated_qty
      from erp.laundry_delivery_batch_size_lines sx
      join erp.laundry_delivery_lines dl on dl.id=sx.delivery_line_id
      join erp.laundry_deliveries ld on ld.id=dl.delivery_id and ld.status='REVERSED'
      join lateral(
        select fr.physical_at return_at,fa.id attempt_id
        from erp.laundry_failed_wash_attempts fa
        join erp.laundry_failed_wash_batch_size_lines fx
          on fx.attempt_id=fa.id and fx.delivery_batch_size_line_id=sx.id
         and fx.qty_attempted_pcs=sx.qty_sent_pcs
        join erp.laundry_receipts fr on fr.id=fa.receipt_id and fr.status='POSTED'
        where fa.delivery_id=ld.id and fa.custody_outcome='RETURN_UNPROCESSED'
        order by fr.physical_at,fa.id limit 1
      ) returned on returned.return_at<=d.successor_at
      where sx.distribution_batch_id=d.distribution_batch_id
        and (ld.physical_at,ld.created_at,ld.id)
            <(d.successor_at,d.successor_created_at,d.successor_delivery_id)
        and sx.size_id=d.size_id
        and dl.cutting_group_id=d.successor_group_id
        and sx.qty_sent_pcs>coalesce((select sum(a.qty_pcs)
          from erp.laundry_redispatch_participant_allocations a
          where a.source_delivery_batch_size_line_id=sx.id),0)
      order by returned.return_at,returned.attempt_id,sx.id
    loop
      exit when v_remaining<=0;
      v_take:=least(v_remaining,s.qty_sent_pcs-s.allocated_qty);
      insert into erp.laundry_redispatch_participant_allocations(
        source_delivery_batch_size_line_id,successor_delivery_batch_size_line_id,
        source_offset_pcs,successor_offset_pcs,qty_pcs,created_by
      ) values(
        s.id,d.id,s.allocated_qty,v_successor_offset,v_take,erp.current_app_user_id()
      );
      v_remaining:=v_remaining-v_take;
      v_successor_offset:=v_successor_offset+v_take;
    end loop;
  end loop;
end
$function$;
alter function erp.allocate_laundry_redispatch_participants_v2620d(uuid) owner to postgres;
revoke all on function erp.allocate_laundry_redispatch_participants_v2620d(uuid)
  from public,anon,authenticated,service_role;

do $patch_laundry_writer$
declare
  v_definition text;
  v_anchor constant text:='    perform erp.post_laundry_delivery(v_delivery_id);';
  v_replacement constant text:=$replacement$    perform erp.allocate_laundry_redispatch_participants_v2620d(v_delivery_line_id);
    perform erp.post_laundry_delivery(v_delivery_id);$replacement$;
begin
  select pg_get_functiondef('erp.save_laundry_qc_action_v1(text,jsonb,uuid,bigint)'::regprocedure)
    into v_definition;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: POST_DELIVERY redispatch anchor is not exact';
  end if;
  execute replace(v_definition,v_anchor,v_replacement);
end
$patch_laundry_writer$;

-- Resolve every failed-wash cost through immutable participant intervals. A
-- recursive mapping carries the same pieces through any number of full-return
-- redispatch legs while leaving unredispatched cost in WIP.
create function erp.cp6_lot_failed_wash_cost_v2620d(p_lot_id uuid)
returns numeric
language sql
stable
security definer
set search_path=''
as $function$
with recursive lot_source as(
  select fl.initial_qty_pcs::numeric lot_qty,
    rx.delivery_batch_size_line_id final_line_id,
    rx.qty_good_received::numeric+rx.qty_bs_laundry::numeric receipt_qty,
    rh.physical_at receipt_at,rh.id receipt_id,rx.id receipt_batch_size_id,
    sx.qty_sent_pcs::numeric final_line_qty,
    coalesce((
      select sum(px.qty_good_received+px.qty_bs_laundry)::numeric
      from erp.laundry_receipt_batch_size_lines px
      join erp.laundry_receipt_lines pl on pl.id=px.receipt_line_id
      join erp.laundry_receipts ph on ph.id=pl.receipt_id and ph.status='POSTED'
      where px.delivery_batch_size_line_id=rx.delivery_batch_size_line_id
        and (ph.physical_at,ph.id,px.id)<(rh.physical_at,rh.id,rx.id)
    ),0) receipt_start
  from erp.fg_lots fl
  join erp.qc_inspection_items qi on qi.id=fl.qc_item_id
  join erp.laundry_receipt_batch_size_lines rx
    on rx.id=qi.source_laundry_receipt_batch_size_line_id
  join erp.laundry_receipt_lines rl on rl.id=rx.receipt_line_id
    and rl.id=qi.source_laundry_receipt_line_id
  join erp.laundry_receipts rh on rh.id=rl.receipt_id and rh.status='POSTED'
  join erp.laundry_delivery_batch_size_lines sx
    on sx.id=rx.delivery_batch_size_line_id
  where fl.id=p_lot_id and fl.lot_origin='PRODUCTION'
), participant_map(line_id,line_start,line_end,final_start,final_end,path) as(
  select s.final_line_id,0::numeric,s.final_line_qty,0::numeric,s.final_line_qty,
    array[s.final_line_id]::uuid[]
  from lot_source s
  union all
  select a.source_delivery_batch_size_line_id,
    a.source_offset_pcs::numeric+(o.overlap_start-a.successor_offset_pcs),
    a.source_offset_pcs::numeric+(o.overlap_end-a.successor_offset_pcs),
    m.final_start+(o.overlap_start-m.line_start),
    m.final_start+(o.overlap_end-m.line_start),
    m.path||a.source_delivery_batch_size_line_id
  from participant_map m
  join erp.laundry_redispatch_participant_allocations a
    on a.successor_delivery_batch_size_line_id=m.line_id
  cross join lateral(
    select greatest(m.line_start,a.successor_offset_pcs::numeric) overlap_start,
      least(m.line_end,(a.successor_offset_pcs+a.qty_pcs)::numeric) overlap_end
  ) o
  where o.overlap_end>o.overlap_start
    and not a.source_delivery_batch_size_line_id=any(m.path)
), attempts as(
  select ax.delivery_batch_size_line_id line_id,
    ax.qty_attempted_pcs::numeric attempt_qty,
    coalesce(rl.actual_cost,a.qty_attempted_pcs*coalesce(rl.actual_rate_snapshot,0))
      *(ax.qty_attempted_pcs::numeric/nullif(a.qty_attempted_pcs,0)) size_cost,
    coalesce((
      select sum(px.qty_good_received+px.qty_bs_laundry)::numeric
      from erp.laundry_receipt_batch_size_lines px
      join erp.laundry_receipt_lines pl on pl.id=px.receipt_line_id
      join erp.laundry_receipts ph on ph.id=pl.receipt_id and ph.status='POSTED'
      where px.delivery_batch_size_line_id=ax.delivery_batch_size_line_id
        and (ph.physical_at,ph.id)<(ah.physical_at,ah.id)
    ),0) attempt_start
  from erp.laundry_failed_wash_batch_size_lines ax
  join erp.laundry_failed_wash_attempts a on a.id=ax.attempt_id
  join erp.laundry_receipt_lines rl on rl.id=a.receipt_line_id
    and rl.actual_cost_status in('ESTIMATED','FINAL')
  join erp.laundry_receipts ah on ah.id=a.receipt_id and ah.status='POSTED'
), mapped_attempts as(
  select
    m.final_start+(greatest(m.line_start,a.attempt_start)-m.line_start) attempt_final_start,
    m.final_start+(least(m.line_end,a.attempt_start+a.attempt_qty)-m.line_start) attempt_final_end,
    a.size_cost/nullif(a.attempt_qty,0) cost_per_participant
  from participant_map m join attempts a on a.line_id=m.line_id
  where least(m.line_end,a.attempt_start+a.attempt_qty)>greatest(m.line_start,a.attempt_start)
)
select coalesce(sum(
  greatest(least(s.receipt_start+s.receipt_qty,a.attempt_final_end)
    -greatest(s.receipt_start,a.attempt_final_start),0)
  *a.cost_per_participant*s.lot_qty/nullif(s.receipt_qty,0)
),0)::numeric
from lot_source s left join mapped_attempts a on true
$function$;
alter function erp.cp6_lot_failed_wash_cost_v2620d(uuid) owner to postgres;
revoke all on function erp.cp6_lot_failed_wash_cost_v2620d(uuid)
  from public,anon,authenticated,service_role;

do $patch_hpp_redispatch_cost$
declare
  v_definition text;
  v_anchor constant text:='erp.cp6_lot_failed_wash_cost_v2620c(r.id)';
  v_replacement constant text:='erp.cp6_lot_failed_wash_cost_v2620d(r.id)';
begin
  select pg_get_functiondef('erp.rebuild_po_hpp(uuid,text)'::regprocedure)
    into v_definition;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: failed-wash resolver anchor is not exact';
  end if;
  execute replace(v_definition,v_anchor,v_replacement);
end
$patch_hpp_redispatch_cost$;

-- Allocate one conserved minor-unit total. COGS receives the first cumulative
-- slice, genuine non-sale disposition receives the delta from total rounded
-- outflow, and FG receives the final deterministic remainder. This prevents
-- any two independently rounded buckets from manufacturing a one-cent
-- gain/loss or a negative FG value when physical stock is exactly zero.
create function erp.compute_po_hpp_gl_targets_v2620d(p_po_id uuid)
returns table(
  base_output_qty integer,hpp_total_cost numeric,fg_value numeric,
  cogs_value numeric,other_out_value numeric
)
language sql
stable
security definer
set search_path=''
as $function$
with raw as(
  select * from erp.compute_po_hpp_gl_targets(p_po_id)
), cents as(
  select
    coalesce(base_output_qty,0)::integer qty,
    round(coalesce(hpp_total_cost,0),2)::numeric hpp,
    round(coalesce(cogs_value,0),2)::numeric cogs,
    round(coalesce(cogs_value,0)+coalesce(other_out_value,0),2)::numeric total_out
  from raw
)
select qty,hpp,(hpp-total_out)::numeric,cogs,(total_out-cogs)::numeric
from cents
$function$;
alter function erp.compute_po_hpp_gl_targets_v2620d(uuid) owner to postgres;
revoke all on function erp.compute_po_hpp_gl_targets_v2620d(uuid)
  from public,anon,authenticated,service_role;

-- Every existing recost path must use the same conserved target allocator as
-- Sale/return posting. The predecessor text is guarded above and the exact
-- original definition is held in the rollback capsule.
do $patch_hpp_sync_target_v2620d$
declare
  v_definition text;
  v_anchor constant text:='erp.compute_po_hpp_gl_targets(p_po_id)';
  v_replacement constant text:='erp.compute_po_hpp_gl_targets_v2620d(p_po_id)';
begin
  select pg_get_functiondef('erp.sync_po_hpp_to_gl(uuid,date)'::regprocedure)
    into v_definition;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: HPP sync target anchor is not exact';
  end if;
  execute replace(v_definition,v_anchor,v_replacement);
end
$patch_hpp_sync_target_v2620d$;

-- Attribute the actual two-decimal COGS line of one Sale lifecycle journal to
-- a PO. New journals carry po_id directly. Historical untagged journals use a
-- deterministic cumulative allocation whose PO slices always sum to the
-- exact amount that was posted, never to independently rounded estimates.
create function erp.sale_lifecycle_po_hpp_amount_v2620d(
  p_journal_id uuid,p_po_id uuid
)
returns numeric
language plpgsql
stable
security definer
set search_path=''
as $function$
declare
  v_origin_type text;
  v_origin_id uuid;
  v_book numeric(20,2):=0;
  v_fg_book numeric(20,2):=0;
  v_po_book numeric(20,2):=0;
  v_po_fg_book numeric(20,2):=0;
  v_tagged integer:=0;
  v_untagged integer:=0;
  v_raw_total numeric:=0;
  v_result numeric(20,2):=0;
begin
  select coalesce(o.source_type,e.source_type),coalesce(o.source_id,e.source_id)
  into v_origin_type,v_origin_id
  from erp.journal_entries e
  left join erp.journal_entries o on o.id=e.reversal_of_id
  where e.id=p_journal_id and(
    e.source_type in('SALE','SALES_RETURN')
    or(e.source_type='JOURNAL_REVERSAL' and o.source_type in('SALE','SALES_RETURN'))
  );
  if v_origin_type is null then
    return null;
  end if;

  select
    coalesce(sum(l.debit-l.credit) filter(where l.account_id=erp.account_id('COGS')),0),
    coalesce(sum(l.debit-l.credit) filter(where l.account_id=erp.account_id('FG_INVENTORY')),0),
    count(*) filter(where l.account_id=erp.account_id('COGS') and l.po_id is not null),
    count(*) filter(where l.account_id=erp.account_id('COGS') and l.po_id is null)
  into v_book,v_fg_book,v_tagged,v_untagged
  from erp.journal_lines l where l.journal_entry_id=p_journal_id;
  if abs(v_book+v_fg_book)>0.005 then
    return null;
  end if;
  if abs(v_book)<=0.005 then return 0; end if;
  if v_tagged>0 and v_untagged>0 then
    return null;
  end if;

  if v_tagged>0 then
    select coalesce(sum(l.debit-l.credit),0) into v_po_book
    from erp.journal_lines l
    where l.journal_entry_id=p_journal_id and l.po_id=p_po_id
      and l.account_id=erp.account_id('COGS');
    select coalesce(sum(l.debit-l.credit),0) into v_po_fg_book
    from erp.journal_lines l
    where l.journal_entry_id=p_journal_id and l.po_id=p_po_id
      and l.account_id=erp.account_id('FG_INVENTORY');
    if abs(v_po_book+v_po_fg_book)>0.005 then
      return null;
    end if;
    return round(v_po_book,2);
  end if;

  if v_origin_type='SALE' then
    select coalesce(sum(a.qty_pcs*a.unit_hpp_snapshot),0) into v_raw_total
    from erp.sale_stock_allocations a
    join erp.sales_items i on i.id=a.sale_item_id
    where i.sale_id=v_origin_id;
    with weights as(
      select fl.po_id,sum(a.qty_pcs*a.unit_hpp_snapshot)::numeric raw_value
      from erp.sale_stock_allocations a
      join erp.sales_items i on i.id=a.sale_item_id
      join erp.fg_lots fl on fl.id=a.lot_id
      where i.sale_id=v_origin_id and fl.po_id is not null
      group by fl.po_id
    ), ordered as(
      select w.*,
        sum(raw_value) over(order by po_id rows unbounded preceding) cumulative_value,
        sum(raw_value) over() total_value
      from weights w
    )
    select round(v_book*cumulative_value/nullif(total_value,0),2)
          -round(v_book*(cumulative_value-raw_value)/nullif(total_value,0),2)
    into v_result from ordered where po_id=p_po_id;
  else
    select coalesce(sum(i.qty_pcs*i.unit_hpp_snapshot),0) into v_raw_total
    from erp.sales_return_items i where i.return_id=v_origin_id;
    with weights as(
      select fl.po_id,sum(i.qty_pcs*i.unit_hpp_snapshot)::numeric raw_value
      from erp.sales_return_items i
      join erp.fg_lots fl on fl.id=i.lot_id
      where i.return_id=v_origin_id and fl.po_id is not null
      group by fl.po_id
    ), ordered as(
      select w.*,
        sum(raw_value) over(order by po_id rows unbounded preceding) cumulative_value,
        sum(raw_value) over() total_value
      from weights w
    )
    select round(v_book*cumulative_value/nullif(total_value,0),2)
          -round(v_book*(cumulative_value-raw_value)/nullif(total_value,0),2)
    into v_result from ordered where po_id=p_po_id;
  end if;
  if v_raw_total<=0 then
    return null;
  end if;
  return coalesce(v_result,0);
end
$function$;
alter function erp.sale_lifecycle_po_hpp_amount_v2620d(uuid,uuid) owner to postgres;
revoke all on function erp.sale_lifecycle_po_hpp_amount_v2620d(uuid,uuid)
  from public,anon,authenticated,service_role;

create function erp.compute_po_hpp_gl_book_v2620d(p_po_id uuid)
returns table(fg_value numeric,cogs_value numeric,other_out_value numeric)
language sql
stable
security definer
set search_path=''
as $function$
with lifecycle as(
  select e.id,coalesce(o.source_type,e.source_type) origin_type,
    coalesce(o.source_id,e.source_id) origin_id
  from erp.journal_entries e
  left join erp.journal_entries o on o.id=e.reversal_of_id
  where e.status in('POSTED','REVERSED') and(
    e.source_type in('SALE','SALES_RETURN')
    or(e.source_type='JOURNAL_REVERSAL' and o.source_type in('SALE','SALES_RETURN'))
  )
), relevant_lifecycle as(
  select l.id
  from lifecycle l
  where (l.origin_type='SALE' and exists(
      select 1
      from erp.sale_stock_allocations a
      join erp.sales_items i on i.id=a.sale_item_id
      join erp.fg_lots fl on fl.id=a.lot_id
      where i.sale_id=l.origin_id and fl.po_id=p_po_id
    )) or(l.origin_type='SALES_RETURN' and exists(
      select 1 from erp.sales_return_items i
      join erp.fg_lots fl on fl.id=i.lot_id
      where i.return_id=l.origin_id and fl.po_id=p_po_id
    ))
), lifecycle_book as(
  select coalesce(sum(erp.sale_lifecycle_po_hpp_amount_v2620d(id,p_po_id)),0)::numeric cogs
  from relevant_lifecycle
), direct_book as(
  select
    coalesce(sum(l.debit-l.credit) filter(
      where l.account_id=erp.account_id('FG_INVENTORY')),0)::numeric fg,
    coalesce(sum(l.debit-l.credit) filter(
      where l.account_id=erp.account_id('COGS')),0)::numeric cogs,
    coalesce(sum(l.debit-l.credit) filter(
      where l.account_id in(erp.account_id('OTHER_EXPENSE'),erp.account_id('OTHER_INCOME'))),0)::numeric other_out
  from erp.journal_lines l
  join erp.journal_entries e on e.id=l.journal_entry_id
    and e.status in('POSTED','REVERSED')
  left join erp.journal_entries o on o.id=e.reversal_of_id
  where l.po_id=p_po_id and not(
    e.source_type in('SALE','SALES_RETURN')
    or(e.source_type='JOURNAL_REVERSAL' and o.source_type in('SALE','SALES_RETURN'))
  )
), residual_close as(
  select coalesce(sum(e.residual_amount),0)::numeric amount
  from erp.po_wip_close_events e
  join erp.journal_entries j on j.id=e.journal_entry_id
    and j.source_type='PO_WIP_RESIDUAL_CLOSE' and j.status='POSTED'
  where e.po_id=p_po_id
)
select round(d.fg-l.cogs,2),round(d.cogs+l.cogs,2),round(d.other_out-c.amount,2)
from direct_book d cross join lifecycle_book l cross join residual_close c
$function$;
alter function erp.compute_po_hpp_gl_book_v2620d(uuid) owner to postgres;
revoke all on function erp.compute_po_hpp_gl_book_v2620d(uuid)
  from public,anon,authenticated,service_role;

create or replace function erp.refresh_po_hpp_gl_baseline(p_po_id uuid)
returns void
language plpgsql
security definer
set search_path=''
as $function$
declare
  t record;
  b record;
  v_hpp numeric(24,6);
begin
  perform erp.require_internal();
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  select * into t from erp.compute_po_hpp_gl_targets_v2620d(p_po_id);
  select * into b from erp.compute_po_hpp_gl_book_v2620d(p_po_id);
  if coalesce(t.base_output_qty,0)<=0
     and not exists(select 1 from erp.po_hpp_gl_state where po_id=p_po_id)
     and abs(coalesce(b.fg_value,0))+abs(coalesce(b.cogs_value,0))
         +abs(coalesce(b.other_out_value,0))<=0.005 then
    return;
  end if;
  v_hpp:=round(coalesce(b.fg_value,0)+coalesce(b.cogs_value,0)+coalesce(b.other_out_value,0),2);
  insert into erp.po_hpp_gl_state(
    po_id,base_output_qty,hpp_total_cost,fg_value,cogs_value,other_out_value,updated_at
  ) values(
    p_po_id,coalesce(t.base_output_qty,0),v_hpp,
    round(coalesce(b.fg_value,0),2),round(coalesce(b.cogs_value,0),2),
    round(coalesce(b.other_out_value,0),2),clock_timestamp()
  )
  on conflict(po_id) do update set
    base_output_qty=excluded.base_output_qty,
    hpp_total_cost=excluded.hpp_total_cost,
    fg_value=excluded.fg_value,cogs_value=excluded.cogs_value,
    other_out_value=excluded.other_out_value,updated_at=excluded.updated_at
  where (erp.po_hpp_gl_state.base_output_qty,
         erp.po_hpp_gl_state.hpp_total_cost,
         erp.po_hpp_gl_state.fg_value,
         erp.po_hpp_gl_state.cogs_value,
         erp.po_hpp_gl_state.other_out_value)
    is distinct from
        (excluded.base_output_qty,excluded.hpp_total_cost,excluded.fg_value,
         excluded.cogs_value,excluded.other_out_value);
end
$function$;
alter function erp.refresh_po_hpp_gl_baseline(uuid) owner to postgres;

create function erp.assert_po_hpp_target_book_v2620d(p_po_id uuid)
returns void
language plpgsql
stable
security definer
set search_path=''
as $function$
declare
  t record;
  b record;
  s erp.po_hpp_gl_state%rowtype;
  v_hpp numeric(24,6);
  v_fg numeric(24,6);
  v_cogs numeric(24,6);
  v_other numeric(24,6);
begin
  perform erp.require_internal();
  select * into t from erp.compute_po_hpp_gl_targets_v2620d(p_po_id);
  select * into b from erp.compute_po_hpp_gl_book_v2620d(p_po_id);
  select * into s from erp.po_hpp_gl_state where po_id=p_po_id;
  v_hpp:=round(coalesce(t.hpp_total_cost,0),2);
  v_fg:=round(coalesce(t.fg_value,0),2);
  v_cogs:=round(coalesce(t.cogs_value,0),2);
  v_other:=v_hpp-v_fg-v_cogs;
  if s.po_id is null
     or s.base_output_qty is distinct from coalesce(t.base_output_qty,0)
     or s.hpp_total_cost is distinct from v_hpp
     or s.fg_value is distinct from v_fg
     or s.cogs_value is distinct from v_cogs
     or s.other_out_value is distinct from v_other
     or s.fg_value is distinct from round(coalesce(b.fg_value,0),2)
     or s.cogs_value is distinct from round(coalesce(b.cogs_value,0),2)
     or s.other_out_value is distinct from round(coalesce(b.other_out_value,0),2) then
    raise exception 'PO_HPP_TARGET_BOOK_MISMATCH_V2620D for PO %',p_po_id;
  end if;
end
$function$;
alter function erp.assert_po_hpp_target_book_v2620d(uuid) owner to postgres;
revoke all on function erp.assert_po_hpp_target_book_v2620d(uuid)
  from public,anon,authenticated,service_role;

-- Sale/return postings now consume the delta between the prior actual book and
-- the new cumulative cent target. The saved baseline is refreshed only after
-- the journal exists, so ten sub-cent allocations cannot strand one cent.
create or replace function erp.post_sale(p_sale_id uuid)
returns void
language plpgsql
security definer
set search_path to 'erp','public','pg_temp'
as $function$
declare
  h erp.sales_headers%rowtype;
  r record;
  v_sales numeric(24,6):=0;
  v_item_qty bigint;
  v_reserved_qty bigint;
  v_delta_cogs numeric(24,6);
  v_delta_fg numeric(24,6);
  v_target_hpp numeric(24,6);
  v_target_other numeric(24,6);
  v_book_hpp numeric(24,6);
  v_book_other numeric(24,6);
  v_lines jsonb:='[]'::jsonb;
begin
  perform erp.require_internal();
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  select * into h from erp.sales_headers where id=p_sale_id for update;
  if h.id is null or h.status<>'DRAFT' then raise exception 'Sale must be DRAFT'; end if;
  if h.source_location_id is null then raise exception 'Sale source FG location is required'; end if;
  if not exists(select 1 from erp.sales_items where sale_id=p_sale_id) then raise exception 'Sale has no items'; end if;

  select coalesce(sum(qty_pcs),0),coalesce(sum(line_total),0)
  into v_item_qty,v_sales from erp.sales_items where sale_id=h.id;
  select coalesce(sum(abs(m.qty_signed)),0) into v_reserved_qty
  from erp.fg_stock_movements m
  join erp.sales_items i on i.id=m.source_id
  where i.sale_id=h.id and m.source_type='SALE_ITEM' and m.movement_type='SALE_RESERVE'
    and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=m.id);

  if v_reserved_qty=0 then v_reserved_qty:=erp._reserve_sale_draft(h.id); end if;
  if v_reserved_qty<>v_item_qty then
    raise exception 'Sale Draft reservation mismatch. Items %, active reservation %',v_item_qty,v_reserved_qty;
  end if;
  if exists(
    select 1 from erp.sales_items i
    left join(select sale_item_id,sum(qty_pcs)::bigint qty_pcs
      from erp.sale_stock_allocations group by sale_item_id) a on a.sale_item_id=i.id
    where i.sale_id=h.id and coalesce(a.qty_pcs,0)<>i.qty_pcs
  ) then raise exception 'Sale allocation does not match Draft line quantity'; end if;

  update erp.sale_stock_allocations a
  set unit_hpp_snapshot=coalesce(erp.lock_current_hpp_per_pcs(a.lot_id),0)
  from erp.sales_items i
  where i.id=a.sale_item_id and i.sale_id=h.id;

  update erp.fg_stock_movements m
  set unit_hpp_snapshot=a.unit_hpp_snapshot
  from erp.sales_items i
  join erp.sale_stock_allocations a on a.sale_item_id=i.id
  where i.id=m.source_id and i.sale_id=h.id
    and a.lot_id=m.lot_id
    and m.source_type='SALE_ITEM' and m.movement_type='SALE_RESERVE'
    and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=m.id);

  update erp.fg_stock_movements m
  set movement_type='SALE',notes='Sale posted · quantity reserved in Draft; HPP frozen at POST'
  from erp.sales_items i
  where i.id=m.source_id and i.sale_id=h.id
    and m.source_type='SALE_ITEM' and m.movement_type='SALE_RESERVE'
    and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=m.id);

  update erp.sales_headers set status='POSTED' where id=h.id;
  if abs(v_sales)>0.005 then
    v_lines:=v_lines||jsonb_build_array(
      jsonb_build_object('mapping_key','AR_CUSTOMER','debit',round(v_sales,2),'credit',0,'customer_id',h.customer_id),
      jsonb_build_object('mapping_key','SALES_REVENUE','debit',0,'credit',round(v_sales,2),'customer_id',h.customer_id));
  end if;

  for r in
    select distinct fl.po_id
    from erp.sale_stock_allocations a
    join erp.sales_items i on i.id=a.sale_item_id
    join erp.fg_lots fl on fl.id=a.lot_id
    where i.sale_id=h.id and fl.po_id is not null
    order by fl.po_id
  loop
    perform erp.refresh_po_hpp_gl_baseline(r.po_id);
    select
      round(coalesce(t.cogs_value,0),2)-s.cogs_value,
      round(coalesce(t.fg_value,0),2)-s.fg_value,
      round(coalesce(t.hpp_total_cost,0),2),
      round(coalesce(t.hpp_total_cost,0),2)-round(coalesce(t.fg_value,0),2)-round(coalesce(t.cogs_value,0),2),
      s.hpp_total_cost,s.other_out_value
    into v_delta_cogs,v_delta_fg,v_target_hpp,v_target_other,v_book_hpp,v_book_other
    from erp.po_hpp_gl_state s
    cross join lateral erp.compute_po_hpp_gl_targets_v2620d(r.po_id) t
    where s.po_id=r.po_id for update of s;
    if v_delta_cogs<-0.005 or v_delta_fg>0.005
       or abs(v_delta_cogs+v_delta_fg)>0.005
       or v_target_hpp is distinct from v_book_hpp
       or v_target_other is distinct from v_book_other then
      raise exception 'Sale cumulative HPP target is not a pure FG-to-COGS movement for PO %. dc %, df %, target/book hpp %/%, target/book other %/%',
        r.po_id,v_delta_cogs,v_delta_fg,v_target_hpp,v_book_hpp,v_target_other,v_book_other;
    end if;
    if abs(v_delta_cogs)>0.005 then
      v_lines:=v_lines||jsonb_build_array(
        jsonb_build_object('mapping_key','COGS','debit',v_delta_cogs,'credit',0,'customer_id',h.customer_id,'po_id',r.po_id),
        jsonb_build_object('mapping_key','FG_INVENTORY','debit',0,'credit',v_delta_cogs,'customer_id',h.customer_id,'po_id',r.po_id));
    end if;
  end loop;
  if jsonb_array_length(v_lines)>=2 then
    perform erp.post_journal('SALE',h.id,h.sale_date::date,
      'Sales to customer/toko · cumulative exact HPP target',v_lines);
  end if;

  for r in
    select distinct fl.po_id
    from erp.sale_stock_allocations a
    join erp.sales_items i on i.id=a.sale_item_id
    join erp.fg_lots fl on fl.id=a.lot_id
    where i.sale_id=h.id and fl.po_id is not null
    order by fl.po_id
  loop
    perform erp.refresh_po_hpp_gl_baseline(r.po_id);
    perform erp.assert_po_hpp_target_book_v2620d(r.po_id);
  end loop;
end
$function$;
alter function erp.post_sale(uuid) owner to postgres;

create or replace function erp.post_sales_return(p_return_id uuid)
returns void
language plpgsql
security definer
set search_path to 'erp','public'
as $function$
declare
  h erp.sales_returns%rowtype;
  s erp.sales_headers%rowtype;
  r record;
  v_refund numeric(24,6):=0;
  v_sold_qty integer;
  v_prior_returned integer;
  v_current_return integer;
  v_product_sale_value numeric(24,6);
  v_prior_product_refund numeric(24,6);
  v_current_product_refund numeric(24,6);
  v_original_hpp numeric(18,6);
  v_unit_hpp numeric(18,6);
  v_net_total numeric(20,2);
  v_paid numeric(20,2);
  v_delta_cogs numeric(24,6);
  v_delta_fg numeric(24,6);
  v_target_hpp numeric(24,6);
  v_target_other numeric(24,6);
  v_book_hpp numeric(24,6);
  v_book_other numeric(24,6);
  v_lines jsonb:='[]'::jsonb;
begin
  perform erp.require_internal();
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  select * into h from erp.sales_returns where id=p_return_id for update;
  if h.id is null or h.status<>'DRAFT' then raise exception 'Sales return must be DRAFT'; end if;
  if h.sale_id is null then raise exception 'Native sales return must reference the original sale'; end if;
  select * into s from erp.sales_headers where id=h.sale_id for update;
  if s.id is null or s.status not in('POSTED','PARTIAL_PAID','PAID') then raise exception 'Original sale must be active/posted'; end if;
  if s.customer_id is distinct from h.customer_id then raise exception 'Sales return customer does not match original sale customer'; end if;
  if not exists(select 1 from erp.sales_return_items where return_id=h.id) then raise exception 'Sales return has no lines'; end if;

  for r in
    select * from erp.sales_return_items where return_id=h.id
    order by product_id,location_id,quality_grade,lot_id,id
  loop
    if r.lot_id is null then raise exception 'Sales return line requires original FG lot'; end if;
    if not exists(select 1 from erp.fg_lots fl where fl.id=r.lot_id and fl.product_id=r.product_id) then raise exception 'Sales return lot does not belong to selected product'; end if;

    insert into erp.fg_inventory_balances(product_id,location_id,quality_grade,cached_qty_pcs)
    values(r.product_id,r.location_id,r.quality_grade,0)
    on conflict(product_id,location_id,quality_grade) do nothing;
    perform 1 from erp.fg_inventory_balances
    where product_id=r.product_id and location_id=r.location_id and quality_grade=r.quality_grade
    for update;
    perform 1 from erp.fg_lots where id=r.lot_id for update;

    select coalesce(sum(a.qty_pcs),0)::integer,
           case when coalesce(sum(a.qty_pcs),0)>0 then sum(a.qty_pcs*a.unit_hpp_snapshot)/sum(a.qty_pcs) else null end
    into v_sold_qty,v_original_hpp
    from erp.sale_stock_allocations a
    join erp.sales_items si on si.id=a.sale_item_id
    where si.sale_id=h.sale_id and si.product_id=r.product_id and a.lot_id=r.lot_id and a.location_id=r.location_id;
    if v_sold_qty<=0 or v_original_hpp is null then raise exception 'Returned product/lot/location was not allocated on the original sale'; end if;

    v_unit_hpp:=coalesce(erp.lock_current_hpp_per_pcs(r.lot_id),v_original_hpp);
    select coalesce(sum(sri.qty_pcs),0)::integer into v_prior_returned
    from erp.sales_return_items sri join erp.sales_returns sr on sr.id=sri.return_id
    where sr.sale_id=h.sale_id and sr.id<>h.id and sr.status='POSTED'
      and sri.product_id=r.product_id and sri.lot_id=r.lot_id and sri.location_id=r.location_id;
    select coalesce(sum(sri.qty_pcs),0)::integer into v_current_return
    from erp.sales_return_items sri
    where sri.return_id=h.id and sri.product_id=r.product_id and sri.lot_id=r.lot_id and sri.location_id=r.location_id;
    if v_prior_returned+v_current_return>v_sold_qty then
      raise exception 'Sales return exceeds quantity originally sold for this lot/location. Sold %, prior returned %, current return %',v_sold_qty,v_prior_returned,v_current_return;
    end if;

    select coalesce(sum(si.line_total),0) into v_product_sale_value
    from erp.sales_items si where si.sale_id=h.sale_id and si.product_id=r.product_id;
    select coalesce(sum(sri.refund_amount),0) into v_prior_product_refund
    from erp.sales_return_items sri join erp.sales_returns sr on sr.id=sri.return_id
    where sr.sale_id=h.sale_id and sr.id<>h.id and sr.status='POSTED' and sri.product_id=r.product_id;
    select coalesce(sum(sri.refund_amount),0) into v_current_product_refund
    from erp.sales_return_items sri where sri.return_id=h.id and sri.product_id=r.product_id;
    if v_prior_product_refund+v_current_product_refund>v_product_sale_value+0.01 then
      raise exception 'Refund exceeds original net sale value for product. Sold value %, prior refund %, current refund %',v_product_sale_value,v_prior_product_refund,v_current_product_refund;
    end if;

    update erp.sales_return_items set unit_hpp_snapshot=v_unit_hpp where id=r.id;
    perform erp.post_fg_movement(r.product_id,r.lot_id,r.location_id,r.quality_grade,
      'SALE_RETURN',r.qty_pcs,v_unit_hpp,h.customer_id,'SALES_RETURN_ITEM',r.id,
      h.physical_at,'Customer sales return',false);
    v_refund:=v_refund+r.refund_amount;
  end loop;

  select greatest(erp.sale_net_total(h.sale_id)-v_refund,0)::numeric(20,2) into v_net_total;
  select coalesce(sum(sp.amount),0)::numeric(20,2) into v_paid
  from erp.sales_payments sp where sp.sale_id=h.sale_id and sp.status='POSTED';
  if v_paid>v_net_total+0.01 then
    raise exception 'Retur ini membuat pembayaran customer melebihi nilai penjualan tersisa. Nilai setelah retur %, sudah dibayar %. Reverse/koreksi pembayaran customer dulu agar kelebihan bayar tidak hilang dari pembukuan.',v_net_total,v_paid;
  end if;

  update erp.sales_returns set status='POSTED' where id=h.id;
  if abs(v_refund)>0.005 then
    v_lines:=v_lines||jsonb_build_array(
      jsonb_build_object('mapping_key','SALES_REVENUE','debit',round(v_refund,2),'credit',0,'customer_id',h.customer_id),
      jsonb_build_object('mapping_key','AR_CUSTOMER','debit',0,'credit',round(v_refund,2),'customer_id',h.customer_id));
  end if;

  for r in
    select distinct fl.po_id
    from erp.sales_return_items i join erp.fg_lots fl on fl.id=i.lot_id
    where i.return_id=h.id and fl.po_id is not null order by fl.po_id
  loop
    perform erp.refresh_po_hpp_gl_baseline(r.po_id);
    select
      round(coalesce(t.cogs_value,0),2)-st.cogs_value,
      round(coalesce(t.fg_value,0),2)-st.fg_value,
      round(coalesce(t.hpp_total_cost,0),2),
      round(coalesce(t.hpp_total_cost,0),2)-round(coalesce(t.fg_value,0),2)-round(coalesce(t.cogs_value,0),2),
      st.hpp_total_cost,st.other_out_value
    into v_delta_cogs,v_delta_fg,v_target_hpp,v_target_other,v_book_hpp,v_book_other
    from erp.po_hpp_gl_state st
    cross join lateral erp.compute_po_hpp_gl_targets_v2620d(r.po_id) t
    where st.po_id=r.po_id for update of st;
    if v_delta_cogs>0.005 or v_delta_fg<-0.005
       or abs(v_delta_cogs+v_delta_fg)>0.005
       or v_target_hpp is distinct from v_book_hpp
       or v_target_other is distinct from v_book_other then
      raise exception 'Sales-return cumulative HPP target is not a pure COGS-to-FG movement for PO %. dc %, df %, target/book hpp %/%, target/book other %/%',
        r.po_id,v_delta_cogs,v_delta_fg,v_target_hpp,v_book_hpp,v_target_other,v_book_other;
    end if;
    if abs(v_delta_cogs)>0.005 then
      v_lines:=v_lines||jsonb_build_array(
        jsonb_build_object('mapping_key','FG_INVENTORY','debit',abs(v_delta_cogs),'credit',0,'customer_id',h.customer_id,'po_id',r.po_id),
        jsonb_build_object('mapping_key','COGS','debit',0,'credit',abs(v_delta_cogs),'customer_id',h.customer_id,'po_id',r.po_id));
    end if;
  end loop;
  if jsonb_array_length(v_lines)>=2 then
    perform erp.post_journal('SALES_RETURN',h.id,h.physical_at::date,
      'Sales return from customer · cumulative exact HPP target',v_lines);
  end if;

  update erp.sales_headers
  set status=case when v_paid>=v_net_total-0.01 then 'PAID' when v_paid>0 then 'PARTIAL_PAID' else 'POSTED' end
  where id=h.sale_id;
  for r in
    select distinct fl.po_id
    from erp.sales_return_items i join erp.fg_lots fl on fl.id=i.lot_id
    where i.return_id=h.id and fl.po_id is not null order by fl.po_id
  loop
    perform erp.refresh_po_hpp_gl_baseline(r.po_id);
    perform erp.assert_po_hpp_target_book_v2620d(r.po_id);
  end loop;
end
$function$;
alter function erp.post_sales_return(uuid) owner to postgres;

create or replace function erp.reverse_sale(p_sale_id uuid,p_reason text)
returns void
language plpgsql
security definer
set search_path to 'erp','public'
as $function$
declare
  h erp.sales_headers%rowtype;
  r record;
  v_journal uuid;
  v_expected numeric(24,6);
  v_po uuid;
begin
  perform erp.require_owner_admin();
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  if nullif(trim(p_reason),'') is null then raise exception 'Alasan reversal penjualan wajib diisi'; end if;

  select * into h from erp.sales_headers where id=p_sale_id for update;
  if h.id is null then raise exception 'Penjualan tidak ditemukan'; end if;
  if h.status='REVERSED' then return; end if;
  if h.status not in('POSTED','PARTIAL_PAID','PAID') then
    raise exception 'Hanya penjualan yang sudah POSTED/aktif yang dapat direverse';
  end if;
  if exists(select 1 from erp.sales_payments where sale_id=h.id and status='POSTED') then
    raise exception 'Penjualan ini sudah memiliki pembayaran customer. Reverse pembayaran aktif terlebih dahulu.';
  end if;
  if exists(select 1 from erp.sales_returns where sale_id=h.id and status='POSTED') then
    raise exception 'Penjualan ini sudah memiliki retur POSTED. Reverse retur aktif terlebih dahulu.';
  end if;

  select coalesce((select sum(line_total) from erp.sales_items where sale_id=h.id),0)
       +coalesce((select sum(a.qty_pcs*a.unit_hpp_snapshot)
          from erp.sale_stock_allocations a
          join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=h.id),0)
  into v_expected;
  select id into v_journal from erp.journal_entries
  where source_type='SALE' and source_id=h.id and status='POSTED'
  order by posting_at desc,id desc limit 1;
  if v_expected>0.005 and v_journal is null then
    raise exception 'Jurnal penjualan tidak ditemukan; reversal dibatalkan agar piutang/HPP tidak rusak';
  end if;

  for r in
    select fm.id
    from erp.fg_stock_movements fm
    join erp.sales_items i on i.id=fm.source_id
    where i.sale_id=h.id and fm.source_type='SALE_ITEM' and fm.movement_type='SALE'
      and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=fm.id)
    order by fm.physical_at desc,fm.id desc
  loop
    perform erp.reverse_fg_movement(r.id,p_reason);
  end loop;

  if v_journal is not null then perform erp.reverse_journal(v_journal,p_reason); end if;
  update erp.sales_headers set status='REVERSED' where id=h.id;

  for v_po in
    select distinct fl.po_id
    from erp.sale_stock_allocations a
    join erp.sales_items i on i.id=a.sale_item_id
    join erp.fg_lots fl on fl.id=a.lot_id
    where i.sale_id=h.id and fl.po_id is not null order by fl.po_id
  loop
    -- First reflect only the exact compensating journal, then let the normal
    -- synchronizer post any cumulative-rounding redistribution still needed by
    -- the remaining active sales.
    perform erp.refresh_po_hpp_gl_baseline(v_po);
    perform erp.sync_po_hpp_to_gl(v_po,current_date);
    perform erp.refresh_po_hpp_gl_baseline(v_po);
    perform erp.assert_po_hpp_target_book_v2620d(v_po);
  end loop;
  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason)
  values('sales_headers',h.id,'REVERSE',erp.current_app_user_id(),p_reason);
end
$function$;
alter function erp.reverse_sale(uuid,text) owner to postgres;

create or replace function erp.reverse_sales_return(p_return_id uuid,p_reason text)
returns void
language plpgsql
security definer
set search_path to 'erp','public'
as $function$
declare
  h erp.sales_returns%rowtype;
  s erp.sales_headers%rowtype;
  r record;
  v_journal uuid;
  v_expected numeric(24,6);
  v_paid numeric(20,2);
  v_total numeric(20,2);
  v_po uuid;
begin
  perform erp.require_owner_admin();
  perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
  if nullif(trim(p_reason),'') is null then raise exception 'Alasan reversal retur penjualan wajib diisi'; end if;

  select * into h from erp.sales_returns where id=p_return_id for update;
  if h.id is null then raise exception 'Retur penjualan tidak ditemukan'; end if;
  if h.status='REVERSED' then return; end if;
  if h.status<>'POSTED' then raise exception 'Hanya retur penjualan POSTED yang dapat direverse'; end if;
  select * into s from erp.sales_headers where id=h.sale_id for update;
  if s.id is null or s.status='REVERSED' then raise exception 'Penjualan sumber retur tidak aktif'; end if;

  select coalesce(sum(i.refund_amount+i.qty_pcs*i.unit_hpp_snapshot),0)
  into v_expected from erp.sales_return_items i where i.return_id=h.id;
  select id into v_journal from erp.journal_entries
  where source_type='SALES_RETURN' and source_id=h.id and status='POSTED'
  order by posting_at desc,id desc limit 1;
  if v_expected>0.005 and v_journal is null then
    raise exception 'Jurnal retur penjualan tidak ditemukan; reversal dibatalkan agar piutang/HPP tidak rusak';
  end if;

  for r in
    select fm.id,fm.qty_signed,fl.cached_qty_pcs
    from erp.fg_stock_movements fm
    join erp.sales_return_items i on i.id=fm.source_id
    join erp.fg_lots fl on fl.id=fm.lot_id
    where i.return_id=h.id and fm.source_type='SALES_RETURN_ITEM'
      and fm.movement_type='SALE_RETURN'
      and not exists(select 1 from erp.fg_stock_movements rv where rv.reversal_of_id=fm.id)
    order by fm.physical_at desc,fm.id desc
  loop
    if r.cached_qty_pcs<r.qty_signed then
      raise exception 'Barang dari retur ini sudah dipakai/dijual lagi. Reverse transaksi downstream dulu sebelum membatalkan retur.';
    end if;
    perform erp.reverse_fg_movement(r.id,p_reason);
  end loop;

  if v_journal is not null then perform erp.reverse_journal(v_journal,p_reason); end if;
  update erp.sales_returns set status='REVERSED' where id=h.id;
  select erp.sale_net_total(s.id)::numeric(20,2) into v_total;
  select coalesce(sum(amount),0)::numeric(20,2) into v_paid
  from erp.sales_payments where sale_id=s.id and status='POSTED';
  update erp.sales_headers
  set status=case when v_paid>=v_total-0.01 then 'PAID' when v_paid>0 then 'PARTIAL_PAID' else 'POSTED' end
  where id=s.id;

  for v_po in
    select distinct fl.po_id
    from erp.sales_return_items i join erp.fg_lots fl on fl.id=i.lot_id
    where i.return_id=h.id and fl.po_id is not null order by fl.po_id
  loop
    perform erp.refresh_po_hpp_gl_baseline(v_po);
    perform erp.sync_po_hpp_to_gl(v_po,current_date);
    perform erp.refresh_po_hpp_gl_baseline(v_po);
    perform erp.assert_po_hpp_target_book_v2620d(v_po);
  end loop;
  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason)
  values('sales_returns',h.id,'REVERSE',erp.current_app_user_id(),p_reason);
end
$function$;
alter function erp.reverse_sales_return(uuid,text) owner to postgres;

do $patch_financial_checks$
declare
  v_definition text;
  v_anchor text;
  v_replacement text;
begin
  select pg_get_functiondef('erp.run_v268_financial_report_checks()'::regprocedure)
    into v_definition;

  v_anchor:='erp.compute_po_hpp_gl_targets(';
  v_replacement:='erp.compute_po_hpp_gl_targets_v2620d(';
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>2 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: financial-check HPP target anchors are not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$  from erp.po_hpp_gl_state s
  cross join lateral(
    select
      coalesce(sum(jl.debit-jl.credit) filter(
        where jl.account_id=erp.account_id('FG_INVENTORY')),0)::numeric fg_book,
      coalesce(sum(jl.debit-jl.credit) filter(
        where jl.account_id=erp.account_id('COGS')),0)::numeric cogs_book,
      coalesce(sum(jl.debit-jl.credit) filter(
        where jl.account_id in(
          erp.account_id('OTHER_EXPENSE'),erp.account_id('OTHER_INCOME')
        )),0)::numeric other_book
    from erp.journal_lines jl
    join erp.journal_entries je on je.id=jl.journal_entry_id
      and je.status in('POSTED','REVERSED')
    where jl.po_id=s.po_id
  ) b
  cross join lateral(
    select coalesce(sum(e.residual_amount),0)::numeric active_wip_close
    from erp.po_wip_close_events e
    join erp.journal_entries je on je.id=e.journal_entry_id
      and je.source_type='PO_WIP_RESIDUAL_CLOSE' and je.status='POSTED'
    where e.po_id=s.po_id
  ) c
  where abs(b.fg_book-s.fg_value)>0.005
     or abs(b.cogs_book-s.cogs_value)>0.005
     or abs((b.other_book-c.active_wip_close)-s.other_out_value)>0.005$anchor$;
  v_replacement:=$replacement$  from erp.po_hpp_gl_state s
  cross join lateral erp.compute_po_hpp_gl_book_v2620d(s.po_id) b
  where abs(b.fg_value-s.fg_value)>0.005
     or abs(b.cogs_value-s.cogs_value)>0.005
     or abs(b.other_out_value-s.other_out_value)>0.005$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: financial-check book anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$        select sum(actual_cost+greatest(qty_sent_pcs-qty_costed,0)
          *coalesce(estimated_rate_snapshot,0)) from delivery_cost
      ),0)
      +coalesce((
        select sum(l.amount_payable)$anchor$;
  v_replacement:=$replacement$        select sum(actual_cost+greatest(qty_sent_pcs-qty_costed,0)
          *coalesce(estimated_rate_snapshot,0)) from delivery_cost
      ),0)
      +coalesce((
        select sum(rl.actual_cost)
        from erp.laundry_failed_wash_attempts a
        join erp.laundry_receipt_lines rl on rl.id=a.receipt_line_id
          and rl.actual_cost_status in('ESTIMATED','FINAL')
        join erp.laundry_receipts rh on rh.id=a.receipt_id and rh.status='POSTED'
        join erp.laundry_deliveries d on d.id=a.delivery_id and d.status='REVERSED'
        where d.po_id=s.po_id
      ),0)
      +coalesce((
        select sum(l.amount_payable)$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: financial-check returned-cost anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$  union all
  select 'V2620C_HPP_STATE_HAS_SUBCENT','CRITICAL',count(*)::bigint,
    'Cumulative PO HPP GL state must contain exactly the minor-unit amounts that were journaled'
  from erp.po_hpp_gl_state s
  where s.hpp_total_cost<>round(s.hpp_total_cost,2)
     or s.fg_value<>round(s.fg_value,2)
     or s.cogs_value<>round(s.cogs_value,2)
     or s.other_out_value<>round(s.other_out_value,2);$anchor$;
  v_replacement:=$replacement$  union all
  select 'V2620C_HPP_STATE_HAS_SUBCENT','CRITICAL',count(*)::bigint,
    'Cumulative PO HPP GL state must contain exactly the minor-unit amounts that were journaled'
  from erp.po_hpp_gl_state s
  where s.hpp_total_cost<>round(s.hpp_total_cost,2)
     or s.fg_value<>round(s.fg_value,2)
     or s.cogs_value<>round(s.cogs_value,2)
     or s.other_out_value<>round(s.other_out_value,2)

  union all
  select 'V2620D_REDISPATCH_PARTICIPANT_LINEAGE_MISMATCH','CRITICAL',count(*)::bigint,
    'Every carried participant interval must be contiguous, bounded, acyclic, same-source, and descend from a prior immutable full return'
  from(
    select a.id issue_id
    from erp.laundry_redispatch_participant_allocations a
    join erp.laundry_delivery_batch_size_lines sx
      on sx.id=a.source_delivery_batch_size_line_id
    join erp.laundry_delivery_lines sdl on sdl.id=sx.delivery_line_id
    join erp.laundry_deliveries sd on sd.id=sdl.delivery_id
    join erp.laundry_delivery_batch_size_lines dx
      on dx.id=a.successor_delivery_batch_size_line_id
    join erp.laundry_delivery_lines ddl on ddl.id=dx.delivery_line_id
    join erp.laundry_deliveries dd on dd.id=ddl.delivery_id
    where sx.distribution_batch_id<>dx.distribution_batch_id
       or sx.size_id<>dx.size_id or sdl.cutting_group_id<>ddl.cutting_group_id
       or sd.status<>'REVERSED'
       or (sd.physical_at,sd.created_at,sd.id)>=(dd.physical_at,dd.created_at,dd.id)
       or a.source_offset_pcs+a.qty_pcs>sx.qty_sent_pcs
       or a.successor_offset_pcs+a.qty_pcs>dx.qty_sent_pcs
       or not exists(
         select 1 from erp.laundry_failed_wash_attempts f
         join erp.laundry_failed_wash_batch_size_lines fx
           on fx.attempt_id=f.id and fx.delivery_batch_size_line_id=sx.id
          and fx.qty_attempted_pcs=sx.qty_sent_pcs
         join erp.laundry_receipts fr on fr.id=f.receipt_id and fr.status='POSTED'
         where f.delivery_id=sd.id and f.custody_outcome='RETURN_UNPROCESSED'
           and fr.physical_at<=dd.physical_at
       )
    union all
    select min(a.id::text)::uuid
    from erp.laundry_redispatch_participant_allocations a
    group by a.source_delivery_batch_size_line_id
    having min(a.source_offset_pcs)<>0
       or max(a.source_offset_pcs+a.qty_pcs)<>sum(a.qty_pcs)
    union all
    select min(a.id::text)::uuid
    from erp.laundry_redispatch_participant_allocations a
    group by a.successor_delivery_batch_size_line_id
    having min(a.successor_offset_pcs)<>0
       or max(a.successor_offset_pcs+a.qty_pcs)<>sum(a.qty_pcs)
  ) bad_lineage

  union all
  select 'V2620D_SALE_LIFECYCLE_HPP_DIMENSION_MISMATCH','CRITICAL',count(*)::bigint,
    'Every Sale lifecycle journal must conserve FG/COGS and use either complete PO dimensions or one attributable historical aggregate'
  from erp.journal_entries e
  left join erp.journal_entries o on o.id=e.reversal_of_id
  cross join lateral(
    select
      coalesce(sum(l.debit-l.credit) filter(where l.account_id=erp.account_id('COGS')),0) cogs,
      coalesce(sum(l.debit-l.credit) filter(where l.account_id=erp.account_id('FG_INVENTORY')),0) fg,
      count(*) filter(where l.account_id in(erp.account_id('COGS'),erp.account_id('FG_INVENTORY'))
        and l.po_id is not null) tagged,
      count(*) filter(where l.account_id in(erp.account_id('COGS'),erp.account_id('FG_INVENTORY'))
        and l.po_id is null) untagged
    from erp.journal_lines l where l.journal_entry_id=e.id
  ) b
  where e.status in('POSTED','REVERSED') and(
    e.source_type in('SALE','SALES_RETURN')
    or(e.source_type='JOURNAL_REVERSAL' and o.source_type in('SALE','SALES_RETURN'))
  ) and(
    abs(b.cogs+b.fg)>0.005 or(b.tagged>0 and b.untagged>0)
    or exists(
      select 1 from erp.journal_lines l
      where l.journal_entry_id=e.id
        and l.account_id in(erp.account_id('COGS'),erp.account_id('FG_INVENTORY'))
        and l.po_id is not null
      group by l.po_id
      having abs(sum(l.debit-l.credit))>0.005
    )
  );$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: financial-check terminal anchor is not exact';
  end if;
  execute replace(v_definition,v_anchor,v_replacement);
end
$patch_financial_checks$;

create or replace function erp.get_owner_financial_snapshot_v2(
  p_from date,p_to date,p_as_of date default current_date
)
returns jsonb
language plpgsql
stable
security definer
set search_path to 'erp','public','pg_catalog','pg_temp'
as $function$
declare
  v_assets numeric:=0;v_liabilities numeric:=0;v_equity numeric:=0;v_current_earnings numeric:=0;
  v_cash numeric:=0;v_ar numeric:=0;v_material numeric:=0;v_wip numeric:=0;v_fg numeric:=0;
  v_ap numeric:=0;v_grni numeric:=0;
  v_sales_revenue numeric:=0;v_cogs numeric:=0;v_other_income numeric:=0;v_opex numeric:=0;v_net_profit numeric:=0;
  v_gross_sales numeric:=0;v_discounts numeric:=0;v_sales_returns numeric:=0;
  v_operational_net_sales numeric:=0;v_sales_revenue_bridge numeric:=0;
  v_qc_good numeric:=0;v_qc_bs numeric:=0;
  v_laundry_good numeric:=0;v_laundry_bs numeric:=0;v_laundry_stuck numeric:=0;v_laundry_missing numeric:=0;
  v_laundry_outstanding numeric:=0;
  v_failed_checks jsonb:='[]'::jsonb;
  v_grni_docs bigint:=0;v_grni_oldest integer:=0;v_ap_docs bigint:=0;v_ap_overdue numeric:=0;
  v_critical bigint:=0;v_warning bigint:=0;v_pending bigint:=0;
begin
  perform erp.require_owner_admin();
  if p_from is null or p_to is null or p_as_of is null then raise exception 'p_from, p_to and p_as_of are required'; end if;
  if p_from>p_to then raise exception 'p_from cannot be after p_to'; end if;
  if p_to>p_as_of then raise exception 'p_to cannot be after p_as_of'; end if;

  select
    coalesce(sum(case when ca.account_type='ASSET' then a.debit_total-a.credit_total else 0 end),0),
    coalesce(sum(case when ca.account_type='LIABILITY' then a.credit_total-a.debit_total else 0 end),0),
    coalesce(sum(case when ca.account_type='EQUITY' then a.credit_total-a.debit_total else 0 end),0),
    coalesce(sum(case when ca.account_type in('REVENUE','EXPENSE') then a.credit_total-a.debit_total else 0 end),0)
  into v_assets,v_liabilities,v_equity,v_current_earnings
  from erp.account_daily_balances a join erp.chart_accounts ca on ca.id=a.account_id
  where a.balance_date<=p_as_of;

  select coalesce(sum(a.debit_total-a.credit_total),0) into v_cash
  from erp.account_daily_balances a
  where a.balance_date<=p_as_of and a.account_id in(
    select ca.coa_account_id from erp.cash_accounts ca
    union select erp.account_id('CASH')
  );
  select coalesce(sum(a.debit_total-a.credit_total),0) into v_ar
  from erp.account_daily_balances a where a.balance_date<=p_as_of and a.account_id=erp.account_id('AR_CUSTOMER');
  select coalesce(sum(a.debit_total-a.credit_total),0) into v_material
  from erp.account_daily_balances a where a.balance_date<=p_as_of and a.account_id=erp.account_id('MATERIAL_INVENTORY');
  select coalesce(sum(a.debit_total-a.credit_total),0) into v_wip
  from erp.account_daily_balances a where a.balance_date<=p_as_of and a.account_id=erp.account_id('WIP');
  select coalesce(sum(a.debit_total-a.credit_total),0) into v_fg
  from erp.account_daily_balances a where a.balance_date<=p_as_of and a.account_id=erp.account_id('FG_INVENTORY');
  select coalesce(sum(a.credit_total-a.debit_total),0) into v_ap
  from erp.account_daily_balances a where a.balance_date<=p_as_of and a.account_id=erp.account_id('AP_SUPPLIER');
  select coalesce(sum(a.credit_total-a.debit_total),0) into v_grni
  from erp.account_daily_balances a where a.balance_date<=p_as_of and a.account_id=erp.account_id('GRNI_MATERIAL');

  select
    coalesce(sum(case when a.account_id=erp.account_id('SALES_REVENUE') then a.credit_total-a.debit_total else 0 end),0),
    coalesce(sum(case when a.account_id=erp.account_id('COGS') then a.debit_total-a.credit_total else 0 end),0),
    coalesce(sum(case when ca.account_type='REVENUE' and a.account_id<>erp.account_id('SALES_REVENUE') then a.credit_total-a.debit_total else 0 end),0),
    coalesce(sum(case when ca.account_type='EXPENSE' and a.account_id<>erp.account_id('COGS') then a.debit_total-a.credit_total else 0 end),0),
    coalesce(sum(case when ca.account_type in('REVENUE','EXPENSE') then a.credit_total-a.debit_total else 0 end),0)
  into v_sales_revenue,v_cogs,v_other_income,v_opex,v_net_profit
  from erp.account_daily_balances a join erp.chart_accounts ca on ca.id=a.account_id
  where a.balance_date between p_from and p_to;

  with sale_events as(
    select original.source_id sale_id,1::integer event_sign
    from erp.journal_entries original
    where original.source_type='SALE' and original.status in('POSTED','REVERSED')
      and original.transaction_date between p_from and p_to
    union all
    select original.source_id,-1::integer
    from erp.journal_entries reversal
    join erp.journal_entries original on original.id=reversal.reversal_of_id
      and original.source_type='SALE'
    where reversal.source_type='JOURNAL_REVERSAL' and reversal.status='POSTED'
      and reversal.transaction_date between p_from and p_to
  )
  select coalesce(sum(e.event_sign*i.qty_pcs*i.unit_price_snapshot),0),
         coalesce(sum(e.event_sign*i.discount_amount),0)
  into v_gross_sales,v_discounts
  from sale_events e join erp.sales_items i on i.sale_id=e.sale_id;

  with return_events as(
    select original.source_id return_id,1::integer event_sign
    from erp.journal_entries original
    where original.source_type='SALES_RETURN' and original.status in('POSTED','REVERSED')
      and original.transaction_date between p_from and p_to
    union all
    select original.source_id,-1::integer
    from erp.journal_entries reversal
    join erp.journal_entries original on original.id=reversal.reversal_of_id
      and original.source_type='SALES_RETURN'
    where reversal.source_type='JOURNAL_REVERSAL' and reversal.status='POSTED'
      and reversal.transaction_date between p_from and p_to
  )
  select coalesce(sum(e.event_sign*i.refund_amount),0) into v_sales_returns
  from return_events e join erp.sales_return_items i on i.return_id=e.return_id;
  v_operational_net_sales:=round(v_gross_sales-v_discounts-v_sales_returns,2);
  v_sales_revenue_bridge:=round(v_operational_net_sales-v_sales_revenue,2);

  select coalesce(sum(i.qty_good_pcs),0),coalesce(sum(i.qty_bs_pcs),0)
  into v_qc_good,v_qc_bs
  from erp.qc_inspection_items i join erp.qc_inspections h on h.id=i.inspection_id
  where h.status='POSTED' and h.physical_at::date between p_from and p_to;
  select coalesce(sum(i.qty_good_received),0),coalesce(sum(i.qty_bs_laundry),0),
         coalesce(sum(i.qty_stuck),0),coalesce(sum(i.qty_missing),0)
  into v_laundry_good,v_laundry_bs,v_laundry_stuck,v_laundry_missing
  from erp.laundry_receipt_lines i join erp.laundry_receipts h on h.id=i.receipt_id
  where h.status='POSTED' and h.physical_at::date between p_from and p_to;

  select greatest(coalesce(sum(case
    when w.stage_to='LAUNDRY' then w.qty_pcs
    when w.stage_from='LAUNDRY' then -w.qty_pcs
    else 0 end),0),0)
  into v_laundry_outstanding
  from erp.wip_stage_events w
  where w.physical_at::date<=p_as_of
    and w.source_type in(
      'LAUNDRY_DELIVERY_LINE','LAUNDRY_RECEIPT_LINE',
      'CP6_LAUNDRY_DELIVERY_WIP_REVERSAL','CP6_LAUNDRY_RECEIPT_WIP_REVERSAL'
    );

  select count(*)::bigint,coalesce(max(unfinalized_days),0)::integer
  into v_grni_docs,v_grni_oldest from erp.v_material_grni_aging;
  select count(*)::bigint,coalesce(sum(case when days_overdue>0 then outstanding_amount else 0 end),0)
  into v_ap_docs,v_ap_overdue from erp.v_supplier_ap_aging where outstanding_amount>0.005;

  select coalesce(sum(issue_count) filter(where severity='CRITICAL'),0)::bigint,
         coalesce(sum(issue_count) filter(where severity='WARNING'),0)::bigint
  into v_critical,v_warning from erp.run_v268_financial_report_checks();
  select coalesce(jsonb_agg(jsonb_build_object(
    'check_name',c.check_name,'severity',c.severity,'issue_count',c.issue_count,
    'details',c.details) order by c.severity,c.check_name),'[]'::jsonb)
  into v_failed_checks from erp.run_v268_financial_report_checks() c
  where c.issue_count>0;
  if abs(v_sales_revenue_bridge)>0.005 then
    v_critical:=v_critical+1;
    v_failed_checks:=v_failed_checks||jsonb_build_array(jsonb_build_object(
      'check_name','V2620D_PERIOD_SALES_REVENUE_BRIDGE_MISMATCH',
      'severity','CRITICAL','issue_count',1,
      'details','Signed Sale/Sales-return lifecycle events do not reconcile to SALES_REVENUE for the selected posting period'
    ));
  end if;
  select count(*)::bigint into v_pending from erp.cost_recalc_queue
  where status in('PENDING','RUNNING') or(status='FAILED' and attempt_count<3);

  return jsonb_build_object(
    'basis',jsonb_build_object(
      'period_from',p_from,'period_to',p_to,'balance_sheet_as_of',p_as_of,
      'supplier_exposure_basis','CURRENT_OPERATIONAL_STATE',
      'performance_lifecycle_basis','SIGNED_JOURNAL_LIFECYCLE_EVENTS_IN_POSTING_PERIOD',
      'performance_reconciliation_basis','OPERATIONAL_NET_SALES_MINUS_SALES_REVENUE_GL',
      'quality_event_basis','CURRENT_OPERATIONAL_STATE_WITH_EVENT_DATE_CUTOFF',
      'laundry_outstanding_basis','IMMUTABLE_WIP_STAGE_EVENT_NET_AS_OF_BALANCE_DATE'
    ),
    'data_confidence',jsonb_build_object(
      'status',case when v_critical>0 then 'BLOCKED'
                    when v_pending>0 then 'RECALC_PENDING' else 'READY' end,
      'critical_issue_count',v_critical,'warning_issue_count',v_warning,
      'pending_cost_recalc_count',v_pending,'failed_checks',v_failed_checks
    ),
    'financial_position',jsonb_build_object(
      'assets',round(v_assets,2),'cash',round(v_cash,2),'customer_ar',round(v_ar,2),
      'material_inventory',round(v_material,2),'wip_inventory',round(v_wip,2),'fg_inventory',round(v_fg,2),
      'liabilities',round(v_liabilities,2),'supplier_final_ap',round(v_ap,2),
      'grni_estimated_liability',round(v_grni,2),'recorded_equity',round(v_equity,2),
      'current_earnings',round(v_current_earnings,2),
      'liabilities_plus_equity',round(v_liabilities+v_equity+v_current_earnings,2),
      'balance_difference',round(v_assets-v_liabilities-v_equity-v_current_earnings,2)
    ),
    'performance',jsonb_build_object(
      'sales_revenue_gl',round(v_sales_revenue,2),'cogs_gl',round(v_cogs,2),
      'gross_profit',round(v_sales_revenue-v_cogs,2),
      'gross_margin_pct',case when abs(v_sales_revenue)>0.005 then round((v_sales_revenue-v_cogs)*100/v_sales_revenue,4) else null end,
      'other_income',round(v_other_income,2),'operating_and_other_expense',round(v_opex,2),
      'net_profit',round(v_net_profit,2),
      'net_margin_pct',case when abs(v_sales_revenue)>0.005 then round(v_net_profit*100/v_sales_revenue,4) else null end,
      'gross_sales_before_discount',round(v_gross_sales,2),'line_discounts',round(v_discounts,2),
      'posted_sales_returns',round(v_sales_returns,2),
      'operational_net_sales',v_operational_net_sales,
      'sales_revenue_bridge_delta',v_sales_revenue_bridge,
      'sales_revenue_reconciled',abs(v_sales_revenue_bridge)<=0.005
    ),
    'quality',jsonb_build_object(
      'qc_good_pcs',v_qc_good,'qc_bs_pcs',v_qc_bs,
      'qc_defect_rate_pct',case when v_qc_good+v_qc_bs>0 then round(v_qc_bs*100/(v_qc_good+v_qc_bs),4) else null end,
      'laundry_good_received_pcs',v_laundry_good,'laundry_bs_pcs',v_laundry_bs,
      'laundry_bs_rate_on_resolved_receipts_pct',case when v_laundry_good+v_laundry_bs>0 then round(v_laundry_bs*100/(v_laundry_good+v_laundry_bs),4) else null end,
      'laundry_outstanding_pcs',v_laundry_outstanding,
      'legacy_receipt_stuck_pcs',v_laundry_stuck,'legacy_receipt_missing_pcs',v_laundry_missing
    ),
    'supplier_exposure',jsonb_build_object(
      'unfinalized_receipt_count',v_grni_docs,'oldest_unfinalized_days',v_grni_oldest,
      'open_final_ap_document_count',v_ap_docs,'overdue_final_ap_amount',round(v_ap_overdue,2)
    )
  );
end
$function$;
alter function erp.get_owner_financial_snapshot_v2(date,date,date) owner to postgres;

-- Apply the repair to pre-v20d facts without editing any posted row. Derived
-- participant lineage causes a normal HPP rebuild; prior cent drift is closed
-- by a new PO_HPP_GL_SYNC journal against the independently reconstructed book.
do $reconcile_existing_v2620d$
declare
  r record;
begin
  for r in
    select distinct sd.po_id
    from erp.laundry_redispatch_participant_allocations a
    join erp.laundry_delivery_batch_size_lines sx
      on sx.id=a.source_delivery_batch_size_line_id
    join erp.laundry_delivery_lines sl on sl.id=sx.delivery_line_id
    join erp.laundry_deliveries sd on sd.id=sl.delivery_id
    order by sd.po_id
  loop
    perform erp.rebuild_po_hpp(
      r.po_id,'v2.6.20d append-only redispatch participant lineage backfill'
    );
  end loop;

  for r in select po_id from erp.po_hpp_gl_state order by po_id
  loop
    perform erp.refresh_po_hpp_gl_baseline(r.po_id);
    perform erp.sync_po_hpp_to_gl(r.po_id,current_date);
    perform erp.refresh_po_hpp_gl_baseline(r.po_id);
    perform erp.assert_po_hpp_target_book_v2620d(r.po_id);
  end loop;
end
$reconcile_existing_v2620d$;

do $installed_guard_v2620d$
declare
  v_issue_count bigint;
begin
  if to_regclass('erp.laundry_redispatch_participant_allocations') is null
     or not (select c.relrowsecurity from pg_class c
       where c.oid='erp.laundry_redispatch_participant_allocations'::regclass)
     or exists(select 1 from pg_policy p
       where p.polrelid='erp.laundry_redispatch_participant_allocations'::regclass)
     or exists(
       select 1 from information_schema.role_table_grants g
       where g.table_schema='erp'
         and g.table_name='laundry_redispatch_participant_allocations'
         and g.grantee in('PUBLIC','anon','authenticated','service_role')
     )
     or (select count(*) from pg_trigger t
       where t.tgrelid='erp.laundry_redispatch_participant_allocations'::regclass
         and not t.tgisinternal and t.tgname in(
           'trg_guard_laundry_redispatch_participant_v2620d',
           'trg_audit_laundry_redispatch_participant_v2620d'
         ))<>2
     or position('allocate_laundry_redispatch_participants_v2620d' in pg_get_functiondef(
       'erp.save_laundry_qc_action_v1(text,jsonb,uuid,bigint)'::regprocedure))=0
     or position('cp6_lot_failed_wash_cost_v2620d' in pg_get_functiondef(
       'erp.rebuild_po_hpp(uuid,text)'::regprocedure))=0
     or position('compute_po_hpp_gl_targets_v2620d' in pg_get_functiondef(
       'erp.sync_po_hpp_to_gl(uuid,date)'::regprocedure))=0
     or position('cumulative exact HPP target' in pg_get_functiondef(
       'erp.post_sale(uuid)'::regprocedure))=0
     or position('cumulative exact HPP target' in pg_get_functiondef(
       'erp.post_sales_return(uuid)'::regprocedure))=0
     or position('SIGNED_JOURNAL_LIFECYCLE_EVENTS_IN_POSTING_PERIOD' in pg_get_functiondef(
       'erp.get_owner_financial_snapshot_v2(date,date,date)'::regprocedure))=0
     or exists(
       select 1 from (values
         ('erp.guard_laundry_redispatch_participant_v2620d()'),
         ('erp.allocate_laundry_redispatch_participants_v2620d(uuid)'),
         ('erp.cp6_lot_failed_wash_cost_v2620d(uuid)'),
         ('erp.compute_po_hpp_gl_targets_v2620d(uuid)'),
         ('erp.sale_lifecycle_po_hpp_amount_v2620d(uuid,uuid)'),
         ('erp.compute_po_hpp_gl_book_v2620d(uuid)'),
         ('erp.assert_po_hpp_target_book_v2620d(uuid)')
       ) f(identity)
       cross join (values('anon'),('authenticated'),('service_role')) r(role_name)
       where has_function_privilege(r.role_name,f.identity,'EXECUTE')
     ) then
    raise exception 'ERP v2.6.20d business closure did not install privately and completely';
  end if;

  select coalesce(sum(c.issue_count),0)::bigint into v_issue_count
  from erp.run_v268_financial_report_checks() c
  where c.check_name in(
    'V2620C_PO_HPP_TARGET_STATE_MISMATCH',
    'V2620C_PO_HPP_BOOK_MISMATCH',
    'V2620C_WIP_SOURCE_CONSERVATION_MISMATCH',
    'V2620D_REDISPATCH_PARTICIPANT_LINEAGE_MISMATCH',
    'V2620D_SALE_LIFECYCLE_HPP_DIMENSION_MISMATCH'
  );
  if v_issue_count<>0 then
    raise exception 'ERP v2.6.20d targeted financial/lineage reconciliation still has % issue(s)',
      v_issue_count;
  end if;

  update erp.cp6_v2620d_rollback_capsule c
  set installed_definition_sha256=encode(extensions.digest(convert_to(
    pg_get_functiondef(to_regprocedure(c.object_regidentity)),'UTF8'
  ),'sha256'),'hex');
  if (select count(*) from erp.cp6_v2620d_rollback_capsule
      where installed_definition_sha256 is not null)<>10 then
    raise exception 'ERP v2.6.20d installed-definition capsule is incomplete';
  end if;
end
$installed_guard_v2620d$;

comment on table erp.laundry_redispatch_participant_allocations is
  'Private append-only physical participant intervals carrying failed-wash cost through return and redispatch chains; deterministic FIFO is explicit.';
comment on function erp.compute_po_hpp_gl_targets_v2620d(uuid) is
  'Conserved cumulative minor-unit HPP allocation: rounded COGS and genuine disposition, with exact FG remainder.';
comment on function erp.compute_po_hpp_gl_book_v2620d(uuid) is
  'Independent actual per-PO FG/COGS/disposition book, including attributed historical Sale/return lifecycle journals.';
comment on function erp.get_owner_financial_snapshot_v2(date,date,date) is
  'Owner report with signed posting-period Sale/return lifecycle events and an explicit operational-to-GL revenue bridge.';

insert into erp.schema_migrations(version,description)
values(
  'v2.6.20d',
  'CP6 independent re-audit closure: redispatch cost lineage, signed report bridge, conserved cumulative sale cents, executable rollback proof'
);

commit;
