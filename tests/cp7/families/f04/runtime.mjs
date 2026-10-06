import { execFileSync } from 'node:child_process';
import { existsSync, mkdtempSync, readFileSync, readdirSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { resolve, join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { createHash } from 'node:crypto';

export const sourceFiles = [
  'scripts/cp7-src/wip/bootstrap.sql',
  'scripts/cp7-src/wip/matching.sql',
  'scripts/cp7-src/wip/timing.sql',
  'scripts/cp7-src/demand/bootstrap.sql',
  'scripts/cp7-src/demand/history.sql',
  'scripts/cp7-src/demand/estimate.sql',
  'scripts/cp7-src/baseline/target.sql',
  'scripts/cp7-src/baseline/timeline.sql',
  'scripts/cp7-src/baseline/feasibility.sql',
  'scripts/cp7-src/baseline/allocation.sql',
  'scripts/cp7-src/baseline/capacity.sql',
  'scripts/cp7-src/baseline/dependencies.sql',
  'scripts/cp7-src/models/kernels.sql',
  'scripts/cp7-src/models/evaluation.sql',
  'scripts/cp7-src/models/comparison.sql',
  'scripts/cp7-src/models/ownership.sql',
];
export const digest = value => createHash('sha256').update(value).digest('hex');
export const sourceHashes = Object.fromEntries(sourceFiles.map(path => [path, digest(readFileSync(path))]));
const literal = value => `'${String(value).replaceAll("'", "''")}'`;
export const jsonArg = value => `${literal(JSON.stringify(value))}::jsonb`;
export const textArg = value => `${literal(value)}::text`;

// No external DB URL is accepted. Native mode creates an isolated Unix-socket DB;
// the optional WASM mode must be explicitly selected and is labelled as such.
export async function openRuntime({ commandTimeoutMs = 60_000 } = {}) {
  if (!Number.isInteger(commandTimeoutMs) || commandTimeoutMs < 60_000 || commandTimeoutMs > 180_000) throw new Error('F04 disposable command timeout out of bounds');
  let execute, query, close, flavor;
  if (process.env.F04_PGLITE_MODULE) {
    if (process.env.CI) throw new Error('F04 CI requires native PostgreSQL; WASM override refused');
    const { PGlite } = await import(pathToFileURL(resolve(process.env.F04_PGLITE_MODULE)).href);
    const db = new PGlite();
    await db.waitReady;
    execute = sql => db.exec(sql);
    query = async sql => (await db.query(sql)).rows;
    close = () => db.close();
    flavor = 'PGLITE_WASM_LOCAL_NOT_NATIVE_AUTH_PROOF';
  } else {
    const root = '/usr/lib/postgresql';
    const versions = existsSync(root) ? readdirSync(root).filter(v => /^\d+$/.test(v)).sort((a, b) => Number(b) - Number(a)) : [];
    const bin = versions.map(v => join(root, v, 'bin')).find(p => existsSync(join(p, 'initdb')));
    if (!bin || process.getuid?.() === 0) throw new Error('F04 native PostgreSQL unavailable/non-root required. Explicit local F04_PGLITE_MODULE is allowed; no green skip.');
    const dir = mkdtempSync(join(tmpdir(), 'cp7-f04-'));
    const data = join(dir, 'data');
    let started = false;
    // Unrelated PG* credentials/URLs cannot redirect this disposable connection.
    const env = Object.fromEntries(Object.entries(process.env).filter(([key]) => !key.startsWith('PG')));
    const command = (name, args, options = {}) => execFileSync(join(bin, name), args, { env, encoding: 'utf8', timeout: commandTimeoutMs, maxBuffer: 32 * 1024 * 1024, ...options });
    close = async () => {
      if (started || existsSync(join(data, 'postmaster.pid'))) { command('pg_ctl', ['-D', data, '-m', 'immediate', '-w', 'stop']); started = false; }
      rmSync(dir, { recursive: true, force: true });
    };
    try {
      command('initdb', ['-D', data, '-U', 'cp7_f04_test', '--auth-local=trust', '--auth-host=reject', '--no-locale', '--encoding=UTF8']);
      command('pg_ctl', ['-D', data, '-l', join(dir, 'postgres.log'), '-o', `-k ${dir} -c listen_addresses='' -c max_connections=10`, '-w', 'start']);
      started = true;
      const psql = sql => command('psql', ['-X', '-q', '-A', '-t', '-v', 'ON_ERROR_STOP=1', '-h', dir, '-U', 'cp7_f04_test', '-d', 'postgres'], { input: sql });
      execute = async sql => psql(sql);
      query = async sql => {
        const result = psql(`select coalesce(json_agg(f04_row),'[]'::json) from (${sql.replace(/;\s*$/, '')}) f04_row;`);
        return JSON.parse(result.trim());
      };
      flavor = 'NATIVE_POSTGRES_DISPOSABLE_KERNEL_ONLY';
    } catch (error) { await close(); throw error; }
  }
  try {
    const roles = `create role cp7_capture nologin nosuperuser nobypassrls;
      create role anon nologin;create role authenticated nologin;create role service_role nologin;
      create table public.f04_ledger_canary(id integer primary key, amount numeric not null);
      insert into public.f04_ledger_canary values(1,12345.67);`;
    const dependenciesOwnership = `alter function cp7_wip.fields(jsonb,text[]) owner to cp7_capture;
      alter function cp7_wip.key(jsonb) owner to cp7_capture;
      alter function cp7_wip.pcs(jsonb) owner to cp7_capture;
      alter function cp7_wip.refs(jsonb) owner to cp7_capture;
      alter function cp7_wip.match_target(jsonb,jsonb) owner to cp7_capture;
      alter function cp7_wip.check_allocations(jsonb,jsonb) owner to cp7_capture;
      revoke all on all functions in schema cp7_wip from public,anon,authenticated,service_role;`;
    await execute(`begin;${roles}\n${sourceFiles.map(path => readFileSync(path, 'utf8')).join('\n')}\n${dependenciesOwnership}\ncommit;`);
    const version = (await query('select version() as version'))[0].version;
    return {
      execute, query, close, flavor, version,
      async call(name, args) {
        if (!/^cp7_(demand|baseline|models|wip)\.[a-z_]+$/.test(name)) throw new Error('Invalid test function');
        return (await query(`select ${name}(${args.join(',')}) as result`))[0].result;
      },
    };
  } catch (error) { await close(); throw error; }
}
