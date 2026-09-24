\set QUIET 1
\pset footer off
-- F2: lot V (10) QC d-3, QC reversed d-2 (lot VOIDED), redo lot b2 QC d-1. AZ puts WIP -17.50 on d-4 (cut).
begin;
insert into erp.settings values('E',(current_date-4)::text);
insert into erp.cutting_groups values('00000000-0000-0000-0000-0000000000a1','00000000-0000-0000-0000-0000000000a0',null,((current_date-4)+time '08:00') at time zone 'Asia/Jakarta');
insert into erp.fg_lots values
 ('00000000-0000-0000-0000-0000000000b1','00000000-0000-0000-0000-0000000000a0','VOIDED_PRODUCTION',10,((current_date-3)+time '13:00') at time zone 'Asia/Jakarta','00000000-0000-0000-0000-0000000000a1',null,null);
insert into erp.v_cutting_group_totals values('00000000-0000-0000-0000-0000000000a1',10);
insert into erp.material_stock_movements(id,source_id,source_type,qty_signed,unit_cost_snapshot,physical_at) values('00000000-0000-0000-0000-0000000000f1','00000000-0000-0000-0000-0000000000a1','CUTTING_GROUP',-10,8.25,((current_date-4)+time '08:00') at time zone 'Asia/Jakarta');
insert into erp.po_hpp_gl_material_state_v1 values('00000000-0000-0000-0000-0000000000a0','M:00000000-0000-0000-0000-0000000000f1',100,now()-interval '1 hour');
insert into erp.hpp_versions(lot_id,version_no,qty_basis_pcs,total_cost,is_current,calculated_at) values
 ('00000000-0000-0000-0000-0000000000b1',1,10,100,true,now()-interval '3 hour'),
 ('00000000-0000-0000-0000-0000000000b2',1,10,100,false,now()-interval '2 hour'),('00000000-0000-0000-0000-0000000000b2',2,10,82.5,true,now());
insert into erp.fg_stock_movements(id,lot_id,movement_type,qty_signed,physical_at,reversal_of_id) values
 ('00000000-0000-0000-0000-0000000000c1','00000000-0000-0000-0000-0000000000b1','QC_GOOD',10,((current_date-3)+time '13:00') at time zone 'Asia/Jakarta',null),
 ('00000000-0000-0000-0000-0000000000c2','00000000-0000-0000-0000-0000000000b1','REVERSAL',-10,((current_date-2)+time '13:00') at time zone 'Asia/Jakarta','00000000-0000-0000-0000-0000000000c1');
insert into erp.po_hpp_gl_state values('00000000-0000-0000-0000-0000000000a0',0,0,0,0,0,now()-interval '1 hour');
insert into erp.po_hpp_gl_lot_state_v1 values('00000000-0000-0000-0000-0000000000b2','00000000-0000-0000-0000-0000000000a0',10,now()-interval '1 hour'),('00000000-0000-0000-0000-0000000000b1','00000000-0000-0000-0000-0000000000a0',10,now()-interval '1 hour');
select erp.sync_po_hpp_to_gl('00000000-0000-0000-0000-0000000000a0',current_date-4);
select * from public.show();
\echo 'AZ: WIP -17.50 on d-4 (cut). GL WIP of the PO: d-4 100-17.50, d-3 0-17.50 (QC moved 100 to FG), d-2 100-17.50 (QC reversed).'
rollback;
