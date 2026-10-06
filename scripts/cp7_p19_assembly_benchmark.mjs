#!/usr/bin/env node
// Full assembler/kernel benchmark with explicit source stand-ins. The real
// Native compiler/original equivalence remains a separate analysis152 gate.
import { createHash } from 'node:crypto'
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname } from 'node:path'
import { execFileSync } from 'node:child_process'
import { openRuntime } from '../tests/cp7/families/f04/runtime.mjs'
import { assemblyArgs, assemblyBase, assemblyInput, installAssemblyControls } from '../tests/cp7/families/f04/analysis-assembly-fixture.mjs'

const sizes = (process.env.CP7_P19_ASSEMBLY_SIZES || '300,1200,5000').split(',').map(Number)
if (sizes.some(n => !Number.isInteger(n) || n < 1 || n > 5000)) throw new Error('P19_BENCHMARK_SIZES')
const out = process.argv[2] || 'cp7-proof/p19/ASSEMBLY_KERNEL.json'
const digest = bytes => createHash('sha256').update(bytes).digest('hex')
const files = ['scripts/cp7-src/planning/analysis.sql', 'tests/cp7/families/f04/analysis-assembly-fixture.mjs', 'tests/cp7/families/f04/runtime.mjs', 'scripts/cp7_p19_assembly_benchmark.mjs']
const head = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim()
const dirty = Boolean(execFileSync('git', ['status', '--porcelain', '--', ...files], { encoding: 'utf8' }).trim())
const report = { classification: 'DISPOSABLE_PURE_COMPILER_KERNEL_EXPLICIT_SOURCE_STAND_INS', base: assemblyBase, git_head: head, working_tree_dirty: dirty, source_sha: dirty ? null : head, files_sha256: Object.fromEntries(files.map(p => [p, digest(readFileSync(p))])), vectors: [], Native_case_credit_added: 0, full_P19_acceptance: false, independent_acceptance: false, production_go: false }
let db
try {
 // The quadratic predecessor at 5000 targets exceeded the ordinary 60s
 // kernel-process deadline. This bound applies only to this disposable,
 // source-stand-in comparison, never to the Native ERP/HTTP timeout.
 db = await openRuntime({ commandTimeoutMs: 180_000 });report.runtime = db.flavor;report.version = db.version
 report.disposable_comparison_deadline_ms = 180_000
 report.Native_ERP_timeouts_changed = false
 await installAssemblyControls(db)
 await db.execute([0, 1].map(i => `create function public.p19_timed_${i}(c jsonb,q jsonb,p uuid,a jsonb)returns jsonb language plpgsql as $$declare started timestamptz:=clock_timestamp();v jsonb;ms numeric;begin v:=public.p19_assembly_${i}(c,q,p,a);ms:=extract(epoch from clock_timestamp()-started)*1000;return jsonb_build_object('body',v,'elapsed_ms',ms::text);end$$;`).join('\n'))
 const canary = (await db.query('select amount::text amount from public.f04_ledger_canary'))[0].amount
 for (const targets of sizes) {
  const input = assemblyInput(targets, 5), args = assemblyArgs(input)
  const measured = (await db.query(`with bodies as materialized(select public.p19_timed_0(${args}) old,public.p19_timed_1(${args}) candidate)
   select old->>'elapsed_ms' predecessor_ms,candidate->>'elapsed_ms' candidate_ms,
    (old->'body')::text=(candidate->'body')::text byte_identical,
    octet_length((candidate->'body')::text) bytes,encode(pg_catalog.sha256(convert_to((candidate->'body')::text,'UTF8')),'hex') sha256 from bodies`))[0]
  report.vectors.push({ targets, input_sha256: digest(JSON.stringify(input)), ...measured })
  if (!measured.byte_identical) throw new Error('P19_BENCHMARK_FULL_BODY_DIFFERENCE')
  console.log(JSON.stringify({ targets, ...measured }))
 }
 report.ledger_canary_unchanged = (await db.query('select amount::text amount from public.f04_ledger_canary'))[0].amount === canary
 if (!report.ledger_canary_unchanged) throw new Error('P19_BENCHMARK_CANARY_CHANGED')
 const last = report.vectors.at(-1)
 report.largest_ratio = Number(last.candidate_ms) / Number(last.predecessor_ms)
 if (last.targets >= 1200 && report.largest_ratio >= 0.5) throw new Error('P19_LARGEST_VECTOR_NOT_SUBSTANTIALLY_FASTER')
 report.status = 'PASS'
} catch (error) {
 report.status = 'INCOMPLETE';report.error = String(error);process.exitCode = 1
} finally {
 if (db) await db.close()
 mkdirSync(dirname(out), { recursive: true });writeFileSync(out, JSON.stringify(report, null, 2) + '\n')
 console.log(JSON.stringify({ status: report.status, runtime: report.runtime, vectors: report.vectors.length, largest_ratio: report.largest_ratio, error: report.error }))
}
