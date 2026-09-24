\set QUIET 1
\pset footer off
-- No lots left (state from before), invoice path; and a PO with a group, facts, contractor item but no lots and no state.
begin;
insert into erp.settings values('E',(current_date-3)::text);
insert into erp.po_hpp_gl_state values('00000000-0000-0000-0000-0000000000a0',10,100,60,30,10,now()-interval '1 hour');
insert into erp.cutting_groups values('00000000-0000-0000-0000-0000000000a1','00000000-0000-0000-0000-0000000000a9',null,now());
insert into erp.material_stock_movements(source_id,source_type,qty_signed,unit_cost_snapshot,physical_at) values('00000000-0000-0000-0000-0000000000a1','CUTTING_GROUP',-1,1,now());
select erp.sync_po_hpp_to_gl('00000000-0000-0000-0000-0000000000a0',current_date-3);
select erp.sync_po_hpp_to_gl('00000000-0000-0000-0000-0000000000a9',current_date-3);
select * from public.show();
select po_id,source_key from erp.po_hpp_gl_material_state_v1;
rollback;
