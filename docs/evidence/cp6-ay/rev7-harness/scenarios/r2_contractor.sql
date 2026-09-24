\set QUIET 1
\pset footer off
-- M-1: contractor (non-accessory) issue after the lot. Cut 10 @ 10.00 -> 8.25 on d-4; contractor issue item 5 @ 2.00 -> 1.60,
-- header physical d-2 but its stock movement d-1 (AZ dates the WIP revaluation -2.00 on the movement day d-1).
-- Source qty 10. Old 11.00/pc, new 9.05. Expected: d-3 FG -17.50; d-1 FG -2.00 (not on d-3, not on d-2).
begin;
\ir common_lot.sql
insert into erp.material_stock_movements(id,source_id,source_type,qty_signed,unit_cost_snapshot,physical_at) values
 ('00000000-0000-0000-0000-0000000000f1','00000000-0000-0000-0000-0000000000a1','CUTTING_GROUP',-10,8.25,((current_date-4)+time '08:00') at time zone 'Asia/Jakarta'),
 ('00000000-0000-0000-0000-0000000000f3','00000000-0000-0000-0000-0000000000ad','CONTRACTOR_MATERIAL_ISSUE_ITEM',-5,1.60,((current_date-1)+time '09:00') at time zone 'Asia/Jakarta');
insert into erp.materials values('00000000-0000-0000-0000-0000000000ae','FABRIC');
insert into erp.contractor_material_issues values('00000000-0000-0000-0000-0000000000ac','00000000-0000-0000-0000-0000000000a0','POSTED',((current_date-2)+time '09:00') at time zone 'Asia/Jakarta');
insert into erp.contractor_material_issue_items values('00000000-0000-0000-0000-0000000000ad','00000000-0000-0000-0000-0000000000ac','00000000-0000-0000-0000-0000000000ae',5,1.60);
insert into erp.po_hpp_gl_material_state_v1 values('00000000-0000-0000-0000-0000000000a0','M:00000000-0000-0000-0000-0000000000f1',100,now()-interval '1 hour'),
 ('00000000-0000-0000-0000-0000000000a0','C:00000000-0000-0000-0000-0000000000ad',10,now()-interval '1 hour');
update erp.hpp_versions set total_cost=case when is_current then 90.5 else 110 end;
update erp.po_hpp_gl_lot_state_v1 set hpp_per_pcs=11;
insert into erp.po_hpp_gl_state values('00000000-0000-0000-0000-0000000000a0',10,110,110,0,0,now()-interval '1 hour');
select erp.sync_po_hpp_to_gl('00000000-0000-0000-0000-0000000000a0',current_date-4);
select * from public.show();
rollback;
