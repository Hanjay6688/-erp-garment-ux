\set QUIET 1
\pset footer off
begin;
\ir common_lot.sql
-- write-off 4 on d-2, positive adjustment +1 on d-1
insert into erp.fg_stock_movements(lot_id,movement_type,qty_signed,physical_at,source_type) values
 ('00000000-0000-0000-0000-0000000000b1','ADJUSTMENT',-4,((current_date-2)+time '10:00') at time zone 'Asia/Jakarta','FG_ADJUSTMENT_ITEM'),
 ('00000000-0000-0000-0000-0000000000b1','ADJUSTMENT',1,((current_date-1)+time '10:00') at time zone 'Asia/Jakarta','FG_ADJUSTMENT_ITEM');
insert into erp.po_hpp_gl_state values('00000000-0000-0000-0000-0000000000a0',10,100,70,0,30,now()-interval '1 hour');
select * from erp.compute_po_hpp_gl_targets_v2620d('00000000-0000-0000-0000-0000000000a0');
select erp.sync_po_hpp_to_gl('00000000-0000-0000-0000-0000000000a0',current_date-4);
select * from public.show();
select l.mapping_key,sum(l.debit) dr,sum(l.credit) cr from erp.journal_lines l group by 1 order by 1;
rollback;
