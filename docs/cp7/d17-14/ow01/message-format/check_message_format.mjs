// Actual formatter SQL, isolated in-memory PGlite; no Native data or provider.
// EXPECTED.json was frozen before this runner and before product edits.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';

const directory=path.dirname(fileURLToPath(import.meta.url));
const sourcePath=path.resolve(process.argv[2]??path.join(directory,'BEFORE_b65_alerts.sql'));
const outputPath=path.resolve(process.argv[3]??path.join(directory,'BEFORE_RESULT.json'));
assert.equal(path.dirname(outputPath),directory,'write receipts only in proposal directory');
const {PGlite}=await import(process.env.OW01_PGLITE_MODULE??'/workspace/scratch/9442228ed2dc/sql-dev/node_modules/@electric-sql/pglite/dist/index.js');
const sha=s=>createHash('sha256').update(s).digest('hex');
const source=await fs.readFile(sourcePath,'utf8'),expectedText=await fs.readFile(path.join(directory,'EXPECTED.json'),'utf8'),expected=JSON.parse(expectedText);
const result={classification:'ISOLATED_ACTUAL_FORMATTER_SQL_LITERAL_EXPECTED_NOT_NATIVE',native_execution_proven:false,
 active_repo_modified:false,source_path:sourcePath,source_sha256:sha(source),expected_sha256:sha(expectedText),declared_cases:[...expected.cases],
 required_settings_stub:null,functions:[],cases:[]};
const db=new PGlite();
const roots=['num','rp','tgl','label','item_line','render'],definitions=new Map(),visiting=new Set(),ordered=[];
function definition(name){
 if(definitions.has(name))return definitions.get(name);
 const pattern=new RegExp(`^create\\s+(?:or\\s+replace\\s+)?function\\s+cp7_alert_native\\.${name}\\s*\\(`,'im');
 const found=pattern.exec(source);assert.ok(found,`actual formatter dependency missing: ${name}`);
 const rest=source.slice(found.index),body=/\bas\s+(\$[A-Za-z_0-9]*\$)/i.exec(rest);
 assert.ok(body,`missing dollar body ${name}`);
 const end=rest.indexOf(body[1]+';',body.index+body[0].length);
 assert.ok(end>=0,`missing function end ${name}`);
 const text=rest.slice(0,end+body[1].length+1);definitions.set(name,text);return text;
}
function visit(name){
 if(ordered.includes(name))return;
 assert.ok(!visiting.has(name),`formatter dependency cycle ${name}`);visiting.add(name);
 const text=definition(name);
 for(const call of text.matchAll(/cp7_alert_native\.([a-z_][a-z0-9_]*)\s*\(/g))if(call[1]!==name)visit(call[1]);
 visiting.delete(name);ordered.push(name);
}
const clone=x=>structuredClone(x),e=expected.literal,input=expected.input;
function unknown(label=input.label,n=0){return{kind:'LAUNDRY_RECEIPT',title:`Laundry review ${String(n).padStart(2,'0')}`,subject_key:`LAUNDRY_RECEIPT:${n}`,party_names:['BD vendor P16 Native obligation'],repeat:false,
 detail:{domain:'LAUNDRY_RECEIPT',label,state:'DATA_REVIEW',economic_state:'UNKNOWN',remaining_state:'UNKNOWN',remaining:null,due_date:null}};}
function known(label=input.label){const item=unknown(label);item.kind='LAUNDRY_AP';item.detail={domain:'LAUNDRY_AP',label,state:'READY',economic_state:'OPEN',remaining_state:'KNOWN',remaining:input.known_amount,due_date:input.due_date};return item;}
const q=(sql,args=[])=>db.query(sql,args);
const scalar=async(sql,args=[])=>(await q(sql,args)).rows[0].value;
const line=item=>scalar('select cp7_alert_native.item_line($1::jsonb,\'DETAILED\')as value',[JSON.stringify(item)]);
const render=(items,detail='DETAILED')=>scalar("select cp7_alert_native.render('INSTANT',$1::jsonb,'{}'::text[],$2,5,$3::timestamptz,'{}'::jsonb)as value",[JSON.stringify(items),detail,input.at]);
const length=s=>[...s].length;
const checkBody=body=>{assert.ok(length(body)>0&&length(body)<=1000,'body must fit1000 codepoints');assert.ok(body.endsWith('Buka ERP > Reminder'),'full footer');assert.ok(!body.includes('FAIL'),'positive-provider sentinel must not occur');};
async function test(id,run){assert.ok(expected.cases.includes(id),'undeclared case');assert.ok(!result.cases.some(r=>r.id===id),'duplicate case');const row={id,status:'PASS'};try{await run(row);}catch(error){row.status='FAIL';row.error=String(error.message??error);row.sql_where=error.where??null;}result.cases.push(row);}
try{
 await db.exec('create schema cp7_alert_native;set TimeZone=\'UTC\';');
 for(const root of roots)visit(root);
 for(const name of ordered){const text=definition(name);await db.exec(text);result.functions.push({name,sha256:sha(text)});}
 assert.equal(length(e.exact_unknown_line),138);assert.equal(length(e.long_unknown_line),256);assert.equal(length(e.long_known_line),256);
 await test('EXACT_NATIVE_LRC_UNKNOWN138',async r=>{r.observed=await line(unknown());r.old_precise_truncation=r.observed===e.old_exact_unknown_line;assert.equal(r.observed,e.exact_unknown_line);assert.equal(length(r.observed),138);});
 await test('KNOWN_FULL_MAXCENT_AND_DATE',async r=>{r.observed=await line(known());assert.equal(r.observed,e.exact_known_line);assert.ok(r.observed.endsWith(e.known_suffix));});
 await test('OVERLONG_LABEL_UNKNOWN_SUFFIX256',async r=>{r.observed=await line(unknown(input.long_label));assert.equal(r.observed,e.long_unknown_line);assert.equal(length(r.observed),256);assert.ok(r.observed.endsWith('…'+e.unknown_suffix));});
 await test('OVERLONG_LABEL_KNOWN_SUFFIX256',async r=>{r.observed=await line(known(input.long_label));assert.equal(r.observed,e.long_known_line);assert.equal(length(r.observed),256);assert.ok(r.observed.endsWith('…'+e.known_suffix));});
 await test('DETAILED_EXACT_LRC_BODY',async r=>{const item=unknown(),before=JSON.stringify(item);r.observed=await render([item]);assert.equal(r.observed,e.detailed_unknown_body);checkBody(r.observed);assert.equal(JSON.stringify(item),before,'input/source detail/IDs immutable');});
 await test('SUMMARY_UNKNOWN_REVIEW_PRIVACY',async r=>{r.observed=await render([unknown()],'SUMMARY');assert.equal(r.observed,e.summary_unknown_body);checkBody(r.observed);assert.ok(!r.observed.includes(input.label)&&!r.observed.includes('BD vendor'),'SUMMARY hides parties/labels');assert.ok(!r.observed.includes('Rp0'),'UNKNOWN notzero');});
 await test('SUMMARY_KNOWN_EXACT_VALUE_PRIVACY',async r=>{r.observed=await render([known()],'SUMMARY');assert.equal(r.observed,e.summary_known_body);checkBody(r.observed);assert.ok(!r.observed.includes(input.label)&&!r.observed.includes('BD vendor'),'SUMMARY hides parties/labels');});
 await test('MULTI_WHOLE_LINES_1000_FOOTER',async r=>{const items=input.multi_labels.map((label,n)=>unknown(label,n)),before=JSON.stringify(items);r.observed=await render(items);assert.equal(r.observed,e.multi_body);checkBody(r.observed);r.body_length=length(r.observed);const shown=r.observed.split('\n').filter(s=>s.startsWith('- ')&&!s.startsWith('- dan '));assert.equal(shown.length,e.multi_shown);assert.ok(shown.every(s=>length(s.slice(2))===256&&s.endsWith('…'+e.unknown_suffix)),'only complete protected lines');assert.ok(r.observed.includes(`- dan ${e.multi_omitted} lainnya`),'all omitted items counted');assert.equal(JSON.stringify(items),before,'source detail/IDs immutable');});
 await test('LEGACY_FG_UNCHANGED',async r=>{const item={kind:'FG_AT_REORDER_POINT',detail:{product_name:'Model pcs',size_code:null,free_pcs:'10',wip_status:'UNKNOWN',wip_pcs:null,reorder_point_pcs:'25'}};r.observed=await line(item);assert.equal(r.observed,e.legacy_fg_line);});
 await test('ACTUAL_SCALARS_UNCHANGED',async r=>{r.observed={num:await scalar("select cp7_alert_native.num('1.234')value"),rp:await scalar("select cp7_alert_native.rp('17312.90')value"),tgl:await scalar("select cp7_alert_native.tgl('2026-10-20')value"),label:await scalar('select cp7_alert_native.label($1::timestamptz)value',[input.at])};assert.deepEqual(r.observed,e.scalars);});
 assert.deepEqual(result.cases.map(r=>r.id),expected.cases,'exact declared order/count');
 result.passed=result.cases.filter(r=>r.status==='PASS').length;result.failed=result.cases.filter(r=>r.status==='FAIL').length;
 result.status=result.failed?'FAIL':'PASS';
}catch(error){result.status='HARNESS_FAILED';result.error=String(error.stack??error);result.sql_where=error.where??null;}
finally{await db.close();await fs.writeFile(outputPath,JSON.stringify(result,null,2)+'\n');}
console.log(JSON.stringify({status:result.status,passed:result.passed??0,failed:result.failed??0,expected_sha256:result.expected_sha256,source_sha256:result.source_sha256,receipt:outputPath}));
if(result.status!=='PASS')process.exitCode=1;
