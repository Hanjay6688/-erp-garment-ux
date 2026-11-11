import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { writeFile } from 'node:fs/promises';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const digest = value => createHash('sha256').update(JSON.stringify(value)).digest('hex');
const errorDetails = error => ({
  message: error.message, sqlstate: error.code ?? null, where: error.where ?? null,
  detail: error.detail ?? null, stack: error.stack,
});
const fixtureInventory = `
  select jsonb_build_object(
    'namespaces', (select jsonb_agg(nspname order by nspname) from pg_namespace
      where nspname !~ '^pg_' and nspname <> 'information_schema'),
    'roles', (select jsonb_agg(rolname order by rolname) from pg_roles
      where rolname !~ '^pg_'),
    'relations', (select coalesce(jsonb_agg(n.nspname||'.'||c.relname order by n.nspname,c.relname),'[]')
      from pg_class c join pg_namespace n on n.oid=c.relnamespace
      where n.nspname !~ '^pg_' and n.nspname <> 'information_schema')
  ) as inventory`;

export class Pg17Lab {
  static async open() {
    const { Client } = require(process.env.CP7_PG_MODULE);
    const port = Number(process.env.CP7_LAB_PORT);
    const dataDirectory = process.env.CP7_LAB_PGDATA;
    assert.ok(Number.isInteger(port) && port >= 1024 && port <= 65535 && dataDirectory);
    const client = new Client({
      host: '127.0.0.1', port, database: 'postgres', user: 'movavg_lab',
      ssl: false, connectionTimeoutMillis: 3000, application_name: 'cp7_b_movavg_fixture',
    });
    await client.connect();
    try {
      const { rows: [server] } = await client.query(`
        select host(inet_server_addr()) as ip, current_database() as database,
          current_user as actor, current_setting('data_directory') as pgdata,
          current_setting('server_version') as version`);
      assert.deepEqual(server, {
        ip: '127.0.0.1', database: 'postgres', actor: 'movavg_lab', pgdata: dataDirectory, version: '17.6',
      });
      const { rows: [{ inventory }] } = await client.query(fixtureInventory);
      assert.deepEqual(inventory, { namespaces: ['public'], roles: ['movavg_lab'], relations: [] });
      await client.query('begin');
      await client.query("set local statement_timeout='15s'; set local lock_timeout='3s'; set local timezone='UTC'");
      return new Pg17Lab(client, inventory);
    } catch (error) {
      await client.end();
      throw error;
    }
  }

  constructor(client, inventory) {
    this.client = client;
    this.before = inventory;
    this.report = { scope: 'POSTGRESQL_17_6_EXACT_MONEY_SQL_WITH_TYPED_FIXTURE', cases: [],
      actual_full_ERP_cases: 0, production_go: false, independent_acceptance: false };
  }

  query(text, values) { return this.client.query(text, values); }
  exec(text) { return this.client.query(text); }

  async firstFailure(error, stage) {
    const failure = { stage, ...errorDetails(error) };
    try {
      await writeFile(process.env.CP7_FIRST_FAILURE, JSON.stringify(failure, null, 2) + '\n', { flag: 'wx' });
    } catch (error) {
      if (error.code !== 'EEXIST') throw error;
    }
    this.report.failures ??= [];
    this.report.failures.push(failure);
    console.error(JSON.stringify({ stage, message: failure.message, sqlstate: failure.sqlstate }));
  }

  async close() {
    try {
      await this.exec('rollback');
      const { rows: [{ inventory }] } = await this.query(fixtureInventory);
      this.report.recovery = { method: 'ROLLBACK_OUTER_TRANSACTION',
        before: this.before, after: inventory, exact: digest(this.before) === digest(inventory) };
      assert.deepEqual(inventory, this.before, 'Disposable schema/data and test roles must be removed');
    } catch (error) {
      await this.firstFailure(error, 'OUTER_ROLLBACK');
      process.exitCode = 1;
    } finally {
      await this.client.end();
    }
    await writeFile(process.env.CP7_REPORT, JSON.stringify(this.report, null, 2) + '\n', { flag: 'wx' });
  }
}

// The oracle uses integer cents calculated from the approved 2-piece pool and
// source-price changes. No target or journal field is used to calculate them.
const expected = {
  usage: { pcs: 2, hpp: 7200, fg: 7200, cogs: 0, other: 0 },
  soldOne: { pcs: 1, hpp: 7200, fg: 3600, cogs: 3600, other: 0 },
  lateOne: { pcs: 1, hpp: 7302, fg: 3651, cogs: 3651, other: 0 },
  returnedAfterPartial: { pcs: 2, hpp: 7302, fg: 7302, cogs: 0, other: 0 },
  soldTwo: { pcs: 0, hpp: 7200, fg: 0, cogs: 7200, other: 0 },
  lateTwo: { pcs: 0, hpp: 7301, fg: 0, cogs: 7301, other: 0 },
  returned: { pcs: 1, hpp: 7301, fg: 3651, cogs: 3650, other: 0 },
  costReverted: { pcs: 1, hpp: 7200, fg: 3600, cogs: 3600, other: 0 },
};
const salePriceCents = 18_500_000;

export async function runFocusedCases(ctx) {
  const { db, input, engine, x, id, query, scalar, insert, saleSetup, costReconcile,
    costPool, costSnapshot, costBaseline: moneyBaseline, initializeBaseFixture, costDocument, costAccount } = ctx;
  db.report.engine = engine;
  db.report.source = input.source_pins;
  db.report.variant = input.probe_variant ?? 'UNCHANGED_CANDIDATE_DEFINITIONS';
  db.report.model_providers = ['historical openings and conversion', 'source amount from material valuation',
    'authority and credit lifecycle', 'journal storage', 'known laundry state'];
  assert.match(engine, /^PostgreSQL 17\.6 /);
  const costBaseline = await costSnapshot();
  assert.deepEqual(costBaseline, { ...moneyBaseline,
    'cp7_sku_conversion.automatic_admissions_v5': [], 'cp7_sku_conversion.automatic_context_v5': [],
  }, 'The automatic delta adds two empty tables and preserves all existing rows');

  const journalIds = () => scalar("select coalesce(array_agg(id order by id),'{}') from erp.journal_entries");
  const allocationSnapshot = () => scalar(`
    select jsonb_build_object(
      'allocations', (select jsonb_agg(to_jsonb(a) order by id) from erp.sale_stock_allocations a
        where a.sale_item_id=$1),
      'values', (select jsonb_agg(to_jsonb(v) order by sale_stock_allocation_id)
        from cp7_sku_conversion.sale_allocation_values_v2 v where v.sale_id=$2),
      'cost_components', (select jsonb_agg(to_jsonb(c) order by c.sale_stock_allocation_id,c.line_no)
        from cp7_sku_conversion.sale_cost_components_v3 c join cp7_sku_conversion.sale_allocation_values_v2 v
        using(sale_stock_allocation_id) where v.sale_id=$2))`, [x.saleItem, x.sale]);
  const returnSnapshot = returned => scalar(`
    select jsonb_agg(to_jsonb(v) order by sales_return_item_id)
    from cp7_sku_conversion.sales_return_values_v2 v where return_id=$1`, [returned]);

  async function journalSince(before) {
    const { rows } = await query(`
      select j.id,j.source_type,j.source_id,j.economic_date::text,
        coalesce(m.mapping_key,case when l.account_id=$2 then 'MATERIAL_COST_OFFSET' else l.account_id::text end) as account,
        (l.debit*100)::integer as debit,(l.credit*100)::integer as credit,l.product_id::text
      from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id
      left join erp.accounting_account_mappings m on m.account_id=l.account_id
      where not(j.id=any($1::uuid[])) order by j.source_type,j.id,account,l.id`, [before, costAccount]);
    const net = {}, totals = {};
    for (const line of rows) {
      const amount = line.debit - line.credit;
      totals[line.id] = (totals[line.id] ?? 0) + amount;
      net[line.account] = (net[line.account] ?? 0) + amount;
    }
    return { rows, net: Object.fromEntries(Object.entries(net).filter(([, amount]) => amount)), totals };
  }

  async function observe(result, phase, want, before, net) {
    const { rows: [state] } = await query(`
      select
        (select cached_qty_pcs from erp.fg_inventory_balances where product_id=$1 and location_id=$2
         and quality_grade='GRADE_A') as cached_pcs,
        (select coalesce(sum(qty_signed),0)::integer from erp.fg_stock_movements
         where product_id=$1 and location_id=$2 and quality_grade='GRADE_A') as ledger_pcs,
        (t.hpp_total_cost*100)::integer as hpp,(t.fg_value*100)::integer as fg,
        (t.cogs_value*100)::integer as cogs,(t.other_out_value*100)::integer as other,
        (b.hpp_total_cost*100)::integer as book_hpp,(b.fg_value*100)::integer as book_fg,
        (b.cogs_value*100)::integer as book_cogs,(b.other_out_value*100)::integer as book_other
      from erp.compute_non_po_product_hpp_targets_v2620f($1)t
      cross join erp.compute_non_po_product_hpp_book_v2620f($1)b`, [x.target, x.location]);
    const pool = await costPool();
    const journal = await journalSince(before);
    result.observations.push({ phase, expected: want, actual: state, pool, expected_journal_net_cents: net, journal });
    assert.deepEqual(state, {
      cached_pcs: want.pcs, ledger_pcs: want.pcs, hpp: want.hpp, fg: want.fg, cogs: want.cogs,
      other: want.other, book_hpp: want.hpp, book_fg: want.fg, book_cogs: want.cogs, book_other: want.other,
    }, phase);
    assert.equal(Number(pool.qty), want.pcs);
    assert.equal(want.fg + want.cogs + want.other, want.hpp);
    assert.deepEqual(journal.net, net, phase + ' journal accounts');
    assert.ok(Object.values(journal.totals).every(total => total === 0), phase + ' balanced journals');
  }

  async function sale(count) {
    const lots = count === 2 ? [x.root50, x.converted] : [x.root50];
    await saleSetup(x.target, lots, lots.map(() => 1));
    await query('update erp.sales_headers set source_location_id=$1,customer_id=$2 where id=$3',
      [x.location, id(900), x.sale]);
    await query('update erp.sales_items set qty_pcs=$1,unit_price_snapshot=185000,discount_amount=0 where id=$2',
      [count, x.saleItem]);
    for (const lot of lots) {
      await query(`select erp.post_fg_movement($1,$2,$3,'GRADE_A','SALE_RESERVE',-1,0,$4,'SALE_ITEM',$5,
        '2026-01-02T00:00:00Z','disposable probe reservation',false)`,
        [x.target, lot, x.location, id(900), x.saleItem]);
    }
    await query('select erp.post_sale($1)', [x.sale]);
  }

  async function returnOne() {
    const returned = id(88001);
    await insert('erp.sales_returns', { id: returned, sale_id: x.sale, customer_id: id(900), status: 'DRAFT',
      physical_at: '2026-01-03T01:00:00Z' });
    await insert('erp.sales_return_items', { id: id(89001), return_id: returned, sale_stock_allocation_id: x.saleA,
      product_id: x.target, lot_id: x.root50, location_id: x.location, quality_grade: 'GRADE_A',
      qty_pcs: 1, refund_amount: 185000 });
    await query('select erp.post_sales_return($1)', [returned]);
    return returned;
  }

  async function sameAmountReplay(result, amount) {
    const before = await costSnapshot();
    await costReconcile(amount);
    const after = await costSnapshot();
    result.same_source_amount_replayed = { amount, before: digest(before), after: digest(after), identical: digest(before) === digest(after) };
    assert.deepEqual(after, before, 'Repeat reconciliation must leave every fixture row identical');
  }

  async function run(caseId, count, body) {
    const result = { id: caseId, status: 'FAIL', observations: [] };
    db.report.cases.push(result);
    await db.exec('savepoint focused_case');
    try {
      await initializeBaseFixture(caseId);
      let before = await journalIds();
      await costReconcile('2.00');
      await observe(result, 'initial_usage', expected.usage, before, { FG_INVENTORY: 200, MATERIAL_COST_OFFSET: -200 });
      before = await journalIds();
      await sale(count);
      const sold = count === 1 ? expected.soldOne : expected.soldTwo;
      await observe(result, 'sale', sold, before, {
        AR_CUSTOMER: count * salePriceCents, SALES_REVENUE: -count * salePriceCents,
        FG_INVENTORY: -sold.cogs, COGS: sold.cogs,
      });
      await body(result, await allocationSnapshot());
      result.status = 'PASS';
    } catch (error) {
      await db.firstFailure(error, caseId);
      process.exitCode = 1;
    } finally {
      await db.exec('rollback to savepoint focused_case; release savepoint focused_case');
      const restored = await costSnapshot();
      result.rollback = { before: digest(costBaseline), after: digest(restored), identical: digest(restored) === digest(costBaseline) };
      assert.deepEqual(restored, costBaseline, 'All fixture tables must match their starting state');
    }
  }

  await run('B_LATE_COST_AFTER_PARTIAL_SALE', 1, async (result, original) => {
    const before = await journalIds();
    await costReconcile('3.02');
    await observe(result, 'late_cost', expected.lateOne, before, { FG_INVENTORY: 51, COGS: 51, MATERIAL_COST_OFFSET: -102 });
    assert.deepEqual(await allocationSnapshot(), original, 'Recost preserves the posted sale snapshot');
    await sameAmountReplay(result, '3.02');
    const returnBefore = await journalIds();
    const returned = await returnOne();
    await observe(result, 'return_one', expected.returnedAfterPartial, returnBefore, {
      FG_INVENTORY: 3651, COGS: -3651, SALES_REVENUE: salePriceCents, AR_CUSTOMER: -salePriceCents,
    });
    assert.equal((await returnSnapshot(returned))[0].effective_value, 36.51);
    assert.deepEqual(await allocationSnapshot(), original, 'Return preserves the original sale snapshot');
    result.sale_snapshot_immutable = true;
  });

  await run('B_RETURN_AFTER_LATE_COST_ODD_CENT', 2, async (result, original) => {
    let before = await journalIds();
    await costReconcile('3.01');
    await observe(result, 'late_cost', expected.lateTwo, before, { COGS: 101, MATERIAL_COST_OFFSET: -101 });
    await sameAmountReplay(result, '3.01');
    before = await journalIds();
    const returned = await returnOne();
    const { rows: [costParts] } = await query(`
      select cp7_sku_conversion.cost_scope_value_v3($1,null,'SOLD')::text as sold,
        cp7_sku_conversion.cost_scope_value_v3($1,null,'RETURNED')::text as returned`, [x.target]);
    result.additional_cost_projection = costParts;
    assert.equal(Number(costParts.sold), 3.01);
    assert.equal(Number(costParts.returned), 1.505);
    await observe(result, 'return_one', expected.returned, before, {
      FG_INVENTORY: 3651, COGS: -3651, SALES_REVENUE: salePriceCents, AR_CUSTOMER: -salePriceCents,
    });
    const bookedReturn = await returnSnapshot(returned);
    assert.equal(bookedReturn.length, 1);
    assert.equal(bookedReturn[0].effective_value, 36.51);
    before = await journalIds();
    await costReconcile('2.00');
    await observe(result, 'cost_reverted_with_active_return', expected.costReverted, before,
      { FG_INVENTORY: -51, COGS: -50, MATERIAL_COST_OFFSET: 101 });
    assert.deepEqual(await returnSnapshot(returned), bookedReturn);
    assert.deepEqual(await allocationSnapshot(), original);
    result.sale_snapshot_immutable = true;
    result.return_snapshot_immutable = true;
    result.return_snapshot = bookedReturn;
  });

  db.report.cost_document_id = costDocument;
  db.report.model_tables_checked = Object.keys(costBaseline).length;
}
