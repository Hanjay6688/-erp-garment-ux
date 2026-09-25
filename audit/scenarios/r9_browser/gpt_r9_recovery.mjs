// Frozen R8 recovery oracle, restricted to the two commit reply loss cases.
import { cases as frozenCases } from '../recovery_round8/gpt_recovery_browser.mjs'

export async function cases(ui, today) {
  return (await frozenCases(ui, today)).filter(([id]) => id.startsWith('G8UI:RECOVERY:'))
}
