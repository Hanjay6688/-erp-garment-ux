\set QUIET 1
\pset footer off
-- First late invoice after the AY install for a PO produced before it (no po_hpp_gl_material_state_v1 rows, no SYNC marker):
-- same facts as rev7/r1_return (cut 10 @ d-4, lot 10 pcs QC d-3, 2 units returned d-1, old 8.00/pc, new 6.60/pc).
-- AZ: WIP -17.50 d-4, +3.50 d-1. Expected (owner rule): d-3 FG -17.50/WIP +17.50, d-1 FG +3.50/WIP -3.50.
begin;
\ir common_lot.sql
insert into erp.material_stock_movements(id,source_id,source_type,qty_signed,unit_cost_snapshot,physical_at) values
 ('00000000-0000-0000-0000-0000000000f1','00000000-0000-0000-0000-0000000000a1','CUTTING_GROUP',-10,8.25,((current_date-4)+time '08:00') at time zone 'Asia/Jakarta'),
 ('00000000-0000-0000-0000-0000000000f2','00000000-0000-0000-0000-0000000000a1','CUTTING_GROUP_RETURN',2,8.25,((current_date-1)+time '08:00') at time zone 'Asia/Jakarta');
insert into erp.po_hpp_gl_state values('00000000-0000-0000-0000-0000000000a0',10,80,80,0,0,now()-interval '1 hour');
select erp.sync_po_hpp_to_gl('00000000-0000-0000-0000-0000000000a0',current_date-4);
\echo 'po_wip_after_qc = AY WIP legs + AZ legs (the physical WIP of the PO is 0 after the QC of d-3 and after the return of d-1):'
select d,fg,wip,cum_wip + case when d>=current_date-1 then 3.50-17.50 else -17.50 end as po_wip_after_qc from public.show();
rollback;
