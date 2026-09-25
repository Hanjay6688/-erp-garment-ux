// Frozen R8 oracle, with rev2 UI selectors/retry button adapted for d1bc8ad.
import { cases as frozenCases } from './gpt_r9_recovery_cases_rev2.mjs'

export async function cases(ui, today) {
  return (await frozenCases(ui, today)).filter(([id]) => id.startsWith('G8UI:RECOVERY:'))
}
