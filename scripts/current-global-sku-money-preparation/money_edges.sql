  -- Monetary identity is retained for zero values, reversals and old revisions.
  union select 'HPP_VERSION',h.id,'LOT',h.lot_id from erp.hpp_versions h
  union select 'SKU_GROUP',c.group_id,'LOT',c.root_lot_id from cp7_sku_conversion.cost_contributors_v3 c
  union select 'SKU_GROUP',c.group_id,'PO',c.po_id from cp7_sku_conversion.cost_contributors_v3 c
  union select 'SKU_GROUP',c.group_id,'HPP_VERSION',c.hpp_version_id from cp7_sku_conversion.cost_contributors_v3 c
  union select 'SKU_SALE_ALLOCATION',c.sale_stock_allocation_id,'LOT',c.root_lot_id from cp7_sku_conversion.sale_cost_components_v3 c
  union select 'SKU_SALE_ALLOCATION',c.sale_stock_allocation_id,'PO',c.po_id from cp7_sku_conversion.sale_cost_components_v3 c
  union select 'SKU_RETURN_ITEM',c.sales_return_item_id,'LOT',c.root_lot_id from cp7_sku_conversion.return_cost_components_v3 c
  union select 'SKU_RETURN_ITEM',c.sales_return_item_id,'PO',c.po_id from cp7_sku_conversion.return_cost_components_v3 c
  union select 'SKU_COST_EVENT',e.id,'PRODUCT',e.product_id from cp7_sku_conversion.cost_events_v3 e
  union select 'SKU_COST_EVENT',e.id,'LOT',e.root_lot_id from cp7_sku_conversion.cost_events_v3 e
  union select 'SKU_COST_EVENT',e.id,case e.source_type when 'SKU_CONVERSION'then'SKU_GROUP'when'SALE'then'SALE'when'SALES_RETURN'then'SALES_RETURN'else'SKU_COST_SOURCE_'||e.source_type end,e.source_id from cp7_sku_conversion.cost_events_v3 e
  union select 'SKU_COST_EVENT',e.id,'SKU_COST_EVENT',e.supersedes_event_id from cp7_sku_conversion.cost_events_v3 e
  union select 'SKU_GROUP',r.group_id,'JOURNAL',r.journal_id from cp7_sku_conversion.group_inverse_rebalances_v3 r
  union select 'SKU_SOURCE_REBALANCE',r.id,'BC_DOCUMENT',r.document_id from cp7_sku_conversion.cost_source_rebalances_v3 r
  union select 'SKU_SOURCE_REBALANCE',r.id,'JOURNAL',r.journal_id from cp7_sku_conversion.cost_source_rebalances_v3 r
  union select 'SKU_COST_MONEY_EVENT',e.id,'LOT',e.root_lot_id from cp7_sku_conversion.cost_money_events_v3 e
  union select 'SKU_COST_MONEY_EVENT',e.id,'PRODUCT',e.product_id from cp7_sku_conversion.cost_money_events_v3 e
  union select 'SKU_COST_MONEY_EVENT',e.id,case when e.kind='SOURCE_PRICE'then'BC_DOCUMENT'else'SKU_GROUP'end,e.source_id from cp7_sku_conversion.cost_money_events_v3 e
  union select 'SKU_BASE_MONEY_EVENT',e.id,'LOT',e.root_lot_id from cp7_sku_conversion.base_money_events_v4 e
  union select 'SKU_BASE_MONEY_EVENT',e.id,'PRODUCT',e.product_id from cp7_sku_conversion.base_money_events_v4 e
  union select 'SKU_BASE_MONEY_EVENT',e.id,case when e.kind in('ORIGIN','SOURCE_PRICE')then'HPP_VERSION'else'SKU_GROUP'end,e.source_id from cp7_sku_conversion.base_money_events_v4 e
  union select 'SKU_GROUP',g.group_id,'CONVERSION',g.group_id from cp7_sku_conversion.legacy_groups_v4 g
  union select 'SKU_GROUP',g.group_id,'LOT',g.source_lot_id from cp7_sku_conversion.legacy_groups_v4 g
  union select 'SKU_GROUP',g.group_id,'REWORK',g.rework_id from cp7_sku_conversion.legacy_groups_v4 g
