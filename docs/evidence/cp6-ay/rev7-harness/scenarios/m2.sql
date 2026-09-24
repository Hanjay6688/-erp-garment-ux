begin;
insert into erp.settings values('E',(current_date-3)::text);
insert into erp.cutting_groups values
 ('00000000-0000-0000-0000-0000000000a1','00000000-0000-0000-0000-0000000000a0','00000000-0000-0000-0000-0000000000bb',((current_date-2)+time '08:00') at time zone 'Asia/Jakarta'),
 ('00000000-0000-0000-0000-0000000000a2','00000000-0000-0000-0000-0000000000a0','00000000-0000-0000-0000-0000000000bb',((current_date-1)+time '08:00') at time zone 'Asia/Jakarta');
insert into erp.v_cutting_group_totals values('00000000-0000-0000-0000-0000000000a1',8),('00000000-0000-0000-0000-0000000000a2',3);
insert into erp.v_cutting_batch_totals values('00000000-0000-0000-0000-0000000000bb',11);
insert into erp.material_stock_movements(id,source_id,source_type,qty_signed,unit_cost_snapshot,physical_at) values
 ('00000000-0000-0000-0000-0000000000e1','00000000-0000-0000-0000-0000000000a1','CUTTING_GROUP',-4,10.70,((current_date-2)+time '08:00') at time zone 'Asia/Jakarta'),
 ('00000000-0000-0000-0000-0000000000e2','00000000-0000-0000-0000-0000000000a2','CUTTING_GROUP',-6,10.70,((current_date-1)+time '08:00') at time zone 'Asia/Jakarta');
insert into erp.fg_lots values
 ('00000000-0000-0000-0000-0000000000b1','00000000-0000-0000-0000-0000000000a0','PRODUCTION',8,((current_date-2)+time '13:00') at time zone 'Asia/Jakarta','00000000-0000-0000-0000-0000000000a1',null,null),
 ('00000000-0000-0000-0000-0000000000b2','00000000-0000-0000-0000-0000000000a0','PRODUCTION',3,((current_date-1)+time '13:00') at time zone 'Asia/Jakarta','00000000-0000-0000-0000-0000000000a2',null,null);
insert into erp.hpp_versions(lot_id,version_no,qty_basis_pcs,total_cost,is_current,calculated_at) values
 ('00000000-0000-0000-0000-0000000000b1',1,8,800.0/11,false,now()-interval '2 hour'),('00000000-0000-0000-0000-0000000000b1',2,8,856.0/11,true,now()),
 ('00000000-0000-0000-0000-0000000000b2',1,3,300.0/11,false,now()-interval '2 hour'),('00000000-0000-0000-0000-0000000000b2',2,3,321.0/11,true,now());
insert into erp.fg_stock_movements(lot_id,movement_type,qty_signed,physical_at) values
 ('00000000-0000-0000-0000-0000000000b1','QC_GOOD',8,((current_date-2)+time '13:00') at time zone 'Asia/Jakarta'),
 ('00000000-0000-0000-0000-0000000000b2','QC_GOOD',3,((current_date-1)+time '13:00') at time zone 'Asia/Jakarta');
insert into erp.po_hpp_gl_state values('00000000-0000-0000-0000-0000000000a0',11,100,100,0,0,now()-interval '1 hour');
insert into erp.po_hpp_gl_lot_state_v1 values('00000000-0000-0000-0000-0000000000b1','00000000-0000-0000-0000-0000000000a0',100.0/11,now()-interval '1 hour'),
 ('00000000-0000-0000-0000-0000000000b2','00000000-0000-0000-0000-0000000000a0',100.0/11,now()-interval '1 hour');
insert into erp.po_hpp_gl_material_state_v1 values('00000000-0000-0000-0000-0000000000a0','M:00000000-0000-0000-0000-0000000000e1',40,now()-interval '1 hour'),
 ('00000000-0000-0000-0000-0000000000a0','M:00000000-0000-0000-0000-0000000000e2',60,now()-interval '1 hour');
select erp.sync_po_hpp_to_gl('00000000-0000-0000-0000-0000000000a0',current_date-3);
select j.transaction_date d,l.mapping_key k,sum(l.debit-l.credit) amt from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id group by 1,2 order by 1,2;
select * from erp.po_hpp_gl_material_state_v1 order by 2;
rollback;
