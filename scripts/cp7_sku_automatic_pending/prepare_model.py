"""Derive a focused Native-hook model from the retained counter setup.

The upstream completion, authority and physical PO GL synchronization are
explicit model providers. Native BE post/inverse, physical movement writers,
PO propagation/book assertions and the prepared economic writers are exact.
"""
from hashlib import sha256
from pathlib import Path
import json,re,sys
from cp7_sku_cost_components.valuation_delta import Derivation
from .derivation import derive,HERE

ROOT=HERE.parents[1]
COUNTER_SHA='c346ca249df0031a5c4195446715a459b0e0b345b23243b8b9ecf5549c541efd'
INPUT_SHA='90ccf2bdfbf0e123d525dacdb2d6237706b4348bec41486a0ce203716f4c217c'
NATIVE_SHA='8411e6378b2c606d46eb50864ca5ef952d283cc093f8bb0bceeb8982201a6d11'


def credit_setup(destination):
    original=(ROOT/'scripts/cp7_sku_moving_average/test_credit_projection_pg17.mjs').read_bytes()
    if sha256(original).hexdigest()!='1d210889a0c2777fb245ce62c2bb62a300b7fccdf73fc047a05bd190c81a430f':
        raise ValueError('AUTOMATIC_EXACT_CREDIT_SETUP_SOURCE_REQUIRED')
    d=Derivation(original.decode())
    d.once('assert.equal(p.economic_return_components.length,3);',"""assert.deepEqual(p.economic_return_components.map(c=>[c.component_kind,c.root_lot_id,Number(c.component_units),Number(c.hpp_per_pcs)]),[
   ['BASE',x.root10,.25,10],['BASE',x.root30,.25,30],['BASE',x.root50,.5,50],['COST',x.converted,.5,0]]);""",'retain the prior exact cost-root credit setup')
    d.once(' create function erp.post_journal(p_type text,p_id uuid,p_date date,p_reason text,p_lines jsonb)returns uuid language plpgsql as $$',
        """ create function public.model_journal_account(line jsonb)returns uuid language plpgsql stable as $$
 declare resolved uuid;begin
  if line?'account_id'then
   if line?'mapping_key'then raise exception 'MODEL_ACCOUNT_ID_AND_MAPPING_BOTH_SET';end if;
   select id into strict resolved from erp.chart_accounts where id=(line->>'account_id')::uuid and is_active and is_postable;
   return resolved;
  end if;
  return cp7_credit.account_by_mapping_v1(line->>'mapping_key');end$$;
 create function erp.post_journal(p_type text,p_id uuid,p_date date,p_reason text,p_lines jsonb)returns uuid language plpgsql as $$""",'retain the explicit Native account-id journal storage provider')
    d.once("values(gen_random_uuid(),j,cp7_credit.account_by_mapping_v1(l->>'mapping_key'),",
        'values(gen_random_uuid(),j,public.model_journal_account(l),','retain both Native account representations')
    if d.inverse()!=original.decode():raise ValueError('AUTOMATIC_CREDIT_SETUP_ORIGINAL_RECOVERY_REQUIRED')
    path=destination/'credit_setup.mjs';path.write_text(d.source);return path


def prepare(counter,input_path,native_path,po_path,destination):
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
    raw=Path(counter).read_bytes();old=Path(input_path).read_bytes();native_raw=Path(native_path).read_bytes()
    if(sha256(raw).hexdigest()!=COUNTER_SHA or sha256(old).hexdigest()!=INPUT_SHA
        or sha256(native_raw).hexdigest()!=NATIVE_SHA):raise ValueError('AUTOMATIC_EXACT_RETAINED_INPUTS_REQUIRED')
    value=json.loads(old);native=json.loads(native_raw);po=json.loads(Path(po_path).read_bytes())
    if sha256(Path(po_path).read_bytes()).hexdigest()!='3b7d41475d530649ec5708149fb020a52f5f64ce80d0855d7bf9118a1df88314':
        raise ValueError('AUTOMATIC_EXACT_PO_SOURCE_REQUIRED')
    value['columns']['erp.bs_cases']=native['columns']['erp.bs_cases']
    for name in('erp.rework_orders','erp.be_rework_targets_v1'):
        if value['columns'][name]!=native['columns'][name]:raise ValueError('AUTOMATIC_NATIVE_TYPES_DIFFER:'+name)
    functions=dict(value['valuation_definitions'])|dict(value['legacy_definitions'])
    for body in re.findall(r'(?ms)^create (?:or replace )?function [\s\S]*?\$\$;\n',value['cost_ddl']):
        name=re.search(r'(?i)function\s+([^\s(]+)',body).group(1);functions[name]=body
    for name in('erp.be_complete_rework_target_v1(uuid)','erp.be_reverse_rework_target_v1(uuid,text)'):
        if value['legacy_helpers'][name]!=native['functions'][name][0]:raise ValueError('AUTOMATIC_NATIVE_HOOK_DIFFERS:'+name)
        functions[name]=value['legacy_helpers'][name]
    value['automatic_product']=derive(functions)
    value['automatic_po_helpers']={name:po[name][0]for name in(
        'erp.propagate_conversion_hpp_for_po(uuid)','erp.compute_po_hpp_gl_book_v2620e(uuid)',
        'erp.refresh_po_hpp_gl_baseline(uuid)','erp.assert_po_hpp_target_book_v2620e(uuid)',
        'erp.be_po_extra_v1(uuid)')}
    book=(Path(native_path).parent/'NONPO_BOOK_ORIGINAL.sql').read_bytes()
    if sha256(book).hexdigest()!='1647164dc565d08a010b182c3c08b1d729b00d588fc7a6e43774f8672c9c6ea5':
        raise ValueError('AUTOMATIC_EXACT_NATIVE_NONPO_BOOK_REQUIRED')
    value['automatic_po_helpers']['erp.compute_non_po_product_hpp_book_v2620f(uuid)']=book.decode()
    value['automatic_model_providers']=(HERE/'model_providers.sql').read_text()
    target=destination/'INPUT.json';target.write_text(json.dumps(value,sort_keys=True)+'\n')
    credit=credit_setup(destination)
    source=raw.decode();marker=' const originalPreview=input.original_legacy_preview.replace('
    if source.count(marker)!=1:raise ValueError('AUTOMATIC_EXACT_COUNTER_BOUNDARY_REQUIRED')
    prefix=source.split(marker)[0]
    d=Derivation(prefix)
    d.once('from "/workspace/scratch/268d44d856bf/sku/legacy-signed-full-first/test_credit_cost_successor.mjs"',
        'from '+json.dumps(str(credit.resolve())),'rehome only the exact retained explicit credit setup')
    d.once('const here = "/workspace/scratch/268d44d856bf/sku-cost-prepared/scripts/cp7_sku_moving_average";',
        'const here = '+json.dumps(str((ROOT/'scripts/cp7_sku_moving_average').resolve()))+';',
        'same immutable parent DDL at its restored checkout')
    d.once("('OPENING_EQUITY','AR_CUSTOMER','SALES_REVENUE')",
        "('OPENING_EQUITY','AR_CUSTOMER','SALES_REVENUE','WIP')",
        'explicit journal storage provider supports the new PO-only WIP counterpart')
    d.once("  if entry->>'mapping_key'='FG_INVENTORY'then",
        "  if entry->>'po_id'is not null then continue;\n  elsif entry->>'mapping_key'='FG_INVENTORY'then",
        'modeled non-PO balance bookkeeping excludes PO-tagged lines exactly as the real Native book does')
    d.once(' await actualBookBaseline();\n const costBaseline=await costSnapshot();',
        """ for(const definition of Object.values(input.automatic_po_helpers))await db.exec(definition);
 await db.exec(input.automatic_model_providers);
 await actualBookBaseline();
 const costBaseline=await costSnapshot();""",'collect every typed PO helper/provider before executing focused cases')
    if d.inverse()!=prefix:raise ValueError('AUTOMATIC_COUNTER_SETUP_NOT_REVERSIBLE')
    tail="""
 const report={status:'AUTOMATIC_PENDING_NATIVE_HOOK_MODEL_PASS_NOT_ERP',engine,findings:automaticFindings,
  new_controls:automaticFindings.length,old_controls_rerun:0,actual_ERP_cases:0,actual_Auth_HTTP_cases:0,
  modeled_upstream_completion:true,modeled_PO_physical_GL_sync:true,
  actual_full_lifecycle_qualification_pending:true,production_go:false,independent_acceptance:false};
 await writeFile(process.env.CP7_CONSUMER_MODEL_REPORT,JSON.stringify(report,null,2)+'\\n');
 console.log(JSON.stringify({status:report.status,new_controls:report.new_controls,actual_ERP_cases:0}));
}catch(error){
 await writeFile(process.env.CP7_CONSUMER_MODEL_REPORT,JSON.stringify({status:'FAILED',engine,results,
  error:{message:error.message,SQLSTATE:error.code??null,context:error.where??null,detail:error.detail??null},actual_ERP_cases:0},null,2)+'\\n');
 console.error(JSON.stringify({status:'FAILED',message:error.message,SQLSTATE:error.code??null,context:error.where??null}));process.exitCode=1;
}finally{await db.close();}
"""
    harness=destination/'model.mjs';harness.write_text(d.source+'\n'+(HERE/'model_cases.mjs.inc').read_text()+tail)
    receipt=dict(status='EXACT_NATIVE_HOOK_INPUTS_PREPARED_MODEL_NOT_ERP',
        input_bytes=target.stat().st_size,input_sha256=sha256(target.read_bytes()).hexdigest(),
        harness_sha256=sha256(harness.read_bytes()).hexdigest(),setup_derivations=[x[2]for x in d.routes],
        upstream_completion_and_authority_and_PO_GL_are_explicit_models=True,actual_ERP_cases=0)
    (destination/'PREPARATION.json').write_text(json.dumps(receipt,indent=2)+'\n');return receipt


if __name__=='__main__':print(json.dumps(prepare(*sys.argv[1:])))
