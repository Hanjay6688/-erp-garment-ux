\set QUIET 1
\pset footer off
-- Pocket fabric (kain kantong) recost on the invoice path: the PO's pocket allocation for the period d-6..d-1 is posted at
-- the period end d-1; lot 10 pcs QC d-3; old HPP 12.00/pc (pocket part 4.00), new 11.00 (pocket part 3.00, rebuilt in this
-- statement). E = d-4. Expected: FG -10.00 on d-1 (the pocket allocation day), not on the lot day d-3.
begin;
\ir common_lot.sql
update erp.hpp_versions set calculated_at=now()+interval '1 hour' where is_current;
insert into erp.hpp_version_components(hpp_version_id,component_type,total_cost,source_type)
 select id,'OTHER',case when is_current then 30 else 40 end,'POCKET_PERIOD_ALLOCATION' from erp.hpp_versions;
insert into erp.pocket_periods values('00000000-0000-0000-0000-00000000f001',current_date-6,current_date-1);
insert into erp.pocket_period_destinations(pool_id,po_id) values('00000000-0000-0000-0000-00000000f001','00000000-0000-0000-0000-0000000000a0');
insert into erp.po_hpp_gl_state values('00000000-0000-0000-0000-0000000000a0',10,120,120,0,0,now()-interval '1 hour');
select erp.sync_po_hpp_to_gl('00000000-0000-0000-0000-0000000000a0',current_date-4);
select * from public.show();
rollback;
