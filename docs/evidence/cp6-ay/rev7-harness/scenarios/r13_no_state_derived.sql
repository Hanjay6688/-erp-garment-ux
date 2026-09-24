\set QUIET 1
\pset footer off
-- Independent review of rev7, F1: first late invoice after the AY install for a PO produced before it (no material state,
-- no SYNC marker). Same facts as r1 (cut 10 @ d-4, lot 10 pcs QC d-3, 2 units returned d-1, old 8.00/pc, new 6.60/pc); the
-- HPP was last rebuilt 2 hours ago (tp) and again in this statement; the invoice's revaluation events (after tp): cut
-- +17.50, return -3.50 (inventory delta). Expected: as r1, d-3 FG -17.50 / WIP +17.50, d-1 FG +3.50 / WIP -3.50; state written.
begin;
\ir common_lot.sql
update erp.hpp_versions set calculated_at=case when is_current then now()+interval '1 hour' else now()-interval '2 hour' end;
insert into erp.material_stock_movements(id,source_id,source_type,qty_signed,unit_cost_snapshot,physical_at) values
 ('00000000-0000-0000-0000-0000000000f1','00000000-0000-0000-0000-0000000000a1','CUTTING_GROUP',-10,8.25,((current_date-4)+time '08:00') at time zone 'Asia/Jakarta'),
 ('00000000-0000-0000-0000-0000000000f2','00000000-0000-0000-0000-0000000000a1','CUTTING_GROUP_RETURN',2,8.25,((current_date-1)+time '08:00') at time zone 'Asia/Jakarta');
insert into erp.material_cost_revaluation_events(movement_id,delta_amount,created_at) values
 ('00000000-0000-0000-0000-0000000000f1',17.50,now()-interval '30 minute'),('00000000-0000-0000-0000-0000000000f2',-3.50,now()-interval '30 minute'),
 ('00000000-0000-0000-0000-0000000000f1',99,now()-interval '3 hour');
insert into erp.po_hpp_gl_state values('00000000-0000-0000-0000-0000000000a0',10,80,80,0,0,now()-interval '1 hour');
select erp.sync_po_hpp_to_gl('00000000-0000-0000-0000-0000000000a0',current_date-4);
select * from public.show();
select source_key,material_value from erp.po_hpp_gl_material_state_v1 order by 1;
rollback;
