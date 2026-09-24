\set QUIET 1
\pset footer off
-- Perf: :nlots lots over :ngrp groups (one cutting batch with :nother groups of other POs), each lot QC'd on its own day,
-- :nsale sales per lot spread over 700 days, 10 material facts per group with state (price change), contractor items.
begin;
insert into erp.settings values('E',(current_date-800)::text);
insert into erp.cutting_groups select ('00000000-0000-0000-0002-'||lpad(g::text,12,'0'))::uuid,
  case when g<=:ngrp then '00000000-0000-0000-0000-0000000000a0'::uuid else gen_random_uuid() end,
  case when g%2=0 then '00000000-0000-0000-0000-0000000000bb'::uuid end, now()-((800-g)||' day')::interval
 from generate_series(1,:ngrp+:nother) g;
insert into erp.v_cutting_group_totals select id,100 from erp.cutting_groups;
insert into erp.v_cutting_batch_totals values('00000000-0000-0000-0000-0000000000bb',95*((:ngrp+:nother)/2));
insert into erp.material_stock_movements(id,source_id,source_type,qty_signed,unit_cost_snapshot,physical_at,system_created_at)
 select gen_random_uuid(),g.id,case when k=10 then 'CUTTING_GROUP_RETURN' else 'CUTTING_GROUP' end,case when k=10 then 1 else -10 end,8.25,
   g.cut_at+(k||' day')::interval,now()-interval '3 hour'
 from erp.cutting_groups g,generate_series(1,10) k;
insert into erp.po_hpp_gl_material_state_v1 select '00000000-0000-0000-0000-0000000000a0','M:'||id::text,-qty_signed*10,now()-interval '1 hour' from erp.material_stock_movements;
insert into erp.po_hpp_gl_material_state_v1 values('00000000-0000-0000-0000-0000000000a0','SYNC',0,now()-interval '1 hour');
insert into erp.materials values('00000000-0000-0000-0000-0000000000ae','FABRIC');
insert into erp.contractor_material_issues select ('00000000-0000-0000-0003-'||lpad(i::text,12,'0'))::uuid,'00000000-0000-0000-0000-0000000000a0','POSTED',now()-((700-i)||' day')::interval from generate_series(1,200) i;
insert into erp.contractor_material_issue_items(id,issue_id,material_id,qty,unit_cost_snapshot) select gen_random_uuid(),id,'00000000-0000-0000-0000-0000000000ae',5,1.6 from erp.contractor_material_issues;
insert into erp.material_stock_movements(source_id,source_type,qty_signed,unit_cost_snapshot,physical_at,system_created_at)
 select ci.id,'CONTRACTOR_MATERIAL_ISSUE_ITEM',-5,1.6,cm.physical_at,now()-interval '3 hour' from erp.contractor_material_issue_items ci join erp.contractor_material_issues cm on cm.id=ci.issue_id;
insert into erp.po_hpp_gl_material_state_v1 select '00000000-0000-0000-0000-0000000000a0','C:'||id::text,10,now()-interval '1 hour' from erp.contractor_material_issue_items;
insert into erp.fg_lots select ('00000000-0000-0000-0001-'||lpad(i::text,12,'0'))::uuid,'00000000-0000-0000-0000-0000000000a0','PRODUCTION',100,
  now()-((790-(i%700))||' day')::interval,('00000000-0000-0000-0002-'||lpad((1+i%:ngrp)::text,12,'0'))::uuid,null,null from generate_series(1,:nlots) i;
insert into erp.hpp_versions(lot_id,version_no,qty_basis_pcs,total_cost,is_current,calculated_at)
 select id,1,100,1000,false,now()-interval '2 hour' from erp.fg_lots union all select id,2,100,850,true,now() from erp.fg_lots;
insert into erp.po_hpp_gl_lot_state_v1 select id,po_id,10,now()-interval '1 hour' from erp.fg_lots;
insert into erp.fg_stock_movements(lot_id,movement_type,qty_signed,physical_at) select id,'QC_GOOD',100,produced_at from erp.fg_lots;
insert into erp.fg_stock_movements(lot_id,movement_type,qty_signed,physical_at)
 select l.id,'SALE',-1,l.produced_at+((s*7 % 60)||' day')::interval from erp.fg_lots l, generate_series(1,:nsale) s;
insert into erp.po_hpp_gl_state values('00000000-0000-0000-0000-0000000000a0',100*:nlots,1000*:nlots,(100-:nsale)*10*:nlots,:nsale*10*:nlots,0,now()-interval '1 hour');
insert into erp.sales_headers values('00000000-0000-0000-0000-0000000000d1','POSTED',null);
insert into erp.sales_items values('00000000-0000-0000-0000-0000000000d2','00000000-0000-0000-0000-0000000000d1');
insert into erp.sale_stock_allocations(sale_item_id,lot_id,qty_pcs) select '00000000-0000-0000-0000-0000000000d2',id,:nsale from erp.fg_lots;
create index on erp.fg_stock_movements(lot_id); create index on erp.material_stock_movements(source_id); create index on erp.hpp_versions(lot_id);
analyze;
select count(*) lots,(select count(*) from erp.fg_stock_movements) fgmov,(select count(*) from erp.material_stock_movements) matmov from erp.fg_lots;
load 'auto_explain'; set auto_explain.log_min_duration=500; set auto_explain.log_nested_statements=on; set auto_explain.log_analyze=on; set auto_explain.log_level=notice; set auto_explain.log_timing=on;
\timing on
select erp.sync_po_hpp_to_gl('00000000-0000-0000-0000-0000000000a0',current_date-800);
\timing off
select count(*) journals,min(transaction_date),max(transaction_date) from erp.journal_entries;
rollback;
