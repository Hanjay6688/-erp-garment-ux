/** DDL/body compilation ONLY; Native schema/authority/writer helpers are stand-ins. */
import {readFile} from 'node:fs/promises'
import {execFileSync} from 'node:child_process'
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE||'@electric-sql/pglite')
const here=new URL('./',import.meta.url),db=new PGlite()
try{
 const fixture=execFileSync('python3',[new URL('local_compile_fixture.py',here).pathname,process.argv[2]],{encoding:'utf8',maxBuffer:15e6})
 await db.exec(fixture)
 for(const file of ['../cp7_customer_credit/kernel/kernel.sql','../cp7_customer_credit/ordinal-wrapper/wrapper.sql',
  'review.sql','facts.sql','owning.sql','proof.sql','posting.sql','materialize.sql','closure.sql']){
  try{await db.exec(await readFile(new URL(file,here),'utf8'))}catch(e){throw Error(file+': '+e.message,{cause:e})}
 }
 console.log(JSON.stringify({status:'PASS',scope:'SQL declaration/body compilation only',Native_execution:false,standins:'Native/private relation column types; SQL-helper signatures; no real source, accounting, Auth, RLS or writer effects exercised'},null,2))
}finally{await db.close()}
