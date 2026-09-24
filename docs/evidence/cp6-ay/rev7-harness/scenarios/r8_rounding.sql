\set QUIET 1
\pset footer off
-- Rounding: dh = +1.745/pc, 10 pcs QC d-3, 1 pc sold d-2 (nothing enters or leaves WIP on d-2)
begin;
\ir common_lot.sql
insert into erp.fg_stock_movements(lot_id,movement_type,qty_signed,physical_at) values
 ('00000000-0000-0000-0000-0000000000b1','SALE',-1,((current_date-2)+time '10:00') at time zone 'Asia/Jakarta'),('00000000-0000-0000-0000-0000000000b1','SALE',-1,((current_date-1)+time '10:00') at time zone 'Asia/Jakarta');
insert into erp.sales_headers values('00000000-0000-0000-0000-0000000000d1','POSTED',null);
insert into erp.sales_items values('00000000-0000-0000-0000-0000000000d2','00000000-0000-0000-0000-0000000000d1');
insert into erp.sale_stock_allocations(sale_item_id,lot_id,qty_pcs) values('00000000-0000-0000-0000-0000000000d2','00000000-0000-0000-0000-0000000000b1',2);
insert into erp.po_hpp_gl_state values('00000000-0000-0000-0000-0000000000a0',10,100,80,20,0,now()-interval '1 hour');
select erp.sync_po_hpp_to_gl('00000000-0000-0000-0000-0000000000a0',current_date-4);
select * from public.show();
rollback;
