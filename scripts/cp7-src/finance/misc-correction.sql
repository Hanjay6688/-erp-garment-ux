-- One atomic correction through the unchanged reviewed miscellaneous writers.
-- Posted documents and their Native journals remain append-only history.
create schema cp7_misc_correction authorization cp7_misc_read;
revoke all on schema cp7_misc_correction from public,anon,authenticated,service_role,cp7_capture;
grant usage,create on schema cp7_misc_correction to cp7_misc_write;
create table cp7_misc_correction.links(
 original_id uuid primary key references erp.misc_finance_transactions(id),
 replacement_id uuid not null unique references erp.misc_finance_transactions(id),
 actor uuid not null,request_id uuid not null,reason text not null,
 time_neutral_id uuid references erp.journal_entries(id),effective_inverse_id uuid references erp.journal_entries(id),
 recorded_at timestamptz not null default statement_timestamp(),
 check(original_id<>replacement_id),check(length(btrim(reason))between 5 and 1000),
 check((time_neutral_id is null)=(effective_inverse_id is null)),
 unique(actor,request_id)
);
alter table cp7_misc_correction.links owner to cp7_misc_write;
alter table cp7_misc_correction.links enable row level security;
create policy cp7_misc_correction_links_deny on cp7_misc_correction.links for all to public using(false)with check(false);
revoke all on cp7_misc_correction.links from public,anon,authenticated,service_role,cp7_capture;
grant select on cp7_misc_correction.links to cp7_misc_read;

create function cp7_misc_correction.validate(p jsonb)returns void
language plpgsql immutable security invoker set search_path=''as $$
begin
 if jsonb_typeof(p)is distinct from'object'or not(p?&array['transaction_id','review_token','replacement','change_reason'])
  or(select count(*)from jsonb_object_keys(p))<>4 then raise exception 'CP7_MISC_CORRECTION_FIELDS';end if;
 perform cp7_misc.validate('REVERSE',p-'replacement');
 perform cp7_misc.validate('SAVE',p->'replacement');
 if p->'replacement'->'transaction_id'is distinct from'null'::jsonb
  or p->'replacement'->'review_token'is distinct from'null'::jsonb
  or p->'replacement'->>'change_reason'is distinct from p->>'change_reason'then
  raise exception 'CP7_MISC_CORRECTION_FIELDS';end if;
end $$;

create function cp7_misc_correction.link_value(p cp7_misc_correction.links)returns jsonb
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select jsonb_build_object('original_id',p.original_id,'replacement_id',p.replacement_id,
  'actor_scope_id',p.actor,'request_id',p.request_id,'reason',p.reason,'recorded_at',p.recorded_at,
  'time_restatement',case when p.time_neutral_id is null then null else(
   select jsonb_build_object('neutral_journal_id',n.id,'neutral_number',n.journal_number,'neutral_economic_date',n.economic_date,'neutral_transaction_date',n.transaction_date,
    'effective_journal_id',e.id,'effective_number',e.journal_number,'effective_economic_date',e.economic_date,'effective_transaction_date',e.transaction_date)
   from erp.journal_entries n join erp.journal_entries e on e.id=p.effective_inverse_id where n.id=p.time_neutral_id)end)
$$;

create function cp7_misc_correction.history(p_id uuid)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;prev cp7_misc_correction.links;nxt cp7_misc_correction.links;previous jsonb:='null';following jsonb:='null';
begin
 a:=cp7_misc.access_now();
 if p_id is null or cp7_misc.source(p_id)is null then raise exception 'CP7_MISC_NOT_FOUND';end if;
 select * into prev from cp7_misc_correction.links where replacement_id=p_id;
 select * into nxt from cp7_misc_correction.links where original_id=p_id;
 if prev.original_id is not null then previous:=jsonb_build_object('link',cp7_misc_correction.link_value(prev),'document',cp7_misc.source(prev.original_id));end if;
 if nxt.original_id is not null then following:=jsonb_build_object('link',cp7_misc_correction.link_value(nxt),'document',cp7_misc.source(nxt.replacement_id));end if;
 if cp7_misc.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_MISC_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.misc-correction-history.v1','captured_at',statement_timestamp(),
  'transaction_id',p_id,'previous',previous,'next',following);
end $$;

create function cp7_misc_correction.protect_link()returns trigger
language plpgsql volatile security definer set search_path=''as $$
begin
 if tg_op<>'INSERT'then raise exception 'CP7_MISC_CORRECTION_LINK_IMMUTABLE';end if;
 if not exists(select 1 from cp7_misc.command_context c where c.backend_pid=pg_backend_pid()
  and c.transaction_id=txid_current()and c.actor=auth.uid()and c.actor=new.actor
  and c.request_id=new.request_id and c.action='CORRECT'
  and c.payload->>'transaction_id'=new.original_id::text and btrim(c.payload->>'change_reason')=new.reason)
  or not exists(select 1 from erp.misc_finance_transactions t where t.id=new.original_id and t.status='REVERSED')
  or not exists(select 1 from erp.misc_finance_transactions t where t.id=new.replacement_id and t.status='POSTED')then
  raise exception using errcode='42501',message='CP7_MISC_PRIVATE_CONTEXT_REQUIRED';end if;
 if new.time_neutral_id is not null and(not exists(select 1 from erp.journal_entries where id=new.time_neutral_id and source_type='MISC_CORRECTION_TIME_NEUTRAL'and source_id=new.original_id and status='POSTED')
  or not exists(select 1 from erp.journal_entries where id=new.effective_inverse_id and source_type='MISC_CORRECTION_EFFECTIVE'and source_id=new.original_id and status='POSTED'))then
  raise exception 'CP7_MISC_JOURNAL_SOURCE_CHANGED';end if;
 return new;
end $$;
create trigger cp7_misc_correction_link_immutable before insert or update or delete on cp7_misc_correction.links
 for each row execute function cp7_misc_correction.protect_link();
create trigger cp7_misc_correction_link_no_truncate before truncate on cp7_misc_correction.links
 for each statement execute function cp7_misc_correction.protect_link();

create function cp7_misc_correction.apply(p jsonb,p_request uuid)returns jsonb
language plpgsql volatile security definer set search_path=''set TimeZone='UTC'as $$
declare a jsonb;original erp.misc_finance_transactions;review jsonb;replacement jsonb;reversed jsonb;saved jsonb;posted jsonb;link cp7_misc_correction.links;intent jsonb;
 original_journal erp.journal_entries;inverse_journal erp.journal_entries;lines jsonb;neutral uuid;effective uuid;
begin
 a:=cp7_misc.access_now();perform cp7_misc_correction.validate(p);
 if not exists(select 1 from cp7_misc.command_context where backend_pid=pg_backend_pid()and transaction_id=txid_current()
  and actor=auth.uid()and request_id=p_request and action='CORRECT'and payload=p)then
  raise exception using errcode='42501',message='CP7_MISC_PRIVATE_CONTEXT_REQUIRED';end if;
 select * into original from erp.misc_finance_transactions where id=(p->>'transaction_id')::uuid for update;
 if original.id is null then raise exception 'CP7_MISC_NOT_FOUND';end if;
 lock table erp.accounting_account_mappings in share mode;
 perform 1 from erp.misc_finance_categories where id in(original.category_id,(p->'replacement'->>'category_id')::uuid)order by id for share;
 perform 1 from erp.cash_accounts where id in(original.cash_account_id,(p->'replacement'->>'cash_account_id')::uuid)order by id for share;
 perform 1 from erp.chart_accounts where id in(
  select default_account_id from erp.misc_finance_categories where id in(original.category_id,(p->'replacement'->>'category_id')::uuid)
  union select coa_account_id from erp.cash_accounts where id in(original.cash_account_id,(p->'replacement'->>'cash_account_id')::uuid))order by id for share;
 perform 1 from erp.journal_entries j where(j.source_type='MISC_FINANCE'and j.source_id=original.id)
  or j.reversal_of_id in(select id from erp.journal_entries where source_type='MISC_FINANCE'and source_id=original.id)order by j.id for update;
 perform 1 from erp.journal_lines l where l.journal_entry_id in(select id from erp.journal_entries where source_type='MISC_FINANCE'and source_id=original.id)order by l.id for update;
 if cp7_misc.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_MISC_ACCESS_CHANGED';end if;
 review:=cp7_misc.source(original.id);
 if review->>'review_token'is distinct from p->>'review_token'then raise exception 'CP7_MISC_REVIEW_CHANGED';end if;
 if original.status<>'POSTED'then raise exception 'CP7_MISC_POSTED_ONLY';end if;
 if exists(select 1 from cp7_misc_correction.links where original_id=original.id)then raise exception 'CP7_MISC_ALREADY_CORRECTED';end if;
 if p->'replacement'->>'transaction_number'is distinct from original.transaction_number then raise exception 'CP7_MISC_CORRECTION_NUMBER';end if;
 -- Keep the original number. A bounded full-request suffix identifies the
 -- replacement without a caller-chosen row ID or collision-prone counter.
 replacement:=(p->'replacement')||jsonb_build_object('transaction_number',left(original.transaction_number,20)||' · K-'||replace(p_request::text,'-',''));
 -- These calls reuse every Native amount, source, close, audit and current
 -- authority guard. All three are in this single transaction. Any failure
 -- rolls back the inverse, replacement, journals, link and UUID receipt.
 delete from cp7_misc.command_context where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 intent:=p-'replacement';
 insert into cp7_misc.command_context values(pg_backend_pid(),txid_current(),auth.uid(),p_request,'REVERSE',intent);
 reversed:=cp7_misc.apply_command('REVERSE',intent,p_request);
 -- A plain Native inverse has today's economic date. Correcting an old
 -- document also needs its inverse's effect at the original economic date.
 -- Reuse the exact immutable Native lines, as the owning note correction
 -- does: neutralize today, apply at the original date. Native post_journal
 -- alone selects the allowed open accounting date; closed books stay intact.
 select * into strict original_journal from erp.journal_entries where source_type='MISC_FINANCE'and source_id=original.id and reversal_of_id is null;
 select * into strict inverse_journal from erp.journal_entries where reversal_of_id=original_journal.id and source_type='JOURNAL_REVERSAL'and source_id=original_journal.id;
 if original_journal.status<>'REVERSED'or inverse_journal.status<>'POSTED'then raise exception 'CP7_MISC_JOURNAL_SOURCE_CHANGED';end if;
 if original_journal.economic_date<>inverse_journal.economic_date then
  select jsonb_agg(jsonb_build_object('account_id',l.account_id,'debit',l.credit,'credit',l.debit,'description',l.description,
   'customer_id',l.customer_id,'vendor_id',l.vendor_id,'contractor_id',l.contractor_id,'po_id',l.po_id,'product_id',l.product_id)order by l.id)into lines
   from erp.journal_lines l where l.journal_entry_id=inverse_journal.id;
  neutral:=erp.post_journal('MISC_CORRECTION_TIME_NEUTRAL',original.id,inverse_journal.economic_date,'Koreksi transaksi lain: pindahkan waktu ekonomi pembalikan | '||btrim(p->>'change_reason'),lines);
  select jsonb_agg(jsonb_build_object('account_id',l.account_id,'debit',l.debit,'credit',l.credit,'description',l.description,
   'customer_id',l.customer_id,'vendor_id',l.vendor_id,'contractor_id',l.contractor_id,'po_id',l.po_id,'product_id',l.product_id)order by l.id)into lines
   from erp.journal_lines l where l.journal_entry_id=inverse_journal.id;
  effective:=erp.post_journal('MISC_CORRECTION_EFFECTIVE',original.id,original_journal.economic_date,'Koreksi transaksi lain: waktu ekonomi kejadian asal | '||btrim(p->>'change_reason'),lines);
 end if;
 delete from cp7_misc.command_context where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 insert into cp7_misc.command_context values(pg_backend_pid(),txid_current(),auth.uid(),p_request,'SAVE',replacement);
 saved:=cp7_misc.apply_command('SAVE',replacement,p_request);
 delete from cp7_misc.command_context where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 intent:=jsonb_build_object('transaction_id',saved->>'transaction_id','review_token',saved->'document'->>'review_token','change_reason',p->>'change_reason');
 insert into cp7_misc.command_context values(pg_backend_pid(),txid_current(),auth.uid(),p_request,'POST',intent);
 posted:=cp7_misc.apply_command('POST',intent,p_request);
 delete from cp7_misc.command_context where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 if cp7_misc.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_MISC_ACCESS_CHANGED';end if;
 insert into cp7_misc.command_context values(pg_backend_pid(),txid_current(),auth.uid(),p_request,'CORRECT',p);
 insert into cp7_misc_correction.links(original_id,replacement_id,actor,request_id,reason,time_neutral_id,effective_inverse_id)
  values(original.id,(posted->>'transaction_id')::uuid,auth.uid(),p_request,btrim(p->>'change_reason'),neutral,effective)returning * into link;
 return posted||jsonb_build_object('original_document',reversed->'document','original_review_token',p->>'review_token','link',cp7_misc_correction.link_value(link));
end $$;

create function cp7_misc_correction.command(p jsonb,p_request uuid)returns jsonb
language plpgsql volatile security invoker set search_path=''as $$
declare a jsonb;saved cp7_misc.requests;r jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_misc.access_now();perform cp7_misc_correction.validate(p);
 if p_request is null then raise exception 'CP7_MISC_COMMAND_FIELDS';end if;
 insert into cp7_misc.requests(actor,request_id,action,payload)values(auth.uid(),p_request,'CORRECT',p)on conflict do nothing;
 select * into saved from cp7_misc.requests where actor=auth.uid()and request_id=p_request for update;
 if cp7_misc.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_MISC_ACCESS_CHANGED';end if;
 if saved.action<>'CORRECT'or saved.payload is distinct from p then raise exception 'CP7_MISC_REQUEST_CHANGED';end if;
 if saved.response is not null then return saved.response;end if;
 insert into cp7_misc.command_context values(pg_backend_pid(),txid_current(),auth.uid(),p_request,'CORRECT',p);
 r:=cp7_misc_correction.apply(p,p_request);
 delete from cp7_misc.command_context where backend_pid=pg_backend_pid()and transaction_id=txid_current();
 if cp7_misc.access_now()is distinct from a then raise exception using errcode='42501',message='CP7_MISC_ACCESS_CHANGED';end if;
 r:=r||jsonb_build_object('contract_version','cp7.misc-correction.v1','kind','COMMITTED_OUTCOME','action','CORRECT','request_id',p_request);
 update cp7_misc.requests set response=r where actor=auth.uid()and request_id=p_request;return r;
end $$;

alter function cp7_misc_correction.validate(jsonb)owner to cp7_misc_read;
alter function cp7_misc_correction.link_value(cp7_misc_correction.links)owner to cp7_misc_read;
alter function cp7_misc_correction.history(uuid)owner to cp7_misc_read;
alter function cp7_misc_correction.command(jsonb,uuid)owner to cp7_misc_write;
alter function cp7_misc_correction.apply(jsonb,uuid)owner to postgres;
alter function cp7_misc_correction.protect_link()owner to postgres;
revoke all on all functions in schema cp7_misc_correction from public,anon,authenticated,service_role,cp7_capture;
grant execute on function cp7_misc_correction.validate(jsonb),cp7_misc_correction.apply(jsonb,uuid)to cp7_misc_write;
grant execute on function cp7_misc_correction.link_value(cp7_misc_correction.links)to cp7_misc_write;
revoke create on schema cp7_misc_correction from cp7_misc_write;

create function public.erp_cp7_correct_misc_finance_v1(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''as $$select cp7_misc_correction.command(p_payload,p_request)$$;
alter function public.erp_cp7_correct_misc_finance_v1(jsonb,uuid)owner to cp7_misc_write;
revoke all on function public.erp_cp7_correct_misc_finance_v1(jsonb,uuid)from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_correct_misc_finance_v1(jsonb,uuid)to authenticated;
create function public.erp_cp7_get_misc_correction_history_v1(p_transaction_id uuid)returns jsonb
language sql stable security definer set search_path=''as $$select cp7_misc_correction.history(p_transaction_id)$$;
alter function public.erp_cp7_get_misc_correction_history_v1(uuid)owner to cp7_misc_read;
revoke all on function public.erp_cp7_get_misc_correction_history_v1(uuid)from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_get_misc_correction_history_v1(uuid)to authenticated;
