const fs = require('node:fs'), path = require('node:path'), cp = require('node:child_process'), crypto = require('node:crypto')
const root = process.cwd(), src = path.resolve(process.argv[2]), output = path.resolve(process.argv[3])
const manifest = JSON.parse(fs.readFileSync(path.join(__dirname,'source-pins.json')))
const sha = data => crypto.createHash('sha1').update('blob '+data.length+'\0').update(data).digest('hex')
if (!process.env.ASTRA_LOCAL_INSTALLED) {
  if(cp.execFileSync('git',['rev-parse','HEAD'],{cwd:src,encoding:'utf8'}).trim()!==manifest.base)throw Error('Unexpected published base')
  for(const file of fs.readdirSync(path.join(__dirname,'ui-delta')).sort())
    cp.execFileSync('git',['apply','--whitespace=nowarn',path.join(__dirname,'ui-delta',file)],{cwd:src})
}
for (const [file,expected] of Object.entries(manifest.files))
  if(sha(fs.readFileSync(path.join(src,file)))!==expected)throw Error('Candidate source mismatch '+file)
fs.mkdirSync(output,{recursive:true})
const build=require(path.join(src,'node_modules/esbuild'))
build.build({absWorkingDir:src,stdin:{contents:fs.readFileSync(path.join(__dirname,'mobile-entry.tsx'),'utf8'),loader:'tsx',resolveDir:src},outfile:path.join(output,'ui.js'),bundle:true,jsx:'automatic',metafile:true,minify:true,define:{'process.env.NODE_ENV':'"production"'},plugins:[{name:'loopback-identity',setup(b){
  b.onResolve({filter:/\/auth\/AuthProvider$|^\.\/AuthProvider$/},()=>({path:'identity',namespace:'test'}))
  b.onResolve({filter:/\/lib\/supabase$/},()=>({path:'api',namespace:'test'}))
  b.onLoad({filter:/.*/,namespace:'test'},arg=>({resolveDir:src,contents:arg.path==='identity'?'export const useAuth=()=>window.auditAuth':"import {createClient} from '@supabase/supabase-js';const client=createClient(location.origin,'synthetic-disposable-test',{auth:{persistSession:false,autoRefreshToken:false,detectSessionInUrl:false}});export const getUatSupabaseClient=()=>client;"}))
}}]}).then(r=>{
  const modules=Object.keys(r.metafile.inputs).filter(x=>x.startsWith('src/'));
  for(const f of modules)if(!manifest.files[f])throw Error('Unpinned product dependency '+f)
  for(const [f,expected]of Object.entries({'tests/fixtures/nativeAnalysisStandin.json':'77522a959ed93c6fb5573dc08b7ad780c284a678','tests/fixtures/productionRecovery.ts':'65e673708fe2f3c3f1fc82a43cd4eade4c5ec6d9'}))
    if(sha(fs.readFileSync(path.join(src,f)))!==expected)throw Error('Published fixture changed')
  fs.copyFileSync(path.join(src,'tests/fixtures/nativeAnalysisStandin.json'),path.join(output,'sample.json'))
  fs.writeFileSync(path.join(output,'receipt.json'),JSON.stringify({candidate:manifest.candidate,modules:modules.length,checkedInputs:Object.keys(manifest.files).length}))
  console.log('ASTRA_PUBLIC_UI '+fs.readFileSync(path.join(output,'receipt.json'),'utf8'))
}).catch(e=>{console.error(e.message);process.exitCode=1})
