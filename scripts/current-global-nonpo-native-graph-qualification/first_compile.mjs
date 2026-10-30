import {setup,inspect,snapshot}from'./model.mjs';
import assert from'node:assert/strict';
const db=await setup();
try{
 await db.exec("set local_model.inspecting='on'");
 const before=await snapshot(db),result=await inspect(db),after=await snapshot(db);
 assert.deepEqual(after,before,'LOCAL_INSPECTOR_CHANGED_MODEL_BEFORE_ROLLBACK');
 assert.equal(result.status,'OBSERVED_QUIESCENT_SOURCE_ONLY',JSON.stringify(result));
 console.log(JSON.stringify({classification:'LOCAL_STRUCTURAL_SQL_ONLY',status:'PASS',result,actual_Native:0},null,2));
}finally{await db.close()}
