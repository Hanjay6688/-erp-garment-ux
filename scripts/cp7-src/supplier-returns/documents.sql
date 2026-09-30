-- Complete same-supplier return documents. Native source valuation, stock
-- capacity, payment dependency and credit allocation remain authoritative.
create function cp7_supplier_return.sources(p_purchase uuid,p_q text,p_offset integer,p_limit integer) returns jsonb
language plpgsql stable security invoker set search_path='' as $$
declare h erp.material_purchase_headers;term text;total bigint;rows jsonb;
begin
 perform cp7_supplier_return.access_now();term:=btrim(coalesce(p_q,''));
 if p_purchase is null or length(term)>120 or p_offset is null or p_offset not between 0 and 1000000 or p_limit is null or p_limit not between 1 and 25 then raise exception 'CP7_RETURN_QUERY';end if;
 select * into h from erp.material_purchase_headers where id=p_purchase;
 if not found or h.supplier_id is null then raise exception 'CP7_RETURN_RECEIPT_NOT_FOUND';end if;
 select count(*) into total from erp.material_purchase_headers ph where ph.supplier_id=h.supplier_id and ph.status='POSTED' and (term='' or strpos(lower(ph.purchase_number),lower(term))>0);
 select coalesce(jsonb_agg(jsonb_build_object('id',ph.id,'number',ph.purchase_number,'physical_at',ph.physical_at,'row_version',ph.row_version::text) order by ph.physical_at desc,ph.id),'[]'::jsonb) into rows
 from(select x.* from erp.material_purchase_headers x where x.supplier_id=h.supplier_id and x.status='POSTED' and (term='' or strpos(lower(x.purchase_number),lower(term))>0) order by x.physical_at desc,x.id limit p_limit offset p_offset) ph;
 return jsonb_build_object('contract_version','cp7.return-sources.v1','read_at',statement_timestamp(),'purchase_id',p_purchase,'supplier_id',h.supplier_id,
  'page',jsonb_build_object('rows',rows,'total',total::text,'offset',p_offset,'limit',p_limit,'next_offset',case when p_offset+jsonb_array_length(rows)<total then p_offset+jsonb_array_length(rows) else null end));
end $$;
create function public.erp_cp7_get_supplier_return_sources_v1(p_purchase uuid,p_q text,p_offset integer,p_limit integer) returns jsonb
language sql stable security definer set search_path='' as $$select cp7_supplier_return.sources(p_purchase,p_q,p_offset,p_limit)$$;

create function cp7_supplier_return.validate_sources(p_purchase uuid,p_payload jsonb) returns void
language plpgsql stable security definer set search_path='' as $$
declare matched integer;anchored boolean;g record;
begin
 perform cp7_supplier_return.access_now();
 if jsonb_typeof(p_payload->'items') is distinct from 'array' or jsonb_array_length(p_payload->'items') not between 1 and 100 then raise exception 'CP7_RETURN_LINES';end if;
 select count(*),bool_or(ph.id=p_purchase) into matched,anchored from jsonb_array_elements(p_payload->'items') l
 join erp.material_purchase_items i on i.id=(l->>'purchase_item_id')::uuid join erp.material_purchase_headers ph on ph.id=i.purchase_id
 where ph.status='POSTED' and ph.supplier_id=(p_payload->>'supplier_id')::uuid;
 if matched<>jsonb_array_length(p_payload->'items') or anchored is distinct from true then raise exception 'CP7_RETURN_SAME_SUPPLIER_POSTED_RECEIPTS_REQUIRED';end if;
 -- Reuse the complete exact quantity/material/roll contract for each source.
 for g in select i.purchase_id,jsonb_agg(l order by n) items from jsonb_array_elements(p_payload->'items') with ordinality x(l,n)
  join erp.material_purchase_items i on i.id=(l->>'purchase_item_id')::uuid group by i.purchase_id order by i.purchase_id loop
  perform cp7_supplier_return.validate_source(g.purchase_id,p_payload||jsonb_build_object('items',g.items));
 end loop;
end $$;

create function cp7_supplier_return.assert_complete_document(p_purchase uuid,p_return uuid,p_reviewed jsonb) returns void
language plpgsql stable security definer set search_path='' as $$
declare ids jsonb;n integer;
begin
 perform cp7_supplier_return.access_now();
 if jsonb_typeof(p_reviewed) is distinct from 'array' or jsonb_array_length(p_reviewed) not between 1 and 100
  or exists(select 1 from jsonb_array_elements(p_reviewed) x where jsonb_typeof(x)<>'string') then raise exception 'CP7_RETURN_COMPLETE_DOCUMENT_REQUIRED';end if;
 select count(*),jsonb_agg(distinct i.purchase_id::text order by i.purchase_id::text) into n,ids
 from erp.material_supplier_return_items l left join erp.material_purchase_items i on i.id=l.purchase_item_id where l.return_id=p_return;
 if n not between 1 and 100 or ids is null or not ids ? p_purchase::text
  or ids is distinct from(select jsonb_agg(x order by x) from jsonb_array_elements(p_reviewed) x)
  or exists(select 1 from erp.material_supplier_return_items l left join erp.material_purchase_items i on i.id=l.purchase_item_id
   left join erp.material_purchase_headers ph on ph.id=i.purchase_id join erp.material_supplier_returns rh on rh.id=l.return_id
   where rh.id=p_return and (i.id is null or ph.supplier_id is distinct from rh.supplier_id)) then raise exception 'CP7_RETURN_COMPLETE_DOCUMENT_REQUIRED';end if;
end $$;

create function cp7_supplier_return.validate_document_post(p_return uuid) returns void
language plpgsql stable security definer set search_path='' as $$
begin
 perform cp7_supplier_return.access_now();
 if not exists(select 1 from erp.material_supplier_returns h join erp.locations l on l.id=h.location_id where h.id=p_return and l.is_active and l.location_type='RAW_MATERIAL_WAREHOUSE'
  and not exists(select 1 from erp.bc_accessory_zones_v1 z where z.location_id=l.id)) then raise exception 'CP7_RETURN_ACTIVE_WAREHOUSE_REQUIRED';end if;
 if exists(select 1 from erp.material_supplier_return_items r join erp.materials m on m.id=r.material_id where r.return_id=p_return and not m.is_active) then raise exception 'CP7_RETURN_ACTIVE_MATERIAL_REQUIRED';end if;
end $$;

create function cp7_supplier_return.document_command(p_action text,p_payload jsonb,p_request uuid,p_expected text) returns jsonb
language plpgsql volatile security invoker set search_path='' as $$
declare a jsonb;r jsonb;pid uuid;ident uuid;expected bigint;kind text;permission_key text;old cp7_supplier_return.requests;
begin
 if current_setting('transaction_isolation')<>'read committed' then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_supplier_return.access_now();
 if p_action is null or p_action not in('SAVE_DOCUMENT','POST_DOCUMENT','REVERSE_DOCUMENT') or p_request is null then raise exception 'CP7_RETURN_ACTION';end if;
 kind:=replace(p_action,'_DOCUMENT','');
 if a->(case kind when 'SAVE' then 'create' when 'POST' then 'post' else 'reverse' end) is distinct from 'true'::jsonb then raise exception using errcode='42501',message='CP7_RETURN_ACTION_DENIED';end if;
 if p_expected is not null and p_expected!~'^[1-9][0-9]{0,18}$' then raise exception 'CP7_RETURN_VERSION';end if;expected:=p_expected::bigint;
 if jsonb_typeof(p_payload) is distinct from 'object' or jsonb_typeof(p_payload->'purchase_id') is distinct from 'string' then raise exception 'CP7_RETURN_FIELDS';end if;
 insert into cp7_supplier_return.requests values(auth.uid(),p_request,p_action,p_payload,p_expected,null) on conflict do nothing;
 select * into old from cp7_supplier_return.requests where actor=auth.uid() and request_id=p_request for update;
 if old.action<>p_action or old.payload is distinct from p_payload or old.expected_version is distinct from p_expected then raise exception 'CP7_RETURN_REQUEST_PAYLOAD_CHANGED';end if;
 if cp7_supplier_return.access_now()<>a then raise exception using errcode='42501',message='CP7_RETURN_ACCESS_CHANGED';end if;
 if old.response is not null then return old.response;end if;
 pid:=(p_payload->>'purchase_id')::uuid;
 if kind='SAVE' then
  if not p_payload ?& array['purchase_id','return_number','supplier_id','location_id','physical_at','change_reason','items'] or exists(select 1 from jsonb_each(p_payload) e
   where e.key not in('purchase_id','id','return_number','supplier_id','location_id','physical_at','change_reason','reason','items') or(e.key<>'items' and jsonb_typeof(e.value) not in('string','null'))) then raise exception 'CP7_RETURN_FIELDS';end if;
  if exists(select 1 from unnest(array['purchase_id','return_number','supplier_id','location_id','physical_at','change_reason']) k where jsonb_typeof(p_payload->k) is distinct from 'string' or nullif(btrim(p_payload->>k),'') is null) then raise exception 'CP7_RETURN_FIELDS';end if;
  if (p_payload->>'id' is null and expected is not null) or (p_payload->>'id' is not null and expected is null) then raise exception 'CP7_RETURN_VERSION';end if;
  perform cp7_supplier_return.validate_sources(pid,p_payload);
 else
  if expected is null or not p_payload ?& array['purchase_id','return_id','change_reason','reviewed_purchase_ids'] or exists(select 1 from jsonb_each(p_payload) e
   where e.key not in('purchase_id','return_id','change_reason','reviewed_purchase_ids') or(e.key<>'reviewed_purchase_ids' and jsonb_typeof(e.value)<>'string')) then raise exception 'CP7_RETURN_FIELDS';end if;
  ident:=(p_payload->>'return_id')::uuid;
  perform cp7_supplier_return.assert_complete_document(pid,ident,p_payload->'reviewed_purchase_ids');
  if kind='POST' then perform cp7_supplier_return.validate_document_post(ident);end if;
 end if;
 permission_key:=case kind when 'SAVE' then 'warehouse.procurement.create' else 'warehouse.procurement.reverse' end;
 insert into cp7_supplier_return.execution_context values(pg_backend_pid(),txid_current(),auth.uid(),kind,permission_key);
 if kind='SAVE' then
  r:=erp.save_material_supplier_return_draft_v2(p_payload-'purchase_id',p_request,expected);
  perform cp7_supplier_return.validate_sources(pid,p_payload);
 elsif kind='POST' then r:=erp.post_material_supplier_return_v2(ident,p_request,expected,p_payload->>'change_reason');
 else r:=erp.reverse_material_supplier_return_v2(ident,p_payload->>'change_reason',p_request,expected);end if;
 if cp7_supplier_return.access_now()<>a then raise exception using errcode='42501',message='CP7_RETURN_ACCESS_CHANGED';end if;
 if kind<>'SAVE' then perform cp7_supplier_return.assert_complete_document(pid,ident,p_payload->'reviewed_purchase_ids');end if;
 if kind='POST' then perform cp7_supplier_return.validate_document_post(ident);end if;
 delete from cp7_supplier_return.execution_context where backend_pid=pg_backend_pid() and transaction_id=txid_current();
 r:=jsonb_build_object('contract_version','cp7.supplier-return-outcome.v1','kind','COMMITTED_OUTCOME','action',p_action,'request_id',p_request,'purchase_id',pid,
  'return_id',r->'material_supplier_return_id','row_version',r->>'row_version','status',r->>'status');
 update cp7_supplier_return.requests set response=r where actor=auth.uid() and request_id=p_request;
 return r;
end $$;
