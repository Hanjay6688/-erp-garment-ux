-- Current, paginated Native QC dependencies of one physical Laundry receipt.
-- Uses the existing read-only source role; no inverse, reservation or ERP DML.
create function cp7_transaction_source.dependencies(p_source jsonb,p_offset integer)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare a jsonb;ident uuid;h erp.laundry_receipts%rowtype;n bigint;items jsonb;
begin
 if jsonb_typeof(p_source)is distinct from'object'or not(p_source?&array['source_type','source_id'])
  or(select count(*)from jsonb_object_keys(p_source))<>2
  or p_source->>'source_type'is distinct from'LAUNDRY_RECEIPT'
  or jsonb_typeof(p_source->'source_id')is distinct from'string'
  or p_source->>'source_id'!~'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
  or p_offset is null or p_offset<0 or p_offset>1000000 or p_offset%25<>0 then
  raise exception using errcode='22023',message='CP7_TRANSACTION_DEPENDENCY_FIELDS';end if;
 a:=cp7_transaction_source.authority();
 -- Both current view permissions precede header/FK resolution. Laundry view
 -- alone never exposes inspection numbers from another operational domain.
 if not erp.has_permission('production.laundry.view')or not erp.has_permission('production.final_sku.view')then
  raise exception using errcode='42501',message='CP7_TRANSACTION_SOURCE_ACCESS_DENIED';end if;
 ident:=(p_source->>'source_id')::uuid;
 select * into h from erp.laundry_receipts where id=ident;
 if not found then raise exception 'CP7_TRANSACTION_SOURCE_UNAVAILABLE';end if;
 -- Exactly the relationship and active-status predicate used by the frozen
 -- Native receipt inverse. EXISTS deduplicates a QC with multiple source lines.
 select count(*)into n from erp.qc_inspections q where q.status<>'REVERSED'and exists(
  select 1 from erp.qc_inspection_items i join erp.laundry_receipt_lines l on l.id=i.source_laundry_receipt_line_id
  where i.inspection_id=q.id and l.receipt_id=ident);
 select coalesce(jsonb_agg(x.item order by x.physical_at desc,x.id),'[]'::jsonb)into items from(
  select q.id,q.physical_at,jsonb_build_object('source_type','QC_INSPECTION','source_id',q.id,
   'number',q.inspection_number,'status',q.status,'revision',q.row_version::text)as item
  from erp.qc_inspections q where q.status<>'REVERSED'and exists(
   select 1 from erp.qc_inspection_items i join erp.laundry_receipt_lines l on l.id=i.source_laundry_receipt_line_id
   where i.inspection_id=q.id and l.receipt_id=ident)
  order by q.physical_at desc,q.id limit 25 offset p_offset
 )x;
 if cp7_transaction_source.authority()is distinct from a
  or not erp.has_permission('production.laundry.view')or not erp.has_permission('production.final_sku.view')then
  raise exception using errcode='42501',message='CP7_TRANSACTION_SOURCE_ACCESS_CHANGED';end if;
 return jsonb_build_object('contract_version','cp7.transaction-dependencies.v1','actor_scope_id',auth.uid(),
  'source',p_source,'parent',jsonb_build_object('id',h.id,'number',h.receipt_number,'status',h.status,'revision',h.row_version::text),
  'page',jsonb_build_object('offset',p_offset,'limit',25,'total',n,'has_more',p_offset+jsonb_array_length(items)<n),
  'dependencies',items,'read_at',statement_timestamp(),'business_DML',false);
end $$;
alter function cp7_transaction_source.dependencies(jsonb,integer)owner to cp7_transaction_source_read;
revoke all on function cp7_transaction_source.dependencies(jsonb,integer)from public,anon,authenticated,service_role;
grant create on schema public to cp7_transaction_source_read;
create function public.erp_cp7_get_transaction_dependencies_v1(p_source jsonb,p_offset integer default 0)returns jsonb
language sql stable security definer set search_path=''as $$select cp7_transaction_source.dependencies(p_source,p_offset)$$;
alter function public.erp_cp7_get_transaction_dependencies_v1(jsonb,integer)owner to cp7_transaction_source_read;
revoke create on schema public from cp7_transaction_source_read;
revoke all on function public.erp_cp7_get_transaction_dependencies_v1(jsonb,integer)from public,anon,authenticated,service_role;
grant execute on function public.erp_cp7_get_transaction_dependencies_v1(jsonb,integer)to authenticated;
