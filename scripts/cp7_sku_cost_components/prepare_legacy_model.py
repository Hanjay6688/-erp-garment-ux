"""Exact Native physical/legacy bodies inside the retained explicit PG17 model.

This does not substitute for actual ERP/Auth, race or owning restore evidence.
All prerequisite types, helpers, fixture dates, source identities and providers
are collected together before execution. The counter keeps the prior SQL.
"""
from pathlib import Path
from hashlib import sha256
import json,os,sys
import prepare_model,legacy_delta
from valuation_delta import Derivation
from financial_delta import parent

HERE=Path(__file__).resolve().parent
TABLES=('erp.rework_orders','erp.be_rework_targets_v1','erp.be_conversion_returns_v1',
 'erp.bc_outstanding_returns_v1','erp.bc_return_lots_v1','erp.materials','erp.uom_definitions')
HELPERS=('erp.bd_uuid_v1(jsonb,text,boolean)','erp.bd_qty_v1(jsonb,text)','erp.bd_at_v1(text,text)',
 'erp.bc_uuid_v1(jsonb,text,boolean)','erp.bc_text_v1(jsonb,text,boolean,integer)','erp.bc_parse_qty_v1(uuid,jsonb,text)',
 'erp._cp3_assert_closed_json_object(jsonb,text[],text[],text)','erp._cp3_business_date(timestamp with time zone)',
 'erp.pocket_period_lock_v1()','erp.assert_product_identity_time(uuid,timestamp with time zone,text)',
 'erp.fg_lot_has_active_downstream(uuid,text,text,uuid)','erp.be_nonpo_admitted_v1(uuid)',
 'cp7_sku_conversion.manual_allocation_v1(uuid,uuid,uuid,integer,timestamp with time zone)',
 'cp7_sku_conversion.assert_group_reverse_v1(uuid)',
 'cp7_sku_conversion.stock_v1(uuid,uuid)','cp7_sku_conversion.revision_v1(uuid,uuid,uuid)',
 'erp.post_product_conversion(uuid)','erp.reverse_product_conversion(uuid,text)',
 'erp.save_product_conversion_action_v1(text,jsonb,uuid)',
 'erp.be_complete_rework_target_v1(uuid)','erp.be_reverse_rework_target_v1(uuid,text)')

def prepare(destination):
    full=os.environ.get('CP7_COST_LEGACY_FULL')=='1'
    counter=os.environ.get('CP7_COST_LEGACY_COUNTER')=='1'
    more=os.environ.get('CP7_COST_LEGACY_MORE_ONLY')=='1'
    if more and(full or counter):raise ValueError('LEGACY_FOLLOWUP_REQUIRES_ISOLATED_REPAIR')
    if full and counter:raise ValueError('LEGACY_COUNTER_REQUIRES_ISOLATED_INPUT')
    expected=['CP7_COST_REBALANCE','CP7_COST_MONEY','CP7_COST_INVERSE_REPAIR','CP7_COST_BASE_MONEY']
    expected+=['CP7_COST_BASE_FULL','CP7_COST_FULL_WITH_CHAINS']if full else['CP7_COST_CHAIN_MODEL','CP7_COST_MONEY_CREDIT_ONLY','CP7_COST_BASE_CENT_ONLY']
    if not all(os.environ.get(k)=='1'for k in expected)or os.environ.get('CP7_COST_BASE_FORWARD')=='1':
        raise ValueError('LEGACY_MODEL_COMPLETE_EXACT_INPUT_REQUIRED')
    destination=Path(destination);prepare_model.prepare(destination)
    path=destination/'COST_MODEL_INPUT.json';x=json.loads(path.read_bytes())
    raw=(Path(os.environ['CP7_SKU_PARENT_ORIGINALS'])/'CP7_SKU_MANAGED_RECOVERY_NATIVE27.json').read_bytes()
    if sha256(raw).hexdigest()!='5e22077e71e34add6fd0627c89e9d21a2235f463818e45b233c7619bcfb0d48f':raise ValueError('LEGACY_NATIVE_ORIGINAL_CHANGED')
    catalog=json.loads(raw)['committed']['SKU_NATIVE7_COST5_RACES3_PERMISSION_WAITS7_RECOVERY_BUSY1_AUTH_BROWSER4']['Native_to_copy_handoff']['raw_current_catalog']
    for table in TABLES:
        x['columns'][table]=sorted([v for k,v in catalog['columns'].items()if k.startswith(table+':')],key=lambda v:v[1])
        if not x['columns'][table]:raise ValueError('LEGACY_TYPED_PREREQUISITE_MISSING:'+table)
    x['legacy_helpers']={s:catalog['functions'][s][0]for s in HELPERS}
    private=x['private_inverse_definition']['cp7_sku_conversion.action_v1(text,jsonb,uuid)']
    x['legacy_definitions']={s:catalog['functions'][s][0]for s in legacy_delta.ORIGINALS}
    x['legacy_raw_revision_original']=catalog['functions']['erp.be_source_revision_v1(uuid,uuid)'][0]
    x['legacy_definitions']['cp7_sku_conversion.action_v1(text,jsonb,uuid)']=private
    x['legacy_counter']=counter
    x['legacy_more_only']=more
    private_parent=parent('private_delta.py')
    x['legacy_private_preview']=private_parent.patched({s:catalog['functions'][s][0]for s in private_parent.SIGNATURES})[
        'cp7_sku_conversion.preview_v1(jsonb)']
    if not counter:
        x['legacy_definitions'],x['legacy_routes']=legacy_delta.derive(catalog,private)
        x['cost_ddl']=legacy_delta.bind_base_transition(x['cost_ddl'])+'\n'+(HERE/'legacy.sql').read_text()
    x['legacy_native_source_pins']={s:dict(bytes=len(v.encode()),sha256=sha256(v.encode()).hexdigest())
        for s,v in x['legacy_helpers'].items()}
    x['legacy_model_providers']=['authority and actor','permission visibility toggle','idempotency storage',
        'journal storage and reversal','known PO/laundry inputs','the retained historical fixture and monetary origins']
    x['legacy_prerequisites']=dict(all_columns_from_exact_original=True,all_helpers_from_exact_original=True,
        physical_post_and_reverse_bodies_unchanged=True,fixture_at='2026-01-03T00:00:00Z',
        source_and_target_effective_from='2020-01-01T00:00:00Z',backend_context='original typed private and BE execution tables',
        authority='explicit model providers; no Auth acceptance')
    path.write_text(json.dumps(x,sort_keys=True)+'\n')
    harness=destination/'test_cost_successor.mjs';before=harness.read_text();d=Derivation(before)
    d.once(' const costSnapshot=async()=>{',(HERE/'legacy_model_setup.mjs.inc').read_text()+'\n const costSnapshot=async()=>{',
           'collect every exact Native helper and explicit model fixture before the rollback baseline')
    cases=(HERE/'legacy_cases.mjs.inc').read_text().replace('// LEGACY_FOLLOWUP_CONTROLS',
        (HERE/'legacy_followup_cases.mjs.inc').read_text())
    if full:
        cases=cases.replace('baseCentFindings','legacyFindings')
        d.once(' const report={costChainFindings,currentInverseFindings,moneyFindings,moneyCreditFindings,baseCoreFindings,baseFollowupFindings,status:',
               cases+'\n const report={costChainFindings,currentInverseFindings,moneyFindings,moneyCreditFindings,baseCoreFindings,baseFollowupFindings,legacyFindings,status:',
               'unfiltered full monetary controls plus exact Native legacy body controls')
        d.once('MODELED_COMPLETE_BASE_AND_COST_MONEY_CONTROLS_PASS_NOT_NATIVE','MODELED_COMPLETE_MONEY_AND_NATIVE_LEGACY_BODIES_PASS_NOT_ERP',
               'complete explicit model does not imply actual ERP acceptance')
    else:
        d.once((HERE/'base_money_cases.mjs.inc').read_text(),cases,'focused legacy controls without repeating skipped earlier case credit')
        d.once('MODELED_BASE_SOURCE_MONEY_REPAIR_CONTROLS_PASS_NOT_NATIVE',
               'MODELED_NATIVE_LEGACY_COUNTER_NOT_ACCEPTED'if counter else'MODELED_NATIVE_LEGACY_BODIES_REPAIR_NOT_ERP',
               'counter and repair are separate exact inputs and results')
    if d.inverse()!=before:raise ValueError('LEGACY_MODEL_HARNESS_NOT_REVERSIBLE')
    harness.write_text(d.source)
    print(json.dumps(dict(status='EXACT_NATIVE_LEGACY_MODEL_INPUT_PREPARED',counter=counter,full=full,
        typed_tables=len(x['columns']),unchanged_helpers=len(x['legacy_helpers']),legacy_definitions=len(x['legacy_definitions']),
        input_bytes=path.stat().st_size,input_sha256=sha256(path.read_bytes()).hexdigest(),actual_ERP_cases=0)))

if __name__=='__main__':prepare(sys.argv[1])
