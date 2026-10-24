import {cases as work} from '../cp7_ow13c_bounded_entry_browser.mjs'
import {cases as quantity} from '../cp7_ow13c_quantity_browser.mjs'
export function cases(ui,today){return [...work(ui,today),...quantity(ui,today)]}
