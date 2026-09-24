\set QUIET 1
\pset footer off
-- Variant: one pool P1 only; the pocket recost is followed in the same statement by another rebuild+sync.
-- PO a0, lot b1 10 pcs QC d-6 (all pieces in FG; the PO's WIP is 0 after QC). Pocket pools P1 (d-10..d-5) and P2 (d-4..d-2)
-- both allocate to a0, 20.00 each (HPP 12.00/pc: pocket part 4.00). One late invoice (E=d-8, open) lowers the pocket fabric
-- used in both periods: in ONE statement guard_pocket_period_v1 fires per pool: P1 recost (-5.00: AZ rev2 WIP credit on d-5,
-- rebuild 11.50, AY sync), then P2 recost (-5.00: WIP credit on d-2, rebuild 11.00, AY sync).
-- Expected (owner rule): P1 part leaves WIP no earlier than it entered (d-5), P2 part on d-2; per-PO WIP never < 0.
begin;
\set old 12
\set new 12
\ir ../harness/scenarios/common_lot.sql
update erp.settings set v=(current_date-8)::text where k='E';
update erp.fg_lots set produced_at=((current_date-6)+time '13:00') at time zone 'Asia/Jakarta';
update erp.fg_stock_movements set physical_at=((current_date-6)+time '13:00') at time zone 'Asia/Jakarta';
update erp.hpp_versions set calculated_at=now()-interval '2 day';
delete from erp.hpp_versions where is_current; update erp.hpp_versions set is_current=true;
insert into erp.hpp_version_components(hpp_version_id,component_type,total_cost,source_type) select id,'OTHER',40,'POCKET_PERIOD_ALLOCATION' from erp.hpp_versions;
insert into erp.pocket_periods values('00000000-0000-0000-0000-00000000f001',current_date-10,current_date-5);
insert into erp.pocket_period_destinations(pool_id,po_id) values('00000000-0000-0000-0000-00000000f001','00000000-0000-0000-0000-0000000000a0');
update erp.po_hpp_gl_lot_state_v1 set hpp_per_pcs=12, updated_at=now()-interval '1 day';
insert into erp.po_hpp_gl_state values('00000000-0000-0000-0000-0000000000a0',10,120,120,0,0,now()-interval '1 day');
create function pg_temp.pool_recost(p_day date) returns void language plpgsql as $f$
declare v uuid;
begin
 -- AZ rev2 pocket recost journal: WIP|a0 credit 5.00 on the pool's end day
 perform erp.post_journal('POCKET_HPP_PERIOD',gen_random_uuid(),p_day,'x','[{"mapping_key":"WIP","debit":0,"credit":5,"po_id":"00000000-0000-0000-0000-0000000000a0"},{"mapping_key":"OTHER_EXPENSE","debit":5,"credit":0}]');
 -- rebuild_po_hpp: new current version, pocket component -5.00
 update erp.hpp_versions set is_current=false where is_current returning id into v;
 insert into erp.hpp_versions(id,lot_id,version_no,qty_basis_pcs,total_cost,is_current,calculated_at)
  select gen_random_uuid(),lot_id,version_no+1,10,total_cost-5,true,statement_timestamp() from erp.hpp_versions where id=v;
 insert into erp.hpp_version_components(hpp_version_id,component_type,total_cost,source_type)
  select h.id,'OTHER',(select total_cost from erp.hpp_version_components where hpp_version_id=v)-5,'POCKET_PERIOD_ALLOCATION' from erp.hpp_versions h where h.is_current;
 perform erp.sync_po_hpp_to_gl('00000000-0000-0000-0000-0000000000a0',p_day);
end $f$;
create function pg_temp.other_rebuild() returns void language plpgsql as $f$
declare v uuid;
begin
 -- same statement: a second rebuild of the PO for a non-pocket change (-1.00 total, e.g. another invoice line), then sync
 update erp.hpp_versions set is_current=false where is_current returning id into v;
 insert into erp.hpp_versions(id,lot_id,version_no,qty_basis_pcs,total_cost,is_current,calculated_at)
  select gen_random_uuid(),lot_id,version_no+1,10,total_cost-1,true,statement_timestamp() from erp.hpp_versions where id=v;
 insert into erp.hpp_version_components(hpp_version_id,component_type,total_cost,source_type)
  select h.id,'OTHER',(select total_cost from erp.hpp_version_components where hpp_version_id=v),'POCKET_PERIOD_ALLOCATION' from erp.hpp_versions h where h.is_current;
 perform erp.sync_po_hpp_to_gl('00000000-0000-0000-0000-0000000000a0',current_date-8);
end $f$;
select pg_temp.pool_recost(current_date-5), pg_temp.other_rebuild();
select d,fg,wip,cum_fg,cum_wip as po_wip_balance from public.show();
select po_id is not null, sum(debit-credit) from erp.journal_lines where mapping_key='FG_INVENTORY' group by 1;
rollback;
