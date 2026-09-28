#!/usr/bin/env python3
"""BF development family: one commercial SKU, exact-size physical history. No release/production claim."""
from pathlib import Path
import gzip,hashlib,re,sys
from cp6_bc_build import last_definition,substitute
import cp6_bf_laundry_build as laundry
import cp6_bf_rework_build as rework
import cp6_bf_recovery as recovery
import cp6_bf_import_build as imports

ROOT=Path(__file__).resolve().parents[1]
VERSION='v2.6.20bf'
OUT=ROOT/'supabase/dev/cp6_bf_t1_family.sql'
AC=ROOT/'supabase/migrations/20260915031500_erp_v2_6_20ac_cp6_temporal_surface_closure.sql'
AI=ROOT/'supabase/migrations/20260916090022_erp_v2_6_20ai_cp6_work_source_lineage.sql'
C=ROOT/'supabase/migrations/20260907190000_erp_v2_6_20c_cp6_deep_business_reliability.sql'
BE=ROOT/'supabase/dev/cp6_be_t1_family.sql'
BD=ROOT/'supabase/dev/cp6_bd_t1_family.sql'
BB=ROOT/'supabase/dev/cp6_bb_t1_family.sql'
FIXTURE=ROOT/'supabase/tests/fixtures/erp_enteng_cp45a_catalog_bootstrap.sql.gz'
PARTS=('master','rates','work','laundry','import','router')
NEW_TABLES=['bf_rollback_v1','bf_skus_v1','bf_sku_versions_v1','bf_sku_members_v1','bf_wave_skus_v1','bf_po_boms_v1','bf_requests_v1','bf_context_v1','bf_laundry_delivery_sources_v1']
REPLACED=['erp.commit_accessory_bom_for_lot(uuid)','erp.ensure_po_work_component_snapshots(uuid,timestamp with time zone)',
 'erp.validate_work_completion()','erp.guard_work_completion_posting_consistency()',
 'erp.seed_bs_case_component_baseline()','erp.classify_bs_case_v2(uuid,jsonb,uuid,bigint)',
 'erp.cp6_lot_work_cost_v2620c(uuid,text)','erp.assert_new_stock_cutoff_coverage_v1()']+laundry.REPLACED+rework.REPLACED+imports.REPLACED

def fixture(name):return last_definition(None,name,text=gzip.open(FIXTURE,'rt').read())
def objects():return '\n'.join((ROOT/f'scripts/cp6_bf_objects_{p}.sql').read_text() for p in PARTS)
def new_functions():return list(dict.fromkeys(re.findall(r'(?i)create or replace function ((?:erp|public)\.[a-z0-9_]+)\(',objects())))

def changed():
    bom=substitute(fixture('commit_accessory_bom_for_lot'),[("    perform pg_advisory_xact_lock(hashtextextended('ABOM:'||v_root::text,0));", "    v_bom:=erp.bf_bom_for_lot_v1(p_lot_id);\n    if v_bom is null then\n    perform pg_advisory_xact_lock(hashtextextended('ABOM:'||v_root::text,0));"),
      ("    if v_bom is null then\n      raise exception 'Accessory BOM", "    end if;\n    if v_bom is null then\n      raise exception 'Accessory BOM")],'BF shared BOM')
    work=last_definition(AC,'ensure_po_work_component_snapshots')
    work=work.replace('where po_id=p.id;','where po_id=p.id and bf_sku_version_id is null;')
    work=substitute(work,[('if v_count>0 then return v_count; end if;','if v_count>0 then perform erp.bf_ensure_work_v1(p_po_id,p_basis_at);return v_count; end if;'),
      ('  return v_count;','  perform erp.bf_ensure_work_v1(p_po_id,p_basis_at);\n  return v_count;')],'BF work scopes')
    validate=substitute(last_definition(AI,'validate_work_completion',text=AI.read_text().replace('$function$\n$definition$;', '$function$;')),[('  new.rate_snapshot:=v_snapshot_rate;',
      '  perform erp.bf_assert_work_scope_v1(new.completion_id,new.po_component_snapshot_id);\n  new.rate_snapshot:=v_snapshot_rate;')],'BF line scope')
    posting=substitute(last_definition(BB,'guard_work_completion_posting_consistency'),[
      ('  v_prior_payable bigint;','  v_prior_payable bigint;\n  v_scope_capacity bigint;'),
      ('select l.id,l.work_component_id,l.qty_completed,l.qty_payable,wc.component_name','select l.id,l.po_component_snapshot_id,l.work_component_id,l.qty_completed,l.qty_payable,wc.component_name'),
      ('    loop\n      select coalesce(sum(l2.qty_completed),0)',
       '    loop\n      perform erp.bf_assert_work_scope_v1(new.id,r.po_component_snapshot_id);\n      v_scope_capacity:=erp.bf_work_capacity_v1(new.cutting_group_id,r.po_component_snapshot_id,v_effective);\n      select coalesce(sum(l2.qty_completed),0)'),
      ('        and l2.work_component_id=r.work_component_id','        and l2.work_component_id=r.work_component_id\n        and erp.bf_snapshot_sku_v1(l2.po_component_snapshot_id) is not distinct from erp.bf_snapshot_sku_v1(r.po_component_snapshot_id)'),
      ('if v_prior_completed+r.qty_completed>v_effective then','if v_prior_completed+r.qty_completed>v_scope_capacity then'),
      ('if v_prior_payable+r.qty_payable>v_effective then','if v_prior_payable+r.qty_payable>v_scope_capacity then')],'BF posting scope/capacity')
    seed=substitute(fixture('seed_bs_case_component_baseline'),[
      ('  where s.po_id=new.po_id','  where s.po_id=new.po_id and erp.bf_snapshot_matches_v1(s.id,new.cutting_group_id,new.product_id)'),
      ('          and wcl.work_component_id=s.work_component_id','          and wcl.work_component_id=s.work_component_id\n          and erp.bf_snapshot_sku_v1(wcl.po_component_snapshot_id) is not distinct from erp.bf_snapshot_sku_v1(s.id)')],'BF BS entitlement')
    classify=substitute(last_definition(AC,'classify_bs_case_v2'),[
      ("      where po_id=v_case.po_id and work_component_id=(v_component->>'work_component_id')::uuid",
       "      where po_id=v_case.po_id and work_component_id=(v_component->>'work_component_id')::uuid\n        and erp.bf_snapshot_matches_v1(id,v_case.cutting_group_id,v_case.product_id)")],'BF BS choice')
    cost=last_definition(C,'cp6_lot_work_cost_v2620c',text=re.sub(r'(?i)create function erp\.','CREATE OR REPLACE FUNCTION erp.',C.read_text()))
    cost=substitute(cost,[
      ('    fl.initial_qty_pcs::numeric lot_qty,fl.produced_at','    fl.initial_qty_pcs::numeric lot_qty,fl.produced_at,fl.product_id'),
      ('  select t.*,','  select t.*,\n    erp.bf_group_sku_v1(t.group_id,t.product_id) sku_id,\n    coalesce((select sum(x.initial_qty_pcs)::numeric from erp.fg_lots x\n      left join erp.qc_inspection_items xqi on xqi.id=x.qc_item_id\n      where x.po_id=t.po_id and x.lot_origin=\'PRODUCTION\'\n        and coalesce(x.cutting_group_id,xqi.cutting_group_id)=t.group_id\n        and erp.bf_group_sku_v1(t.group_id,x.product_id)=erp.bf_group_sku_v1(t.group_id,t.product_id)\n        and (x.produced_at,x.id)<(t.produced_at,t.id)),0) sku_start,'),
      ('  select wce.cutting_group_id,wc.component_category,','  select wce.cutting_group_id,wc.component_category,erp.bf_snapshot_sku_v1(wcl.po_component_snapshot_id) sku_id,'),
      ('partition by wce.po_id,wce.cutting_group_id,wcl.work_component_id','partition by wce.po_id,wce.cutting_group_id,wcl.work_component_id,erp.bf_snapshot_sku_v1(wcl.po_component_snapshot_id)'),
      ('case when s.cutting_group_id is null then p.po_start+p.lot_qty else p.group_start+p.lot_qty end','case when s.sku_id is not null then p.sku_start+p.lot_qty when s.cutting_group_id is null then p.po_start+p.lot_qty else p.group_start+p.lot_qty end'),
      ('case when s.cutting_group_id is null then p.po_start else p.group_start end','case when s.sku_id is not null then p.sku_start when s.cutting_group_id is null then p.po_start else p.group_start end'),
      ('from position p left join source_lines s on true','from position p left join source_lines s on s.sku_id is null or s.sku_id=p.sku_id')],'BF HPP intervals per SKU')
    coverage=substitute(last_definition(BE,'assert_new_stock_cutoff_coverage_v1'),[
      ('  -- Structural catalog read:', '''  v_registry:=v_registry||'{"erp.bf_sku_members_v1.product_root":{"class":"MASTER","reason":"Commercial SKU membership; exact physical root is preserved"}}'::jsonb;
  -- Structural catalog read:''')],'BF master classification')
    return [bom,work,validate,posting,seed,classify,cost,coverage]+laundry.changed(BD)+rework.changed(fixture)+imports.changed(BB,BD,BE)

def build():
    grants=r"""
do $grants$ declare t text;f record;begin
 foreach t in array ARRAY[TABLE_LIST] loop
   execute format('alter table erp.%I enable row level security',t);
   execute format('revoke all on erp.%I from public,anon,authenticated,service_role',t);
 end loop;
 for f in select p.oid::regprocedure sig,n.nspname from pg_proc p join pg_namespace n on n.oid=p.pronamespace
   where (n.nspname='erp' and(p.proname like 'bf\_%' or p.proname in('save_sku_action_v1','get_sku_workspace_v1','get_sku_hpp_v1')))
     or (n.nspname='public' and p.proname in('erp_save_sku_action_v1','erp_get_sku_workspace_v1','erp_get_sku_hpp_v1')) loop
   execute format('revoke all on function %s from public,anon,authenticated,service_role',f.sig);
   if f.nspname='public' then execute format('grant execute on function %s to authenticated,service_role',f.sig);end if;
 end loop;
end $grants$;
""".replace('TABLE_LIST',','.join("'"+t+"'" for t in NEW_TABLES))
    return '\n'.join(['-- BF development family. NOT_READY until complete qualification. Generated; do not edit.',
      "begin;set local search_path='';set local lock_timeout='10s';set local statement_timeout='240s';",
      "do $guard$ begin if not exists(select 1 from erp.schema_migrations where version='v2.6.20be') then raise exception 'BF_REQUIRES_BE';end if;",
      "if exists(select 1 from erp.schema_migrations where version='v2.6.20bf') then raise exception 'BF_ALREADY_INSTALLED';end if;end $guard$;",
      recovery.capture(REPLACED),objects(),*changed(),grants,recovery.seal(list(dict.fromkeys([s.split('(')[0] for s in REPLACED]+new_functions()))),
      "insert into erp.schema_migrations(version,description) values('v2.6.20bf','Commercial SKU ranges; physical-size lineage preserved');",'commit;',''])

if __name__=='__main__':
    value=build()
    if '--check' in sys.argv:assert OUT.read_text()==value,'BF_BUILD_STALE'
    else:OUT.write_text(value)
    rollback=ROOT/'supabase/dev/cp6_bf_t2_rollback.sql'
    rollback_value=recovery.rollback(new_functions(),NEW_TABLES)
    if '--check' in sys.argv:assert rollback.read_text()==rollback_value,'BF_ROLLBACK_BUILD_STALE'
    else:rollback.write_text(rollback_value)
    print(OUT.relative_to(ROOT),len(value),hashlib.sha256(value.encode()).hexdigest())
