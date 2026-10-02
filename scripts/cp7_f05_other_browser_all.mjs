import{cases as predecessorCases}from'./cp7_f05_attention_browser.mjs'
import{cases as obligationCases}from'./cp7_f05_other_browser.mjs'
export function cases(ui,today){return[...predecessorCases(ui,today),...obligationCases(ui,today)]}
