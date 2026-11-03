import fs from 'node:fs'
import crypto from 'node:crypto'
import {execFileSync} from 'node:child_process'
const file='docs/cp7/d17-14/ui-b-source-refusal-20261103/SOURCE.json'
const m=JSON.parse(fs.readFileSync(file))
const git=(...args)=>execFileSync('git',args,{encoding:'utf8'}).trim()
const require=(ok,message)=>{if(!ok)throw Error(message)}
const pin=b=>({bytes:b.length,sha256:crypto.createHash('sha256').update(b).digest('hex')})
require(m.base==='8678feba7652d1d483536d1baf82135030dc3548'&&m.production_go===false,'BASE_AND_SCOPE')
require(git('diff','--name-only',m.base,'--','src','package.json','package-lock.json','vite.config.ts')==='','PRODUCT_SOURCE_MUST_REMAIN_BASE_A')
require(git('rev-parse',m.base+':src')===m.src_tree,'EXACT_A_PRODUCT_TREE')
for(const[p,expected]of Object.entries(m.new_files))require(JSON.stringify(pin(fs.readFileSync(p)))===JSON.stringify(expected),'OWN_FILE_PIN:'+p)
for(const p of git('diff','--name-only',m.base).split('\n').filter(Boolean))require(p===file||Object.hasOwn(m.new_files,p),'UNDECLARED_CHANGE:'+p)
require(m.claim.actual_Auth===0&&m.claim.actual_SQL===0&&m.claim.adopted_by_A===false,'NO_ACTUAL_BACKEND_OR_ADOPTION_CLAIM')
console.log(JSON.stringify({status:'B_LOCAL_PROPOSAL_AND_RETAINED_VISUAL_REVIEW_ONLY',files:Object.keys(m.new_files).length,protected_A_src:m.src_files,product_source_changed:false,production_go:false}))
