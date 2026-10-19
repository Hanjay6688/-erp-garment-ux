// Genuine tool qualification; stable case IDs, original results remain separate.
import {cases as ordinaryCases} from './journey_observer_q2_browser.mjs'
import {cases as claimCases} from './claim_observer_q2_browser.mjs'
export function cases(ui,today){return [...ordinaryCases(ui,today),...claimCases(ui,today)]}
