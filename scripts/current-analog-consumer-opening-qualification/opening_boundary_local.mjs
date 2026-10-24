// Execute the exact production availability function over controlled facts.
// This local SQL witness is not a Native posting, Auth or full-chain claim.
import {readFile,writeFile} from 'node:fs/promises'
import {createHash} from 'node:crypto'
import assert from 'node:assert/strict'
const {PGlite}=await import(process.env.CP7_PGLITE_MODULE??'@electric-sql/pglite')
const path='scripts/cp7-src/planning/history.sql',source=await readFile(path,'utf8')
const functions=source.match(/create function cp7_planning\.history_availability\([\s\S]*?\$\$;/g)
assert.equal(functions?.length,1)
const db=new PGlite(),results=[]
try{
 await db.exec('create schema cp7_planning;'+functions[0])
 const query={from_date:'2026-10-21',through_date:'2026-10-23',group_mode:'AS_SOLD'}
 const product={id:'COMPARATOR',root_id:'COMPARATOR',size_id:'M',established_at:'2026-06-15T00:00:00Z'}
 const movement=(id,physical_at,qty_signed)=>({id,root_id:product.root_id,quality_grade:'GRADE_A',physical_at,book_order:id,qty_signed})
 for(const [name,opening,expected]of[
  ['FIRST_FIXTURE_OPENING_ON_FIRST_QUERY_DAY','2026-10-21T00:00:00+07:00',['STOCKOUT','AVAILABLE','AVAILABLE']],
  ['SUCCESSOR_OPENING_PRECEDES_THREE_QUERY_DAYS','2026-10-20T00:00:00+07:00',['AVAILABLE','AVAILABLE','AVAILABLE']]
 ]){
  const c={captured_at:'2026-10-24T12:00:00Z',facts:{products:[product],stock:[movement('1',opening,'800'),movement('2','2026-10-23T10:00:00+07:00','-1')]}}
  const rows=(await db.query('select cp7_planning.history_availability($1::jsonb,$2::jsonb)v',[JSON.stringify(c),JSON.stringify(query)])).rows[0].v
  assert.deepEqual(rows.map(r=>r.state),expected)
  results.push({name,status:'PASS',opening,query,days:rows.map(({date,state})=>({date,state})),available_days:rows.filter(r=>r.state==='AVAILABLE').length})
 }
 const report={status:'PASS',classification:'ACTUAL_SQL_OVER_CONTROLLED_FACTS_PGLITE_NOT_NATIVE',sources:{[path]:createHash('sha256').update(source).digest('hex')},cases:results,product_rule_changed:false,production_go:false}
 if(process.argv[2])await writeFile(process.argv[2],JSON.stringify(report,null,2)+'\n')
 console.log(JSON.stringify(report))
}finally{await db.close()}
