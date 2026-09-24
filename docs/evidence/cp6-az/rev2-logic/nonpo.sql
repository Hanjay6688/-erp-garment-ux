\set QUIET 1
\pset footer off
-- Non-PO opening lot: 10 pcs, HPP 10.00 -> 9.00 (rebuilt in this statement). Adjustment -2 on d-3, sale 3 on d-2, return 1 on
-- d-1. E = d-5 (open). Book (after the opening source leg): FG 50, COGS 20, other 20; targets FG 54, COGS 18, other 18.
-- Expected: d-3 other -2 / FG +2; d-2 COGS -3 / FG +3; d-1 COGS +1 / FG -1. Closed E / no invoice: one journal on the date.
begin;
insert into erp.settings values('E',(current_date-5)::text);
update erp.accounting_period_control set closed_through=case when :'mode'='closed' then current_date-5 end;
delete from erp.settings where k='E' and :'mode'='noninv';
insert into erp.fg_lots values('00000000-0000-0000-0000-0000000000b1','00000000-0000-0000-0000-0000000000c1',null,'OPENING');
insert into erp.hpp_versions(lot_id,version_no,qty_basis_pcs,total_cost,is_current,calculated_at) values
 ('00000000-0000-0000-0000-0000000000b1',1,10,100,false,now()-interval '2 day'),('00000000-0000-0000-0000-0000000000b1',2,10,90,true,now()+interval '1 hour');
insert into erp.fg_stock_movements(lot_id,movement_type,qty_signed,physical_at) values
 ('00000000-0000-0000-0000-0000000000b1','OPENING',10,(current_date-10)+time '08:00'),
 ('00000000-0000-0000-0000-0000000000b1','ADJUSTMENT',-2,((current_date-3)+time '10:00') at time zone 'Asia/Jakarta'),
 ('00000000-0000-0000-0000-0000000000b1','SALE',-3,((current_date-2)+time '10:00') at time zone 'Asia/Jakarta'),
 ('00000000-0000-0000-0000-0000000000b1','SALE_RETURN',1,((current_date-1)+time '10:00') at time zone 'Asia/Jakarta');
insert into erp.tb values('b',90,50,20,20),('t',90,54,18,18);
select erp.sync_non_po_product_hpp_to_gl_v2620f('00000000-0000-0000-0000-0000000000c1',current_date-5,'TEST',gen_random_uuid(),'probe');
select * from public.jl;
select effective_date,fg_delta,cogs_delta,other_delta from erp.non_po_hpp_gl_sync_events_v2620f order by 1;
rollback;
