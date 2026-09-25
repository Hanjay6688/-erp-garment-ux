// BB (writer): runs the import page's own workspace parser (src/ConnectedInitialImportPage.tsx, bundled as is) over workspace
// JSON files the BB probe saved from real server reads. The page parser fails closed on any field it cannot read, which
// hides the whole batch; this check makes that a probe failure instead of a browser-only surprise (found by the auditor
// runtime browser mode: reserved_amount '0' and a voided credit's remaining '0' hid every batch with an opening balance).
// usage: node scripts/cp6_bb_workspace_parse.mjs DIR  -> prints one JSON line {files, refused:[{file,error}]}; exit 1 if refused.
import { build } from 'esbuild'
import { mkdtempSync, readdirSync, readFileSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const dir = process.argv[2]
const bundle = await build({
  stdin: { contents: "export { parseInitialImportWorkspace } from './src/ConnectedInitialImportPage'", resolveDir: root, loader: 'ts' },
  bundle: true, platform: 'node', format: 'esm', write: false, loader: { '.css': 'empty' }, logLevel: 'warning',
})
const file = join(mkdtempSync(join(tmpdir(), 'cp6-bb-parse-')), 'parser.mjs')
writeFileSync(file, bundle.outputFiles[0].text)
const { parseInitialImportWorkspace } = await import(pathToFileURL(file).href)
const files = readdirSync(dir).filter(name => name.endsWith('.json')).sort()
const refused = []
for (const name of files) {
  try {
    const workspace = parseInitialImportWorkspace(JSON.parse(readFileSync(join(dir, name), 'utf8')))
    if (!workspace.batch) throw new Error('batch tidak terbaca')
  } catch (error) { refused.push({ file: name, error: String(error) }) }
}
console.log(JSON.stringify({ files: files.length, refused }))
process.exit(refused.length || !files.length ? 1 : 0)
