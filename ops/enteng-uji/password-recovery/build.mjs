// Run against a fresh unpacking of Enteng_Uji_Worker_20261127.zip.
import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { copyFile, mkdir, readFile, writeFile } from 'node:fs/promises'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { build } from 'esbuild'

const source = dirname(fileURLToPath(import.meta.url))
const release = resolve(process.argv[2] ?? '')
const key = process.env.UJI_PUBLISHABLE_KEY ?? ''
assert.match(key, /^sb_publishable_[A-Za-z0-9_-]+$/)
const hash = data => createHash('sha256').update(data).digest('hex')
const manifestFile = join(release, 'asset-manifest.json')
const manifestBytes = await readFile(manifestFile)
assert.equal(hash(manifestBytes), 'd25dfcf3f01fc37cf6fbafe3051b8b65076db1eb001ca0a6461abafd9d6fe0a4')
assert.equal(hash(await readFile(join(release, 'wrangler.jsonc'))), 'f7a3db0958e7455445f247f034e319843522bfa7c8962105f9a72782601d49ab')
assert.equal(hash(await readFile(join(release, 'deploy.mjs'))), 'f03a399ccba7b02104b09169ac924d8c0d1d347d7f905fdfd293bbef77037b75')
const manifest = JSON.parse(manifestBytes)
for (const item of manifest) assert.equal(hash(await readFile(join(release, item.path))), item.sha256)
const route = 'dist/auth/atur-sandi'
const output = join(release, route)
await mkdir(dirname(output), { recursive: true })
await mkdir(output)
await copyFile(join(source, 'index.html'), join(output, 'index.html'))
await copyFile(join(source, 'page.css'), join(output, 'page.css'))
await build({
  entryPoints: [join(source, 'page.mjs')], bundle: true, format: 'esm', minify: true,
  platform: 'browser', target: 'es2022', outfile: join(output, 'page.js'),
  legalComments: 'inline', define: { __UJI_PUBLISHABLE_KEY__: JSON.stringify(key) },
})
const headers = '/auth/atur-sandi/*\n  Cache-Control: no-store\n  Referrer-Policy: no-referrer\n  X-Frame-Options: DENY\n  X-Content-Type-Options: nosniff\n'
await writeFile(join(release, 'dist/_headers'), headers, { flag: 'wx' })
for (const path of ['dist/_headers', ...['index.html','page.css','page.js'].map(name => route + '/' + name)]) {
  manifest.push({ path, sha256: hash(await readFile(join(release, path))) })
}
manifest.sort((a, b) => a.path < b.path ? -1 : a.path > b.path ? 1 : 0)
await writeFile(manifestFile, JSON.stringify(manifest, null, 2) + '\n')
console.log('Verified 167 original assets and packaged the isolated Uji recovery page.')
