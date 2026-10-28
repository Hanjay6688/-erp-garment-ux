-- Read-only local projection. No writes, live recapture or reference rewrite.
create schema cp7_frozen_analysis_readers_v2 authorization cp7_capture;
revoke all on schema cp7_frozen_analysis_readers_v2 from public,anon,authenticated,service_role;

create function cp7_frozen_analysis_readers_v2.reference(j cp7_analysis_stage.jobs)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare cached jsonb;inputs jsonb;c jsonb:=j.reference;
begin
 if j.id is null or j.state is distinct from'DONE'
  or c->>'bounded_request_contract'is distinct from'cp7.bounded-analysis-request.v2'
  or c->>'bounded_reference_contract'is distinct from'cp7.bounded-analysis-reference.v2'
  or cp7_frozen_analysis_units_v2.coverage(j.id)is distinct from'COMPLETE'then
  raise exception 'CP7_FROZEN_READER_REFERENCE_REQUIRED';end if;
 if cp7_frozen_analysis_units_v2.producer_hash()is distinct from c->>'bounded_producer_hash'then
  raise exception using errcode='40001',message='CP7_PRODUCT_ANALOG_PRODUCER_CHANGED';end if;
 select x.payload into cached from cp7_analysis_stage.target_rows x
  where x.job_id=j.id and x.kind='FROZEN_INPUTS_V2'and x.ord=1 and x.key=c->>'bounded_capsule_hash';
 if cached is not null then
  inputs:=cp7_frozen_analysis_units_v2.unpack(j,cached);
 else
  -- Existing K3 removes temporary inputs while retaining the immutable capsule
  -- and pages. Recompute only from that sealed capsule, with the same compiler.
  -- Never write a replacement cache or recapture current stock at an old clock.
  inputs:=cp7_frozen_analysis_v2.prepare(c,j.query,(cp7_analysis_stage.bounds()->>'job_targets')::integer);
 end if;
 return c||jsonb_build_object('bounded_history_inputs',inputs,'bounded_input_coverage','COMPLETE');
end $$;
alter function cp7_frozen_analysis_readers_v2.reference(cp7_analysis_stage.jobs)owner to cp7_capture;
revoke all on function cp7_frozen_analysis_readers_v2.reference(cp7_analysis_stage.jobs)from public,anon,authenticated,service_role;
