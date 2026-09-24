\set QUIET 1
\pset footer off
-- Independent review of rev7.2 (1, 2; reviewer repro p6, realistic order): lot b1 10 pcs QC d-6; pools P1 (d-10..d-5) and P2
-- (d-4..d-2) each 20 of pocket for the lot; HPP 12.00/pc. One late invoice (E=d-8) lowers the pocket fabric of both periods;
-- the core updates both first, so the sync of P1's recost (caller d-5) already sees P1 and P2 (-5 each); the sync of P2's
-- recost (caller d-2) sees nothing new. AZ rev2 recost journals: WIP|PO -5 on d-5 (P1) and -5 on d-2 (P2).
-- Expected AY: FG -5 on d-5 and -5 on d-2; the second sync posts nothing; per-PO WIP (with the pocket journals) 0 every day.
begin;
\set old 12
\set new 12
\ir common_lot.sql
update erp.settings set v=(current_date-8)::text where k='E';
update erp.fg_stock_movements set physical_at=((current_date-6)+time '13:00') at time zone 'Asia/Jakarta';
delete from erp.hpp_versions where is_current; update erp.hpp_versions set is_current=true,calculated_at=now()-interval '2 day';
insert into erp.pocket_periods values('00000000-0000-0000-0000-00000000f001',current_date-10,current_date-5),('00000000-0000-0000-0000-00000000f002',current_date-4,current_date-2);
update erp.po_hpp_gl_lot_state_v1 set hpp_per_pcs=12,updated_at=now()-interval '1 day',
 pocket_by_pool='{"00000000-0000-0000-0000-00000000f001":20,"00000000-0000-0000-0000-00000000f002":20}';
insert into erp.po_hpp_gl_state values('00000000-0000-0000-0000-0000000000a0',10,120,120,0,0,now()-interval '1 day');
insert into erp.stub_pocket_by_pool values('00000000-0000-0000-0000-0000000000b1','00000000-0000-0000-0000-00000000f001',15),('00000000-0000-0000-0000-0000000000b1','00000000-0000-0000-0000-00000000f002',15);
-- the core's rebuild: HPP 11.00 (both pools lowered)
update erp.hpp_versions set is_current=false;
insert into erp.hpp_versions(lot_id,version_no,qty_basis_pcs,total_cost,is_current,calculated_at) values('00000000-0000-0000-0000-0000000000b1',9,10,110,true,now());
select erp.post_journal('POCKET_HPP_PERIOD',gen_random_uuid(),current_date-5,'P1','[{"mapping_key":"WIP","debit":0,"credit":5,"po_id":"00000000-0000-0000-0000-0000000000a0"},{"mapping_key":"OTHER_EXPENSE","debit":5,"credit":0}]');
select erp.sync_po_hpp_to_gl('00000000-0000-0000-0000-0000000000a0',current_date-5);
select erp.post_journal('POCKET_HPP_PERIOD',gen_random_uuid(),current_date-2,'P2','[{"mapping_key":"WIP","debit":0,"credit":5,"po_id":"00000000-0000-0000-0000-0000000000a0"},{"mapping_key":"OTHER_EXPENSE","debit":5,"credit":0}]');
select erp.sync_po_hpp_to_gl('00000000-0000-0000-0000-0000000000a0',current_date-2);
select d,fg,wip,cum_fg,cum_wip po_wip_balance from public.show();
rollback;
