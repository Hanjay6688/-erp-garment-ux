-- Operational reads deliberately expose no financial metadata to a reader
-- without finance.ap.view. These are live, paged workspaces, not planner captures.
create function cp7_procurement.header(h erp.material_purchase_headers,can_value boolean) returns jsonb
language sql stable security invoker set search_path='' as $$
 select jsonb_build_object('id',h.id,'purchase_number',h.purchase_number,'supplier_id',h.supplier_id,
  'supplier_name',(select s.supplier_name from erp.suppliers s where s.id=h.supplier_id),
  'location_id',h.location_id,'location_name',(select l.location_name from erp.locations l where l.id=h.location_id),
  'physical_at',h.physical_at,'status',h.status,'row_version',h.row_version::text,
  'notes',h.notes,'line_count',(select count(*) from erp.material_purchase_items i where i.purchase_id=h.id))
 || case when can_value then jsonb_build_object('finance',jsonb_build_object(
  'supplier_invoice_number',h.supplier_invoice_number,'due_date',h.due_date,'payment_status',h.payment_status,
  'receipt_value',(select coalesce(sum(i.line_total),0)::text from erp.material_purchase_items i where i.purchase_id=h.id),
  'basis','RECEIPT_PRICE_NOT_CURRENT_PAYABLE')) else '{}'::jsonb end
$$;

create function cp7_procurement.workspace(p_query jsonb) returns jsonb
language plpgsql stable security invoker set search_path='' as $$
declare a jsonb;outrows jsonb;items jsonb;detail jsonb:='null'::jsonb;h erp.material_purchase_headers;
 q text;st text;n integer;off integer;pid uuid;total bigint;rolled integer;
begin
 a:=cp7_procurement.access_now();
 perform cp7_procurement.fields(p_query,array['q','status','limit','offset','purchase_id'],array[]::text[]);
 if exists(select 1 from jsonb_each(p_query) e where e.key in ('q','status','purchase_id') and jsonb_typeof(e.value) not in ('string','null')) then raise exception 'CP7_PROCUREMENT_QUERY';end if;
 if (p_query ? 'limit' and (jsonb_typeof(p_query->'limit')<>'number' or (p_query->>'limit')!~'^[0-9]{1,3}$'))
  or(p_query ? 'offset' and (jsonb_typeof(p_query->'offset')<>'number' or (p_query->>'offset')!~'^[0-9]{1,7}$')) then raise exception 'CP7_PROCUREMENT_PAGE';end if;
 q:=btrim(coalesce(p_query->>'q',''));st:=coalesce(p_query->>'status','ALL');n:=coalesce((p_query->>'limit')::integer,25);off:=coalesce((p_query->>'offset')::integer,0);
 pid:=nullif(p_query->>'purchase_id','')::uuid;
 if length(q)>120 or st not in ('ALL','DRAFT','POSTED','REVERSED') or n not between 1 and 100 or off not between 0 and 1000000 then raise exception 'CP7_PROCUREMENT_QUERY';end if;
 select count(*) into total from erp.material_purchase_headers x left join erp.suppliers s on s.id=x.supplier_id
 where (st='ALL' or x.status=st) and (q='' or strpos(lower(x.purchase_number||' '||coalesce(s.supplier_name,'')),lower(q))>0);
 select coalesce(jsonb_agg(cp7_procurement.header(x::erp.material_purchase_headers,(a->>'can_value')::boolean) order by x.physical_at desc,x.id),'[]'::jsonb) into outrows
 from (select x.* from erp.material_purchase_headers x left join erp.suppliers s on s.id=x.supplier_id
  where (st='ALL' or x.status=st) and (q='' or strpos(lower(x.purchase_number||' '||coalesce(s.supplier_name,'')),lower(q))>0)
  order by x.physical_at desc,x.id limit n offset off) x;
 if pid is not null then
  select * into h from erp.material_purchase_headers where id=pid;
  if not found then raise exception 'CP7_PROCUREMENT_NOT_FOUND';end if;
  if (select count(*) from erp.material_purchase_items where purchase_id=pid)>100 then raise exception 'CP7_PROCUREMENT_DOCUMENT_TOO_LARGE';end if;
  select count(*) into rolled from erp.material_rolls r join erp.material_purchase_items i on i.id=r.purchase_item_id where i.purchase_id=pid;
  if rolled>2000 then raise exception 'CP7_PROCUREMENT_DOCUMENT_TOO_LARGE';end if;
  select coalesce(jsonb_agg(jsonb_build_object('id',i.id,'material_id',i.material_id,'material_sku',m.material_sku,
   'material_name',m.material_name,'material_type',m.material_type,'unit_code',m.unit_code,'qty',i.qty::text,
   'purchase_qty_entered',i.purchase_qty_entered::text,'purchase_uom_code',i.purchase_uom_code,'purchase_uom_factor',i.purchase_uom_factor_snapshot::text,
   'lot_number',i.lot_number,'notes',i.notes,
   'rolls',coalesce((select jsonb_agg(jsonb_build_object('id',r.id,'roll_number',r.roll_number,
     'receipt_qty',r.original_qty::text,'notes',r.notes) order by r.roll_number,r.id)
    from erp.material_rolls r where r.purchase_item_id=i.id),'[]'::jsonb))
   ||case when (a->>'can_value')::boolean then jsonb_build_object('finance',jsonb_build_object(
    'unit_price',i.unit_price::text,'line_total',i.line_total::text,'price_state',i.price_state,'price_source',i.price_source,
    'invoice_match_state',i.invoice_match_state,'benchmark_price_version_id',i.benchmark_price_version_id)) else '{}'::jsonb end order by i.id),'[]'::jsonb)
   into items from erp.material_purchase_items i join erp.materials m on m.id=i.material_id where i.purchase_id=pid;
  detail:=cp7_procurement.header(h,(a->>'can_value')::boolean)||jsonb_build_object('items',items,
   'stock_effect',case when h.status='DRAFT' then 'NOT_POSTED' when h.status='POSTED' then 'POSTED_RECEIPT' else 'REVERSED_RECEIPT' end,
   'quantity_basis','RECEIPT_DOCUMENT_NOT_CURRENT_ON_HAND');
 end if;
 return jsonb_build_object('contract_version','cp7.procurement-workspace.v1','kind','LIVE_WORKSPACE','read_at',statement_timestamp(),
  'capabilities',jsonb_build_object('create',a->'can_create','post',a->'can_post','reverse',(a->>'can_reverse')::boolean and a->'profile'->>'role_code' in('OWNER','ADMIN'),'view_value',a->'can_value'),
  'page',jsonb_build_object('rows',outrows,'total',total::text,'offset',off,'limit',n,
   'next_offset',case when off+jsonb_array_length(outrows)<total then off+jsonb_array_length(outrows) else null end),
  'detail',detail);
end $$;

create function cp7_procurement.options(p_kind text,p_q text,p_offset integer,p_limit integer) returns jsonb
language plpgsql stable security invoker set search_path='' as $$
declare a jsonb;rows jsonb;total bigint;q text:=lower(btrim(coalesce(p_q,'')));
begin
 a:=cp7_procurement.access_now();
 if p_kind is null or p_kind not in ('MATERIAL','SUPPLIER','LOCATION') or length(q)>120
  or p_offset is null or p_offset not between 0 and 1000000 or p_limit is null or p_limit not between 1 and 100 then raise exception 'CP7_PROCUREMENT_OPTIONS';end if;
 if p_kind='MATERIAL' then
  select count(*) into total from erp.materials m where m.is_active and (q='' or strpos(lower(m.material_sku||' '||m.material_name),q)>0);
  select coalesce(jsonb_agg(jsonb_build_object('id',m.id,'code',m.material_sku,'name',m.material_name,'material_type',m.material_type,
   'unit_code',m.unit_code) order by m.material_sku,m.id),'[]'::jsonb) into rows
  from (select * from erp.materials m where m.is_active and (q='' or strpos(lower(m.material_sku||' '||m.material_name),q)>0)
   order by m.material_sku,m.id limit p_limit offset p_offset) m;
 elsif p_kind='SUPPLIER' then
  select count(*) into total from erp.suppliers s where s.is_active and (q='' or strpos(lower(s.supplier_code||' '||s.supplier_name),q)>0);
  select coalesce(jsonb_agg(jsonb_build_object('id',s.id,'code',s.supplier_code,'name',s.supplier_name) order by s.supplier_code,s.id),'[]'::jsonb) into rows
  from (select * from erp.suppliers s where s.is_active and (q='' or strpos(lower(s.supplier_code||' '||s.supplier_name),q)>0)
   order by s.supplier_code,s.id limit p_limit offset p_offset) s;
 else
  select count(*) into total from erp.locations l where l.is_active and l.location_type='RAW_MATERIAL_WAREHOUSE' and not exists(select 1 from erp.bc_accessory_zones_v1 z where z.location_id=l.id) and (q='' or strpos(lower(l.location_code||' '||l.location_name),q)>0);
  select coalesce(jsonb_agg(jsonb_build_object('id',l.id,'code',l.location_code,'name',l.location_name) order by l.location_code,l.id),'[]'::jsonb) into rows
  from (select * from erp.locations l where l.is_active and l.location_type='RAW_MATERIAL_WAREHOUSE' and not exists(select 1 from erp.bc_accessory_zones_v1 z where z.location_id=l.id) and (q='' or strpos(lower(l.location_code||' '||l.location_name),q)>0)
   order by l.location_code,l.id limit p_limit offset p_offset) l;
 end if;
 return jsonb_build_object('contract_version','cp7.procurement-options.v1','kind',p_kind,'rows',rows,'total',total::text,
  'offset',p_offset,'limit',p_limit,'next_offset',case when p_offset+jsonb_array_length(rows)<total then p_offset+jsonb_array_length(rows) else null end);
end $$;
