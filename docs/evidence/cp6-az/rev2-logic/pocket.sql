\set QUIET 1
\pset footer off
-- Pocket recost: pool period d-10..d-3, the pocket fabric adjustment revaluated on d-6 (E open, AZ adjustment date). Expected
-- RECOST date d-3 (period end); closed: d-6 kept; a non-invoice recost (today) stays today.
begin;
update erp.accounting_period_control set closed_through=case when :'mode'='closed' then current_date-6 end;
insert into erp.pocket_fabric_usage values('00000000-0000-0000-0000-0000000000ad');
insert into erp.pocket_periods values('00000000-0000-0000-0000-0000000000f0',current_date-10,current_date-3);
insert into erp.pocket_period_sources values('00000000-0000-0000-0000-0000000000f0','00000000-0000-0000-0000-0000000000ad');
insert into erp.material_adjustment_revaluation_facts(adjustment_id,effective_date) values('00000000-0000-0000-0000-0000000000ad',case when :'mode'='noninv' then current_date else current_date-6 end);
select d,kind from erp.pocket_log;
rollback;
