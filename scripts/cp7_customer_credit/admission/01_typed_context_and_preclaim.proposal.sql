-- UNINSTALLED PROPOSAL. Owning source/financial/closure implementations are required.
do $not_an_installer$ begin
 raise exception 'OW04_ADMISSION_REQUIRES_COMPLETE_OWNING_FEATURE';
end $not_an_installer$;

-- cp7_credit exists in the ledger proposal. cp7_credit_write is a proposed
-- owning role, with NO ERP DML; creating/granting that role is not done here.
create table cp7_credit.return_requests(
 actor uuid not null,request_id uuid not null,payload jsonb not null,
 expected_version text not null,response jsonb,
 primary key(actor,request_id)
);
-- The owning outer wrapper inserts this scope only after locking its request.
-- It is not Native admission: existing cp7_sales RETURN remains the sole
-- require_internal context for that nested route.
create table cp7_credit.return_command_scope(
 backend_pid integer not null,transaction_id bigint not null,actor uuid not null,
 request_id uuid not null,expected_version text not null,
 payload_sha256 text not null check(payload_sha256~'^[0-9a-f]{64}$'),
 legacy_payload jsonb not null,
 quote_sha256 text not null check(quote_sha256~'^[0-9a-f]{64}$'),
 stage text not null check(stage in('CLAIMED','LOCKED','NATIVE','COMPLETE')),
 source_lock_sha256 text check(source_lock_sha256~'^[0-9a-f]{64}$'),
 projection_sha256 text check(projection_sha256~'^[0-9a-f]{64}$'),
 actual_manifest_sha256 text check(actual_manifest_sha256~'^[0-9a-f]{64}$'),
 source_sale_id uuid not null,return_id uuid,
 family_id uuid,family_ordinal bigint check(family_ordinal>0),
 mode text check(mode in('CREDIT','REFUND')),
 credit_account_id uuid,cash_account_id uuid,refund_physical_at timestamptz,
 credit_account_snapshot jsonb,cash_account_snapshot jsonb,
 current_authority jsonb not null,
 primary key(backend_pid,transaction_id),
 check(stage='CLAIMED'or(source_lock_sha256 is not null and projection_sha256 is not null)),
 check(stage not in('NATIVE','COMPLETE')or return_id is not null),
 check(stage<>'COMPLETE'or(family_id is not null and family_ordinal is not null and actual_manifest_sha256 is not null)),
 check(case when mode is null then credit_account_id is null and cash_account_id is null and refund_physical_at is null
  when mode='CREDIT'then credit_account_id is not null and cash_account_id is null and refund_physical_at is null
  when mode='REFUND'then credit_account_id is not null and cash_account_id is not null and refund_physical_at is not null
  else false end)
);
create table cp7_credit.return_native_scope(
 backend_pid integer not null,transaction_id bigint not null,actor uuid not null,
 return_id uuid not null,source_sale_id uuid not null,customer_id uuid not null,
 origin text not null check(origin in('ORDINARY','REVIEWED_SETTLEMENT','BOUND_CORRECTION')),
 request_id uuid,source_lock_sha256 text not null check(source_lock_sha256~'^[0-9a-f]{64}$'),
 projection_sha256 text not null check(projection_sha256~'^[0-9a-f]{64}$'),
 -- PRIOR only: sealed under source locks while this exact own row is DRAFT.
 -- The full manifest is server-only. Its five-field summary matches the quote;
 -- structural CHECKs below do not attest source completeness or authority.
 prior_causal jsonb not null,prior_causal_manifest jsonb not null,
 journal_effect text not null check(journal_effect in('JOURNAL_EXPECTED','NO_JOURNAL')),
 planned_book_date date,
 recognition_nonempty boolean not null,explicit_choice boolean not null,
 native_refund numeric,native_net_after numeric,guard_effective_paid numeric,
 completed boolean not null default false,
 primary key(backend_pid,transaction_id),
 check(origin<>'REVIEWED_SETTLEMENT'or request_id is not null),
 check(coalesce(jsonb_typeof(prior_causal)='object'
  and prior_causal?&array['contract_version','scope','state','causal_book_floor','proof_sha256']
  and prior_causal-array['contract_version','scope','state','causal_book_floor','proof_sha256']='{}'::jsonb
  and prior_causal->>'contract_version'='ow04.prior-causal-book-proof.v1'
  and prior_causal->>'scope'='PRIOR_CAUSAL_SALE_RETURN'
  and jsonb_typeof(prior_causal->'proof_sha256')='string'
  and prior_causal->>'proof_sha256'~'^[0-9a-f]{64}$'
  and jsonb_typeof(prior_causal_manifest)='object'
  and case prior_causal->>'state'
   when'DATED'then jsonb_typeof(prior_causal->'causal_book_floor')='string'
    and prior_causal->>'causal_book_floor'~'^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
    and to_char((prior_causal->>'causal_book_floor')::date,'YYYY-MM-DD')=prior_causal->>'causal_book_floor'
   when'PROVEN_ABSENT'then prior_causal->'causal_book_floor'='null'::jsonb
   else false end,false)),
 check((journal_effect='JOURNAL_EXPECTED')=(planned_book_date is not null)),
 check(case when journal_effect='JOURNAL_EXPECTED'and prior_causal->>'state'='DATED'
  then planned_book_date>=(prior_causal->>'causal_book_floor')::date else true end),
 -- This narrow branch is not financial recognition admission. The protected
 -- sealer must ALSO prove the entire actual zero AR/P/U/I/gross/net/returns
 -- profile, empty signed target vector and no cash refund. K0 alone is not it.
 check(prior_causal->>'state'<>'PROVEN_ABSENT'or(not recognition_nonempty and not explicit_choice)),
 check(not completed or(native_refund is not null and native_net_after is not null and guard_effective_paid is not null))
);
alter table cp7_credit.return_requests enable row level security;
alter table cp7_credit.return_command_scope enable row level security;
alter table cp7_credit.return_native_scope enable row level security;
revoke all on cp7_credit.return_requests,cp7_credit.return_command_scope,cp7_credit.return_native_scope
 from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write;

create function cp7_credit.return_command_access(p_mode text)returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare a jsonb;
begin
 if p_mode is not null and p_mode not in('CREDIT','REFUND')then raise exception 'CP7_CREDIT_MODE_INVALID';end if;
 a:=cp7_sales.command_access('RETURN');
 if p_mode='REFUND'then
  perform erp.require_owner_admin();
  if not erp.has_permission('finance.cash.view')then
   raise exception using errcode='42501',message='CP7_CREDIT_REFUND_CASH_ACCESS_REQUIRED';end if;
 end if;
 return a;
end $$;
revoke all on function cp7_credit.return_command_access(text)from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read;

-- This verifier grants no request DML. It proves the current backend's outer
-- pending request and exact inner payload before the narrow owner preclaim.
-- The complete installer must give only the owning writer DML on its own
-- tables and set each owner/ACL explicitly; no default PUBLIC EXECUTE survives.
create function cp7_credit.assert_pending_return_outer(p_request uuid,p_legacy jsonb,p_expected text)returns void
language plpgsql volatile security definer set search_path=''as $$
declare s cp7_credit.return_command_scope;r cp7_credit.return_requests;
begin
 if current_setting('transaction_isolation')<>'read committed'
  or auth.uid()is null or auth.jwt()->>'role'is distinct from'authenticated'then
  raise exception using errcode='42501',message='CP7_CREDIT_CURRENT_ACTOR_REQUIRED';end if;
 select *into strict s from cp7_credit.return_command_scope
  where backend_pid=pg_backend_pid()and transaction_id=txid_current()and actor=auth.uid();
 select *into strict r from cp7_credit.return_requests where actor=auth.uid()and request_id=p_request;
 if s.stage<>'CLAIMED'or r.response is not null
  or(s.request_id,s.expected_version,s.legacy_payload)is distinct from(p_request,p_expected,p_legacy)
  or r.expected_version is distinct from p_expected
  or cp7_credit.pg_jsonb_sha256(r.payload)is distinct from s.payload_sha256
  or r.payload->>'quote_sha256'is distinct from s.quote_sha256
  or p_legacy is distinct from(r.payload-'settlement'-'quote_sha256')
  or(s.mode,s.credit_account_id,s.cash_account_id,s.refund_physical_at)is distinct from
   (r.payload#>>'{settlement,mode}',(r.payload#>>'{settlement,credit_account_id}')::uuid,
    (r.payload#>>'{settlement,cash_account_id}')::uuid,(r.payload#>>'{settlement,refund_physical_at}')::timestamptz)
  or(p_legacy->>'sale_id')::uuid is distinct from s.source_sale_id then
  raise exception using errcode='42501',message='CP7_CREDIT_PENDING_OUTER_BINDING_REQUIRED';end if;
 if cp7_credit.return_command_access(s.mode)is distinct from s.current_authority then
  raise exception using errcode='42501',message='CP7_CREDIT_ACCESS_CHANGED';end if;
 -- A new top-level settlement is not an alias for a correction context.
 -- Required generated helper covers the COMPLETE exact R4-05 context manifest,
 -- not a convenient subset of sales contexts. No implementation means refusal.
 perform cp7_credit.assert_no_ambient_native_context();
end $$;

-- Owner-only-table capability: acquire INNER request BEFORE FG. No postgres or
-- credit role receives INSERT/UPDATE rights on cp7_sales.requests.
create function cp7_sales.preclaim_credit_return(p_request uuid,p_legacy jsonb,p_expected text)returns void
language plpgsql volatile security definer set search_path=''as $$
declare a jsonb;r cp7_sales.requests;
begin
 perform cp7_credit.assert_pending_return_outer(p_request,p_legacy,p_expected);
 a:=cp7_sales.command_access('RETURN');
 perform cp7_sales.validate_return(p_legacy,false);
 if p_request is null or p_expected is null or p_expected!~'^[1-9][0-9]{0,18}$'then
  raise exception 'CP7_CREDIT_RETURN_REQUEST_REQUIRED';end if;
 insert into cp7_sales.requests values(auth.uid(),p_request,'RETURN',p_legacy,p_expected,null)on conflict do nothing;
 select *into strict r from cp7_sales.requests where actor=auth.uid()and request_id=p_request for update;
 -- The lookup result is in a typed row; later PERFORM must not clobber FOUND.
 if cp7_sales.command_access('RETURN')is distinct from a then
  raise exception using errcode='42501',message='CP7_CREDIT_ACCESS_CHANGED_AFTER_REQUEST_WAIT';end if;
 perform cp7_credit.assert_pending_return_outer(p_request,p_legacy,p_expected);
 if(r.action,r.payload,r.expected_version)is distinct from('RETURN',p_legacy,p_expected)then
  raise exception 'CP7_CREDIT_INNER_REQUEST_CHANGED';end if;
 if r.response is not null then
  raise exception 'CP7_CREDIT_STANDALONE_INNER_RECEIPT_REFUSED';end if;
end $$;
alter function cp7_sales.preclaim_credit_return(uuid,jsonb,text)owner to cp7_sales_write;
revoke all on function cp7_sales.preclaim_credit_return(uuid,jsonb,text)from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read;
-- Complete installer grants EXECUTE only to cp7_credit_write; it also grants
-- cp7_sales_write EXECUTE on assert_pending_return_outer, no table access.
revoke all on function cp7_credit.assert_pending_return_outer(uuid,jsonb,text)from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read;

-- Deliberately classify NO party before FG. A missing/uncommitted advance at
-- the outer probe can become CUSTOMER while waiting for the batch; probing
-- without a typed certificate would reintroduce late FG under a batch lock.
-- Reuse one existing lock for this whole rare PREPAYMENT continuation domain.
create function cp7_credit.prepayment_entry(p_outer boolean)returns void
language plpgsql volatile security definer set search_path=''as $$
begin
 perform erp.require_owner_admin();
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 perform erp.require_owner_admin();
 if p_outer then perform erp.require_permission('settings.erp.view');end if;
end $$;
revoke all on function cp7_credit.prepayment_entry(boolean)from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write;

-- Required implementation contracts, NOT permissive SQL stubs:
-- native_return_enter(uuid): after Native's FG, before return/header/stock locks;
--   lock full source/masters, compare semantic projection, bind Native ID once.
--   While own return is DRAFT, seal PRIOR causal SALE/RETURN summary/full proof,
--   own draft/items, actor/request/context, source locks and exact projection.
--   Summary is ow04.prior-causal-book-proof.v1, scope PRIOR_CAUSAL_SALE_RETURN,
--   state DATED with real floor or PROVEN_ABSENT with null. No caller exclusion.
--   Only this exact sealed own projection is omitted from prior source; every
--   existing bound ancestor, including NET0/HPP-only journals, remains included.
--   PROVEN_ABSENT may project an HPP-only journal, independently of prior absence.
--   Exact planned_book_date comes from the Native lawful resolver under period
--   SHARE (plus proved prior floor if DATED), never from a client or fake floor.
--   Preserve original authority/stock/HPP/cent/account/period guards. A missing
--   prior proof, nonempty credit target or nonzero financial profile refuses.
--   Full prior manifest and digest must be factually verified by the protected
--   owning adapter before storing this scope; its shape is not an attestation.
-- native_return_guard(uuid,numeric,numeric,numeric)->numeric: actual R/net-after/rawP;
--   see README precise original-refusal ordering and canonical E/K validation.
-- native_return_complete(uuid,numeric,numeric)->numeric: after actual RETURN
--   journal-or-NO_JOURNAL, register family, prove mapping, post exact recognition
--   and optional refund in current compound, return actual canonical E for status.
--   Completed factual collectors run ONLY after Native's actual journal/no-J
--   decision; never at its POSTED-but-pre-journal poster. Bind actual generated
--   journal/physical no-J proof to the sealed projection with a DISTINCT digest.
-- native_return_leave(uuid): current rights/final binding; clear only its owned
--   temporary native scope; preserve outer scope until wrapper verifies receipt.
-- native_source_enter(text,uuid),native_source_complete(text,uuid): source mutation
--   ownership, complete affected family admission/actual adjustment and closure.
-- prepayment_entry(boolean) above: FG/current Native owner admission before ANY
--   outer batch or direct helper payment/header/advance locks, no unlocked probe.
-- No request scope or GUC substitutes for any of these current source proofs.
