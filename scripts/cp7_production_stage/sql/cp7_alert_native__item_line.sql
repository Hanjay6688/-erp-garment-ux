create or replace function cp7_alert_native.item_line(p jsonb,p_detail text)returns text
language sql stable security definer set search_path=''set TimeZone='UTC'as $$
 -- Obligation facts have priority over a long document/party label. Preserve
 -- the complete value/UNKNOWN and review/due text; only the label may shorten.
 select case when p->'detail'?'domain'then(
  select case when length(label||suffix)<=256 then label||suffix
   else left(label,greatest(0,255-length(suffix)))||'…'||suffix end
  from(select coalesce(p->'detail'->>'label','?')label,': '
   ||case when p->'detail'->>'remaining_state'='KNOWN'then cp7_alert_native.rp(p->'detail'->>'remaining')else'nilai belum diketahui'end
   ||case when p->'detail'->>'state'='DATA_REVIEW'then', perlu diperiksa'
     else', jatuh tempo '||cp7_alert_native.tgl(p->'detail'->>'due_date')end suffix)x)
 when p->>'kind'='FABRIC_BELOW_MINIMUM'and p->'detail'->>'basis'='MANUAL'and p->'detail'?'reorder_point_qty'then(
  -- Selected legacy compares physical stock only. Keep its rule and quantities
  -- intact even when the material label fills the message budget.
  select case when length(label||suffix)<=256 then label||suffix
   else left(label,greatest(0,255-length(suffix)))||'…'||suffix end
  from(select coalesce(p->'detail'->>'name','?')label,': sisa '
   ||cp7_alert_native.num(p->'detail'->>'free_qty')||' '||coalesce(p->'detail'->>'unit_code','')
   ||', minimum lama yang dipilih '||cp7_alert_native.num(p->'detail'->>'reorder_point_qty')||' '||coalesce(p->'detail'->>'unit_code','')suffix)x)
 else left(case p->>'kind'
  when'FABRIC_BELOW_MINIMUM'then case when p->'detail'?'reorder_point_qty'then(p->'detail'->>'name')||': sisa '
    ||cp7_alert_native.num(p->'detail'->>'free_qty')||' '||coalesce(p->'detail'->>'unit_code','')
    ||', dipesan '||cp7_alert_native.num(p->'detail'->>'on_order_qty')||' '||coalesce(p->'detail'->>'unit_code','')
    ||', minimum rumus '||cp7_alert_native.num(p->'detail'->>'reorder_point_qty')||' '||coalesce(p->'detail'->>'unit_code','')
   else(p->'detail'->>'material_name')||': sisa '||cp7_alert_native.num(p->'detail'->>'qty')||' '||(p->'detail'->>'unit_code')
   ||', minimum '||cp7_alert_native.num(p->'detail'->>'minimum_qty')||' '||(p->'detail'->>'unit_code')end
  when'FG_AT_REORDER_POINT'then coalesce(p->'detail'->>'product_name','?')||coalesce(' '||(p->'detail'->>'size_code'),'')
   ||': sisa '||cp7_alert_native.num(p->'detail'->>'free_pcs')||' pcs, sedang diproduksi '
   ||case when p->'detail'->>'wip_status'='COMPLETE'then cp7_alert_native.num(p->'detail'->>'wip_pcs')||' pcs'else'belum diketahui'end
   ||', titik pesan ulang '||cp7_alert_native.num(p->'detail'->>'reorder_point_pcs')||' pcs'
  when'ACCESSORY_AT_REORDER_POINT'then(p->'detail'->>'name')||': sisa '||cp7_alert_native.num(p->'detail'->>'free_qty')||' '||coalesce(p->'detail'->>'unit_code','')
   ||', minimum '||cp7_alert_native.num(p->'detail'->>'reorder_point_qty')||' '||coalesce(p->'detail'->>'unit_code','')
  when'MANUAL_REMINDER'then(p->>'title')||case when p_detail='DETAILED'and coalesce(p->'detail'->>'note','')<>''then' ('||left(p->'detail'->>'note',60)||')'else''end
  when'AR_DUE'then coalesce((p->'party_names'->>0)||' ','')||coalesce(p->'detail'->>'number','?')||': '||cp7_alert_native.rp(p->'detail'->>'open_balance')
   ||', jatuh tempo '||cp7_alert_native.tgl(p->'detail'->>'due_date')
  when'AP_DUE'then coalesce((p->'party_names'->>0)||' ','')||coalesce(p->'detail'->>'purchase_number','?')||': '||cp7_alert_native.rp(p->'detail'->>'remaining')
   ||', jatuh tempo '||cp7_alert_native.tgl(p->'detail'->>'due_date')
  when'PRODUCTION_GAP'then coalesce(p->'detail'->>'label','?')||': kurang '||cp7_alert_native.num(p->'detail'->>'need_now_pcs')||' pcs'
  when'ACCESSORY_NEED'then left(coalesce(p->'detail'->>'label','?'),20)||': perlu diperiksa; jumlah tambahan belum diketahui'
   ||case when p->'detail'->>'gross_qty'is not null and length(trim_scale((p->'detail'->>'gross_qty')::numeric)::text||' '||coalesce(p->'detail'->>'unit',''))<=25
    then'; BOM '||case when p->'detail'->>'gross_state'='ASSUMED'then'(perkiraan) 'else''end
    ||trim_scale((p->'detail'->>'gross_qty')::numeric)::text||' '||coalesce(p->'detail'->>'unit','')else''end
  when'FABRIC_NEED'then coalesce(p->'detail'->>'material_name','?')||' untuk '||coalesce(p->'detail'->>'label','?')||': '
   ||cp7_alert_native.num(p->'detail'->>'value')||' '||coalesce(p->'detail'->>'unit','')
  else p->>'title'end,120)end$$;
