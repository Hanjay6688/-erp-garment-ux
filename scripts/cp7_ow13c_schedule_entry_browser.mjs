import {cases as transportCases} from './cp7_ow13c_schedule_browser.mjs'
export function cases(ui,today){return transportCases(ui,today).map(([id,run])=>[
 id==='OW13C_SCHEDULE_BROWSER_DESKTOP_STALE_DIRTY'?'OW13C_SCHEDULE_ENTRY_DESKTOP_STALE_DIRTY':'OW13C_SCHEDULE_ENTRY_MOBILE_LOST_REPLY',run,
])}
