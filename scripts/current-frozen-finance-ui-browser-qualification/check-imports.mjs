import assert from 'node:assert/strict'
import{cases as desktop}from'./desktop.mjs'
import{cases as mobile}from'./mobile.mjs'
const rows=[...await desktop({},'2026-10-26'),...await mobile({},'2026-10-26')];assert.deepEqual(rows.map(x=>x[0]),["A_FROZEN_FINANCE_BROWSER_DESKTOP_REAL_AUTH_LOST_REPLY_REPLAY_OFFICIAL24", "A_FROZEN_FINANCE_BROWSER_MOBILE_REAL_AUTH_BLOCKED_REPORT_ACCESS_REVOKED"]);assert.ok(rows.every(x=>typeof x[1]==='function'));console.log(JSON.stringify({status:'PASS',cases:2,actual_ESM_modules_loaded:2,browser_executed:false}))
