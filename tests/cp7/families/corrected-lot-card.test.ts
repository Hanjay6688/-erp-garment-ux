// @vitest-environment node
import {readFileSync}from'node:fs'
import {beforeAll,afterAll,test,expect}from'vitest'
import {openRuntime,jsonArg}from'./f04/runtime.mjs'
// Deliberate raw reader stubs only; actual Native business proof is Native36.
let db:Awaited<ReturnType<typeof openRuntime>>
const product='10000000-0000-4000-8000-000000000001',a='10000000-0000-4000-8000-000000000002',b='10000000-0000-4000-8000-000000000003',location='10000000-0000-4000-8000-000000000004'
beforeAll(async()=>{
 db=await openRuntime()
 await db.execute(`create role cp7_fg_read nologin;create schema erp;create schema cp7_fg authorization cp7_fg_read;
 create table erp.fg_stock_movements(id uuid primary key,product_id uuid,lot_id uuid,location_id uuid,quality_grade text,physical_at timestamptz,system_created_at timestamptz,movement_type text,source_type text,source_id uuid,reversal_of_id uuid,customer_id uuid,notes text,book_order bigint,qty_signed numeric);
 create table erp.customers(id uuid,customer_name text);
 create table cp7_fg.correction_movements(member_id uuid,origin_id uuid,correction_id uuid,recorded_at timestamptz);
 create function erp.bf_commercial_sku_at_v1(uuid,timestamptz)returns text language sql as $$select 'SKU-REAL-TIME'::text$$;
 create function cp7_fg.access_now(text)returns jsonb language sql as $$select '{"can_value":false}'::jsonb$$;
 create function cp7_fg.lot_value(uuid,numeric)returns jsonb language sql as $$select '{"state":"UNKNOWN","unit_cost":null}'::jsonb$$;
 create function cp7_fg.positions(text,boolean)returns table(product_id uuid,product_sku text,commercial_sku text,product_name text,size_code text,brand_name text,lot_id uuid,lot_number text,location_id uuid,location_name text,quality_grade text)language sql as $$select distinct m.product_id,'SKU','SKU','Product','M','Brand',m.lot_id,m.lot_id::text,m.location_id,'Warehouse',m.quality_grade from erp.fg_stock_movements m$$;
 grant usage on schema erp to cp7_fg_read;grant select on all tables in schema erp,cp7_fg to cp7_fg_read;
 ${readFileSync('scripts/cp7-src/fg/corrected-ledger.sql','utf8')}`)
},120000)
afterAll(async()=>{if(db)await db.close()})
const card=async(lot:string,extra={})=>(await db.query(`select public.erp_cp7_get_fg_ledger_v2(${jsonArg({product_id:product,lot_id:lot,location_id:location,quality_grade:'GRADE_A',limit:100,offset:0,...extra})}) r`))[0].r
test('cross-lot corrections restore old lot, debit replacement lot, preserve originals and filter after the complete prefix',async()=>{
 const ids=Array.from({length:7},(_,i)=>`20000000-0000-4000-8000-${String(i+1).padStart(12,'0')}`),corr='30000000-0000-4000-8000-000000000001'
 const facts=[{lot:a,qty:100,at:1,type:'OPENING',reversal:null},{lot:b,qty:40,at:1,type:'OPENING',reversal:null},{lot:a,qty:-24,at:2,type:'SALE',reversal:null},{lot:a,qty:24,at:2,type:'REVERSAL',reversal:ids[2]},{lot:b,qty:-12,at:2,type:'SALE',reversal:null},{lot:a,qty:-3,at:3,type:'SALE',reversal:null},{lot:b,qty:-5,at:3,type:'SALE',reversal:null}]
 for(const[f,r]of facts.entries())await db.execute(`insert into erp.fg_stock_movements values('${ids[f]}','${product}','${r.lot}','${location}','GRADE_A','2025-10-0${r.at}T01:00:00.123456Z','2026-10-01T01:00:00.00000${f}Z','${r.type}','SALE_ITEM','${ids[f]}',${r.reversal?`'${r.reversal}'`:'null'},null,'${f===5||f===6?'LATER':'SOURCE'}',${f+1},${r.qty})`)
 await db.execute(`insert into cp7_fg.correction_movements values('${ids[3]}','${ids[2]}','${corr}',clock_timestamp()),('${ids[4]}','${ids[2]}','${corr}',clock_timestamp())`)
 const old=await card(a),replacement=await card(b)
 expect(old.balances.physical_qty).toBe('97');expect(replacement.balances.physical_qty).toBe('23')
 const sourceA=old.page.rows.find((r:{id:string})=>r.id===ids[2]),sourceB=replacement.page.rows.find((r:{id:string})=>r.id===ids[2])
 expect([sourceA.physical_delta,sourceA.original_physical_delta,sourceA.correction_count,sourceA.audit_movements.length]).toEqual(['0','-24','1',2])
 expect([sourceB.physical_delta,sourceB.original_physical_delta,sourceB.correction_count,sourceB.audit_movements.length]).toEqual(['-12','0','1',1])
 expect(sourceA.audit_movements.every((r:{lot_id:string})=>r.lot_id===a)).toBe(true);expect(sourceB.audit_movements.every((r:{lot_id:string})=>r.lot_id===b)).toBe(true)
 const filtered=await card(a,{q:'LATER',limit:1});expect(filtered.page.rows[0].physical_balance).toBe('97');expect(filtered.page.total).toBe('1');expect(filtered.balances.physical_qty).toBe('97')
 expect((await db.query(`select qty_signed::text qty from erp.fg_stock_movements where id='${ids[2]}'`))[0].qty).toBe('-24')
 await expect(card(a,{history_complete:true})).rejects.toThrow('CP7_FG_QUERY')
})
