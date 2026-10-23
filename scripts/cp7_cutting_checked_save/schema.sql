-- Additive OW13c stage. A supplies transaction/envelope and global use guard.
create schema cp7_cutting_checked authorization cp7_plan_writer;
revoke all on schema cp7_cutting_checked from public,anon,authenticated,service_role;
create table cp7_cutting_checked.receipts(
 actor uuid not null,request_id uuid not null,payload jsonb not null,result jsonb not null,
 draft_id uuid not null,recorded_at timestamptz not null default clock_timestamp(),
 primary key(actor,request_id));
alter table cp7_cutting_checked.receipts owner to cp7_plan_writer;
alter table cp7_cutting_checked.receipts enable row level security;
create policy cutting_checked_private on cp7_cutting_checked.receipts for all to public using(false)with check(false);
revoke all on cp7_cutting_checked.receipts from public,anon,authenticated,service_role;
create trigger cutting_checked_receipt_immutable before update or delete on cp7_cutting_checked.receipts
 for each row execute function cp7_private.immutable_run();
create trigger cutting_checked_receipt_no_truncate before truncate on cp7_cutting_checked.receipts
 for each statement execute function cp7_private.immutable_run();
grant usage on schema cp7_cutting_checked to cp7_capture;
