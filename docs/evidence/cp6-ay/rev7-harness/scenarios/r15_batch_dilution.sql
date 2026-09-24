\set QUIET 1
\pset footer off
-- (Independent review of rev7, F4; copied from the reviewer repro x6. Expected: -7.00 on the lot day, +37.69 on the new group cut day.)
-- Batch bb: G1 (PO a0, 8 pcs, cut d-4, 4 units, state 40.00) and G2 (PO ab, 3 pcs, cut d-1 AFTER a0's last state write,
-- 6 units @ 10.70 = 64.20, so it counts from zero). Invoice E=d-5 lowers G1's material 40.00 -> 33.00.
-- a0's lot b1 (8 pcs, QC d-3) was last posted at 40/8 = 5.00/pc; now (33+64.20)/11 = 8.8364/pc.
-- Owner rule: d-3 only the invoice change of G1 is there: 8 x (33-40)/8 = -7.00; d-1 G2 is cut: the rest +37.69.
begin;
insert into erp.settings values('E',(current_date-5)::text);
insert into erp.cutting_groups values
 ('00000000-0000-0000-0000-0000000000a1','00000000-0000-0000-0000-0000000000a0','00000000-0000-0000-0000-0000000000bb',((current_date-4)+time '08:00') at time zone 'Asia/Jakarta'),
 ('00000000-0000-0000-0000-0000000000a2','00000000-0000-0000-0000-0000000000ab','00000000-0000-0000-0000-0000000000bb',((current_date-1)+time '08:00') at time zone 'Asia/Jakarta');
insert into erp.v_cutting_group_totals values('00000000-0000-0000-0000-0000000000a1',8),('00000000-0000-0000-0000-0000000000a2',3);
insert into erp.v_cutting_batch_totals values('00000000-0000-0000-0000-0000000000bb',11);
insert into erp.material_stock_movements(id,source_id,source_type,qty_signed,unit_cost_snapshot,physical_at,system_created_at) values
 ('00000000-0000-0000-0000-0000000000e1','00000000-0000-0000-0000-0000000000a1','CUTTING_GROUP',-4,8.25,((current_date-4)+time '08:00') at time zone 'Asia/Jakarta',now()-interval '3 hour'),
 ('00000000-0000-0000-0000-0000000000e2','00000000-0000-0000-0000-0000000000a2','CUTTING_GROUP',-6,10.70,((current_date-1)+time '08:00') at time zone 'Asia/Jakarta',now()-interval '30 minute');
insert into erp.fg_lots values
 ('00000000-0000-0000-0000-0000000000b1','00000000-0000-0000-0000-0000000000a0','PRODUCTION',8,((current_date-3)+time '13:00') at time zone 'Asia/Jakarta','00000000-0000-0000-0000-0000000000a1',null,null);
insert into erp.hpp_versions(lot_id,version_no,qty_basis_pcs,total_cost,is_current,calculated_at) values
 ('00000000-0000-0000-0000-0000000000b1',1,8,40,false,now()-interval '2 hour'),('00000000-0000-0000-0000-0000000000b1',2,8,8*97.2/11,true,now());
insert into erp.fg_stock_movements(lot_id,movement_type,qty_signed,physical_at) values
 ('00000000-0000-0000-0000-0000000000b1','QC_GOOD',8,((current_date-3)+time '13:00') at time zone 'Asia/Jakarta');
insert into erp.po_hpp_gl_state values('00000000-0000-0000-0000-0000000000a0',8,40,40,0,0,now()-interval '1 hour');
insert into erp.po_hpp_gl_lot_state_v1 values('00000000-0000-0000-0000-0000000000b1','00000000-0000-0000-0000-0000000000a0',5,now()-interval '1 hour');
insert into erp.po_hpp_gl_material_state_v1 values('00000000-0000-0000-0000-0000000000a0','M:00000000-0000-0000-0000-0000000000e1',40,now()-interval '1 hour'),
 ('00000000-0000-0000-0000-0000000000a0','SYNC',0,now()-interval '1 hour');
select erp.sync_po_hpp_to_gl('00000000-0000-0000-0000-0000000000a0',current_date-5);
select d,fg,wip,cum_fg from public.show();
rollback;
