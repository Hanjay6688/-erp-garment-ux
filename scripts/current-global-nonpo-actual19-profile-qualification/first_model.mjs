/** Reproduce the old source authority's refusal against two actual source bodies. */
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {setup,snapshot,inspect} from './model_profile.mjs';
const db=await setup({sqlSources:{'authority.sql':fileURLToPath(new URL('./retained/PUBLIC14B_authority.sql',import.meta.url))}});
const result={classification:'LOCAL_SQL_SOURCE_PROFILE_REPRODUCTION_NOT_NATIVE_EXECUTION',actual_Native_credit:0};
try{
 await db.exec("set local_model.inspecting='on'");
 const before=await snapshot(db),authority=(await db.query('select cp7_global_nonpo_native_graph.authority_v1()value')).rows[0].value;
 const observed=await inspect(db),after=await snapshot(db);
 assert.deepEqual(after,before);
 assert.equal(authority.known_functions_exact,false);
 const mismatches=authority.functions.filter(x=>!x.exact_known_source).map(x=>x.signature).sort();
 assert.deepEqual(mismatches,['erp.compute_non_po_product_hpp_book_v2620f(uuid)','erp.require_internal()']);
 assert.notEqual(observed.status,'OBSERVED_QUIESCENT_SOURCE_ONLY');
 Object.assign(result,{status:'EXPECTED_OLD_PROFILE_REFUSAL_REPRODUCED',mismatches,
  observed_status:observed.status,refusals:observed.refusals,
  model_rows_sequence_and_new_catalog_directly_unchanged:true,standins:db.actual19LocalStandins,
  actual_loaded_SQL_pins:db.localSourcePins});
}finally{await db.close()}
process.stdout.write(JSON.stringify(result,null,2)+'\n');
