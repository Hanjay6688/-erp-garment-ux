#!/usr/bin/env python3
"""BE family builder. Development stages remain NOT_READY until all four flows and CI gates are complete.

Existing function changes use exactly-once substitutions from the pinned predecessor definitions.
The selected-lot adapter never falls back to a different FIFO lot.
"""
from pathlib import Path
import hashlib,re,sys
import cp6_be_redye_build as redye
import cp6_be_pocket_build as pocket
from cp6_bc_build import last_definition,substitute

ROOT=Path(__file__).resolve().parents[1]
AC=ROOT/'supabase/migrations/20260915031500_erp_v2_6_20ac_cp6_temporal_surface_closure.sql'
F=ROOT/'supabase/migrations/20260909174713_erp_v2_6_20f_cp6_final_runtime_reliability.sql'
BC=ROOT/'supabase/dev/cp6_bc_t1_family.sql'
BD=ROOT/'supabase/dev/cp6_bd_t1_family.sql'
AV=ROOT/'supabase/migrations/20260923110000_erp_v2_6_20av_cp6_identity_new_stock_cutoff.sql'
OUT=ROOT/'supabase/dev/cp6_be_t1_family.sql'
VERSION='v2.6.20be'
REPLACED=['erp.post_product_conversion(uuid)','erp.propagate_conversion_hpp_for_po(uuid)',
          'erp.compute_po_hpp_gl_targets_v2620d(uuid)','erp.bc_value_custody_v1(jsonb,uuid)',
          'erp.bc_reverse_v1(jsonb,uuid)','erp.sync_material_cost_revaluation(uuid)','erp.run_v268_financial_report_checks()',
          'erp.reverse_product_conversion(uuid,text)','erp.compute_non_po_product_hpp_targets_v2620f(uuid)',
          'erp.compute_non_po_product_hpp_book_v2620f(uuid)','erp.assert_non_po_product_hpp_target_book_v2620f(uuid)',
          'erp.sync_non_po_product_hpp_to_gl_v2620f(uuid,date,text,uuid,text)',
          'erp.post_rework_completion(uuid)','erp.reverse_rework_completion(uuid,text)','erp.assert_new_stock_cutoff_coverage_v1()']+redye.REPLACED+pocket.REPLACED
NEW_TABLES=['be_execution_context_v1','be_conversion_sources_v1','be_conversion_returns_v1',
            'be_conversion_cost_sources_v1','be_conversion_cost_events_v1','be_nonpo_transfer_events_v1','be_rework_targets_v1','be_redye_services_v1','be_redye_price_events_v1']+pocket.TABLES
OBJECTS=[ROOT/f'scripts/cp6_be_objects_{part}.sql' for part in ('conversion','cost','nonpo','rework','redye','pocket')]

def objects():return '\n'.join(p.read_text().rstrip() for p in OBJECTS)

def new_functions():
    return [m.group(1) for m in re.finditer(r'(?i)create or replace function ((?:erp|public)\.[a-z0-9_]+)\(',objects())]+['erp.be_propagate_nonpo_v1']

def old_definition(path,name):
    return last_definition(path,name,text=re.sub(r'(?i)create function erp\.', 'CREATE OR REPLACE FUNCTION erp.',path.read_text()))

def replace_count(text,old,new,count,label):
    assert text.count(old)==count,(label,old[:100],text.count(old))
    return text.replace(old,new)

def conversion():
    return substitute(last_definition(AC,'post_product_conversion'),[
      ("where fl.product_id=h.from_product_id and fl.po_id is null\n",
       "where fl.product_id=h.from_product_id and fl.po_id is null and not erp.be_nonpo_admitted_v1(h.id)\n"
       "      and (not exists(select 1 from erp.be_conversion_sources_v1 where conversion_id=h.id)\n"
       "        or fl.id=(select source_lot_id from erp.be_conversion_sources_v1 where conversion_id=h.id))\n"),
      ("where fl.product_id=h.from_product_id and fl.po_id is not null\n",
       "where fl.product_id=h.from_product_id and (fl.po_id is not null or erp.be_nonpo_admitted_v1(h.id))\n"
       "      and (not exists(select 1 from erp.be_conversion_sources_v1 where conversion_id=h.id)\n"
       "        or fl.id=(select source_lot_id from erp.be_conversion_sources_v1 where conversion_id=h.id))\n"),
      ('where a.conversion_id=h.id order by fl.po_id','where a.conversion_id=h.id and fl.po_id is not null order by fl.po_id'),
      ('end\n$function$;',
       "  if erp.be_nonpo_admitted_v1(h.id) then perform erp.be_nonpo_sync_all_v1(erp._cp3_business_date(h.physical_at),'PRODUCT_CONVERSION',h.id,'Konversi non-PO');end if;\nend\n$function$;")
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
      ("    )::numeric source_cost\n", "      +erp.be_po_extra_v1(s.po_id)+erp.be_redye_po_cost_v1(s.po_id)\n    )::numeric source_cost\n"),
      ('+a.conversion_cost_allocated/nullif(a.qty_pcs,0)', '+erp.be_allocation_extra_v1(a.id)/nullif(a.qty_pcs,0)'),
      ('or abs(ch.total_cost-fl.initial_qty_pcs\n      *coalesce(correction.corrected_hpp,om.unit_hpp))>0.000001',
       'or abs(ch.total_cost-erp.be_pocket_opening_extra_v1(oi.id)-fl.initial_qty_pcs\n      *coalesce(correction.corrected_hpp,om.unit_hpp))>0.000001'),
      ('where s.po_id is null or d.id is null or d.po_id is distinct from s.po_id',
       'where (s.po_id is null and not erp.be_nonpo_admitted_v1(c.id)) or d.id is null or d.po_id is distinct from s.po_id'),
      ('Every posted conversion must be PO-sourced, value-preserving, rooted, and represented by exact OUT/IN facts with current descendant HPP',
       'Every posted conversion has an admitted source, exact OUT/IN facts, rooted lineage and current HPP equal to source plus linked cost less recovery')],'BE source and lineage detectors')
    checks=pocket.filter_native(checks)
    nonpo_propagate=substitute(propagate,[('erp.propagate_conversion_hpp_for_po(p_po_id uuid)','erp.be_propagate_nonpo_v1()'),
      ("or s.po_id is null or d.po_id is distinct from s.po_id","or not erp.be_nonpo_admitted_v1(c.id) or d.po_id is distinct from s.po_id"),
      ("raise exception 'CONVERSION_LINEAGE_ORPHAN_OR_CYCLE: PO % conversion graph is not rooted and acyclic',p_po_id;",
       "raise exception 'BE_NON_PO_LINEAGE_ORPHAN_OR_CYCLE';")],'BE non-PO propagation')
    nonpo_propagate=replace_count(nonpo_propagate,'po_id=p_po_id','po_id is null',4,'BE non-PO roots')
    nonpo_propagate=replace_count(nonpo_propagate,"lot_origin='PRODUCTION'","lot_origin not in('CONVERSION','VOIDED_PRODUCTION')",2,'BE opening/return roots')
    nonpo_propagate=replace_count(nonpo_propagate,"lot_origin in('PRODUCTION','CONVERSION')","lot_origin<>'VOIDED_PRODUCTION'",1,'BE lock all non-PO')
    nonpo_target=substitute(old_definition(F,'compute_non_po_product_hpp_targets_v2620f'),[
      ('coalesce(hv.total_cost,0)::numeric raw_total,',
       "(case when fl.lot_origin<>'CONVERSION' or exists(select 1 from erp.product_conversion_allocations a join erp.product_conversions c on c.id=a.conversion_id\n"
       "       where a.destination_lot_id=fl.id and c.status='POSTED') then coalesce(hv.total_cost,0) else 0 end\n"
       "     -coalesce((select sum(a.qty_pcs*(hv.total_cost/nullif(hv.qty_basis_pcs,0))) from erp.product_conversion_allocations a\n"
       "       join erp.product_conversions c on c.id=a.conversion_id where a.source_lot_id=fl.id and c.status='POSTED'),0))::numeric raw_total,"),
      ("and fl.lot_origin not in('CONVERSION','VOIDED_PRODUCTION')","and fl.lot_origin<>'VOIDED_PRODUCTION'")],'BE non-PO source target')
    nonpo_book=substitute(old_definition(F,'compute_non_po_product_hpp_book_v2620f'),[
      ("    and e.source_type<>'PRODUCT_CONVERSION'\n    and not(e.source_type='JOURNAL_REVERSAL'\n      and o.source_type='PRODUCT_CONVERSION')",'')],'BE include real SKU value transfers')
    guards=[]
    for name in ('assert_non_po_product_hpp_target_book_v2620f','sync_non_po_product_hpp_to_gl_v2620f'):
      body=substitute(old_definition(F,name),[
        ('where(s.po_id is null or d.po_id is null)',
         'where(s.po_id is null or d.po_id is null) and not erp.be_nonpo_admitted_v1(c.id)')],'BE non-PO admission '+name)
      if name.startswith('sync_'):
        body=substitute(body,[("  if exists(\n",
          "  if not erp.be_nonpo_in_sync_v1() and exists(select 1 from erp.be_conversion_sources_v1 be_source\n"
          "      join erp.fg_lots be_lot on be_lot.id=be_source.source_lot_id where be_lot.po_id is null) then\n"
          "    perform erp.be_nonpo_sync_all_v1(p_effective_date,p_trigger_source_type,p_trigger_source_id,p_reason);return;\n"
          "  end if;\n  if exists(\n")],'BE atomic non-PO graph sync')
      guards.append(body)
    inverse=substitute(last_definition(AC,'reverse_product_conversion'),[
      ("  if v_journal is not null then perform erp.reverse_journal(v_journal,p_reason); end if;",
       "  for r in select e.journal_id from erp.be_nonpo_transfer_events_v1 e join erp.journal_entries j on j.id=e.journal_id\n"
       "    where e.conversion_id=h.id and j.status='POSTED' order by e.created_at desc,e.id desc loop\n"
       "    perform erp.reverse_journal(r.journal_id,p_reason);\n  end loop;\n"
       "  if v_journal is not null then perform erp.reverse_journal(v_journal,p_reason); end if;"),
      ("  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason)",
       "  if erp.be_nonpo_admitted_v1(h.id) then perform erp.be_nonpo_sync_all_v1(erp._cp3_business_date(current_timestamp),'PRODUCT_CONVERSION_REVERSE',h.id,p_reason);end if;\n"
       "  insert into erp.audit_logs(entity_type,entity_id,action,changed_by,change_reason)")],'BE non-PO inverse')
    complete=substitute(last_definition(AV,'post_rework_completion'),[
      ('end\n$function$;', '  perform erp.be_complete_rework_target_v1(r.id);\nend\n$function$;')],'BE atomic rework target')
    reverse_rework=substitute(last_definition(AC,'reverse_rework_completion'),[
      ("  if r.good_fg_lot_id is not null then\n    if erp.fg_lot_has_active_downstream",
       "  perform erp.be_reverse_rework_target_v1(r.id,p_reason);\n  if r.good_fg_lot_id is not null then\n    if erp.fg_lot_has_active_downstream")],'BE reverse child conversion before rework')
    coverage=substitute(last_definition(BC,'assert_new_stock_cutoff_coverage_v1'),[
      ('"erp.bc_customer_custody_v1.product_id":',
       '"erp.be_pocket_sewing_v1.product_id":{"class":"SOURCE_DOCUMENT","reason":"Evidence of a sold SKU before cutover; no new stock identity is created"},"erp.be_rework_targets_v1.target_product_id":{"class":"SOURCE_DOCUMENT","reason":"Requested rework/redye target; checked as NEW_STOCK when the native GOOD lot is converted atomically"},"erp.bc_customer_custody_v1.product_id":')],'BE target identity coverage')
    grants=r"""do $grants$
declare t text;f text;
begin
 foreach t in array array['be_execution_context_v1','be_conversion_sources_v1','be_conversion_returns_v1',
   'be_conversion_cost_sources_v1','be_conversion_cost_events_v1','be_nonpo_transfer_events_v1','be_rework_targets_v1','be_redye_services_v1','be_redye_price_events_v1','be_pocket_usage_v1','be_pocket_sewing_v1','be_pocket_source_events_v1','be_pocket_target_events_v1','be_pocket_receipt_origins_v1'] loop
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
      objects(),conversion(),propagate,target,recover,reverse,recost,checks,nonpo_propagate,nonpo_target,nonpo_book,*guards,inverse,
      complete,reverse_rework,coverage,redye.build(old_definition),pocket.build(),grants,
      "insert into erp.schema_migrations(version,description) values('v2.6.20be','BE development family: SKU conversion, rework/redye and pocket cutover');",
      'commit;',''])

if __name__=='__main__':
    text=build()
    if '--check' in sys.argv:assert OUT.read_text()==text,'BE_BUILD_STALE'
    else:OUT.write_text(text)
    print(OUT.relative_to(ROOT),len(text),hashlib.sha256(text.encode()).hexdigest())
