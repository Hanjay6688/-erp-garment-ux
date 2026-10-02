import{cases as previous}from'./cp7_f05_other_browser_all.mjs'
import{cases as reports}from'./cp7_f05_obligation_report_browser.mjs'
export function cases(ui,today){return[...previous(ui,today),...reports(ui,today)]}
