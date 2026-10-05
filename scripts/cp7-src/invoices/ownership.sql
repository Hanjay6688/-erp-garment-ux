grant create on schema public,cp7_invoice to cp7_invoice_read,cp7_invoice_write;
alter function cp7_invoice.access_now() owner to cp7_invoice_read;
alter function cp7_invoice.assert_single_receipt(uuid,uuid) owner to cp7_invoice_read;
alter function cp7_invoice.workspace(uuid,integer,integer) owner to cp7_invoice_read;
alter function cp7_invoice.command(text,jsonb,uuid,text) owner to cp7_invoice_write;
alter function cp7_invoice.document_command(text,jsonb,uuid,text) owner to cp7_invoice_write;
alter function cp7_invoice.source_lines(uuid) owner to cp7_invoice_read;
alter function cp7_invoice.sources(uuid,text,integer,integer) owner to cp7_invoice_read;
alter function cp7_invoice.validate_sources(uuid,uuid,jsonb) owner to cp7_invoice_read;
alter function cp7_invoice.assert_document(uuid,uuid,jsonb) owner to cp7_invoice_read;
alter function cp7_invoice.payment_access() owner to cp7_invoice_read;
alter function cp7_invoice.payment_ap(uuid) owner to cp7_invoice_read;
alter function cp7_invoice.payment_detail(uuid,jsonb) owner to cp7_invoice_read;
alter function cp7_invoice.payment_workspace(uuid,text,integer,uuid) owner to cp7_invoice_read;
alter function cp7_invoice.reverse_payment_request(jsonb,uuid) owner to cp7_invoice_write;
alter function public.erp_cp7_get_supplier_payments_v1(uuid,text,integer,uuid) owner to cp7_invoice_read;
alter function public.erp_cp7_reverse_supplier_payment_v1(jsonb,uuid) owner to cp7_invoice_write;
alter function public.erp_cp7_get_invoice_sources_v1(uuid,text,integer,integer) owner to cp7_invoice_read;
alter function public.erp_cp7_get_purchase_invoices_v1(uuid,integer,integer) owner to cp7_invoice_read;
alter function public.erp_cp7_save_purchase_invoice_v1(text,jsonb,uuid,text) owner to cp7_invoice_write;
revoke create on schema public,cp7_invoice from cp7_invoice_read,cp7_invoice_write;
revoke all on all functions in schema cp7_invoice from public,anon,authenticated,service_role,cp7_capture;
grant execute on function cp7_invoice.access_now(),cp7_invoice.assert_single_receipt(uuid,uuid) to cp7_invoice_write;
grant execute on function cp7_invoice.validate_sources(uuid,uuid,jsonb),cp7_invoice.assert_document(uuid,uuid,jsonb) to cp7_invoice_write;
grant execute on function cp7_invoice.payment_access(),cp7_invoice.reverse_payment_locked(jsonb) to cp7_invoice_write;
-- The accepted runtime's postgres role is deliberately not a superuser. The
-- narrow locking helper needs these exact private readers, including the
-- invoker access check's dependency; no ERP DML or App execution is added.
grant execute on function cp7_invoice.access_now(),cp7_invoice.payment_access(),
 cp7_invoice.payment_ap(uuid),cp7_invoice.payment_detail(uuid,jsonb) to postgres;
revoke all on function public.erp_cp7_get_supplier_payments_v1(uuid,text,integer,uuid),public.erp_cp7_reverse_supplier_payment_v1(jsonb,uuid) from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_get_supplier_payments_v1(uuid,text,integer,uuid),public.erp_cp7_reverse_supplier_payment_v1(jsonb,uuid) to authenticated;
revoke all on function public.erp_cp7_get_invoice_sources_v1(uuid,text,integer,integer) from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_get_invoice_sources_v1(uuid,text,integer,integer) to authenticated;
revoke all on function public.erp_cp7_get_purchase_invoices_v1(uuid,integer,integer),public.erp_cp7_save_purchase_invoice_v1(text,jsonb,uuid,text) from public,anon,authenticated,service_role,cp7_capture;
grant execute on function public.erp_cp7_get_purchase_invoices_v1(uuid,integer,integer),public.erp_cp7_save_purchase_invoice_v1(text,jsonb,uuid,text) to authenticated;
