-- OUTSIDE PRODUCT exact owning-wrapper derivation; no public wire change.
-- Source file SHA256 22559f9cfb09c9f8cd0d0b64f50c08e52d3c1a302ea88803044373ab691eea34
-- Exact added closure occurs after the real outer response persists.
do $not_an_installer$begin raise exception 'OW04_COORDINATOR_REQUIRES_ATOMIC_NATIVE_COMPOSITION';end $not_an_installer$;

create or replace function cp7_credit.return_settlement_command(p_payload jsonb,p_request uuid,p_expected text)returns jsonb
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
 perform cp7_credit.close_completed_return_receipt_v1(p_request);
 if cp7_credit.return_command_access(mode)is distinct from a then
  raise exception using errcode='42501',message='CP7_CREDIT_ACCESS_CHANGED';end if;
 return result;
end $$;
