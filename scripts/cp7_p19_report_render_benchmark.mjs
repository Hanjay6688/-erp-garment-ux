#!/usr/bin/env node
// report_render predecessor vs current on complete compiler outputs (explicit
// source stand-ins). The render text must be byte-identical at every size.
import { createHash } from 'node:crypto'
import { mkdirSync, writeFileSync } from 'node:fs'
import { dirname } from 'node:path'
import { openRuntime } from '../tests/cp7/families/f04/runtime.mjs'
import { assemblyInput } from '../tests/cp7/families/f04/analysis-assembly-fixture.mjs'
import { installRenderControls, outcomeSql, renderBase } from '../tests/cp7/families/f04/report-render-fixture.mjs'

const sizes = (process.env.CP7_P19_RENDER_SIZES || '300,1200,5000').split(',').map(Number)
if (sizes.some(n => !Number.isInteger(n) || n < 1 || n > 5000)) throw new Error('P19_RENDER_SIZES')
const out = process.argv[2] || 'cp7-proof/p19/REPORT_RENDER_KERNEL.json'
const report = { classification: 'DISPOSABLE_PURE_RENDER_KERNEL_EXPLICIT_SOURCE_STAND_INS', base: renderBase, vectors: [], Native_case_credit: 0, Native_ERP_timeouts_changed: false, production_go: false }
let db
try {
 // Disposable comparator deadline only; the quadratic predecessor needs it.
 db = await openRuntime({ commandTimeoutMs: 600_000 });report.runtime = db.flavor;report.version = db.version
 await installRenderControls(db)
 await db.execute([0, 1].map(i => `create function public.p19_render_timed_${i}(e jsonb)returns jsonb language plpgsql as $$declare started timestamptz:=clock_timestamp();t text;begin t:=public.p19_render_${i}(e,'PERIOD','Laporan periode');return jsonb_build_object('ms',extract(epoch from clock_timestamp()-started)*1000,'text',t);end$$;`).join('\n'))
 for (const targets of sizes) {
  const measured = (await db.query(`with o as materialized(select ${outcomeSql(assemblyInput(targets, 5))} e),
   r as materialized(select public.p19_render_timed_0(e) old,public.p19_render_timed_1(e) candidate,octet_length(e::text) outcome_bytes from o)
   select round((old->>'ms')::numeric,3)::text predecessor_ms,round((candidate->>'ms')::numeric,3)::text candidate_ms,old->>'text'=candidate->>'text' byte_identical,
    octet_length(candidate->>'text') bytes,encode(sha256(convert_to(candidate->>'text','UTF8')),'hex') sha256,outcome_bytes from r`))[0]
  report.vectors.push({ targets, ...measured })
  if (!measured.byte_identical) throw new Error('P19_RENDER_TEXT_DIFFERENCE')
  console.log(JSON.stringify({ targets, ...measured }))
 }
 report.status = 'PASS'
} catch (error) { report.status = 'INCOMPLETE'; report.error = String(error); process.exitCode = 1 }
finally {
 if (db) await db.close()
 mkdirSync(dirname(out), { recursive: true });writeFileSync(out, JSON.stringify(report, null, 2) + '\n')
 console.log(JSON.stringify({ status: report.status, vectors: report.vectors.length, error: report.error, digest: createHash('sha256').update(JSON.stringify(report.vectors)).digest('hex') }))
}
