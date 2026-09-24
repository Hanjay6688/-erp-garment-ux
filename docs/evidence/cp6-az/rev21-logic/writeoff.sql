\set QUIET 1
\pset footer off
-- Reversed write-off: receipt 10 units d-3 (revalued by the invoice journal, not here), material adjustment item -10 on
-- d-2 at 10 (all units written off), reversed today (+10). Replay average before the write-off 8.25. :mode open|closed|noninv.
-- Expected open: +17.50 on d-2 (MATERIAL_INVENTORY against OTHER_EXPENSE), -17.50 today, on the reversal movement.
-- Without the legs MATERIAL_INVENTORY would be 82.50-100 = -17.50 from d-2 to today. closed / noninv: nothing.
begin;
insert into erp.material_adjustment_items values('00000000-0000-0000-0000-0000000000d1','00000000-0000-0000-0000-0000000000d0','00000000-0000-0000-0000-0000000000cc');
insert into erp.material_stock_movements values
 ('00000000-0000-0000-0000-0000000000f0','00000000-0000-0000-0000-0000000000cc','MATERIAL_PURCHASE_ROLL',null,'PURCHASE',10,8.25,10,((current_date-3)+time '23:30') at time zone 'Asia/Jakarta',now()-interval '5 hour',null,null),
 ('00000000-0000-0000-0000-0000000000f4','00000000-0000-0000-0000-0000000000cc','MATERIAL_ADJUSTMENT_ITEM','00000000-0000-0000-0000-0000000000d1','ADJUSTMENT',-10,10,10,((current_date-2)+time '12:00') at time zone 'Asia/Jakarta',now()-interval '4 hour',null,null),
 ('00000000-0000-0000-0000-0000000000f5','00000000-0000-0000-0000-0000000000cc','MATERIAL_ADJUSTMENT_ITEM','00000000-0000-0000-0000-0000000000d1','REVERSAL',10,10,null,now(),now()-interval '1 hour',null,'00000000-0000-0000-0000-0000000000f4');
insert into erp.material_cost_history values('00000000-0000-0000-0000-0000000000cc','00000000-0000-0000-0000-0000000000f0',8.25);
insert into erp.settings select 'E',(current_date-3)::text where :'mode'<>'noninv';
update erp.accounting_period_control set closed_through=current_date-3 where :'mode'='closed';
select erp.sync_material_cost_revaluation('00000000-0000-0000-0000-0000000000cc');
select right(e.movement_id::text,2) mv,e.effective_date-current_date as day_from_today,e.delta_amount,e.counterpart_mapping_key from erp.material_cost_revaluation_events e order by e.effective_date,mv;
select l.mapping_key,j.transaction_date-current_date day_from_today,sum(l.debit-l.credit) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id group by 1,2 order by 2,1;
select erp.sync_material_cost_revaluation('00000000-0000-0000-0000-0000000000cc');
select count(*) events_after_second_run from erp.material_cost_revaluation_events;
rollback;
