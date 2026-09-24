\set QUIET 1
\pset footer off
-- Accessory recost of an accrued lot: snapshot 10 pcs at 2.00 -> 2.20 (+2.00); lot produced d-2; E = d-5. Expected: one
-- ACCESSORY_HPP_RECOST journal WIP +2.00 / ACCESSORY_REIMBURSE_VARIANCE -2.00 on d-2 (open), d-5 (closed), today (no invoice).
begin;
insert into erp.settings values('E',(current_date-5)::text);
update erp.accounting_period_control set closed_through=case when :'mode'='closed' then current_date-5 end;
delete from erp.settings where k='E' and :'mode'='noninv';
insert into erp.materials values('00000000-0000-0000-0000-0000000000ac','ACCESSORY','00000000-0000-0000-0000-0000000000ca');
insert into erp.fg_lots values('00000000-0000-0000-0000-0000000000b1','00000000-0000-0000-0000-0000000000c1','00000000-0000-0000-0000-0000000000a0','PRODUCTION',((current_date-2)+time '13:00') at time zone 'Asia/Jakarta');
insert into erp.fg_accessory_cost_snapshots values('00000000-0000-0000-0000-0000000000f5','00000000-0000-0000-0000-0000000000ca','CATEGORY_MOVING_AVG',now()-interval '3 day',2,2,'00000000-0000-0000-0000-0000000000a0','00000000-0000-0000-0000-0000000000b1',10);
insert into erp.journal_entries(source_type,source_id,transaction_date) values('ACCESSORY_REIMBURSE_ACCRUAL','00000000-0000-0000-0000-0000000000b1',current_date-2);
select erp.refresh_accessory_hpp_after_material_recost('00000000-0000-0000-0000-0000000000ac','probe');
select j.source_type,j.transaction_date,l.mapping_key,l.debit,l.credit from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id order by 1,2,3;
rollback;
