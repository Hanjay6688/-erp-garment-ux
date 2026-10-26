import assert from 'node:assert/strict'
import {build} from 'vite'
import {resolve,dirname} from 'node:path'
import {fileURLToPath} from 'node:url'
const here=dirname(fileURLToPath(import.meta.url)),vendor=resolve(here,'vendor')
const source=path=>resolve(vendor,path)
const callers=new Set(['scripts/cp7_frozen_quantity_ui/client/NativeFrozenQuantityPanel.tsx','scripts/cp7_frozen_finance_ui/client/NativeFrozenFinancePanel.tsx'].map(source))

export async function buildCurrentFrozenFinance(ui){
  assert.equal(ui.origin,'http://127.0.0.1:4176')
  assert.equal(process.env.AUDITOR_UI_MODE??'DISPOSABLE','DISPOSABLE')
  const api=new URL(ui.api)
  assert.equal(api.hostname,'127.0.0.1')
  assert.ok(Number(api.port)>=32768&&Number(api.port)<=65535)
  const environment={VITE_ERP_RUNTIME_MODE:'DISPOSABLE_TEST',VITE_SUPABASE_URL:ui.api,VITE_DISPOSABLE_API_PORT:api.port,VITE_SUPABASE_ANON_KEY:process.env.SUPABASE_ANON_KEY}
  assert.ok(environment.VITE_SUPABASE_ANON_KEY)
  const entry=`import React from 'react';import{createRoot}from'react-dom/client';
import{AuthProvider}from'${source('src/auth/AuthProvider.tsx')}';import{AuthGate}from'${source('src/auth/AuthGate.tsx')}';
import{parseRuntimeConfig}from'${source('src/config/runtime.ts')}';import Panel from'${source('scripts/cp7_frozen_finance_ui/client/NativeFrozenFinancePanel.tsx')}';
import '${source('src/styles.css')}';import '${source('src/auth/auth.css')}';
const runtime=parseRuntimeConfig(${JSON.stringify(environment)},{mode:'cp6-disposable-test',pageOrigin:location.origin});
const q=JSON.parse(new URLSearchParams(location.search).get('query')??'null');
const root=createRoot(document.getElementById('root')),idle=()=>{};
root.render(<AuthProvider runtime={runtime}><AuthGate><main style={{maxWidth:1100,margin:'auto',padding:16}}><Panel query={q} onSourceReadStart={idle} onSourceReadEnd={idle} onClose={()=>root.unmount()}/></main></AuthGate></AuthProvider>);`
  const html='<!doctype html><html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Kebutuhan produk — pengujian terpisah</title></head><body><div id="root"></div><script type="module" src="/current-frozen-finance-entry.tsx"></script></body></html>'
  const paths=new Set(),routed=new Set(),virtual=resolve('current-frozen-finance.html')
  await build({configFile:false,root:process.cwd(),cacheDir:'.cache/current-frozen-finance-build',logLevel:'error',base:'/current-frozen-finance/',oxc:{jsx:{runtime:'automatic',refresh:false}},
    build:{outDir:'cp6-ui-build/current-frozen-finance',emptyOutDir:false,rollupOptions:{input:virtual}},
    plugins:[{name:'A-frozen-finance-host',enforce:'pre',resolveId(id,importer){
      if(id===virtual)return virtual
      if(id==='/current-frozen-finance-entry.tsx')return'\0current-frozen-finance-entry.tsx'
      if(importer&&callers.has(importer)&&resolve(dirname(importer),id)===source('src/lib/supabase')){routed.add(importer);return resolve(here,'client.ts')}
    },load(id){if(id===virtual)return html;if(id==='\0current-frozen-finance-entry.tsx')return entry},moduleParsed(m){if(m.id.startsWith(process.cwd()+'/')&&!m.id.includes('/node_modules/')&&m.id!==virtual)paths.add(m.id.slice(process.cwd().length+1))}}]})
  assert.deepEqual([...routed].sort(),[...callers].sort(),'Both exact B panels must use the A adapter; AuthProvider stays original')
  return{url:ui.origin+'/current-frozen-finance/current-frozen-finance.html',source_paths:[...paths].sort(),adapted_importers:[...routed].map(x=>x.slice(process.cwd().length+1)).sort(),actual_AuthProvider:true,actual_AuthGate:true,actual_Supabase_client:true,B_source_unchanged:true,default_application_adopted:false,actual_Auth_HTTP_credit:false}
}
