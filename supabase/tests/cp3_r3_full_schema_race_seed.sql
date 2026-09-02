-- Committed CP3 R3 fixture for real two-connection races. Disposable local DB only.
\set ON_ERROR_STOP on
set timezone='Asia/Jakarta';
\ir cp3_r3_full_schema_seed.sql

do $cp3$
begin
  if not exists (
    select 1
    from erp.schema_migrations
    where version='v2.6.14c'
  ) then
    raise exception 'CP3 R3 race seed requires applied v2.6.14c';
  end if;
end
$cp3$;

-- Two additional authoritative work-completion facts are posted but terminal sewing is not yet recorded.
insert into erp.work_completion_events(
  id,completion_number,po_id,contractor_id,cutting_group_id,physical_at,status,notes
) values
 ('a5000000-0000-0000-0000-000000000011','CP3R3-WC-LATE-1','a3000000-0000-0000-0000-000000000001','a1000000-0000-0000-0000-000000000001','a3200000-0000-0000-0000-000000000001','2026-01-01 14:00:00+07','DRAFT','CP3 R3 race late 1'),
 ('a5000000-0000-0000-0000-000000000012','CP3R3-WC-LATE-2','a3000000-0000-0000-0000-000000000001','a1000000-0000-0000-0000-000000000001','a3200000-0000-0000-0000-000000000001','2026-01-01 15:00:00+07','DRAFT','CP3 R3 race late 2');
insert into erp.work_completion_lines(
  id,completion_id,po_component_snapshot_id,work_component_id,qty_completed,qty_payable,rate_snapshot
) values
 ('a5100000-0000-0000-0000-000000000011','a5000000-0000-0000-0000-000000000011','a4100000-0000-0000-0000-000000000001','a4000000-0000-0000-0000-000000000001',10,10,0),
 ('a5100000-0000-0000-0000-000000000012','a5000000-0000-0000-0000-000000000012','a4100000-0000-0000-0000-000000000001','a4000000-0000-0000-0000-000000000001',5,5,0);
select erp.post_work_completion('a5000000-0000-0000-0000-000000000011');
select erp.post_work_completion('a5000000-0000-0000-0000-000000000012');
