grant create on schema public,cp7_material to cp7_material_read,cp7_material_write;
alter function cp7_material.access_now() owner to cp7_material_read;
alter function cp7_material.validate_lines(jsonb) owner to cp7_material_read;
alter function cp7_material.validate_transfer_scope(uuid,uuid,uuid) owner to cp7_material_read;
alter function cp7_material.balances(text,uuid,uuid,boolean) owner to cp7_material_read;
alter function cp7_material.workspace(jsonb) owner to cp7_material_read;
alter function cp7_material.ledger(uuid,uuid,uuid,integer,integer) owner to cp7_material_read;
alter function cp7_material.transfer_header(erp.material_transfers) owner to cp7_material_read;
alter function cp7_material.transfers(jsonb) owner to cp7_material_read;
alter function cp7_material.locations(text,integer,integer) owner to cp7_material_read;
alter function cp7_material.command(text,jsonb,uuid,text) owner to cp7_material_write;
alter function public.erp_cp7_get_materials_v1(jsonb) owner to cp7_material_read;
alter function public.erp_cp7_get_material_ledger_v1(uuid,uuid,uuid,integer,integer) owner to cp7_material_read;
alter function public.erp_cp7_get_material_transfers_v1(jsonb) owner to cp7_material_read;
alter function public.erp_cp7_get_material_locations_v1(text,integer,integer) owner to cp7_material_read;
alter function public.erp_cp7_save_materials_v1(text,jsonb,uuid,text) owner to cp7_material_write;
alter function cp7_material.count_lines(uuid,timestamptz,jsonb,boolean,uuid) owner to cp7_material_read;
alter function cp7_material.count_preview(jsonb) owner to cp7_material_read;
alter function cp7_material.count_signature(uuid) owner to cp7_material_read;
alter function cp7_material.count_header(erp.material_adjustments) owner to cp7_material_read;
alter function cp7_material.count_workspace(jsonb) owner to cp7_material_read;
alter function cp7_material.count_options(jsonb) owner to cp7_material_read;
alter function cp7_material.count_command(text,jsonb,uuid,text) owner to cp7_material_write;
alter function public.erp_cp7_preview_material_count_v1(jsonb) owner to cp7_material_read;
alter function public.erp_cp7_get_material_counts_v1(jsonb) owner to cp7_material_read;
alter function public.erp_cp7_get_material_count_options_v1(jsonb) owner to cp7_material_read;
alter function public.erp_cp7_save_material_count_v1(text,jsonb,uuid,text) owner to cp7_material_write;
revoke create on schema public,cp7_material from cp7_material_read,cp7_material_write;
revoke all on all functions in schema cp7_material from public,anon,authenticated,service_role,cp7_capture;
grant execute on function cp7_material.access_now(),cp7_material.validate_lines(jsonb) to cp7_material_write;
grant execute on function cp7_material.validate_transfer_scope(uuid,uuid,uuid) to cp7_material_write;
revoke all on function public.erp_cp7_get_materials_v1(jsonb),public.erp_cp7_get_material_ledger_v1(uuid,uuid,uuid,integer,integer),
 public.erp_cp7_get_material_transfers_v1(jsonb),public.erp_cp7_get_material_locations_v1(text,integer,integer),public.erp_cp7_save_materials_v1(text,jsonb,uuid,text)
 from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_get_materials_v1(jsonb),public.erp_cp7_get_material_ledger_v1(uuid,uuid,uuid,integer,integer),
 public.erp_cp7_get_material_transfers_v1(jsonb),public.erp_cp7_get_material_locations_v1(text,integer,integer),public.erp_cp7_save_materials_v1(text,jsonb,uuid,text) to authenticated;

grant execute on function cp7_material.count_lines(uuid,timestamptz,jsonb,boolean,uuid),cp7_material.count_signature(uuid) to cp7_material_write;
revoke all on function public.erp_cp7_preview_material_count_v1(jsonb),public.erp_cp7_get_material_counts_v1(jsonb),public.erp_cp7_save_material_count_v1(text,jsonb,uuid,text) from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_preview_material_count_v1(jsonb),public.erp_cp7_get_material_counts_v1(jsonb),public.erp_cp7_save_material_count_v1(text,jsonb,uuid,text) to authenticated;
revoke all on function public.erp_cp7_get_material_count_options_v1(jsonb) from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_get_material_count_options_v1(jsonb) to authenticated;
