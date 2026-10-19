// Genuine UI form-state repair and read-only claim dialog diagnostics.
import {cases as ordinaryCases} from './journey_form_q3_browser.mjs'
import {cases as claimCases} from './claim_form_q3_browser.mjs'
export function cases(ui,today){return [...ordinaryCases(ui,today),...claimCases(ui,today)]}
