-- Source-only first increment. Note writers are not enabled by this module.
create function public.erp_cp7_get_nota_sources_v1(p_query jsonb) returns jsonb
language sql stable security definer set search_path='' as $$select cp7_payroll.source_workspace(p_query)$$;
grant create on schema public,cp7_payroll to cp7_payroll_read;
alter function cp7_payroll.access_now(text) owner to cp7_payroll_read;
alter function cp7_payroll.source_lines() owner to cp7_payroll_read;
alter function cp7_payroll.source_cards(boolean) owner to cp7_payroll_read;
alter function cp7_payroll.source_workspace(jsonb) owner to cp7_payroll_read;
alter function public.erp_cp7_get_nota_sources_v1(jsonb) owner to cp7_payroll_read;
revoke create on schema public,cp7_payroll from cp7_payroll_read;
revoke all on all functions in schema cp7_payroll from public,anon,authenticated,service_role,cp7_capture;
revoke all on function public.erp_cp7_get_nota_sources_v1(jsonb) from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_get_nota_sources_v1(jsonb) to authenticated;
