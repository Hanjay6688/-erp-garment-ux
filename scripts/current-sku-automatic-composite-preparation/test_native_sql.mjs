// Parse and resolve all prepared callback SQL against exact retained types.
// PREPARE never executes the business statements; no ERP case credit follows.
import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE);
const input=JSON.parse(await readFile(process.env.CP7_AUTO_NATIVE_SQL_INPUT,'utf8'));
assert.equal(input.classification,'ISOLATED_CALLBACK_SQL_ANALYSIS_NOT_ERP');
const db=new PGlite(),quote=s=>'"'+s.replaceAll('"','""')+'"';
let stage='SETUP';
try{
 await db.exec("create schema erp;create schema cp7_sku_conversion;set check_function_bodies=off;set search_path='';");
 for(const[name,columns]of Object.entries(input.tables)){
  await db.exec('create table '+name+'('+Object.entries(columns).map(([column,type])=>quote(column)+' '+type).join(',')+')');
 }
 for(const body of Object.values(input.functions))await db.exec(body);
 const columnCounters=[];
 for(const sql of input.old_column_counterexamples){
  let code=null;try{await db.exec('prepare old_bad_column_'+columnCounters.length+' as '+sql);}catch(error){code=error.code;}
  assert.equal(code,'42703','The actual retained column types must reject each old mistaken name');
  columnCounters.push({sql,sqlstate:code});
 }
 const checked=[],transactionControls=[];
 for(const statement of input.statements){
  stage='CALLBACK_LINE_'+statement.line;
  if(/^(savepoint|rollback to savepoint|release savepoint)\b/i.test(statement.sql)){
   transactionControls.push(statement);continue;
  }
  let number=0;const sql=statement.sql.replaceAll('%s',()=>'$'+(++number));
  await db.exec('prepare callback_'+checked.length+' as '+sql);
  checked.push({line:statement.line,parameters:number,sql:statement.sql});
 }
 for(const name of Object.keys(input.tables))assert.equal((await db.query('select count(*)count from '+name)).rows[0].count,0);
 const report={status:'POSTGRES17_CALLBACK_SQL_TYPES_PASS_NO_BUSINESS_EXECUTION',engine:(await db.query('select version()version')).rows[0].version,
  source:input.source,tables:Object.keys(input.tables),checked,transactionControls,columnCounters,actual_ERP_cases:0,business_commands_executed:0,production_go:false};
 assert(checked.length>10);assert.equal(transactionControls.length,3);
 await writeFile(process.env.CP7_AUTO_NATIVE_SQL_REPORT,JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({status:report.status,checked:checked.length,transaction_controls:transactionControls.length,old_column_counterexamples:columnCounters.length,business_commands_executed:0}));
}catch(error){
 const report={status:'FAILED',stage,error:{message:error.message,code:error.code,detail:error.detail,context:error.where},actual_ERP_cases:0};
 await writeFile(process.env.CP7_AUTO_NATIVE_SQL_REPORT,JSON.stringify(report,null,2)+'\n');console.error(JSON.stringify(report));process.exitCode=1;
}finally{await db.close();}
