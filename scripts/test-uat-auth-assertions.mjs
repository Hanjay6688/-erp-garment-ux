import assert from 'node:assert/strict'
import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { resolve } from 'node:path'
import { assertUatAuthArtifact } from './assert-uat-auth-artifact.mjs'
import {
  assertUatAuthBuildEnvironment,
  assertUatAuthReleaseEnvironment,
  ERP_ENTENG_PUBLISHABLE_KEY_SHA256,
  ERP_ENTENG_UAT_URL,
  UAT_AUTH_RUNTIME_MODE,
} from './assert-uat-auth-env.mjs'
import { assertUatAuthWranglerTarget, UAT_AUTH_WORKER_NAME } from './assert-uat-auth-target.mjs'
import {
  assertUatAuthWranglerAction,
  uatAuthWranglerArguments,
} from './run-uat-auth-wrangler.mjs'

const browserKey = 'sb_publishable_mock_12345678901234567890'
const validEnvironment = Object.freeze({
  VITE_ERP_RUNTIME_MODE: UAT_AUTH_RUNTIME_MODE,
  VITE_SUPABASE_URL: ERP_ENTENG_UAT_URL,
  VITE_SUPABASE_PUBLISHABLE_KEY: browserKey,
  ERP_UAT_AUTH_ALLOW_MOCK_KEY: '1',
})

assert.equal(UAT_AUTH_RUNTIME_MODE, 'UAT_AUTH_SIMULATION')
assert.equal(ERP_ENTENG_UAT_URL, 'https://siimvrusnzxexizpyoib.supabase.co')
assert.equal(ERP_ENTENG_PUBLISHABLE_KEY_SHA256, '4a393f01d18cf637ca1e38967790d4c76a2478d687335b6cb948a1bff8a017cf')
assert.equal(UAT_AUTH_WORKER_NAME, 'erp-garment-ux-uat-auth')
assert.equal(assertUatAuthWranglerAction(['deploy']), 'deploy')
assert.equal(assertUatAuthWranglerAction(['preview']), 'preview')
expectFailure(
  () => assertUatAuthWranglerAction(['deploy', '--name', 'erp-garment-ux']),
  'UAT_WRANGLER_ARGUMENTS_FORBIDDEN',
)
assert.deepEqual(uatAuthWranglerArguments('deploy', '/fixed/wrangler.jsonc'), [
  'deploy',
  '--env',
  'uat-auth',
  '--config',
  '/fixed/wrangler.jsonc',
])
assert.deepEqual(uatAuthWranglerArguments('preview', '/fixed/wrangler.jsonc'), [
  'versions',
  'upload',
  '--env',
  'uat-auth',
  '--config',
  '/fixed/wrangler.jsonc',
  '--preview-alias',
  'uat-auth',
])

function expectFailure(operation, code, forbiddenValue = '') {
  let failure
  try {
    operation()
  } catch (error) {
    failure = error
  }
  assert.ok(failure instanceof Error, `Expected ${code} failure.`)
  assert.equal(failure.code, code)
  if (forbiddenValue) assert.equal(failure.message.includes(forbiddenValue), false)
}

assert.deepEqual(assertUatAuthBuildEnvironment(validEnvironment), {
  mode: UAT_AUTH_RUNTIME_MODE,
  supabaseUrl: ERP_ENTENG_UAT_URL,
  publishableKey: browserKey,
  keyIdentity: 'mock',
})
expectFailure(
  () => assertUatAuthReleaseEnvironment(validEnvironment),
  'UAT_MOCK_KEY_RELEASE_FORBIDDEN',
  browserKey,
)
expectFailure(
  () => assertUatAuthBuildEnvironment({}),
  'UAT_RUNTIME_MODE_REQUIRED',
)
expectFailure(
  () => assertUatAuthBuildEnvironment({
    VITE_ERP_RUNTIME_MODE: UAT_AUTH_RUNTIME_MODE,
    VITE_SUPABASE_URL: ERP_ENTENG_UAT_URL,
  }),
  'UAT_PUBLISHABLE_KEY_INVALID',
)
expectFailure(
  () => assertUatAuthBuildEnvironment({ ...validEnvironment, VITE_ERP_RUNTIME_MODE: 'DEMO_SIMULATION' }),
  'UAT_RUNTIME_MODE_REQUIRED',
)
expectFailure(
  () => assertUatAuthBuildEnvironment({ ...validEnvironment, VITE_SUPABASE_URL: 'https://example.supabase.co' }),
  'UAT_TARGET_INVALID',
)
expectFailure(
  () => assertUatAuthBuildEnvironment({ ...validEnvironment, VITE_SUPABASE_ANON_KEY: 'legacy-key-must-not-print' }),
  'UAT_LEGACY_ANON_KEY_FORBIDDEN',
  'legacy-key-must-not-print',
)
expectFailure(
  () => assertUatAuthBuildEnvironment({ ...validEnvironment, VITE_SUPABASE_PUBLISHABLE_KEY: 'invalid-key-must-not-print' }),
  'UAT_PUBLISHABLE_KEY_INVALID',
  'invalid-key-must-not-print',
)
expectFailure(
  () => assertUatAuthBuildEnvironment({
    ...validEnvironment,
    ERP_UAT_AUTH_ALLOW_MOCK_KEY: '',
    VITE_SUPABASE_PUBLISHABLE_KEY: 'sb_publishable_unreviewed_12345678901234567890',
  }),
  'UAT_PUBLISHABLE_KEY_IDENTITY_MISMATCH',
  'sb_publishable_unreviewed_12345678901234567890',
)
expectFailure(
  () => assertUatAuthBuildEnvironment({
    ...validEnvironment,
    ERP_UAT_AUTH_ALLOW_MOCK_KEY: '',
    VITE_SUPABASE_PUBLISHABLE_KEY: 'sb_publishable_Unreviewed_MixedCase_1234567890',
  }),
  'UAT_PUBLISHABLE_KEY_IDENTITY_MISMATCH',
  'sb_publishable_Unreviewed_MixedCase_1234567890',
)
expectFailure(
  () => assertUatAuthBuildEnvironment({ ...validEnvironment, ERP_UAT_AUTH_ALLOW_MOCK_KEY: 'true' }),
  'UAT_MOCK_KEY_FLAG_INVALID',
  browserKey,
)
expectFailure(
  () => assertUatAuthBuildEnvironment({
    ...validEnvironment,
    VITE_SUPABASE_PUBLISHABLE_KEY: 'sb_publishable_not_mock_12345678901234567890',
  }),
  'UAT_MOCK_KEY_INVALID',
  'sb_publishable_not_mock_12345678901234567890',
)
expectFailure(
  () => assertUatAuthBuildEnvironment({ ...validEnvironment, VITE_SUPABASE_EXTRA: 'extra-value-must-not-print' }),
  'UAT_UNEXPECTED_SUPABASE_VARIABLE',
  'extra-value-must-not-print',
)

const target = assertUatAuthWranglerTarget()
assert.equal(target.workerName, UAT_AUTH_WORKER_NAME)
assert.equal(target.environment, 'uat-auth')

const packageScripts = JSON.parse(readFileSync(resolve('package.json'), 'utf8')).scripts
assert.equal(packageScripts.deploy, 'npm run build && wrangler deploy')
assert.equal(packageScripts['cf:preview'], 'npm run build && wrangler versions upload')
assert.equal(packageScripts['check:uat-auth-env'], 'node scripts/assert-uat-auth-env.mjs')
assert.equal(packageScripts['check:uat-auth-release-env'], 'node scripts/assert-uat-auth-env.mjs --release')
assert.equal(packageScripts['check:uat-auth-target'], 'node scripts/assert-uat-auth-target.mjs')
assert.equal(packageScripts['check:uat-auth-dist'], 'node scripts/assert-uat-auth-artifact.mjs dist')
assert.equal(
  packageScripts['build:uat-auth'],
  'npm run check:uat-auth-env && npm run build && npm run check:uat-auth-dist',
)
assert.equal(
  packageScripts['deploy:uat-auth'],
  'npm run check:uat-auth-target && npm run check:uat-auth-release-env && npm run build:uat-auth && npm run check:uat-auth-target && npm run check:uat-auth-release-env && node scripts/run-uat-auth-wrangler.mjs deploy',
)
assert.equal(
  packageScripts['cf:preview:uat-auth'],
  'npm run check:uat-auth-target && npm run check:uat-auth-release-env && npm run build:uat-auth && npm run check:uat-auth-target && npm run check:uat-auth-release-env && node scripts/run-uat-auth-wrangler.mjs preview',
)

const redirectedTargetRoot = mkdtempSync(resolve(tmpdir(), 'erp-uat-auth-target-'))
try {
  const redirectedConfig = resolve(redirectedTargetRoot, 'wrangler.jsonc')
  const redirectDirectory = resolve(redirectedTargetRoot, '.wrangler', 'deploy')
  mkdirSync(redirectDirectory, { recursive: true })
  writeFileSync(redirectedConfig, '{}')
  writeFileSync(resolve(redirectDirectory, 'config.json'), '{}')
  expectFailure(
    () => assertUatAuthWranglerTarget(redirectedConfig),
    'UAT_WRANGLER_REDIRECT_FORBIDDEN',
  )
  rmSync(resolve(redirectDirectory, 'config.json'))
  const unexpectedEnvironmentConfig = JSON.parse(readFileSync(resolve('wrangler.jsonc'), 'utf8'))
  unexpectedEnvironmentConfig.env['uat-auth'].assets = { directory: './other-dist/' }
  writeFileSync(redirectedConfig, JSON.stringify(unexpectedEnvironmentConfig))
  expectFailure(
    () => assertUatAuthWranglerTarget(redirectedConfig),
    'UAT_WORKER_CONFIG_UNEXPECTED',
  )
} finally {
  rmSync(redirectedTargetRoot, { recursive: true, force: true })
}

const fixtureRoot = mkdtempSync(resolve(tmpdir(), 'erp-uat-auth-assertions-'))
const assetDirectory = resolve(fixtureRoot, 'assets')
mkdirSync(assetDirectory)

try {
  const indexFile = resolve(fixtureRoot, 'index.html')
  const runtimeArtifact = [
    'const runtime=parseRuntimeConfig({',
    `VITE_ERP_RUNTIME_MODE:"${UAT_AUTH_RUNTIME_MODE}",`,
    `VITE_SUPABASE_URL:"${ERP_ENTENG_UAT_URL}",`,
    `VITE_SUPABASE_PUBLISHABLE_KEY:"${browserKey}",`,
    'VITE_SUPABASE_ANON_KEY:void 0});',
  ].join('')
  const runtimeFile = resolve(assetDirectory, 'index.js')
  writeFileSync(runtimeFile, runtimeArtifact)
  writeFileSync(indexFile, '<!doctype html><html><head><script type="module" src="/assets/index.js"></script></head><body></body></html>')
  const artifactResult = assertUatAuthArtifact(fixtureRoot, validEnvironment)
  assert.equal(artifactResult.javascriptFileCount, 1)
  assert.equal(artifactResult.runtimeBundle, runtimeFile)

  writeFileSync(indexFile, '<!doctype html><html><head><script type="module" src="./assets/index.js"></script></head><body></body></html>')
  expectFailure(
    () => assertUatAuthArtifact(fixtureRoot, validEnvironment),
    'UAT_ARTIFACT_ENTRYPOINT_NOT_ROOTED',
    browserKey,
  )

  writeFileSync(indexFile, '<!doctype html><html><head><!-- <script type="module" src="/assets/index.js"></script> --><script type="module" src="/assets/not-runtime.js"></script></head><body></body></html>')
  expectFailure(
    () => assertUatAuthArtifact(fixtureRoot, validEnvironment),
    'UAT_ARTIFACT_RUNTIME_NOT_ENTRYPOINT',
    browserKey,
  )
  writeFileSync(indexFile, '<!doctype html><html><head><template><script type="module" src="/assets/index.js"></script></template><script type="module" src="/assets/not-runtime.js"></script></head><body></body></html>')
  expectFailure(
    () => assertUatAuthArtifact(fixtureRoot, validEnvironment),
    'UAT_ARTIFACT_RUNTIME_NOT_ENTRYPOINT',
    browserKey,
  )
  writeFileSync(indexFile, '<!doctype html><html><head><script type="module" src="/assets/index.js"></script></head><body></body></html>')

  writeFileSync(runtimeFile, runtimeArtifact.replace(
    `VITE_ERP_RUNTIME_MODE:"${UAT_AUTH_RUNTIME_MODE}"`,
    `VITE_ERP_RUNTIME_MODE:"WRONG",decoy:"${UAT_AUTH_RUNTIME_MODE}"`,
  ))
  expectFailure(
    () => assertUatAuthArtifact(fixtureRoot, validEnvironment),
    'UAT_ARTIFACT_RUNTIME_VALUES_INVALID',
    browserKey,
  )

  writeFileSync(runtimeFile, runtimeArtifact.replace(
    `VITE_ERP_RUNTIME_MODE:"${UAT_AUTH_RUNTIME_MODE}"`,
    'VITE_ERP_RUNTIME_MODE:void 0',
  ))
  expectFailure(
    () => assertUatAuthArtifact(fixtureRoot, validEnvironment),
    'UAT_ARTIFACT_MODE_MISMATCH',
    browserKey,
  )

  writeFileSync(runtimeFile, `${runtimeArtifact}\nconst duplicate="${browserKey}";`)
  expectFailure(
    () => assertUatAuthArtifact(fixtureRoot, validEnvironment),
    'UAT_ARTIFACT_BROWSER_KEY_AMBIGUOUS',
    browserKey,
  )
} finally {
  rmSync(fixtureRoot, { recursive: true, force: true })
}

console.log('UAT Auth deployment assertions passed: environment, target isolation, artifact identity, and key-redaction failures.')
