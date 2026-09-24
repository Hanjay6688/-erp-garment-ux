\set QUIET 1
\pset footer off
-- Opening WIP/BS: source value 100 -> 90 for 10 pcs (BS case of 10 pcs); 2 pcs disposed on d-4 (before E? no: E=d-5) and 3
-- pcs on d-1; prior posted value 50 (5 pcs x 10). Target 45 -> delta -5. Expected (open E): d-4 -2.00, d-1 -3.00.
begin;
insert into erp.settings values('E',(current_date-5)::text),('SRCV','90');
update erp.accounting_period_control set closed_through=case when :'mode'='closed' then current_date-5 end;
delete from erp.settings where k='E' and :'mode'='noninv';
insert into erp.initial_import_production_sources values('00000000-0000-0000-0000-0000000000e1','00000000-0000-0000-0000-0000000000a0','00000000-0000-0000-0000-0000000000cb',10);
insert into erp.bs_resolutions(bs_case_id,qty_pcs,physical_at,resolution_type) values
 ('00000000-0000-0000-0000-0000000000cb',2,((current_date-4)+time '10:00') at time zone 'Asia/Jakarta','SOLD'),
 ('00000000-0000-0000-0000-0000000000cb',3,((current_date-1)+time '10:00') at time zone 'Asia/Jakarta','SOLD'),
 ('00000000-0000-0000-0000-0000000000cb',4,((current_date-1)+time '11:00') at time zone 'Asia/Jakarta','REWORK_SEWING');
insert into erp.initial_import_bs_value_events values(gen_random_uuid(),'00000000-0000-0000-0000-0000000000e1',5,0,50,current_date-1,null,null);
select erp.sync_initial_import_bs_value_v1('00000000-0000-0000-0000-0000000000e1',current_date-5);
select * from public.jl;
select economic_date,disposed_qty,previous_amount,target_amount from erp.initial_import_bs_value_events order by previous_amount,economic_date;
rollback;
