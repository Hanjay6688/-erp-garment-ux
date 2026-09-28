"""Extend BD's exact covered-PCS accounting with a shared SKU tariff source."""
from cp6_bc_build import last_definition,substitute

REPLACED=['erp.bd_compute_pricing_v1(jsonb,jsonb)','erp.bd_attach_delivery_pricing_v1(uuid)',
 'erp.bd_post_priced_delivery_v1(jsonb,uuid)','erp.save_laundry_qc_action_v1(text,jsonb,uuid,bigint)']

def changed(bd):
    compute=last_definition(bd,'bd_compute_pricing_v1')
    compute=substitute(compute,[
      ('  v_status text;v_label text;v_kind text;','  v_status text;v_label text;v_kind text;bf_group uuid;bf_rate jsonb;'),
      ('select po.model_id into v_model','select po.model_id,g.id into v_model,bf_group'),
      ('      select * into v_scoped from erp.bd_scoped_rate_at_v1', '''      bf_rate:=null;
      if exists(select 1 from erp.bf_wave_skus_v1 where cutting_group_id=bf_group and size_id=v_sizeids[i]) then
        bf_rate:=erp.bf_laundry_rate_v1('PROCESS',v_process,v_vendor,bf_group,v_sizeids[i],v_at);
        v_rate:=(bf_rate->>'rate')::numeric;v_kind:='RATE';v_label:='Tarif bersama SKU';
      else
      select * into v_scoped from erp.bd_scoped_rate_at_v1'''),
      ('      v_amount:=round(v_qtys[i]*v_rate,2);','      end if;\n      v_amount:=round(v_qtys[i]*v_rate,2);'),
      ("'ref_id',v_scoped.rate_id,'version_id',v_scoped.rate_id,'label'", "'ref_id',case when bf_rate is not null then v_process else v_scoped.rate_id end,'version_id',case when bf_rate is not null then (bf_rate->>'version_id')::uuid else v_scoped.rate_id end,'bf_sku_version_id',bf_rate->'sku_version_id','label'"),
      ('erp.bd_component_charge_v1(v_vendor,v_x,v_at,v_sizeids,v_qtys,v_total_qty,\'EXTRA\',v_seen)',"erp.bf_component_charge_v1(v_vendor,v_x,v_at,v_sizeids,v_qtys,v_total_qty,'EXTRA',v_seen,bf_group)"),
      ('erp.bd_component_charge_v1(v_vendor,v_x,v_at,v_sizeids,v_qtys,v_total_qty,\'COMPONENT\',v_seen)',"erp.bf_component_charge_v1(v_vendor,v_x,v_at,v_sizeids,v_qtys,v_total_qty,'COMPONENT',v_seen,bf_group)")], 'BF laundry rates by wave SKU')
    begin=compute.index('    select * into v_scoped from erp.bd_package_rate_at_v1')
    end=compute.index("    if p_pricing ? 'extras'",begin)
    compute=compute[:begin]+'''    select array_agg(component_id order by component_id) into v_included from erp.bd_laundry_package_components_v1 where package_id=v_pkg.id;
    v_charges:=v_charges||erp.bf_complete_shares_v1(erp.bf_package_charges_v1(v_vendor,v_pkg.id,bf_group,v_at,v_sizeids,v_qtys,v_included,v_pkg.package_name),v_sizeids);
'''+compute[end:]
    attach=substitute(last_definition(bd,'bd_attach_delivery_pricing_v1'),[
      ('amount,included_components,price_reason)','amount,included_components,price_reason,bf_sku_version_id)'),
      ("v_ch->'included_components',v_ch->>'price_reason')", "v_ch->'included_components',v_ch->>'price_reason',(v_ch->>'bf_sku_version_id')::uuid)")], 'BF tariff snapshot provenance')
    post=substitute(last_definition(bd,'bd_post_priced_delivery_v1'),[
      ('  -- The prices read below', "  perform pg_advisory_xact_lock(hashtextextended('BF:COMMERCIAL_SKUS',0));\n  -- The prices read below")], 'BF tariff mutation serialization')
    facade=substitute(last_definition(bd,'save_laundry_qc_action_v1'),[
      ('elsif erp.bd_vendor_needs_pricing_v1(v_vendor_id,v_process_id) then',
       'elsif erp.bd_vendor_needs_pricing_v1(v_vendor_id,v_process_id) or exists(select 1 from erp.bf_wave_skus_v1 where cutting_group_id=v_group_id) then')], 'BF direct delivery no tariff bypass')
    return [compute,attach,post,facade]
