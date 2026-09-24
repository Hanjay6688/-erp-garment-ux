\set QUIET 1
\pset footer off
-- Relabel chain (depth 2), both conversions POSTED, no conversion cost (every lot in the chain has the same HPP change).
-- PO a0: group a1 (10 pcs, lot b1) and group a2 (10 pcs, lot b2), cut d-5 (E), QC d-4. b1 -> c1 (4 pcs) d-3, c1 -> c2 d-2.
-- Late invoice lowers the price: a1 100 -> 82.50, a2 100 -> 82.50 and a2's cutting return of d-1 -20 -> -16.50.
-- Expected: the other account never moves (the chain carries b1's correction); FG -35.00 on d-4, +3.50 on d-1.
begin;
insert into erp.settings values('E',(current_date-5)::text);
insert into erp.cutting_groups values
 ('00000000-0000-0000-0000-0000000000a1','00000000-0000-0000-0000-0000000000a0',null,((current_date-5)+time '08:00') at time zone 'Asia/Jakarta'),
 ('00000000-0000-0000-0000-0000000000a2','00000000-0000-0000-0000-0000000000a0',null,((current_date-5)+time '08:00') at time zone 'Asia/Jakarta');
insert into erp.v_cutting_group_totals values('00000000-0000-0000-0000-0000000000a1',10),('00000000-0000-0000-0000-0000000000a2',10);
insert into erp.material_stock_movements(id,source_id,source_type,qty_signed,unit_cost_snapshot,physical_at) values
 ('00000000-0000-0000-0000-0000000000f1','00000000-0000-0000-0000-0000000000a1','CUTTING_GROUP',-10,8.25,((current_date-5)+time '08:00') at time zone 'Asia/Jakarta'),
 ('00000000-0000-0000-0000-0000000000f2','00000000-0000-0000-0000-0000000000a2','CUTTING_GROUP',-10,8.25,((current_date-5)+time '08:00') at time zone 'Asia/Jakarta'),
 ('00000000-0000-0000-0000-0000000000f3','00000000-0000-0000-0000-0000000000a2','CUTTING_GROUP_RETURN',2,8.25,((current_date-1)+time '08:00') at time zone 'Asia/Jakarta');
insert into erp.po_hpp_gl_material_state_v1 values
 ('00000000-0000-0000-0000-0000000000a0','M:00000000-0000-0000-0000-0000000000f1',100,now()-interval '1 hour'),
 ('00000000-0000-0000-0000-0000000000a0','M:00000000-0000-0000-0000-0000000000f2',100,now()-interval '1 hour'),
 ('00000000-0000-0000-0000-0000000000a0','M:00000000-0000-0000-0000-0000000000f3',-20,now()-interval '1 hour'),
 ('00000000-0000-0000-0000-0000000000a0','SYNC',0,now()-interval '1 hour');
insert into erp.fg_lots values
 ('00000000-0000-0000-0000-0000000000b1','00000000-0000-0000-0000-0000000000a0','PRODUCTION',10,((current_date-4)+time '13:00') at time zone 'Asia/Jakarta','00000000-0000-0000-0000-0000000000a1',null,null),
 ('00000000-0000-0000-0000-0000000000b2','00000000-0000-0000-0000-0000000000a0','PRODUCTION',10,((current_date-4)+time '13:00') at time zone 'Asia/Jakarta','00000000-0000-0000-0000-0000000000a2',null,null),
 ('00000000-0000-0000-0000-0000000000c1','00000000-0000-0000-0000-0000000000a0','CONVERSION',4,((current_date-3)+time '10:00') at time zone 'Asia/Jakarta',null,null,null),
 ('00000000-0000-0000-0000-0000000000c2','00000000-0000-0000-0000-0000000000a0','CONVERSION',4,((current_date-2)+time '10:00') at time zone 'Asia/Jakarta',null,null,null);
insert into erp.hpp_versions(lot_id,version_no,qty_basis_pcs,total_cost,is_current,calculated_at) values
 ('00000000-0000-0000-0000-0000000000b1',1,10,100,false,now()-interval '2 hour'),('00000000-0000-0000-0000-0000000000b1',2,10,82.5,true,now()),
 ('00000000-0000-0000-0000-0000000000b2',1,10,80,false,now()-interval '2 hour'),('00000000-0000-0000-0000-0000000000b2',2,10,66,true,now()),
 ('00000000-0000-0000-0000-0000000000c1',1,4,40,false,now()-interval '2 hour'),('00000000-0000-0000-0000-0000000000c1',2,4,33,true,now()),
 ('00000000-0000-0000-0000-0000000000c2',1,4,40,false,now()-interval '2 hour'),('00000000-0000-0000-0000-0000000000c2',2,4,33,true,now());
insert into erp.fg_stock_movements(lot_id,movement_type,qty_signed,physical_at) values
 ('00000000-0000-0000-0000-0000000000b1','QC_GOOD',10,((current_date-4)+time '13:00') at time zone 'Asia/Jakarta'),
 ('00000000-0000-0000-0000-0000000000b2','QC_GOOD',10,((current_date-4)+time '13:00') at time zone 'Asia/Jakarta'),
 ('00000000-0000-0000-0000-0000000000b1','REBRAND_OUT',-4,((current_date-3)+time '10:00') at time zone 'Asia/Jakarta'),
 ('00000000-0000-0000-0000-0000000000c1','REBRAND_IN',4,((current_date-3)+time '10:00') at time zone 'Asia/Jakarta'),
 ('00000000-0000-0000-0000-0000000000c1','REBRAND_OUT',-4,((current_date-2)+time '10:00') at time zone 'Asia/Jakarta'),
 ('00000000-0000-0000-0000-0000000000c2','REBRAND_IN',4,((current_date-2)+time '10:00') at time zone 'Asia/Jakarta');
insert into erp.product_conversions values('00000000-0000-0000-0000-00000000cf01','POSTED'),('00000000-0000-0000-0000-00000000cf02','POSTED');
insert into erp.product_conversion_allocations(conversion_id,source_lot_id,destination_lot_id) values
 ('00000000-0000-0000-0000-00000000cf01','00000000-0000-0000-0000-0000000000b1','00000000-0000-0000-0000-0000000000c1'),
 ('00000000-0000-0000-0000-00000000cf02','00000000-0000-0000-0000-0000000000c1','00000000-0000-0000-0000-0000000000c2');
insert into erp.po_hpp_gl_lot_state_v1 values
 ('00000000-0000-0000-0000-0000000000b1','00000000-0000-0000-0000-0000000000a0',10,now()-interval '1 hour'),
 ('00000000-0000-0000-0000-0000000000b2','00000000-0000-0000-0000-0000000000a0',8,now()-interval '1 hour'),
 ('00000000-0000-0000-0000-0000000000c1','00000000-0000-0000-0000-0000000000a0',10,now()-interval '1 hour'),
 ('00000000-0000-0000-0000-0000000000c2','00000000-0000-0000-0000-0000000000a0',10,now()-interval '1 hour');
insert into erp.po_hpp_gl_state values('00000000-0000-0000-0000-0000000000a0',20,180,180,0,0,now()-interval '1 hour');
select * from erp.compute_po_hpp_gl_targets_v2620d('00000000-0000-0000-0000-0000000000a0');
select erp.sync_po_hpp_to_gl('00000000-0000-0000-0000-0000000000a0',current_date-5);
select * from public.show();
rollback;
