"""Observe the PO inputs reached by the prepared SKU Native sync expansion.

Source-only derivation. The old helpers, Native sync and admission stay exact.
All columns, timestamps, immutable histories and multiplicity are retained.
"""
from pathlib import Path
import importlib.util

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('global_original_SKU_routes',HERE/'routes.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)

# Output key, source CTE, physical relation. All are full original rows.
OBSERVATIONS=(
 ('orders','po_orders','production_orders'),
 ('cutting_groups','po_groups','cutting_groups'),
 ('cutting_batches','po_batches','cutting_batches'),
 ('cutting_rolls','po_rolls','cutting_group_rolls'),
 ('cutting_yields','po_yields','cutting_roll_yields'),
 ('cutting_corrections','po_corrections','cutting_qty_correction_lines'),
 ('qc_items','po_qc','qc_inspection_items'),
 ('sewing_events','po_terminal','sewing_terminal_events'),
 ('lot_states','po_lot_states','po_hpp_gl_lot_state_v1'),
 ('material_states','po_material_states','po_hpp_gl_material_state_v1'),
 ('hpp_events','po_hpp_events','po_hpp_gl_events'),
 ('pocket_destinations','po_destinations','pocket_period_destinations'),
 ('pocket_pools','po_pools','pocket_periods'),
 ('pocket_events','po_pool_events','pocket_period_events'),
 ('pocket_sources','po_pool_sources','pocket_period_sources'),
 ('pocket_usages','po_usages','be_pocket_usage_v1'),
 ('pocket_usage_events','po_usage_events','be_pocket_source_events_v1'),
 ('adjustments','po_adjustments','material_adjustments'),
 ('adjustment_items','po_adjustment_items','material_adjustment_items'),
 ('adjustment_purposes','po_purposes','bc_adjustment_purposes_v1'),
 ('adjustment_revaluations','po_adjustment_facts','material_adjustment_revaluation_facts'),
 ('contractor_issues','po_issues','contractor_material_issues'),
 ('contractor_issue_items','po_issue_items','contractor_material_issue_items'),
 ('material_movements','po_movements','material_stock_movements'),
 ('material_revaluations','po_revaluations','material_cost_revaluation_events'),
 ('materials','po_materials','materials'),
 ('input_journals','po_input_journals','journal_entries'),
 ('input_journal_lines','po_input_lines','journal_lines'),
 ('account_mappings','po_mappings','accounting_account_mappings'),
 ('accounts','po_accounts','chart_accounts'),
 ('invoice_context','po_invoice_context','invoice_recost_execution_context'),
)


def derive():
    original,prior=base.derive();result=dict(original);routes=[]
    def change(name,before,after,label):
        base.require(result[name].count(before)==1 and after not in result[name],
            'GLOBAL_SKU_PO_EXACT_ROUTE:'+label)
        result[name]=result[name].replace(before,after,1)
        routes.append(dict(helper=name,before=before,after=after,label=label))
    anchor="  select 'LOT'::text,l.id,'PRODUCT'::text,l.product_id from erp.fg_lots l\n"
    edges="""  union select 'PO_HPP_EVENT',e.id,'PO',e.po_id from erp.po_hpp_gl_events e
  union select 'PO_HPP_EVENT',e.id,'JOURNAL',e.journal_entry_id from erp.po_hpp_gl_events e
  union select 'PO',s.po_id,'LOT',s.lot_id from erp.po_hpp_gl_lot_state_v1 s
"""
    change('scope',anchor,anchor+edges,'immutable_PO_state_event_and_journal_identities')
    change('capture',' with domain as(',' with recursive domain as(','finite_immutable_reversal_closure')
    anchor=' facts as(select jsonb_build_object(\n'
    change('capture',anchor,(HERE/'po_capture_ctes.sql').read_text()+anchor,'complete_PO_read_dependencies')
    before="  'po_states',coalesce((select jsonb_agg(to_jsonb(s)order by s.po_id)from erp.po_hpp_gl_state s where s.po_id in(select po_id from lots)),'[]'),\n"
    after=before.replace('select po_id from lots','select id from po_ids')
    change('capture',before,after,'complete_direct_PO_identity_states')
    # Keep every jsonb_build_object below PostgreSQL's argument count limit.
    # Keys are disjoint, so concatenation cannot overwrite an old observation.
    parts=[]
    for offset in range(0,len(OBSERVATIONS),16):
        pairs=["'PO_"+name+"',coalesce((select jsonb_agg(to_jsonb(t)order by to_jsonb(t)::text collate \"C\")from "+cte+" t),'[]')"
            for name,cte,_ in OBSERVATIONS[offset:offset+16]]
        parts.append(' || jsonb_build_object(\n  '+',\n  '.join(pairs)+'\n )')
    anchor="  'period',(select to_jsonb(c)from erp.accounting_period_control c where singleton_id=1)) value)\n"
    change('capture',anchor,anchor.replace(' value)',''.join(parts)+' value)'),
        'thirty_one_full_PO_input_and_output_rowsets')
    recovered=dict(result)
    for route in reversed(routes):
        base.require(recovered[route['helper']].count(route['after'])==1,'GLOBAL_SKU_PO_INVERSE_ROUTE')
        recovered[route['helper']]=recovered[route['helper']].replace(route['after'],route['before'],1)
    base.require(recovered==original and result['authority']==original['authority']
        and result['inspect']==original['inspect']and len(routes)==5,'GLOBAL_SKU_PO_ORIGINALS_NOT_RECOVERED')
    return result,dict(status='GLOBAL_SKU_PO_SOURCE_OBSERVATIONS_PREPARED_NOT_INSTALLED',
        retained_SKU_helpers=prior['derived_helpers'],derived_helpers={k:base.pin(v.encode())for k,v in result.items()},
        exact_routes=routes,new_PO_observations=len(OBSERVATIONS),new_PO_identity_edges=3,
        all_source_columns_and_timestamp_fields_retained=True,original_Native_writers_unchanged=True,
        original_inspector_and_all_refusals_unchanged=True,current_parent_ROOT_adopted=False,
        actual_Native_cases=0,production_go=False,independent_acceptance=False)
