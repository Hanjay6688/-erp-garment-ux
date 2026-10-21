import { PGlite } from '/workspace/scratch/9442228ed2dc/sql-dev/node_modules/@electric-sql/pglite/dist/index.js';
import fs from 'node:fs';
import crypto from 'node:crypto';
const dir=new URL('.',import.meta.url),read=name=>fs.readFileSync(new URL(name,dir),'utf8');
const db=new PGlite();const results=[];
try {
 await db.exec("set check_function_bodies=on;set search_path='';create schema erp;create schema cp7_credit;");
 for(const role of ['anon','authenticated','service_role','cp7_capture','cp7_sales_read','cp7_sales_write'])await db.exec('create role '+role);
 for(const table of ['sales_headers','sales_payments','sales_returns','fg_stock_movements','journal_entries','hpp_versions'])await db.exec('create table erp.'+table+'(id uuid primary key)');
 await db.exec(read('ACTUAL_PG_HASH_HELPER.sql'));
 const actual=await db.query(read('CAPTURE_QUERY.sql'));
 if(actual.rows.length!==1)throw new Error('CAPTURE_QUERY_CARDINALITY');
 results.push({id:'ACTUAL_CAPTURE_QUERY_ON_LABELLED_EMPTY_SCAFFOLD',status:'PASS',native:false});
 const sql=read('RUNTIME_SYNTAX_ONLY.sql');await db.exec(sql);
 const setting=await db.query('show check_function_bodies');
 if(setting.rows[0].check_function_bodies!=='on')throw new Error('VALIDATOR_NOT_ON');
 results.push({id:'ACTUAL_RENDERED_RUNTIME_FUNCTION_VALIDATOR',status:'PASS',check_function_bodies:'on',expected_digest:'explicit zero compiler placeholder; never installer input'});
 let refused;
 try {await db.query('select cp7_credit.assert_source_native_trigger_census_v1()');}
 catch(error){refused={sqlstate:error.code,message:error.message};}
 if(refused?.sqlstate!=='P0001'||refused?.message!=='CP7_CREDIT_SOURCE_NATIVE_TRIGGER_CENSUS_CHANGED')throw new Error('RUNTIME_GUARD_DID_NOT_REFUSE_WRONG_CATALOGUE: '+JSON.stringify(refused));
 results.push({id:'ACTUAL_RUNTIME_WRONG_CATALOGUE_REFUSED',status:'PASS',observed:refused});
 const model=read('SYNTHETIC_CATALOG_MODEL.json');
 const hash=await db.query('select cp7_credit.pg_jsonb_sha256($1::jsonb)as hash',[model]);
 if(!/^[0-9a-f]{64}$/.test(hash.rows[0].hash))throw new Error('PG_HASH_NOT_SHA256');
 results.push({id:'ACTUAL_PG_JSONB_HASH_HELPER_SYNTHETIC_MODEL',status:'PASS',sha256_pg:hash.rows[0].hash,native:false});
 const report={classification:'LOCAL_EPHEMERAL_POSTGRES18_RENDERER_SYNTAX_AND_CATALOGUE_REFUSAL_ONLY',engine:(await db.query('select version()as version')).rows[0].version,production_go:false,native_executed:false,money_rows:0,real_database_connections:0,runtime_input_sha256:crypto.createHash('sha256').update(sql).digest('hex'),results,limits:['Empty labelled six-table scaffold, not accepted ERP installation.','Explicit zero expected digest exercises refusal only; real installer computes PG-canonical digest from source-validated actual snapshot.','No payment, stock, locking concurrency, actor authorization or Native63 acceptance.']};
 fs.writeFileSync(new URL('RESULT.json',dir),JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({controls:results.length,PASS:results.length,native_executed:false,runtime_sql_bytes:Buffer.byteLength(sql)}));
} catch(error){fs.writeFileSync(new URL('FIRST_ERROR.json',dir),JSON.stringify({message:error.message,sqlstate:error.code,stack:error.stack},null,2)+'\n');console.log(JSON.stringify({status:'FAILED',message:error.message,sqlstate:error.code}));process.exitCode=1;}
finally {await db.close();}
