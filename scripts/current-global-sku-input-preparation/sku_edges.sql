  -- Economic identities include immutable reversals and historical rows.
  union select 'SKU_GROUP',q.group_id,'PRODUCT',q.source_product_id from cp7_sku_conversion.valuation_quotes_v2 q
  union select 'SKU_GROUP',q.group_id,'PRODUCT',q.target_product_id from cp7_sku_conversion.valuation_quotes_v2 q
  union select 'SKU_GROUP',c.group_id,'LOT',c.root_lot_id from cp7_sku_conversion.valuation_contributors_v2 c
  union select 'SKU_GROUP',c.group_id,'PO',c.po_id from cp7_sku_conversion.valuation_contributors_v2 c
  union select 'SKU_GROUP',p.group_id,'JOURNAL',p.correction_journal_id from cp7_sku_conversion.valuation_postings_v2 p
  union select 'SKU_GROUP',a.group_id,'PRODUCT',a.product_id from cp7_sku_conversion.valuation_attributions_v2 a
  union select 'SKU_GROUP',a.group_id,'PO',a.po_id from cp7_sku_conversion.valuation_attributions_v2 a
  union select 'SKU_SALE_ALLOCATION',v.sale_stock_allocation_id,'SALE',v.sale_id from cp7_sku_conversion.sale_allocation_values_v2 v
  union select 'SKU_SALE_ALLOCATION',v.sale_stock_allocation_id,'LOT',v.lot_id from cp7_sku_conversion.sale_allocation_values_v2 v
  union select 'SKU_SALE_ALLOCATION',v.sale_stock_allocation_id,'PRODUCT',v.product_id from cp7_sku_conversion.sale_allocation_values_v2 v
  union select 'SKU_SALE_ALLOCATION',c.sale_stock_allocation_id,'LOT',c.root_lot_id from cp7_sku_conversion.sale_allocation_components_v2 c
  union select 'SKU_SALE_ALLOCATION',c.sale_stock_allocation_id,'PO',c.po_id from cp7_sku_conversion.sale_allocation_components_v2 c
  union select 'SKU_SALE_ALLOCATION',a.sale_stock_allocation_id,'PRODUCT',a.product_id from cp7_sku_conversion.sale_allocation_attributions_v2 a
  union select 'SKU_SALE_ALLOCATION',a.sale_stock_allocation_id,'PO',a.po_id from cp7_sku_conversion.sale_allocation_attributions_v2 a
  union select 'SKU_RETURN_ITEM',v.sales_return_item_id,'SALES_RETURN',v.return_id from cp7_sku_conversion.sales_return_values_v2 v
  union select 'SKU_RETURN_ITEM',v.sales_return_item_id,'SKU_SALE_ALLOCATION',v.sale_stock_allocation_id from cp7_sku_conversion.sales_return_values_v2 v
  union select 'SKU_RETURN_ITEM',v.sales_return_item_id,'LOT',v.lot_id from cp7_sku_conversion.sales_return_values_v2 v
  union select 'SKU_RETURN_ITEM',v.sales_return_item_id,'PRODUCT',v.product_id from cp7_sku_conversion.sales_return_values_v2 v
  union select 'SKU_RETURN_ITEM',c.sales_return_item_id,'LOT',c.root_lot_id from cp7_sku_conversion.sales_return_components_v2 c
  union select 'SKU_RETURN_ITEM',c.sales_return_item_id,'PO',c.po_id from cp7_sku_conversion.sales_return_components_v2 c
  union select 'SKU_RETURN_ITEM',a.sales_return_item_id,'PRODUCT',a.product_id from cp7_sku_conversion.sales_return_attributions_v2 a
  union select 'SKU_RETURN_ITEM',a.sales_return_item_id,'PO',a.po_id from cp7_sku_conversion.sales_return_attributions_v2 a
  union select 'SKU_VALUE_EVENT',e.id,'SKU_GROUP',e.group_id from cp7_sku_conversion.valuation_events_v2 e
  union select 'SKU_VALUE_EVENT',e.id,'PRODUCT',e.product_id from cp7_sku_conversion.valuation_events_v2 e
  union select 'SKU_VALUE_EVENT',e.id,case e.source_type when 'SKU_CONVERSION'then'SKU_GROUP'when'SALE'then'SALE'when'SALES_RETURN'then'SALES_RETURN'else'SKU_VALUE_SOURCE_'||e.source_type end,e.source_id from cp7_sku_conversion.valuation_events_v2 e
  union select 'SKU_VALUE_EVENT',e.id,'SKU_VALUE_EVENT',e.supersedes_event_id from cp7_sku_conversion.valuation_events_v2 e
  union select 'SKU_COMPONENT_EVENT',e.id,'SKU_GROUP',e.group_id from cp7_sku_conversion.component_events_v2 e
  union select 'SKU_COMPONENT_EVENT',e.id,'PRODUCT',e.product_id from cp7_sku_conversion.component_events_v2 e
  union select 'SKU_COMPONENT_EVENT',e.id,'LOT',e.root_lot_id from cp7_sku_conversion.component_events_v2 e
  union select 'SKU_COMPONENT_EVENT',e.id,case e.source_type when 'SKU_CONVERSION'then'SKU_GROUP'when'SALE'then'SALE'when'SALES_RETURN'then'SALES_RETURN'else'SKU_COMPONENT_SOURCE_'||e.source_type end,e.source_id from cp7_sku_conversion.component_events_v2 e
  union select 'SKU_COMPONENT_EVENT',e.id,'SKU_COMPONENT_EVENT',e.supersedes_event_id from cp7_sku_conversion.component_events_v2 e
