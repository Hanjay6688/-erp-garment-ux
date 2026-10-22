-- OW-04b part 3 (retest 23 Oct 2026, "OW-04 retur transaksi lunas"): when the credit product must still refuse, the
-- screen names the reason and the next step. Three retained refusals keep their exact condition, order and message;
-- native_delta.py only adds a DETAIL built here, listing every sub-condition that is true. Read-only, no business row.
create schema cp7_credit_followups authorization postgres;
revoke all on schema cp7_credit_followups from public,anon,authenticated,service_role,cp7_capture;

-- One closed detail shape for all three refusals (src/lib/creditRefusalMessages.ts parses exactly these keys).
create function cp7_credit_followups.detail_v1(p_refusal text,p_action text,p_reasons jsonb,p_blockers jsonb)returns text
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
begin
 return jsonb_build_object('contract','cp7.credit-followups.refusal.v1','refusal',p_refusal,'action',p_action,
  'reasons',case when jsonb_array_length(p_reasons)=0 then jsonb_build_array('UNCLASSIFIED')else p_reasons end,
  'source_blockers',p_blockers)::text;
end $$;

-- 02_initial_projection.sql:314-318: the five sub-conditions of CP7_CREDIT_INITIAL_SOURCE_FAMILY_UNSUPPORTED, same
-- expressions, same order. Called only after that condition was true; a reason is listed only when it is true.
create function cp7_credit_followups.initial_family_reasons_v1(p_sale uuid,p_src jsonb)returns text
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare reasons jsonb:='[]';blockers jsonb:='[]';
begin
 if p_src->>'source_status'<>'BASE_COLLECTED'then
  reasons:=reasons||jsonb_build_array('SOURCE_HISTORY_BLOCKED');
  select coalesce(jsonb_agg(x.b->>'code'order by x.n),'[]')into blockers
   from jsonb_array_elements(case when jsonb_typeof(p_src->'blockers')='array'then p_src->'blockers'else'[]'::jsonb end)with ordinality x(b,n)
   where jsonb_typeof(x.b->'code')='string';
 end if;
 if jsonb_typeof(p_src->'family'->'note_revisions')='array'and jsonb_array_length(p_src->'family'->'note_revisions')<>0 then
  reasons:=reasons||jsonb_build_array('NOTE_REVISED');end if;
 if exists(select 1 from cp7_credit.cohorts ch join cp7_credit.return_families f on f.id=ch.family_id where f.family_root_sale_id=p_sale)then
  reasons:=reasons||jsonb_build_array('PRIOR_CREDIT_RETURN');end if;
 if exists(select 1 from cp7_credit.consumption_events where event_kind='APPLY'and target_sale_id=p_sale)then
  reasons:=reasons||jsonb_build_array('CREDIT_APPLIED_TO_INVOICE');end if;
 if exists(select 1 from cp7_sales_return_correction.links where sale_id=p_sale)then
  reasons:=reasons||jsonb_build_array('RETURN_CORRECTED');end if;
 return cp7_credit_followups.detail_v1('INITIAL_SOURCE_FAMILY',null,reasons,blockers);
end $$;

-- 05_factual_profile.sql:45-48 as installed by the payment-correction stage (its payment-link sub-condition moved to
-- payment_link_source_check_v1): CP7_CREDIT_SOURCE_CORRECTION_ADAPTER_UNIMPLEMENTED.
create function cp7_credit_followups.correction_reasons_v1(p_sale uuid)returns text
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare reasons jsonb:='[]';
begin
 if exists(select 1 from cp7_note.revisions where p_sale in(root_sale_id,previous_sale_id,replacement_sale_id))then
  reasons:=reasons||jsonb_build_array('NOTE_REVISED');end if;
 if exists(select 1 from cp7_sales_return_correction.links where sale_id=p_sale)then
  reasons:=reasons||jsonb_build_array('RETURN_CORRECTED');end if;
 return cp7_credit_followups.detail_v1('SOURCE_CORRECTION',null,reasons,'[]'::jsonb);
end $$;

-- native-empty/04_exact_overlays.sql native_source_enter: CP7_CREDIT_REGISTERED_SOURCE_MUTATION_REQUIRES_BOUND_
-- RECONCILIATION (a direct payment, Edit retur or Benerin nota reaching the Native writer on an invoice in credit).
create function cp7_credit_followups.source_mutation_reasons_v1(p_action text,p_sale uuid)returns text
language plpgsql stable security definer set search_path=''set TimeZone='UTC'as $$
declare reasons jsonb:='[]';
begin
 if exists(select 1 from cp7_credit.cohorts ch join cp7_credit.return_families f on f.id=ch.family_id where f.family_root_sale_id=p_sale)then
  reasons:=reasons||jsonb_build_array('PRIOR_CREDIT_RETURN');end if;
 if exists(select 1 from cp7_credit.consumption_events where event_kind='APPLY'and target_sale_id=p_sale)then
  reasons:=reasons||jsonb_build_array('CREDIT_APPLIED_TO_INVOICE');end if;
 return cp7_credit_followups.detail_v1('REGISTERED_SOURCE_MUTATION',p_action,reasons,'[]'::jsonb);
end $$;

do $owners$declare sig text;begin
 foreach sig in array array['detail_v1(text,text,jsonb,jsonb)','initial_family_reasons_v1(uuid,jsonb)',
  'correction_reasons_v1(uuid)','source_mutation_reasons_v1(text,uuid)']loop
  execute 'alter function cp7_credit_followups.'||sig||' owner to postgres';
  execute 'revoke all on function cp7_credit_followups.'||sig||' from public,anon,authenticated,service_role,cp7_capture,cp7_sales_read,cp7_sales_write,cp7_credit_write';
 end loop;
end $owners$;
