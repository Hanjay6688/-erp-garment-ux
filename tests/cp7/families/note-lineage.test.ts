// @vitest-environment node
import {readFileSync}from'node:fs'
import {beforeEach,afterEach,test,expect}from'vitest'
import {openRuntime,jsonArg}from'./f04/runtime.mjs'
// Deliberate Native-shaped reader stubs. Actual financial proof requires Native40.
let db:Awaited<ReturnType<typeof openRuntime>>
const u=(n:number)=>`10000000-0000-4000-8000-${String(n).padStart(12,'0')}`
const previous=u(1),replacement=u(2),revision=u(3),product=u(4),location=u(5),lot=u(6),old5=u(10),old10=u(11),new5=u(30),new6=u(20)
const line=(qty:string)=>({product_id:product,qty_pcs:qty,unit_price_snapshot:'10.00',discount_amount:'0',notes:null})
beforeEach(async()=>{
 db=await openRuntime();await db.execute(`do $$begin if not exists(select 1 from pg_roles where rolname='postgres')then create role postgres nologin;end if;end$$;create role cp7_sales_write nologin;
 create schema erp;create schema cp7_note;create schema cp7_fg;
 create table cp7_note.revisions(id uuid primary key);insert into cp7_note.revisions values('${revision}');
 create function cp7_note.immutable_revision()returns trigger language plpgsql as $$begin raise exception 'CONTROL_IMMUTABLE';end$$;
 create table erp.sales_items(id uuid primary key,sale_id uuid,product_id uuid,qty_pcs integer,unit_price_snapshot numeric,discount_amount numeric,notes text);
 create table erp.fg_stock_movements(id uuid primary key,source_id uuid,source_type text,movement_type text,product_id uuid,location_id uuid,quality_grade text,lot_id uuid,book_order bigint,qty_signed numeric);
 create table cp7_fg.correction_movements(member_id uuid,origin_id uuid);
 -- Both runtimes must emulate the installed Native owner. Native PG16 opens
 -- as cp7_f04_test, while PGlite opens as postgres; this changes only the stubs.
 alter schema erp owner to postgres;alter schema cp7_note owner to postgres;alter schema cp7_fg owner to postgres;
 alter table erp.sales_items owner to postgres;alter table erp.fg_stock_movements owner to postgres;
 alter table cp7_note.revisions owner to postgres;alter table cp7_fg.correction_movements owner to postgres;
 insert into erp.sales_items values('${old5}','${previous}','${product}',5,10,0,null),('${old10}','${previous}','${product}',10,10,0,null),('${new5}','${replacement}','${product}',5,10,0,null),('${new6}','${replacement}','${product}',6,10,0,null);
 insert into erp.fg_stock_movements values('${u(40)}','${old5}','SALE_ITEM','SALE','${product}','${location}','GRADE_A','${lot}',1,-5),('${u(41)}','${old10}','SALE_ITEM','SALE','${product}','${location}','GRADE_A','${lot}',2,-10);
 ${readFileSync('scripts/cp7-src/sales/correction-lines.sql','utf8')}`)
})
afterEach(async()=>{await db?.close()})
const bind=async(items:unknown,ids?:unknown)=>db.query(`select cp7_note.bind_items('${previous}','${replacement}','${revision}',${jsonArg(items)},${ids===undefined?'null':jsonArg(ids)})`)
const origin=async(id:string)=>(await db.query(`select cp7_note.line_origin('${previous}','${id}','${product}','${lot}','${location}','GRADE_A') id`))[0].id
test('duplicate SKU5/10→5/6 keeps two original anchors even when new ids sort6 before5',async()=>{
 const before=await db.query('select *from erp.fg_stock_movements');await bind([line('5'),line('6')],[old5,old10]);expect(await origin(new5)).toBe(u(40));expect(await origin(new6)).toBe(u(41));expect(await db.query('select *from erp.fg_stock_movements')).toEqual(before)
 const pairs=await db.query('select previous_item_id,replacement_item_id from cp7_note.item_lineage order by request_position');expect(pairs).toEqual([{previous_item_id:old5,replacement_item_id:new5},{previous_item_id:old10,replacement_item_id:new6}])
})
test('explicit reordering preserves original identity; deleted lines are not shifted into the first matching SKU',async()=>{
 await db.execute(`delete from erp.sales_items where id='${new5}'`);await bind([line('6')],[old10]);expect(await origin(new6)).toBe(u(41));expect((await db.query('select previous_item_id from cp7_note.item_lineage'))[0].previous_item_id).toBe(old10)
 await expect(db.execute('update cp7_note.item_lineage set previous_item_id=null')).rejects.toThrow('CONTROL_IMMUTABLE')
})
test('held legacy payload without lineage pairs each SKU occurrence once using submitted full values',async()=>{
 await bind([line('5'),line('6')],undefined);expect(await origin(new5)).toBe(u(40));expect(await origin(new6)).toBe(u(41))
})
test('foreign, repeated or incomplete source references and unmatched Native replacement lines fail atomically',async()=>{
 for(const ids of[[old5,old5],[old5,u(99)],[old5]])await expect(bind([line('5'),line('6')],ids)).rejects.toThrow('CP7_NOTE_ITEM_LINEAGE')
 await expect(bind([line('5'),line('7')],[old5,old10])).rejects.toThrow('CP7_NOTE_ITEM_LINEAGE_NATIVE_MISMATCH')
 expect((await db.query('select count(*)::int n from cp7_note.item_lineage'))[0].n).toBe(0)
})
