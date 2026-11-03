import assert from 'node:assert/strict'
import {expectedKeys as baseKeys,key} from './coverage-polish.mjs'
export {key}
export const extraKeys=['after/movements-vivo-expanded/390','after/movements-vivo-expanded/1440']
export const expectedKeys=config=>baseKeys(config).concat(extraKeys).sort()
export function validateCoverage(variants,config){const actual=variants.map(key).sort();assert.equal(new Set(actual).size,actual.length,'No duplicate view identities');assert.deepEqual(actual,expectedKeys(config),'Exact328 route/state/expanded/filter identities required');return {expected:328,actual:actual.length,dialog_views:variants.filter(x=>x.variant==='after'&&['ready','long','empty','loading','error','stale','approved','review','pending'].some(s=>x.surface==='mandor-'+s)).length}}
