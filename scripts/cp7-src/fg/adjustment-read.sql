create function cp7_fg.adjust_header(h erp.fg_adjustments) returns jsonb
language sql stable security invoker set search_path='' as $$
 select jsonb_build_object('id',h.id,'number',h.adjustment_number,'location_id',h.location_id,'location_name',(select location_name from erp.locations where id=h.location_id),
  'physical_at',h.physical_at,'reason_code',h.reason_code,'reason',h.reason,'notes',h.notes,'status',h.status,'row_version',h.row_version::text,
  'managed',exists(select 1 from cp7_fg.adjustment_documents where adjustment_id=h.id),
  'line_count',(select count(*)::text from erp.fg_adjustment_items where adjustment_id=h.id))
$$;
create function cp7_fg.adjust_workspace(p_query jsonb) returns jsonb
language plpgsql stable security invoker set search_path='' as $$
declare a jsonb;q text;n integer;off integer;chosen uuid;total bigint;rows jsonb;detail jsonb:=null;h erp.fg_adjustments;items jsonb;editable boolean;
begin
 a:=cp7_fg.adjust_access();
 if jsonb_typeof(p_query) is distinct from 'object' or exists(select 1 from jsonb_object_keys(p_query) k where k not in('q','limit','offset','adjustment_id'))
  or exists(select 1 from jsonb_each(p_query) e where e.key in('q','adjustment_id') and jsonb_typeof(e.value) not in('string','null'))
  or(p_query ? 'limit' and (jsonb_typeof(p_query->'limit')<>'number' or (p_query->>'limit')!~'^[0-9]{1,3}$'))
  or(p_query ? 'offset' and (jsonb_typeof(p_query->'offset')<>'number' or (p_query->>'offset')!~'^[0-9]{1,7}$')) then raise exception 'CP7_FG_ADJUST_QUERY';end if;
 q:=btrim(coalesce(p_query->>'q',''));n:=coalesce((p_query->>'limit')::integer,25);off:=coalesce((p_query->>'offset')::integer,0);chosen:=(p_query->>'adjustment_id')::uuid;
 if length(q)>120 or n not between 1 and 100 or off not between 0 and 1000000 then raise exception 'CP7_FG_ADJUST_QUERY';end if;
 select count(*) into total from erp.fg_adjustments doc where q='' or strpos(lower(doc.adjustment_number),lower(q))>0;
 select coalesce(jsonb_agg(cp7_fg.adjust_header(x) order by x.physical_at desc,x.id),'[]') into rows
 from(select * from erp.fg_adjustments doc where q='' or strpos(lower(doc.adjustment_number),lower(q))>0 order by physical_at desc,id limit n offset off)x;
 if chosen is not null then
  select * into h from erp.fg_adjustments where id=chosen;
  if not found then raise exception 'CP7_FG_ADJUST_NOT_FOUND';end if;
  if (select count(*) from erp.fg_adjustment_items where adjustment_id=chosen)>100 then raise exception 'CP7_FG_ADJUST_DOCUMENT_TOO_LARGE';end if;
  select coalesce(jsonb_agg(jsonb_build_object('id',i.id,'product_id',i.product_id,'product_sku',p.sku,'commercial_sku',erp.bf_commercial_sku_at_v1(p.id,h.physical_at),
   'size_code',s.size_code,'lot_id',i.lot_id,'lot_number',l.lot_number,'quality_grade',i.quality_grade,'qty_signed',i.qty_signed::text,'notes',i.notes)
   ||case when a->'can_value'='true'::jsonb then jsonb_build_object('valuation',cp7_fg.lot_value(l.id,i.qty_signed)) else '{}'::jsonb end order by i.id),'[]') into items
  from erp.fg_adjustment_items i join erp.fg_lots l on l.id=i.lot_id join erp.products p on p.id=i.product_id join erp.sizes s on s.id=p.size_id where i.adjustment_id=chosen;
  editable:=h.status='DRAFT' and a->'can_adjust'='true'::jsonb and exists(select 1 from cp7_fg.adjustment_documents where adjustment_id=chosen and source_signature=cp7_fg.adjust_signature(chosen));
  detail:=cp7_fg.adjust_header(h)||jsonb_build_object('items',items,'editable',editable);
 end if;
 return jsonb_build_object('contract_version','cp7.fg-adjustments.v1','read_at',statement_timestamp(),'financial_captured',a->'can_value','can_adjust',a->'can_adjust',
  'page',jsonb_build_object('rows',rows,'total',total::text,'offset',off,'limit',n,'next_offset',case when off+jsonb_array_length(rows)<total then off+jsonb_array_length(rows) else null end),'detail',detail);
end $$;
create function public.erp_cp7_get_fg_adjustments_v1(p_query jsonb) returns jsonb
language sql stable security definer set search_path='' as $$select cp7_fg.adjust_workspace(p_query)$$;
