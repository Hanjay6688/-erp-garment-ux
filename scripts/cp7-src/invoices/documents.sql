-- Complete supplier invoice documents may span several posted receipts.
-- Native draft/post/inverse writers retain all quantity and money authority.
create table cp7_invoice.requests(
 actor uuid not null,request_id uuid not null,action text not null,payload jsonb not null,
 expected_version text,response jsonb,primary key(actor,request_id)
);
alter table cp7_invoice.requests owner to cp7_invoice_write;
alter table cp7_invoice.requests enable row level security;
revoke all on cp7_invoice.requests from public,anon,authenticated,service_role,cp7_capture;
grant execute on function erp.save_material_supplier_invoice_draft_v2(jsonb,uuid,bigint),
 erp.post_material_supplier_invoice_v2(uuid,uuid,bigint,text) to cp7_invoice_write;

create function cp7_invoice.source_lines(p_purchase uuid) returns jsonb
language sql stable security invoker set search_path='' as $$
 select coalesce(jsonb_agg(jsonb_build_object('id',i.id,'material_id',i.material_id,'material_name',m.material_name,'unit_code',m.unit_code,
  'receipt_qty',i.qty::text,'estimate_unit_price',i.unit_price::text,'price_state',i.price_state,'invoice_match_state',i.invoice_match_state,
  'capacity',erp.material_purchase_invoice_capacity(i.id)::text,'invoiced_qty',erp.material_purchase_posted_invoice_qty(i.id)::text,
  'remaining_qty',case when i.invoice_match_state='DIRECT_FINAL' then '0' else (erp.material_purchase_invoice_capacity(i.id)-erp.material_purchase_posted_invoice_qty(i.id))::text end)
  order by i.id),'[]'::jsonb) from erp.material_purchase_items i join erp.materials m on m.id=i.material_id where i.purchase_id=p_purchase
$$;

create function cp7_invoice.sources(p_purchase uuid,p_q text,p_offset integer,p_limit integer) returns jsonb
language plpgsql stable security invoker set search_path='' as $$
declare h erp.material_purchase_headers;total bigint;rows jsonb;term text;
begin
 perform cp7_invoice.access_now();term:=btrim(coalesce(p_q,''));
 if p_purchase is null or length(term)>120 or p_offset is null or p_offset not between 0 and 1000000 or p_limit is null or p_limit not between 1 and 25 then raise exception 'CP7_INVOICE_QUERY';end if;
 select * into h from erp.material_purchase_headers where id=p_purchase;
 if not found or h.supplier_id is null then raise exception 'CP7_INVOICE_RECEIPT_NOT_FOUND';end if;
 select count(*) into total from erp.material_purchase_headers ph where ph.supplier_id=h.supplier_id and ph.status='POSTED' and (term='' or strpos(lower(ph.purchase_number),lower(term))>0);
 if exists(select 1 from (select ph.id from erp.material_purchase_headers ph where ph.supplier_id=h.supplier_id and ph.status='POSTED' and (term='' or strpos(lower(ph.purchase_number),lower(term))>0)
  order by ph.physical_at desc,ph.id limit p_limit offset p_offset) chosen where (select count(*) from erp.material_purchase_items where purchase_id=chosen.id)>100) then raise exception 'CP7_INVOICE_COMPLETE_DOCUMENT_REQUIRED';end if;
 select coalesce(jsonb_agg(jsonb_build_object('id',ph.id,'number',ph.purchase_number,'physical_at',ph.physical_at,'row_version',ph.row_version::text,
  'lines',cp7_invoice.source_lines(ph.id),'line_count',(select count(*)::text from erp.material_purchase_items where purchase_id=ph.id)) order by ph.physical_at desc,ph.id),'[]') into rows
 from (select x.* from erp.material_purchase_headers x where x.supplier_id=h.supplier_id and x.status='POSTED' and (term='' or strpos(lower(x.purchase_number),lower(term))>0)
  order by x.physical_at desc,x.id limit p_limit offset p_offset) ph;
 return jsonb_build_object('contract_version','cp7.invoice-sources.v1','read_at',statement_timestamp(),'purchase_id',p_purchase,'supplier_id',h.supplier_id,
  'page',jsonb_build_object('rows',rows,'total',total::text,'offset',p_offset,'limit',p_limit,'next_offset',case when p_offset+jsonb_array_length(rows)<total then p_offset+jsonb_array_length(rows) else null end));
end $$;
create function public.erp_cp7_get_invoice_sources_v1(p_purchase uuid,p_q text,p_offset integer,p_limit integer) returns jsonb
language sql stable security definer set search_path='' as $$select cp7_invoice.sources(p_purchase,p_q,p_offset,p_limit)$$;

create function cp7_invoice.validate_sources(p_purchase uuid,p_supplier uuid,p_lines jsonb) returns void
language plpgsql stable security definer set search_path='' as $$
declare count_lines integer;matched integer;anchored boolean;
begin
 perform cp7_invoice.access_now();count_lines:=jsonb_array_length(p_lines);
 select count(*),bool_or(ph.id=p_purchase) into matched,anchored from jsonb_array_elements(p_lines) line
 join erp.material_purchase_items i on i.id=(line->>'purchase_item_id')::uuid join erp.material_purchase_headers ph on ph.id=i.purchase_id
 where ph.supplier_id=p_supplier and ph.status='POSTED';
 if matched<>count_lines or anchored is distinct from true then raise exception 'CP7_INVOICE_SAME_SUPPLIER_POSTED_RECEIPTS_REQUIRED';end if;
 if (select count(distinct line->>'purchase_item_id') from jsonb_array_elements(p_lines) line)<>count_lines then raise exception 'CP7_INVOICE_DUPLICATE_LINE';end if;
end $$;

create function cp7_invoice.assert_document(p_invoice uuid,p_purchase uuid,p_reviewed jsonb) returns void
language plpgsql stable security definer set search_path='' as $$
declare ids jsonb;n integer;
begin
 perform cp7_invoice.access_now();
 if jsonb_typeof(p_reviewed) is distinct from 'array' or jsonb_array_length(p_reviewed) not between 1 and 100
  or exists(select 1 from jsonb_array_elements(p_reviewed) x where jsonb_typeof(x)<>'string') then raise exception 'CP7_INVOICE_COMPLETE_DOCUMENT_REQUIRED';end if;
 select count(*),jsonb_agg(distinct i.purchase_id::text order by i.purchase_id::text) into n,ids
 from erp.material_supplier_invoice_lines l join erp.material_purchase_items i on i.id=l.purchase_item_id where l.invoice_id=p_invoice;
 if n not between 1 and 100 or ids is null or not ids ? p_purchase::text
  or ids is distinct from (select jsonb_agg(x order by x) from jsonb_array_elements(p_reviewed) x)
  or exists(select 1 from erp.material_supplier_invoice_lines l join erp.material_purchase_items i on i.id=l.purchase_item_id
   join erp.material_purchase_headers ph on ph.id=i.purchase_id join erp.material_supplier_invoices ih on ih.id=l.invoice_id
   where ih.id=p_invoice and ph.supplier_id is distinct from ih.supplier_id) then raise exception 'CP7_INVOICE_COMPLETE_DOCUMENT_REQUIRED';end if;
end $$;

create function cp7_invoice.document_command(p_action text,p_payload jsonb,p_request uuid,p_expected text) returns jsonb
language plpgsql volatile security invoker set search_path='' as $$
declare a jsonb;r jsonb;old cp7_invoice.requests;l jsonb;expected bigint;pid uuid;ident uuid;
begin
 if current_setting('transaction_isolation')<>'read committed' then raise exception 'CP7_FRESH_ACCESS_REQUIRED';end if;
 a:=cp7_invoice.access_now();
 if p_action is null or p_action not in('SAVE_DOCUMENT','POST_DOCUMENT','DELETE_DOCUMENT','REVERSE_DOCUMENT') or p_request is null then raise exception 'CP7_INVOICE_ACTION';end if;
 if a->(case when p_action='REVERSE_DOCUMENT' then 'reverse' else 'finalize' end) is distinct from 'true'::jsonb then raise exception using errcode='42501',message='CP7_INVOICE_DOCUMENT_ACTION_DENIED';end if;
 if p_expected is not null and p_expected!~'^[1-9][0-9]{0,18}$' then raise exception 'CP7_INVOICE_VERSION';end if;expected:=p_expected::bigint;
 if jsonb_typeof(p_payload) is distinct from 'object' then raise exception 'CP7_INVOICE_FIELDS';end if;
 insert into cp7_invoice.requests values(auth.uid(),p_request,p_action,p_payload,p_expected,null) on conflict do nothing;
 select * into old from cp7_invoice.requests where actor=auth.uid() and request_id=p_request for update;
 if old.action<>p_action or old.payload is distinct from p_payload or old.expected_version is distinct from p_expected then raise exception 'CP7_INVOICE_REQUEST_CHANGED';end if;
 if cp7_invoice.access_now()<>a then raise exception using errcode='42501',message='CP7_INVOICE_ACCESS_CHANGED';end if;
 if old.response is not null then return old.response;end if;
 pid:=(p_payload->>'purchase_id')::uuid;
 if p_action='SAVE_DOCUMENT' then
  if not p_payload ?& array['purchase_id','invoice_number','supplier_id','invoice_date','received_at','change_reason','lines'] or exists(select 1 from jsonb_each(p_payload) e
   where e.key not in('purchase_id','id','invoice_number','supplier_id','invoice_date','received_at','change_reason','lines','due_date','notes') or(e.key<>'lines' and jsonb_typeof(e.value) not in('string','null'))) then raise exception 'CP7_INVOICE_FIELDS';end if;
  if exists(select 1 from unnest(array['purchase_id','invoice_number','supplier_id','invoice_date','received_at','change_reason']) k
   where jsonb_typeof(p_payload->k) is distinct from 'string' or nullif(btrim(p_payload->>k),'') is null) then raise exception 'CP7_INVOICE_FIELDS';end if;
  if ((p_payload->>'id') is null and expected is not null) or ((p_payload->>'id') is not null and expected is null) then raise exception 'CP7_INVOICE_VERSION';end if;
  if jsonb_typeof(p_payload->'lines') is distinct from 'array' or jsonb_array_length(p_payload->'lines') not between 1 and 100 then raise exception 'CP7_INVOICE_LINES';end if;
  for l in select value from jsonb_array_elements(p_payload->'lines') loop
   if jsonb_typeof(l) is distinct from 'object' or not l ?& array['purchase_item_id','qty_invoiced','unit_price']
    or exists(select 1 from jsonb_each(l) e where e.key not in('purchase_item_id','qty_invoiced','unit_price','discount_amount','notes') or jsonb_typeof(e.value) not in('string','null')) then raise exception 'CP7_INVOICE_LINE';end if;
   if l->>'qty_invoiced' is null or l->>'qty_invoiced'!~'^(0|[1-9][0-9]{0,11})(\.[0-9]{1,6})?$' or (l->>'qty_invoiced')::numeric<=0
    or l->>'unit_price' is null or l->>'unit_price'!~'^(0|[1-9][0-9]{0,11})(\.[0-9]{1,6})?$'
    or(l ? 'discount_amount' and (l->>'discount_amount' is null or l->>'discount_amount'!~'^(0|[1-9][0-9]{0,11})(\.[0-9]{1,6})?$')) then raise exception 'CP7_INVOICE_EXACT_DECIMAL';end if;
  end loop;
  perform cp7_invoice.validate_sources(pid,(p_payload->>'supplier_id')::uuid,p_payload->'lines');
  r:=erp.save_material_supplier_invoice_draft_v2(p_payload-'purchase_id',p_request,expected);
  perform cp7_invoice.validate_sources(pid,(p_payload->>'supplier_id')::uuid,p_payload->'lines');
 else
  if expected is null or not p_payload ?& array['purchase_id','invoice_id','reason','reviewed_purchase_ids'] or exists(select 1 from jsonb_each(p_payload) e
   where e.key not in('purchase_id','invoice_id','reason','reviewed_purchase_ids') or(e.key<>'reviewed_purchase_ids' and jsonb_typeof(e.value)<>'string')) then raise exception 'CP7_INVOICE_FIELDS';end if;
  ident:=(p_payload->>'invoice_id')::uuid;
  perform cp7_invoice.assert_document(ident,pid,p_payload->'reviewed_purchase_ids');
  if p_action='POST_DOCUMENT' then r:=erp.post_material_supplier_invoice_v2(ident,p_request,expected,p_payload->>'reason');
  elsif p_action='DELETE_DOCUMENT' then r:=erp.save_material_supplier_invoice_draft_v2(jsonb_build_object('id',ident,'action','DELETE','change_reason',p_payload->>'reason'),p_request,expected);
  else r:=erp.reverse_material_supplier_invoice_v2(ident,p_payload->>'reason',p_request,expected);end if;
  if p_action<>'DELETE_DOCUMENT' then perform cp7_invoice.assert_document(ident,pid,p_payload->'reviewed_purchase_ids');end if;
 end if;
 if cp7_invoice.access_now()<>a then raise exception using errcode='42501',message='CP7_INVOICE_ACCESS_CHANGED';end if;
 r:=jsonb_build_object('contract_version','cp7.purchase-invoice-outcome.v1','kind','COMMITTED_OUTCOME','action',p_action,'request_id',p_request,
  'purchase_id',pid,'invoice_id',r->'supplier_invoice_id','version_subject','INVOICE','row_version',r->>'row_version',
  'status',case when p_action='DELETE_DOCUMENT' then 'DELETED' else r->>'status' end);
 update cp7_invoice.requests set response=r where actor=auth.uid() and request_id=p_request;
 return r;
end $$;
