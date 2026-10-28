import assert from 'node:assert/strict'
import {test} from 'node:test'
import {mkdtemp,readFile,writeFile,rm} from 'node:fs/promises'
import {tmpdir} from 'node:os'
import {join} from 'node:path'
import {fileURLToPath} from 'node:url'
import {fork} from 'node:child_process'
import {writeFirstFailure} from './cp7_first_failure_evidence.mjs'

const payload=label=>JSON.stringify({writer:label,evidence:label.repeat(128*1024)})+'\n'
if(process.argv[2]==='writer'){
 process.on('message',async message=>{
  if(message!=='start')return
  try{const created=await writeFirstFailure(process.argv[3],payload(process.argv[4]));process.send({created,pid:process.pid});process.disconnect()}
  catch(error){process.send({error:String(error)});process.exitCode=1;process.disconnect()}
 })
 process.send('ready')
}else{
 const directory=async t=>{const dir=await mkdtemp(join(tmpdir(),'cp7-first-evidence-'));t.after(()=>rm(dir,{recursive:true,force:true}));return dir}
 test('a new first failure is written completely',async t=>{
  const path=join(await directory(t),'first.json'),bytes=payload('A')
  assert.equal(await writeFirstFailure(path,bytes),true)
  assert.equal(await readFile(path,'utf8'),bytes)
 })
 test('an existing first failure is preserved byte for byte',async t=>{
  const path=join(await directory(t),'first.json'),original=Buffer.from([0,1,255,2,10])
  await writeFile(path,original)
  assert.equal(await writeFirstFailure(path,payload('B')),false)
  assert.deepEqual(await readFile(path),original)
 })
 test('two independent processes released together create exactly one first record',{timeout:15000},async t=>{
  const path=join(await directory(t),'first.json')
  const start=label=>{
   const child=fork(fileURLToPath(import.meta.url),['writer',path,label],{execArgv:[],stdio:['ignore','ignore','pipe','ipc']})
   t.after(()=>{if(child.exitCode===null)child.kill()})
   let readyResolve,doneResolve,doneReject,result,stderr=''
   const ready=new Promise(resolve=>{readyResolve=resolve})
   const done=new Promise((resolve,reject)=>{doneResolve=resolve;doneReject=reject})
   child.stderr.on('data',chunk=>{stderr+=chunk})
   child.on('message',message=>{if(message==='ready')readyResolve();else result=message})
   child.on('error',doneReject)
   child.on('exit',code=>{if(code===0&&result&&!result.error)doneResolve({...result,label});else doneReject(Error(stderr||result?.error||'Writer exited without result'))})
   return{child,ready,done}
  }
  const writers=[start('A'),start('B')]
  await Promise.all(writers.map(w=>w.ready));for(const w of writers)w.child.send('start')
  const results=await Promise.all(writers.map(w=>w.done))
  assert.equal(new Set(results.map(r=>r.pid)).size,2)
  assert.deepEqual(results.map(r=>r.created).sort(),[false,true])
  const winner=results.find(r=>r.created)
  assert.equal(await readFile(path,'utf8'),payload(winner.label))
 })
 test('a real write error other than EEXIST propagates',async t=>{
  const path=join(await directory(t),'missing-parent','first.json')
  await assert.rejects(writeFirstFailure(path,payload('A')),{code:'ENOENT'})
 })
}
