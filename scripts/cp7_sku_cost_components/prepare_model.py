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
    if os.environ.get('CP7_COST_BASE_FULL')=='1'and(not all(os.environ.get(k)=='1'for k in('CP7_COST_BASE_MONEY','CP7_COST_FULL_WITH_CHAINS','CP7_COST_INVERSE_REPAIR'))or any(os.environ.get(k)=='1'for k in('CP7_COST_CHAIN_MODEL','CP7_COST_MONEY_CREDIT_ONLY','CP7_COST_BASE_CENT_ONLY'))):
        raise ValueError('BASE_MONEY_FULL_REQUIRES_UNFILTERED_COMPLETE_INPUT')
    if os.environ.get('CP7_COST_BASE_MONEY_MORE_ONLY')=='1'and not all(os.environ.get(k)=='1'for k in('CP7_COST_BASE_CENT_ONLY','CP7_COST_BASE_MONEY')):
        raise ValueError('BASE_MONEY_FOLLOWUP_REQUIRES_ISOLATED_BASE_MONEY_MODE')
    if os.environ.get('CP7_COST_BASE_CENT_ONLY')=='1'and os.environ.get('CP7_COST_MONEY_CREDIT_ONLY')!='1':
        raise ValueError('BASE_CENT_COUNTER_REQUIRES_COMPLETE_ISOLATED_MONEY_INPUT')
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
    if os.environ.get('CP7_COST_BASE_MONEY')=='1':
        if not input.get('cost_money_enabled'):raise ValueError('BASE_MONEY_REQUIRES_COMPLETE_COST_MONEY_LAYER')
        from base_money_delta import definitions as base_definitions
        table='cp7_sku_conversion.execution_v1'
        input['columns'][table]=sorted([v for k,v in catalog['columns'].items()if k.startswith(table+':')],key=lambda v:v[1])
        if not input['columns'][table]:raise ValueError('BASE_MONEY_EXACT_EXECUTION_TABLE_REQUIRED')
        input['valuation_definitions'],input['definitions'],input['credit_definitions'],input['base_money_derivations']=base_definitions(
            input['valuation_definitions'],input['definitions'],input['credit_definitions'])
        input['cost_ddl']+='\n'+(HERE/'base_money.sql').read_text()
        input['base_money_enabled']=True
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
    if input.get('base_money_enabled'):
        d.once('const control = async (label, operation) => {','let initializeBaseFixture=async()=>{};\nconst control = async (label, operation) => {',
               'isolated coherent base-money starting facts for each scenario')
        d.once('try { await operation();','try { await initializeBaseFixture(label); await operation();',
               'fixture provenance established before each control, full rollback retained')
        d.once(" await query('select cp7_sku_conversion.finalize_costs_v3($1)',[x.group]);",
            " await query('select cp7_sku_conversion.finalize_costs_v3($1)',[x.group]);\n"+(HERE/'base_money_fixture.mjs.inc').read_text(),
            'explicit retained historical fixture monetary postconditions, not a production backfill')
        d.many("  await query('update erp.hpp_versions set total_cost=80 where id=$1',[x.hpp30]);",
               "  await query('update erp.hpp_versions set total_cost=80 where id=$1',[x.hpp30]);\n  await modelBaseSourcePostcondition(x.root30,80);",2,
               'two original exact-source refusal fixtures retain complete monetary source postconditions')
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
    if os.environ.get('CP7_COST_BASE_FULL')=='1':
        combined=(HERE/'money_credit_cases.mjs.inc').read_text()+'\n'+(HERE/'money_history_case.mjs.inc').read_text()
        combined+='\n'+(HERE/'base_money_cases.mjs.inc').read_text().replace('baseCentFindings','baseCoreFindings')
        combined+='\n'+(HERE/'base_money_followup_cases.mjs.inc').read_text().replace('baseCentFindings','baseFollowupFindings')
        d.once(" const report={costChainFindings,currentInverseFindings,moneyFindings,status:'MODELED_SOURCE_CENT_CUSTODY_FULL_CONTROLS_PASS_NOT_NATIVE'",
               combined+"\n const report={costChainFindings,currentInverseFindings,moneyFindings,moneyCreditFindings,baseCoreFindings,baseFollowupFindings,status:'MODELED_COMPLETE_BASE_AND_COST_MONEY_CONTROLS_PASS_NOT_NATIVE'",
               'unfiltered full prior controls plus monetary credit and new base-custody regressions')
    if os.environ.get('CP7_COST_BASE_CENT_ONLY')=='1':
        d.once("if(!label.startsWith('CHAIN: MONEY CREDIT:'))return;","if(!label.startsWith('CHAIN: BASE CENT:'))return;",
               'isolate only new base-source cent counterexamples')
        d.once('assert.equal(moneyCreditFindings.length,3);','assert.equal(moneyCreditFindings.length,0 /* skipped 3 */);',
               'no borrowed prior credit-case execution')
        d.once('assert.equal(moneyCreditFindings.length,4);','assert.equal(moneyCreditFindings.length,0 /* skipped 4 */);',
               'no borrowed prior receipt-history execution')
        cases='base_money_cases.mjs.inc'if input.get('base_money_enabled')else'base_cent_cases.mjs.inc'
        status='MODELED_BASE_SOURCE_MONEY_REPAIR_CONTROLS_PASS_NOT_NATIVE'if input.get('base_money_enabled')else'MODELED_BASE_SOURCE_CENT_COUNTEREXAMPLES_CONFIRMED_NOT_ACCEPTED'
        if os.environ.get('CP7_COST_BASE_MONEY_MORE_ONLY')=='1':
            if not input.get('base_money_enabled'):raise ValueError('BASE_MONEY_FOLLOWUP_REQUIRES_COMPLETE_BASE_MONEY_INPUT')
            cases='base_money_followup_cases.mjs.inc'
            status='MODELED_BASE_MONEY_CREDIT_AND_REFUSALS_PASS_NOT_NATIVE'
        if os.environ.get('CP7_COST_BASE_FORWARD')=='1':
            if not input.get('base_money_enabled'):raise ValueError('BASE_NATIVE_FORWARD_REQUIRES_BASE_MONEY')
            cases='base_forward_cases.mjs.inc'
            status='MODELED_NATIVE_FORWARD_ORDER_COUNTER_NOT_ACCEPTED'if os.environ.get('CP7_COST_BASE_FORWARD_COUNTER')=='1'else'MODELED_NATIVE_FORWARD_ORDER_REPAIR_NOT_NATIVE'
        d.once(" const report={moneyCreditFindings,status:'MODELED_CROSS_SKU_CENT_CREDIT_CONTROLS_PASS_NOT_NATIVE'",
            (HERE/cases).read_text()+"\n const report={baseCentFindings,status:"+json.dumps(status),
            'retain exact source conservation failures before proposing another change')
    if os.environ.get('CP7_COST_BASE_FORWARD')=='1':
        d.once("  await insert('cp7_sku_conversion.members_v1',{group_id:group,conversion_id:conversion});",
               '  // Native action inserts the member only after its complete physical post returns.',
               'Native posting synchronizes books before the owning action inserts its member')
        d.once("  await insert('erp.product_conversions',{id:conversion,from_product_id:x.target,to_product_id:product,status:'POSTED',physical_at:'2026-01-03T00:00:00Z'});",
               "  await insert('erp.product_conversions',{id:conversion,from_product_id:x.target,to_product_id:product,location_id:x.location,qty_pcs:1,status:'POSTED',physical_at:'2026-01-03T00:00:00Z'});",
               'full Native source target location quantity and date identity in the physical postcondition')
        d.once("  const physicalValue=Number(await scalar('select hpp_per_pcs from erp.hpp_versions where lot_id=$1 and is_current',[physicalSource]));",
               """  await query("insert into cp7_sku_conversion.execution_v1(backend_pid,transaction_id,group_id,mode,source_lot_id,target_id,location_id,qty,physical_at)values(pg_backend_pid(),txid_current(),$1,'POST',$2,$3,$4,1,'2026-01-03T00:00:00Z')",[group,physicalSource,product,x.location]);
  await query('insert into erp.be_execution_context_v1(backend_pid,transaction_id,request_id)values(pg_backend_pid(),txid_current(),$1)',[conversion]);
  const physicalValue=Number(await scalar('select hpp_per_pcs from erp.hpp_versions where lot_id=$1 and is_current',[physicalSource]));""",
               'exact existing private and Native execution-table postconditions before Native physical posting')
        d.once("  await query('select cp7_sku_conversion.finalize_valuation_v2($1)',[group]);",
               """  if(!baseForwardCounter&&physicalSource===x.root50)await checkPendingNativeIdentity(physicalSource,group,conversion);
  await query("select erp.be_nonpo_sync_all_v1('2026-01-03','PRODUCT_CONVERSION',$1,'Native physical post before member')",[conversion]);
  await query('delete from erp.be_execution_context_v1 where backend_pid=pg_backend_pid()and transaction_id=txid_current()');
  await insert('cp7_sku_conversion.members_v1',{group_id:group,conversion_id:conversion});
  await query('select cp7_sku_conversion.finalize_valuation_v2($1)',[group]);
  await query('delete from cp7_sku_conversion.execution_v1 where backend_pid=pg_backend_pid()and transaction_id=txid_current()');""",
               'same exact Native book sync in the real before-member order, then economic finalize')
        d.once(' const baseForwardCounter=true;',
               ' const baseForwardCounter='+('true'if os.environ.get('CP7_COST_BASE_FORWARD_COUNTER')=='1'else'false')+';',
               'explicit first counter versus repaired expected outcome')
    if input.get('base_money_enabled')and 'async function modelNativeInverse(child,physicalSource)'in d.source:
        d.once(' async function modelNativeInverse(child,physicalSource){',
            " async function modelNativeInverse(child,physicalSource){\n  await query(\"insert into cp7_sku_conversion.execution_v1(backend_pid,transaction_id,group_id,mode)values(pg_backend_pid(),txid_current(),$1,'REVERSE')\",[child.group]);",
            'explicit original owning execution-table postcondition before modeled Native inverse')
    if d.inverse()!=original.decode():raise ValueError('COST_MODEL_HARNESS_NOT_REVERSIBLE')
    (destination/'test_cost_successor.mjs').write_text(d.source)
    print(json.dumps(dict(status='COMPLETE_COST_MODEL_PREPARED',typed_tables=len(input['columns']),
        unchanged_native_cost_functions=len(COST_FUNCTIONS)-(1 if input.get('cost_rebalance_enabled')else 0),
        derived_native_cost_functions=1 if input.get('cost_rebalance_enabled')else 0,changed_valuation_functions=len(input['valuation_definitions']),
        input_bytes=out.stat().st_size,input_sha256=sha256(out.read_bytes()).hexdigest(),actual_ERP_cases=0)))


if __name__=='__main__':prepare(sys.argv[1])
