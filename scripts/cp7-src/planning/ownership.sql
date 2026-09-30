alter function cp7_planning.utc(timestamptz)owner to cp7_capture;
alter function cp7_planning.history_query(jsonb)owner to cp7_capture;
alter function cp7_planning.history_source()owner to cp7_capture;
alter function cp7_planning.history_events(jsonb)owner to cp7_capture;
alter function cp7_planning.history_availability(jsonb,jsonb)owner to cp7_capture;
alter function cp7_planning.history_build(jsonb,jsonb)owner to cp7_capture;
alter function cp7_planning.serve_history(uuid)owner to cp7_capture;
alter function cp7_planning.capture_history(jsonb,uuid)owner to cp7_capture;
revoke all on all functions in schema cp7_planning from public,anon,authenticated,service_role;
grant create on schema public to cp7_capture;
alter function public.erp_cp7_capture_demand_history_v1(jsonb,uuid)owner to cp7_capture;
alter function public.erp_cp7_read_demand_history_v1(uuid)owner to cp7_capture;
revoke create on schema public from cp7_capture;
revoke all on function public.erp_cp7_capture_demand_history_v1(jsonb,uuid),public.erp_cp7_read_demand_history_v1(uuid)
 from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_capture_demand_history_v1(jsonb,uuid),public.erp_cp7_read_demand_history_v1(uuid)to authenticated;
