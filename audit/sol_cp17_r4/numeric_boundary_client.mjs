// Read-only derivative execution of the exact candidate's text helpers.
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {createRequire} from 'node:module'
import {resolve} from 'node:path'
import {createHash} from 'node:crypto'
const root=resolve(process.argv[2]),require=createRequire(resolve(root,'package.json')),ts=require('typescript')
const sources={}
async function load(path,extra=''){
 const source=readFileSync(resolve(root,path),'utf8');sources[path]={sha256:createHash('sha256').update(source).digest('hex'),bytes:Buffer.byteLength(source),transformation:extra?'transpile in-memory plus explicit export of original private pure functions':'transpile in-memory; type-only imports erased'}
 const output=ts.transpileModule(source+extra,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ES2022}}).outputText
 return import('data:text/javascript;base64,'+Buffer.from(output).toString('base64'))
}
const procurement=await load('src/procurementContract.ts'),laundry=await load('src/laundryBd.ts'),pool=await load('src/hppPoolContract.ts','\nexport {money as solMoney,unit as solUnit,count as solCount}\n')
const controls=[]
for(const [value,accepted] of [['999999999999.999998',true],['999999999999.999999',true],['1000000000000.000000',false],['0.00001',true],['0.000001',true],['0.0000001',false],['21474836.47',true],['21474836.48',true],['21474836.49',true]]){
 assert.equal(procurement.moneyDecimal(value),accepted?value:null);controls.push({helper:'procurement.moneyDecimal',value,accepted})
}
for(const [value,accepted]of [['999999999999999.98',true],['999999999999999.99',true],['1000000000000000.00',false],['21474836.47',true],['21474836.48',true],['21474836.49',true]]){
 assert.equal(laundry.moneyInput(value),accepted);if(accepted)assert.equal(laundry.normalizeMoney(value),value);controls.push({helper:'laundry.moneyInput/normalizeMoney',value,accepted})
}
for(const [value,accepted]of [['999999998',true],['999999999',true],['1000000000',false]]){
 assert.equal(laundry.wholePcs(value),accepted);if(accepted)assert.ok(Number.isSafeInteger(Number(value)));controls.push({helper:'laundry.wholePcs',value,accepted})
}
for(const [helper,values]of [[pool.solMoney,['999999999999999999.98','999999999999999999.99','1000000000000000000.00']],[pool.solUnit,['9999999999999999.999999999998','9999999999999999.999999999999','10000000000000000.000000000000']]]){
 for(const [index,value]of values.entries()){
  if(index<2)assert.equal(helper(value),value);else assert.throws(()=>helper(value));controls.push({helper:helper===pool.solMoney?'pool.numeric20,2 text':'pool.numeric28,12 text',value,accepted:index<2})
 }
}
for(const [value,accepted]of [[9007199254740990,true],[9007199254740991,true],[9007199254740992,false]]){
 if(accepted)assert.equal(pool.solCount(value),value);else assert.throws(()=>pool.solCount(value));controls.push({helper:'pool.count safe integer',value:String(value),accepted})
}
for(const [path,metadata]of Object.entries(sources))assert.equal(createHash('sha256').update(readFileSync(resolve(root,path))).digest('hex'),metadata.sha256)
console.log(JSON.stringify({status:'PASS',controls,sources,pinned_source_not_modified:true,browser_executed:false,scope:'Pure actual helpers only. Float cents in Payables is sign/zero display classification, not amount payload. No global32-bit N/A or transaction acceptance inferred.'}))
