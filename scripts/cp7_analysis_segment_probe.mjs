// Independent diagnostic; no ERP product source is changed or installed.
// Native runtime is a disposable Unix-socket database. An explicit local WASM
// run is supported by the existing F04 runtime and is never Native/CI proof.
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs'
import { dirname } from 'node:path'
import { createHash } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import { openRuntime, textArg } from '../tests/cp7/families/f04/runtime.mjs'

const out = process.argv[2] ?? 'test-results/cp7-support/SEGMENT_CUT_PROBE.json'
const requestedSizes = process.argv.slice(3).map(Number)
const sizes = requestedSizes.length ? requestedSizes : [4000003, 16000003, 65000003, 210000003]
if (sizes.some(n => !Number.isSafeInteger(n) || n < 1 || n > 210000003)) throw new Error('Bad diagnostic character count')
const sourcePath = 'scripts/cp7-src/planning/analysis-jobs.sql'
const source = readFileSync(sourcePath, 'utf8')
if (!source.includes('part:=left(rest,n);rest:=right(rest,-n);')) throw new Error('Current source changed; re-review the probe before running it')
const db = await openRuntime({ commandTimeoutMs: 600000 })
const receipt = {
  scope: 'SEGMENT_CUT_DIAGNOSTIC_ONLY_NOT_PRODUCT_NOT_NATIVE_AUTH_BROWSER_ACCEPTANCE',
  runtime: db.flavor, version: db.version,
  source_head: execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim(),
  source_path: sourcePath, source_sha256: createHash('sha256').update(source).digest('hex'),
  parity: { comparisons: 0, passed: 0, mutants: [] }, benchmarks: [],
  statement_timeout: '8s', production_go: false, status: 'RUNNING',
}
const save = () => { mkdirSync(dirname(out), { recursive: true }); writeFileSync(out, JSON.stringify(receipt, null, 2) + '\n') }
const signature = r => JSON.stringify(r === null ? null : {
  parts: r.parts.map(p => [p.idx, p.characters, p.utf8_bytes, p.sha256]),
  characters: r.characters, utf8_bytes: r.utf8_bytes,
})
const compare = (a, b, label) => {
  receipt.parity.comparisons++
  if (signature(a) !== signature(b)) throw new Error('SEGMENT_PARITY_FAILED:' + label)
  receipt.parity.passed++
}
async function probe(bodySql, chunk, method) {
  // Native openRuntime starts a fresh psql session for each command. SET must
  // be in THIS command; a separate SET would not constrain the next session.
  const result = await db.execute(`set statement_timeout='8s';select coalesce(public.f04_segment_probe(${bodySql},${chunk},${textArg(method)})::text,'null') as result;`)
  return typeof result === 'string' ? JSON.parse(result.trim()) : JSON.parse(result.at(-1).rows[0].result)
}
try {
  await db.execute(readFileSync('tests/cp7/families/f04/segment-cut-probe.sql', 'utf8'))
  // An independent JavaScript code-point oracle pins exact chunk contents,
  // rather than comparing only two implementations that could share a bug.
  const bodies = [null, '', 'A', 'AB', '\n\r\t', 'é', '漢', '😀', 'e\u0301',
    'Aé漢😀\nB', '😀éA漢e\u0301'.repeat(41),
    JSON.stringify({ label: 'Kain 😀 ukuran 漢', refs: ['é', 'e\u0301'], pcs: '125' }),
  ]
  let random = 0x5e8bb513
  const alphabet = ['A', 'Z', 'é', '漢', '😀', '\n', '\u0301', '\t', ' ', '𐐷']
  for (let k = 0; k < 25; k++) {
    let body = ''
    for (let i = 0; i < 1 + k * 13; i++) { random = (Math.imul(random, 1664525) + 1013904223) >>> 0; body += alphabet[random % alphabet.length] }
    bodies.push(body)
  }
  for (const body of bodies) for (const chunk of [1, 2, 3, 7, 31, 199, 2000000]) {
    const sql = body === null ? 'null::text' : textArg(body)
    const ref = await probe(sql, chunk, 'REFERENCE')
    const current = await probe(sql, chunk, 'CURRENT')
    const candidate = await probe(sql, chunk, 'WINDOW')
    compare(ref, current, `current/${bodies.indexOf(body)}/${chunk}`)
    compare(ref, candidate, `window/${bodies.indexOf(body)}/${chunk}`)
    const points = body === null ? null : Array.from(body)
    const parts = points === null ? null : Array.from({ length: Math.ceil(points.length / chunk) }, (_, idx) => {
      const text = points.slice(idx * chunk, (idx + 1) * chunk).join('')
      return { idx, characters: Array.from(text).length, utf8_bytes: Buffer.byteLength(text), sha256: createHash('sha256').update(text).digest('hex') }
    })
    compare(ref, points === null ? null : { parts, characters: points.length, utf8_bytes: Buffer.byteLength(body) }, `codepoint-oracle/${bodies.indexOf(body)}/${chunk}`)
  }
  // Force the maximum UTF8 byte window to end inside a 2-, 3-, or 4-byte
  // character. Include combining marks and a non-BMP scalar. Chunk 2M
  // boundary cases also prove the exact production cut and final segment.
  for (const width of [1, 2, 3, 7, 2000000]) for (const scalar of ['é', '漢', '😀', '𐐷']) {
    const sql = `repeat('A',${4 * width - 1})||${textArg(scalar)}||repeat('Z',${width + 3})`
    const ref = await probe(sql, width, 'REFERENCE')
    compare(ref, await probe(sql, width, 'CURRENT'), `boundary/current/${width}/${scalar}`)
    compare(ref, await probe(sql, width, 'WINDOW'), `boundary/window/${width}/${scalar}`)
  }
  for (const method of ['BAD_SIZE', 'SKIP_LAST']) {
    const ref = await probe(textArg('Aé漢😀Z'.repeat(5)), 3, 'REFERENCE')
    const bad = await probe(textArg('Aé漢😀Z'.repeat(5)), 3, method)
    const caught = signature(ref) !== signature(bad)
    receipt.parity.mutants.push({ method, caught })
    if (!caught) throw new Error('WEAK_PROBE:' + method)
  }
  save()
  console.log(JSON.stringify({ parity: receipt.parity, runtime: db.flavor }))
  for (const chars of sizes) {
    const rows = []
    // A/B/B/A reduces simple warm-up bias. Large synthetic fixtures stay
    // inside the server; no full document is returned to Node/the browser.
    const bodySql = `repeat('A',${chars - 1})||'😀'`
    for (const method of ['CURRENT', 'WINDOW', 'WINDOW', 'CURRENT']) {
      try {
        const r = await probe(bodySql, 2000000, method)
        rows.push({ method, state: 'DONE', ...r })
      } catch (error) {
        const stopped = error.code === '57014' || /canceling statement due to statement timeout/.test(String(error.message))
        rows.push({ method, state: 'REFUSED', sqlstate: stopped ? '57014' : error.code ?? null, message: String(error.message).slice(0,300) })
        if (!stopped) throw error
      }
    }
    const done = rows.filter(r => r.state === 'DONE')
    // The benchmark fixture is known independently. Hash at most one 2M
    // ASCII chunk and its last A...emoji chunk in Node; never allocate the
    // full 210MB input. A survivor is checked against an independent oracle
    // even if the other method timed out.
    const fullHash = createHash('sha256').update('A'.repeat(2000000)).digest('hex')
    const count = Math.ceil(chars / 2000000)
    const expectedParts = Array.from({ length: count }, (_, idx) => {
      const length = Math.min(2000000, chars - idx * 2000000)
      const last = idx === count - 1
      return { idx, characters: length, utf8_bytes: length + (last ? 3 : 0),
        sha256: last ? createHash('sha256').update('A'.repeat(length - 1) + '😀').digest('hex') : fullHash }
    })
    const expected = { parts: expectedParts, characters: chars, utf8_bytes: chars + 3 }
    const identical = done.length ? done.every(r => signature(r) === signature(expected)) : null
    if (!identical) throw new Error('BENCHMARK_PARITY_FAILED:' + chars)
    receipt.benchmarks.push({ characters: chars, utf8_bytes: chars + 3, independent_pattern_oracle_match: identical,
      all_methods_completed: done.length === rows.length,
      rows: rows.map(({ parts, ...r }) => ({ ...r, segments: parts?.length, segment_metadata_sha256: parts ? createHash('sha256').update(JSON.stringify(parts)).digest('hex') : null })) })
    save()
    console.log(JSON.stringify(receipt.benchmarks.at(-1)))
  }
  receipt.status = 'COMPLETE'
} catch (error) {
  receipt.status = 'FAILED'; receipt.failure = String(error.stack ?? error); throw error
} finally {
  save(); await db.close()
}
