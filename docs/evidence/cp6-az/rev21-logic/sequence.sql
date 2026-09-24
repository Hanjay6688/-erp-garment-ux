\set QUIET 1
\pset footer off
-- Same data as scenario.sql. Open invoice (8.25), then a recost without invoice, then another open invoice after which the
-- replay average is 8.00. Expected: M2 +10.50 d-2 / R -10.50 today; the recost without invoice adds nothing for M2/R
-- (the interim is kept, not zeroed); the second invoice adds only the change: M2 +1.50 d-2 / R -1.50 today (and M1 +1.00).
begin;
insert into erp.cutting_groups values('00000000-0000-0000-0000-0000000000a1','00000000-0000-0000-0000-0000000000a0'),('00000000-0000-0000-0000-0000000000a2','00000000-0000-0000-0000-0000000000a0');
insert into erp.material_stock_movements values
 ('00000000-0000-0000-0000-0000000000f0','00000000-0000-0000-0000-0000000000cc','MATERIAL_PURCHASE_ROLL',null,'PURCHASE',10,8.25,10,((current_date-3)+time '23:30') at time zone 'Asia/Jakarta',now()-interval '5 hour',null,null),
 ('00000000-0000-0000-0000-0000000000f2','00000000-0000-0000-0000-0000000000cc','CUTTING_GROUP','00000000-0000-0000-0000-0000000000a2','CUTTING_ISSUE',-6,10,10,((current_date-2)+time '08:00') at time zone 'Asia/Jakarta',now()-interval '4 hour',null,null),
 ('00000000-0000-0000-0000-0000000000f1','00000000-0000-0000-0000-0000000000cc','CUTTING_GROUP','00000000-0000-0000-0000-0000000000a1','CUTTING_ISSUE',-4,8.25,10,((current_date-2)+time '08:00') at time zone 'Asia/Jakarta',now()-interval '3 hour',null,null),
 ('00000000-0000-0000-0000-0000000000f3','00000000-0000-0000-0000-0000000000cc','CUTTING_PRESEWING_REVERSAL','00000000-0000-0000-0000-0000000000a2','REVERSAL',6,10,null,now(),now()-interval '1 hour',null,'00000000-0000-0000-0000-0000000000f2');
insert into erp.material_cost_history values('00000000-0000-0000-0000-0000000000cc','00000000-0000-0000-0000-0000000000f0',8.25),('00000000-0000-0000-0000-0000000000cc','00000000-0000-0000-0000-0000000000f1',8.25);
insert into erp.settings values('E',(current_date-3)::text);
select erp.sync_material_cost_revaluation('00000000-0000-0000-0000-0000000000cc');
delete from erp.settings;
select erp.sync_material_cost_revaluation('00000000-0000-0000-0000-0000000000cc');
insert into erp.settings values('E',(current_date-3)::text);
update erp.material_cost_history set average_after=8.00;
update erp.material_stock_movements set unit_cost_snapshot=8.00 where id='00000000-0000-0000-0000-0000000000f1';
select erp.sync_material_cost_revaluation('00000000-0000-0000-0000-0000000000cc');
select right(e.movement_id::text,2) mv,e.effective_date-current_date as day_from_today,e.delta_amount from erp.material_cost_revaluation_events e order by e.id::text is null,e.effective_date,mv,e.delta_amount;
select right(movement_id::text,2) mv,applied_inventory_delta from erp.material_cost_revaluation_state order by 1;
rollback;
