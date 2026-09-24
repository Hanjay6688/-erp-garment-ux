\set QUIET 1
\pset footer off
-- M-1: cutting return after the lot. Group cut 10 units d-4 (E), lot 10 pcs QC d-3, 2 units returned d-1.
-- Old 8.00/pc (80 = 100-20 at 10.00, synced after the return); new 6.60 (82.50-16.50). AZ: WIP -17.50 d-4, +3.50 d-1.
-- Expected AY: d-3 FG -17.50 / WIP +17.50; d-1 FG +3.50 / WIP -3.50 (PO WIP with AZ never below the material in it).
begin;
\ir common_lot.sql
insert into erp.material_stock_movements(id,source_id,source_type,qty_signed,unit_cost_snapshot,physical_at) values
 ('00000000-0000-0000-0000-0000000000f1','00000000-0000-0000-0000-0000000000a1','CUTTING_GROUP',-10,11.75,((current_date-4)+time '08:00') at time zone 'Asia/Jakarta'),
 ('00000000-0000-0000-0000-0000000000f2','00000000-0000-0000-0000-0000000000a1','CUTTING_GROUP_RETURN',2,11.75,((current_date-1)+time '08:00') at time zone 'Asia/Jakarta');
insert into erp.po_hpp_gl_material_state_v1 values('00000000-0000-0000-0000-0000000000a0','M:00000000-0000-0000-0000-0000000000f1',100,now()-interval '1 hour'),
 ('00000000-0000-0000-0000-0000000000a0','M:00000000-0000-0000-0000-0000000000f2',-20,now()-interval '1 hour');
insert into erp.po_hpp_gl_state values('00000000-0000-0000-0000-0000000000a0',10,80,80,0,0,now()-interval '1 hour');
select erp.sync_po_hpp_to_gl('00000000-0000-0000-0000-0000000000a0',current_date-4);
select *, cum_wip + case when d>=current_date-1 then -3.50+17.50 else 17.50 end as po_wip_delta_with_az from public.show();
select source_key,material_value from erp.po_hpp_gl_material_state_v1 order by 1;
rollback;
