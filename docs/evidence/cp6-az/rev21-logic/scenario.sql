\set QUIET 1
\pset footer off
-- Native case AY:PRESEWING_REVERSAL_THEN_LATE_INVOICE_LOWER (run 35998326956) in miniature. Receipt 10 units d-3 (not a
-- revalued movement here; the invoice journal carries its -17.50); M2 issue 6 units d-2 08:00 (group g2, reversed today),
-- M1 issue 4 units d-2 08:01 (group g1); reversal R of M2 today. Invoice at 8.25 (was 10): replay average 8.25 before both
-- issues; M1 effective (snapshot 8.25), M2 excluded from the replay (snapshot 10). :mode = open | closed | noninv.
-- Expected open: M1 +7.00 and M2 +10.50 on d-2, R -10.50 today (inventory delta; counterpart WIP of the PO).
-- Expected closed / noninv: M1 +7.00 on E / today; M2 and R nothing (net zero on one day, as before).
begin;
insert into erp.cutting_groups values('00000000-0000-0000-0000-0000000000a1','00000000-0000-0000-0000-0000000000a0'),('00000000-0000-0000-0000-0000000000a2','00000000-0000-0000-0000-0000000000a0');
insert into erp.material_stock_movements values
 ('00000000-0000-0000-0000-0000000000f0','00000000-0000-0000-0000-0000000000cc','MATERIAL_PURCHASE_ROLL',null,'PURCHASE',10,8.25,10,((current_date-3)+time '23:30') at time zone 'Asia/Jakarta',now()-interval '5 hour',null,null),
 ('00000000-0000-0000-0000-0000000000f2','00000000-0000-0000-0000-0000000000cc','CUTTING_GROUP','00000000-0000-0000-0000-0000000000a2','CUTTING_ISSUE',-6,10,10,((current_date-2)+time '08:00') at time zone 'Asia/Jakarta',now()-interval '4 hour',null,null),
 ('00000000-0000-0000-0000-0000000000f1','00000000-0000-0000-0000-0000000000cc','CUTTING_GROUP','00000000-0000-0000-0000-0000000000a1','CUTTING_ISSUE',-4,8.25,10,((current_date-2)+time '08:00') at time zone 'Asia/Jakarta',now()-interval '3 hour',null,null),
 ('00000000-0000-0000-0000-0000000000f3','00000000-0000-0000-0000-0000000000cc','CUTTING_PRESEWING_REVERSAL','00000000-0000-0000-0000-0000000000a2','REVERSAL',6,10,null,now(),now()-interval '1 hour',null,'00000000-0000-0000-0000-0000000000f2');
insert into erp.material_cost_history values('00000000-0000-0000-0000-0000000000cc','00000000-0000-0000-0000-0000000000f0',8.25),('00000000-0000-0000-0000-0000000000cc','00000000-0000-0000-0000-0000000000f1',8.25);
insert into erp.settings select 'E',(current_date-3)::text where :'mode'<>'noninv';
update erp.accounting_period_control set closed_through=current_date-3 where :'mode'='closed';
select erp.sync_material_cost_revaluation('00000000-0000-0000-0000-0000000000cc');
select right(e.movement_id::text,2) mv,e.effective_date-current_date as day_from_today,e.new_inventory_delta,e.delta_amount,e.counterpart_mapping_key from erp.material_cost_revaluation_events e order by e.effective_date,mv;
select right(movement_id::text,2) mv,applied_inventory_delta from erp.material_cost_revaluation_state order by 1;
-- second run in the same state: nothing new
select erp.sync_material_cost_revaluation('00000000-0000-0000-0000-0000000000cc');
select count(*) events_after_second_run from erp.material_cost_revaluation_events;
rollback;
