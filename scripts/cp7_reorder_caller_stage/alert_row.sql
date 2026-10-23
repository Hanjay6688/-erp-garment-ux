-- No per-tick clocks in the alert hash: identical facts do not requeue a WA
-- every minute. WIP is explicitly projected good, never physical free stock.
create or replace function cp7_stock_formula.alert_row(e jsonb,p_level numeric)returns jsonb
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 select jsonb_build_object('subject_key',e->>'target_key','title','Stok barang jadi menipis: '||(e->>'product_name')||coalesce(' '||(e->>'size_code'),''),
  'detail',jsonb_build_object('contract_version','cp7.fg-reorder-detail.v2',
   'root_id',e->'root_id','size_id',e->'size_id','sku',e->'sku','product_name',e->'product_name','size_code',e->'size_code',
   'free_pcs',e->'free_pcs','wip_pcs',e->'wip_pcs','wip_status',e->'wip_status',
   'position_pcs',e->'projection'->'base_position_pcs','reorder_point_pcs',e->'point','basis',e->'basis',
   'daily_mean',e->'daily_mean','lead_days',e->'lead_days','lead_basis',e->'lead_basis',
   'buffer_mode',case when e->>'basis'='FORMULA'then e->'buffer_mode'else'null'::jsonb end,
   'safety_pcs',case when e->>'basis'='FORMULA'then e->'safety_pcs'else'null'::jsonb end,
   'service_level',case when e->>'basis'='FORMULA'and e->>'buffer_mode'='STATISTICAL'then e->'service_level'else'null'::jsonb end,
   'projection',jsonb_build_object('basis','GLOBAL_PROJECTED_GOOD_ON_TIME','analysis_at',e->'projection'->'analysis_at',
    'candidate_pcs',e->'projection'->'candidate_pcs','conditional_position_pcs',e->'projection'->'conditional_position_pcs',
    'threshold_source',e->'projection'->'threshold_source','candidate_mutes_alert',false)),
  'party_names','[]'::jsonb)
$$;
