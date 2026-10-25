// Actual Python installer and catalog reader, actual local PostgreSQL SQL.
// The transport supplies no identity/Auth, concurrency or Native claim.
import {spawn} from 'node:child_process'
import {createInterface} from 'node:readline'

export async function beginLocalStageAudit(db,stage,script='scripts/cp7_local_stage_audit.py'){
 const child=spawn('python',['-B',script,stage],{stdio:['pipe','pipe','pipe']})
 let readyResolve,readyReject,doneResolve,doneReject,stderr='',finished=false
 const ready=new Promise((resolve,reject)=>{readyResolve=resolve;readyReject=reject})
 const done=new Promise((resolve,reject)=>{doneResolve=resolve;doneReject=reject});done.catch(()=>{})
 const fail=e=>{readyReject(e);doneReject(e);if(!finished)child.kill('SIGTERM')}
 const timer=setTimeout(()=>fail(Error('Local stage audit exceeded45seconds')),45000)
 child.stderr.on('data',chunk=>{stderr=(stderr+chunk.toString()).slice(-7000)})
 child.on('error',fail)
 child.on('close',code=>{clearTimeout(timer);if(code!==0)fail(Error('Local stage audit failed: '+stderr));else if(!finished)fail(Error('Local stage audit ended without a result'))})
 void(async()=>{
  for await(const line of createInterface({input:child.stdout,crlfDelay:Infinity})){
   const message=JSON.parse(line)
   if(message.kind==='ready'){readyResolve(message.result);continue}
   if(message.kind==='done'){finished=true;doneResolve(message.result);continue}
   if(message.kind!=='query')throw Error('Unknown local installer message')
   try{
    const params=message.params??[];let index=0
    const sql=params.length?message.sql.replace(/%s/g,()=>'$'+(++index)):message.sql
    if(index!==params.length)throw Error('Local SQL placeholder mismatch')
    const result=params.length||/^\s*(select|with|show)\b/i.test(sql)?await db.query(sql,params,{rowMode:'array'}):null
    if(result===null)await db.exec(sql)
    child.stdin.write(JSON.stringify({ok:true,rows:result?.rows??[]})+'\n')
   }catch(e){child.stdin.write(JSON.stringify({ok:false,rows:[],error:String(e.message).slice(0,1500)})+'\n')}
  }
 })().catch(fail)
 try{await ready}catch(e){clearTimeout(timer);throw e}
 return{afterUse:async()=>{child.stdin.write(JSON.stringify({kind:'after_use'})+'\n');return done}}
}
