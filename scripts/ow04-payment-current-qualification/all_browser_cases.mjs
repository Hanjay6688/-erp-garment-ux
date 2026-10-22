import{cases as retained}from'../ow04-consumer-ui-qualification/browser_cases.mjs'
import{cases as source}from'../ow04-source-inverse-ui-qualification/browser_cases.mjs'
import{cases as current,positiveCases}from'./browser_cases.mjs'
export function cases(ui,today){return[...retained(ui,today),...source(ui,today),...current(ui,today),...positiveCases(ui,today)]}
