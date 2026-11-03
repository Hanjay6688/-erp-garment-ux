import fs from 'node:fs'
import path from 'node:path'
import {spawn} from 'node:child_process'
const require=(ok,message)=>{if(!ok)throw Error(message)}
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms))
export const children=[]
const exited=child=>child.exitCode!==null||child.signalCode!==null
const groupExists=child=>{try{process.kill(-child.pid,0);return true}catch(error){if(error.code==='ESRCH')return false;throw error}}

export async function server(directory,port,name,out){
  const log=fs.openSync(path.join(out,name+'-server.log'),'wx')
  const env={PATH:process.env.PATH,HOME:process.env.HOME,LANG:'C.UTF-8',
    VITE_ERP_RUNTIME_MODE:'DEMO_SIMULATION',NODE_ENV:'development'}
  const child=spawn(process.execPath,[path.join(directory,'node_modules/vite/bin/vite.js'),
    '--config','scripts/ui-reference/connected-ui/vite.config.mjs','--host','127.0.0.1','--port',String(port),'--strictPort','--mode','writer-b-connected-ui-fixture'],
    {cwd:directory,env,stdio:['ignore',log,log],detached:true})
  fs.closeSync(log);children.push(child);
  const url=`http://127.0.0.1:${port}`
  for(let attempt=0;attempt<300;attempt++){
    if(exited(child))throw Error(name+' preview server exited before readiness')
    try{const response=await fetch(url+'/scripts/ui-reference/connected-ui/fixture.html');if(response.ok)return {url,child}}catch{}
    await sleep(200)
  }
  throw Error(name+' preview server did not become ready')
}

export async function stop(child){
  if(exited(child)&&!groupExists(child))return
  try{process.kill(-child.pid,'SIGTERM')}catch(error){if(error.code!=='ESRCH')throw error}
  for(let i=0;i<50&&(!exited(child)||groupExists(child));i++)await sleep(100)
  if(!exited(child)||groupExists(child)){try{process.kill(-child.pid,'SIGKILL')}catch(error){if(error.code!=='ESRCH')throw error}}
  for(let i=0;i<20&&(!exited(child)||groupExists(child));i++)await sleep(100)
  require(exited(child)&&!groupExists(child),'UI_CAPTURE_PREVIEW_CHILD_MUST_BE_REAPED')
}


export async function stopAll(){for(const child of children)await stop(child)}
