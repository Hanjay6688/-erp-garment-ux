-- Scoped source facts for immutable runs; monetary facts read only when authorized.
create function cp7_private.capture_sources(p_root uuid,p_financial boolean) returns jsonb
language sql stable security invoker set search_path='' set timezone='Asia/Jakarta' as $cp7source$
with clock as materialized (
  -- The request may have waited before this INSERT/SELECT acquired its snapshot.
  -- Materialize the capture-time clock once, after the request lock is acquired.
  select p_root as root_id, clock_timestamp() as at
),
physical as materialized (
  select p.id,coalesce(p.identity_root_id,p.id) root_id,p.size_id,p.model_id,p.brand_id,
         p.effective_from,p.effective_to
  from erp.products p cross join clock c
  where coalesce(p.identity_root_id,p.id)=c.root_id
    and p.effective_from<=c.at and (p.effective_to is null or p.effective_to>c.at)
  order by p.effective_from desc,p.id limit 2
),
scope as materialized (select * from physical limit 1),
memberships as materialized (
  select v.id version_id,v.revision,s.id sku_id,s.sku
  from erp.bf_sku_members_v1 m join erp.bf_sku_versions_v1 v on v.id=m.version_id
  join erp.bf_skus_v1 s on s.id=v.sku_id cross join clock c
  where m.product_root=c.root_id and v.effective_from<=c.at
    and (v.effective_to is null or v.effective_to>c.at)
  order by v.effective_from desc,v.id limit 2
),
cutting_page as materialized (
  select y.id yield_id,g.id cutting_group_id,g.po_id,slot.id slot_id,
         slot.size_id,g.pattern_id,g.pattern_revision_snapshot,
         g.row_version,y.qty_pcs,g.cut_at
  from scope p join erp.production_orders po on po.model_id=p.model_id
  join erp.cutting_groups g on g.po_id=po.id
  join erp.cutting_group_size_slots slot on slot.cutting_group_id=g.id and slot.size_id=p.size_id
  join erp.cutting_group_rolls roll on roll.cutting_group_id=g.id
  join erp.cutting_roll_yields y on y.cutting_group_roll_id=roll.id and y.size_slot_id=slot.id
  cross join clock c
  where g.cut_at<=c.at
  order by g.cut_at,g.id,slot.id,y.id limit 501
),
stock_page as materialized (
  select m.id,m.product_id,m.lot_id,m.location_id,m.quality_grade,m.qty_signed,
         m.physical_at,m.system_created_at,m.reversal_of_id
  from erp.fg_stock_movements m cross join clock c
  join erp.products p on p.id=m.product_id
  where coalesce(p.identity_root_id,p.id)=c.root_id and m.physical_at<=c.at
    and m.system_created_at<=c.at
  order by m.physical_at,m.book_order,m.id limit 501
),
sales_page as materialized (
  select i.id,h.id sale_id,i.product_id,h.status,h.row_version,h.sale_date,
         h.created_at,i.qty_pcs
  from erp.sales_items i join erp.sales_headers h on h.id=i.sale_id
  join erp.products p on p.id=i.product_id cross join clock c
  where coalesce(p.identity_root_id,p.id)=c.root_id
    and h.created_at<=c.at and h.sale_date<=c.at
  order by h.created_at,h.id,i.id limit 501
),
cost_page as materialized (
  select l.id lot_id,l.product_id,l.produced_at,h.id hpp_version_id,
         h.version_no,h.cost_state,h.total_cost,h.calculated_at,
         (h.id is null or h.cost_state='ESTIMATED'
          or erp.bd_lot_laundry_unknown_v1(l.id)
          or (l.po_id is not null and not exists(
            select 1 from erp.get_hpp_completeness(l.po_id) z where z.pending_reason_count=0))) pending
  from erp.fg_lots l join erp.products p on p.id=l.product_id
  left join erp.hpp_versions h on h.lot_id=l.id and h.is_current
    and h.calculated_at<=(select at from clock)
  cross join clock c
  where p_financial and coalesce(p.identity_root_id,p.id)=c.root_id and l.produced_at<=c.at
  order by l.produced_at,l.id,h.version_no limit 501
),
observed as (
  select jsonb_build_object(
    'physical',coalesce((select jsonb_agg(jsonb_build_object(
      'product_id',id,'root_id',root_id,'size_id',size_id,'model_id',model_id,
      'brand_id',brand_id,'effective_from',effective_from) order by effective_from,id)
      from physical),'[]'::jsonb),
    'commercial',coalesce((select jsonb_agg(jsonb_build_object(
      'sku_id',sku_id,'version_id',version_id,'revision',revision::text,'sku',sku)
      order by version_id) from memberships),'[]'::jsonb),
    'cutting_candidates',coalesce((select jsonb_agg(jsonb_build_object(
      'source_key','CUTTING_YIELD:'||yield_id::text,'yield_id',yield_id,
      'cutting_group_id',cutting_group_id,'po_id',po_id,'slot_id',slot_id,
      'size_id',size_id,'pattern_id',pattern_id,
      'pattern_revision',pattern_revision_snapshot,'group_revision',row_version::text,
      'cut_at',cut_at,'cut_qty_pcs',qty_pcs::text,'match','UNBOUND_CANDIDATE')
      order by cut_at,cutting_group_id,slot_id,yield_id) from cutting_page),'[]'::jsonb),
    'stock_movements',coalesce((select jsonb_agg(jsonb_build_object(
      'source_key','FG_MOVEMENT:'||id::text,'product_id',product_id,'lot_id',lot_id,
      'location_id',location_id,'quality_grade',quality_grade,
      'qty_signed_pcs',qty_signed::text,'physical_at',physical_at,
      'system_created_at',system_created_at,'reversal_of_id',reversal_of_id)
      order by physical_at,id) from stock_page),'[]'::jsonb),
    'sales_lines',coalesce((select jsonb_agg(jsonb_build_object(
      'source_key','SALE_LINE:'||id::text,'sale_id',sale_id,'product_id',product_id,
      'status',status,'header_revision',row_version::text,
      'sale_date',sale_date,'created_at',created_at,'qty_pcs',qty_pcs::text)
      order by created_at,sale_id,id) from sales_page),'[]'::jsonb),
    'lot_cost',coalesce((select jsonb_agg(jsonb_build_object(
      'source_key','LOT_COST:'||lot_id::text,'lot_id',lot_id,'product_id',product_id,
      'produced_at',produced_at,'hpp_version_id',hpp_version_id,
      'hpp_revision',version_no::text,'calculated_at',calculated_at,
      'cost_state',cost_state,'valuation',case when pending then
        jsonb_build_object('state','UNKNOWN','reason','PENDING_COST_OR_NO_HPP')
        else jsonb_build_object('state','KNOWN','value',total_cost::text,'unit','IDR') end)
      order by produced_at,lot_id,hpp_version_id) from cost_page),'[]'::jsonb)
  ) as sources,
  jsonb_build_object('physical',(select count(*) from physical),
    'commercial',(select count(*) from memberships),
    'cutting_candidates',(select count(*) from cutting_page),
    'stock_movements',(select count(*) from stock_page),
    'sales_lines',(select count(*) from sales_page),
    'lot_cost',(select count(*) from cost_page)) as counts
),
result as (
  select jsonb_build_object(
    'contract_version','cp7.source-probe.v1',
    'status',case when (counts->>'physical')::int=1
                  and (counts->>'commercial')::int<=1
                  and (counts->>'cutting_candidates')::int<=500
                  and (counts->>'stock_movements')::int<=500
                  and (counts->>'sales_lines')::int<=500
                  and (counts->>'lot_cost')::int<=500
                  and (select count(distinct lot_id) from cost_page)
                    =(counts->>'lot_cost')::int
      then 'COMPLETE' else 'INCOMPLETE' end,
    'scope',jsonb_build_object('root_id',(select root_id from clock),
      'exact_size_id',(select size_id from scope),
      'commercial_status',case when (counts->>'commercial')::int=0
        then 'LEGACY_UNMAPPED' else 'BOUND' end),
    'snapshot',jsonb_build_object('effective_as_of',(select at from clock),
      'known_as_of',(select at from clock),'generated_at',(select at from clock),
      'knowledge_mode','CURRENT','time_zone','Asia/Jakarta',
      'completeness_proven_only_for','SOURCE_PROBE_SIX_DOMAINS'),
    'counts',counts,'sources',sources) payload
  from observed
)
select payload||jsonb_build_object('snapshot_hash',
  encode(extensions.digest(convert_to((payload->'sources')::text,'UTF8'),'sha256'),'hex'))
from result

$cp7source$;
