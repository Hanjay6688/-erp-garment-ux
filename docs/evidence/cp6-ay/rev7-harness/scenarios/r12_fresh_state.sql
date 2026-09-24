\set QUIET 1
\pset footer off
-- A contractor issue posted after the last state write (no rebuild since): cut 10 @ 10.00 -> 8.25 on d-4 (state 100),
-- contractor item 5 @ 1.60 on d-1 created after the SYNC marker, no state row. Old 10.00/pc (no contractor material in
-- the HPP last posted); new 9.05. Expected: d-3 FG -17.50; d-1 FG +8.00 (the contractor material enters on its day).
-- Fresh: the HPP was rebuilt in this statement (current version calculated at or after the statement), so the state is written.
begin;
\ir common_lot.sql
insert into erp.material_stock_movements(id,source_id,source_type,qty_signed,unit_cost_snapshot,physical_at,system_created_at) values
 ('00000000-0000-0000-0000-0000000000f1','00000000-0000-0000-0000-0000000000a1','CUTTING_GROUP',-10,8.25,((current_date-4)+time '08:00') at time zone 'Asia/Jakarta',now()-interval '3 hour'),
 ('00000000-0000-0000-0000-0000000000f3','00000000-0000-0000-0000-0000000000ad','CONTRACTOR_MATERIAL_ISSUE_ITEM',-5,1.60,((current_date-1)+time '09:00') at time zone 'Asia/Jakarta',now()-interval '30 minute');
insert into erp.materials values('00000000-0000-0000-0000-0000000000ae','FABRIC');
insert into erp.contractor_material_issues values('00000000-0000-0000-0000-0000000000ac','00000000-0000-0000-0000-0000000000a0','POSTED',((current_date-1)+time '09:00') at time zone 'Asia/Jakarta');
insert into erp.contractor_material_issue_items values('00000000-0000-0000-0000-0000000000ad','00000000-0000-0000-0000-0000000000ac','00000000-0000-0000-0000-0000000000ae',5,1.60);
insert into erp.po_hpp_gl_material_state_v1 values('00000000-0000-0000-0000-0000000000a0','M:00000000-0000-0000-0000-0000000000f1',100,now()-interval '1 hour');
insert into erp.po_hpp_gl_material_state_v1 select '00000000-0000-0000-0000-0000000000a0','SYNC',0,now()-interval '1 hour' where :'marker'='yes';
update erp.hpp_versions set total_cost=case when is_current then 90.5 else 100 end,calculated_at=case when is_current then now()+interval '1 hour' else calculated_at end;
insert into erp.po_hpp_gl_state values('00000000-0000-0000-0000-0000000000a0',10,100,100,0,0,now()-interval '1 hour');
select erp.sync_po_hpp_to_gl('00000000-0000-0000-0000-0000000000a0',current_date-4);
select * from public.show();
select source_key,material_value,updated_at>now()-interval '1 minute' written_now from erp.po_hpp_gl_material_state_v1 order by 1;
rollback;
