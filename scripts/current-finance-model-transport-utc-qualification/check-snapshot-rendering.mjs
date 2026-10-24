import assert from 'node:assert/strict'
import {readFileSync,writeFileSync} from 'node:fs'
import {createHash} from 'node:crypto'
import {PGlite} from '@electric-sql/pglite'
const source=readFileSync(new URL('../cp7_finance_capture/finance_capture.sql',import.meta.url),'utf8')
const table=source.slice(source.indexOf('create table cp7_finance_capture.captures('),source.indexOf('-- One stored chunk'))
const db=new PGlite(),checks=[]
try {
 await db.exec('create schema cp7_finance_capture;'+table)
 await db.query('insert into cp7_finance_capture.captures (id,actor,owner_kind,owner_id,query,dates,access_at_start,state,units_done,units_total,report,report_snapshot,report_read_at,report_ms,plan,book_signature,source_hash,created_at,updated_at,finished_at) values($1,$2,$3,$4,$5,$6,$7,$8,2,2,$9,pg_current_snapshot(),$10,1.234,$11,$12,$13,$14,$15,$16)',[
  '00000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000002','STAGED_ANALYSIS','00000000-0000-0000-0000-000000000003','{}','{}','{}','READY',
  JSON.stringify({amount:'123.45',fixed_timestamp:'2026-10-25T00:00:00+07:00'}),'2026-10-24 17:12:00.123456+00','{}','synthetic-book','synthetic-seal','2026-10-24 17:10:00.000001+00','2026-10-24 17:12:01.654321+00','2026-10-24 17:12:01.654321+00'])
 const read=async()=> (await db.query('select to_jsonb(c) value from cp7_finance_capture.captures c')).rows[0].value
 const canonical=async()=>{
  const zone=(await db.query('show TimeZone')).rows[0].TimeZone
  await db.query("select set_config('TimeZone','UTC',false)")
  try{return await read()}finally{await db.query("select set_config('TimeZone',$1,false)",[zone])}
 }
 const rows=[]
 for(const zone of ['UTC','Asia/Jakarta','America/Los_Angeles']){
  await db.query("select set_config('TimeZone',$1,false)",[zone])
  rows.push({zone,raw:await read(),canonical:await canonical()})
  assert.equal((await db.query('show TimeZone')).rows[0].TimeZone,zone)
 }
 assert.notDeepEqual(rows[0].raw,rows[1].raw);assert.notDeepEqual(rows[0].raw,rows[2].raw)
 checks.push('UNCHANGED_ROW_RAW_JSON_DIFFERS_BETWEEN_SESSIONS')
 assert.deepEqual(rows[0].canonical,rows[1].canonical);assert.deepEqual(rows[0].canonical,rows[2].canonical)
 checks.push('ALL_COLUMNS_UTC_EQUAL_IN_THREE_ZONES')
 const names=(await db.query("select attname from pg_attribute where attrelid='cp7_finance_capture.captures'::regclass and attnum>0 and not attisdropped")).rows.map(x=>x.attname)
 assert.deepEqual(Object.keys(rows[0].canonical).sort(),names.sort());checks.push('EVERY_ACTUAL_CAPTURE_COLUMN_RETAINED')
 assert.deepEqual(rows[0].canonical.report,{amount:'123.45',fixed_timestamp:'2026-10-25T00:00:00+07:00'})
 checks.push('NESTED_IMMUTABLE_JSON_STRINGS_UNCHANGED')
 await db.exec('begin');await db.query("update cp7_finance_capture.captures set report=jsonb_set(report,'{amount}',$1::jsonb)",[JSON.stringify('123.46')])
 assert.notDeepEqual(await canonical(),rows[0].canonical);await db.exec('rollback');checks.push('ONE_CENT_CHANGE_STILL_FAILS_EQUALITY')
 await db.exec('begin');await db.exec("update cp7_finance_capture.captures set updated_at=updated_at+interval '1 microsecond'")
 assert.notDeepEqual(await canonical(),rows[0].canonical);await db.exec('rollback');checks.push('ONE_MICROSECOND_CHANGE_STILL_FAILS_EQUALITY')
 assert.deepEqual(await canonical(),rows[0].canonical);checks.push('CONTROL_ROLLBACK_RETAINS_WHOLE_ROW')
 const receipt={status:'PASS',kind:'LOCAL_SQL_SYNTHETIC_CAPTURE_OBSERVER',checks,actual_capture_table_source_sha256:createHash('sha256').update(table).digest('hex'),column_count:names.length,rows,first_failed_capture_values_available:false,Native_Auth_race_credit:false,production_go:false}
 writeFileSync(new URL('./LOCAL_SNAPSHOT_SQL7.json',import.meta.url),JSON.stringify(receipt,null,2)+'\n')
 console.log(JSON.stringify({status:receipt.status,checks,columns:names.length,Native_Auth_race_credit:false}))
} finally {await db.close()}
