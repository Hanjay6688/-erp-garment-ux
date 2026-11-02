"""Exact private conversion changes for the moving-average successor.

Physical FIFO allocations stay byte-for-byte in the parent function. Only the
pool quote/revision, displayed accounting amount, and append-only prepare /
finalize / inverse hooks are added.
"""

SIGNATURES=(
 'cp7_sku_conversion.preview_v1(jsonb)',
 'cp7_sku_conversion.action_v1(text,jsonb,uuid)',
)

def once(text,before,after,label):
    if text.count(before)!=1:
        raise ValueError('SKU_MOVAVG_PRIVATE_PREDECESSOR_CHANGED:'+label)
    return text.replace(before,after,1)

def patched(originals):
    if set(originals)!=set(SIGNATURES):
        raise ValueError('SKU_MOVAVG_EXACT_PRIVATE_TWO_REQUIRED')
    result={}

    sig=SIGNATURES[0]
    text=originals[sig]
    text=once(text,
      "source_stock jsonb;target_stock jsonb;revision text;value numeric:=0;money boolean;",
      "source_stock jsonb;target_stock jsonb;source_pool jsonb;target_pool jsonb;revision text;value numeric:=0;money boolean;",
      'preview declarations')
    text=once(text,
      "source_stock:=cp7_sku_conversion.stock_v1(src.id,loc.id);target_stock:=cp7_sku_conversion.stock_v1(dst.id,loc.id);\n revision:=cp7_sku_conversion.revision_v1(src.id,dst.id,loc.id);",
      "source_stock:=cp7_sku_conversion.stock_v1(src.id,loc.id);target_stock:=cp7_sku_conversion.stock_v1(dst.id,loc.id);\n source_pool:=cp7_sku_conversion.pool_quote_v2(src.id,loc.id,'GRADE_A');target_pool:=cp7_sku_conversion.pool_quote_v2(dst.id,loc.id,'GRADE_A');\n if (source_pool->>'qty')::numeric<qty then raise exception 'CP7_SKU_INSUFFICIENT_VALUE_POOL: stok fisik bernilai tidak cukup';end if;\n revision:=md5(jsonb_build_object('physical',cp7_sku_conversion.revision_v1(src.id,dst.id,loc.id),'source_value',source_pool->>'revision','target_value',target_pool->>'revision')::text);",
      'pool quote and combined revision')
    text=once(text,
      "'cost',case when money then jsonb_build_object('source_value',value::text)else '{}'::jsonb end);",
      "'source_value_revision',source_pool->>'revision','target_value_revision',target_pool->>'revision',\n 'source_value_pool',case when money then source_pool else jsonb_build_object('state','HIDDEN','reserved_included',true,'basis','SKU_LOCATION_GRADE_MOVING_AVERAGE_V2')end,\n 'target_value_pool',case when money then target_pool else jsonb_build_object('state','HIDDEN','reserved_included',true,'basis','SKU_LOCATION_GRADE_MOVING_AVERAGE_V2')end,\n 'cost',case when money then jsonb_build_object('source_value',round(qty*(source_pool->>'average')::numeric,2)::text,'native_physical_value',round(value,2)::text,'basis','SKU_LOCATION_GRADE_MOVING_AVERAGE_V2')else '{}'::jsonb end);",
      'preview value contract')
    result[sig]=text

    sig=SIGNATURES[1]
    text=originals[sig]
    text=once(text,
      "insert into cp7_sku_conversion.groups_v1(request_id,actor,payload)values(p_request,erp.current_app_user_id(),p_payload);\n  insert into cp7_sku_conversion.execution_v1",
      "insert into cp7_sku_conversion.groups_v1(request_id,actor,payload)values(p_request,erp.current_app_user_id(),p_payload);\n  perform cp7_sku_conversion.prepare_valuation_v2(p_request,v);\n  insert into cp7_sku_conversion.execution_v1",
      'prepare before Native children')
    text=once(text,
      "end loop;\n  v:=v||jsonb_build_object('conversion_id',p_request,",
      "end loop;\n  perform cp7_sku_conversion.finalize_valuation_v2(p_request);\n  v:=v||jsonb_build_object('conversion_id',p_request,",
      'finalize after Native children')
    text=once(text,
      "ids:=ids||jsonb_build_array(r.conversion_id);\n  end loop;\n  v:=jsonb_build_object('conversion_id',p_payload->'conversion_id'",
      "ids:=ids||jsonb_build_array(r.conversion_id);\n  end loop;\n  perform cp7_sku_conversion.reverse_valuation_v2(v_group_id);\n  v:=jsonb_build_object('conversion_id',p_payload->'conversion_id'",
      'append exact group value inverse')
    result[sig]=text
    return result
