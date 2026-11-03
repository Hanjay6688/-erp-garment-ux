import fs from 'node:fs'
import crypto from 'node:crypto'
import {execFileSync} from 'node:child_process'
const file='docs/cp7/d17-14/ui-b-connected-20261103/SOURCE_V3.json',m=JSON.parse(fs.readFileSync(file))
const git=(...a)=>execFileSync('git',a),pin=b=>({bytes:b.length,sha256:crypto.createHash('sha256').update(b).digest('hex')})
const equal=(a,b,label)=>{if(JSON.stringify(a)!==JSON.stringify(b))throw Error(label)}
const require=(ok,label)=>{if(!ok)throw Error(label)}
require(m.base==='bb826c3b74ce962b507df92e7f94861f339165c1'&&m.production_go===false,'UI_SOURCE_CONTRACT')
const changed=git('diff','--name-only',m.base,'--','src').toString().trim().split('\n').filter(Boolean).sort()
equal(changed,Object.keys(m.UI_changes).sort(),'ONLY_DECLARED_UI_CHANGES')
for(const[p,refs]of Object.entries(m.UI_changes)){
 const before=git('show',m.base+':'+p),after=fs.readFileSync(p);equal(pin(before),refs.before,'BEFORE:'+p);equal(pin(after),refs.after,'AFTER:'+p)
 if(p.endsWith('.tsx')){const marker='  return <section className="initial-import">';const a=before.toString().indexOf(marker),b=after.toString().indexOf(marker);require(a>=0&&b>=0,'UI_RENDER_BOUNDARY');equal(after.toString().slice(0,b),before.toString().slice(0,a),'CONTROLLER_PARSERS_RPC_AND_GUARDS_UNCHANGED:'+p)}
}
for(const[p,refs]of Object.entries(m.new_files))equal(pin(fs.readFileSync(p)),refs,'FIXTURE_SOURCE:'+p)
for(const p of ['package.json','package-lock.json','vite.config.ts','src/auth/AuthProvider.tsx','src/lib/supabase.ts','src/useProductionMutation.ts','src/productionRecovery.ts','src/auth/accessCatalog.ts'])equal(fs.readFileSync(p).toString(),git('show',m.base+':'+p).toString(),'SHARED_CONTRACT_UNCHANGED:'+p)
const names=git('diff','--name-only',m.base,'--').toString().trim().split('\n').filter(Boolean)
for(const p of names)require(p in m.UI_changes||p in m.new_files||p===file,'UNDECLARED_CHANGE:'+p)
for(const command of [['node','scripts/check-source-ownership.mjs'],['node','scripts/check-access-catalog.mjs'],['node','scripts/check-css-ownership.mjs']])execFileSync(command[0],command.slice(1),{stdio:'inherit'})
console.log(JSON.stringify({status:'UI_SOURCE_ONLY_ADMITTED_NOT_BACKEND_ACCEPTANCE',UI_files:changed.length,actual_Auth:0,actual_SQL:0,production_go:false}))
