// PL-8 supply normalization: exact predecessor normalize_production (and its
// normalize_cutting, settle_bs, reconcile) vs the linear form on generated
// captures of spent cutting groups (every piece FG). Byte equality is required
// for every compared size; the largest sizes run the linear form only. Above
// 1000 groups the unchanged 1000-pool graph limit refuses (CP7_WIP_LIMIT).
import { mkdirSync, writeFileSync } from 'node:fs'
import { dirname } from 'node:path'
import { openRuntime, jsonArg } from '../tests/cp7/families/f04/runtime.mjs'
import { installWipControls, productionInput, wipBase } from '../tests/cp7/families/f04/wip-normalize-fixture.mjs'
const out = process.argv[2] ?? 'test-results/cp7-shell-proof/P19_WIP_NORMALIZE_KERNEL.json'
const db = await openRuntime({ commandTimeoutMs: 600_000 })
const report = { contract: 'cp7.p19.wip-normalize-kernel.v1', predecessor: wipBase, entry: 'cp7_wip.normalize_production', compared: [], linear_only: [], status: 'INCOMPLETE', production_go: false }
try {
  await installWipControls(db)
  // [spent groups, positions per size, lifecycle groups (with opening and
  // unsourced origins), compare with predecessor]. 1000 one-size groups are
  // exactly the 1000-pool graph limit; 2000 must refuse with CP7_WIP_LIMIT.
  const sizes = [[50, 2, 0, true], [250, 2, 0, true], [500, 2, 0, true], [250, 4, 0, true], [200, 2, 60, true], [1000, 2, 0, false], [1000, 4, 0, false], [2000, 2, 0, false]]
  for (const [i, [spent, positionsPerSize, groups, compare]] of sizes.entries()) {
    await db.execute(`insert into public.wn_in values(${i},${jsonArg(productionInput(9000 + i, { groups, exhaustedGroups: spent, positionsPerSize, other: groups > 0 }))})`)
    const run = async fn => ({ groups: spent + groups, spent_groups: spent, positions_per_size: positionsPerSize, ...(await db.query(`select public.wn_run('${fn}',c) r from public.wn_in where n=${i}`))[0].r })
    const now = await run('cp7_wip.normalize_production')
    if (compare) {
      const old = await run('cp7_wip.normalize_production_0')
      if (old.state !== now.state || old.md5 !== now.md5 || old.utf8_bytes !== now.utf8_bytes) throw new Error(`PL8_WIP_NORMALIZE_NOT_IDENTICAL ${JSON.stringify({ old, now })}`)
      if (now.status !== 'COMPLETE') throw new Error(`PL8_WIP_NORMALIZE_BENCH_NOT_EXERCISED ${JSON.stringify(now)}`)
      report.compared.push({ old, new: now, identical: true, speedup: Math.round(old.ms / Math.max(now.ms, 0.1) * 10) / 10 })
      console.log(JSON.stringify(report.compared.at(-1)))
    } else {
      const expected = spent + groups > 1000 ? '54000:CP7_WIP_LIMIT' : 'NO_ERROR'
      if (now.state !== expected || (expected === 'NO_ERROR' && now.status !== 'COMPLETE')) throw new Error(`PL8_WIP_NORMALIZE_LINEAR_UNEXPECTED ${JSON.stringify(now)}`)
      report.linear_only.push(now); console.log(JSON.stringify(now))
    }
  }
  report.status = 'COMPLETE'
} finally {
  await db.close(); mkdirSync(dirname(out), { recursive: true }); writeFileSync(out, JSON.stringify(report, null, 1)); console.log(JSON.stringify({ status: report.status, out }))
}
