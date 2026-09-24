\set QUIET 1
\pset footer off
-- Independent review of rev7 (residual risk): a non-invoice recost still queued when the invoice is processed. Cut 10 units
-- d-4 (state 100 at 10.00), lot 10 pcs QC d-3. Yesterday (d-1) a non-invoice recost 10.00 -> 9.00 (AZ: WIP -10.00 on d-1,
-- revaluation event +10.00 effective d-1), not synced; today the invoice 9.00 -> 8.25 (AZ: WIP -7.50 on d-4, event +7.50
-- effective d-4). Expected AY: d-3 FG -7.50 (the invoice part), d-1 FG -10.00 (the queued part, when it entered WIP).
begin;
\ir common_lot.sql
insert into erp.material_stock_movements(id,source_id,source_type,qty_signed,unit_cost_snapshot,physical_at) values
 ('00000000-0000-0000-0000-0000000000f1','00000000-0000-0000-0000-0000000000a1','CUTTING_GROUP',-10,8.25,((current_date-4)+time '08:00') at time zone 'Asia/Jakarta');
insert into erp.po_hpp_gl_material_state_v1 values('00000000-0000-0000-0000-0000000000a0','M:00000000-0000-0000-0000-0000000000f1',100,now()-interval '1 day'),
 ('00000000-0000-0000-0000-0000000000a0','SYNC',0,now()-interval '1 day');
insert into erp.material_cost_revaluation_events(movement_id,delta_amount,created_at,effective_date) values
 ('00000000-0000-0000-0000-0000000000f1',10.00,now()-interval '20 hour',current_date-1),
 ('00000000-0000-0000-0000-0000000000f1',7.50,now()-interval '1 minute',current_date-4),
 ('00000000-0000-0000-0000-0000000000f1',55,now()-interval '2 day',current_date-9);
update erp.po_hpp_gl_lot_state_v1 set updated_at=now()-interval '1 day';
insert into erp.po_hpp_gl_state values('00000000-0000-0000-0000-0000000000a0',10,100,100,0,0,now()-interval '1 day');
select erp.sync_po_hpp_to_gl('00000000-0000-0000-0000-0000000000a0',current_date-4);
select * from public.show();
rollback;
