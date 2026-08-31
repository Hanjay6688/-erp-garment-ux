import { lstatSync, readFileSync, readdirSync } from 'node:fs'
import { relative, resolve, sep } from 'node:path'
import { pathToFileURL } from 'node:url'
import { JSDOM } from 'jsdom'
import { assertUatAuthBuildEnvironment } from './assert-uat-auth-env.mjs'
import { scanClientArtifacts } from './scan-client-artifacts.mjs'

const runtimeMarkers = [
  'VITE_ERP_RUNTIME_MODE:',
  'VITE_SUPABASE_URL:',
  'VITE_SUPABASE_PUBLISHABLE_KEY:',
  'VITE_SUPABASE_ANON_KEY:',
]

export class UatAuthArtifactError extends Error {
  constructor(code, message) {
    super(message)
    this.name = 'UatAuthArtifactError'
    this.code = code
  }
}

function fail(code, message) {
  throw new UatAuthArtifactError(code, message)
}

function isWithin(root, path) {
  const relativePath = relative(root, path)
  return relativePath !== '..' && !relativePath.startsWith(`..${sep}`) && !relativePath.startsWith(sep)
}

function javascriptFilesUnder(path, root) {
  if (!isWithin(root, path)) fail('UAT_ARTIFACT_PATH_ESCAPE', 'Artifact content must remain inside the selected directory.')
  const entry = lstatSync(path)
  if (entry.isSymbolicLink()) {
    fail('UAT_ARTIFACT_SYMLINK_FORBIDDEN', 'Symbolic links are forbidden in the deployable UAT Auth artifact.')
  }
  if (entry.isFile()) return path.endsWith('.js') ? [path] : []
  if (!entry.isDirectory()) return []
  return readdirSync(path).flatMap((name) => javascriptFilesUnder(resolve(path, name), root))
}

function moduleEntrypoints(indexHtml, root) {
  const entrypoints = []
  let document
  let dom
  try {
    dom = new JSDOM(indexHtml)
    document = dom.window.document
  } catch {
    fail('UAT_ARTIFACT_INDEX_INVALID', 'UAT Auth index.html must be parseable HTML.')
  }
  const sources = [...document.head.querySelectorAll('script[src]')]
    .filter((script) => script.getAttribute('type')?.trim().toLowerCase() === 'module')
    .map((script) => script.getAttribute('src'))
  dom.window.close()

  for (const source of sources) {
    if (
      source.startsWith('//')
      || source.includes('\\')
      || /^[a-z][a-z0-9+.-]*:/i.test(source)
      || /[?#]/.test(source)
    ) {
      fail('UAT_ARTIFACT_ENTRYPOINT_INVALID', 'Module entrypoints must use local, query-free artifact paths.')
    }
    const entrypoint = source.startsWith('/')
      ? resolve(root, `.${source}`)
      : resolve(root, source)
    if (!isWithin(root, entrypoint)) {
      fail('UAT_ARTIFACT_PATH_ESCAPE', 'Module entrypoints must remain inside the selected artifact directory.')
    }
    entrypoints.push(entrypoint)
  }
  return entrypoints
}

function occurrenceCount(content, value) {
  return content.split(value).length - 1
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function stringLiteralPattern(value) {
  const escaped = escapeRegExp(value)
  return `(?:"${escaped}"|'${escaped}'|\`${escaped}\`)`
}

export function assertUatAuthArtifact(rootPath, environment = process.env) {
  const expected = assertUatAuthBuildEnvironment(environment)
  const resolvedRoot = resolve(rootPath)
  let javascriptFiles
  let indexHtml
  try {
    const rootEntry = lstatSync(resolvedRoot)
    if (rootEntry.isSymbolicLink()) {
      fail('UAT_ARTIFACT_SYMLINK_FORBIDDEN', 'The UAT Auth artifact root cannot be a symbolic link.')
    }
    if (!rootEntry.isDirectory()) {
      fail('UAT_ARTIFACT_UNREADABLE', 'UAT Auth artifact path must be a directory.')
    }
    javascriptFiles = javascriptFilesUnder(resolvedRoot, resolvedRoot)
    const indexPath = resolve(resolvedRoot, 'index.html')
    const indexEntry = lstatSync(indexPath)
    if (indexEntry.isSymbolicLink() || !indexEntry.isFile()) {
      fail('UAT_ARTIFACT_INDEX_INVALID', 'UAT Auth artifact requires a regular, non-symlink index.html.')
    }
    indexHtml = readFileSync(indexPath, 'utf8')
  } catch (error) {
    if (error instanceof UatAuthArtifactError) throw error
    fail('UAT_ARTIFACT_UNREADABLE', 'UAT Auth artifact directory is missing or unreadable.')
  }
  if (javascriptFiles.length === 0) {
    fail('UAT_ARTIFACT_JS_MISSING', 'UAT Auth artifact contains no JavaScript bundle.')
  }

  const bundles = javascriptFiles.map((file) => ({ file, content: readFileSync(file, 'utf8') }))
  const runtimeBundles = bundles.filter(({ content }) => runtimeMarkers.every((marker) => content.includes(marker)))
  if (runtimeBundles.length !== 1) {
    fail('UAT_ARTIFACT_RUNTIME_AMBIGUOUS', 'Expected exactly one bundle containing the four explicit runtime inputs.')
  }

  const entrypoints = moduleEntrypoints(indexHtml, resolvedRoot)
  if (entrypoints.length === 0) {
    fail('UAT_ARTIFACT_ENTRYPOINT_MISSING', 'index.html contains no local JavaScript module entrypoint.')
  }
  if (!entrypoints.includes(runtimeBundles[0].file)) {
    fail('UAT_ARTIFACT_RUNTIME_NOT_ENTRYPOINT', 'The reviewed runtime bundle must be loaded directly by index.html.')
  }

  const runtimeContent = runtimeBundles[0].content
  for (const marker of runtimeMarkers) {
    if (occurrenceCount(runtimeContent, marker) !== 1) {
      fail('UAT_ARTIFACT_RUNTIME_AMBIGUOUS', 'A runtime input marker is missing or duplicated in the client bundle.')
    }
  }

  const positions = runtimeMarkers.map((marker) => runtimeContent.indexOf(marker))
  if (!positions.every((position, index) => index === 0 || position > positions[index - 1])) {
    fail('UAT_ARTIFACT_RUNTIME_ORDER_INVALID', 'Runtime inputs are not emitted in the reviewed deterministic order.')
  }

  const modeSegment = runtimeContent.slice(positions[0] + runtimeMarkers[0].length, positions[1])
  const urlSegment = runtimeContent.slice(positions[1] + runtimeMarkers[1].length, positions[2])
  const keySegment = runtimeContent.slice(positions[2] + runtimeMarkers[2].length, positions[3])
  const anonSegment = runtimeContent.slice(positions[3] + runtimeMarkers[3].length, positions[3] + runtimeMarkers[3].length + 64)

  if (!modeSegment.includes(expected.mode) || modeSegment.includes('void 0')) {
    fail('UAT_ARTIFACT_MODE_MISMATCH', 'Client artifact is not pinned to UAT_AUTH_SIMULATION.')
  }
  if (!urlSegment.includes(expected.supabaseUrl) || urlSegment.includes('void 0')) {
    fail('UAT_ARTIFACT_TARGET_MISMATCH', 'Client artifact is not pinned to the exact ERP Enteng endpoint.')
  }
  if (!keySegment.includes(expected.publishableKey) || keySegment.includes('void 0')) {
    fail('UAT_ARTIFACT_BROWSER_KEY_MISSING', 'Client artifact does not contain the selected browser-safe publishable key.')
  }
  if (!/^\s*(?:void 0|undefined)\s*[,}]/.test(anonSegment)) {
    fail('UAT_ARTIFACT_LEGACY_KEY_PRESENT', 'Legacy anon-key input must remain undefined in the dedicated artifact.')
  }

  const exactRuntimeObjectPattern = new RegExp([
    '\\{\\s*',
    `VITE_ERP_RUNTIME_MODE\\s*:\\s*${stringLiteralPattern(expected.mode)}\\s*,\\s*`,
    `VITE_SUPABASE_URL\\s*:\\s*${stringLiteralPattern(expected.supabaseUrl)}\\s*,\\s*`,
    `VITE_SUPABASE_PUBLISHABLE_KEY\\s*:\\s*${stringLiteralPattern(expected.publishableKey)}\\s*,\\s*`,
    'VITE_SUPABASE_ANON_KEY\\s*:\\s*(?:void\\s+0|undefined)\\s*\\}',
  ].join(''))
  if (!exactRuntimeObjectPattern.test(runtimeContent)) {
    fail(
      'UAT_ARTIFACT_RUNTIME_VALUES_INVALID',
      'Runtime inputs must be emitted as one direct object with the reviewed values.',
    )
  }

  const allJavascript = bundles.map(({ content }) => content).join('\n')
  if (occurrenceCount(allJavascript, expected.publishableKey) !== 1) {
    fail('UAT_ARTIFACT_BROWSER_KEY_AMBIGUOUS', 'Publishable key must be emitted exactly once in the client artifact.')
  }

  const secretFindings = scanClientArtifacts(resolvedRoot)
  if (secretFindings.length > 0) {
    fail('UAT_ARTIFACT_SECRET_SCAN_FAILED', 'Client artifact contains a forbidden server credential pattern.')
  }

  return Object.freeze({ javascriptFileCount: javascriptFiles.length, runtimeBundle: runtimeBundles[0].file })
}

const invokedDirectly = process.argv[1]
  && import.meta.url === pathToFileURL(resolve(process.argv[1])).href
if (invokedDirectly) {
  const rootPath = process.argv[2]
  if (!rootPath) fail('UAT_ARTIFACT_PATH_REQUIRED', 'Usage: node scripts/assert-uat-auth-artifact.mjs <directory>')
  const result = assertUatAuthArtifact(rootPath)
  console.log(`UAT Auth artifact identity passed across ${result.javascriptFileCount} JavaScript file(s); browser key value not printed.`)
}
