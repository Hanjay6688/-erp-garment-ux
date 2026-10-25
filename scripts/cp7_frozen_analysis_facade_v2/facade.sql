-- Prepared opt-in facade. No default installer or client route adopts it.
create function public.erp_cp7_request_bounded_staged_analysis_v2(p_query jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''set TimeZone='UTC'as $$
 select cp7_frozen_analysis_units_v2.request(p_query,p_request)
$$;
alter function public.erp_cp7_request_bounded_staged_analysis_v2(jsonb,uuid)owner to cp7_capture;
revoke all on function public.erp_cp7_request_bounded_staged_analysis_v2(jsonb,uuid)from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_request_bounded_staged_analysis_v2(jsonb,uuid)to authenticated;
