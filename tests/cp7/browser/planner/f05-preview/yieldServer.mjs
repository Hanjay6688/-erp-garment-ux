// Disposable demo backend only. Never registered in the operational Worker.
// SQL/history stay server-side; this endpoint provides no real authentication.
import { readFileSync } from 'node:fs'
import { openYieldRuntime } from '../../../families/models/yield/runtime.mjs'
import { demoHistory, policy } from '../../../families/models/yield/history.mjs'

export const yieldEndpoint = '/__cp7_demo_yield'
export function yieldPreviewPlugin() {
  const fixture=JSON.parse(readFileSync('docs/cp7/contracts/analysis.example.json','utf8'))
  let database
  const install = server => {
    server.httpServer?.once('close',()=> { if(database) void database.then(db=>db.close()).catch(()=>{}) })
    server.middlewares.use(yieldEndpoint,async(req,res)=> {
      const send=(status,value)=>{res.statusCode=status;res.setHeader('Content-Type','application/json');res.setHeader('Cache-Control','no-store');res.end(JSON.stringify(value))}
      if(!['127.0.0.1','::1','::ffff:127.0.0.1'].includes(req.socket.remoteAddress)) return send(403,{error:'LOCAL_DEMO_ONLY'})
      if(req.method!=='POST' || req.headers['content-type']?.split(';')[0]!=='application/json') return send(405,{error:'JSON_POST_ONLY'})
      if(req.headers.origin && req.headers.origin!==`http://${req.headers.host}`) return send(403,{error:'SAME_ORIGIN_ONLY'})
      let bytes=0,chunks=[]
      try {
        for await(const chunk of req) { bytes+=chunk.length;if(bytes>32768)return send(413,{error:'BODY_LIMIT'});chunks.push(chunk) }
        const body=JSON.parse(Buffer.concat(chunks).toString('utf8'))
        if(!body || Object.keys(body).sort().join(',')!=='context,example,input,inputKey') return send(400,{error:'DEMO_REQUEST_FIELDS'})
        const ctx=body.context
        if(!ctx || ctx.runId!==fixture.run_id || ctx.actorScope!==fixture.scope.actor_scope_id || ctx.accessEpoch!==fixture.versions.access_epoch) return send(403,{error:'FIXTURE_CONTEXT_ONLY'})
        const examples=['NORMAL','LOW','HIGH','SHORT_ROLL','NARROW_BATCH','INSUFFICIENT','INCOMPLETE','UNSEEN_COMBINATION','ERROR']
        if(!examples.includes(body.example))return send(400,{error:'UNKNOWN_DEMO_CASE'})
        if(body.example==='ERROR')return send(503,{error:'EXPLICIT_FAILURE_CASE'})
        // Server constructs history, cutoff and policy. Never accept client SQL,
        // source rows, credentials, arbitrary URLs, cohort bounds or thresholds.
        let history=demoHistory(ctx.actorScope)
        if(body.example==='INSUFFICIENT') history=history.slice(0,19)
        if(body.example==='UNSEEN_COMBINATION') history=[]
        database??=openYieldRuntime({demoPreview:true})
        const db=await database
        const result=await db.review({contract:'f04.yield-history-request.v1',input:body.input,inputKey:body.inputKey,context:ctx,history,policy})
        return send(200,result)
      } catch { return send(422,{error:'ANALYZER_UNAVAILABLE_NO_FALLBACK'}) }
    })
  }
  return {name:'cp7-disposable-yield-demo',configureServer:install,configurePreviewServer:install}
}
