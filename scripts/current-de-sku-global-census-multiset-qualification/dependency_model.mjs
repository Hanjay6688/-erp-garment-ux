// Local PostgreSQL17 catalogue semantics only; not an actual ERP observation.
// Args: existing PGlite module path, exact frozen query JSON, result JSON.
import { readFileSync, writeFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

if (process.argv.length !== 5) throw new Error('MODEL_MODULE_QUERIES_RESULT_REQUIRED');
const { PGlite } = await import(pathToFileURL(process.argv[2]).href);
const db = new PGlite();
const ddl = `create schema dependency_model;
create table dependency_model.t(a integer primary key, b integer);
create function dependency_model.trigger_fn() returns trigger language plpgsql as $$begin return new; end$$;
create trigger t_update before update of a on dependency_model.t
for each row when(new.a<>old.a) execute function dependency_model.trigger_fn();
create view dependency_model.v as select a from dependency_model.t;`;
try {
  await db.exec(ddl);
  const server = (await db.query('select version()')).rows[0].version;
  if (!server.startsWith('PostgreSQL 17.')) throw new Error('MODEL_PG17_REQUIRED');
  const queries = JSON.parse(readFileSync(process.argv[3], 'utf8'));
  const params = {
    schemas: ['dependency_model'],
    relations: (await db.query("select n.nspname||'.'||c.relname name from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='dependency_model'")).rows.map(r => r.name).sort(),
    functions: ['dependency_model.trigger_fn()'],
  };
  await db.exec('BEGIN');
  await db.exec('SET TRANSACTION ISOLATION LEVEL READ COMMITTED READ ONLY');
  await db.query("SELECT pg_catalog.set_config('search_path','',true)");
  await db.exec("SET LOCAL TimeZone='UTC'");
  const settings = (await db.query("select current_setting('transaction_read_only') ro,current_setting('transaction_isolation') isolation,current_setting('search_path') path,current_setting('TimeZone') timezone")).rows[0];
  const groups = {};
  for (const name of ['dependencies', 'view_relation_dependencies']) {
    const names = [];
    const sql = queries[name].replace(/%\((\w+)\)s/g, (_, key) => {
      if (!names.includes(key)) names.push(key);
      return '$' + (names.indexOf(key) + 1);
    });
    const result = await db.query(sql, names.map(key => params[key]));
    groups[name] = result.rows.map(row => [row['?column?'], row.jsonb_build_array]);
  }
  const identities = groups.dependencies.map(row => row[0]);
  const duplicateIdentities = [...new Set(identities)].filter(key => identities.filter(other => other === key).length > 1);
  if (duplicateIdentities.length !== 1) throw new Error('MODEL_EXPECTED_ONE_DUPLICATE_IDENTITY');
  const duplicateRows = groups.dependencies.filter(row => row[0] === duplicateIdentities[0]);
  if (duplicateRows.length !== 2 || JSON.stringify(duplicateRows[0]) !== JSON.stringify(duplicateRows[1])) throw new Error('MODEL_EXACT_DUPLICATE_REQUIRED');
  if (JSON.stringify(settings) !== JSON.stringify({ ro: 'on', isolation: 'read committed', path: '', timezone: 'UTC' })) throw new Error('MODEL_READ_TRANSACTION_SETTINGS_CHANGED');
  await db.exec('ROLLBACK');
  const result = { classification: 'LOCAL_PG17_DUPLICATE_DEPENDENCY_SEMANTICS_ONLY', server, ddl, settings,
    query_names: Object.keys(groups), raw_query_pairs: groups, repeated_identity_count: duplicateIdentities.length,
    exact_duplicate_occurrences: duplicateRows.length, direct_system_catalog_writes: false,
    actual_ERP_offending_rows_known: false, actual_Native_credit: 0, production_go: false, independent_acceptance: false };
  writeFileSync(process.argv[4], JSON.stringify(result, null, 2) + '\n', { flag: 'wx' });
  console.log(JSON.stringify({ status: 'PASS_LOCAL_PG17_MODEL_ONLY', exact_duplicate_occurrences: 2, actual_Native_credit: 0 }));
} finally { await db.close(); }
