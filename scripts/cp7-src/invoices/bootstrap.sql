-- P09/P13 purchase invoice bridge. Payment/credit allocation stays in its own
-- accepted supplier settlement boundary. These APIs never invent outstanding AP.
create role cp7_invoice_read nologin noinherit nosuperuser nocreatedb nocreaterole noreplication bypassrls;
create role cp7_invoice_write nologin noinherit nosuperuser nocreatedb nocreaterole noreplication;
create schema cp7_invoice authorization cp7_invoice_read;
revoke all on schema cp7_invoice from public,anon,authenticated,service_role;
grant usage,create on schema cp7_invoice to cp7_invoice_write;
grant usage on schema erp,auth to cp7_invoice_read,cp7_invoice_write;
grant execute on function auth.uid(),auth.jwt(),erp.get_my_access_v1(),erp.has_permission(text) to cp7_invoice_read,cp7_invoice_write;
grant select on erp.material_purchase_headers,erp.material_purchase_items,erp.materials,erp.material_supplier_invoices,
 erp.material_supplier_invoice_lines,erp.suppliers to cp7_invoice_read;
grant execute on function erp.material_purchase_invoice_capacity(uuid),erp.material_purchase_posted_invoice_qty(uuid) to cp7_invoice_read;
grant execute on function erp.finalize_material_purchase_invoice_v2(jsonb,uuid,bigint),erp.reverse_material_supplier_invoice_v2(uuid,text,uuid,bigint) to cp7_invoice_write;

create function cp7_invoice.access_now() returns jsonb
language plpgsql stable security invoker set search_path='' as $$
declare a jsonb;legacy boolean;
begin
 if auth.uid() is null or coalesce(auth.jwt()->>'role','')<>'authenticated' then raise exception using errcode='42501',message='CP7_INVOICE_ACCESS_DENIED';end if;
 a:=erp.get_my_access_v1();
 if (a->>'allowed')::boolean is distinct from true or not erp.has_permission('warehouse.procurement.view') or not erp.has_permission('finance.ap.view') then
  raise exception using errcode='42501',message='CP7_INVOICE_ACCESS_DENIED';end if;
 legacy:=a->'profile'->>'role_code' in('OWNER','ADMIN');
 return jsonb_build_object('actor',auth.uid(),'profile',a->'profile','permissions',a->'permissions',
  'finalize',legacy and erp.has_permission('warehouse.procurement.post'),'reverse',legacy and erp.has_permission('warehouse.procurement.reverse'));
end $$;

create function cp7_invoice.assert_single_receipt(p_invoice uuid,p_purchase uuid) returns void
language plpgsql stable security definer set search_path='' as $$
begin
 perform cp7_invoice.access_now();
 if not exists(select 1 from erp.material_supplier_invoice_lines l join erp.material_purchase_items i on i.id=l.purchase_item_id where l.invoice_id=p_invoice and i.purchase_id=p_purchase)
  or exists(select 1 from erp.material_supplier_invoice_lines l join erp.material_purchase_items i on i.id=l.purchase_item_id where l.invoice_id=p_invoice and i.purchase_id<>p_purchase) then
  raise exception 'CP7_INVOICE_COMPLETE_DOCUMENT_REQUIRED';end if;
end $$;
