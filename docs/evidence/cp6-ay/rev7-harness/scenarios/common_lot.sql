-- one PO a0, group a1 (not batched), lot b1 of 10 pcs QC d-3; E = d-4. :old/:new per-piece HPP
insert into erp.settings values('E',(current_date-4)::text);
insert into erp.cutting_groups values('00000000-0000-0000-0000-0000000000a1','00000000-0000-0000-0000-0000000000a0',null,((current_date-4)+time '08:00') at time zone 'Asia/Jakarta');
insert into erp.v_cutting_group_totals values('00000000-0000-0000-0000-0000000000a1',10);
insert into erp.fg_lots values('00000000-0000-0000-0000-0000000000b1','00000000-0000-0000-0000-0000000000a0','PRODUCTION',10,((current_date-3)+time '13:00') at time zone 'Asia/Jakarta','00000000-0000-0000-0000-0000000000a1',null,null);
insert into erp.hpp_versions(lot_id,version_no,qty_basis_pcs,total_cost,is_current,calculated_at) values
 ('00000000-0000-0000-0000-0000000000b1',1,10,10*(:'old')::numeric,false,now()-interval '2 hour'),('00000000-0000-0000-0000-0000000000b1',2,10,10*(:'new')::numeric,true,now());
insert into erp.fg_stock_movements(id,lot_id,movement_type,qty_signed,physical_at) values
 ('00000000-0000-0000-0000-0000000000c1','00000000-0000-0000-0000-0000000000b1','QC_GOOD',10,((current_date-3)+time '13:00') at time zone 'Asia/Jakarta');
insert into erp.po_hpp_gl_lot_state_v1 values('00000000-0000-0000-0000-0000000000b1','00000000-0000-0000-0000-0000000000a0',(:'old')::numeric,now()-interval '1 hour');
