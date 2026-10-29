// @vitest-environment node
import { readFileSync } from 'node:fs'
import { execFileSync } from 'node:child_process'
import { beforeEach, afterEach, test, expect } from 'vitest'
import { openRuntime, jsonArg } from './f04/runtime.mjs'

// The new module's real SQL executes here; selected-lot Native posting, Auth,
// journals and the predecessor workspace are explicit test doubles. This is
// NOT actual Native/Auth/installation/complete-HPP qualification evidence.
let db: Awaited<ReturnType<typeof openRuntime>>
const u = (n: number) => `10000000-0000-4000-8000-${String(n).padStart(12, '0')}`
const source = u(1), target = u(2), other = u(3), warehouse = u(9), lot1 = u(10), lot2 = u(11), lot3 = u(12)
const group1 = u(21), group2 = u(22), group3 = u(23), group4 = u(24)
const payload = () => ({ source_product_id: source, target_product_id: target, location_id: warehouse, qty_pcs: 4, physical_at: '2026-10-20T00:00:00Z', reason: 'Barang tercampur laundry' })
const queryValue = async (sql: string) => { const row = (await db.query(`select ${sql}`))[0]; return row[Object.keys(row)[0]] }
const preview = (p: unknown = payload()) => queryValue(`cp7_sku_conversion.preview_v1(${jsonArg(p)})`)
const post = async (request = u(100), p: Record<string, unknown> = payload()) => {
  const v = await preview(p)
  return queryValue(`cp7_sku_conversion.action_v1('POST',${jsonArg({ ...p, expected_version: v.source_revision })},'${request}')`)
}
const pair = async (a: string, b: string | null, request: string) => queryValue(`cp7_sku_conversion.save_pair_v1(${jsonArg({ source_group_id: a, target_group_id: b, reason: 'Padanan owner', expected_version: await queryValue('cp7_sku_conversion.pair_revision_v1()') })},'${request}')`)
const snapshot = () => queryValue(`jsonb_build_object('movements',(select jsonb_agg(to_jsonb(x)order by id)from erp.fg_stock_movements x),'hpp',(select jsonb_agg(to_jsonb(x)order by lot_id)from erp.current_hpp x),'journals',(select jsonb_agg(to_jsonb(x)order by id)from erp.test_journals x))`)
const pairSnapshot = () => queryValue(`jsonb_build_object('pairs',(select jsonb_agg(to_jsonb(p)order by left_id,right_id)from cp7_sku_conversion.pairs_v1 p),'events',(select jsonb_agg(to_jsonb(e)order by request_id)from cp7_sku_conversion.pair_events_v1 e))`)
const nativeFunction = (path: string, declaration: string) => {
  const sql = readFileSync(path, 'utf8'), start = sql.indexOf(declaration), end = sql.indexOf('$function$;', start)
  if (start < 0 || end < 0) throw new Error(`Pinned Native function not found: ${declaration}`)
  return sql.slice(start, end + '$function$;'.length)
}

beforeEach(async () => {
  db = await openRuntime()
  await db.execute(`
    create schema erp;
    create table erp.test_actor(id uuid,role_name text,permissions text[]);insert into erp.test_actor values('${u(90)}','OWNER',array['master.product.view','master.product.manage','warehouse.brand_conversion.view','warehouse.brand_conversion.post','warehouse.brand_conversion.reverse','finance.hpp.view']);
    create function erp.current_app_user_id()returns uuid language sql stable as $$select id from erp.test_actor$$;
    create function erp.current_app_role()returns text language sql stable as $$select role_name from erp.test_actor$$;
    create function erp.has_permission(p text)returns boolean language sql stable as $$select p=any(permissions)from erp.test_actor$$;
    create function erp.require_permission(p text)returns void language plpgsql as $$begin if not erp.has_permission(p)then raise exception '42501 ACCESS_DENIED';end if;end$$;
    create function erp.require_owner_admin()returns void language plpgsql as $$begin if erp.current_app_role()not in('OWNER','ADMIN')then raise exception 'OWNER_ADMIN_REQUIRED';end if;end$$;
    create function erp.require_internal()returns void language plpgsql as $$begin if erp.current_app_user_id()is null then raise exception 'AUTH_REQUIRED';end if;end$$;
    create function erp.pocket_period_lock_v1()returns void language sql as $$select$$;
    create function erp.bc_text_v1(p jsonb,k text,required boolean,max_length int)returns text language plpgsql as $$begin if required and nullif(btrim(p->>k),'')is null or length(p->>k)>max_length then raise exception 'TEXT_REQUIRED';end if;return p->>k;end$$;
    create function erp.bd_qty_v1(p jsonb,k text)returns int language plpgsql as $$begin if p#>>'{}'!~'^[1-9][0-9]{0,8}$'then raise exception 'QTY_INVALID';end if;return(p#>>'{}')::int;end$$;
    create function erp.bd_at_v1(p text,k text)returns timestamptz language plpgsql as $$begin if p::timestamptz>statement_timestamp()then raise exception 'FUTURE';end if;return p::timestamptz;end$$;
    create table erp.brands(id uuid primary key,brand_name text);insert into erp.brands values('${u(31)}','Vivo'),('${u(32)}','Widie');
    create table erp.product_models(id uuid primary key,model_name text);insert into erp.product_models values('${u(41)}','Classic'),('${u(42)}','Slim');
    create table erp.sizes(id uuid primary key,size_code text,sort_order int);insert into erp.sizes values('${u(51)}','31',1),('${u(52)}','34',2);
    create table erp.products(id uuid primary key,identity_root_id uuid,sku text,product_name text,brand_id uuid,model_id uuid,size_id uuid,is_active boolean,effective_from timestamptz,effective_to timestamptz);
    insert into erp.products values('${source}','${source}','1002','Vivo 1002 31','${u(31)}','${u(41)}','${u(51)}',true,'2026-01-01',null),('${target}','${target}','1001','Widie 1001 34','${u(32)}','${u(42)}','${u(52)}',true,'2026-01-01',null),('${other}','${other}','1003','Vivo 1003 31','${u(31)}','${u(41)}','${u(51)}',true,'2026-01-01',null),('${u(4)}','${u(4)}','1004','Vivo 1004 31','${u(31)}','${u(41)}','${u(51)}',true,'2026-01-01',null);
    create table erp.bf_skus_v1(id uuid primary key,sku text,brand_id uuid,model_id uuid,revision bigint);insert into erp.bf_skus_v1 values('${group1}','1002','${u(31)}','${u(41)}',1),('${group2}','1001','${u(32)}','${u(42)}',1),('${group3}','1003','${u(31)}','${u(41)}',1),('${group4}','1004','${u(31)}','${u(41)}',1);
    create table erp.bf_sku_versions_v1(id uuid primary key,sku_id uuid,revision bigint,effective_from timestamptz,effective_to timestamptz);
    insert into erp.bf_sku_versions_v1 select id,id,1,'2026-01-01'::timestamptz,null from erp.bf_skus_v1;
    create table erp.bf_sku_members_v1(version_id uuid,product_root uuid);insert into erp.bf_sku_members_v1 values('${group1}','${source}'),('${group2}','${target}'),('${group3}','${other}'),('${group4}','${u(4)}');
    create table erp.locations(id uuid primary key,location_name text,location_type text,is_active boolean);insert into erp.locations values('${warehouse}','Gudang A','FG_WAREHOUSE',true);
    create table erp.fg_lots(id uuid primary key,product_id uuid,lot_number text,produced_at timestamptz,lot_origin text);
    insert into erp.fg_lots values('${lot1}','${source}','Lot pertama','2026-10-01','OPENING'),('${lot2}','${source}','Lot kedua','2026-10-02','PRODUCTION'),('${lot3}','${target}','Lot tujuan','2026-10-01','PRODUCTION');
    create table erp.current_hpp(lot_id uuid primary key,hpp_per_pcs numeric);insert into erp.current_hpp values('${lot1}',10.01),('${lot2}',20.02),('${lot3}',30.03);
    create view erp.v_current_hpp as select *from erp.current_hpp;
    create table erp.fg_stock_movements(id uuid primary key default gen_random_uuid(),lot_id uuid,product_id uuid,location_id uuid,quality_grade text,movement_type text,qty_signed int,physical_at timestamptz,reversal_of_id uuid,source_id uuid);
    insert into erp.fg_stock_movements(lot_id,product_id,location_id,quality_grade,movement_type,qty_signed,physical_at)values('${lot1}','${source}','${warehouse}','GRADE_A','OPENING',3,'2026-10-01'),('${lot2}','${source}','${warehouse}','GRADE_A','RECEIPT',7,'2026-10-02'),('${lot3}','${target}','${warehouse}','GRADE_A','RECEIPT',4,'2026-10-01'),('${lot1}','${source}','${warehouse}','GRADE_A','SALE_RESERVE',-1,'2026-10-03');
    create function erp.be_source_revision_v1(p_lot uuid,p_location uuid)returns text language sql stable as $$select md5(jsonb_build_object('movements',(select jsonb_agg(to_jsonb(m)order by id)from erp.fg_stock_movements m where lot_id=p_lot and location_id=p_location),'hpp',(select hpp_per_pcs from erp.current_hpp where lot_id=p_lot))::text)$$;
    create table erp.product_conversions(id uuid primary key,source_lot_id uuid,destination_lot_id uuid,qty_pcs int,status text,expected_returns jsonb);
    create table erp.test_journals(id uuid primary key,debit numeric,credit numeric);
    create table erp.test_downstream(lot_id uuid primary key);
    create table erp.test_requests(namespace text,id uuid,hash text,response jsonb,primary key(namespace,id));
    create function erp._request_hash(p jsonb)returns text language sql as $$select md5(p::text)$$;
    create function erp._idempotency_begin(p_namespace text,p_request uuid,p_hash text)returns jsonb language plpgsql as $$declare r erp.test_requests%rowtype;begin select *into r from erp.test_requests where namespace=p_namespace and id=p_request;if found and r.hash<>p_hash then raise exception 'REQUEST_REUSED';end if;perform set_config('test.request_hash.r'||replace(p_request::text,'-',''),p_hash,true);return r.response;end$$;
    create function erp._idempotency_complete(p_namespace text,p_request uuid,p_response jsonb)returns jsonb language plpgsql as $$begin insert into erp.test_requests values(p_namespace,p_request,current_setting('test.request_hash.r'||replace(p_request::text,'-','')),p_response);return p_response;end$$;
    create function erp.get_sku_workspace_v1(p jsonb)returns jsonb language sql as $$select jsonb_build_object('groups','[]'::jsonb)$$;
    create function erp.save_sku_action_v1(a text,p jsonb,r uuid)returns jsonb language sql as $$select jsonb_build_object('legacy',true)$$;
    create function erp.get_product_conversion_workspace_v1(p jsonb)returns jsonb language sql as $$select jsonb_build_object('lots','[]'::jsonb,'targets','[]'::jsonb,'documents','[]'::jsonb,'page',1,'target_page',1,'page_size',25,'total',0,'targets_total',0,'documents_total',0,'document_page',1)$$;
  `)
  // The original required-key validator rejects JSON null, unlike the former
  // key-existence-only local double. Use both exact Native validators so a
  // nullable endpoint cannot pass locally and fail on the real stack again.
  await db.execute(nativeFunction('supabase/migrations/20260901023000_erp_v2_6_14_attendance_hpp_sewing_terminal_foundation.sql', 'create or replace function erp._cp3_assert_closed_json_object('))
  await db.execute(nativeFunction('scripts/cp6_bd_objects_policy.sql', 'CREATE OR REPLACE FUNCTION erp.bd_uuid_v1('))
  await db.execute(readFileSync('scripts/cp7_sku_pair_conversion/pairs.sql', 'utf8') + '\n' + readFileSync('scripts/cp7_sku_pair_conversion/conversion.sql', 'utf8'))
  const beSource = readFileSync('scripts/cp6_be_objects_conversion.sql', 'utf8')
  const start = beSource.indexOf('CREATE OR REPLACE FUNCTION erp.be_conversion_preview_v1(')
  const end = beSource.indexOf('$function$;', start) + '$function$;'.length
  const nativePreview = beSource.slice(start, end).replace('if t.model_id is distinct from s.model_id or t.size_id is distinct from s.size_id then', "if not cp7_sku_conversion.manual_allocation_v1(l.id,t.id,(p_payload->>'location_id')::uuid,(p_payload->>'qty_pcs')::int,(p_payload->>'physical_at')::timestamptz) and (t.model_id is distinct from s.model_id or t.size_id is distinct from s.size_id) then")
  await db.execute(nativePreview + `
    create function erp.reverse_product_conversion(p_id uuid,p_reason text)returns void language plpgsql as $$declare h erp.product_conversions%rowtype;m record;begin
      perform cp7_sku_conversion.assert_group_reverse_v1(p_id);select *into strict h from erp.product_conversions where id=p_id;
      if exists(select 1 from erp.test_downstream where lot_id=h.destination_lot_id)then raise exception 'DOWNSTREAM_ACTIVE';end if;
      if h.status='REVERSED'then return;end if;
      for m in select *from erp.fg_stock_movements where source_id=p_id and movement_type in('REBRAND_OUT','REBRAND_IN')loop
        insert into erp.fg_stock_movements(lot_id,product_id,location_id,quality_grade,movement_type,qty_signed,physical_at,reversal_of_id,source_id)
        values(m.lot_id,m.product_id,m.location_id,m.quality_grade,'REVERSAL',-m.qty_signed,m.physical_at,m.id,p_id);end loop;
      update erp.product_conversions set status='REVERSED'where id=p_id;end$$;
    create function erp.save_product_conversion_action_v1(a text,p jsonb,p_id uuid)returns jsonb language plpgsql as $$declare v jsonb;dest uuid:=gen_random_uuid();source_id uuid;qty int;unit_cost numeric;before_json jsonb;begin
      perform erp.require_permission(case when a='REVERSE'then 'warehouse.brand_conversion.reverse'else 'warehouse.brand_conversion.post'end);
      if a='REVERSE'then perform erp.reverse_product_conversion((p->>'conversion_id')::uuid,p->>'reason');return jsonb_build_object('conversion_id',p->'conversion_id','status','REVERSED');end if;
      v:=erp.be_conversion_preview_v1(p);source_id:=(v->>'source_lot_id')::uuid;qty:=(v->>'qty_pcs')::int;
      select hpp_per_pcs into unit_cost from erp.current_hpp where lot_id=source_id;
      insert into erp.fg_lots values(dest,(v->>'target_product_id')::uuid,'Converted '||p_id::text,(v->>'physical_at')::timestamptz,'CONVERSION');
      insert into erp.current_hpp values(dest,unit_cost);
      insert into erp.product_conversions values(p_id,source_id,dest,qty,'POSTED',p->'expected_returns');
      insert into erp.fg_stock_movements(lot_id,product_id,location_id,quality_grade,movement_type,qty_signed,physical_at,source_id)
      values(source_id,(v->>'source_product_id')::uuid,(v->>'location_id')::uuid,'GRADE_A','REBRAND_OUT',-qty,(v->>'physical_at')::timestamptz,p_id),
      (dest,(v->>'target_product_id')::uuid,(v->>'location_id')::uuid,'GRADE_A','REBRAND_IN',qty,(v->>'physical_at')::timestamptz,p_id);
      insert into erp.test_journals values(p_id,round(qty*unit_cost,2),round(qty*unit_cost,2));
      return v||jsonb_build_object('conversion_id',p_id,'destination_lot_id',dest,'status','POSTED');end$$;
  `)
})
afterEach(async () => { await db?.close() })

test('commercial groups have one bidirectional pair, reversed input is canonical, replacement removes both old partners and has no ledger effects', async () => {
  const before = await snapshot()
  await pair(group1, group2, u(101)); expect(await queryValue(`cp7_sku_conversion.partner_v1('${group2}')`)).toBe(group1)
  await pair(group2, group1, u(102)); expect(await queryValue('count(*)from cp7_sku_conversion.pairs_v1')).toBe(1)
  await pair(group3, group4, u(103)); await pair(group1, group3, u(104))
  expect(await queryValue(`cp7_sku_conversion.partner_v1('${group2}')`)).toBe(null)
  expect(await queryValue(`cp7_sku_conversion.partner_v1('${group4}')`)).toBe(null)
  expect(await queryValue(`cp7_sku_conversion.partner_v1('${group3}')`)).toBe(group1)
  await pair(group3, null, u(105)); expect(await queryValue('count(*)from cp7_sku_conversion.pairs_v1')).toBe(0)
  expect(await snapshot()).toEqual(before)
})
test('pair replay is exact, stale master state and crossing duplicate endpoints are refused, and authorization is checked before replay', async () => {
  const version = await queryValue('cp7_sku_conversion.pair_revision_v1()'), p = { source_group_id: group1, target_group_id: group2, expected_version: version, reason: 'Padanan owner' }
  const one = await queryValue(`cp7_sku_conversion.save_pair_v1(${jsonArg(p)},'${u(110)}')`)
  expect(await queryValue(`cp7_sku_conversion.save_pair_v1(${jsonArg(p)},'${u(110)}')`)).toEqual({ ...one, replayed: true })
  await expect(queryValue(`cp7_sku_conversion.save_pair_v1(${jsonArg({ ...p, target_group_id: group3 })},'${u(111)}')`)).rejects.toThrow('STALE_VERSION')
  await expect(db.execute(`insert into cp7_sku_conversion.pairs_v1 values('${group2}','${group3}')`)).rejects.toThrow('ALREADY_LINKED')
  await db.execute("update erp.test_actor set permissions=array['master.product.view']")
  await expect(queryValue(`cp7_sku_conversion.save_pair_v1(${jsonArg(p)},'${u(110)}')`)).rejects.toThrow('ACCESS_DENIED')
})
test('explicit nullable target deletes from either endpoint with the original Native validators; missing, malformed, stale and reused requests refuse without effects', async () => {
  const before = await snapshot()
  for (const [index, endpoint] of [group1, group2].entries()) {
    await pair(group1, group2, u(210 + index * 3))
    const request = u(211 + index * 3), deletion = { source_group_id: endpoint, target_group_id: null, reason: 'Hapus padanan owner', expected_version: await queryValue('cp7_sku_conversion.pair_revision_v1()') }
    const saved = await queryValue(`cp7_sku_conversion.save_pair_v1(${jsonArg(deletion)},'${request}')`)
    expect(saved.target_group_id).toBe(null); expect(saved.removed).toHaveLength(1)
    expect(await queryValue(`cp7_sku_conversion.partner_v1('${group1}')`)).toBe(null)
    expect(await queryValue(`cp7_sku_conversion.partner_v1('${group2}')`)).toBe(null)
    const exact = await pairSnapshot()
    expect(await queryValue(`cp7_sku_conversion.save_pair_v1(${jsonArg(deletion)},'${request}')`)).toEqual({ ...saved, replayed: true })
    expect(await pairSnapshot()).toEqual(exact)
    await expect(queryValue(`cp7_sku_conversion.save_pair_v1(${jsonArg({ ...deletion, target_group_id: group3 })},'${request}')`)).rejects.toThrow('CP7_SKU_PAIR_REQUEST_REUSED')
    expect(await pairSnapshot()).toEqual(exact)
  }
  await pair(group1, group2, u(220))
  const current = { source_group_id: group1, target_group_id: null, reason: 'Hapus dengan pemeriksaan', expected_version: await queryValue('cp7_sku_conversion.pair_revision_v1()') }
  const { target_group_id: _target, ...missing } = current
  const invalid: [unknown, string][] = [[missing, 'CP7_SKU_PAIR_TARGET_KEY_REQUIRED'],
    ...['', 7, {}, [], 'null'].map(target_group_id => [{ ...current, target_group_id }, 'BD_FIELD_INVALID'] as [unknown, string]),
    [{ ...current, expected_version: null }, 'requires non-null key expected_version'],
    [{ ...current, reason: null }, 'requires non-null key reason'],
    [{ ...current, extra: true }, 'contains unexpected key extra'],
    [{ ...current, expected_version: 'stale-review' }, 'STALE_VERSION']]
  const exact = await pairSnapshot()
  for (const [index, [bad, message]] of invalid.entries()) {
    await expect(queryValue(`cp7_sku_conversion.save_pair_v1(${jsonArg(bad)},'${u(230 + index)}')`)).rejects.toThrow(message)
    expect(await pairSnapshot()).toEqual(exact); expect(await snapshot()).toEqual(before)
  }
})
test('FIFO preview separates physical/available/reserved and carries each lot cost into a different model and size', async () => {
  const before = await snapshot(), v = await preview()
  expect(v.source_stock).toEqual({ physical: 10, reserved: 1, available: 9 }); expect(v.target_stock).toEqual({ physical: 4, reserved: 0, available: 4 })
  expect(v.source_after).toEqual({ physical: 6, reserved: 1, available: 5 }); expect(v.target_after.physical).toBe(8)
  expect(v.allocations.map((x: { source_lot_id: string; qty_pcs: number; source_value: string }) => [x.source_lot_id, x.qty_pcs, x.source_value])).toEqual([[lot1, 2, '20.02'], [lot2, 2, '40.04']])
  expect(v.cost.source_value).toBe('60.06'); expect(await snapshot()).toEqual(before)
  const result = await post(); expect(result.conversion_ids).toHaveLength(2)
  expect(await queryValue(`cp7_sku_conversion.stock_v1('${source}','${warehouse}')`)).toEqual(v.source_after)
  expect(await queryValue(`cp7_sku_conversion.stock_v1('${target}','${warehouse}')`)).toEqual(v.target_after)
  expect(await queryValue('sum(debit)::text from erp.test_journals')).toBe('60.06')
})
test('only the exact private allocation permits cross-model/size; a direct legacy call cannot opt in using arbitrary data', async () => {
  const p = { source_lot_id: lot1, target_product_id: target, location_id: warehouse, qty_pcs: 1, physical_at: payload().physical_at, reason: 'manual', expected_version: await queryValue(`erp.be_source_revision_v1('${lot1}','${warehouse}')`) }
  await expect(queryValue(`erp.be_conversion_preview_v1(${jsonArg(p)})`)).rejects.toThrow('DIMENSION_MISMATCH')
  await expect(preview({ ...payload(), source_product_id: target, target_product_id: target })).rejects.toThrow('SAME_PRODUCT')
  await expect(preview({ ...payload(), qty_pcs: 10 })).rejects.toThrow('INSUFFICIENT')
  expect(await queryValue('count(*)from erp.product_conversions')).toBe(0)
})
test('changed reservations, target stock or source HPP invalidate the reviewed fingerprint before any write', async () => {
  for (const sql of ["update erp.current_hpp set hpp_per_pcs=hpp_per_pcs+1 where lot_id='" + lot2 + "'", "insert into erp.fg_stock_movements(lot_id,product_id,location_id,quality_grade,movement_type,qty_signed,physical_at)values('" + lot3 + "','" + target + "','" + warehouse + "','GRADE_A','SALE_RESERVE',-1,'2026-10-19')", "update erp.fg_stock_movements set movement_type='SALE'where product_id='" + source + "'and movement_type='SALE_RESERVE'"]) {
    const frozen = { ...payload(), expected_version: (await preview()).source_revision }
    await db.execute(sql)
    await expect(queryValue(`cp7_sku_conversion.action_v1('POST',${jsonArg(frozen)},'${u(120)}')`)).rejects.toThrow('STALE_VERSION')
    expect(await queryValue('count(*)from erp.product_conversions')).toBe(0)
  }
})
test('one request replays without duplicate movements and manual conversion back uses its current source cost', async () => {
  const v = await preview(), frozen = { ...payload(), expected_version: v.source_revision }
  const first = await queryValue(`cp7_sku_conversion.action_v1('POST',${jsonArg(frozen)},'${u(125)}')`), before = await snapshot()
  expect(await queryValue(`cp7_sku_conversion.action_v1('POST',${jsonArg(frozen)},'${u(125)}')`)).toEqual(first)
  expect(await snapshot()).toEqual(before)
  const back = await post(u(126), { ...payload(), source_product_id: target, target_product_id: source, qty_pcs: 1, physical_at: '2026-10-21T00:00:00Z' })
  expect(back.cost.source_value).toBe('30.03') // existing target lot is FIFO first
})
test('a downstream use blocks the whole group inverse with zero partial reversal; after release all allocations reverse atomically', async () => {
  const result = await post(), second = result.destination_lot_ids[0]
  await expect(queryValue(`erp.reverse_product_conversion('${result.conversion_ids[0]}','wrong entry')`)).rejects.toThrow('GROUP_REVERSE_REQUIRED')
  await db.execute(`insert into erp.test_downstream values('${second}')`)
  const before = await snapshot(), p = { conversion_id: u(100), reason: 'Pembatalan fisik' }
  await expect(queryValue(`cp7_sku_conversion.action_v1('REVERSE',${jsonArg(p)},'${u(130)}')`)).rejects.toThrow('DOWNSTREAM_ACTIVE')
  expect(await snapshot()).toEqual(before)
  await db.execute('delete from erp.test_downstream')
  await queryValue(`cp7_sku_conversion.action_v1('REVERSE',${jsonArg(p)},'${u(130)}')`)
  expect(await queryValue("count(*)from erp.product_conversions where status='REVERSED'")).toBe(2)
  expect(await queryValue(`cp7_sku_conversion.stock_v1('${source}','${warehouse}')`)).toEqual({ physical: 10, reserved: 1, available: 9 })
})
test('all active targets remain available beyond equivalents and sizes are explicit, with source and target latest stock', async () => {
  await pair(group1, group2, u(140))
  const v = await queryValue(`cp7_sku_conversion.workspace_v1(${jsonArg({ source_product_id: source, selection: { source_product_id: source, target_product_id: target, location_id: warehouse } })})`)
  expect(v.targets[0]).toMatchObject({ id: target, recommended: true, brand_name: 'Widie', size: '34' })
  expect(v.targets.some((t: { id: string; recommended: boolean }) => t.id === other && !t.recommended)).toBe(true)
  expect(v.selection.target_stock).toEqual({ physical: 4, reserved: 0, available: 4 })
  expect(v.sources.find((s: { product_id: string }) => s.product_id === source).stock).toEqual({ physical: 10, reserved: 1, available: 9 })
})
test('master partner search is group based, paged independently and does not require HPP access', async () => {
  await db.execute("update erp.test_actor set permissions=array['master.product.view','master.product.manage']")
  const noSelection = await queryValue(`cp7_sku_conversion.sku_workspace_v1('{}')`)
  expect(noSelection.pairing.options).toEqual([])
  const w = await queryValue(`cp7_sku_conversion.sku_workspace_v1(${jsonArg({ pair_source_id: group1, pair_query: 'Widie', pair_page: 1 })})`)
  expect(w.pairing.total).toBe(1); expect(w.pairing.can_edit).toBe(true); expect(w.pairing.options[0]).toMatchObject({ id: group2, sku: '1001', brand_name: 'Widie' })
  await pair(group1, group2, u(145))
  const reverseSide = await queryValue(`cp7_sku_conversion.sku_workspace_v1(${jsonArg({ pair_source_id: group2 })})`)
  expect(reverseSide.pairing.current.id).toBe(group1)
})
test('authorization precedes private group dispatch and malformed UUID handling', async () => {
  const before = await snapshot()
  await db.execute("update erp.test_actor set permissions=array[]::text[]")
  for (const action of ["'REVERSE'", 'NULL']) {
    await expect(queryValue(`cp7_sku_conversion.action_v1(${action},${jsonArg({ conversion_id: 'invalid-uuid', reason: 'Unauthorized request' })},'${u(149)}')`)).rejects.toThrow('ACCESS_DENIED')
  }
  expect(await snapshot()).toEqual(before)
})
test('NULL, blank or unknown commands cannot reverse an existing conversion group or change any ledger/status', async () => {
  await post(); const before = await snapshot(), statuses = await db.query('select id,status from erp.product_conversions order by id')
  for (const action of ['NULL', "''", "'UNKNOWN_ACTION'"]) await expect(queryValue(`cp7_sku_conversion.action_v1(${action},${jsonArg({ conversion_id: u(100), reason: 'Must not become reversal' })},'${u(151)}')`)).rejects.toThrow('BE_ACTION_UNKNOWN')
  expect(await snapshot()).toEqual(before); expect(await db.query('select id,status from erp.product_conversions order by id')).toEqual(statuses)
})
test('a revoked grant after the idempotency boundary refuses even an already completed UUID reply', async () => {
  const p = { ...payload(), expected_version: (await preview()).source_revision }
  await queryValue(`cp7_sku_conversion.action_v1('POST',${jsonArg(p)},'${u(155)}')`)
  const before = await snapshot()
  // Directed boundary injection in the explicitly declared Native double.
  // It is not a real two-session/advisory-lock revocation race.
  await db.execute(`create or replace function erp._idempotency_begin(p_namespace text,p_request uuid,p_hash text)returns jsonb language plpgsql as $$declare r erp.test_requests%rowtype;begin
    select *into r from erp.test_requests where namespace=p_namespace and id=p_request;
    update erp.test_actor set permissions=array_remove(permissions,'warehouse.brand_conversion.post');
    return r.response;end$$`)
  await expect(queryValue(`cp7_sku_conversion.action_v1('POST',${jsonArg(p)},'${u(155)}')`)).rejects.toThrow('ACCESS_DENIED')
  expect(await snapshot()).toEqual(before)
})
test('the original all22 catalog query exposes exactly six ERP parent RI triggers; narrow fix admits those and rejects a real rogue ERP trigger', async () => {
  const queries = JSON.parse(execFileSync('python3', ['-c', `import ast,json,pathlib
m=ast.parse(pathlib.Path('scripts/cp7_ow04_restore_bundle.py').read_text());ns=next(ast.literal_eval(n.value)for n in m.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='NAMESPACE'for t in n.targets));d=next(n.value for n in m.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='QUERIES'for t in n.targets));out={}
for k,v in zip(d.keys,d.values):
 if ast.literal_eval(k)in('triggers','constraints'):out[ast.literal_eval(k)]=eval(compile(ast.Expression(v),'<catalog-query>','eval'),{'NAMESPACE':ns})
print(json.dumps(out))`], { encoding: 'utf8' }))
  await db.execute("set search_path=''")
  const constraints = Object.fromEntries((await db.query(queries.constraints)).map((r: Record<string, unknown>) => Object.values(r)))
  const triggers = Object.fromEntries((await db.query(queries.triggers)).map((r: Record<string, unknown>) => Object.values(r)))
  const parents = Object.keys(triggers).filter(key => key.startsWith('erp.'))
  expect(parents).toHaveLength(6)
  await db.execute(`create function erp.sku_rogue_test()returns trigger language plpgsql as $$begin return new;end$$;create trigger sku_rogue_test before update on erp.bf_skus_v1 for each row execute function erp.sku_rogue_test();`)
  const rogue = Object.fromEntries((await db.query(queries.triggers)).map((r: Record<string, unknown>) => Object.values(r)))
  const observed = JSON.parse(execFileSync('python3', ['-c', `import ast,importlib.util,json,pathlib,subprocess,sys
root=pathlib.Path('scripts/cp7_sku_pair_conversion');s=importlib.util.spec_from_file_location('ri',root/'ri_catalog.py');ri=importlib.util.module_from_spec(s);s.loader.exec_module(ri)
def transition(source):
 tree=ast.parse(source);fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='transition');ns={'SCHEMA':'cp7_sku_conversion','FUNCTIONS':functions,'ri_catalog':ri};exec(compile(ast.Module(body=[fn],type_ignores=[]),'<transition>','exec'),ns);return ns['transition']
data=json.load(sys.stdin);tree=ast.parse((root/'composition.py').read_text());expr=next(n.value for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='FUNCTIONS'for t in n.targets));functions=eval(compile(ast.Expression(expr),'<functions>','eval'),{'SCHEMA':'cp7_sku_conversion'})
names=('schemas','functions','relations','columns','constraints','indexes','triggers','types','type_implementation','policies',*[f'other_{i}'for i in range(12)]);before={k:{}for k in names};before['constraints']={k:v for k,v in data['constraints'].items()if not k.startswith('cp7_sku_conversion.')};after={k:dict(v)for k,v in before.items()};after['constraints']=data['constraints'];after['triggers']=data['triggers'];after['functions']={k:['new']for k in functions}
old=(root/'BEFORE_RI_COMPOSITION.py.txt').read_text();assert __import__('hashlib').sha256(old.encode()).hexdigest()=='2ae89e8aadf79f135d82b474ef738dec7fd6267479caaa13748f5e31f232a06a'
try:transition(old)(before,after,{})
except ValueError as e:old_failure=str(e);assert 'UNDECLARED_CATALOG_DELTA:triggers:erp.'in old_failure,old_failure
else:raise AssertionError('ORIGINAL_REJECTION_NOT_REPRODUCED')
transition((root/'composition.py').read_text())(before,after,{})
after['triggers']=data['rogue']
try:transition((root/'composition.py').read_text())(before,after,{})
except ValueError as e:rogue_failure=str(e);assert 'sku_rogue_test'in rogue_failure,rogue_failure
else:raise AssertionError('ROGUE_ERP_TRIGGER_ACCEPTED')
print(json.dumps({'old_failure':old_failure,'exact_RI_after_fix':True,'rogue_failure':rogue_failure,'parent_RI_count':len(ri.expected_parent_triggers(data['constraints']))}))`], { encoding: 'utf8', input: JSON.stringify({ constraints, triggers, rogue }) }))
  expect(observed.exact_RI_after_fix).toBe(true); expect(observed.parent_RI_count).toBe(6); expect(observed.rogue_failure).toContain('sku_rogue_test')
})
