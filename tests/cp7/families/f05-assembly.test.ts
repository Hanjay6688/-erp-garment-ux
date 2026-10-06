// @vitest-environment node
import { expect, test } from 'vitest'
import { openRuntime } from './f04/runtime.mjs'
import { assemblyArgs, assemblyInput, compareAssembly, installAssemblyControls } from './f04/analysis-assembly-fixture.mjs'

test('P19 full assembler preserves every predecessor field, row order, assumptions and refusal', async () => {
 const db = await openRuntime()
 try {
  await installAssemblyControls(db)
  for (let seed = 1; seed <= 24; seed++) {
   for (const count of [0, 1, seed % 7 + 2]) expect((await compareAssembly(db, assemblyInput(count, seed))).same).toBe(true)
  }
  for (const field of ['sql_null_accessory', 'sql_null_fabric']) {
   const c = assemblyInput(3, 5);c.test_netting.rows[0].production_policy.policy.state = 'ACTIVE';c.test_netting.rows[0][field] = true
   const result = await compareAssembly(db, c)
   expect(result.same).toBe(true);expect(result.material_null).toBe(true)
  }
  for (const part of ['products', 'stock', 'history']) {
   const c = assemblyInput(3, 5);c.test_netting.rows[0].production_policy.policy.state = 'ACTIVE'
   const h = c.test_netting.schedule_run_result.supply_run_result.baseline_run_result.history_run_result
   const rows = part === 'products' ? c.facts.products : part === 'stock' ? h.current_stock : h.history.rows
   rows.push(structuredClone(rows[0]))
   for (const name of ['p19_state_0', 'p19_state_1']) expect((await db.query(`select public.${name}(${assemblyArgs(c)}) state`))[0].state).toBe('21000')
  }
  const unknown = assemblyInput(3, 3)
  unknown.test_netting.rows.forEach((r: { production_policy: { policy: { state: null | string } } }) => { r.production_policy.policy.state = null })
  unknown.test_netting.allocation.allocation.edges = []
  unknown.facts.products.push(structuredClone(unknown.facts.products[0]))
  const result = await compareAssembly(db, unknown)
  expect(result.same).toBe(true);expect(result.recommendations).toBe(0);expect(result.warnings).toBe(6)
  // The same comparison must detect a real payload difference.
  await db.execute(`create function public.p19_wrong(c jsonb,q jsonb,p uuid,a jsonb)returns jsonb language sql as $$select public.p19_assembly_1(c,q,p,a)||jsonb_build_object('extra_field',true)$$;`)
  const args = assemblyArgs(assemblyInput(2, 5))
  expect((await db.query(`select public.p19_assembly_0(${args})::text=public.p19_wrong(${args})::text same`))[0].same).toBe(false)
 } finally { await db.close() }
}, 120000)
