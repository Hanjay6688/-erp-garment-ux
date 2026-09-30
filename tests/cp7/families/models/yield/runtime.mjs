import { execFileSync } from 'node:child_process'
import { existsSync, mkdtempSync, readFileSync, readdirSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'
import { pathToFileURL } from 'node:url'

export const sourceFile = 'scripts/cp7-src/models/cutting-yield.sql'
const literal = value => `'${JSON.stringify(value).replaceAll("'", "''")}'::jsonb`
export async function openYieldRuntime({ demoPreview = false } = {}) {
  let execute, query, close, runtime
  if (process.env.F04_YIELD_PGLITE_MODULE) {
    if (process.env.CI && !demoPreview) throw new Error('CI requires native disposable PostgreSQL, not a WASM override.')
    const { PGlite } = await import(pathToFileURL(resolve(process.env.F04_YIELD_PGLITE_MODULE)).href)
    const db = new PGlite(); await db.waitReady
    execute = sql => db.exec(sql); query = async sql => (await db.query(sql)).rows
    close = () => db.close(); runtime = 'PGLITE_LOCAL_NOT_AUTH_PROOF'
  } else {
    if (process.getuid?.() === 0) throw new Error('Native test requires a non-root process; local WASM override must be explicit.')
    const base = '/usr/lib/postgresql'
    const major = existsSync(base) ? readdirSync(base).filter(v => /^\d+$/.test(v)).sort((a,b) => Number(b)-Number(a))[0] : null
    if (!major) throw new Error('Native PostgreSQL unavailable; no green skip or external database fallback.')
    const bin = join(base, major, 'bin'), temp = mkdtempSync(join(tmpdir(), 'cp7-yield-'))
    const env = Object.fromEntries(Object.entries(process.env).filter(([key]) => !/^PG/.test(key)))
    const command = (name,args) => execFileSync(join(bin,name),args,{encoding:'utf8',env,timeout:60000,maxBuffer:16*1024*1024})
    const data = join(temp,'data'); let started = false
    close = async () => { try { if(started) command('pg_ctl',['-D',data,'-m','immediate','-w','stop']) } finally { rmSync(temp,{recursive:true,force:true}) } }
    try {
      command('initdb',['-D',data,'-U','cp7_yield_test','--auth-local=trust','--auth-host=reject','--no-locale','--encoding=UTF8'])
      command('pg_ctl',['-D',data,'-l',join(temp,'postgres.log'),'-o',`-k ${temp} -c listen_addresses='' -c max_connections=10`,'-w','start']); started=true
      const psql = sql => command('psql',['-X','-q','-A','-t','-v','ON_ERROR_STOP=1','-h',temp,'-U','cp7_yield_test','-d','postgres','-c',sql]).trim()
      execute = async sql => { psql(sql) }; query = async sql => JSON.parse(psql(`select coalesce(json_agg(q),'[]'::json) from (${sql}) q`))
      runtime = 'NATIVE_POSTGRES_DISPOSABLE_KERNEL_ONLY'
    } catch(error) { await close(); throw error }
  }
  try {
    await execute(`create role cp7_capture nologin nosuperuser nobypassrls;
      create role anon nologin; create role authenticated nologin; create role service_role nologin;
      create table public.yield_ledger_canary(amount numeric); insert into public.yield_ledger_canary values(12345.67);`)
    await execute(`begin; ${readFileSync(sourceFile,'utf8')} commit;`)
    return { runtime, execute, query, close,
      review: async request => (await query(`select cp7_yield.review(${literal(request)}) as result`))[0].result,
      version: (await query('select version() as version'))[0].version }
  } catch(error) { await close(); throw error }
}
