\set QUIET 1
\pset footer off
-- Posted relabel (child keeps HPP 10.00, not revalued), child revalued with its source (10.00 -> 8.25). Expected: d-3 FG -17.50 only; the relabel moves pieces between lots at the same correction, no other-account line: 4 of 10 pcs relabelled to child lot c on d-2, conversion reversed today (child not revalued: conversion REVERSED)
begin;
\ir common_lot.sql
insert into erp.fg_lots values('00000000-0000-0000-0000-0000000000cc','00000000-0000-0000-0000-0000000000a0','CONVERSION',4,((current_date-2)+time '10:00') at time zone 'Asia/Jakarta',null,null,null);
insert into erp.hpp_versions(lot_id,version_no,qty_basis_pcs,total_cost,is_current,calculated_at) values('00000000-0000-0000-0000-0000000000cc',1,4,40,false,now()-interval '90 minutes'),('00000000-0000-0000-0000-0000000000cc',2,4,33,true,now());
insert into erp.fg_stock_movements(id,lot_id,movement_type,qty_signed,physical_at,reversal_of_id) values
 ('00000000-0000-0000-0000-0000000000e1','00000000-0000-0000-0000-0000000000b1','REBRAND_OUT',-4,((current_date-2)+time '10:00') at time zone 'Asia/Jakarta',null),
 ('00000000-0000-0000-0000-0000000000e2','00000000-0000-0000-0000-0000000000cc','REBRAND_IN',4,((current_date-2)+time '10:00') at time zone 'Asia/Jakarta',null);
insert into erp.product_conversions values('00000000-0000-0000-0000-0000000000cf','POSTED');
insert into erp.product_conversion_allocations(conversion_id,source_lot_id,destination_lot_id) values('00000000-0000-0000-0000-0000000000cf','00000000-0000-0000-0000-0000000000b1','00000000-0000-0000-0000-0000000000cc');
insert into erp.po_hpp_gl_lot_state_v1 values('00000000-0000-0000-0000-0000000000cc','00000000-0000-0000-0000-0000000000a0',10,now()-interval '1 hour');
insert into erp.po_hpp_gl_state values('00000000-0000-0000-0000-0000000000a0',10,100,100,0,0,now()-interval '1 hour');
select * from erp.compute_po_hpp_gl_targets_v2620d('00000000-0000-0000-0000-0000000000a0');
select erp.sync_po_hpp_to_gl('00000000-0000-0000-0000-0000000000a0',current_date-4);
select * from public.show();
rollback;
