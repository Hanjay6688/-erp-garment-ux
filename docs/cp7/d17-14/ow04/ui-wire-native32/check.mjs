import fs from 'node:fs';import zlib from 'node:zlib';import path from 'node:path';import assert from 'node:assert/strict';import {createHash}from'node:crypto';import{pathToFileURL}from'node:url';
const repo=process.env.ERP_REPO||process.cwd(),here=path.dirname(new URL(import.meta.url).pathname),source=process.env.OW04_PARSER_SOURCE||path.join(here,'salesReturnSettlementContract.proposal.ts');
const declaration={classification:'UI_PARSER_VS_REUSED_NATIVE32_WIRE_NOT_NEW_NATIVE_OR_BROWSER',native_candidate:'3f7e0329eb296d98ad8ea0fcdffc1e93e8bd34b0',run:39485291311,job:118844009987,expected:'All12 real server quotes and outcomes parse; frontend command document exactly equals the actual settled envelope; contradictory money, wrong outcome digest and changed source version reject. Same unmodified proposal parser, no RPC/DB/browser.'};
fs.writeFileSync(here+'/DECLARATION.json',JSON.stringify(declaration,null,2)+'\n');
const m=await import(pathToFileURL(source));
const raw=zlib.gunzipSync(fs.readFileSync(path.join(repo,'docs/cp7/d17-14/ow04/CI_3F7E_NATIVE32_RUNTIME.log.gz'))).toString('utf8');
const rows=[];for(const l of raw.split('\n')){let i=l.indexOf('{');if(i<0)continue;try{const r=JSON.parse(l.slice(i));if(r.case&&r.actual_quote)rows.push(r);}catch{}}
assert.equal(rows.length,12);const results=[];let current;
const check=(name,f,refused=false)=>{let e;try{f()}catch(x){e=x}if(refused)assert(e,name);else if(e)throw e;results.push({case:current.case,assertion:name,status:'PASS',observed_error:e?.message||null});};
try{for(const row of rows){current=row;
 check('actual_quote',()=>m.parseSettlementQuote(row.actual_quote,row.actual_quote.input_echo));
 check('actual_envelope',()=>assert.deepEqual(m.commitIntent(row.actual_quote).payload,row.request_envelope.payload));
 check('actual_outcome',()=>m.parseSettlementOutcome(row.actual_outcome,row.request_envelope.id,row.request_envelope.payload));
 check('contradictory_money_refused',()=>{const v=structuredClone(row.actual_quote);v.totals.after.effective_paid='799.99';m.parseSettlementQuote(v,row.actual_quote.input_echo)},true);
 check('wrong_outcome_digest_refused',()=>{const v=structuredClone(row.actual_outcome);v.quote_sha256=v.quote_sha256==='0'.repeat(64)?'1'.repeat(64):'0'.repeat(64);m.parseSettlementOutcome(v,row.request_envelope.id,row.request_envelope.payload)},true);
 check('changed_source_version_refused',()=>{const v=structuredClone(row.actual_quote);v.source.row_version=String(BigInt(v.source.row_version)+1n);m.parseSettlementQuote(v,row.actual_quote.input_echo)},true);
}
const out={...declaration,status:'PASS',native_pairs:rows.length,assertion_count:results.length,parser_sha256:createHash('sha256').update(fs.readFileSync(source)).digest('hex'),results};fs.writeFileSync(here+'/RESULT.json',JSON.stringify(out,null,2)+'\n');console.log(JSON.stringify({status:'PASS',native_pairs:rows.length,assertion_count:results.length}));}
catch(e){const out={...declaration,status:'FAIL',first_case:current?.case,error:e.message,stack:e.stack,results};fs.writeFileSync(here+'/FIRST_FAILURE.json',JSON.stringify(out,null,2)+'\n');console.error(JSON.stringify({status:'FAIL',first_case:current?.case,error:e.message,stack:e.stack}));process.exitCode=1;}
