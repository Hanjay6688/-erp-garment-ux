/** SQL declaration/body compilation only; structural/authority/source helpers are doubles. */
import {readFile} from 'node:fs/promises'
import {execFileSync} from 'node:child_process'
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE||'@electric-sql/pglite')
const here=new URL('./',import.meta.url),db=new PGlite()
try{
 await db.exec(execFileSync('python3',[new URL('e_compile_fixture.py',here).pathname,process.argv[2]],{encoding:'utf8',maxBuffer:15e6,env:{...process.env,PYTHONPATH:new URL('../',here).pathname}}))
 for(const file of ['../cp7_customer_credit/kernel/kernel.sql','../cp7_customer_credit/ordinal-wrapper/wrapper.sql',
  'note_carry/01_facts.sql','note_carry/02_plan.sql','note_carry/03_readers.sql','note_carry/04_basis.sql','note_carry/05_effect.sql','note_carry/06_owning.sql','note_carry/07_profile_closure.sql']){
  try{await db.exec(await readFile(new URL(file,here),'utf8'))}catch(error){throw Error(file+': '+error.message,{cause:error})}
 }
 console.log(JSON.stringify({status:'PASS',scope:'E1 SQL declaration/body compilation',Native_execution:false,standins:'structural Native/private columns and source/authority signatures only; no writer or closure proof'},null,2))
}catch(error){console.error(JSON.stringify({status:'FAIL',message:error.message,sqlstate:error.cause?.code,where:error.cause?.where,Native_execution:false},null,2));process.exitCode=1}finally{await db.close()}
