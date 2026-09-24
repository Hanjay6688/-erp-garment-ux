\set QUIET 1
\pset footer off
-- Independent review of rev7.2 (5; reviewer repro p4): group a1 has a live lot b2 (10 pcs, QC d-3) and a voided lot b1 (QC d-6,
-- reversed d-5). Pool P (d-4..d-2) pocket for b2 40 -> 30 (-1.00/pc; b2 HPP 12 -> 11); b1 copies the live lots' change.
-- Expected: no pocket correction of either lot before the pool day d-2; FG -10.00 (b2) on d-2.
begin;
\set old 12
\set new 11
insert into erp.settings values('E',(current_date-8)::text);
insert into erp.cutting_groups values('00000000-0000-0000-0000-0000000000a1','00000000-0000-0000-0000-0000000000a0',null,((current_date-7)+time '08:00') at time zone 'Asia/Jakarta');
insert into erp.v_cutting_group_totals values('00000000-0000-0000-0000-0000000000a1',20);
insert into erp.fg_lots values
 ('00000000-0000-0000-0000-0000000000b1','00000000-0000-0000-0000-0000000000a0','VOIDED_PRODUCTION',10,((current_date-6)+time '13:00') at time zone 'Asia/Jakarta','00000000-0000-0000-0000-0000000000a1',null,null),
 ('00000000-0000-0000-0000-0000000000b2','00000000-0000-0000-0000-0000000000a0','PRODUCTION',10,((current_date-3)+time '13:00') at time zone 'Asia/Jakarta','00000000-0000-0000-0000-0000000000a1',null,null);
insert into erp.hpp_versions(lot_id,version_no,qty_basis_pcs,total_cost,is_current,calculated_at) values
 ('00000000-0000-0000-0000-0000000000b1',1,10,120,true,now()-interval '3 day'),
 ('00000000-0000-0000-0000-0000000000b2',1,10,120,false,now()-interval '2 hour'),('00000000-0000-0000-0000-0000000000b2',2,10,110,true,now());
insert into erp.fg_stock_movements(id,lot_id,movement_type,qty_signed,physical_at,reversal_of_id) values
 ('00000000-0000-0000-0000-0000000000c1','00000000-0000-0000-0000-0000000000b1','QC_GOOD',10,((current_date-6)+time '13:00') at time zone 'Asia/Jakarta',null),
 ('00000000-0000-0000-0000-0000000000c2','00000000-0000-0000-0000-0000000000b1','REVERSAL',-10,((current_date-5)+time '13:00') at time zone 'Asia/Jakarta','00000000-0000-0000-0000-0000000000c1'),
 ('00000000-0000-0000-0000-0000000000c3','00000000-0000-0000-0000-0000000000b2','QC_GOOD',10,((current_date-3)+time '13:00') at time zone 'Asia/Jakarta',null);
insert into erp.pocket_periods values('00000000-0000-0000-0000-00000000f001',current_date-4,current_date-2);
insert into erp.po_hpp_gl_lot_state_v1 values
 ('00000000-0000-0000-0000-0000000000b1','00000000-0000-0000-0000-0000000000a0',12,now()-interval '1 hour','{}'),
 ('00000000-0000-0000-0000-0000000000b2','00000000-0000-0000-0000-0000000000a0',12,now()-interval '1 hour','{"00000000-0000-0000-0000-00000000f001":40}');
insert into erp.stub_pocket_by_pool values('00000000-0000-0000-0000-0000000000b2','00000000-0000-0000-0000-00000000f001',30);
insert into erp.po_hpp_gl_state values('00000000-0000-0000-0000-0000000000a0',10,120,120,0,0,now()-interval '1 hour');
select erp.sync_po_hpp_to_gl('00000000-0000-0000-0000-0000000000a0',current_date-2);
select d,fg,wip,cum_fg,cum_wip from public.show();
rollback;
