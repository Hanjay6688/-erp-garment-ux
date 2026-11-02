"""Exact current FG reader bindings to the effective pool valuation."""

SIGNATURES=('cp7_fg.workspace(jsonb)','cp7_fg.corrected_ledger(jsonb)')

def once(text,before,after,label):
    if text.count(before)!=1:raise ValueError('SKU_MOVAVG_READER_PREDECESSOR_CHANGED:'+label)
    return text.replace(before,after,1)

def patched(originals):
    if set(originals)!=set(SIGNATURES):raise ValueError('SKU_MOVAVG_EXACT_READER_TWO_REQUIRED')
    result={}
    sig=SIGNATURES[0]
    result[sig]=once(originals[sig],
      "cp7_fg.lot_value(x.lot_id,x.physical_qty)",
      "cp7_sku_conversion.position_value_v2(x.product_id,x.location_id,x.quality_grade,x.physical_qty)",
      'FG workspace position value')
    sig=SIGNATURES[1]
    result[sig]=once(originals[sig],
      "if a->'can_value'='true'::jsonb then cost:=cp7_fg.lot_value(lid,1);end if;",
      "if a->'can_value'='true'::jsonb then cost:=cp7_sku_conversion.position_value_v2(pid,location,grade,1);end if;",
      'FG card current pool unit')
    return result
