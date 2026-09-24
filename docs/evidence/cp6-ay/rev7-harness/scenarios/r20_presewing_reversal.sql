\set QUIET 1
\pset footer off
-- rev7.4: a cutting issue reversed before sewing (erp.reverse_cutting_material_flow_before_sewing_v2) leaves the HPP.
-- PO pool (lot without lineage group, as r3): group a1 cut 10 units d-4, group a2 cut 4 units d-4, lot b1 10 pcs QC d-3,
-- a2's issue reversed d-1 (movement f3 reversal_of_id f2; the issue journal leaves WIP at 40 that day; AS/AZ target the
-- revaluation of a reversed movement to zero). Old 14.00/pc (100+40 at 10.00, synced before the reversal); new 8.25/pc
-- (erp.rebuild_po_hpp rev7.4: 82.50, the reversed issue out). AZ: WIP -17.50 d-4 (a1 at 8.25).
-- Expected AY: d-3 FG -17.50 / WIP +17.50 (a1's correction); d-1 FG -40.00 / WIP +40.00 (a2's material leaves the lot on
-- its reversal day). PO WIP with AZ and the reversal journal: 0 from d-3 on.
begin;
\ir common_lot.sql
update erp.fg_lots set cutting_group_id=null;
insert into erp.cutting_groups values('00000000-0000-0000-0000-0000000000a2','00000000-0000-0000-0000-0000000000a0',null,((current_date-4)+time '09:00') at time zone 'Asia/Jakarta');
insert into erp.v_cutting_group_totals values('00000000-0000-0000-0000-0000000000a2',4);
insert into erp.material_stock_movements(id,source_id,source_type,qty_signed,unit_cost_snapshot,physical_at,reversal_of_id) values
 ('00000000-0000-0000-0000-0000000000f1','00000000-0000-0000-0000-0000000000a1','CUTTING_GROUP',-10,8.25,((current_date-4)+time '08:00') at time zone 'Asia/Jakarta',null),
 ('00000000-0000-0000-0000-0000000000f2','00000000-0000-0000-0000-0000000000a2','CUTTING_GROUP',-4,8.25,((current_date-4)+time '09:00') at time zone 'Asia/Jakarta',null),
 ('00000000-0000-0000-0000-0000000000f3','00000000-0000-0000-0000-0000000000a2','CUTTING_PRESEWING_REVERSAL',4,10,((current_date-1)+time '10:00') at time zone 'Asia/Jakarta','00000000-0000-0000-0000-0000000000f2');
insert into erp.po_hpp_gl_material_state_v1 values('00000000-0000-0000-0000-0000000000a0','M:00000000-0000-0000-0000-0000000000f1',100,now()-interval '1 hour'),
 ('00000000-0000-0000-0000-0000000000a0','M:00000000-0000-0000-0000-0000000000f2',40,now()-interval '1 hour');
insert into erp.po_hpp_gl_state values('00000000-0000-0000-0000-0000000000a0',10,140,140,0,0,now()-interval '1 hour');
select erp.sync_po_hpp_to_gl('00000000-0000-0000-0000-0000000000a0',current_date-4);
select *, cum_wip + case when d>=current_date-1 then -17.50-40 else -17.50 end as po_wip_with_az_and_reversal from public.show();
select source_key,material_value from erp.po_hpp_gl_material_state_v1 order by 1;
rollback;
