import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {createHash} from 'node:crypto'
import {resolve,dirname} from 'node:path'
import {fileURLToPath} from 'node:url'
import {buildCurrentProgressFinance} from './build_3194.mjs'
import {cases as desktop} from './desktop.mjs'
import {cases as mobile} from './mobile.mjs'
const root=resolve(dirname(fileURLToPath(import.meta.url)),'../..')
const previous=process.env.SUPABASE_ANON_KEY
try{
 process.env.SUPABASE_ANON_KEY='source-build-placeholder-not-an-Auth-credential'
 const built=await buildCurrentProgressFinance({origin:'http://127.0.0.1:4176',api:'http://127.0.0.1:32768'})
 const expected=JSON.parse(readFileSync(resolve(root,'scripts/current-finance-combined-browser-qualification/BUILD_SOURCE_3194.json')))
 const actual=built.source_paths.map(path=>{const raw=readFileSync(resolve(root,path));return{path,bytes:raw.length,sha256:createHash('sha256').update(raw).digest('hex')}})
 assert.deepEqual(actual,expected.files)
 const rows=[...await desktop({},'2026-10-28'),...await mobile({},'2026-10-28')]
 assert.equal(rows.length,2);assert.ok(rows.every(x=>typeof x[1]==='function'))
 console.log(JSON.stringify({status:'PASS_SOURCE_BUILD_ONLY',compiled_files:actual.length,runtime_replacements:built.declared_runtime_replacements,real_Auth:false,browser_executed:false}))
}finally{if(previous===undefined)delete process.env.SUPABASE_ANON_KEY;else process.env.SUPABASE_ANON_KEY=previous}
