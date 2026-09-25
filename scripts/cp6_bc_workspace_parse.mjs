// BC (writer): runs the pages' own parsers over workspace JSON files the BC probe saved from real server reads:
//   import_*  -> the import page (src/ConnectedInitialImportPage.tsx, with the BC accessory collections)
//   service_* -> Gudang · Aksesori (src/accessoryService.ts)
//   note_*    -> Nota Ambil Aksesori (src/accessoryIssue.ts)
// A page hides a read it cannot parse; this check makes that a probe failure. The only named exception is the pre-existing
// finding F3: the note page refuses a read whose active contractors include ids that are not RFC-4122 (the chain's seeded
// CP3 contractors a1000000-0000-...). Such a file is counted as f3_seed_ids only when it parses once those seeded
// contractors are left out; anything else is refused. Phase before only (no BC): the pre-existing finding F4 (BB's import read
// sends reversible=null for an opening settlement paid from an advance, and the page refuses the batch) is counted as
// f4_null_reversible when the read parses once those nulls are read as false; after BC (which fixes F4) it is refused.
// usage: node scripts/cp6_bc_workspace_parse.mjs DIR [before|after]
//   -> one JSON line {files, kinds, f3_seed_ids, f4_null_reversible, refused:[{file,error}]}; exit 1 if refused.
import { build } from 'esbuild'
import { mkdtempSync, readdirSync, readFileSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const dir = process.argv[2], phase = process.argv[3] || 'after'
const bundle = await build({
  stdin: { contents: ["export { parseInitialImportWorkspace } from './src/ConnectedInitialImportPage'",
    "export { parseAccessoryServiceWorkspace } from './src/accessoryService'",
    "export { parseAccessoryWorkspace } from './src/accessoryIssue'"].join('\n'), resolveDir: root, loader: 'ts' },
  bundle: true, platform: 'node', format: 'esm', write: false, loader: { '.css': 'empty' }, logLevel: 'warning',
})
const file = join(mkdtempSync(join(tmpdir(), 'cp6-bc-parse-')), 'parser.mjs')
writeFileSync(file, bundle.outputFiles[0].text)
const { parseInitialImportWorkspace, parseAccessoryServiceWorkspace, parseAccessoryWorkspace } = await import(pathToFileURL(file).href)
const rfc = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
const files = readdirSync(dir).filter(name => name.endsWith('.json')).sort()
const refused = [], kinds = { import: 0, service: 0, note: 0 }
let f3 = 0, f4 = 0
for (const name of files) {
  const kind = name.split('_')[0], value = JSON.parse(readFileSync(join(dir, name), 'utf8'))
  try {
    if (kind === 'import') {
      try { if (!parseInitialImportWorkspace(value).batch) throw new Error('batch tidak terbaca') }
      catch (error) {
        const balances = value?.batch?.opening_balances ?? []
        const nulls = balances.flatMap(b => b.settlements ?? []).filter(x => x.reversible === null)
        if (phase !== 'before' || !nulls.length) throw error
        const fixed = structuredClone(value)
        for (const b of fixed.batch.opening_balances) for (const x of b.settlements ?? []) if (x.reversible === null) x.reversible = false
        if (!parseInitialImportWorkspace(fixed).batch) throw error
        f4 += 1
      }
    }
    else if (kind === 'service') parseAccessoryServiceWorkspace(value)
    else if (kind === 'note') {
      try { parseAccessoryWorkspace(value) }
      catch (error) {
        const seeded = (value.contractors ?? []).filter(c => !rfc.test(String(c.id)))
        if (!seeded.length) throw error
        parseAccessoryWorkspace({ ...value, contractors: value.contractors.filter(c => rfc.test(String(c.id))) })
        f3 += 1
      }
    } else throw new Error('jenis berkas tidak dikenal')
    kinds[kind] += 1
  } catch (error) { refused.push({ file: name, error: String(error) }) }
}
console.log(JSON.stringify({ files: files.length, kinds, f3_seed_ids: f3, f4_null_reversible: f4, refused }))
process.exit(refused.length || !files.length ? 1 : 0)
