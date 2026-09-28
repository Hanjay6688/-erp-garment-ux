-- Usual service selections and past observed amounts. No rate resolver calls
-- this reader. The next dispatch always resolves a fresh vendor version.
CREATE OR REPLACE FUNCTION public.erp_get_laundry_history_v1(p_filters jsonb)
 RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO ''
AS $function$
declare vendor uuid;wave uuid;at_time timestamptz;money boolean;result jsonb;
begin
 perform erp.require_permission('production.laundry.view');
 perform erp._cp3_assert_closed_json_object(p_filters,array['vendor_id','wave_id'],array['vendor_id','wave_id','at'],'laundry history');
 vendor:=erp.bd_uuid_v1(p_filters,'vendor_id',true);wave:=erp.bd_uuid_v1(p_filters,'wave_id',true);
 at_time:=coalesce((p_filters->>'at')::timestamptz,statement_timestamp());
 if at_time>statement_timestamp() then raise exception 'BF_HISTORY_FUTURE';end if;
 money:=erp.has_permission('finance.hpp.view') or erp.has_permission('finance.hpp.manage');
 with chosen as materialized(
   select w.sku_id,s.sku,array_agg(w.size_id order by w.size_id) sizes
   from erp.bf_wave_skus_v1 w join erp.bf_skus_v1 s on s.id=w.sku_id
   where w.cutting_group_id=wave and exists(select 1 from erp.bf_sku_versions_v1 v
     join erp.bf_sku_members_v1 m on m.version_id=v.id join erp.products p on p.id=m.product_root
     where v.sku_id=w.sku_id and p.size_id=w.size_id and v.effective_from<=at_time and(v.effective_to is null or v.effective_to>at_time))
   group by w.sku_id,s.sku
 ), past_sizes as materialized(
   select c.sku_id,l.id line_id,w.size_id from chosen c join erp.bf_wave_skus_v1 w on w.sku_id=c.sku_id
   join erp.laundry_delivery_lines l on l.cutting_group_id=w.cutting_group_id
   union
   select c.sku_id,r.delivery_line_id,p.size_id from chosen c
   join erp.bf_sku_versions_v1 v on v.sku_id=c.sku_id
   join erp.bf_sku_members_v1 m on m.version_id=v.id
   join erp.products p on p.identity_root_id=m.product_root
   join erp.fg_lots f on f.product_id=p.id and f.produced_at>=v.effective_from and(v.effective_to is null or f.produced_at<v.effective_to)
   join erp.qc_inspection_items qi on qi.id=f.qc_item_id
   join erp.laundry_receipt_lines r on r.id=qi.source_laundry_receipt_line_id
 ), history as materialized(
   select c.sku_id,c.sku,c.sizes target_sizes,d.id delivery_id,d.delivery_number,d.physical_at,
     d.target_wash_process_id process_id,l.id line_id,p.pricing_mode,p.total_complete,p.total_known,p.qty_sent,
     (select array_agg(ps.size_id order by ps.size_id) from past_sizes ps where ps.line_id=l.id and ps.sku_id=c.sku_id) source_sizes
   from chosen c join erp.laundry_delivery_lines l on exists(select 1 from past_sizes ps where ps.line_id=l.id and ps.sku_id=c.sku_id)
   join erp.laundry_deliveries d on d.id=l.delivery_id and d.vendor_id=vendor and d.status not in('DRAFT','REVERSED') and d.physical_at<=at_time
   join erp.bd_laundry_priced_lines_v1 p on p.delivery_line_id=l.id
   where exists(select 1 from erp.bd_laundry_charge_lines_v1 ch where ch.delivery_line_id=l.id)
   order by d.physical_at desc,d.id,c.sku_id limit 20
 ) select jsonb_build_object('vendor_id',vendor,'wave_id',wave,'at',at_time,'money_visible',money,
   'known_skus',(select count(*) from chosen),
   'items',coalesce((select jsonb_agg(jsonb_build_object('sku_id',h.sku_id,'sku',h.sku,'target_size_ids',h.target_sizes,
     'delivery_id',h.delivery_id,'number',h.delivery_number,'at',h.physical_at,'process_id',h.process_id,'mode',h.pricing_mode,
     'reference_total',case when money and h.total_complete then h.total_known::numeric(18,2)::text end,
     'reference_qty',h.qty_sent,'amount_scope','WHOLE_PREVIOUS_DELIVERY',
     'charges',coalesce((select jsonb_agg(jsonb_build_object('kind',ch.kind,'ref_id',ch.ref_id,'label',ch.label,
       'all_source_pieces',not exists(select 1 from erp.bd_laundry_charge_shares_v1 sh join erp.laundry_delivery_batch_size_lines ds on ds.id=sh.delivery_batch_size_line_id
         where sh.charge_line_id=ch.id and ds.size_id=any(h.source_sizes) and sh.covered_qty<>ds.qty_sent_pcs)) order by ch.line_no)
       from erp.bd_laundry_charge_lines_v1 ch where ch.delivery_line_id=h.line_id and exists(
         select 1 from erp.bd_laundry_charge_shares_v1 sh join erp.laundry_delivery_batch_size_lines ds on ds.id=sh.delivery_batch_size_line_id
         where sh.charge_line_id=ch.id and sh.covered_qty>0 and ds.size_id=any(h.source_sizes))),'[]'))
     order by h.physical_at desc,h.delivery_id,h.sku_id) from history h),'[]')) into result;
 return result;
end;$function$;
