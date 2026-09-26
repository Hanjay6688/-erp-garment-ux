#!/usr/bin/env python3
"""BE family builder. Development stages remain NOT_READY until all four flows and CI gates are complete.

Existing function changes use exactly-once substitutions from the pinned predecessor definitions.
The selected-lot adapter never falls back to a different FIFO lot.
"""
from pathlib import Path
import hashlib,re,sys
from cp6_bc_build import last_definition,substitute

ROOT=Path(__file__).resolve().parents[1]
AC=ROOT/'supabase/migrations/20260915031500_erp_v2_6_20ac_cp6_temporal_surface_closure.sql'
F=ROOT/'supabase/migrations/20260909174713_erp_v2_6_20f_cp6_final_runtime_reliability.sql'
BC=ROOT/'supabase/dev/cp6_bc_t1_family.sql'
BD=ROOT/'supabase/dev/cp6_bd_t1_family.sql'
OUT=ROOT/'supabase/dev/cp6_be_t1_family.sql'
VERSION='v2.6.20be'
REPLACED=['erp.post_product_conversion(uuid)','erp.propagate_conversion_hpp_for_po(uuid)',
          'erp.compute_po_hpp_gl_targets_v2620d(uuid)','erp.bc_value_custody_v1(jsonb,uuid)',
          'erp.bc_reverse_v1(jsonb,uuid)','erp.sync_material_cost_revaluation(uuid)','erp.run_v268_financial_report_checks()']
NEW_TABLES=['be_execution_context_v1','be_conversion_sources_v1','be_conversion_returns_v1',
            'be_conversion_cost_sources_v1','be_conversion_cost_events_v1']
OBJECTS=[ROOT/f'scripts/cp6_be_objects_{part}.sql' for part in ('conversion','cost')]

def objects():return '\n'.join(p.read_text().rstrip() for p in OBJECTS)

def new_functions():
    return [m.group(1) for m in re.finditer(r'(?i)create or replace function ((?:erp|public)\.[a-z0-9_]+)\(',objects())]

def conversion():
    return substitute(last_definition(AC,'post_product_conversion'),[
      ("where fl.product_id=h.from_product_id and fl.po_id is null\n",
       "where fl.product_id=h.from_product_id and fl.po_id is null\n"
       "      and (not exists(select 1 from erp.be_conversion_sources_v1 where conversion_id=h.id)\n"
       "        or fl.id=(select source_lot_id from erp.be_conversion_sources_v1 where conversion_id=h.id))\n"),
      ("where fl.product_id=h.from_product_id and fl.po_id is not null\n",
       "where fl.product_id=h.from_product_id and fl.po_id is not null\n"
       "      and (not exists(select 1 from erp.be_conversion_sources_v1 where conversion_id=h.id)\n"
       "        or fl.id=(select source_lot_id from erp.be_conversion_sources_v1 where conversion_id=h.id))\n")
    ],'BE exact source conversion')

def build():
    propagate=last_definition(F,'propagate_conversion_hpp_for_po')
    assert propagate.count('r.conversion_cost_allocated')==3
    propagate=propagate.replace('r.conversion_cost_allocated','erp.be_allocation_extra_v1(r.id)')
    propagate=substitute(propagate,[("    select hpp_version_id,hpp_per_pcs into v_old_id,v_current",
      "    if v_desired<0 then raise exception 'BE_RECOVERY_EXCEEDS_VALUE: nilai pemulihan melebihi nilai sumber dan biaya sah';end if;\n"
      "    select hpp_version_id,hpp_per_pcs into v_old_id,v_current")],'BE nonnegative cost')
    target=substitute(last_definition(F,'compute_po_hpp_gl_targets_v2620d'),[
      ('coalesce(sum(hv.total_cost),0)::numeric raw_total','(coalesce(sum(hv.total_cost),0)+erp.be_po_extra_v1(p_po_id))::numeric raw_total')],'BE PO source total')
    recover=substitute(last_definition(BC,'bc_value_custody_v1'),[
      ("  return jsonb_build_object('event_id',v_event,'adjustment_id',v_adj,",
       "  perform erp.be_link_recovery_v1(p_request,l.id,erp._cp3_business_date(v_at));\n"
       "  return jsonb_build_object('event_id',v_event,'adjustment_id',v_adj,")],'BE recovery linkage')
    reverse=substitute(last_definition(BC,'bc_reverse_v1'),[
      ("  return jsonb_build_object('reversed_document_id',d.id,",
       "  perform erp.be_reconcile_cost_document_v1(d.id,erp._cp3_business_date(current_timestamp));\n"
       "  return jsonb_build_object('reversed_document_id',d.id,")],'BE reversal linkage')
    recost=substitute(last_definition(BC,'sync_material_cost_revaluation'),[
      ('end;\n$function$;','  perform erp.be_sync_material_cost_v1(p_material_id);\nend;\n$function$;')],'BE material recost hook')
    checks=substitute(last_definition(BD,'run_v268_financial_report_checks'),[
      ("    )::numeric source_cost\n", "      +erp.be_po_extra_v1(s.po_id)\n    )::numeric source_cost\n"),
      ('+a.conversion_cost_allocated/nullif(a.qty_pcs,0)', '+erp.be_allocation_extra_v1(a.id)/nullif(a.qty_pcs,0)')],'BE source and lineage detectors')
    grants=r"""do $grants$
declare t text;f text;
begin
 foreach t in array array['be_execution_context_v1','be_conversion_sources_v1','be_conversion_returns_v1',
   'be_conversion_cost_sources_v1','be_conversion_cost_events_v1'] loop
   execute format('alter table erp.%I enable row level security',t);
   execute format('revoke all on erp.%I from public,anon,authenticated,service_role',t);
 end loop;
 for f in select p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid=p.pronamespace
   where n.nspname='erp' and (p.proname like 'be\_%' or p.proname in('save_product_conversion_action_v1','get_product_conversion_workspace_v1')) loop
   execute format('revoke all on function %s from public,anon,authenticated,service_role',f);
 end loop;
end $grants$;
revoke all on function public.erp_save_product_conversion_action_v1(text,jsonb,uuid) from public,anon;
revoke all on function public.erp_get_product_conversion_workspace_v1(jsonb) from public,anon;
grant execute on function public.erp_save_product_conversion_action_v1(text,jsonb,uuid) to authenticated,service_role;
grant execute on function public.erp_get_product_conversion_workspace_v1(jsonb) to authenticated,service_role;
"""
    return '\n'.join([
      '-- BE T1_FAMILY development install, NOT release evidence. Stage 1; remaining flows recorded in writer progress.',
      '-- Generated by scripts/cp6_be_build.py; do not edit by hand.',
      "begin;set local search_path='';set local lock_timeout='10s';set local statement_timeout='240s';",
      "do $guard$ begin if not exists(select 1 from erp.schema_migrations where version='v2.6.20bd') then raise exception 'BE_REQUIRES_BD';end if;",
      "if exists(select 1 from erp.schema_migrations where version='v2.6.20be') then raise exception 'BE_ALREADY_INSTALLED';end if;end $guard$;",
      objects(),conversion(),propagate,target,recover,reverse,recost,checks,grants,
      "insert into erp.schema_migrations(version,description) values('v2.6.20be','BE development family: SKU conversion, rework/redye and pocket cutover');",
      'commit;',''])

if __name__=='__main__':
    text=build()
    if '--check' in sys.argv:assert OUT.read_text()==text,'BE_BUILD_STALE'
    else:OUT.write_text(text)
    print(OUT.relative_to(ROOT),len(text),hashlib.sha256(text.encode()).hexdigest())
