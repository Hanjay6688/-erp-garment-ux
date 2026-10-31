import assert from 'node:assert/strict'
import http from 'node:http'
import {once} from 'node:events'
import {directRpc} from './rpc_transport.mjs'

const rows=[],connections=new WeakMap();let serial=0
const server=http.createServer((req,res)=>{
 let raw='';req.on('data',chunk=>raw+=chunk);req.on('end',()=>{
  rows.push({connection:connections.get(req.socket),path:req.url,raw,headers:req.headers})
  if(req.url==='/rpc/drop_after_effect'){req.socket.destroy();return}
  if(req.url==='/rpc/partial'){res.writeHead(200,{'Content-Length':'100'});res.write('{');res.socket.destroy();return}
  if(req.url==='/rpc/refuse'){res.writeHead(403,{'Content-Type':'application/json'});res.end('{"message":"OWNER_REQUIRED"}');return}
  if(req.url==='/rpc/plain'){res.end('x'.repeat(2100));return}
  if(req.url==='/rpc/empty'){res.writeHead(204);res.end();return}
  res.setHeader('Content-Type','application/json');res.end(JSON.stringify({actual:JSON.parse(raw)}))
 })
})
server.on('connection',socket=>connections.set(socket,++serial));server.listen(0,'127.0.0.1');await once(server,'listening')
try{
 const port=server.address().port,anon='control-anon',token='control-secret-never-printed',payload={p_client_request_id:'control-one',amount:300000}
 assert.deepEqual(await directRpc(port,anon,token,'first',payload),{status:200,body:{actual:payload}})
 // A synchronous fixture can leave the event loop idle longer than a server socket.
 Atomics.wait(new Int32Array(new SharedArrayBuffer(4)),0,0,150)
 assert.deepEqual(await directRpc(port,anon,token,'second',payload),{status:200,body:{actual:payload}})
 assert.deepEqual(await directRpc(port,anon,null,'refuse',{}),{status:403,body:{message:'OWNER_REQUIRED'}})
 assert.deepEqual(await directRpc(port,anon,token,'plain',{}),{status:200,body:'x'.repeat(2000)})
 assert.deepEqual(await directRpc(port,anon,token,'empty',{}),{status:204,body:null})
 for(const name of ['drop_after_effect','partial']){
  const boundary=rows.length;let error
  try{await directRpc(port,anon,token,name,payload)}catch(caught){error=caught}
  assert(error);assert.match(error.message,/QUALIFIER_RPC_TRANSPORT_FAILURE/);assert(!error.message.includes(token))
  assert.match(error.message,/"automatic_retries":0/);assert.match(error.message,/"body_sha256":"[0-9a-f]{64}"/)
  await new Promise(setImmediate);assert.equal(rows.length,boundary+1,'LOST_WRITE_MUST_NOT_RETRY')
 }
 assert.deepEqual((await Promise.all(['tab_one','tab_two'].map(name=>directRpc(port,anon,token,name,payload)))).map(r=>r.status),[200,200])
 assert.equal(rows.length,9);assert.equal(new Set(rows.map(r=>r.connection)).size,9)
 for(const row of rows){assert.equal(row.headers.connection,'close');assert.equal(row.headers.apikey,anon);assert.equal(row.headers['content-type'],'application/json')}
 assert.equal(rows[0].raw,JSON.stringify(payload));assert.equal(rows[1].raw,rows[0].raw)
 assert.equal(rows[0].headers.authorization,'Bearer '+token);assert.equal(rows[2].headers.authorization,'Bearer '+anon)
 await assert.rejects(directRpc(port,anon,token,'../escape',payload),/LOCAL_ENDPOINT_REQUIRED/);assert.equal(rows.length,9)
 console.log(JSON.stringify({status:'REAL_LOOPBACK_RPC_TRANSPORT_CONTRACT_PASS',observed_requests:9,distinct_connections:9,
  response_loss_without_retry:true,refusal_preserved:true,exact_payload_and_Auth_headers:true,error_cause_retained_without_secret:true,
  actual_Native_cases:0,actual_Auth_cases:0,actual_f42_root_cause_confirmed:false}))
}finally{server.closeAllConnections();server.close();await once(server,'close')}
