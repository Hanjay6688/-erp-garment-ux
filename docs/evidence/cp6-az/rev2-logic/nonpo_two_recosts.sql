\set QUIET 1
\pset footer off
-- Opening lot b1 (product c1) 10 pcs at 10.00 since cutover d-20. Sold 9 on d-3, 1 on d-1 (at 10.00, before the invoice).
-- One late invoice (E=d-5, open) with two lines that are both cost origins of this opening item: recost +5.00/pc then +1.00/pc,
-- each: new HPP version + OPENING_HPP_SOURCE FG leg on E + erp.sync_non_po_product_hpp_to_gl_v2620f (same statement), then the
-- opening lot state (what the opening-lot sync posted) as erp.sync_opening_lot_hpp_to_gl writes it after that call.
-- (Independent review of AZ rev2 (3), reviewer repro n1.) Expected (open): COGS +50 on d-3... per sale day, no swing.
begin;
insert into erp.settings values('E',(current_date-5)::text);
update erp.accounting_period_control set closed_through=case when :'mode'='closed' then current_date-5 end;
insert into erp.fg_lots(id,product_id,po_id,lot_origin) values('00000000-0000-0000-0000-0000000000b1','00000000-0000-0000-0000-0000000000c1',null,'OPENING');
insert into erp.opening_lot_hpp_gl_state values('00000000-0000-0000-0000-0000000000b1',10);
insert into erp.hpp_versions(lot_id,version_no,qty_basis_pcs,total_cost,is_current,calculated_at) values
 ('00000000-0000-0000-0000-0000000000b1',1,10,100,true,now()-interval '20 day');
insert into erp.fg_stock_movements(lot_id,movement_type,qty_signed,physical_at) values
 ('00000000-0000-0000-0000-0000000000b1','OPENING',10,(current_date-20)+time '08:00'),
 ('00000000-0000-0000-0000-0000000000b1','SALE',-9,((current_date-3)+time '10:00') at time zone 'Asia/Jakarta'),
 ('00000000-0000-0000-0000-0000000000b1','SALE',-1,((current_date-1)+time '10:00') at time zone 'Asia/Jakarta');
-- pre-existing book: cutover FG +100, sales at 10.00
select erp.post_journal('CUTOVER',gen_random_uuid(),current_date-20,'x','[{"mapping_key":"FG_INVENTORY","debit":100,"credit":0},{"mapping_key":"OPENING_EQUITY","debit":0,"credit":100}]');
select erp.post_journal('SALE',gen_random_uuid(),current_date-3,'x','[{"mapping_key":"FG_INVENTORY","debit":0,"credit":90},{"mapping_key":"COGS","debit":90,"credit":0}]');
select erp.post_journal('SALE',gen_random_uuid(),current_date-1,'x','[{"mapping_key":"FG_INVENTORY","debit":0,"credit":10},{"mapping_key":"COGS","debit":10,"credit":0}]');
create function pg_temp.recost(p numeric) returns void language plpgsql as $f$
declare v int; b_fg numeric; b_cogs numeric; b_hpp numeric;
begin
 select max(version_no) into v from erp.hpp_versions;
 update erp.hpp_versions set is_current=false;
 insert into erp.hpp_versions(lot_id,version_no,qty_basis_pcs,total_cost,is_current,calculated_at)
  select lot_id,v+1,10,total_cost+10*p,true,statement_timestamp() from erp.hpp_versions where version_no=v;
 perform erp.post_journal('OPENING_HPP_SOURCE_V2620G',gen_random_uuid(),current_date-5,'x',jsonb_build_array(
  jsonb_build_object('mapping_key','FG_INVENTORY','debit',greatest(10*p,0),'credit',greatest(-10*p,0)),
  jsonb_build_object('mapping_key','OPENING_EQUITY','debit',greatest(-10*p,0),'credit',greatest(10*p,0))));
 -- book from the ledger, target from the current HPP (all 10 pcs sold)
 select sum(case when l.mapping_key='FG_INVENTORY' then l.debit-l.credit else 0 end),sum(case when l.mapping_key='COGS' then l.debit-l.credit else 0 end)
  into b_fg,b_cogs from erp.journal_lines l;
 select total_cost into b_hpp from erp.hpp_versions where is_current;
 delete from erp.tb; insert into erp.tb values('b',b_hpp,b_fg,b_cogs,0),('t',b_hpp,0,b_hpp,0);
 perform erp.sync_non_po_product_hpp_to_gl_v2620f('00000000-0000-0000-0000-0000000000c1',current_date-5,'TEST',gen_random_uuid(),'probe');
 update erp.opening_lot_hpp_gl_state set current_hpp=b_hpp/10;
end $f$;
select pg_temp.recost(5), pg_temp.recost(1);
select d,sum(amt) filter(where k='FG_INVENTORY') fg,sum(amt) filter(where k='COGS') cogs,
 sum(sum(amt) filter(where k='FG_INVENTORY')) over(order by d) fg_balance from public.jl group by d order by d;
rollback;
