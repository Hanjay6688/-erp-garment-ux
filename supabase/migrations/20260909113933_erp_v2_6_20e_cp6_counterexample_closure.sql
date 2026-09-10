-- ERP Garment v2.6.20e / CP6 independent counterexample closure.
--
-- Reliable data adalah DEWA. Keuangan termasuk laporan, stok, dan HPP adalah RAJA.
-- Forward-only: C01-C06 are closed without deleting or rewriting posted facts.

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
  erp.laundry_failed_wash_batch_size_lines,
  erp.laundry_redispatch_participant_allocations
in share row exclusive mode;

do $guard$
declare
  r record;
  v_actual text;
  v_platform_match_count integer;
begin
  if not exists(select 1 from erp.schema_migrations where version='v2.6.20d') then
    raise exception 'ERP v2.6.20e requires immutable v2.6.20d first';
  end if;
  if exists(select 1 from erp.schema_migrations where version='v2.6.20e') then
    raise exception 'ERP v2.6.20e is already recorded; never replay or edit a recorded migration';
  end if;
  if to_regclass('erp.cp6_v2620e_rollback_capsule') is not null
     or to_regclass('erp.laundry_redispatch_participant_events') is not null
     or to_regprocedure('erp.guard_laundry_redispatch_participant_event_v2620e()') is not null
     or to_regprocedure('erp.record_laundry_redispatch_release_v2620e()') is not null
     or to_regprocedure('erp.allocate_laundry_redispatch_participants_v2620e(uuid)') is not null
     or to_regprocedure('erp.cp6_lot_failed_wash_cost_v2620e(uuid)') is not null
     or to_regprocedure('erp.compute_po_hpp_gl_book_v2620e(uuid)') is not null
     or to_regprocedure('erp.assert_po_hpp_target_book_v2620e(uuid)') is not null then
    raise exception 'ERP v2.6.20e target guard: prior repair residue exists';
  end if;
  if exists(select 1 from erp.cp6_laundry_qc_execution_context) then
    raise exception 'ERP v2.6.20e refuses installation while a CP6 execution context exists';
  end if;

  select count(*) into v_platform_match_count
  from supabase_migrations.schema_migrations m
  where m.name='erp_v2_6_20d_cp6_reaudit_business_closure'
    and coalesce(encode(extensions.digest(
      convert_to(array_to_string(m.statements,E'\n'),'UTF8'),'sha256'
    ),'hex'),'') in(
      'f3f1ba8f889440c8694ba2932fc787ea5bdfab980b2d94f24cd9bfabf1bbf222',
      'eab866385d3a462aea5815dc5069d5d7a774f7aa88c43d983c665469f4469465'
    );
  if v_platform_match_count<>1 then
    raise exception 'ERP v2.6.20e requires one exact v2.6.20d platform-ledger row; found %',
      v_platform_match_count;
  end if;

  for r in select * from (values
    ('erp.save_laundry_qc_action_v1(text,jsonb,uuid,bigint)','6f8696ff1c1447779af3849ba3860990e88c17edc0322ab94e1ab01b31d0b201'),
    ('erp.rebuild_po_hpp(uuid,text)','955c549457092b467bb0d47cf3f2f4bb656ac6038eb7cc3761332b5b5bffcdde'),
    ('erp.refresh_po_hpp_gl_baseline(uuid)','132cb6d6504f951dbab6d3428bb19040122228b7c6b90e2e5bfbbe0ea81fc026'),
    ('erp.post_sale(uuid)','1309918478e9a38d60b6245f6534453c956ecb7d939d0b3be0f6611a454a60bb'),
    ('erp.post_sales_return(uuid)','4c73f8b6c72a31782d4d626a0227e4f3738ab8e437a4f88de3238984fe6ac818'),
    ('erp.reverse_sale(uuid,text)','ec3011dde09fe24078fbe5aac054aaf1c827193e2b7b12c652d53f149879bc4b'),
    ('erp.reverse_sales_return(uuid,text)','5a6436ec0cc91ecb9c5b7ac20d0e74cf81904e90e73733bebf46231a8e056782'),
    ('erp.run_v268_financial_report_checks()','808d9f982d82123d6589536029bd95c1a5dc3faa93a47c08304b04cefca9add0'),
    ('erp.compute_po_hpp_gl_targets_v2620d(uuid)','77b5b531d484bcb4c1532e529e8b5269f1afab438ca16d0b1dc7f0f143efc53e'),
    ('erp.sale_lifecycle_po_hpp_amount_v2620d(uuid,uuid)','ec051d7014e620ffcb219faaa0ed21bd0f4b7674aff6ba977f773ba4a2ee714a'),
    ('erp.sync_po_hpp_to_gl(uuid,date)','d7899da2ab15841a906d5f5c55e5608ed1eb3a9636254f50018178ece462fd6c')
  ) expected(object_identity,sha256)
  loop
    if to_regprocedure(r.object_identity) is null then
      raise exception 'ERP v2.6.20e predecessor function is missing: %',r.object_identity;
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

create table erp.cp6_v2620e_rollback_capsule(
  object_identity text primary key,
  object_regidentity text not null unique,
  object_definition text not null,
  definition_sha256 text not null,
  installed_definition_sha256 text,
  acl_snapshot text[],
  owner_snapshot text not null,
  captured_at timestamptz not null default clock_timestamp()
);
alter table erp.cp6_v2620e_rollback_capsule enable row level security;
revoke all on table erp.cp6_v2620e_rollback_capsule
  from public,anon,authenticated,service_role;

insert into erp.cp6_v2620e_rollback_capsule(
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
  'erp.post_sale(uuid)'::regprocedure,
  'erp.post_sales_return(uuid)'::regprocedure,
  'erp.reverse_sale(uuid,text)'::regprocedure,
  'erp.reverse_sales_return(uuid,text)'::regprocedure,
  'erp.run_v268_financial_report_checks()'::regprocedure
);

do $capsule_guard$
begin
  if (select count(*) from erp.cp6_v2620e_rollback_capsule)<>8
     or exists(
       select 1 from erp.cp6_v2620e_rollback_capsule c
       where c.definition_sha256 is distinct from encode(extensions.digest(
         convert_to(c.object_definition,'UTF8'),'sha256'
       ),'hex')
     ) then
    raise exception 'ERP v2.6.20e exact rollback capsule is incomplete or corrupt';
  end if;
end
$capsule_guard$;

-- D's allocation row remains immutable. E imports it as an allocation event,
-- and a later cancellation appends a release event. Reassignment is a new
-- allocation event, so the physical history is never erased or overwritten.
create table erp.laundry_redispatch_participant_events(
  id uuid primary key default gen_random_uuid(),
  event_type text not null check(event_type in('ALLOCATE','RELEASE')),
  source_delivery_batch_size_line_id uuid
    references erp.laundry_delivery_batch_size_lines(id) on delete restrict,
  successor_delivery_batch_size_line_id uuid
    references erp.laundry_delivery_batch_size_lines(id) on delete restrict,
  source_offset_pcs integer,
  successor_offset_pcs integer,
  qty_pcs integer,
  releases_allocation_event_id uuid
    references erp.laundry_redispatch_participant_events(id) on delete restrict,
  released_delivery_id uuid
    references erp.laundry_deliveries(id) on delete restrict,
  predecessor_allocation_id uuid unique
    references erp.laundry_redispatch_participant_allocations(id) on delete restrict,
  event_basis text not null check(event_basis in(
    'V2620D_IMPORT','MIGRATION_RECONCILE','LIVE_FIFO','SUCCESSOR_CANCELLED_BEFORE_RECEIPT'
  )),
  created_by uuid not null references erp.app_users(id) on delete restrict,
  created_at timestamptz not null default clock_timestamp(),
  check(
    (event_type='ALLOCATE'
      and source_delivery_batch_size_line_id is not null
      and successor_delivery_batch_size_line_id is not null
      and source_offset_pcs>=0 and successor_offset_pcs>=0 and qty_pcs>0
      and releases_allocation_event_id is null and released_delivery_id is null
      and source_delivery_batch_size_line_id<>successor_delivery_batch_size_line_id)
    or
    (event_type='RELEASE'
      and source_delivery_batch_size_line_id is null
      and successor_delivery_batch_size_line_id is null
      and source_offset_pcs is null and successor_offset_pcs is null and qty_pcs is null
      and releases_allocation_event_id is not null and released_delivery_id is not null
      and predecessor_allocation_id is null)
  )
);
create unique index uq_laundry_redispatch_release_once_v2620e
  on erp.laundry_redispatch_participant_events(releases_allocation_event_id)
  where event_type='RELEASE';
create index idx_laundry_redispatch_event_source_v2620e
  on erp.laundry_redispatch_participant_events(
    source_delivery_batch_size_line_id,source_offset_pcs,id
  ) where event_type='ALLOCATE';
create index idx_laundry_redispatch_event_successor_v2620e
  on erp.laundry_redispatch_participant_events(
    successor_delivery_batch_size_line_id,successor_offset_pcs,id
  ) where event_type='ALLOCATE';
alter table erp.laundry_redispatch_participant_events enable row level security;
revoke all on table erp.laundry_redispatch_participant_events
  from public,anon,authenticated,service_role;

insert into erp.laundry_redispatch_participant_events(
  event_type,source_delivery_batch_size_line_id,
  successor_delivery_batch_size_line_id,source_offset_pcs,
  successor_offset_pcs,qty_pcs,predecessor_allocation_id,event_basis,
  created_by,created_at
)
select 'ALLOCATE',a.source_delivery_batch_size_line_id,
  a.successor_delivery_batch_size_line_id,a.source_offset_pcs,
  a.successor_offset_pcs,a.qty_pcs,a.id,'V2620D_IMPORT',a.created_by,a.created_at
from erp.laundry_redispatch_participant_allocations a
order by a.created_at,a.id;

insert into erp.laundry_redispatch_participant_events(
  event_type,releases_allocation_event_id,released_delivery_id,event_basis,
  created_by,created_at
)
select 'RELEASE',a.id,d.id,'SUCCESSOR_CANCELLED_BEFORE_RECEIPT',d.created_by,
  clock_timestamp()
from erp.laundry_redispatch_participant_events a
join erp.laundry_delivery_batch_size_lines sx
  on sx.id=a.successor_delivery_batch_size_line_id
join erp.laundry_delivery_lines dl on dl.id=sx.delivery_line_id
join erp.laundry_deliveries d on d.id=dl.delivery_id and d.status='REVERSED'
where a.event_type='ALLOCATE'
  and not exists(select 1 from erp.laundry_receipts r where r.delivery_id=d.id)
order by a.created_at,a.id;

create function erp._allocate_laundry_redispatch_participants_v2620e(
  p_delivery_line_id uuid,p_migration_reconcile boolean
)
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
  v_source_start integer;
  v_source_end integer;
  v_successor_start integer;
  v_successor_end integer;
begin
  if not p_migration_reconcile then perform erp.require_internal(); end if;
  for d in
    select sx.*,dl.cutting_group_id successor_group_id,ld.id successor_delivery_id,
      ld.physical_at successor_at,ld.created_at successor_created_at
    from erp.laundry_delivery_batch_size_lines sx
    join erp.laundry_delivery_lines dl on dl.id=sx.delivery_line_id
    join erp.laundry_deliveries ld on ld.id=dl.delivery_id
      and ((not p_migration_reconcile and ld.status='DRAFT')
        or (p_migration_reconcile and ld.status<>'REVERSED'))
    where sx.delivery_line_id=p_delivery_line_id
    order by sx.size_id,sx.id
  loop
    perform pg_advisory_xact_lock(hashtextextended(
      'CP6_REDISPATCH_V2620E:'||d.distribution_batch_id::text||':'||d.size_id::text,0
    ));
    select d.qty_sent_pcs-coalesce(sum(a.qty_pcs),0)::integer into v_remaining
    from erp.laundry_redispatch_participant_events a
    where a.event_type='ALLOCATE'
      and a.successor_delivery_batch_size_line_id=d.id
      and not exists(
        select 1 from erp.laundry_redispatch_participant_events x
        where x.event_type='RELEASE' and x.releases_allocation_event_id=a.id
      );
    if v_remaining<=0 then continue; end if;

    for s in
      select sx.id,sx.qty_sent_pcs,returned.return_at,returned.attempt_id
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
        and sx.qty_sent_pcs>coalesce((
          select sum(a.qty_pcs)
          from erp.laundry_redispatch_participant_events a
          where a.event_type='ALLOCATE'
            and a.source_delivery_batch_size_line_id=sx.id
            and not exists(
              select 1 from erp.laundry_redispatch_participant_events x
              where x.event_type='RELEASE' and x.releases_allocation_event_id=a.id
            )
        ),0)
      order by returned.return_at,returned.attempt_id,sx.id
    loop
      loop
        exit when v_remaining<=0;
        with occupied as(
          select a.source_offset_pcs start_pcs,a.source_offset_pcs+a.qty_pcs end_pcs
          from erp.laundry_redispatch_participant_events a
          where a.event_type='ALLOCATE'
            and a.source_delivery_batch_size_line_id=s.id
            and not exists(
              select 1 from erp.laundry_redispatch_participant_events x
              where x.event_type='RELEASE' and x.releases_allocation_event_id=a.id
            )
        ), candidates as(
          select 0::integer start_pcs union select end_pcs from occupied
        ), free_ranges as(
          select c.start_pcs,
            least(coalesce((select min(o.start_pcs) from occupied o
              where o.start_pcs>=c.start_pcs),s.qty_sent_pcs),s.qty_sent_pcs)::integer end_pcs
          from candidates c
          where c.start_pcs<s.qty_sent_pcs
            and not exists(select 1 from occupied o
              where c.start_pcs>=o.start_pcs and c.start_pcs<o.end_pcs)
        )
        select start_pcs,end_pcs into v_source_start,v_source_end
        from free_ranges where end_pcs>start_pcs order by start_pcs limit 1;
        exit when v_source_start is null;

        with occupied as(
          select a.successor_offset_pcs start_pcs,a.successor_offset_pcs+a.qty_pcs end_pcs
          from erp.laundry_redispatch_participant_events a
          where a.event_type='ALLOCATE'
            and a.successor_delivery_batch_size_line_id=d.id
            and not exists(
              select 1 from erp.laundry_redispatch_participant_events x
              where x.event_type='RELEASE' and x.releases_allocation_event_id=a.id
            )
        ), candidates as(
          select 0::integer start_pcs union select end_pcs from occupied
        ), free_ranges as(
          select c.start_pcs,
            least(coalesce((select min(o.start_pcs) from occupied o
              where o.start_pcs>=c.start_pcs),d.qty_sent_pcs),d.qty_sent_pcs)::integer end_pcs
          from candidates c
          where c.start_pcs<d.qty_sent_pcs
            and not exists(select 1 from occupied o
              where c.start_pcs>=o.start_pcs and c.start_pcs<o.end_pcs)
        )
        select start_pcs,end_pcs into v_successor_start,v_successor_end
        from free_ranges where end_pcs>start_pcs order by start_pcs limit 1;
        exit when v_successor_start is null;

        v_take:=least(v_remaining,v_source_end-v_source_start,
          v_successor_end-v_successor_start);
        insert into erp.laundry_redispatch_participant_events(
          event_type,source_delivery_batch_size_line_id,
          successor_delivery_batch_size_line_id,source_offset_pcs,
          successor_offset_pcs,qty_pcs,event_basis,created_by
        ) values(
          'ALLOCATE',s.id,d.id,v_source_start,v_successor_start,v_take,
          case when p_migration_reconcile then 'MIGRATION_RECONCILE' else 'LIVE_FIFO' end,
          case when p_migration_reconcile then
            (select created_by from erp.laundry_deliveries where id=d.successor_delivery_id)
          else erp.current_app_user_id() end
        );
        v_remaining:=v_remaining-v_take;
      end loop;
      exit when v_remaining<=0;
    end loop;
  end loop;
end
$function$;
alter function erp._allocate_laundry_redispatch_participants_v2620e(uuid,boolean)
  owner to postgres;
revoke all on function erp._allocate_laundry_redispatch_participants_v2620e(uuid,boolean)
  from public,anon,authenticated,service_role;

create function erp.allocate_laundry_redispatch_participants_v2620e(
  p_delivery_line_id uuid
)
returns void
language plpgsql
security definer
set search_path=''
as $function$
begin
  perform erp.require_internal();
  perform erp._allocate_laundry_redispatch_participants_v2620e(
    p_delivery_line_id,false
  );
end
$function$;
alter function erp.allocate_laundry_redispatch_participants_v2620e(uuid)
  owner to postgres;
revoke all on function erp.allocate_laundry_redispatch_participants_v2620e(uuid)
  from public,anon,authenticated,service_role;

do $reconcile_redispatch_events_v2620e$
declare r record;
begin
  for r in
    select dl.id
    from erp.laundry_delivery_lines dl
    join erp.laundry_deliveries d on d.id=dl.delivery_id and d.status<>'REVERSED'
    order by d.physical_at,d.created_at,d.id,dl.id
  loop
    perform erp._allocate_laundry_redispatch_participants_v2620e(r.id,true);
  end loop;
end
$reconcile_redispatch_events_v2620e$;

create function erp.guard_laundry_redispatch_participant_event_v2620e()
returns trigger
language plpgsql
security definer
set search_path=''
as $function$
declare
  v_source record;
  v_successor record;
  v_allocation record;
begin
  perform erp.require_internal();
  if tg_op<>'INSERT' then
    raise exception using errcode='42501',
      message='REDISPATCH_PARTICIPANT_EVENT_IS_APPEND_ONLY';
  end if;
  if new.event_type='ALLOCATE' then
    if new.event_basis<>'LIVE_FIFO' then
      raise exception 'Live redispatch allocation requires LIVE_FIFO basis';
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
    if v_source.id is null or v_successor.id is null
       or v_source.distribution_batch_id<>v_successor.distribution_batch_id
       or v_source.size_id<>v_successor.size_id
       or v_source.cutting_group_id<>v_successor.cutting_group_id
       or v_source.delivery_status<>'REVERSED'
       or v_successor.delivery_status<>'DRAFT'
       or (v_source.delivery_at,v_source.delivery_created_at,v_source.delivery_id)
          >=(v_successor.delivery_at,v_successor.delivery_created_at,v_successor.delivery_id)
       or new.source_offset_pcs+new.qty_pcs>v_source.qty_sent_pcs
       or new.successor_offset_pcs+new.qty_pcs>v_successor.qty_sent_pcs
       or new.created_by is distinct from erp.current_app_user_id()
       or not exists(
         select 1 from erp.laundry_failed_wash_attempts a
         join erp.laundry_failed_wash_batch_size_lines ax
           on ax.attempt_id=a.id
          and ax.delivery_batch_size_line_id=v_source.id
          and ax.qty_attempted_pcs=v_source.qty_sent_pcs
         join erp.laundry_receipts r on r.id=a.receipt_id and r.status='POSTED'
         where a.delivery_id=v_source.delivery_id
           and a.custody_outcome='RETURN_UNPROCESSED'
           and r.physical_at<=v_successor.delivery_at
       ) then
      raise exception 'Redispatch allocation event requires one exact returned source interval and a same-source Draft successor';
    end if;
    if exists(
      select 1 from erp.laundry_redispatch_participant_events a
      where a.event_type='ALLOCATE'
        and not exists(select 1 from erp.laundry_redispatch_participant_events x
          where x.event_type='RELEASE' and x.releases_allocation_event_id=a.id)
        and ((a.source_delivery_batch_size_line_id=new.source_delivery_batch_size_line_id
          and int4range(a.source_offset_pcs,a.source_offset_pcs+a.qty_pcs,'[)')
            && int4range(new.source_offset_pcs,new.source_offset_pcs+new.qty_pcs,'[)'))
          or (a.successor_delivery_batch_size_line_id=new.successor_delivery_batch_size_line_id
          and int4range(a.successor_offset_pcs,a.successor_offset_pcs+a.qty_pcs,'[)')
            && int4range(new.successor_offset_pcs,new.successor_offset_pcs+new.qty_pcs,'[)')))
    ) then
      raise exception 'Effective redispatch participant intervals may not overlap';
    end if;
  else
    select a.*,d.id successor_delivery_id,d.status successor_status
    into v_allocation
    from erp.laundry_redispatch_participant_events a
    join erp.laundry_delivery_batch_size_lines sx
      on sx.id=a.successor_delivery_batch_size_line_id
    join erp.laundry_delivery_lines dl on dl.id=sx.delivery_line_id
    join erp.laundry_deliveries d on d.id=dl.delivery_id
    where a.id=new.releases_allocation_event_id and a.event_type='ALLOCATE'
    for update of a,d;
    if v_allocation.id is null
       or v_allocation.successor_delivery_id<>new.released_delivery_id
       or v_allocation.successor_status<>'REVERSED'
       or new.event_basis<>'SUCCESSOR_CANCELLED_BEFORE_RECEIPT'
       or new.created_by is distinct from erp.current_app_user_id()
       or exists(select 1 from erp.laundry_receipts r
         where r.delivery_id=new.released_delivery_id) then
      raise exception 'Redispatch release requires an actual successor cancellation before any receipt/attempt';
    end if;
  end if;
  return new;
end
$function$;
alter function erp.guard_laundry_redispatch_participant_event_v2620e()
  owner to postgres;
revoke all on function erp.guard_laundry_redispatch_participant_event_v2620e()
  from public,anon,authenticated,service_role;

create function erp.record_laundry_redispatch_release_v2620e()
returns trigger
language plpgsql
security definer
set search_path=''
as $function$
begin
  perform erp.require_internal();
  if old.status is distinct from new.status and new.status='REVERSED'
     and not exists(select 1 from erp.laundry_receipts r where r.delivery_id=new.id) then
    insert into erp.laundry_redispatch_participant_events(
      event_type,releases_allocation_event_id,released_delivery_id,event_basis,
      created_by
    )
    select 'RELEASE',a.id,new.id,'SUCCESSOR_CANCELLED_BEFORE_RECEIPT',
      erp.current_app_user_id()
    from erp.laundry_redispatch_participant_events a
    join erp.laundry_delivery_batch_size_lines sx
      on sx.id=a.successor_delivery_batch_size_line_id
    join erp.laundry_delivery_lines dl on dl.id=sx.delivery_line_id
    where a.event_type='ALLOCATE' and dl.delivery_id=new.id
      and not exists(select 1 from erp.laundry_redispatch_participant_events x
        where x.event_type='RELEASE' and x.releases_allocation_event_id=a.id)
    order by a.created_at,a.id;
  end if;
  return new;
end
$function$;
alter function erp.record_laundry_redispatch_release_v2620e() owner to postgres;
revoke all on function erp.record_laundry_redispatch_release_v2620e()
  from public,anon,authenticated,service_role;

create trigger trg_guard_laundry_redispatch_participant_event_v2620e
before insert or update or delete on erp.laundry_redispatch_participant_events
for each row execute function erp.guard_laundry_redispatch_participant_event_v2620e();
create trigger trg_audit_laundry_redispatch_participant_event_v2620e
after insert on erp.laundry_redispatch_participant_events
for each row execute function erp.audit_row_change();
create trigger trg_release_laundry_redispatch_participant_v2620e
after update of status on erp.laundry_deliveries
for each row execute function erp.record_laundry_redispatch_release_v2620e();

do $patch_laundry_writer_v2620e$
declare
  v_definition text;
  v_anchor constant text:='erp.allocate_laundry_redispatch_participants_v2620d';
  v_replacement constant text:='erp.allocate_laundry_redispatch_participants_v2620e';
begin
  select pg_get_functiondef(
    'erp.save_laundry_qc_action_v1(text,jsonb,uuid,bigint)'::regprocedure
  ) into v_definition;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>2 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: v2.6.20e redispatch writer anchors are not exact';
  end if;
  execute replace(v_definition,v_anchor,v_replacement);
end
$patch_laundry_writer_v2620e$;

create function erp.cp6_lot_failed_wash_cost_v2620e(p_lot_id uuid)
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
), effective_allocations as(
  select a.*
  from erp.laundry_redispatch_participant_events a
  where a.event_type='ALLOCATE'
    and not exists(select 1 from erp.laundry_redispatch_participant_events x
      where x.event_type='RELEASE' and x.releases_allocation_event_id=a.id)
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
  join effective_allocations a
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
alter function erp.cp6_lot_failed_wash_cost_v2620e(uuid) owner to postgres;
revoke all on function erp.cp6_lot_failed_wash_cost_v2620e(uuid)
  from public,anon,authenticated,service_role;

do $patch_hpp_redispatch_cost_v2620e$
declare
  v_definition text;
  v_anchor constant text:='erp.cp6_lot_failed_wash_cost_v2620d(r.id)';
  v_replacement constant text:='erp.cp6_lot_failed_wash_cost_v2620e(r.id)';
begin
  select pg_get_functiondef('erp.rebuild_po_hpp(uuid,text)'::regprocedure)
    into v_definition;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: v2.6.20e failed-wash resolver anchor is not exact';
  end if;
  execute replace(v_definition,v_anchor,v_replacement);
end
$patch_hpp_redispatch_cost_v2620e$;

-- Read the actual PO book directly for every dimensioned journal line. Only
-- legacy Sale/return journals with no PO dimension at all use D's deterministic
-- historical attribution. This permits a valid Sale to carry both PO and
-- opening-stock HPP, and permits a cent carry to move between disposition and
-- COGS without manufacturing value.
create function erp.compute_po_hpp_gl_book_v2620e(p_po_id uuid)
returns table(fg_value numeric,cogs_value numeric,other_out_value numeric)
language sql
stable
security definer
set search_path=''
as $function$
with lifecycle as(
  select e.id
  from erp.journal_entries e
  left join erp.journal_entries o on o.id=e.reversal_of_id
  where e.status in('POSTED','REVERSED') and(
    e.source_type in('SALE','SALES_RETURN')
    or(e.source_type='JOURNAL_REVERSAL' and o.source_type in('SALE','SALES_RETURN'))
  )
), historical_untagged as(
  select l.id
  from lifecycle l
  where not exists(
    select 1 from erp.journal_lines x
    where x.journal_entry_id=l.id
      and x.account_id in(
        erp.account_id('FG_INVENTORY'),erp.account_id('COGS'),
        erp.account_id('OTHER_EXPENSE'),erp.account_id('OTHER_INCOME')
      ) and x.po_id is not null
  ) and exists(
    select 1
    from erp.journal_entries e
    left join erp.journal_entries o on o.id=e.reversal_of_id
    where e.id=l.id and(
      (coalesce(o.source_type,e.source_type)='SALE' and exists(
        select 1 from erp.sale_stock_allocations a
        join erp.sales_items i on i.id=a.sale_item_id
        join erp.fg_lots fl on fl.id=a.lot_id
        where i.sale_id=coalesce(o.source_id,e.source_id) and fl.po_id=p_po_id
      )) or
      (coalesce(o.source_type,e.source_type)='SALES_RETURN' and exists(
        select 1 from erp.sales_return_items i
        join erp.fg_lots fl on fl.id=i.lot_id
        where i.return_id=coalesce(o.source_id,e.source_id) and fl.po_id=p_po_id
      ))
    )
  )
), historical_book as(
  select coalesce(sum(
    erp.sale_lifecycle_po_hpp_amount_v2620d(id,p_po_id)
  ),0)::numeric cogs
  from historical_untagged
), direct_book as(
  select
    coalesce(sum(l.debit-l.credit) filter(
      where l.account_id=erp.account_id('FG_INVENTORY')),0)::numeric fg,
    coalesce(sum(l.debit-l.credit) filter(
      where l.account_id=erp.account_id('COGS')),0)::numeric cogs,
    coalesce(sum(l.debit-l.credit) filter(
      where l.account_id in(
        erp.account_id('OTHER_EXPENSE'),erp.account_id('OTHER_INCOME')
      )),0)::numeric other_out
  from erp.journal_lines l
  join erp.journal_entries e on e.id=l.journal_entry_id
    and e.status in('POSTED','REVERSED')
  where l.po_id=p_po_id
), residual_close as(
  select coalesce(sum(e.residual_amount),0)::numeric amount
  from erp.po_wip_close_events e
  join erp.journal_entries j on j.id=e.journal_entry_id
    and j.source_type='PO_WIP_RESIDUAL_CLOSE' and j.status='POSTED'
  where e.po_id=p_po_id
)
select round(d.fg-h.cogs,2),round(d.cogs+h.cogs,2),
  round(d.other_out-c.amount,2)
from direct_book d cross join historical_book h cross join residual_close c
$function$;
alter function erp.compute_po_hpp_gl_book_v2620e(uuid) owner to postgres;
revoke all on function erp.compute_po_hpp_gl_book_v2620e(uuid)
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
  select * into b from erp.compute_po_hpp_gl_book_v2620e(p_po_id);
  if coalesce(t.base_output_qty,0)<=0
     and not exists(select 1 from erp.po_hpp_gl_state where po_id=p_po_id)
     and abs(coalesce(b.fg_value,0))+abs(coalesce(b.cogs_value,0))
         +abs(coalesce(b.other_out_value,0))<=0.005 then
    return;
  end if;
  v_hpp:=round(coalesce(b.fg_value,0)+coalesce(b.cogs_value,0)
    +coalesce(b.other_out_value,0),2);
  insert into erp.po_hpp_gl_state(
    po_id,base_output_qty,hpp_total_cost,fg_value,cogs_value,
    other_out_value,updated_at
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

create function erp.assert_po_hpp_target_book_v2620e(p_po_id uuid)
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
  select * into b from erp.compute_po_hpp_gl_book_v2620e(p_po_id);
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
    raise exception 'PO_HPP_TARGET_BOOK_MISMATCH_V2620E for PO %',p_po_id;
  end if;
end
$function$;
alter function erp.assert_po_hpp_target_book_v2620e(uuid) owner to postgres;
revoke all on function erp.assert_po_hpp_target_book_v2620e(uuid)
  from public,anon,authenticated,service_role;

do $patch_post_sale_v2620e$
declare
  v_definition text;
  v_anchor text;
  v_replacement text;
begin
  select pg_get_functiondef('erp.post_sale(uuid)'::regprocedure) into v_definition;

  v_anchor:=$anchor$  v_delta_cogs numeric(24,6);
  v_delta_fg numeric(24,6);$anchor$;
  v_replacement:=$replacement$  v_delta_cogs numeric(24,6);
  v_delta_fg numeric(24,6);
  v_delta_other numeric(24,6);$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: Sale delta declaration anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$  end if;

  for r in
    select distinct fl.po_id
    from erp.sale_stock_allocations a
    join erp.sales_items i on i.id=a.sale_item_id
    join erp.fg_lots fl on fl.id=a.lot_id
    where i.sale_id=h.id and fl.po_id is not null
    order by fl.po_id
  loop
    perform erp.refresh_po_hpp_gl_baseline(r.po_id);
    select$anchor$;
  v_replacement:=$replacement$  end if;

  -- Opening and any future non-PO FG origin keeps its frozen transaction HPP.
  -- Cumulative slices conserve the exact rounded total across multiple lots.
  for r in
    with weights as(
      select fl.id lot_id,fl.product_id,
        sum(a.qty_pcs*a.unit_hpp_snapshot)::numeric raw_value
      from erp.sale_stock_allocations a
      join erp.sales_items i on i.id=a.sale_item_id
      join erp.fg_lots fl on fl.id=a.lot_id
      where i.sale_id=h.id and fl.po_id is null
      group by fl.id,fl.product_id
    ), ordered as(
      select w.*,
        sum(raw_value) over(order by lot_id rows unbounded preceding) cumulative_value
      from weights w
    )
    select product_id,
      round(cumulative_value,2)-round(cumulative_value-raw_value,2) hpp_value
    from ordered order by lot_id
  loop
    if abs(r.hpp_value)>0.005 then
      v_lines:=v_lines||jsonb_build_array(
        jsonb_build_object('mapping_key','COGS','debit',r.hpp_value,'credit',0,
          'customer_id',h.customer_id,'product_id',r.product_id),
        jsonb_build_object('mapping_key','FG_INVENTORY','debit',0,'credit',r.hpp_value,
          'customer_id',h.customer_id,'product_id',r.product_id));
    end if;
  end loop;

  for r in
    select distinct fl.po_id
    from erp.sale_stock_allocations a
    join erp.sales_items i on i.id=a.sale_item_id
    join erp.fg_lots fl on fl.id=a.lot_id
    where i.sale_id=h.id and fl.po_id is not null
    order by fl.po_id
  loop
    perform erp.refresh_po_hpp_gl_baseline(r.po_id);
    select$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: Sale non-PO HPP anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$      round(coalesce(t.cogs_value,0),2)-s.cogs_value,
      round(coalesce(t.fg_value,0),2)-s.fg_value,
      round(coalesce(t.hpp_total_cost,0),2),
      round(coalesce(t.hpp_total_cost,0),2)-round(coalesce(t.fg_value,0),2)-round(coalesce(t.cogs_value,0),2),
      s.hpp_total_cost,s.other_out_value
    into v_delta_cogs,v_delta_fg,v_target_hpp,v_target_other,v_book_hpp,v_book_other$anchor$;
  v_replacement:=$replacement$      round(coalesce(t.cogs_value,0),2)-s.cogs_value,
      round(coalesce(t.fg_value,0),2)-s.fg_value,
      (round(coalesce(t.hpp_total_cost,0),2)-round(coalesce(t.fg_value,0),2)
        -round(coalesce(t.cogs_value,0),2))-s.other_out_value,
      round(coalesce(t.hpp_total_cost,0),2),
      round(coalesce(t.hpp_total_cost,0),2)-round(coalesce(t.fg_value,0),2)-round(coalesce(t.cogs_value,0),2),
      s.hpp_total_cost,s.other_out_value
    into v_delta_cogs,v_delta_fg,v_delta_other,
      v_target_hpp,v_target_other,v_book_hpp,v_book_other$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: Sale cumulative target anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$    if v_delta_cogs<-0.005 or v_delta_fg>0.005
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
    end if;$anchor$;
  v_replacement:=$replacement$    if v_delta_cogs<-0.005 or v_delta_fg>0.005
       or abs(v_delta_cogs+v_delta_fg+v_delta_other)>0.005
       or v_target_hpp is distinct from v_book_hpp then
      raise exception 'Sale cumulative HPP target does not conserve PO value %. dc %, df %, do %, target/book hpp %/%',
        r.po_id,v_delta_cogs,v_delta_fg,v_delta_other,v_target_hpp,v_book_hpp;
    end if;
    if abs(v_delta_cogs)>0.005 then
      v_lines:=v_lines||jsonb_build_array(case when v_delta_cogs>0 then
        jsonb_build_object('mapping_key','COGS','debit',v_delta_cogs,'credit',0,
          'customer_id',h.customer_id,'po_id',r.po_id)
        else jsonb_build_object('mapping_key','COGS','debit',0,'credit',abs(v_delta_cogs),
          'customer_id',h.customer_id,'po_id',r.po_id) end);
    end if;
    if abs(v_delta_fg)>0.005 then
      v_lines:=v_lines||jsonb_build_array(case when v_delta_fg>0 then
        jsonb_build_object('mapping_key','FG_INVENTORY','debit',v_delta_fg,'credit',0,
          'customer_id',h.customer_id,'po_id',r.po_id)
        else jsonb_build_object('mapping_key','FG_INVENTORY','debit',0,'credit',abs(v_delta_fg),
          'customer_id',h.customer_id,'po_id',r.po_id) end);
    end if;
    if abs(v_delta_other)>0.005 then
      v_lines:=v_lines||jsonb_build_array(case when v_delta_other>0 then
        jsonb_build_object('mapping_key','OTHER_EXPENSE','debit',v_delta_other,'credit',0,
          'customer_id',h.customer_id,'po_id',r.po_id)
        else jsonb_build_object('mapping_key','OTHER_INCOME','debit',0,'credit',abs(v_delta_other),
          'customer_id',h.customer_id,'po_id',r.po_id) end);
    end if;$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: Sale conserved-delta anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:='erp.assert_po_hpp_target_book_v2620d(r.po_id)';
  v_replacement:='erp.assert_po_hpp_target_book_v2620e(r.po_id)';
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: Sale target/book assertion anchor is not exact';
  end if;
  execute replace(v_definition,v_anchor,v_replacement);
end
$patch_post_sale_v2620e$;

do $patch_post_sales_return_v2620e$
declare
  v_definition text;
  v_anchor text;
  v_replacement text;
begin
  select pg_get_functiondef('erp.post_sales_return(uuid)'::regprocedure)
    into v_definition;

  v_anchor:=$anchor$  v_delta_cogs numeric(24,6);
  v_delta_fg numeric(24,6);$anchor$;
  v_replacement:=$replacement$  v_delta_cogs numeric(24,6);
  v_delta_fg numeric(24,6);
  v_delta_other numeric(24,6);$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: return delta declaration anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:='v_prior_product_refund+v_current_product_refund>v_product_sale_value+0.01';
  v_replacement:='v_prior_product_refund+v_current_product_refund>v_product_sale_value';
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: exact refund ceiling anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$  end if;

  for r in
    select distinct fl.po_id
    from erp.sales_return_items i join erp.fg_lots fl on fl.id=i.lot_id
    where i.return_id=h.id and fl.po_id is not null order by fl.po_id
  loop
    perform erp.refresh_po_hpp_gl_baseline(r.po_id);
    select$anchor$;
  v_replacement:=$replacement$  end if;

  for r in
    with weights as(
      select fl.id lot_id,fl.product_id,
        sum(i.qty_pcs*i.unit_hpp_snapshot)::numeric raw_value
      from erp.sales_return_items i
      join erp.fg_lots fl on fl.id=i.lot_id
      where i.return_id=h.id and fl.po_id is null
      group by fl.id,fl.product_id
    ), ordered as(
      select w.*,
        sum(raw_value) over(order by lot_id rows unbounded preceding) cumulative_value
      from weights w
    )
    select product_id,
      round(cumulative_value,2)-round(cumulative_value-raw_value,2) hpp_value
    from ordered order by lot_id
  loop
    if abs(r.hpp_value)>0.005 then
      v_lines:=v_lines||jsonb_build_array(
        jsonb_build_object('mapping_key','FG_INVENTORY','debit',r.hpp_value,'credit',0,
          'customer_id',h.customer_id,'product_id',r.product_id),
        jsonb_build_object('mapping_key','COGS','debit',0,'credit',r.hpp_value,
          'customer_id',h.customer_id,'product_id',r.product_id));
    end if;
  end loop;

  for r in
    select distinct fl.po_id
    from erp.sales_return_items i join erp.fg_lots fl on fl.id=i.lot_id
    where i.return_id=h.id and fl.po_id is not null order by fl.po_id
  loop
    perform erp.refresh_po_hpp_gl_baseline(r.po_id);
    select$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: return non-PO HPP anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$      round(coalesce(t.cogs_value,0),2)-st.cogs_value,
      round(coalesce(t.fg_value,0),2)-st.fg_value,
      round(coalesce(t.hpp_total_cost,0),2),
      round(coalesce(t.hpp_total_cost,0),2)-round(coalesce(t.fg_value,0),2)-round(coalesce(t.cogs_value,0),2),
      st.hpp_total_cost,st.other_out_value
    into v_delta_cogs,v_delta_fg,v_target_hpp,v_target_other,v_book_hpp,v_book_other$anchor$;
  v_replacement:=$replacement$      round(coalesce(t.cogs_value,0),2)-st.cogs_value,
      round(coalesce(t.fg_value,0),2)-st.fg_value,
      (round(coalesce(t.hpp_total_cost,0),2)-round(coalesce(t.fg_value,0),2)
        -round(coalesce(t.cogs_value,0),2))-st.other_out_value,
      round(coalesce(t.hpp_total_cost,0),2),
      round(coalesce(t.hpp_total_cost,0),2)-round(coalesce(t.fg_value,0),2)-round(coalesce(t.cogs_value,0),2),
      st.hpp_total_cost,st.other_out_value
    into v_delta_cogs,v_delta_fg,v_delta_other,
      v_target_hpp,v_target_other,v_book_hpp,v_book_other$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: return cumulative target anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$    if v_delta_cogs>0.005 or v_delta_fg<-0.005
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
    end if;$anchor$;
  v_replacement:=$replacement$    if v_delta_cogs>0.005 or v_delta_fg<-0.005
       or abs(v_delta_cogs+v_delta_fg+v_delta_other)>0.005
       or v_target_hpp is distinct from v_book_hpp then
      raise exception 'Sales-return cumulative HPP target does not conserve PO value %. dc %, df %, do %, target/book hpp %/%',
        r.po_id,v_delta_cogs,v_delta_fg,v_delta_other,v_target_hpp,v_book_hpp;
    end if;
    if abs(v_delta_cogs)>0.005 then
      v_lines:=v_lines||jsonb_build_array(case when v_delta_cogs>0 then
        jsonb_build_object('mapping_key','COGS','debit',v_delta_cogs,'credit',0,
          'customer_id',h.customer_id,'po_id',r.po_id)
        else jsonb_build_object('mapping_key','COGS','debit',0,'credit',abs(v_delta_cogs),
          'customer_id',h.customer_id,'po_id',r.po_id) end);
    end if;
    if abs(v_delta_fg)>0.005 then
      v_lines:=v_lines||jsonb_build_array(case when v_delta_fg>0 then
        jsonb_build_object('mapping_key','FG_INVENTORY','debit',v_delta_fg,'credit',0,
          'customer_id',h.customer_id,'po_id',r.po_id)
        else jsonb_build_object('mapping_key','FG_INVENTORY','debit',0,'credit',abs(v_delta_fg),
          'customer_id',h.customer_id,'po_id',r.po_id) end);
    end if;
    if abs(v_delta_other)>0.005 then
      v_lines:=v_lines||jsonb_build_array(case when v_delta_other>0 then
        jsonb_build_object('mapping_key','OTHER_EXPENSE','debit',v_delta_other,'credit',0,
          'customer_id',h.customer_id,'po_id',r.po_id)
        else jsonb_build_object('mapping_key','OTHER_INCOME','debit',0,'credit',abs(v_delta_other),
          'customer_id',h.customer_id,'po_id',r.po_id) end);
    end if;$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: return conserved-delta anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:='erp.assert_po_hpp_target_book_v2620d(r.po_id)';
  v_replacement:='erp.assert_po_hpp_target_book_v2620e(r.po_id)';
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: return target/book assertion anchor is not exact';
  end if;
  execute replace(v_definition,v_anchor,v_replacement);
end
$patch_post_sales_return_v2620e$;

do $patch_reverse_sale_v2620e$
declare
  v_definition text;
  v_anchor text;
  v_replacement text;
begin
  select pg_get_functiondef('erp.reverse_sale(uuid,text)'::regprocedure)
    into v_definition;

  v_anchor:=$anchor$  if exists(select 1 from erp.sales_returns where sale_id=h.id and status='POSTED') then
    raise exception 'Penjualan ini sudah memiliki retur POSTED. Reverse retur aktif terlebih dahulu.';
  end if;

  select coalesce((select sum(line_total) from erp.sales_items where sale_id=h.id),0)
       +coalesce((select sum(a.qty_pcs*a.unit_hpp_snapshot)
          from erp.sale_stock_allocations a
          join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=h.id),0)
  into v_expected;$anchor$;
  v_replacement:=$replacement$  if exists(select 1 from erp.sales_returns where sale_id=h.id and status='POSTED') then
    raise exception 'Penjualan ini sudah memiliki retur POSTED. Reverse retur aktif terlebih dahulu.';
  end if;

  -- A missing PO HPP journal is corruption. A sub-cent allocation whose
  -- cumulative PO target did not move is legitimately journal-free.
  for v_po in
    select distinct fl.po_id
    from erp.sale_stock_allocations a
    join erp.sales_items i on i.id=a.sale_item_id
    join erp.fg_lots fl on fl.id=a.lot_id
    where i.sale_id=h.id and fl.po_id is not null order by fl.po_id
  loop
    perform erp.assert_po_hpp_target_book_v2620e(v_po);
  end loop;

  select round(coalesce((select sum(line_total)
           from erp.sales_items where sale_id=h.id),0),2)
       +round(coalesce((select sum(a.qty_pcs*a.unit_hpp_snapshot)
          from erp.sale_stock_allocations a
          join erp.sales_items i on i.id=a.sale_item_id
          join erp.fg_lots fl on fl.id=a.lot_id
          where i.sale_id=h.id and fl.po_id is null),0),2)
  into v_expected;$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: Sale inverse journal proof anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:='erp.assert_po_hpp_target_book_v2620d(v_po)';
  v_replacement:='erp.assert_po_hpp_target_book_v2620e(v_po)';
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: Sale inverse assertion anchor is not exact';
  end if;
  execute replace(v_definition,v_anchor,v_replacement);
end
$patch_reverse_sale_v2620e$;

do $patch_reverse_sales_return_v2620e$
declare
  v_definition text;
  v_anchor text;
  v_replacement text;
begin
  select pg_get_functiondef('erp.reverse_sales_return(uuid,text)'::regprocedure)
    into v_definition;

  v_anchor:=$anchor$  if s.id is null or s.status='REVERSED' then raise exception 'Penjualan sumber retur tidak aktif'; end if;

  select coalesce(sum(i.refund_amount+i.qty_pcs*i.unit_hpp_snapshot),0)
  into v_expected from erp.sales_return_items i where i.return_id=h.id;$anchor$;
  v_replacement:=$replacement$  if s.id is null or s.status='REVERSED' then raise exception 'Penjualan sumber retur tidak aktif'; end if;

  for v_po in
    select distinct fl.po_id
    from erp.sales_return_items i join erp.fg_lots fl on fl.id=i.lot_id
    where i.return_id=h.id and fl.po_id is not null order by fl.po_id
  loop
    perform erp.assert_po_hpp_target_book_v2620e(v_po);
  end loop;

  select round(coalesce(sum(i.refund_amount),0),2)
       +round(coalesce(sum(i.qty_pcs*i.unit_hpp_snapshot)
          filter(where fl.po_id is null),0),2)
  into v_expected
  from erp.sales_return_items i
  join erp.fg_lots fl on fl.id=i.lot_id
  where i.return_id=h.id;$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: return inverse journal proof anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:='erp.assert_po_hpp_target_book_v2620d(v_po)';
  v_replacement:='erp.assert_po_hpp_target_book_v2620e(v_po)';
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: return inverse assertion anchor is not exact';
  end if;
  execute replace(v_definition,v_anchor,v_replacement);
end
$patch_reverse_sales_return_v2620e$;

do $patch_financial_checks_v2620e$
declare
  v_definition text;
  v_anchor text;
  v_replacement text;
begin
  select pg_get_functiondef('erp.run_v268_financial_report_checks()'::regprocedure)
    into v_definition;

  v_anchor:=$anchor$  where r.check_name not in(
    'V268_BROWSER_DIRECT_FINANCIAL_WRITE',
    'V268_BROWSER_DIRECT_LEDGER_OR_INVOICE_WRITE'
  )$anchor$;
  v_replacement:=$replacement$  where r.check_name not in(
    'V268_BROWSER_DIRECT_FINANCIAL_WRITE',
    'V268_BROWSER_DIRECT_LEDGER_OR_INVOICE_WRITE',
    'V268_ACTIVE_SALE_MISSING_JOURNAL',
    'V268_POSTED_SALES_RETURN_MISSING_JOURNAL'
  )$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: report predecessor-filter anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:='erp.compute_po_hpp_gl_book_v2620d(s.po_id)';
  v_replacement:='erp.compute_po_hpp_gl_book_v2620e(s.po_id)';
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: report PO book anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$  select 'V2620C_HPP_COMPONENT_SUM_MISMATCH','CRITICAL',count(*)::bigint,
    'Every current HPP version must equal the exact sum of its traceable components'
  from erp.hpp_versions h
  where h.is_current and abs(h.total_cost-coalesce((
    select sum(c.total_cost) from erp.hpp_version_components c where c.hpp_version_id=h.id
  ),0))>0.000001$anchor$;
  v_replacement:=$replacement$  select 'V2620C_HPP_COMPONENT_SUM_MISMATCH','CRITICAL',count(*)::bigint,
    'Every current production HPP version must equal the exact sum of its traceable production components'
  from erp.hpp_versions h
  join erp.fg_lots fl on fl.id=h.lot_id and fl.lot_origin='PRODUCTION'
  where h.is_current and abs(h.total_cost-coalesce((
    select sum(c.total_cost) from erp.hpp_version_components c where c.hpp_version_id=h.id
  ),0))>0.000001$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: production component-check anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$  union all
  select 'V2620D_SALE_LIFECYCLE_HPP_DIMENSION_MISMATCH','CRITICAL',count(*)::bigint,
    'Every Sale lifecycle journal must conserve FG/COGS and use either complete PO dimensions or one attributable historical aggregate'$anchor$;
  v_replacement:=$replacement$  union all
  select 'V268_ACTIVE_SALE_MISSING_JOURNAL','CRITICAL',count(*)::bigint,
    'Every active Sale with a monetary or rounded non-PO HPP effect requires its SALE journal'
  from erp.sales_headers h
  where h.status in('POSTED','PARTIAL_PAID','PAID')
    and(round(coalesce((select sum(i.line_total) from erp.sales_items i
          where i.sale_id=h.id),0),2)>0.005
      or round(coalesce((select sum(a.qty_pcs*a.unit_hpp_snapshot)
          from erp.sale_stock_allocations a
          join erp.sales_items i on i.id=a.sale_item_id
          join erp.fg_lots fl on fl.id=a.lot_id
          where i.sale_id=h.id and fl.po_id is null),0),2)>0.005)
    and not exists(select 1 from erp.journal_entries j
      where j.source_type='SALE' and j.source_id=h.id and j.status='POSTED')

  union all
  select 'V268_POSTED_SALES_RETURN_MISSING_JOURNAL','CRITICAL',count(*)::bigint,
    'Every posted return with a monetary or rounded non-PO HPP effect requires its SALES_RETURN journal'
  from erp.sales_returns h
  where h.status='POSTED'
    and(round(coalesce((select sum(i.refund_amount)
          from erp.sales_return_items i where i.return_id=h.id),0),2)>0.005
      or round(coalesce((select sum(i.qty_pcs*i.unit_hpp_snapshot)
          from erp.sales_return_items i
          join erp.fg_lots fl on fl.id=i.lot_id
          where i.return_id=h.id and fl.po_id is null),0),2)>0.005)
    and not exists(select 1 from erp.journal_entries j
      where j.source_type='SALES_RETURN' and j.source_id=h.id and j.status='POSTED')

  union all
  select 'V2620E_NON_PO_SALE_HPP_BOOK_MISMATCH','CRITICAL',count(*)::bigint,
    'Opening/non-PO Sale and return HPP must move the exact frozen rounded amount between FG and COGS'
  from(
    select h.id,
      round(coalesce((select sum(a.qty_pcs*a.unit_hpp_snapshot)
        from erp.sale_stock_allocations a
        join erp.sales_items i on i.id=a.sale_item_id
        join erp.fg_lots fl on fl.id=a.lot_id
        where i.sale_id=h.id and fl.po_id is null),0),2) expected_cogs,
      coalesce((select sum(l.debit-l.credit)
        from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id
        where j.source_type='SALE' and j.source_id=h.id and j.status='POSTED'
          and l.account_id=erp.account_id('COGS') and l.po_id is null),0) actual_cogs,
      coalesce((select sum(l.debit-l.credit)
        from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id
        where j.source_type='SALE' and j.source_id=h.id and j.status='POSTED'
          and l.account_id=erp.account_id('FG_INVENTORY') and l.po_id is null),0) actual_fg
    from erp.sales_headers h where h.status in('POSTED','PARTIAL_PAID','PAID')
    union all
    select h.id,
      -round(coalesce((select sum(i.qty_pcs*i.unit_hpp_snapshot)
        from erp.sales_return_items i join erp.fg_lots fl on fl.id=i.lot_id
        where i.return_id=h.id and fl.po_id is null),0),2),
      coalesce((select sum(l.debit-l.credit)
        from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id
        where j.source_type='SALES_RETURN' and j.source_id=h.id and j.status='POSTED'
          and l.account_id=erp.account_id('COGS') and l.po_id is null),0),
      coalesce((select sum(l.debit-l.credit)
        from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id
        where j.source_type='SALES_RETURN' and j.source_id=h.id and j.status='POSTED'
          and l.account_id=erp.account_id('FG_INVENTORY') and l.po_id is null),0)
    from erp.sales_returns h where h.status='POSTED'
  ) non_po
  where abs(non_po.actual_cogs-non_po.expected_cogs)>0.005
     or abs(non_po.actual_fg+non_po.expected_cogs)>0.005

  union all
  select 'V2620E_SALES_RETURN_VALUE_EXCEEDS_SALE','CRITICAL',count(*)::bigint,
    'Posted cumulative product refund may never exceed the exact original product sale value'
  from(
    select sr.sale_id,i.product_id,sum(i.refund_amount)::numeric refund,
      coalesce((select sum(si.line_total) from erp.sales_items si
        where si.sale_id=sr.sale_id and si.product_id=i.product_id),0)::numeric sold
    from erp.sales_returns sr join erp.sales_return_items i on i.return_id=sr.id
    where sr.status='POSTED'
    group by sr.sale_id,i.product_id
  ) refund where refund.refund>refund.sold

  union all
  select 'V2620E_OPENING_HPP_LINEAGE_MISMATCH','CRITICAL',count(*)::bigint,
    'Opening FG HPP must follow its opening source or latest active correction and must not pretend to have production components'
  from erp.fg_lots fl
  left join lateral(
    select count(*)::integer movement_count,min(m.id::text)::uuid movement_id,
      min(m.source_id::text)::uuid source_id,min(m.qty_signed)::integer qty_signed,
      min(m.unit_hpp_snapshot)::numeric unit_hpp
    from erp.fg_stock_movements m
    where m.lot_id=fl.id and m.movement_type='OPENING'
  ) om on true
  left join erp.opening_balance_items oi on oi.id=om.source_id
  left join erp.opening_balance_headers oh on oh.id=oi.opening_id
  left join lateral(
    select count(*)::integer current_count,min(h.id::text)::uuid current_id,
      min(h.qty_basis_pcs)::integer qty_basis,min(h.total_cost)::numeric total_cost
    from erp.hpp_versions h where h.lot_id=fl.id and h.is_current
  ) ch on true
  left join lateral(
    select h.total_cost,h.qty_basis_pcs
    from erp.hpp_versions h where h.lot_id=fl.id
    order by h.version_no,h.id limit 1
  ) first_hpp on true
  left join lateral(
    select c.corrected_hpp
    from erp.opening_hpp_corrections c
    join erp.hpp_versions h on h.id=c.hpp_version_id
    where c.lot_id=fl.id and c.status='POSTED'
    order by h.version_no desc,h.id desc limit 1
  ) correction on true
  where fl.lot_origin='OPENING' and(
    om.movement_count<>1 or ch.current_count<>1
    or oi.id is null or oi.balance_type<>'FINISHED_GOODS'
    or oh.status<>'POSTED' or oi.product_id is distinct from fl.product_id
    or om.qty_signed is distinct from fl.initial_qty_pcs
    or ch.qty_basis is distinct from fl.initial_qty_pcs
    or abs(first_hpp.total_cost-fl.initial_qty_pcs*om.unit_hpp)>0.000001
    or abs(om.unit_hpp-erp.resolve_opening_fg_unit_hpp(oi.id,oh.opening_date))>0.000001
    or abs(ch.total_cost-fl.initial_qty_pcs
      *coalesce(correction.corrected_hpp,om.unit_hpp))>0.000001
    or fl.cached_qty_pcs is distinct from coalesce((
      select sum(m.qty_signed)::integer from erp.fg_stock_movements m
      where m.lot_id=fl.id
    ),0)
    or exists(select 1 from erp.hpp_version_components c
      join erp.hpp_versions h on h.id=c.hpp_version_id where h.lot_id=fl.id)
  )

  union all
  select 'V2620E_OPENING_FG_GL_MISMATCH','CRITICAL',count(*)::bigint,
    'Each posted opening document FG journal must equal its immutable opening FG movement value'
  from erp.opening_balance_headers h
  cross join lateral(
    select coalesce(sum(round(m.qty_signed*m.unit_hpp_snapshot,2)),0)::numeric expected_fg
    from erp.opening_balance_items i
    join erp.fg_stock_movements m
      on m.source_type='OPENING_BALANCE_ITEM' and m.source_id=i.id
     and m.movement_type='OPENING'
    where i.opening_id=h.id and i.balance_type='FINISHED_GOODS'
  ) expected
  cross join lateral(
    select coalesce(sum(l.debit-l.credit),0)::numeric actual_fg
    from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id
    where j.source_type='OPENING_BALANCE' and j.source_id=h.id
      and j.status='POSTED' and l.account_id=erp.account_id('FG_INVENTORY')
  ) actual
  where h.status='POSTED' and abs(expected.expected_fg-actual.actual_fg)>0.005

  union all
  select 'V2620E_REDISPATCH_EVENT_MISMATCH','CRITICAL',count(*)::bigint,
    'Effective redispatch allocation/release events must be bounded, non-overlapping, chronological, and backed by exact custody facts'
  from(
    select a.id
    from erp.laundry_redispatch_participant_events a
    join erp.laundry_delivery_batch_size_lines sx
      on sx.id=a.source_delivery_batch_size_line_id
    join erp.laundry_delivery_lines sl on sl.id=sx.delivery_line_id
    join erp.laundry_deliveries sd on sd.id=sl.delivery_id
    join erp.laundry_delivery_batch_size_lines dx
      on dx.id=a.successor_delivery_batch_size_line_id
    join erp.laundry_delivery_lines dl on dl.id=dx.delivery_line_id
    join erp.laundry_deliveries dd on dd.id=dl.delivery_id
    where a.event_type='ALLOCATE' and(
      sx.distribution_batch_id<>dx.distribution_batch_id or sx.size_id<>dx.size_id
      or sl.cutting_group_id<>dl.cutting_group_id or sd.status<>'REVERSED'
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
          and fr.physical_at<=dd.physical_at)
      or (not exists(select 1 from erp.laundry_redispatch_participant_events x
            where x.event_type='RELEASE' and x.releases_allocation_event_id=a.id)
          and dd.status='REVERSED'
          and not exists(select 1 from erp.laundry_receipts r where r.delivery_id=dd.id))
    )
    union all
    select a.id
    from erp.laundry_redispatch_participant_events a
    where a.event_type='ALLOCATE'
      and not exists(select 1 from erp.laundry_redispatch_participant_events x
        where x.event_type='RELEASE' and x.releases_allocation_event_id=a.id)
      and exists(
        select 1 from erp.laundry_redispatch_participant_events b
        where b.event_type='ALLOCATE' and b.id>a.id
          and not exists(select 1 from erp.laundry_redispatch_participant_events x
            where x.event_type='RELEASE' and x.releases_allocation_event_id=b.id)
          and ((b.source_delivery_batch_size_line_id=a.source_delivery_batch_size_line_id
              and int4range(b.source_offset_pcs,b.source_offset_pcs+b.qty_pcs,'[)')
                && int4range(a.source_offset_pcs,a.source_offset_pcs+a.qty_pcs,'[)'))
            or (b.successor_delivery_batch_size_line_id=a.successor_delivery_batch_size_line_id
              and int4range(b.successor_offset_pcs,b.successor_offset_pcs+b.qty_pcs,'[)')
                && int4range(a.successor_offset_pcs,a.successor_offset_pcs+a.qty_pcs,'[)')))
      )
    union all
    select x.id
    from erp.laundry_redispatch_participant_events x
    join erp.laundry_redispatch_participant_events a
      on a.id=x.releases_allocation_event_id and a.event_type='ALLOCATE'
    join erp.laundry_delivery_batch_size_lines sx
      on sx.id=a.successor_delivery_batch_size_line_id
    join erp.laundry_delivery_lines dl on dl.id=sx.delivery_line_id
    join erp.laundry_deliveries d on d.id=dl.delivery_id
    where x.event_type='RELEASE' and(
      x.released_delivery_id<>d.id or d.status<>'REVERSED'
      or exists(select 1 from erp.laundry_receipts r where r.delivery_id=d.id)
    )
  ) bad_events

  union all
  select 'V2620D_SALE_LIFECYCLE_HPP_DIMENSION_MISMATCH','CRITICAL',count(*)::bigint,
    'Every Sale lifecycle journal must conserve FG/COGS/disposition independently inside each PO or non-PO dimension'$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: report counterexample-check insertion anchor is not exact';
  end if;
  v_definition:=replace(v_definition,v_anchor,v_replacement);

  v_anchor:=$anchor$  cross join lateral(
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
  );$anchor$;
  v_replacement:=$replacement$  cross join lateral(
    select coalesce(sum(l.debit-l.credit) filter(where l.account_id in(
      erp.account_id('COGS'),erp.account_id('FG_INVENTORY'),
      erp.account_id('OTHER_EXPENSE'),erp.account_id('OTHER_INCOME')
    )),0) hpp_net
    from erp.journal_lines l where l.journal_entry_id=e.id
  ) b
  where e.status in('POSTED','REVERSED') and(
    e.source_type in('SALE','SALES_RETURN')
    or(e.source_type='JOURNAL_REVERSAL' and o.source_type in('SALE','SALES_RETURN'))
  ) and(
    abs(b.hpp_net)>0.005
    or exists(
      select 1 from erp.journal_lines l
      where l.journal_entry_id=e.id
        and l.account_id in(
          erp.account_id('COGS'),erp.account_id('FG_INVENTORY'),
          erp.account_id('OTHER_EXPENSE'),erp.account_id('OTHER_INCOME')
        )
      group by l.po_id
      having abs(sum(l.debit-l.credit))>0.005
    )
  );$replacement$;
  if (length(v_definition)-length(replace(v_definition,v_anchor,'')))/length(v_anchor)<>1 then
    raise exception 'DRIFT_CONCURRENT_MUTATION_DETECTED: report lifecycle conservation anchor is not exact';
  end if;
  execute replace(v_definition,v_anchor,v_replacement);
end
$patch_financial_checks_v2620e$;

-- Rebuild only POs whose participant lineage exists. Released D allocations
-- and newly appended replacement allocations then move the already-recorded
-- service cost from WIP into the authoritative current HPP/FG book.
do $reconcile_existing_v2620e$
declare r record;
begin
  for r in
    select distinct d.po_id
    from erp.laundry_redispatch_participant_events a
    join erp.laundry_delivery_batch_size_lines sx
      on sx.id=a.source_delivery_batch_size_line_id
    join erp.laundry_delivery_lines dl on dl.id=sx.delivery_line_id
    join erp.laundry_deliveries d on d.id=dl.delivery_id
    where a.event_type='ALLOCATE'
    order by d.po_id
  loop
    perform erp.rebuild_po_hpp(
      r.po_id,'v2.6.20e append-only effective redispatch event reconciliation'
    );
    perform erp.refresh_po_hpp_gl_baseline(r.po_id);
    perform erp.sync_po_hpp_to_gl(r.po_id,current_date);
    perform erp.refresh_po_hpp_gl_baseline(r.po_id);
    perform erp.assert_po_hpp_target_book_v2620e(r.po_id);
  end loop;
end
$reconcile_existing_v2620e$;

do $installed_guard_v2620e$
declare
  v_issue_count bigint;
begin
  if to_regclass('erp.laundry_redispatch_participant_events') is null
     or not (select c.relrowsecurity from pg_class c
       where c.oid='erp.laundry_redispatch_participant_events'::regclass)
     or exists(select 1 from pg_policy p
       where p.polrelid='erp.laundry_redispatch_participant_events'::regclass)
     or exists(
       select 1 from information_schema.role_table_grants g
       where g.table_schema='erp'
         and g.table_name='laundry_redispatch_participant_events'
         and g.grantee in('PUBLIC','anon','authenticated','service_role')
     )
     or (select count(*) from pg_trigger t
       where not t.tgisinternal and(
         (t.tgrelid='erp.laundry_redispatch_participant_events'::regclass
          and t.tgname in(
            'trg_guard_laundry_redispatch_participant_event_v2620e',
            'trg_audit_laundry_redispatch_participant_event_v2620e'
          ))
         or(t.tgrelid='erp.laundry_deliveries'::regclass
          and t.tgname='trg_release_laundry_redispatch_participant_v2620e')
       ))<>3
     or position('allocate_laundry_redispatch_participants_v2620e' in
       pg_get_functiondef(
         'erp.save_laundry_qc_action_v1(text,jsonb,uuid,bigint)'::regprocedure
       ))=0
     or position('cp6_lot_failed_wash_cost_v2620e' in pg_get_functiondef(
       'erp.rebuild_po_hpp(uuid,text)'::regprocedure))=0
     or position('compute_po_hpp_gl_book_v2620e' in pg_get_functiondef(
       'erp.refresh_po_hpp_gl_baseline(uuid)'::regprocedure))=0
     or position('v_delta_cogs+v_delta_fg+v_delta_other' in pg_get_functiondef(
       'erp.post_sale(uuid)'::regprocedure))=0
     or position('v_prior_product_refund+v_current_product_refund>v_product_sale_value' in
       pg_get_functiondef('erp.post_sales_return(uuid)'::regprocedure))=0
     or position('assert_po_hpp_target_book_v2620e' in pg_get_functiondef(
       'erp.reverse_sales_return(uuid,text)'::regprocedure))=0
     or position('V2620E_OPENING_HPP_LINEAGE_MISMATCH' in pg_get_functiondef(
       'erp.run_v268_financial_report_checks()'::regprocedure))=0
     or exists(
       select 1 from (values
         ('erp._allocate_laundry_redispatch_participants_v2620e(uuid,boolean)'),
         ('erp.allocate_laundry_redispatch_participants_v2620e(uuid)'),
         ('erp.guard_laundry_redispatch_participant_event_v2620e()'),
         ('erp.record_laundry_redispatch_release_v2620e()'),
         ('erp.cp6_lot_failed_wash_cost_v2620e(uuid)'),
         ('erp.compute_po_hpp_gl_book_v2620e(uuid)'),
         ('erp.assert_po_hpp_target_book_v2620e(uuid)')
       ) f(identity)
       cross join (values('anon'),('authenticated'),('service_role')) r(role_name)
       where has_function_privilege(r.role_name,f.identity,'EXECUTE')
     ) then
    raise exception 'ERP v2.6.20e counterexample closure did not install privately and completely';
  end if;

  select coalesce(sum(c.issue_count),0)::bigint into v_issue_count
  from erp.run_v268_financial_report_checks() c
  where c.check_name in(
    'V2620C_PO_HPP_TARGET_STATE_MISMATCH',
    'V2620C_PO_HPP_BOOK_MISMATCH',
    'V2620C_WIP_SOURCE_CONSERVATION_MISMATCH',
    'V2620C_HPP_COMPONENT_SUM_MISMATCH',
    'V2620E_NON_PO_SALE_HPP_BOOK_MISMATCH',
    'V2620E_SALES_RETURN_VALUE_EXCEEDS_SALE',
    'V2620E_OPENING_HPP_LINEAGE_MISMATCH',
    'V2620E_OPENING_FG_GL_MISMATCH',
    'V2620E_REDISPATCH_EVENT_MISMATCH'
  );
  if v_issue_count<>0 then
    raise exception 'ERP v2.6.20e targeted reconciliation still has % issue(s)',
      v_issue_count;
  end if;

  update erp.cp6_v2620e_rollback_capsule c
  set installed_definition_sha256=encode(extensions.digest(convert_to(
    pg_get_functiondef(to_regprocedure(c.object_regidentity)),'UTF8'
  ),'sha256'),'hex');
  if (select count(*) from erp.cp6_v2620e_rollback_capsule
      where installed_definition_sha256 is not null)<>8 then
    raise exception 'ERP v2.6.20e installed-definition capsule is incomplete';
  end if;
end
$installed_guard_v2620e$;

comment on table erp.laundry_redispatch_participant_events is
  'Private append-only allocation/release event ledger. A cancellation before any receipt releases an interval; a retry appends a new allocation.';
comment on function erp.cp6_lot_failed_wash_cost_v2620e(uuid) is
  'Failed-wash cost follows only effective append-only participant allocations through any redispatch cycle.';
comment on function erp.compute_po_hpp_gl_book_v2620e(uuid) is
  'Independent actual PO FG/COGS/disposition book supporting mixed-origin lifecycle journals and cent-carry redistribution.';

insert into erp.schema_migrations(version,description)
values(
  'v2.6.20e',
  'CP6 C01-C06 closure: append-only redispatch releases, mixed-origin HPP, conserved cent carry, exact refund and inverse/report integrity'
);

commit;
