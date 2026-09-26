// Run the real UI parsers against unmodified native server responses captured by the BE writer probe.
import { build } from 'esbuild'
import { mkdtempSync, readdirSync, readFileSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const bundle = await build({ stdin: { contents: "export { parseConversionWorkspace, validateConversionResult } from './src/productConversion'; export { parseLaundryBdWorkspace } from './src/laundryBd'; export { parsePocketOpening } from './src/pocketOpening'", resolveDir: root, loader: 'ts' }, bundle: true, platform: 'node', format: 'esm', write: false })
const file = join(mkdtempSync(join(tmpdir(), 'cp6-be-parse-')), 'parser.mjs'); writeFileSync(file, bundle.outputFiles[0].text)
const parser = await import(pathToFileURL(file).href), refused = []
const files = readdirSync(process.argv[2]).filter(x => x.endsWith('.json')).sort()
for (const name of files) {
  const value = JSON.parse(readFileSync(join(process.argv[2], name), 'utf8'))
  try {
    if (name.startsWith('be_')) parser.parseConversionWorkspace(value)
    else if (name.startsWith('bd_')) parser.parseLaundryBdWorkspace(value)
    else if (name.startsWith('pocket_')) { if (parser.parsePocketOpening(value) === null) throw new Error('Missing BE pocket extension') }
    else if (name.startsWith('response_')) parser.validateConversionResult(value.result, value.action, value.request, value.payload)
    else throw new Error('Unrecognised snapshot')
  } catch (error) { refused.push({ file: name, error: String(error) }) }
}
console.log(JSON.stringify({ files: files.length, refused })); process.exit(refused.length || !files.length ? 1 : 0)
