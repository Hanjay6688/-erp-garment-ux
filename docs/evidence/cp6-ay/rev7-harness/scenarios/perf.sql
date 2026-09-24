\set QUIET 1
\pset footer off
begin;
insert into erp.settings values('E',(current_date-800)::text);
insert into erp.fg_lots select ('00000000-0000-0000-0001-'||lpad(i::text,12,'0'))::uuid,'00000000-0000-0000-0000-0000000000a0','PRODUCTION',5000,now()-interval '799 day',null,null,null from generate_series(1,20) i;
insert into erp.hpp_versions(lot_id,version_no,qty_basis_pcs,total_cost,is_current,calculated_at)
 select id,1,5000,50000,false,now()-interval '2 hour' from erp.fg_lots union all select id,2,5000,41250,true,now() from erp.fg_lots;
insert into erp.fg_stock_movements(lot_id,movement_type,qty_signed,physical_at) select id,'QC_GOOD',5000,now()-interval '799 day' from erp.fg_lots;
insert into erp.fg_stock_movements(lot_id,movement_type,qty_signed,physical_at)
 select l.id,'SALE',-1,now()-((s % :ndays)||' day')::interval from erp.fg_lots l, generate_series(1,:nper) s;
insert into erp.po_hpp_gl_state values('00000000-0000-0000-0000-0000000000a0',100000,1000000,1000000-20*:nper*10,20*:nper*10,0,now()-interval '1 hour');
insert into erp.sales_headers values('00000000-0000-0000-0000-0000000000d1','POSTED',null);
insert into erp.sales_items values('00000000-0000-0000-0000-0000000000d2','00000000-0000-0000-0000-0000000000d1');
insert into erp.sale_stock_allocations(sale_item_id,lot_id,qty_pcs) select '00000000-0000-0000-0000-0000000000d2',id,:nper from erp.fg_lots;
analyze;
\timing on
select erp.sync_po_hpp_to_gl('00000000-0000-0000-0000-0000000000a0',current_date-800);
\timing off
select count(*) journals from erp.journal_entries;
rollback;
