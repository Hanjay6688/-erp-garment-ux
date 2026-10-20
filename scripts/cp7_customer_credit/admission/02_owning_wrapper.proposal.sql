-- UNINSTALLED PRIVATE WRAPPER PROPOSAL. This is not a public placeholder.
-- The owning source/admission/completion callbacks named below MUST exist as
-- reviewed implementations before the complete feature can install anything.
do $not_an_installer$ begin
 raise exception 'OW04_RETURN_WRAPPER_REQUIRES_COMPLETE_OWNING_FEATURE';
end $not_an_installer$;

-- Deliberately one final wire: exact legacy RETURN plus the opaque server
-- quote digest and an explicit discriminated choice (NULL for a truly empty
-- signed target). No client amount, date pair, journal vector or family ID.
create function cp7_credit.validate_return_settlement_payload(p jsonb)returns void
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare c jsonb;k text;
begin
 if jsonb_typeof(p)is distinct from'object'or not(p?&array['settlement','quote_sha256'])
  or jsonb_typeof(p->'quote_sha256')is distinct from'string'
  or p->>'quote_sha256'!~'^[0-9a-f]{64}$'then
  raise exception 'CP7_CREDIT_RETURN_FIELDS';end if;
 perform cp7_sales.validate_return(p-'settlement'-'quote_sha256',false);
 c:=p->'settlement';
 if c='null'::jsonb then return;end if;
 if jsonb_typeof(c)is distinct from'object'or c->>'mode'not in('CREDIT','REFUND')
  or jsonb_typeof(c->'mode')is distinct from'string'then
  raise exception 'CP7_CREDIT_RETURN_CHOICE';end if;
 if c->>'mode'='CREDIT'then
  if not(c?&array['mode','credit_account_id'])or(select count(*)from jsonb_object_keys(c))<>2 then
   raise exception 'CP7_CREDIT_RETURN_CHOICE';end if;
 else
  if not(c?&array['mode','credit_account_id','cash_account_id','refund_physical_at','reference'])
   or(select count(*)from jsonb_object_keys(c))<>5
   or jsonb_typeof(c->'cash_account_id')is distinct from'string'
   or c->>'cash_account_id'!~*'^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$'
   or jsonb_typeof(c->'refund_physical_at')is distinct from'string'
   or length(c->>'refund_physical_at')not between 20 and 40
   or c->>'refund_physical_at'!~'(Z|[+-][0-9]{2}:[0-9]{2})$'
   or jsonb_typeof(c->'reference')not in('string','null')
   or length(c->>'reference')>100 then raise exception 'CP7_CREDIT_RETURN_CHOICE';end if;
  perform(c->>'refund_physical_at')::timestamptz;
 end if;
 if jsonb_typeof(c->'credit_account_id')is distinct from'string'
  or c->>'credit_account_id'!~*'^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$'then
  raise exception 'CP7_CREDIT_RETURN_CHOICE';end if;
 -- Eligibility, dated capacity and actual account snapshots are server source
 -- proofs; passing this structural validator confers none of them.
end $$;

-- This is a concrete structural scope check, followed by the REQUIRED owning
-- factual verifier. Hash-shaped strings alone never authorize Native work.
create function cp7_credit.assert_locked_return_outer(p_request uuid,p_legacy jsonb,p_expected text)returns void
language plpgsql volatile security definer set search_path=''as $$
declare s cp7_credit.return_command_scope;r cp7_credit.return_requests;
begin
 if current_setting('transaction_isolation')<>'read committed'or auth.uid()is null
  or auth.jwt()->>'role'is distinct from'authenticated'then
  raise exception using errcode='42501',message='CP7_CREDIT_CURRENT_ACTOR_REQUIRED';end if;
 select *into strict s from cp7_credit.return_command_scope where backend_pid=pg_backend_pid()
  and transaction_id=txid_current()and actor=auth.uid();
 select *into strict r from cp7_credit.return_requests where actor=auth.uid()and request_id=p_request;
 if s.stage<>'LOCKED'or r.response is not null
  or(s.request_id,s.expected_version,s.legacy_payload)is distinct from(p_request,p_expected,p_legacy)
  or r.expected_version is distinct from p_expected
  or cp7_credit.pg_jsonb_sha256(r.payload)is distinct from s.payload_sha256
  or r.payload->>'quote_sha256'is distinct from s.quote_sha256
  or p_legacy is distinct from(r.payload-'settlement'-'quote_sha256')
  or(s.mode,s.credit_account_id,s.cash_account_id,s.refund_physical_at)is distinct from
   (r.payload#>>'{settlement,mode}',(r.payload#>>'{settlement,credit_account_id}')::uuid,
    (r.payload#>>'{settlement,cash_account_id}')::uuid,(r.payload#>>'{settlement,refund_physical_at}')::timestamptz)
  or(p_legacy->>'sale_id')::uuid is distinct from s.source_sale_id
  or s.source_lock_sha256 is null or s.projection_sha256 is null
  or s.return_id is not null then
  raise exception using errcode='42501',message='CP7_CREDIT_LOCKED_OUTER_BINDING_REQUIRED';end if;
 if cp7_credit.return_command_access(s.mode)is distinct from s.current_authority then
  raise exception using errcode='42501',message='CP7_CREDIT_ACCESS_CHANGED';end if;
 perform cp7_credit.assert_no_ambient_native_context();
 -- REQUIRED, intentionally absent: prove source/master/period lock ownership,
 -- complete quote/projection equality (including typed PRIOR causal proof,
 -- exact journal_effect/planned_book_date) and fresh account/source facts. Reentry
 -- discovers no new earlier-order lock after period; a changed set must abort.
 perform cp7_credit.assert_sealed_return_source(p_request);
end $$;

-- The new writer gets a fixed-action capability, not a general command/table
-- grant. Its owner can operate cp7_sales.requests under existing Native RLS.
create function cp7_sales.execute_preclaimed_credit_return(p_request uuid,p_legacy jsonb,p_expected text)returns jsonb
language plpgsql volatile security definer set search_path=''as $$
declare r cp7_sales.requests;a jsonb;
begin
 perform cp7_credit.assert_locked_return_outer(p_request,p_legacy,p_expected);
 a:=cp7_sales.command_access('RETURN');
 -- This exact row was acquired BEFORE FG. Re-reading it does not introduce
 -- a new lock order. A standalone committed inner receipt is never accepted.
 select *into strict r from cp7_sales.requests where actor=auth.uid()and request_id=p_request for update;
 if(r.action,r.payload,r.expected_version)is distinct from('RETURN',p_legacy,p_expected)
  or r.response is not null then raise exception 'CP7_CREDIT_PENDING_INNER_REQUIRED';end if;
 if cp7_sales.command_access('RETURN')is distinct from a then
  raise exception using errcode='42501',message='CP7_CREDIT_ACCESS_CHANGED_AFTER_REQUEST_WAIT';end if;
 return cp7_sales.command('RETURN',p_legacy,p_request,p_expected);
end $$;
alter function cp7_sales.execute_preclaimed_credit_return(uuid,jsonb,text)owner to cp7_sales_write;

-- Only the complete feature may expose a public SQL SECURITY DEFINER facade,
-- owned by cp7_credit_write, calling this fixed implementation. The existing
-- SALES recovery dispatch routes RETURN_SETTLEMENT there, never to the closed
-- cp7_sales.command enum. No public function is created by this proposal.
create function cp7_credit.return_settlement_command(p_payload jsonb,p_request uuid,p_expected text)returns jsonb
language plpgsql volatile security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;r cp7_credit.return_requests;s cp7_credit.return_command_scope;
 legacy jsonb;c jsonb;mode text;inner_receipt jsonb;result jsonb;
begin
 if current_setting('transaction_isolation')<>'read committed'then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 perform cp7_credit.validate_return_settlement_payload(p_payload);
 if p_request is null or p_expected is null or p_expected!~'^[1-9][0-9]{0,18}$'then
  raise exception 'CP7_CREDIT_RETURN_REQUEST_REQUIRED';end if;
 legacy:=p_payload-'settlement'-'quote_sha256';c:=p_payload->'settlement';mode:=c->>'mode';
 a:=cp7_credit.return_command_access(mode);
 perform cp7_credit.assert_no_ambient_native_context();
 insert into cp7_credit.return_requests values(auth.uid(),p_request,p_payload,p_expected,null)on conflict do nothing;
 select *into strict r from cp7_credit.return_requests where actor=auth.uid()and request_id=p_request for update;
 if(r.payload,r.expected_version)is distinct from(p_payload,p_expected)then
  raise exception 'CP7_CREDIT_RETURN_REQUEST_CHANGED';end if;
 if cp7_credit.return_command_access(mode)is distinct from a then
  raise exception using errcode='42501',message='CP7_CREDIT_ACCESS_CHANGED_AFTER_REQUEST_WAIT';end if;
 perform cp7_credit.assert_no_ambient_native_context();
 if r.response is not null then
  -- REQUIRED, intentionally absent: validate the historical receipt against
  -- this exact outer and committed inner request/factual completion. No new
  -- source event, cash movement or current quote is created on reply recovery.
  perform cp7_credit.assert_completed_return_receipt(p_request,p_payload,p_expected,r.response);
  if cp7_credit.return_command_access(mode)is distinct from a then
   raise exception using errcode='42501',message='CP7_CREDIT_ACCESS_CHANGED';end if;
  return r.response;
 end if;
 insert into cp7_credit.return_command_scope(backend_pid,transaction_id,actor,request_id,expected_version,
  payload_sha256,legacy_payload,quote_sha256,stage,source_sale_id,mode,credit_account_id,cash_account_id,
  refund_physical_at,current_authority)
 values(pg_backend_pid(),txid_current(),auth.uid(),p_request,p_expected,cp7_credit.pg_jsonb_sha256(p_payload),legacy,
  p_payload->>'quote_sha256','CLAIMED',(legacy->>'sale_id')::uuid,mode,(c->>'credit_account_id')::uuid,
  (c->>'cash_account_id')::uuid,(c->>'refund_physical_at')::timestamptz,a);
 perform cp7_sales.preclaim_credit_return(p_request,legacy,p_expected);
 perform pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0));
 if cp7_credit.return_command_access(mode)is distinct from a then
  raise exception using errcode='42501',message='CP7_CREDIT_ACCESS_CHANGED_AFTER_FG_WAIT';end if;
 -- REQUIRED, intentionally absent: deterministic complete source/master locks,
 -- then period SHARE; fresh typed PRIOR causal/choice/account/source/quote proof;
 -- exact sealed projection; only then set this own scope stage to LOCKED.
 -- The nested Native entry binds its actual generated DRAFT return ID once to
 -- that projection and seals complete PRIOR ancestors there. It must not use a
 -- completed-return collector before Native has made the actual journal/no-J
 -- decision. PROVEN_ABSENT+HPP-only new journal uses only the exact lawful Native
 -- resolver with the proved zero financial profile/empty target; no free date.
 perform cp7_credit.seal_return_settlement(p_request);
 inner_receipt:=cp7_sales.execute_preclaimed_credit_return(p_request,legacy,p_expected);
 -- REQUIRED, intentionally absent: Native actual return ID/source match,
 -- family/member + signed recognition/refund materialization and closed parts,
 -- actual projection-to-journal mapping and DISTINCT actual manifest SHA,
 -- final current authority/account/cash/joint-capacity proof; verify the exact
 -- committed inner receipt and Native COMPLETE marker; clear financial scopes.
 result:=cp7_credit.finish_return_settlement(p_request,inner_receipt);
 select *into strict s from cp7_credit.return_command_scope where backend_pid=pg_backend_pid()
  and transaction_id=txid_current()and actor=auth.uid()and request_id=p_request;
 if s.stage<>'COMPLETE'or s.return_id is null or s.family_id is null or s.family_ordinal is null
  or s.actual_manifest_sha256 is null
  or inner_receipt->>'action'is distinct from'RETURN'
  or inner_receipt->>'request_id'is distinct from p_request::text
  or inner_receipt->>'sale_id'is distinct from s.source_sale_id::text
  or inner_receipt->>'return_id'is distinct from s.return_id::text
  or inner_receipt->>'return_status'is distinct from'POSTED'
  or result->>'action'is distinct from'RETURN_SETTLEMENT'
  or result->>'request_id'is distinct from p_request::text
  or result->>'sale_id'is distinct from s.source_sale_id::text
  or result->>'return_id'is distinct from s.return_id::text
  or result->>'quote_sha256'is distinct from s.quote_sha256
  or result->>'projection_sha256'is distinct from s.projection_sha256
  or result->>'actual_manifest_sha256'is distinct from s.actual_manifest_sha256 then
  raise exception 'CP7_CREDIT_NATIVE_COMPLETION_RECEIPT_REQUIRED';end if;
 perform cp7_credit.assert_completed_return_receipt(p_request,p_payload,p_expected,result);
 if cp7_credit.return_command_access(mode)is distinct from a then
  raise exception using errcode='42501',message='CP7_CREDIT_ACCESS_CHANGED';end if;
 perform cp7_credit.assert_return_native_scope_cleared_v1();
 perform cp7_credit.assert_no_ambient_native_context();
 delete from cp7_credit.return_command_scope where backend_pid=pg_backend_pid()and transaction_id=txid_current()
  and actor=auth.uid()and request_id=p_request;
 update cp7_credit.return_requests set response=result where actor=auth.uid()and request_id=p_request;
 if cp7_credit.return_command_access(mode)is distinct from a then
  raise exception using errcode='42501',message='CP7_CREDIT_ACCESS_CHANGED';end if;
 return result;
end $$;

-- Owning installer must set exact owners/ACLs transactionally. In particular:
--  * cp7_credit_write owns only these NEW request/scope tables and fixed writer;
--    grant no ERP DML and no general cp7_sales.command/public sales facade EXEC;
--  * EXEC fixed preclaim + fixed execute_preclaimed_credit_return ONLY to it;
--  * cp7_sales_write receives USAGE cp7_credit and EXEC only pending/locked
--    outer verifiers; no SELECT/DML on credit request/scope/fact tables;
--  * credit writer EXEC on the existing PURE validate_return only, and on its
--    reviewed own access/source/completion capabilities; no account/journal API;
--  * no authenticated/private schema USAGE, role membership, table permission,
--    verifier/preclaim/bridge/writer EXEC. Only a complete public owning facade.
revoke all on function cp7_credit.validate_return_settlement_payload(jsonb),
 cp7_credit.assert_locked_return_outer(uuid,jsonb,text),
 cp7_sales.execute_preclaimed_credit_return(uuid,jsonb,text),
 cp7_credit.return_settlement_command(jsonb,uuid,text)
 from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read;
