\set QUIET 1
\pset footer off
-- One invoice with two materials (one statement): M1 cut d-4 (10 @ 10 -> 8.25), M2 contractor item d-1 (5 @ 2 -> 1.60).
-- _recalculate_material_cost_core runs rebuild+sync per material in the same statement. Lot 10 pcs QC d-3.
-- Expected: sync 1 (M1): d-3 FG -17.50; sync 2 (M2): d-1 FG -2.00; state = final values.
begin;
\ir common_lot.sql
insert into erp.materials values('00000000-0000-0000-0000-0000000000ae','FABRIC');
insert into erp.contractor_material_issues values('00000000-0000-0000-0000-0000000000ac','00000000-0000-0000-0000-0000000000a0','POSTED',((current_date-1)+time '09:00') at time zone 'Asia/Jakarta');
insert into erp.contractor_material_issue_items values('00000000-0000-0000-0000-0000000000ad','00000000-0000-0000-0000-0000000000ac','00000000-0000-0000-0000-0000000000ae',5,2);
insert into erp.material_stock_movements(id,source_id,source_type,qty_signed,unit_cost_snapshot,physical_at,system_created_at) values
 ('00000000-0000-0000-0000-0000000000f1','00000000-0000-0000-0000-0000000000a1','CUTTING_GROUP',-10,10,((current_date-4)+time '08:00') at time zone 'Asia/Jakarta',now()-interval '3 hour'),
 ('00000000-0000-0000-0000-0000000000f3','00000000-0000-0000-0000-0000000000ad','CONTRACTOR_MATERIAL_ISSUE_ITEM',-5,2,((current_date-1)+time '09:00') at time zone 'Asia/Jakarta',now()-interval '3 hour');
insert into erp.po_hpp_gl_material_state_v1 values('00000000-0000-0000-0000-0000000000a0','M:00000000-0000-0000-0000-0000000000f1',100,now()-interval '1 hour'),
 ('00000000-0000-0000-0000-0000000000a0','C:00000000-0000-0000-0000-0000000000ad',10,now()-interval '1 hour'),('00000000-0000-0000-0000-0000000000a0','SYNC',0,now()-interval '1 hour');
update erp.hpp_versions set total_cost=110,is_current=true where version_no=1; delete from erp.hpp_versions where version_no=2;
update erp.po_hpp_gl_lot_state_v1 set hpp_per_pcs=11;
insert into erp.po_hpp_gl_state values('00000000-0000-0000-0000-0000000000a0',10,110,110,0,0,now()-interval '1 hour');
do $$
begin
  update erp.material_stock_movements set unit_cost_snapshot=8.25 where id='00000000-0000-0000-0000-0000000000f1';
  update erp.hpp_versions set is_current=false where is_current;
  insert into erp.hpp_versions(lot_id,version_no,qty_basis_pcs,total_cost,is_current,calculated_at) values('00000000-0000-0000-0000-0000000000b1',2,10,92.5,true,statement_timestamp());
  perform erp.sync_po_hpp_to_gl('00000000-0000-0000-0000-0000000000a0',current_date-4);
  update erp.material_stock_movements set unit_cost_snapshot=1.6 where id='00000000-0000-0000-0000-0000000000f3';
  update erp.contractor_material_issue_items set unit_cost_snapshot=1.6;
  update erp.hpp_versions set is_current=false where is_current;
  insert into erp.hpp_versions(lot_id,version_no,qty_basis_pcs,total_cost,is_current,calculated_at) values('00000000-0000-0000-0000-0000000000b1',3,10,90.5,true,statement_timestamp());
  perform erp.sync_po_hpp_to_gl('00000000-0000-0000-0000-0000000000a0',current_date-4);
end $$;
select * from public.show();
select source_key,material_value from erp.po_hpp_gl_material_state_v1 order by 1;
rollback;
