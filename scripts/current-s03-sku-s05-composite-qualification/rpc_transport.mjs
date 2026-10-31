// Qualification host only. Each real public RPC gets one loopback connection.
// No retry: a lost write reply remains a failed, reviewable first attempt.
import http from 'node:http'
import {createHash} from 'node:crypto'

export async function directRpc(port,anon,token,name,args={}){
 if(!Number.isInteger(port)||port<1||port>65535||!/^\w+$/.test(name))throw new Error('QUALIFIER_RPC_LOCAL_ENDPOINT_REQUIRED')
 const raw=JSON.stringify(args),bodyHash=createHash('sha256').update(raw).digest('hex')
 return await new Promise((resolve,reject)=>{
  let settled=false
  const fail=(error,phase)=>{
   if(settled)return;settled=true
   const detail={rpc:name,phase,code:error.code??null,errno:error.errno??null,syscall:error.syscall??null,
    address:error.address??null,port,request_id:args.p_client_request_id??args.p_request??null,
    body_sha256:bodyHash,automatic_retries:0}
   reject(new Error('QUALIFIER_RPC_TRANSPORT_FAILURE:'+JSON.stringify(detail),{cause:error}))
  }
  const req=http.request({hostname:'127.0.0.1',port,path:'/rpc/'+name,method:'POST',agent:false,
   headers:{apikey:anon,Authorization:`Bearer ${token||anon}`,'Content-Type':'application/json',
    'Content-Length':Buffer.byteLength(raw),Connection:'close'}},res=>{
   const chunks=[]
   res.on('data',chunk=>chunks.push(chunk))
   res.on('error',error=>fail(error,'RESPONSE'))
   res.on('aborted',()=>fail(Object.assign(new Error('RESPONSE_ABORTED'),{code:'RESPONSE_ABORTED'}),'RESPONSE'))
   res.on('end',()=>{
    if(settled)return;settled=true
    const text=Buffer.concat(chunks).toString('utf8');let body
    try{body=text?JSON.parse(text):null}catch{body=text.slice(0,2000)}
    resolve({status:res.statusCode,body})
   })
  })
  req.on('error',error=>fail(error,'REQUEST'))
  req.setTimeout(300000,()=>req.destroy(Object.assign(new Error('RPC_TIMEOUT'),{code:'RPC_TIMEOUT'})))
  req.end(raw)
 })
}
