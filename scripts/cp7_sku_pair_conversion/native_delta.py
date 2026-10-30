"""Five public/preview changes and one Native reversal guard, derived exactly once.

Native conversion costing, source selection for legacy callers, accessories,
rework/redye and existing posting functions remain untouched.
"""
SCHEMA='cp7_sku_conversion'
SIGNATURES=(
 'public.erp_get_sku_workspace_v1(jsonb)',
 'public.erp_save_sku_action_v1(text,jsonb,uuid)',
 'public.erp_get_product_conversion_workspace_v1(jsonb)',
 'public.erp_save_product_conversion_action_v1(text,jsonb,uuid)',
 'erp.be_conversion_preview_v1(jsonb)',
 'erp.reverse_product_conversion(uuid,text)',
)

def once(text,before,after,label):
    if text.count(before)!=1:raise ValueError('SKU_CONVERSION_PREDECESSOR_CHANGED:'+label)
    return text.replace(before,after,1)

def patched(originals):
    if set(originals)!=set(SIGNATURES):raise ValueError('SKU_CONVERSION_EXACT_SIX_REQUIRED')
    result={}
    redirects=(('erp.get_sku_workspace_v1(p_filters)','cp7_sku_conversion.sku_workspace_v1(p_filters)'),
      ('erp.save_sku_action_v1(p_action,p_payload,p_client_request_id)','cp7_sku_conversion.sku_action_v1(p_action,p_payload,p_client_request_id)'),
      ('erp.get_product_conversion_workspace_v1(p_filters)','cp7_sku_conversion.workspace_v1(p_filters)'),
      ('erp.save_product_conversion_action_v1(p_action,p_payload,p_client_request_id)','cp7_sku_conversion.action_v1(p_action,p_payload,p_client_request_id)'))
    for sig,(before,after)in zip(SIGNATURES,redirects):
        result[sig]=once(originals[sig],before,after,sig)
    sig=SIGNATURES[4]
    old='if t.model_id is distinct from s.model_id or t.size_id is distinct from s.size_id then'
    new="if not cp7_sku_conversion.manual_allocation_v1(l.id,t.id,(p_payload->>'location_id')::uuid,(p_payload->>'qty_pcs')::int,(p_payload->>'physical_at')::timestamptz) and (t.model_id is distinct from s.model_id or t.size_id is distinct from s.size_id) then"
    result[sig]=once(originals[sig],old,new,'narrow manual dimension guard')
    sig=SIGNATURES[5]
    result[sig]=once(originals[sig],'  perform erp.require_owner_admin();',
      '  perform erp.require_owner_admin();\n  perform cp7_sku_conversion.assert_group_reverse_v1(p_conversion_id);','atomic group inverse')
    return result
