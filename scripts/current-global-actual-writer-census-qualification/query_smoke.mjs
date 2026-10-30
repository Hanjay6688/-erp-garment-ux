// Local SQL syntax/ABI control only. No ERP installed, no concurrency credit.
// Args: installed PGlite module path, capture query JSON, result JSON.
import { readFileSync, writeFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

if (process.argv.length !== 5) throw new Error('PGLITE_MODULE_QUERY_JSON_RESULT_JSON_REQUIRED');
const { PGlite } = await import(pathToFileURL(process.argv[2]).href);
const db = new PGlite();
try {
  await db.exec(`
    create schema erp;
    create role census_reader;
    create role census_writer;
    grant census_writer to census_reader with inherit false, set true;
    create table erp.lots(id bigint primary key);
    create table erp.history(transaction_id bigint, lot_id bigint references erp.lots(id));
    create function erp.writer() returns void language sql as $$insert into erp.lots values(1);$$;
    create function erp.trigger_fn() returns trigger language plpgsql as $$begin return new;end$$;
    create trigger lots_after after insert on erp.lots for each row execute function erp.trigger_fn();
    create view erp.v_lots as select * from erp.lots;
    create sequence erp.serial;
    grant select(id) on erp.lots to census_reader;
    set search_path='';set timezone='UTC';
  `);
  const queries = JSON.parse(readFileSync(process.argv[3], 'utf8'));
  const inputs = {
    schemas: ['erp'],
    relations: (await db.query("select n.nspname||'.'||c.relname name from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp'")).rows.map(r => r.name),
    functions: (await db.query("select p.oid::regprocedure::text name from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='erp'")).rows.map(r => r.name),
  };
  const results = {
    classification: 'LOCAL_PGLITE_QUERY_SYNTAX_AND_CATALOG_ABI_ONLY',
    server: (await db.query('select version()')).rows[0].version,
    actual_Native_credit: 0, production_go: false, independent_acceptance: false, checks: {},
  };
  await db.exec('begin read only');
  for (const [name, query] of Object.entries(queries)) {
    const names = [];
    const rewritten = query.replace(/%\((\w+)\)s/g, (_, key) => {
      if (!names.includes(key)) names.push(key);
      return '$' + (names.indexOf(key) + 1);
    });
    try {
      const result = await db.query(rewritten, names.map(key => inputs[key]));
      results.checks[name] = { status: 'PASS', rows: result.rows.length };
    } catch (error) {
      results.checks[name] = { status: 'FAIL', message: error.message };
      process.exitCode = 1;
    }
  }
  await db.exec('rollback');
  writeFileSync(process.argv[4], JSON.stringify(results, null, 2) + '\n');
  console.log(JSON.stringify({ classification: results.classification,
    checks: Object.keys(results.checks).length,
    failures: Object.entries(results.checks).filter(([, value]) => value.status !== 'PASS') }));
} finally {
  await db.close();
}
