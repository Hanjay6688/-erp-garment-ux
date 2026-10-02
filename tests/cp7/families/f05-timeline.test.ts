// @vitest-environment node
import { execFileSync } from 'node:child_process'
import { readFileSync } from 'node:fs'
import { expect, test } from 'vitest'
import { openRuntime, jsonArg } from './f04/runtime.mjs'

test('ordered timeline aggregation equals the predecessor including intraday rows, nulls and exact decimals', async () => {
  // Pure SQL only. Real Native complete-compiler equivalence is mandatory in
  // P14_NATIVE_ANALYSIS_FROZEN_NATIVE; this grants no Native/Auth PASS credit.
  const constants = JSON.parse(execFileSync('python', ['-c', 'import sys,json;sys.path.insert(0,"scripts");import cp7_timeline_compile_equivalence as t;print(json.dumps([t.OLD_TIMELINE,t.NEW_TIMELINE]))'], { encoding: 'utf8' }))
  const source = readFileSync('scripts/cp7-src/planning/analysis.sql', 'utf8')
  expect(source.split(constants[1])).toHaveLength(2)
  const fact = source.slice(source.indexOf('create function cp7_analysis_native.fact('), source.indexOf('create function cp7_analysis_native.build('))
  const db = await openRuntime()
  try {
    await db.execute(`create schema cp7_analysis_native;${fact}
      ${constants.map((body: string, i: number) => `create function public.timeline_control_${i}(r jsonb,n jsonb,row_aids jsonb)returns jsonb
        language plpgsql immutable set search_path=''set TimeZone='UTC'as $$
        declare e jsonb;event jsonb;supply_match text;timeline jsonb:='[]';target_timeline jsonb;
        begin ${body}return timeline;end $$;`).join('\n')}`)
    const matches = ['CONFIRMED_TARGET', 'CANDIDATE_MATCH', null, 'REJECTED', null]
    const n = { allocation: { allocation: { edges: matches.map((match, i) => ({ key: String(i), target_key: 'ROOT:SIZE', match })) } }, match_results: [{ position_key: '2', target_key: 'ROOT:SIZE', result: { match: 'CONFIRMED_TARGET' } }] }
    const events = Array.from({ length: 2700 }, (_, i) => ({ event: { kind: i % 3 === 0 ? 'DEMAND' : i % 3 === 1 ? 'SUPPLY' : 'UNKNOWN', at: i % 2 ? '2026-01-01T17:00:00.000001Z' : '2026-01-01T16:59:59.999999Z', key: `supply-${i % 5}`, qty_pcs: i % 2 ? '9007199254740993.01' : '3', refs: [{ source: 'EXPLICIT_SYNTHETIC_KERNEL_ONLY', key: String(i) }] }, balance_pcs: i % 13 === 0 ? null : '-9007199254740993.01', new_unmet_pcs: '0.01' }))
    for (const sample of [[], events.slice(0, 15), events]) {
      const row = { target_key: 'ROOT:SIZE', timeline: { events: sample, minimum_balance_pcs: '-9007199254740993.01', first_known_gap: { at: '2026-01-01T17:00:00.000001Z' } } }
      const args = [jsonArg(row), jsonArg(n), jsonArg(['OWNER_ASSUMPTION'])].join(',')
      const result = (await db.query(`select public.timeline_control_0(${args})::text old,public.timeline_control_1(${args})::text candidate`))[0]
      expect(result.candidate).toBe(result.old)
      const timeline = JSON.parse(result.candidate)
      expect(timeline).toHaveLength(sample.length)
      if (sample.length) {
        expect(timeline[0].date).toBe('2026-01-01')
        expect(timeline[1].date).toBe('2026-01-02')
        expect(timeline[0].balance_end.state).toBe('UNKNOWN')
        expect(timeline[1].candidate_supply.value).toBe('9007199254740993.01')
        expect(timeline.map((entry: { event_refs: { key: string }[] }) => entry.event_refs[0].key)).toEqual(sample.map((_, i) => String(i)))
      }
    }
  } finally { await db.close() }
}, 120000)
