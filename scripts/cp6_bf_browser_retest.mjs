import { resolve } from 'node:path'
import { pathToFileURL } from 'node:url'
const { freeMaster } = await import(pathToFileURL(resolve('scripts/cp6_bf_free_browser.mjs')).href)
export async function cases(ui,today){return [
 ['SKU01_BROWSER:FREE_WAIVED_DESKTOP_SAVE_RELOAD',()=>freeMaster(ui,false)],
 ['SKU01_BROWSER:FREE_WAIVED_MOBILE_SAVE_RELOAD',()=>freeMaster(ui,true)],
]}
