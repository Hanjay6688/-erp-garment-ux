// Compilation only over an aligned ERP schema, without its COPY/data. Auth/
// storage environment stubs do not authorize or execute any business command.
import{readFileSync}from'node:fs';import{gunzipSync}from'node:zlib';
import{createHash}from'node:crypto';import assert from'node:assert/strict';
const{PGlite}=await import(process.env.OW04_PGLITE_MODULE||'@electric-sql/pglite');
const schemaPath=process.env.OW04_LOCAL_ALIGNED_SCHEMA,derivedPath=process.env.OW04_LOCAL_DERIVED_PROFILES;
const acceptedPath=process.env.OW04_LOCAL_ACCEPTED_MANIFEST,posterPath=process.env.OW04_LOCAL_DERIVED_POSTER;
if(!schemaPath||!derivedPath||!acceptedPath||!posterPath)throw Error('Explicit local aligned schema and accepted/derived source paths required');
const read=p=>readFileSync(new URL(p,import.meta.url),'utf8');
const strip=s=>s.replace(/do \$not_an_installer\$\s*begin[\s\S]*?end \$not_an_installer\$;/g,'');
const raw=readFileSync(schemaPath,'utf8');let copy=false,copies=0;const ddl=[];
for(const line of raw.split('\n')){if(copy){if(line==='\\.')copy=false;continue}if(line.startsWith('COPY ')){copy=true;copies++;continue}if(line.startsWith('\\restrict ')||line.startsWith('\\unrestrict '))continue;ddl.push(line)}
const db=new PGlite(),completed=[];
async function exec(label,sql){await db.exec(sql);completed.push(label)}
try{
await exec('EXPLICIT_LOCAL_ENVIRONMENT_ONLY',`set timezone='UTC';create role anon;create role authenticated;create role service_role;create role cp7_capture;create role cp7_sales_read;create role cp7_credit_write nologin noinherit nobypassrls;
create schema auth;create schema storage;create schema extensions;
create table auth.users(id uuid primary key);create table storage.buckets(id text primary key);
create function auth.uid()returns uuid language sql stable as $$select null::uuid$$;
create function auth.jwt()returns jsonb language sql stable as $$select '{}'::jsonb$$;
create function extensions.digest(text,text)returns bytea language sql immutable as $$select pg_catalog.sha256(convert_to($1,'UTF8'))$$;`);
await exec('ALIGNED_ERP_SCHEMA_WITHOUT_COPY_DATA',ddl.join('\n'));
await exec('ACTUAL_SALES_REQUEST_TABLE_DECLARATIONS',"create schema cp7_sales;"+read('../../cp7-src/sales/commands.sql').split('create function cp7_sales.command_access')[0]);
await exec('ACTUAL_NOTE_TABLE_DECLARATIONS',read('../../cp7-src/sales/correction.sql').split('create function ')[0]);
await exec('ACTUAL_LEDGER_DDL',strip(read('../ledger/01_immutable_facts.proposal.sql')));
await exec('ACTUAL_NO_JOURNAL_SCHEMA_DELTA',strip(read('../source/NO_JOURNAL_SCHEMA_DIFF.proposal.sql')));
await exec('ACTUAL_KERNEL',read('../kernel/kernel.sql'));
await exec('ACTUAL_ORDINAL_WRAPPER',read('../ordinal-wrapper/wrapper.sql'));
await exec('ACTUAL_SOURCE_FUNCTIONS',strip(read('../source/source.sql')));
await exec('ACTUAL_CURRENT_READER_DECLARATIONS',strip(read('../readers/01_current_reader_capability.proposal.sql')));
await exec('ACTUAL_MATERIALIZED_READER_DECLARATIONS',strip(read('../readers/02_materialized_profile.proposal.sql')));
await exec('ACTUAL_INITIAL_TABLE_DECLARATIONS',strip(read('../coordinator/01_coordinator_facts.sql').split('-- Fixed factual reader.')[0]));
await exec('ACTUAL_REFUND_TABLE_DECLARATIONS',strip(read('../refund/01_initial_refund.proposal.sql').split('-- Separate, closed, one-call scope.')[0]));
await exec('ACTUAL_SOURCE_OPERATION_FACT_DECLARATIONS',strip(read('../reconciliation/01_source_operation_facts.sql')));
await exec('ACTUAL_REFUND_DATE_HELPER','create function cp7_credit.refund_physical_text'+read('../refund/01_initial_refund.proposal.sql').split('create function cp7_credit.refund_physical_text')[1].split('create function cp7_credit.initial_refund_proof_shape')[0]);
await exec('ACTUAL_NATIVE_CENT_HELPERS',read('../ledger/02_uuid_poster.proposal.sql').split('create function cp7_credit.native_cent_lines')[1].split('-- Private per-part')[0].replace(/^/,'create function cp7_credit.native_cent_lines'));
const accepted=JSON.parse(gunzipSync(readFileSync(acceptedPath))),pins={functions:{...JSON.parse(read('SOURCE_PINS.json')).functions,...JSON.parse(read('SOURCE_HISTORY_PINS.json')).functions}};
for(const[signature,pin]of Object.entries(pins.functions)){
 const definition=accepted.catalog.functions[signature][0];assert.equal(createHash('sha256').update(definition).digest('hex'),pin.definition_sha256);
 await exec('ACCEPTED_PREDECESSOR_'+signature,definition);
}
// pg_dump deliberately disables body checks for its unordered dependencies.
// Restore validation before any new consumer DDL or derivation is compiled.
await exec('ENABLE_NEW_FUNCTION_BODY_VALIDATION','set check_function_bodies=on');
await exec('PRIVATE_SCHEMA_OWNER_CREATE',`grant usage on schema cp7_credit to cp7_credit_write;grant create on schema cp7_credit,public to cp7_credit_write;`);
for(const name of ['01_dependency_graph.sql','02_operation_facts.sql','04_credit_book_bound.sql','05_event_data.sql','06_access_and_requests.sql','07_locked_projection.sql','08_owning_command.sql','09_deferred_closure.sql','10_capabilities.sql','11_source_history.sql'])await exec(name,strip(read(name)));
const derived=JSON.parse(readFileSync(derivedPath,'utf8'));
for(const[signature,definition]of Object.entries(derived))await exec('DERIVED_'+signature,definition);
await exec('ACTUAL_DERIVED_NATIVE_CONSUMER_POSTER',readFileSync(posterPath,'utf8'));
await exec('REMOVE_TEMPORARY_CREATE',`revoke create on schema cp7_credit,public from cp7_credit_write;`);
assert.equal(copies,215);assert.equal(Object.keys(derived).length,12);
assert.equal((await db.query("select current_setting('check_function_bodies')as enabled")).rows[0].enabled,'on');
console.log(JSON.stringify({classification:'LOCAL_PGLITE_ALIGNED_ERP_SCHEMA_AND_ACTUAL_CP7_DDL_WITH_AUTH_STORAGE_STUBS_COMPILE_ONLY_NOT_NATIVE_OR_BUSINESS_EXECUTION',status:'PASS',completed,aligned_schema_sha256:createHash('sha256').update(raw).digest('hex'),copy_sections_omitted:copies,check_function_bodies_enabled:true,actual_consumer_SQL_files_compiled:10,actual_source_derivations_compiled:12,actual_derived_native_poster_compiled:true,financial_command_executed:false,Native_cases_added:0,production_go:false}));
}catch(e){console.error(JSON.stringify({status:'FAIL_LOCAL_DDL_COMPILE',completed,error:e.message,query:e.query?.slice(0,300)}));process.exitCode=1}finally{await db.close()}
