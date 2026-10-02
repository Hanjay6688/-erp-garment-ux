-- The Native report retains its owner guard, amounts, GL dates and readiness.
-- These are the operational counterparts of the exact journal restatement
-- pair. They use the actual GL posting period, including a closed old period.
create table cp7_note.report_sources(
 native_signature text primary key,original_definition text not null,
 original_sha256 text not null,overlay_sha256 text not null
);
alter table cp7_note.report_sources owner to postgres;
alter table cp7_note.report_sources enable row level security;
create policy private_report_sources on cp7_note.report_sources for all using(false)with check(false);
revoke all on cp7_note.report_sources from public,anon,authenticated,service_role,cp7_capture,cp7_sales_write;
create trigger immutable_report_source before update or delete on cp7_note.report_sources
 for each row execute function cp7_note.immutable_revision();

create function cp7_note.report_lifecycle(p_from date,p_to date,p_source_type text)
returns table(source_id uuid,event_sign integer)
language sql stable security definer set search_path=''as $$
 select original.source_id,e.event_sign
 from cp7_note.journal_restatements r
 join erp.journal_entries original on original.id=r.source_journal_id
 cross join lateral(values
  (r.neutral_journal_id,1,'NOTE_REVERSAL_TIME_NEUTRAL'),
  (r.effective_journal_id,-1,'NOTE_REVERSAL_EFFECTIVE')
 )e(journal_id,event_sign,source_type)
 join erp.journal_entries posted on posted.id=e.journal_id
  and posted.source_type=e.source_type and posted.source_id=r.inverse_journal_id
 where original.status='REVERSED'and original.source_type=p_source_type
  and p_source_type in('SALE','SALES_RETURN')and posted.status='POSTED'
  and posted.transaction_date between p_from and p_to
$$;
alter function cp7_note.report_lifecycle(date,date,text)owner to postgres;
revoke all on function cp7_note.report_lifecycle(date,date,text)
 from public,anon,authenticated,service_role,cp7_capture,cp7_sales_write;
