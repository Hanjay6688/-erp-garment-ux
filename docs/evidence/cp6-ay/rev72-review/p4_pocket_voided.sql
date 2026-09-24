\set QUIET 1
\pset footer off
-- Group a1: live lot b1 10 pcs QC d-3; voided lot v1 10 pcs QC d-6, QC reversed d-5. Pocket pool d-10..d-2 allocates to a0;
-- late invoice (E=d-8, open) raises the pocket fabric: b1 HPP 12.00 -> 13.00 (pocket part +1.00/pc, rebuilt in this statement).
-- AZ rev2: pocket recost WIP +10.00 on d-2. Expected AY: FG +10 on d-2 only (no pocket correction before d-2).
begin;
insert into erp.settings values('E',(current_date-8)::text);
insert into erp.cutting_groups values('00000000-0000-0000-0000-0000000000a1','00000000-0000-0000-0000-0000000000a0',null,((current_date-9)+time '08:00') at time zone 'Asia/Jakarta');
insert into erp.v_cutting_group_totals values('00000000-0000-0000-0000-0000000000a1',20);
insert into erp.fg_lots values
 ('00000000-0000-0000-0000-0000000000b1','00000000-0000-0000-0000-0000000000a0','PRODUCTION',10,((current_date-3)+time '13:00') at time zone 'Asia/Jakarta','00000000-0000-0000-0000-0000000000a1',null,null),
 ('00000000-0000-0000-0000-0000000000b9','00000000-0000-0000-0000-0000000000a0','VOIDED_PRODUCTION',10,((current_date-6)+time '13:00') at time zone 'Asia/Jakarta','00000000-0000-0000-0000-0000000000a1',null,null);
insert into erp.hpp_versions(id,lot_id,version_no,qty_basis_pcs,total_cost,is_current,calculated_at) values
 ('00000000-0000-0000-0000-00000000aa01','00000000-0000-0000-0000-0000000000b1',1,10,120,false,now()-interval '2 day'),
 ('00000000-0000-0000-0000-00000000aa02','00000000-0000-0000-0000-0000000000b1',2,10,130,true,now()+interval '1 hour'),
 ('00000000-0000-0000-0000-00000000aa03','00000000-0000-0000-0000-0000000000b9',1,10,120,true,now()-interval '3 day');
insert into erp.hpp_version_components(hpp_version_id,component_type,total_cost,source_type) values
 ('00000000-0000-0000-0000-00000000aa01','OTHER',40,'POCKET_PERIOD_ALLOCATION'),('00000000-0000-0000-0000-00000000aa02','OTHER',50,'POCKET_PERIOD_ALLOCATION');
insert into erp.fg_stock_movements(id,lot_id,movement_type,qty_signed,physical_at,reversal_of_id) values
 ('00000000-0000-0000-0000-0000000000c1','00000000-0000-0000-0000-0000000000b1','QC_GOOD',10,((current_date-3)+time '13:00') at time zone 'Asia/Jakarta',null),
 ('00000000-0000-0000-0000-0000000000c8','00000000-0000-0000-0000-0000000000b9','QC_GOOD',10,((current_date-6)+time '13:00') at time zone 'Asia/Jakarta',null),
 ('00000000-0000-0000-0000-0000000000c9','00000000-0000-0000-0000-0000000000b9','REVERSAL',-10,((current_date-5)+time '13:00') at time zone 'Asia/Jakarta','00000000-0000-0000-0000-0000000000c8');
insert into erp.pocket_periods values('00000000-0000-0000-0000-00000000f001',current_date-10,current_date-2);
insert into erp.pocket_period_destinations(pool_id,po_id) values('00000000-0000-0000-0000-00000000f001','00000000-0000-0000-0000-0000000000a0');
insert into erp.po_hpp_gl_state values('00000000-0000-0000-0000-0000000000a0',10,120,120,0,0,now()-interval '1 day');
insert into erp.po_hpp_gl_lot_state_v1 values('00000000-0000-0000-0000-0000000000b1','00000000-0000-0000-0000-0000000000a0',12,now()-interval '1 day'),('00000000-0000-0000-0000-0000000000b9','00000000-0000-0000-0000-0000000000a0',12,now()-interval '1 day');
select erp.sync_po_hpp_to_gl('00000000-0000-0000-0000-0000000000a0',current_date-8);
select d,fg,wip,cum_fg,cum_wip,cum_wip+case when d>=current_date-2 then 10 else 0 end po_wip_with_az_pocket from public.show();
rollback;
