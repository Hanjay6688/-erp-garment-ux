// Build the prepared panel under the existing disposable host's origin.
// Actual AuthProvider, AuthGate, runtime guard and Supabase client; no mock imports.
import assert from 'node:assert/strict'
import {build} from 'vite'
import {resolve} from 'node:path'
export async function buildPreparedFinance(ui){
 assert.equal(ui.origin,'http://127.0.0.1:4176')
 assert.equal(process.env.AUDITOR_UI_MODE??'DISPOSABLE','DISPOSABLE')
 const api=new URL(ui.api);assert.equal(api.hostname,'127.0.0.1');assert.ok(Number(api.port)>=32768&&Number(api.port)<=65535)
 const environment={VITE_ERP_RUNTIME_MODE:'DISPOSABLE_TEST',VITE_SUPABASE_URL:ui.api,VITE_DISPOSABLE_API_PORT:api.port,VITE_SUPABASE_ANON_KEY:process.env.SUPABASE_ANON_KEY}
 assert.ok(environment.VITE_SUPABASE_ANON_KEY)
 const entry=`import React from 'react';import{createRoot}from'react-dom/client';
import{AuthProvider}from'${resolve('src/auth/AuthProvider.tsx')}';import{AuthGate}from'${resolve('src/auth/AuthGate.tsx')}';
import{parseRuntimeConfig}from'${resolve('src/config/runtime.ts')}';import Panel from'${resolve('scripts/cp7_frozen_finance_ui/client/NativeFrozenFinancePanel.tsx')}';
import '${resolve('src/styles.css')}';import '${resolve('src/auth/auth.css')}';
const runtime=parseRuntimeConfig(${JSON.stringify(environment)},{mode:'cp6-disposable-test',pageOrigin:location.origin});
const q=JSON.parse(new URLSearchParams(location.search).get('query')??'null');
const root=createRoot(document.getElementById('root')),idle=()=>{};
root.render(<AuthProvider runtime={runtime}><AuthGate><main style={{maxWidth:1100,margin:'auto',padding:16}}><Panel query={q} onSourceReadStart={idle} onSourceReadEnd={idle} onClose={()=>root.unmount()}/></main></AuthGate></AuthProvider>);`
 const html='<!doctype html><html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Kebutuhan produk — pengujian terpisah</title></head><body><div id="root"></div><script type="module" src="/frozen-finance-auth-entry.tsx"></script></body></html>'
 const paths=new Set(),virtual=resolve('frozen-finance-auth.html')
 await build({configFile:false,root:process.cwd(),logLevel:'error',base:'/frozen-finance-auth/',oxc:{jsx:{runtime:'automatic',refresh:false}},
  build:{outDir:'cp6-ui-build/frozen-finance-auth',emptyOutDir:false,rollupOptions:{input:virtual}},
  plugins:[{name:'prepared-auth-entry',resolveId(id){if(id===virtual)return virtual;if(id==='/frozen-finance-auth-entry.tsx')return'\0frozen-finance-auth-entry.tsx'},load(id){if(id===virtual)return html;if(id==='\0frozen-finance-auth-entry.tsx')return entry},moduleParsed(m){if(m.id.startsWith(process.cwd()+'/')&&!m.id.includes('/node_modules/')&&m.id!==virtual)paths.add(m.id.slice(process.cwd().length+1))}}]})
 return{url:ui.origin+'/frozen-finance-auth/frozen-finance-auth.html',source_paths:[...paths].sort(),actual_AuthProvider:true,actual_AuthGate:true,actual_Supabase_client:true,default_application_adopted:false}
}
