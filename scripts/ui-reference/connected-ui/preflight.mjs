/* Compile/probe in the same process as the local fixture server. No browser/DB. */
import fs from 'node:fs'
import path from 'node:path'
import {execFileSync} from 'node:child_process'
import {server,stopAll,children} from './server.mjs'
const out=path.resolve(process.env.UI_PREFLIGHT_DIR??'../ui-connected-preflight');fs.mkdirSync(out,{recursive:false})
const report={checks:[],product_root_enabled:false,database_calls:0};let child
try{
 const running=await server(process.cwd(),4188,'fixture-preflight',out);child=running.child
 for(const target of ['/scripts/ui-reference/connected-ui/fixture.html','/src/ConnectedPocketFabricPage.tsx','/src/useProductionMutation.ts','/src/ConnectedInitialImportPage.tsx','/src/CutoverPanel.tsx']){
  const response=await fetch(running.url+target);if(!response.ok)throw Error('FIXTURE_COMPILE:'+target+':'+response.status);const source=await response.text()
  if(target.startsWith('/src/')){if(!source.includes('/scripts/ui-reference/connected-ui/auth.ts')||source.includes('/src/auth/AuthProvider.tsx'))throw Error('EXACT_TEST_AUTH_ALIAS:'+target)}
  report.checks.push({target,status:response.status})
 }
 for(const target of ['/','/index.html','/cp7-preview','/src/auth/AuthProvider.tsx','/src/lib/supabase.ts']){const response=await fetch(running.url+target);if(response.status!==403)throw Error('PRODUCT_ROOT_MUST_BE_REFUSED:'+target);report.checks.push({target,status:403})}
 try{execFileSync(process.execPath,['node_modules/vite/bin/vite.js','build','--config','scripts/ui-reference/connected-ui/vite.config.mjs','--mode','writer-b-connected-ui-fixture'],{stdio:'pipe'});throw Error('FIXTURE_MUST_NOT_BUILD')}
 catch(error){if(!String(error.stderr).includes('FIXTURE_CONFIG_SERVE_ONLY'))throw error;report.checks.push({fixture_production_build:'REFUSED'})}
 report.status='PASS'
}finally{await stopAll();report.server_started=children.length>0;report.server_reaped=children.length>0;fs.writeFileSync(path.join(out,'PREFLIGHT.json'),JSON.stringify(report,null,2)+'\n')}
console.log(JSON.stringify(report))
