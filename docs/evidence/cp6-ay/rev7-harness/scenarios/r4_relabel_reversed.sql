\set QUIET 1
\pset footer off
-- F6 (expected rev7: no other-account line; FG -17.50 on d-3 only): 4 of 10 pcs relabelled to child lot c on d-2, conversion reversed today (child not revalued: conversion REVERSED)
begin;
\ir common_lot.sql
insert into erp.fg_lots values('00000000-0000-0000-0000-0000000000cc','00000000-0000-0000-0000-0000000000a0','CONVERSION',4,((current_date-2)+time '10:00') at time zone 'Asia/Jakarta',null,null,null);
insert into erp.hpp_versions(lot_id,version_no,qty_basis_pcs,total_cost,is_current,calculated_at) values('00000000-0000-0000-0000-0000000000cc',1,4,40,true,now()-interval '90 minutes');
insert into erp.fg_stock_movements(id,lot_id,movement_type,qty_signed,physical_at,reversal_of_id) values
 ('00000000-0000-0000-0000-0000000000e1','00000000-0000-0000-0000-0000000000b1','REBRAND_OUT',-4,((current_date-2)+time '10:00') at time zone 'Asia/Jakarta',null),
 ('00000000-0000-0000-0000-0000000000e2','00000000-0000-0000-0000-0000000000cc','REBRAND_IN',4,((current_date-2)+time '10:00') at time zone 'Asia/Jakarta',null),
 ('00000000-0000-0000-0000-0000000000e3','00000000-0000-0000-0000-0000000000cc','REVERSAL',-4,now(),'00000000-0000-0000-0000-0000000000e2'),
 ('00000000-0000-0000-0000-0000000000e4','00000000-0000-0000-0000-0000000000b1','REVERSAL',4,now(),'00000000-0000-0000-0000-0000000000e1');
insert into erp.product_conversions values('00000000-0000-0000-0000-0000000000cf','REVERSED');
insert into erp.product_conversion_allocations(conversion_id,source_lot_id,destination_lot_id) values('00000000-0000-0000-0000-0000000000cf','00000000-0000-0000-0000-0000000000b1','00000000-0000-0000-0000-0000000000cc');
insert into erp.po_hpp_gl_lot_state_v1 values('00000000-0000-0000-0000-0000000000cc','00000000-0000-0000-0000-0000000000a0',10,now()-interval '1 hour');
insert into erp.po_hpp_gl_state values('00000000-0000-0000-0000-0000000000a0',10,100,100,0,0,now()-interval '1 hour');
select erp.sync_po_hpp_to_gl('00000000-0000-0000-0000-0000000000a0',current_date-4);
select * from public.show();
rollback;
