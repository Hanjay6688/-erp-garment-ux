// Exact observer bodies on typed empty tables and four declared read models.
// This does not execute Native business, constraints, RLS, Auth or an ERP case.
import assert from 'node:assert/strict';
import {readFile, writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const {PGlite} = await import(process.env.CP7_PGLITE_MODULE);
const raw = await readFile(process.env.CP7_GRAPH_INPUT), input = JSON.parse(raw);
assert.equal(input.classification, 'MODELED_AUTOMATIC_GLOBAL_OBSERVATION_NOT_ERP');
const db = new PGlite(), results = [];
const id = n => '76000000-0000-4000-8000-' + String(n).padStart(12, '0');
const names = ['product', 'target', 'lot', 'rootLot', 'group', 'sale', 'saleItem', 'allocation', 'rework', 'po', 'request'];
const fixture = n => Object.fromEntries(names.map((key, i) => [key, id(n + i + 1)]));
const relevant = fixture(0), outside = fixture(100), isolated = fixture(200);
const location = id(990), account = id(991);
const quote = s => '"' + s.replaceAll('"', '""') + '"';
const scalar = async (sql, params = []) => Object.values((await db.query(sql, params)).rows[0])[0];
const scope = () => scalar('select cp7_global_nonpo_native_graph.scope_v1($1::uuid[])', [[relevant.sale]]);
const oldScope = () => scalar('select cp7_global_nonpo_native_graph.parent_money_scope_model($1::uuid[])', [[relevant.sale]]);
const capture = (selected, outsideOnly = true) => scalar('select cp7_global_nonpo_native_graph.capture_v1($1::jsonb,$2)', [JSON.stringify(selected), outsideOnly]);
const oldCapture = selected => scalar('select cp7_global_nonpo_native_graph.parent_money_capture_model($1::jsonb,true)', [JSON.stringify(selected)]);
const keys = part => new Set(part.identity_keys.map(row => row.kind + ':' + row.id));
const passed = label => results.push({label, result: 'PASS'});
async function insert(table, values) {
  const columns = input.columns[table]; assert(columns, table);
  const row = Object.fromEntries(columns.map(([name, , type]) => [name,
    type === 'uuid' || type.endsWith('[]') ? null : type === 'date' ? '2026-01-02' :
    type === 'timestamp with time zone' ? '2026-01-02T03:04:05Z' :
    type === 'timestamp without time zone' ? '2026-01-02 03:04:05' : type === 'xid8' ? '1' :
    /^(numeric|integer|smallint|bigint)/.test(type) ? 1 : type === 'boolean' ? false : type === 'jsonb' ? {} : 'M']));
  for (const [key, value] of Object.entries(values)) { assert(Object.hasOwn(row, key), table + '.' + key); row[key] = value; }
  await db.query('insert into ' + table + '(' + Object.keys(row).map(quote).join(',') + ')values(' +
    Object.keys(row).map((_, index) => '$' + (index + 1)).join(',') + ')', Object.values(row));
}
let engine, stage = 'SETUP';
try {
  engine = await scalar('select version()'); assert.match(engine, /^PostgreSQL 17\./);
  await db.exec('create role anon;create role authenticated;create role service_role;' +
    'create schema erp;create schema cp7_sku_conversion;create schema cp7_credit;create schema cp7_global_nonpo_native_graph;');
  for (const [table, columns] of Object.entries(input.columns)) {
    await db.exec('create table ' + table + '(' + columns.map(([name, , type]) => quote(name) + ' ' + type).join(',') + ')');
    const actual = await scalar('select jsonb_object_agg(attname,format_type(atttypid,atttypmod))from pg_attribute where attrelid=$1::regclass and attnum>0 and not attisdropped', [table]);
    assert.deepEqual(actual, Object.fromEntries(columns.map(([name, , type]) => [name, type])));
  }
  assert.equal(Object.keys(input.columns).length, 82);
  assert.equal(Object.values(input.columns).reduce((total, columns) => total + columns.length, 0), 835);
  await db.exec(`create function cp7_credit.consumer_dependency_graph_v1(uuid)returns jsonb language sql stable as $$select jsonb_build_object('sale_ids',jsonb_build_array($1))$$;
create function cp7_credit.source_hpp_lot_ids_v1(uuid)returns uuid[]language sql stable as $$select array_agg(a.lot_id order by a.lot_id)from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=$1$$;
create function cp7_credit.initial_hpp_account_facts_v1()returns jsonb language sql stable as $$select '{"model_provider":true}'::jsonb$$;
create function cp7_credit.pg_jsonb_sha256(jsonb)returns text language sql immutable as $$select encode(sha256(convert_to($1::text,'UTF8')),'hex')$$;`);
  for (const sql of Object.values(input.helpers)) await db.exec(sql);
  await db.exec(input.parent_helpers.capture.replaceAll('cp7_global_nonpo_native_graph.capture_v1', 'cp7_global_nonpo_native_graph.parent_money_capture_model'));
  await db.exec(input.parent_helpers.scope.replaceAll('cp7_global_nonpo_native_graph.scope_v1', 'cp7_global_nonpo_native_graph.parent_money_scope_model'));
  passed('All derived observer statements compile against exact 82 table and 835 column types');
  stage = 'FIXTURE';
  for (const x of [relevant, outside, isolated]) {
    await insert('erp.fg_lots', {id: x.lot, product_id: x.product, po_id: null, lot_origin: 'OPENING'});
    await insert('erp.fg_lots', {id: x.rootLot, product_id: x.product, po_id: x.po, lot_origin: 'PRODUCTION'});
    await insert('erp.sales_items', {id: x.saleItem, sale_id: x.sale, product_id: x.product});
    await insert('erp.sale_stock_allocations', {id: x.allocation, sale_item_id: x.saleItem, lot_id: x.lot});
    // Identical shared warehouse/account values cannot connect these three
    // components. Only the source identities below may expand their scope.
    await insert('erp.journal_lines', {id: id(500 + [relevant, outside, isolated].indexOf(x)), journal_entry_id: id(600 + [relevant, outside, isolated].indexOf(x)),
      account_id: account, product_id: null, po_id: null});
    await insert('cp7_sku_conversion.automatic_context_v5', {
      backend_pid: 77, transaction_id: 88, native_request_id: x.request, rework_id: x.rework,
      conversion_id: x.group, phase: 'POST', source_lot_id: x.rootLot, source_po_id: x.po,
      source_product_id: x.product, target_product_id: x.target, location_id: location, qty: 2,
      physical_at: '2026-01-02T03:04:05Z', origin_kind: 'REDYE',
      rework_proof: {status: 'COMPLETED', zero: 0}, target_proof: {target: x.target, value: 0},
    });
    for (const phase of ['POST', 'REVERSE']) await insert('cp7_sku_conversion.automatic_admissions_v5', {
      conversion_id: x.group, phase, rework_id: x.rework,
      context_proof: {backend_pid: 77, phase, zero: 0, native_request_id: x.request},
      conversion_proof: {native: {id: x.group, status: phase === 'POST' ? 'POSTED' : 'REVERSED'}, zero: 0},
      recorded_at: '2026-01-02T03:04:05Z',
    });
  }
  stage = 'SCOPE';
  const selected = await scope(), former = await oldScope();
  const r = keys(selected.relevant), o = keys(selected.outside), s = keys(selected.support);
  assert([...r].every(key => !o.has(key))); assert.deepEqual(new Set([...r, ...o]), s);
  assert(r.has('CONVERSION:' + relevant.group)); assert(r.has('REWORK:' + relevant.rework));
  assert(o.has('CONVERSION:' + outside.group)); assert(o.has('REWORK:' + outside.rework));
  assert(!keys(former.outside).has('CONVERSION:' + outside.group));
  assert(!r.has('CONVERSION:' + outside.group));
  passed('Typed automatic source identities expand each disjoint relevant/outside component');
  assert(!r.has('PRODUCT:' + outside.target));
  assert(!r.has('PRODUCT:' + isolated.target));
  passed('Shared location, account, backend and transaction values do not merge components');
  const baseline = await capture(selected), support = await capture(selected, false), formerCapture = await oldCapture(selected);
  for (const table of input.automatic_tables) {
    const rows = baseline.facts['SKU_AUTOMATIC_' + table];
    const expected = await scalar('select jsonb_agg(to_jsonb(t)order by to_jsonb(t)::text collate "C")from cp7_sku_conversion.' + table + ' t where conversion_id=$1', [outside.group]);
    // All non-relevant support components belong to the existing outside
    // domain. Check exact membership using the actual selected identity keys.
    const ids = selected.outside.identity_keys.filter(row => ['CONVERSION', 'SKU_GROUP'].includes(row.kind)).map(row => row.id);
    const allExpected = await scalar('select jsonb_agg(to_jsonb(t)order by to_jsonb(t)::text collate "C")from cp7_sku_conversion.' + table + ' t where conversion_id=any($1::uuid[])', [ids]);
    assert.deepEqual(rows, allExpected);
    assert(rows.some(row => row.conversion_id === outside.group));
    assert(!rows.some(row => row.conversion_id === relevant.group));
    assert.deepEqual(Object.keys(expected[0]).sort(), input.automatic_columns[table].map(([name]) => name).sort());
    assert(support.facts['SKU_AUTOMATIC_' + table].some(row => row.conversion_id === relevant.group));
    passed('Complete ' + table + ' rows retain every field and exact scope membership');
  }
  const history = baseline.facts.SKU_AUTOMATIC_automatic_admissions_v5.filter(row => row.conversion_id === outside.group);
  assert.deepEqual(history.map(row => row.phase).sort(), ['POST', 'REVERSE']);
  assert(history.every(row => row.context_proof.zero === 0 && row.conversion_proof.zero === 0));
  passed('Zero values and both immutable phases remain observable');
  stage = 'MUTATIONS';
  for (const table of input.automatic_tables) {
    for (const [column, , type] of input.automatic_columns[table]) {
      // Changing a key may remove a row from this frozen domain; that is a
      // detectable change too. No projection silently excuses the mutation.
      let value = type === 'uuid' ? id(890) : type === 'jsonb' ? {unreviewed: true, zero: 0} :
        type === 'timestamp with time zone' ? '2026-01-02T03:04:06Z' : /^(integer|bigint)/.test(type) ? 89 : 'CHANGED';
      await db.exec('begin');
      try {
        await db.query('update cp7_sku_conversion.' + table + ' set ' + quote(column) + '=$1 where conversion_id=$2', [value, outside.group]);
        assert.notEqual((await capture(selected)).sha256, baseline.sha256, table + '.' + column);
        assert.deepEqual(await oldCapture(selected), formerCapture, 'The retained parent omitted the new raw rows');
        passed('Detect full original field ' + table + '.' + column);
      } finally { await db.exec('rollback'); }
    }
    await db.exec('begin');
    try {
      await db.query('insert into cp7_sku_conversion.' + table + ' select *from cp7_sku_conversion.' + table + ' where conversion_id=$1', [outside.group]);
      const duplicated = await capture(selected);
      assert.notEqual(duplicated.sha256, baseline.sha256);
      assert.equal(duplicated.facts['SKU_AUTOMATIC_' + table].length,
        baseline.facts['SKU_AUTOMATIC_' + table].length + (table === 'automatic_context_v5' ? 1 : 2));
      passed('Retain duplicate multiplicity in ' + table);
    } finally { await db.exec('rollback'); }
  }
  for (const role of ['anon', 'authenticated', 'service_role']) {
    assert.equal(await scalar("select bool_or(has_function_privilege($1,p.oid,'EXECUTE'))from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='cp7_global_nonpo_native_graph'", [role]), false);
    passed(role + ' cannot execute the prepared private observation helpers');
  }
  const report = {status: 'MODELED_POSTGRES17_AUTOMATIC_GLOBAL_OBSERVATION_PASS_NOT_ERP', engine, results,
    input: {bytes: raw.length, sha256: createHash('sha256').update(raw).digest('hex')},
    derived_helpers: input.proof.derived_helpers, typed_tables: 82, typed_columns: 835,
    new_full_rowsets: 2, new_identity_edges: 8, modeled_callbacks: input.modeled_callbacks,
    constraints_owners_RLS_Native_callbacks_and_business_transactions_are_not_tested: true,
    actual_ERP_cases: 0, actual_Auth_HTTP_cases: 0, production_go: false, independent_acceptance: false};
  await writeFile(process.env.CP7_GRAPH_REPORT, JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify({status: report.status, checks: results.length, actual_ERP_cases: 0}));
} catch (error) {
  await writeFile(process.env.CP7_GRAPH_REPORT, JSON.stringify({status: 'MODEL_FAILED', stage, engine, results,
    error: {message: error.message, SQLSTATE: error.code ?? null, detail: error.detail, stack: error.stack}, actual_ERP_cases: 0}, null, 2) + '\n');
  throw error;
} finally { await db.close(); }
