// BD (writer): runs the pages' own parsers over workspace JSON files the BD probe saved from real server reads:
//   bd_*      -> the Laundry page tab "Harga & tagihan" (src/laundryBd.ts)
//   import_*  -> the import page (src/ConnectedInitialImportPage.tsx, with the BD laundry claims and uninvoiced returns)
//   laundry_* -> the Laundry page (src/laundryQcModel.ts), read as the owner next to each owner BD read
//   laundryerror_* -> a Laundry/QC read that the server refused (always refused here)
// A page hides a read it cannot parse; this check makes that a probe failure (first missing: auditor scenario run
// 36206435863, where the owner's BD workspace sent released "0" for an unreleased opening record and the tab showed nothing).
// No exception: since owner decision D08 the pages accept any canonical UUID, so the F3 exception (seeded CP3 ids rewritten
// before parsing) is gone and every refusal fails. non_rfc_files counts the files that carry a canonical non RFC-4122 id
// (the chain's seeded CP3 rows: contractors a1000000-0000-..., model a2000000-0000-...) and were parsed as they are.
// usage: node scripts/cp6_bd_workspace_parse.mjs DIR [before|after]
//   -> one JSON line {files, kinds, non_rfc_files, refused:[{file,error}]}; exit 1 if refused (or, after BD, if no file).
import { build } from 'esbuild'
import { mkdtempSync, readdirSync, readFileSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const dir = process.argv[2], phase = process.argv[3] || 'after'
const bundle = await build({
  stdin: { contents: ["export { parseLaundryBdWorkspace } from './src/laundryBd'",
    "export { parseInitialImportWorkspace } from './src/ConnectedInitialImportPage'",
    "export { parseLaundryQcWorkspace } from './src/laundryQcModel'"].join('\n'), resolveDir: root, loader: 'ts' },
  bundle: true, platform: 'node', format: 'esm', write: false, loader: { '.css': 'empty' }, logLevel: 'warning',
})
const file = join(mkdtempSync(join(tmpdir(), 'cp6-bd-parse-')), 'parser.mjs')
writeFileSync(file, bundle.outputFiles[0].text)
const { parseLaundryBdWorkspace, parseInitialImportWorkspace, parseLaundryQcWorkspace } = await import(pathToFileURL(file).href)
const rfc = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
const uuidLike = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gi
const files = readdirSync(dir).filter(name => name.endsWith('.json')).sort()
const refused = [], kinds = { bd: 0, import: 0, laundry: 0 }
let nonRfc = 0
for (const name of files) {
  const kind = name.split('_')[0], text = readFileSync(join(dir, name), 'utf8'), value = JSON.parse(text)
  try {
    if (kind === 'bd') parseLaundryBdWorkspace(value)
    else if (kind === 'import') { if (!parseInitialImportWorkspace(value).batch) throw new Error('batch tidak terbaca') }
    else if (kind === 'laundry') { if (parseLaundryQcWorkspace(value).scope !== 'LAUNDRY') throw new Error('scope bukan LAUNDRY') }
    else if (kind === 'laundryerror') throw new Error('bacaan Laundry/QC ditolak server: ' + String(value.error))
    else throw new Error('jenis berkas tidak dikenal')
    kinds[kind] += 1
    if ((text.match(uuidLike) ?? []).some(id => !rfc.test(id))) nonRfc += 1
  } catch (error) { refused.push({ file: name, error: String(error) }) }
}
console.log(JSON.stringify({ files: files.length, kinds, non_rfc_files: nonRfc, refused }))
process.exit(refused.length || (phase === 'after' && !files.length) ? 1 : 0)
