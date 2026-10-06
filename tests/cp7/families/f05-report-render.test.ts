// @vitest-environment node
import { expect, test } from 'vitest'
import { openRuntime } from './f04/runtime.mjs'
import { assemblyInput, run, uid } from './f04/analysis-assembly-fixture.mjs'
import { installRenderControls, outcomeSql } from './f04/report-render-fixture.mjs'

const finance = { report: { snapshot: { data_confidence: { blockers: [{ reason: 'HPP belum final', scope: 'PO-1', impact_date: '2026-10-01', reference: { kind: 'PO', id: uid(5) } }, { reason: 'Kas', scope: 'ALL', impact_date: null, reference: null }] } } } }

test('P19 report_render with grouped labels equals the predecessor text, refusal and order', async () => {
 const db = await openRuntime({ commandTimeoutMs: 600_000 })
 try {
  await installRenderControls(db)
  let compared = 0
  for (let seed = 1; seed <= 16; seed++) {
   for (const count of [0, 1, seed % 6 + 2]) {
    const c = assemblyInput(count, seed)
    if (seed % 4 === 0 && count > 1) c.facts.products.pop()   // a recommendation without its label
    for (const kind of ['DAILY', 'PERIOD', 'EXCEPTIONS', 'ARCHIVE']) {
     const row = (await db.query(`with o as materialized(select ${outcomeSql(c, seed % 3 ? null : finance)} e)
      select public.p19_render_state_0(e,'${kind}','Laporan ✓ ${seed}') s0,public.p19_render_state_1(e,'${kind}','Laporan ✓ ${seed}') s1,
       case when public.p19_render_state_0(e,'${kind}','x')='NO_ERROR' then public.p19_render_0(e,'${kind}','Laporan ✓ ${seed}')=public.p19_render_1(e,'${kind}','Laporan ✓ ${seed}') end same from o`))[0]
     expect(row.s1).toBe(row.s0)
     if (row.s0 === 'NO_ERROR') { expect(row.same).toBe(true); compared++ }
    }
   }
  }
  expect(compared).toBeGreaterThan(150)
  // A duplicated label key for a visited recommendation refuses identically.
  // The compiler itself refuses duplicate products, so the label is duplicated in the outcome.
  const duplicate = (await db.query(`with o as materialized(select jsonb_set(e,'{product_labels}',(e->'product_labels')||jsonb_build_array(e->'product_labels'->0)) e
    from(select ${outcomeSql(assemblyInput(3, 5))} e)x)
   select public.p19_render_state_0(e,'DAILY','x') s0,public.p19_render_state_1(e,'DAILY','x') s1 from o`))[0]
  expect(duplicate).toEqual({ s0: '21000', s1: '21000' })
  // The comparison sees a real text difference.
  const changed = (await db.query(`with o as materialized(select ${outcomeSql(assemblyInput(3, 5))} e)
   select public.p19_render_0(e,'DAILY','A')=public.p19_render_1(e,'DAILY','B') same from o`))[0]
  expect(changed.same).toBe(false)
  expect(run).toMatch(/^[0-9a-f-]{36}$/)
 } finally { await db.close() }
}, 600_000)
