import {readFileSync} from 'node:fs'
import {createHash} from 'node:crypto'
import assert from 'node:assert/strict'
const manifest=JSON.parse(readFileSync(new URL('./MANIFEST.json',import.meta.url)))
export async function cases(ui,today){const all=[];for(const [file,spec]of Object.entries(manifest.retained_browser_modules)){const url=new URL('../../scripts/'+file,import.meta.url);assert.equal(createHash('sha256').update(readFileSync(url)).digest('hex'),spec.sha256);const module=await import(url.href),rows=await module.cases(ui,today);for(const id of spec.ids){const row=rows.find(([key])=>key===id);assert.ok(row,'Missing frozen case '+id);all.push([id,async()=>({...await row[1](),evidence_origin:'INDEPENDENT_EXECUTION_WRITER_ORACLE',source:file})]);}}assert.equal(all.length,manifest.retained_case_count);return all}
