// Preserve R8 rev6 valid-UUID positive control and unknown/refetch case for QC.
import { cases as frozenCases } from '../unknown_round8/gpt_unknown_browser_rev6.mjs'

export async function cases(ui, today) {
  return (await frozenCases(ui, today)).filter(([id]) => id.startsWith('G8UI:UNKNOWN:QC_'))
    .map(([id, run]) => [id, async () => {
      const observed = await run()
      if (!id.includes('INITIAL_READ') || observed.status !== 'PASS') return observed
      const kpi = observed.primary
      const strictUnknown = kpi?.value?.trim() === '—'
        && kpi?.text?.includes('belum diketahui')
      return { ...observed, status: strictUnknown ? 'PASS' : 'COUNTEREXAMPLE', strict_unknown_kpi: strictUnknown }
    }])
}
