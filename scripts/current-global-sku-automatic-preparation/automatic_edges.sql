  -- Typed Native identities only. Backend/transaction and shared location are not graph hubs.
  union select 'CONVERSION',a.conversion_id,'SKU_GROUP',a.conversion_id from cp7_sku_conversion.automatic_context_v5 a
  union select 'CONVERSION',a.conversion_id,'REWORK',a.rework_id from cp7_sku_conversion.automatic_context_v5 a
  union select 'CONVERSION',a.conversion_id,'LOT',a.source_lot_id from cp7_sku_conversion.automatic_context_v5 a
  union select 'CONVERSION',a.conversion_id,'PO',a.source_po_id from cp7_sku_conversion.automatic_context_v5 a
  union select 'CONVERSION',a.conversion_id,'PRODUCT',a.source_product_id from cp7_sku_conversion.automatic_context_v5 a
  union select 'CONVERSION',a.conversion_id,'PRODUCT',a.target_product_id from cp7_sku_conversion.automatic_context_v5 a
  union select 'CONVERSION',a.conversion_id,'SKU_GROUP',a.conversion_id from cp7_sku_conversion.automatic_admissions_v5 a
  union select 'CONVERSION',a.conversion_id,'REWORK',a.rework_id from cp7_sku_conversion.automatic_admissions_v5 a
