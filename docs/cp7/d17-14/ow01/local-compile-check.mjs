// Compile changed PL/pgSQL bodies in an isolated WASM database. Referenced
// relations are empty row-type stubs: this is syntax/PLpgSQL validation only,
// never Native query planning, business execution, ownership or acceptance.
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {execFileSync} from 'node:child_process'
const {PGlite}=await import(process.env.PGLITE_MODULE)
const files=['scripts/cp7-src/reminders/accessory-source.sql','scripts/cp7-src/reminders/staged-reminders.sql','scripts/cp7-src/alerts/alerts.sql']
const results=[]
for(const file of files){
 const text=readFileSync(file,'utf8'),db=new PGlite()
 const refs=[...new Set([...text.matchAll(/\b((?:erp|auth|extensions|cp7_[a-z_0-9]+)\.[a-z_0-9]+)\b/g)].map(m=>m[1]))]
 for(const schema of new Set(refs.map(r=>r.split('.')[0])))await db.exec('create schema if not exists '+schema)
 for(const ref of refs)await db.exec('create table if not exists '+ref+'()')
 const functions=[...text.matchAll(/create (?:or replace )?function ([a-z_0-9.]+)\([\s\S]*?\$\$;/gi)].filter(m=>/language\s+plpgsql/i.test(m[0]))
 assert.ok(functions.length>0,file)
 for(const fn of functions){
  try{await db.exec(fn[0]);results.push({file,function:fn[1],status:'PASS'})}
  catch(error){results.push({file,function:fn[1],status:'TOOL_STUB_OR_COMPILE_FAILURE',error:String(error)})}
 }
 await db.close()
}
const failed=results.filter(r=>r.status!=='PASS')
console.log(JSON.stringify({classification:'LOCAL_PGLITE18_COMPILE_WITH_EMPTY_ROW_TYPES_NOT_NATIVE',candidate:'OW01_UNCOMMITTED_SOURCE_CHECK',files:files.length,compiled:results.length-failed.length,failed:failed.length,results,Native:false}))
assert.equal(failed.length,0,'Inspect the retained first output; missing stub types are not automatically product defects')
