/** Frozen923 source-only Native-identity gap replay; no Native command is run. */
import assert from'node:assert/strict';
import path from'node:path';
import {setup,inspect,snapshot,uuid,here}from'./model.mjs';
import {cost}from'./identity_fixtures.mjs';
const db=await setup({sqlSources:{'scope.sql':path.join(here,'retained/923_scope.sql')}});
await cost(db,{product:null});
await db.exec(`insert into erp.journal_entries(id,status,source_type,source_id,description)values('${uuid(612)}','POSTED','MATERIAL_ADJUSTMENT','${uuid(902)}','Native-source account-only original');
 insert into erp.journal_lines(id,journal_entry_id,account_id,debit,credit,product_id,po_id)values
 ('${uuid(714)}','${uuid(612)}','${uuid(501)}',1,0,null,null),('${uuid(715)}','${uuid(612)}','${uuid(502)}',0,1,null,null);
 set local_model.inspecting='on'`);
const before=await snapshot(db),first=await inspect(db),after=await snapshot(db);assert.deepEqual(before,after);
assert(first.outside_source.facts.material_adjustments.some(x=>x.id===uuid(902)));
assert(!first.outside_source.facts.journals.some(x=>x.id===uuid(612)));
await db.exec(`set local_model.inspecting='off';update erp.journal_entries set description='Changed Native original journal'where id='${uuid(612)}';set local_model.inspecting='on'`);
const beforeChanged=await snapshot(db),changed=await inspect(db),afterChanged=await snapshot(db);assert.deepEqual(beforeChanged,afterChanged);
assert.equal(first.basis_sha256,changed.basis_sha256);
console.log(JSON.stringify({classification:'LOCAL_TYPED_INSPECTOR_SOURCE_CLOSURE_GAP_NOT_NATIVE_TRANSACTION_BUG',
 status:'CONFIRMED_923_OMITTED_NATIVE_ADJUSTMENT_JOURNAL_IDENTITY',frozen_inspector:'923a9620d41f618fe72e9cd9181fcf7ddee3cf91',
 source_pins:db.localSourcePins,adjustment_captured:true,original_account_only_journal_captured:false,
 retained_journal_description_mutation_changes_basis:false,basis_sha256:first.basis_sha256,
 direct_before:before,direct_after:after,direct_before_changed:beforeChanged,direct_after_changed:afterChanged,
 qualified_for_runtime:first.qualified_for_runtime,actual_Native:0,actual_DB_server:0,runtime_entry:null,writer_or_phantom_lock_closed:false},null,2));
await db.close();
