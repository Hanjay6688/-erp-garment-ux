-- The only exposed calls. Read and command owners are deliberately separate.
create function public.erp_cp7_get_procurement_v1(p_query jsonb) returns jsonb
language sql stable security definer set search_path='' as $$select cp7_procurement.workspace(p_query)$$;
create function public.erp_cp7_get_procurement_options_v1(p_kind text,p_q text,p_offset integer,p_limit integer) returns jsonb
language sql stable security definer set search_path='' as $$select cp7_procurement.options(p_kind,p_q,p_offset,p_limit)$$;
create function public.erp_cp7_save_procurement_v1(p_action text,p_payload jsonb,p_request uuid,p_expected text) returns jsonb
language sql volatile security definer set search_path='' as $$select cp7_procurement.command(p_action,p_payload,p_request,p_expected)$$;
grant create on schema public,cp7_procurement to cp7_procure_read,cp7_procure_write;
alter function cp7_procurement.access_now() owner to cp7_procure_read;
alter function cp7_procurement.fields(jsonb,text[],text[]) owner to cp7_procure_read;
alter function cp7_procurement.decimal(jsonb,boolean) owner to cp7_procure_read;
alter function cp7_procurement.header(erp.material_purchase_headers,boolean) owner to cp7_procure_read;
alter function cp7_procurement.workspace(jsonb) owner to cp7_procure_read;
alter function cp7_procurement.options(text,text,integer,integer) owner to cp7_procure_read;
alter function cp7_procurement.command(text,jsonb,uuid,text) owner to cp7_procure_write;
alter function public.erp_cp7_get_procurement_v1(jsonb) owner to cp7_procure_read;
alter function public.erp_cp7_get_procurement_options_v1(text,text,integer,integer) owner to cp7_procure_read;
alter function public.erp_cp7_save_procurement_v1(text,jsonb,uuid,text) owner to cp7_procure_write;
revoke create on schema public,cp7_procurement from cp7_procure_read,cp7_procure_write;
revoke all on all functions in schema cp7_procurement from public,anon,authenticated,service_role,cp7_capture;
grant execute on function cp7_procurement.access_now(),cp7_procurement.fields(jsonb,text[],text[]),cp7_procurement.decimal(jsonb,boolean) to cp7_procure_write;
revoke all on function public.erp_cp7_get_procurement_v1(jsonb),public.erp_cp7_get_procurement_options_v1(text,text,integer,integer),public.erp_cp7_save_procurement_v1(text,jsonb,uuid,text)
 from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_get_procurement_v1(jsonb),public.erp_cp7_get_procurement_options_v1(text,text,integer,integer),public.erp_cp7_save_procurement_v1(text,jsonb,uuid,text) to authenticated;
