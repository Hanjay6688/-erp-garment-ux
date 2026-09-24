\set QUIET 1
\pset footer off
-- Pocket fabric (kain kantong) recost on the invoice path: the PO's pocket pool P (period d-6..d-1) is allocated at its period
-- end d-1; lot 10 pcs QC d-3; old HPP 12.00/pc (pocket part 40 for the lot), new 11.00 (pocket 30). E = d-4.
-- Expected: FG -10.00 on d-1 (the pool's allocation/recost day), not on the lot day d-3.
begin;
\ir common_lot.sql
insert into erp.pocket_periods values('00000000-0000-0000-0000-00000000f001',current_date-6,current_date-1);
update erp.po_hpp_gl_lot_state_v1 set pocket_by_pool='{"00000000-0000-0000-0000-00000000f001":40}';
insert into erp.stub_pocket_by_pool values('00000000-0000-0000-0000-0000000000b1','00000000-0000-0000-0000-00000000f001',30);
insert into erp.po_hpp_gl_state values('00000000-0000-0000-0000-0000000000a0',10,120,120,0,0,now()-interval '1 hour');
select erp.sync_po_hpp_to_gl('00000000-0000-0000-0000-0000000000a0',current_date-1);
select * from public.show();
select pocket_by_pool from erp.po_hpp_gl_lot_state_v1;
rollback;
