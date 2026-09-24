begin;
insert into erp.settings values('E',(current_date-3)::text); update erp.accounting_period_control set closed_through=current_date-3;
-- PO p, group g, lot L (10 pcs on d+1), old hpp 10, new 8.25
insert into erp.cutting_groups values('00000000-0000-0000-0000-00000000000a','00000000-0000-0000-0000-0000000000a0',null,(current_date-2)+time '08:00');
insert into erp.fg_lots values('00000000-0000-0000-0000-0000000000b1','00000000-0000-0000-0000-0000000000a0','PRODUCTION',10,((current_date-2)+time '13:00') at time zone 'Asia/Jakarta','00000000-0000-0000-0000-00000000000a',null,null);
insert into erp.hpp_versions(lot_id,version_no,qty_basis_pcs,total_cost,is_current,calculated_at) values
 ('00000000-0000-0000-0000-0000000000b1',1,10,100,false,now()-interval '2 hour'),('00000000-0000-0000-0000-0000000000b1',2,10,82.5,true,now());
insert into erp.fg_stock_movements(id,lot_id,movement_type,qty_signed,physical_at,reversal_of_id) values
 ('00000000-0000-0000-0000-0000000000c1','00000000-0000-0000-0000-0000000000b1','QC_GOOD',10,((current_date-2)+time '13:00') at time zone 'Asia/Jakarta',null),
 ('00000000-0000-0000-0000-0000000000c2','00000000-0000-0000-0000-0000000000b1','SALE',-10,((current_date-1)+time '10:00') at time zone 'Asia/Jakarta',null),
 ('00000000-0000-0000-0000-0000000000c3','00000000-0000-0000-0000-0000000000b1','REVERSAL',10,now(),'00000000-0000-0000-0000-0000000000c2');
insert into erp.sales_headers values('00000000-0000-0000-0000-0000000000d1','REVERSED',((current_date-1)+time '10:00') at time zone 'Asia/Jakarta');
insert into erp.sales_items values('00000000-0000-0000-0000-0000000000d2','00000000-0000-0000-0000-0000000000d1');
insert into erp.sale_stock_allocations(sale_item_id,lot_id,qty_pcs) values('00000000-0000-0000-0000-0000000000d2','00000000-0000-0000-0000-0000000000b1',10);
insert into erp.po_hpp_gl_state values('00000000-0000-0000-0000-0000000000a0',10,100,100,0,0,now()-interval '1 hour');
insert into erp.po_hpp_gl_lot_state_v1 values('00000000-0000-0000-0000-0000000000b1','00000000-0000-0000-0000-0000000000a0',10,now()-interval '1 hour');
select erp.sync_po_hpp_to_gl('00000000-0000-0000-0000-0000000000a0',current_date-3);
select j.transaction_date d,l.mapping_key k,sum(l.debit-l.credit) amt from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id group by 1,2 order by 1,2;
rollback;
