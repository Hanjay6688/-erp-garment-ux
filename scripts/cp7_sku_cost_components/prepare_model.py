"""Bind the full retained typed fixture and exact sources before one PG17 run."""
from hashlib import sha256
from pathlib import Path
import importlib.util,json,os,sys
from valuation_delta import derive,Derivation
from financial_delta import derive_consumers,derive_credit,parent

HERE=Path(__file__).resolve().parent
PREVIOUS=HERE.parent/'cp7_sku_moving_average'
COST_FUNCTIONS=('erp.be_conversion_extra_v1(uuid)','erp.be_allocation_extra_v1(uuid)',
 'erp.be_in_context_v1()','erp.be_nonpo_in_sync_v1()','erp.be_propagate_nonpo_v1()',
 'erp.be_nonpo_prepare_transfers_v1(date)','erp.be_nonpo_sync_all_v1(date,text,uuid,text)',
 'erp.be_reconcile_cost_document_v1(uuid,date)')


def prepare(destination):
    if os.environ.get('CP7_COST_MONEY_CREDIT_ONLY')=='1'and not all(os.environ.get(k)=='1'for k in('CP7_COST_CHAIN_MODEL','CP7_COST_INVERSE_REPAIR','CP7_COST_MONEY')):
        raise ValueError('COST_MONEY_CREDIT_ISOLATION_REQUIRES_COMPLETE_CHAIN_MONEY_INPUT')
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
    spec=importlib.util.spec_from_file_location('cost_prior_model',PREVIOUS/'prepare_consumer_model.py')
    prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior);input=prior.prepare()
    raw=(Path(os.environ['CP7_SKU_PARENT_ORIGINALS'])/'CP7_SKU_MANAGED_RECOVERY_NATIVE27.json').read_bytes()
    if sha256(raw).hexdigest()!='5e22077e71e34add6fd0627c89e9d21a2235f463818e45b233c7619bcfb0d48f':raise ValueError('COST_NATIVE_ORIGINAL_CHANGED')
    catalog=json.loads(raw)['committed']['SKU_NATIVE7_COST5_RACES3_PERMISSION_WAITS7_RECOVERY_BUSY1_AUTH_BROWSER4']['Native_to_copy_handoff']['raw_current_catalog']
    for table in ('erp.be_execution_context_v1','erp.bc_adjustment_purposes_v1','erp.bc_documents_v1',
                  'erp.hpp_version_components','erp.be_nonpo_transfer_events_v1'):
        input['columns'][table]=sorted([v for k,v in catalog['columns'].items()if k.startswith(table+':')],key=lambda v:v[1])
        if not input['columns'][table]:raise ValueError('COST_TYPED_TABLE_MISSING:'+table)
    input['cost_functions']={sig:catalog['functions'][sig][0]for sig in COST_FUNCTIONS}
    input['cost_function_originals']={sig:catalog['functions'][sig]for sig in COST_FUNCTIONS}
    input['po_extra_original']=catalog['functions']['erp.be_po_extra_v1(uuid)']
    input['definitions'],consumer_routes=derive_consumers({sig:catalog['functions'][sig][0]for sig in parent('consumer_delta.py').SIGNATURES})
    input['credit_definitions'],credit_routes=derive_credit({sig:catalog['functions'][sig][0]for sig in parent('credit_delta.py').SIGNATURES})
    input['valuation_definitions'],valuation_routes=derive()
    from private_inverse_delta import derive as derive_inverse_action,SIGNATURE as inverse_signature
    originals={sig:catalog['functions'][sig][0]for sig in parent('private_delta.py').SIGNATURES}
    inverse_action,inverse_routes=derive_inverse_action(originals)
    input['private_inverse_definition']={inverse_signature:inverse_action}
    input['private_inverse_routes']=inverse_routes
    input['cost_ddl']=(HERE/'costs.sql').read_text()
    input['cost_ddl']+='\n'+(HERE/'inverse_rebalance.sql').read_text()
    if os.environ.get('CP7_COST_REBALANCE')=='1':
        from source_delta import derive as derive_source,SIGNATURE
        input['cost_functions'][SIGNATURE],source_routes=derive_source(catalog['functions'][SIGNATURE][0])
        input['cost_ddl']+='\n'+(HERE/'source_rebalance.sql').read_text()
        input['source_rebalance_derivation']=source_routes
        input['cost_rebalance_enabled']=True
    if os.environ.get('CP7_COST_MONEY')=='1':
        if not input.get('cost_rebalance_enabled'):raise ValueError('COST_MONEY_REQUIRES_COMPLETE_SOURCE_REBALANCE')
        from money_delta import definitions as money_definitions,credit_definitions as money_credit
        money_cost,input['valuation_definitions'],money_routes=money_definitions(input['valuation_definitions'])
        input['credit_definitions'],money_credit_routes=money_credit(input['credit_definitions'])
        input['cost_ddl']+='\n'+(HERE/'money.sql').read_text()+'\n'+'\n'.join(money_cost.values())
        input['money_derivations']=dict(cost=money_routes,credit=money_credit_routes)
        input['cost_money_enabled']=True
    input['cost_source_manifest']={str(p.relative_to(HERE)):dict(bytes=len(p.read_bytes()),sha256=sha256(p.read_bytes()).hexdigest())
        for p in sorted(HERE.iterdir())if p.is_file()}
    input['cost_derivations']=dict(valuation=valuation_routes,consumer=consumer_routes,credit=credit_routes)
    out=destination/'COST_MODEL_INPUT.json';out.write_text(json.dumps(input,sort_keys=True)+'\n')

    original=(PREVIOUS/'test_consumers_pg17.mjs').read_bytes()
    if sha256(original).hexdigest()!='798a9b8f11d8bdd3bdd4b4f1246a463ade32a335a9135a0478d8d4ee6b3e5b08':raise ValueError('COST_MODEL_HARNESS_CHANGED')
    credit_original=(PREVIOUS/'test_credit_projection_pg17.mjs').read_bytes()
    if sha256(credit_original).hexdigest()!='1d210889a0c2777fb245ce62c2bb62a300b7fccdf73fc047a05bd190c81a430f':raise ValueError('COST_CREDIT_MODEL_CHANGED')
    credit=Derivation(credit_original.decode())
    credit.once('assert.equal(p.economic_return_components.length,3);',"""assert.deepEqual(p.economic_return_components.map(c=>[c.component_kind,c.root_lot_id,Number(c.component_units),Number(c.hpp_per_pcs)]),[
   ['BASE',x.root10,.25,10],['BASE',x.root30,.25,30],['BASE',x.root50,.5,50],['COST',x.converted,.5,0]]);""",'all original three roots plus the exact zero cost ownership root')
    credit.once(' create function erp.post_journal(p_type text,p_id uuid,p_date date,p_reason text,p_lines jsonb)returns uuid language plpgsql as $$',
        """ create function public.model_journal_account(line jsonb)returns uuid language plpgsql stable as $$
 declare resolved uuid;begin
  if line?'account_id'then
   if line?'mapping_key'then raise exception 'MODEL_ACCOUNT_ID_AND_MAPPING_BOTH_SET';end if;
   select id into strict resolved from erp.chart_accounts where id=(line->>'account_id')::uuid and is_active and is_postable;
   return resolved;
  end if;
  return cp7_credit.account_by_mapping_v1(line->>'mapping_key');end$$;
 create function erp.post_journal(p_type text,p_id uuid,p_date date,p_reason text,p_lines jsonb)returns uuid language plpgsql as $$""",'explicit typed Native journal account storage provider')
    credit.once("values(gen_random_uuid(),j,cp7_credit.account_by_mapping_v1(l->>'mapping_key'),",'values(gen_random_uuid(),j,public.model_journal_account(l),','retain both supported Native account representations')
    if credit.inverse()!=credit_original.decode():raise ValueError('COST_CREDIT_HARNESS_NOT_REVERSIBLE')
    credit_path=destination/'test_credit_cost_successor.mjs';credit_path.write_text(credit.source)
    d=Derivation(original.decode())
    d.once("from './test_credit_projection_pg17.mjs'",'from '+json.dumps(str(credit_path.resolve())),'retained credit harness with exact additional cost root assertion')
    d.once('const here = dirname(fileURLToPath(import.meta.url));','const here = '+json.dumps(str(PREVIOUS))+';','same exact parent DDL path')
    d.once(' await db.exec(ddl);',""" await db.exec(ddl);
 await db.exec(input.cost_functions['erp.be_conversion_extra_v1(uuid)']);
 await db.exec(input.cost_functions['erp.be_allocation_extra_v1(uuid)']);
 await db.exec(input.cost_ddl);
 for(const definition of Object.values(input.valuation_definitions))await db.exec(definition);""",'complete candidate cost DDL before any cases')
    d.once(" assert.deepEqual(await values(x.source),{hpp:60,fg:60,cogs:0,other:0});", """ await query('update erp.product_conversion_allocations set conversion_cost_allocated=0 where id=$1',[x.allocation]);
 await query('update erp.fg_lots set source_lot_id=$1 where id=$2',[x.root10,x.converted]);
 await query('select cp7_sku_conversion.finalize_costs_v3($1)',[x.group]);
 assert.deepEqual(await values(x.source),{hpp:60,fg:60,cogs:0,other:0});""",'zero cost root exists before any sale transfer or invoice')
    d.once(" const report={status:'POSTGRES17_EXACT_CONSUMER_SQL_CONTROLS_PASS_NOT_NATIVE'",(HERE/'cost_cases.mjs.inc').read_text()+"\n const report={status:'POSTGRES17_COST_SUCCESSOR_MODELED_CONTROLS_PASS_NOT_NATIVE'",'new cost regression and chain cases after original controls')
    if os.environ.get('CP7_COST_CHAIN_MODEL')=='1'or os.environ.get('CP7_COST_FULL_WITH_CHAINS')=='1':
        if os.environ.get('CP7_COST_CHAIN_MODEL')=='1':
            d.once(" console.log(JSON.stringify({control:label,state:'ENTER'}));",
                " if(!label.startsWith('CHAIN:'))return;\n console.log(JSON.stringify({control:label,state:'ENTER'}));",'isolated new chain controls, no repeated prior case credit')
        d.once(" const report={status:'POSTGRES17_COST_SUCCESSOR_MODELED_CONTROLS_PASS_NOT_NATIVE'",
            (HERE/'chain_cases.mjs.inc').read_text()+"\n const report={costChainFindings,status:'POSTGRES17_COST_CHAIN_COUNTEREXAMPLES_CONFIRMED_NOT_ACCEPTED'",'retain first independently expected downstream failures')
        if os.environ.get('CP7_COST_REBALANCE')=='1':
            old="""   const before=await costSnapshot();let failure;
   await db.exec('savepoint cost_chain_reprice');
   try{await costReconcile(4);}catch(error){failure={message:error.message,code:error.code,where:error.where};}
   await db.exec('rollback to savepoint cost_chain_reprice');
   assert.deepEqual(await costSnapshot(),before,'Failed later cost correction must restore every modeled table');
   assert(failure?.message.includes('NON_PO_HPP_SOURCE_VALUE_MISMATCH'),JSON.stringify(failure));
   assert(failure.message.includes('target total 37.00, book total '+expectedBook),failure.message);
   costChainFindings.push({caseName,physicalSource,physicalValue:child.physicalValue,
    expectedBefore:{originalProduct:36,descendantProduct:36},expectedAfter:{originalProduct:37,descendantProduct:37},failure,
    complete_modeled_rows_restored:true,product_fix_admitted:false,actual_ERP_cases:0});"""
            d.once(old,(HERE/'chain_repair_checks.mjs.inc').read_text().rstrip(),'same independent expected 37 per SKU now requires successful exact journals')
            d.once("status:'POSTGRES17_COST_CHAIN_COUNTEREXAMPLES_CONFIRMED_NOT_ACCEPTED'","status:'POSTGRES17_COST_CHAIN_SOURCE_REBALANCE_MODELED_PASS_NOT_NATIVE'",'explicit local repair status, no actual acceptance')
            if os.environ.get('CP7_COST_INVERSE_REPAIR')=='1':
                inverse_cases=(HERE/'inverse_cases.mjs.inc').read_text()
                if os.environ.get('CP7_COST_CAPACITY_ONLY')=='1':
                    isolated=Derivation(inverse_cases)
                    isolated.once('for(const physicalSource of[x.root50,x.converted])','for(const physicalSource of[])','skip already executed twelve current-value inverse controls')
                    isolated.once('assert.equal(currentInverseFindings.length,12);','assert.equal(currentInverseFindings.length,0);','no borrowed inverse execution credit')
                    isolated.once('assert.equal(currentInverseFindings.length,13);','assert.equal(currentInverseFindings.length,1);','only the economic capacity refusal executes')
                    if isolated.inverse()!=inverse_cases:raise ValueError('COST_INVERSE_CASE_ISOLATION_NOT_REVERSIBLE')
                    inverse_cases=isolated.source
                d.once(" const report={costChainFindings,status:'POSTGRES17_COST_CHAIN_SOURCE_REBALANCE_MODELED_PASS_NOT_NATIVE'",
                    inverse_cases+"\n const report={costChainFindings,currentInverseFindings,status:'MODELED_CURRENT_VALUE_INVERSE_PASS_NOT_NATIVE'",'current inverse after positive negative zero and fractional cost, unchanged source facts and strict refusals')
                if os.environ.get('CP7_COST_MONEY')=='1':
                    d.once(" const report={costChainFindings,currentInverseFindings,status:'MODELED_CURRENT_VALUE_INVERSE_PASS_NOT_NATIVE'",
                        (HERE/'money_cases.mjs.inc').read_text()+"\n const report={costChainFindings,currentInverseFindings,moneyFindings,status:'MODELED_SOURCE_CENT_CUSTODY_FULL_CONTROLS_PASS_NOT_NATIVE'",'independent fractional source expectations after complete consumer credit and inverse controls')
                    if os.environ.get('CP7_COST_MONEY_CREDIT_ONLY')=='1':
                        d.once(" console.log(JSON.stringify({control:label,state:'ENTER'}));",
                            " if(!label.startsWith('CHAIN: MONEY CREDIT:'))return;\n console.log(JSON.stringify({control:label,state:'ENTER'}));",'execute only new cross-SKU monetary sale and credit cases')
                        for variable,count in [('costChainFindings',2),('currentInverseFindings',12),('currentInverseFindings',13),('moneyFindings',6)]:
                            d.once('assert.equal('+variable+'.length,'+str(count)+');','assert.equal('+variable+'.length,0 /* skipped '+str(count)+' */);','no borrowed skipped '+variable+' '+str(count))
                        d.once(" const report={costChainFindings,currentInverseFindings,moneyFindings,status:'MODELED_SOURCE_CENT_CUSTODY_FULL_CONTROLS_PASS_NOT_NATIVE'",
                            (HERE/'money_credit_cases.mjs.inc').read_text()+'\n'+(HERE/'money_history_case.mjs.inc').read_text()+"\n const report={moneyCreditFindings,status:'MODELED_CROSS_SKU_CENT_CREDIT_CONTROLS_PASS_NOT_NATIVE'",'independent raw credit guard, exact sale return, immutable price history and bounded receipt nesting')
            if os.environ.get('CP7_COST_CENT_COUNTER')=='1':
                retained_counters=(HERE/'cent_inverse_counterexamples.mjs.inc').read_text()
                current_counters=Derivation(retained_counters)
                current_counters.once('assert.equal(Number(book.find(b=>b.product_id===x.target).fg),inverseBook);',
                    'assert.equal(Number(book.find(b=>b.product_id===x.target).fg),70);','current inverse repairs retained source book counterexample')
                current_counters.once('assert.equal(Number(book.find(b=>b.product_id===child.product).fg),70-inverseBook);',
                    'assert.equal(Number(book.find(b=>b.product_id===child.product).fg),0);','current inverse clears descendant book')
                if current_counters.inverse()!=retained_counters:raise ValueError('COST_RETAINED_COUNTER_DERIVATION_NOT_REVERSIBLE')
                d.once(" const report={costChainFindings,status:'POSTGRES17_COST_CHAIN_SOURCE_REBALANCE_MODELED_PASS_NOT_NATIVE'",
                    current_counters.source+"\n const report={costChainFindings,remainingCostGaps,status:'MODELED_SOURCE_CENTS_STILL_REFUSED_CURRENT_INVERSE_REPAIRED_NOT_NATIVE'",'source penny guard unchanged, current inverse checked against the repaired expected values')
    if d.inverse()!=original.decode():raise ValueError('COST_MODEL_HARNESS_NOT_REVERSIBLE')
    (destination/'test_cost_successor.mjs').write_text(d.source)
    print(json.dumps(dict(status='COMPLETE_COST_MODEL_PREPARED',typed_tables=len(input['columns']),
        unchanged_native_cost_functions=len(COST_FUNCTIONS)-(1 if input.get('cost_rebalance_enabled')else 0),
        derived_native_cost_functions=1 if input.get('cost_rebalance_enabled')else 0,changed_valuation_functions=len(input['valuation_definitions']),
        input_bytes=out.stat().st_size,input_sha256=sha256(out.read_bytes()).hexdigest(),actual_ERP_cases=0)))


if __name__=='__main__':prepare(sys.argv[1])
