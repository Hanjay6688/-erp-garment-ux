\set QUIET 1
\pset footer off
-- M-1: a lot without a lineage group takes the PO-wide pool (rebuild_po_hpp: PO material over the PO's production pieces).
-- Same facts as r1 (cut d-4, return d-1 after the lot). Expected: d-3 FG -17.50; d-1 FG +3.50.
begin;
\ir common_lot.sql
update erp.fg_lots set cutting_group_id=null;
insert into erp.material_stock_movements(id,source_id,source_type,qty_signed,unit_cost_snapshot,physical_at) values
 ('00000000-0000-0000-0000-0000000000f1','00000000-0000-0000-0000-0000000000a1','CUTTING_GROUP',-10,8.25,((current_date-4)+time '08:00') at time zone 'Asia/Jakarta'),
 ('00000000-0000-0000-0000-0000000000f2','00000000-0000-0000-0000-0000000000a1','CUTTING_GROUP_RETURN',2,8.25,((current_date-1)+time '08:00') at time zone 'Asia/Jakarta');
insert into erp.po_hpp_gl_material_state_v1 values('00000000-0000-0000-0000-0000000000a0','M:00000000-0000-0000-0000-0000000000f1',100,now()-interval '1 hour'),
 ('00000000-0000-0000-0000-0000000000a0','M:00000000-0000-0000-0000-0000000000f2',-20,now()-interval '1 hour');
insert into erp.po_hpp_gl_state values('00000000-0000-0000-0000-0000000000a0',10,80,80,0,0,now()-interval '1 hour');
select erp.sync_po_hpp_to_gl('00000000-0000-0000-0000-0000000000a0',current_date-4);
select * from public.show();
rollback;
