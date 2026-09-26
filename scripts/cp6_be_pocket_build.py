"""Counted predecessor changes for ALL-C04 cutover sources in the real pocket period pipeline."""
from pathlib import Path
import json,re
from cp6_bc_build import last_definition,substitute
import cp6_bd_build as bd
ROOT=Path(__file__).resolve().parents[1]
BD=ROOT/'supabase/dev/cp6_bd_t1_family.sql'
AP=ROOT/'supabase/migrations/20260922135615_erp_v2_6_20ap_cp6_connected_import_materials.sql'
ENTITIES=['OPENING_POCKET_USAGE','OPENING_POCKET_SEWING']
TABLES=['be_pocket_usage_v1','be_pocket_sewing_v1','be_pocket_source_events_v1','be_pocket_target_events_v1']
REPLACED=['erp.stage_migration_row(uuid,text,integer,text,jsonb,jsonb)','erp._validate_migration_batch_base(uuid)',
 'erp.finalize_migration_batch(uuid)','erp.save_initial_import_action_v1(text,jsonb,uuid)','erp.get_initial_import_workspace_v1(uuid)',
 'erp.initial_import_revision_v1(uuid)','erp.pocket_period_total_v1(uuid)','erp.pocket_period_manifest_v1(date,date)',
 'erp.pocket_period_target_v1(uuid,boolean)','erp.pocket_period_book_v1(uuid)','erp.sync_pocket_period_v1(uuid,date,text,text)',
 'erp.save_pocket_period_action_v1(text,jsonb,uuid)','erp.initial_import_source_value_v1(uuid)',
 'erp.pocket_period_checks_v1()','erp.save_pocket_fabric_action_v1(text,jsonb,uuid)']

def catalog():return {**bd.catalog(),**json.loads((ROOT/'src/initialImportCatalogBE.json').read_text())}
def patch(path,name,changes):return substitute(last_definition(path,name),changes,'BE pocket '+name)
def build():
    tail="'OPENING_LAUNDRY_CLAIM','OPENING_LAUNDRY_UNINVOICED'"
    newtail=tail+','+','.join("'"+x+"'" for x in ENTITIES)
    stage=patch(BD,'stage_migration_row',[(tail+") then\n    raise exception 'Unsupported migration entity_type %'",newtail+") then\n    raise exception 'Unsupported migration entity_type %'")])
    base=patch(BD,'_validate_migration_batch_base',[(tail+")\n",newtail+")\n")])
    final=patch(BD,'finalize_migration_batch',[(tail+") and posted_entity_id is null)",newtail+") and posted_entity_id is null)")])
    router=patch(BD,'save_initial_import_action_v1',[
     ('     perform erp.bd_validate_imports_v1(b.id);','     perform erp.bd_validate_imports_v1(b.id);\n     perform erp.be_validate_pocket_imports_v1(b.id);'),
     ('       perform erp.bd_apply_imports_v1(b.id);','       perform erp.bd_apply_imports_v1(b.id);\n       perform erp.be_apply_pocket_imports_v1(b.id);')])
    old=re.search(r"v_catalog constant jsonb:=('.*?')::jsonb;",router,re.S)
    assert old and router.count(old.group(0))==1
    router=router.replace(old.group(0),"v_catalog constant jsonb:='"+json.dumps(catalog(),ensure_ascii=False).replace("'","''")+"'::jsonb;")
    ws=patch(BD,'get_initial_import_workspace_v1',[('||erp.bd_import_workspace_v1(b.id);','||erp.bd_import_workspace_v1(b.id)||erp.be_pocket_import_workspace_v1(b.id);')])
    rev=patch(BD,'initial_import_revision_v1',[("'bd',erp.bd_import_revision_part_v1(p_batch_id)","'bd',erp.bd_import_revision_part_v1(p_batch_id),'be',erp.be_pocket_import_workspace_v1(p_batch_id)")])
    total=patch(AP,'pocket_period_total_v1',[("-((erp._cp6_material_adjustment_revaluation_state(s.adjustment_id)->>'current_value')::numeric)","case when s.historical_usage_id is not null then erp.be_pocket_usage_amount_v1(s.historical_usage_id) else -((erp._cp6_material_adjustment_revaluation_state(s.adjustment_id)->>'current_value')::numeric) end")])
    manifest=patch(AP,'pocket_period_manifest_v1',[
     ('u.adjustment_id,h.row_version::text version,','u.adjustment_id,null::uuid historical_usage_id,h.row_version::text version,'),
     (' ), destinations as(','  union all select null::uuid,u.id,erp.be_pocket_usage_amount_v1(u.id)::text,u.physical_date,u.material_id,null::uuid,u.material_qty::text,erp.be_pocket_usage_amount_v1(u.id)::numeric(20,2)::text\n  from erp.be_pocket_usage_v1 u where u.allocation_status=\'UNALLOCATED\' and u.physical_date between p_start and p_end\n ), native_destinations as('),
     ('select e.id event_id,e.po_id,','select e.id event_id,null::uuid historical_sewing_id,e.physical_at,0 sort_kind,e.po_id,'),
     ('   coalesce(sum(e.qty_signed) over(order by e.physical_at,e.id rows between unbounded preceding and 1 preceding),0)::bigint preceding_qty,\n',''),
     (" ) select jsonb_build_object('period_start'", " ), all_destinations as(\n  select * from native_destinations\n  union all select null::uuid,s.id,s.physical_date::timestamp at time zone 'Asia/Jakarta',case s.target_kind when 'FINISHED_GOODS' then 1 when 'COGS' then 2 else 3 end,\n   s.po_id,s.contractor_id,null::uuid,s.qty,to_jsonb(s)\n  from erp.be_pocket_sewing_v1 s where s.physical_date between p_start and p_end\n ), destinations as(\n  select event_id,historical_sewing_id,po_id,contractor_id,cutting_group_id,sewing_qty,\n   coalesce(sum(sewing_qty) over(order by physical_at,sort_kind,coalesce(event_id,historical_sewing_id) rows between unbounded preceding and 1 preceding),0)::bigint preceding_qty,source_snapshot\n  from all_destinations\n ) select jsonb_build_object('period_start'"),
     ('order by adjustment_id','order by coalesce(adjustment_id,historical_usage_id)'),
     ('order by preceding_qty,event_id','order by preceding_qty,coalesce(event_id,historical_sewing_id)')])
    target=patch(AP,'pocket_period_target_v1',[
     ("select 'WIP|'||d.po_id::text key,sum(erp.pocket_period_amount_v1(d.pool_id,d.preceding_qty,d.sewing_qty)) amount\n  from erp.pocket_period_destinations d where d.pool_id=p_pool group by d.po_id",
      "select case when s.target_kind='FINISHED_GOODS' then 'OPENING_EQUITY' when s.target_kind='COGS' then 'COGS' else 'WIP|'||d.po_id::text end key,\n   sum(erp.pocket_period_amount_v1(d.pool_id,d.preceding_qty,d.sewing_qty)) amount\n  from erp.pocket_period_destinations d left join erp.be_pocket_sewing_v1 s on s.id=d.historical_sewing_id where d.pool_id=p_pool group by 1")])
    book=patch(AP,'pocket_period_book_v1',[("   else 'INVALID|'", "   when l.account_id=erp.account_id('OPENING_EQUITY') and l.po_id is null then 'OPENING_EQUITY'\n   when l.account_id=erp.account_id('COGS') and l.po_id is null then 'COGS'\n   else 'INVALID|'")])
    sync=patch(AP,'sync_pocket_period_v1',[
     (' for v_po in select distinct po_id from erp.pocket_period_destinations where pool_id=p_pool order by po_id loop',
      " perform erp.be_pocket_sync_targets_v1(p_pool,p_date,p_kind='CANCEL');\n for v_po in select distinct po_id from erp.pocket_period_destinations where pool_id=p_pool and po_id is not null order by po_id loop")])
    post=patch(AP,'save_pocket_period_action_v1',[
     ('insert into erp.pocket_period_sources(pool_id,adjustment_id,original_amount)','insert into erp.pocket_period_sources(pool_id,adjustment_id,historical_usage_id,original_amount)'),
     ("select ident,(x->>'adjustment_id')::uuid,(x->>'amount')::numeric", "select ident,(x->>'adjustment_id')::uuid,(x->>'historical_usage_id')::uuid,(x->>'amount')::numeric"),
     ('insert into erp.pocket_period_destinations(pool_id,event_id,po_id,','insert into erp.pocket_period_destinations(pool_id,event_id,historical_sewing_id,po_id,'),
     ("select ident,(x->>'event_id')::uuid,(x->>'po_id')::uuid", "select ident,(x->>'event_id')::uuid,(x->>'historical_sewing_id')::uuid,(x->>'po_id')::uuid")])
    value=patch(AP,'initial_import_source_value_v1',[(" from erp.opening_balance_items i where i.id=p_item;", " +erp.be_pocket_opening_extra_v1(i.id)\n from erp.opening_balance_items i where i.id=p_item;")])
    checks=patch(AP,'pocket_period_checks_v1',[(" union all select 'AP_PERIOD_POCKET_OVERLAP'", "  or exists(select 1 from erp.pocket_period_destinations d join erp.be_pocket_sewing_v1 s on s.id=d.historical_sewing_id where d.pool_id=p.id and to_jsonb(s)<>d.source_snapshot)\n union all select 'AP_PERIOD_POCKET_OVERLAP'")])
    facade=patch(AP,'save_pocket_fabric_action_v1',[(" if v_action in('POST_PERIOD','CANCEL_PERIOD') then", " if v_action='CORRECT_OPENING_USAGE' then return erp.be_correct_pocket_usage_v1(p_payload,p_client_request_id);end if;\n if v_action in('POST_PERIOD','CANCEL_PERIOD') then")])
    return '\n'.join([stage,base,final,router,ws,rev,total,manifest,target,book,sync,post,value,checks,facade])

def filter_native(text):
    return substitute(text,[("from erp.pocket_period_destinations d where d.po_id=", "from erp.pocket_period_destinations d where d.event_id is not null and d.po_id=")],'BE historical pocket value via opening source, not twice')
