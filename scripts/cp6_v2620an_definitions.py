#!/usr/bin/env python3
"""AN versioned read-only selector; legacy reader and write APIs stay exact."""
PRIVATE_ID="erp.get_cutting_workspace_v2(text,uuid,integer,integer,text,integer,integer,text,integer,integer,uuid,uuid)"
PUBLIC_ID="public.erp_get_cutting_workspace_v2(text,uuid,integer,integer,text,integer,integer,text,integer,integer,uuid,uuid)"
PRIVATE=r"""CREATE OR REPLACE FUNCTION erp.get_cutting_workspace_v2(p_roll_query text DEFAULT NULL::text, p_location_id uuid DEFAULT NULL::uuid, p_limit integer DEFAULT 100, p_offset integer DEFAULT 0, p_order_query text DEFAULT NULL::text, p_order_limit integer DEFAULT 50, p_order_offset integer DEFAULT 0, p_draft_query text DEFAULT NULL::text, p_draft_limit integer DEFAULT 25, p_draft_offset integer DEFAULT 0, p_selected_order_id uuid DEFAULT NULL::uuid, p_selected_draft_id uuid DEFAULT NULL::uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare v_query text:=lower(nullif(btrim(p_roll_query),''));
  v_order_query text:=lower(nullif(btrim(p_order_query),''));
  v_draft_query text:=lower(nullif(btrim(p_draft_query),''));
  v_order jsonb;
  v_draft jsonb;
begin
  perform erp.require_permission('production.cutting.view');
  if p_limit is null or p_limit<1 or p_limit>200 then raise exception 'limit must be between 1 and 200'; end if;
  if p_offset is null or p_offset<0 then raise exception 'offset must be nonnegative'; end if;
  if p_location_id is not null and not exists(
    select 1 from erp.locations l where l.id=p_location_id and l.is_active and l.location_type='RAW_MATERIAL_WAREHOUSE'
  ) then raise exception 'Active raw-material warehouse is required'; end if;

  if p_order_limit is null or p_order_limit<1 or p_order_limit>200
     or p_draft_limit is null or p_draft_limit<1 or p_draft_limit>100
     or p_order_offset is null or p_order_offset<0
     or p_draft_offset is null or p_draft_offset<0 then
    raise exception 'AN_INVALID_SELECTOR_PAGE';
  end if;
  if length(p_order_query)>200 or length(p_draft_query)>200 then
    raise exception 'AN_SELECTOR_QUERY_TOO_LONG';
  end if;

  with eligible as not materialized (
        select po.id,po.po_number,po.model_id,m.model_code,m.model_name,
          po.status,po.current_stage,po.contractor_id,c.contractor_name
        from erp.production_orders po
        join erp.product_models m on m.id=po.model_id
        left join erp.contractors c on c.id=po.contractor_id
        where po.status not in ('FINISHED','CANCELLED')
  ), page as (
    select * from eligible where (v_order_query is null or strpos(lower(concat_ws(' ',po_number,model_code,model_name,contractor_name)),v_order_query)>0)
    order by po_number,id limit p_order_limit offset p_order_offset
  ), targets as (
    select * from page union select * from eligible where id=p_selected_order_id
  ), serialized as (
    select x.id,x.po_number,
      jsonb_build_object(
        'id',x.id,'po_number',x.po_number,'model_id',x.model_id,
        'model_code',x.model_code,'model_name',x.model_name,
        'status',x.status,'current_stage',x.current_stage,
        'contractor_id',x.contractor_id,'contractor_name',x.contractor_name
      ) as datum from targets x
  )
  select jsonb_build_object(
    'query',v_order_query,'limit',p_order_limit,'offset',p_order_offset,
    'total',(select count(*) from eligible where (v_order_query is null or strpos(lower(concat_ws(' ',po_number,model_code,model_name,contractor_name)),v_order_query)>0)),
    'rows',coalesce((select jsonb_agg(s.datum order by s.po_number,s.id)
      from serialized s join page p on p.id=s.id),'[]'::jsonb),
    'selected',(select datum from serialized where id=p_selected_order_id)
  ) into v_order;

  with eligible as not materialized (
        select g.*,po.model_id,po.po_number,pm.model_code,pm.model_name,p.is_active pattern_is_active,
          erp.is_cutting_group_presewing_reversible(g.id) editable
        from erp.cutting_groups g
        join erp.production_orders po on po.id=g.po_id
        join erp.product_models pm on pm.id=po.model_id
        left join erp.production_patterns p on p.id=g.pattern_id
        where g.status='CUT' and g.picked_up_at is null and not g.material_issue_posted
  ), page as (
    select * from eligible where (v_draft_query is null or strpos(lower(concat_ws(' ',group_number,po_number,model_code,model_name,pattern_code_snapshot,pattern_revision_snapshot,pattern_name_snapshot)),v_draft_query)>0)
    order by updated_at desc,id desc limit p_draft_limit offset p_draft_offset
  ), targets as (
    select * from page union select * from eligible where id=p_selected_draft_id
  ), serialized as (
    select x.id,x.po_number,x.updated_at,
      jsonb_build_object(
        'cutting_group_id',x.id,'group_number',x.group_number,'row_version',x.row_version,
        'model_id',x.model_id,'po_id',x.po_id,'po_number',x.po_number,'model_code',x.model_code,'model_name',x.model_name,
        'cut_at',x.cut_at,'source_location_id',x.source_location_id,'notes',x.notes,
        'pattern_id',x.pattern_id,'pattern_code',x.pattern_code_snapshot,
        'pattern_revision',x.pattern_revision_snapshot,'pattern_name',x.pattern_name_snapshot,
        'pattern_is_active',x.pattern_is_active,'editable',x.editable,
        'size_slots',coalesce((
          select jsonb_agg(jsonb_build_object(
            'slot_no',ss.slot_no,'size_id',ss.size_id,'size_code',sz.size_code,
            'drawing_no',ss.drawing_no,'label_override',ss.label_override
          ) order by ss.slot_no,ss.id)
          from erp.cutting_group_size_slots ss join erp.sizes sz on sz.id=ss.size_id
          where ss.cutting_group_id=x.id
        ),'[]'::jsonb),
        'rolls',coalesce((
          select jsonb_agg(jsonb_build_object(
            'roll_id',r.roll_id,'roll_number',mr.roll_number,'material_id',mr.material_id,
            'material_sku',m.material_sku,'material_name',m.material_name,'unit_code',m.unit_code,
            'supplier_id',mr.supplier_id,'supplier_name',s.supplier_name,
            'original_qty',mr.original_qty,'qty_issued',r.qty_issued,
            'qty_consumed',coalesce(r.qty_consumed,r.qty_issued),
            'qty_reported_remaining',coalesce(r.qty_reported_remaining,greatest(r.qty_issued-coalesce(r.qty_consumed,r.qty_issued),0)),
            'yields',coalesce((
              select jsonb_agg(jsonb_build_object('slot_no',ss.slot_no,'qty_pcs',y.qty_pcs)
                order by ss.slot_no,y.id)
              from erp.cutting_roll_yields y
              join erp.cutting_group_size_slots ss on ss.id=y.size_slot_id
              where y.cutting_group_roll_id=r.id
            ),'[]'::jsonb)
          ) order by m.material_name,mr.roll_number,mr.id)
          from erp.cutting_group_rolls r
          join erp.material_rolls mr on mr.id=r.roll_id
          join erp.materials m on m.id=mr.material_id
          left join erp.suppliers s on s.id=mr.supplier_id
          where r.cutting_group_id=x.id
        ),'[]'::jsonb)
      ) as datum from targets x
  )
  select jsonb_build_object(
    'query',v_draft_query,'limit',p_draft_limit,'offset',p_draft_offset,
    'total',(select count(*) from eligible where (v_draft_query is null or strpos(lower(concat_ws(' ',group_number,po_number,model_code,model_name,pattern_code_snapshot,pattern_revision_snapshot,pattern_name_snapshot)),v_draft_query)>0)),
    'rows',coalesce((select jsonb_agg(s.datum order by s.updated_at desc,s.id desc)
      from serialized s join page p on p.id=s.id),'[]'::jsonb),
    'selected',(select datum from serialized where id=p_selected_draft_id)
  ) into v_draft;

  return jsonb_build_object(
    'contract_version',2,
    'order_page',v_order-'rows'-'selected','draft_page',v_draft-'rows'-'selected',
    'selected_order_id',p_selected_order_id,'selected_order',v_order->'selected',
    'selected_draft_id',p_selected_draft_id,'selected_draft',v_draft->'selected',
    'roll_query',v_query,'location_id',p_location_id,'limit',p_limit,'offset',p_offset,
    'orders',v_order->'rows',
    'sizes',coalesce((
      select jsonb_agg(jsonb_build_object(
          'id',s.id,'code',s.size_code,'sort_order',s.sort_order,
          'model_ids',coalesce((
            select jsonb_agg(pms.model_id order by pms.sort_order,pms.model_id)
            from erp.product_model_sizes pms where pms.size_id=s.id
          ),'[]'::jsonb)
        )
        order by s.sort_order,s.size_code,s.id)
      from erp.sizes s where s.is_active
    ),'[]'::jsonb),
    'locations',coalesce((
      select jsonb_agg(jsonb_build_object('id',l.id,'code',l.location_code,'name',l.location_name)
        order by l.location_code,l.id)
      from erp.locations l where l.is_active and l.location_type='RAW_MATERIAL_WAREHOUSE'
    ),'[]'::jsonb),
    'contractors',coalesce((
      select jsonb_agg(jsonb_build_object('id',c.id,'code',c.contractor_code,'name',c.contractor_name)
        order by c.contractor_name,c.contractor_code,c.id)
      from erp.contractors c where c.is_active and c.contractor_type='MANDOR'
    ),'[]'::jsonb),
    'drafts',v_draft->'rows',
    'roll_total',case when p_location_id is null then 0 else (
      with stock as (
        select msm.roll_id,sum(msm.qty_signed)::numeric available_qty
        from erp.material_stock_movements msm
        where msm.location_id=p_location_id and msm.roll_id is not null
        group by msm.roll_id having sum(msm.qty_signed)>0
      )
      select count(*) from stock st
      join erp.material_rolls r on r.id=st.roll_id
      join erp.materials m on m.id=r.material_id
      left join erp.suppliers s on s.id=r.supplier_id
      where r.status in ('AVAILABLE','HALF_USED')
        and (v_query is null or lower(concat_ws(' ',r.roll_number,m.material_sku,m.material_name,s.supplier_code,s.supplier_name)) like '%'||v_query||'%')
    ) end,
    'rolls',case when p_location_id is null then '[]'::jsonb else coalesce((
      with stock as (
        select msm.roll_id,sum(msm.qty_signed)::numeric available_qty
        from erp.material_stock_movements msm
        where msm.location_id=p_location_id and msm.roll_id is not null
        group by msm.roll_id having sum(msm.qty_signed)>0
      )
      select jsonb_agg(jsonb_build_object(
        'id',x.id,'roll_number',x.roll_number,'material_id',x.material_id,
        'material_sku',x.material_sku,'material_name',x.material_name,'unit_code',x.unit_code,
        'supplier_id',x.supplier_id,'supplier_code',x.supplier_code,'supplier_name',x.supplier_name,
        'original_qty',x.original_qty,'available_qty',x.available_qty,'status',x.status,
        'received_at',x.received_at
      ) order by x.material_name,x.roll_number,x.id)
      from (
        select r.id,r.roll_number,r.material_id,m.material_sku,m.material_name,m.unit_code,
          r.supplier_id,s.supplier_code,s.supplier_name,r.original_qty,st.available_qty,r.status,r.received_at
        from stock st
        join erp.material_rolls r on r.id=st.roll_id
        join erp.materials m on m.id=r.material_id
        left join erp.suppliers s on s.id=r.supplier_id
        where r.status in ('AVAILABLE','HALF_USED')
          and (v_query is null or lower(concat_ws(' ',r.roll_number,m.material_sku,m.material_name,s.supplier_code,s.supplier_name)) like '%'||v_query||'%')
        order by m.material_name,r.roll_number,r.id limit p_limit offset p_offset
      ) x
    ),'[]'::jsonb) end
  );
end
$function$
"""
PUBLIC=r"""CREATE OR REPLACE FUNCTION public.erp_get_cutting_workspace_v2(p_roll_query text DEFAULT NULL::text, p_location_id uuid DEFAULT NULL::uuid, p_limit integer DEFAULT 100, p_offset integer DEFAULT 0, p_order_query text DEFAULT NULL::text, p_order_limit integer DEFAULT 50, p_order_offset integer DEFAULT 0, p_draft_query text DEFAULT NULL::text, p_draft_limit integer DEFAULT 25, p_draft_offset integer DEFAULT 0, p_selected_order_id uuid DEFAULT NULL::uuid, p_selected_draft_id uuid DEFAULT NULL::uuid)
 RETURNS jsonb
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
  select erp.get_cutting_workspace_v2(p_roll_query, p_location_id, p_limit, p_offset, p_order_query, p_order_limit, p_order_offset, p_draft_query, p_draft_limit, p_draft_offset, p_selected_order_id, p_selected_draft_id);
$function$
"""
