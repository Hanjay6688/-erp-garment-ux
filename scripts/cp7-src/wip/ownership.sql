alter function cp7_wip.fields(jsonb,text[]) owner to cp7_capture;
alter function cp7_wip.key(jsonb) owner to cp7_capture;
alter function cp7_wip.pcs(jsonb) owner to cp7_capture;
alter function cp7_wip.refs(jsonb) owner to cp7_capture;
alter function cp7_wip.reconcile(jsonb) owner to cp7_capture;
alter function cp7_wip.match_target(jsonb,jsonb) owner to cp7_capture;
alter function cp7_wip.check_allocations(jsonb,jsonb) owner to cp7_capture;
alter function cp7_wip.remaining_eta(timestamptz,timestamptz,jsonb) owner to cp7_capture;
revoke all on all functions in schema cp7_wip from public,anon,authenticated,service_role;
