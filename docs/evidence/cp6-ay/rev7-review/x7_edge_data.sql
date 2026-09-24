\set QUIET 1
\pset footer off
-- Edge data in one PO: lot without group; lot whose group is another PO's (no batch); batch with effective pcs 0; batch
-- group of another PO with no movement and no cut_at; contractor item without stock movement; voided lot without group;
-- conversion lot without allocation; source qty 0 (settings SRCQ). Compare per-account totals with AS (sync_po_hpp_to_gl_as).
begin;
insert into erp.settings values('E',(current_date-6)::text),('SRCQ','0');
insert into erp.cutting_groups values
 ('00000000-0000-0000-0000-0000000000a1','00000000-0000-0000-0000-0000000000a0','00000000-0000-0000-0000-0000000000bb',((current_date-5)+time '08:00') at time zone 'Asia/Jakarta'),
 ('00000000-0000-0000-0000-0000000000a2','00000000-0000-0000-0000-0000000000ab','00000000-0000-0000-0000-0000000000bb',null),
 ('00000000-0000-0000-0000-0000000000a3','00000000-0000-0000-0000-0000000000ab',null,((current_date-5)+time '08:00') at time zone 'Asia/Jakarta');
insert into erp.v_cutting_group_totals values('00000000-0000-0000-0000-0000000000a1',10),('00000000-0000-0000-0000-0000000000a2',0),('00000000-0000-0000-0000-0000000000a3',5);
insert into erp.v_cutting_batch_totals values('00000000-0000-0000-0000-0000000000bb',0);
insert into erp.material_stock_movements(id,source_id,source_type,qty_signed,unit_cost_snapshot,physical_at) values
 ('00000000-0000-0000-0000-0000000000e1','00000000-0000-0000-0000-0000000000a1','CUTTING_GROUP',-4,8.25,((current_date-5)+time '08:00') at time zone 'Asia/Jakarta'),
 ('00000000-0000-0000-0000-0000000000e3','00000000-0000-0000-0000-0000000000a3','CUTTING_GROUP',-2,8.25,((current_date-5)+time '08:00') at time zone 'Asia/Jakarta');
insert into erp.materials values('00000000-0000-0000-0000-0000000000ae','FABRIC');
insert into erp.contractor_material_issues values('00000000-0000-0000-0000-0000000000ac','00000000-0000-0000-0000-0000000000a0','POSTED',((current_date-2)+time '09:00') at time zone 'Asia/Jakarta');
insert into erp.contractor_material_issue_items values('00000000-0000-0000-0000-0000000000ad','00000000-0000-0000-0000-0000000000ac','00000000-0000-0000-0000-0000000000ae',5,1.60);
insert into erp.fg_lots values
 ('00000000-0000-0000-0000-0000000000b1','00000000-0000-0000-0000-0000000000a0','PRODUCTION',10,((current_date-4)+time '13:00') at time zone 'Asia/Jakarta','00000000-0000-0000-0000-0000000000a1',null,null),
 ('00000000-0000-0000-0000-0000000000b2','00000000-0000-0000-0000-0000000000a0','PRODUCTION',5,((current_date-4)+time '13:00') at time zone 'Asia/Jakarta',null,null,null),
 ('00000000-0000-0000-0000-0000000000b3','00000000-0000-0000-0000-0000000000a0','PRODUCTION',5,((current_date-4)+time '13:00') at time zone 'Asia/Jakarta','00000000-0000-0000-0000-0000000000a3',null,null),
 ('00000000-0000-0000-0000-0000000000b4','00000000-0000-0000-0000-0000000000a0','VOIDED_PRODUCTION',5,((current_date-4)+time '13:00') at time zone 'Asia/Jakarta',null,null,null),
 ('00000000-0000-0000-0000-0000000000c1','00000000-0000-0000-0000-0000000000a0','CONVERSION',2,((current_date-3)+time '13:00') at time zone 'Asia/Jakarta',null,null,null);
insert into erp.hpp_versions(lot_id,version_no,qty_basis_pcs,total_cost,is_current,calculated_at)
 select id,1,initial_qty_pcs,initial_qty_pcs*10,false,now()-interval '2 hour' from erp.fg_lots union all
 select id,2,initial_qty_pcs,initial_qty_pcs*8.37,true,now() from erp.fg_lots where lot_origin<>'VOIDED_PRODUCTION' union all
 select id,2,initial_qty_pcs,initial_qty_pcs*10,true,now() from erp.fg_lots where lot_origin='VOIDED_PRODUCTION';
insert into erp.fg_stock_movements(lot_id,movement_type,qty_signed,physical_at) values
 ('00000000-0000-0000-0000-0000000000b1','QC_GOOD',10,((current_date-4)+time '13:00') at time zone 'Asia/Jakarta'),
 ('00000000-0000-0000-0000-0000000000b2','QC_GOOD',5,((current_date-4)+time '13:00') at time zone 'Asia/Jakarta'),
 ('00000000-0000-0000-0000-0000000000b3','QC_GOOD',5,((current_date-4)+time '13:00') at time zone 'Asia/Jakarta'),
 ('00000000-0000-0000-0000-0000000000b4','QC_GOOD',5,((current_date-4)+time '13:00') at time zone 'Asia/Jakarta'),
 ('00000000-0000-0000-0000-0000000000b1','REBRAND_OUT',-2,((current_date-3)+time '13:00') at time zone 'Asia/Jakarta'),
 ('00000000-0000-0000-0000-0000000000c1','REBRAND_IN',2,((current_date-3)+time '13:00') at time zone 'Asia/Jakarta'),
 ('00000000-0000-0000-0000-0000000000b2','SALE',-3,((current_date-1)+time '13:00') at time zone 'Asia/Jakarta'),
 ('00000000-0000-0000-0000-0000000000b3','BS_OUT',-1,((current_date-1)+time '13:00') at time zone 'Asia/Jakarta');
insert into erp.fg_stock_movements(lot_id,movement_type,qty_signed,physical_at,reversal_of_id) select lot_id,'REVERSAL',-5,((current_date-2)+time '13:00') at time zone 'Asia/Jakarta',id from erp.fg_stock_movements where lot_id='00000000-0000-0000-0000-0000000000b4';
insert into erp.sales_headers values('00000000-0000-0000-0000-0000000000d1','POSTED',null);
insert into erp.sales_items values('00000000-0000-0000-0000-0000000000d2','00000000-0000-0000-0000-0000000000d1');
insert into erp.sale_stock_allocations(sale_item_id,lot_id,qty_pcs) values('00000000-0000-0000-0000-0000000000d2','00000000-0000-0000-0000-0000000000b2',3);
insert into erp.po_hpp_gl_state values('00000000-0000-0000-0000-0000000000a0',20,200,160,30,10,now()-interval '1 hour');
insert into erp.po_hpp_gl_lot_state_v1 select id,po_id,10,now()-interval '1 hour' from erp.fg_lots;
insert into erp.po_hpp_gl_material_state_v1 values('00000000-0000-0000-0000-0000000000a0','M:00000000-0000-0000-0000-0000000000e1',40,now()-interval '1 hour'),
 ('00000000-0000-0000-0000-0000000000a0','M:00000000-0000-0000-0000-0000000000e3',20,now()-interval '1 hour'),('00000000-0000-0000-0000-0000000000a0','SYNC',0,now()-interval '1 hour');
select * from erp.compute_po_hpp_gl_targets_v2620d('00000000-0000-0000-0000-0000000000a0');
savepoint s;
select erp.sync_po_hpp_to_gl_as('00000000-0000-0000-0000-0000000000a0',current_date-6);
select jsonb_object_agg(mapping_key,amt) as_tot from (select l.mapping_key,sum(l.debit-l.credit) amt from erp.journal_lines l group by 1) x \gset
rollback to savepoint s;
select erp.sync_po_hpp_to_gl('00000000-0000-0000-0000-0000000000a0',current_date-6);
select * from public.show();
select coalesce(a.key,b.mapping_key) k,a.value::numeric as_amt,b.amt ay_amt from jsonb_each_text(:'as_tot'::jsonb) a full join (select l.mapping_key,sum(l.debit-l.credit) amt from erp.journal_lines l group by 1) b on a.key=b.mapping_key order by 1;
rollback;
