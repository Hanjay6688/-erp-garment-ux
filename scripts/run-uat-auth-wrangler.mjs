import { spawnSync } from 'node:child_process'
import { dirname, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { assertUatAuthArtifact } from './assert-uat-auth-artifact.mjs'
import { assertUatAuthReleaseEnvironment } from './assert-uat-auth-env.mjs'
import { assertUatAuthWranglerTarget, UAT_AUTH_ENVIRONMENT } from './assert-uat-auth-target.mjs'

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const defaultConfigPath = resolve(projectRoot, 'wrangler.jsonc')
const defaultArtifactPath = resolve(projectRoot, 'dist')

export class UatAuthWranglerInvocationError extends Error {
  constructor(code, message) {
    super(message)
    this.name = 'UatAuthWranglerInvocationError'
    this.code = code
  }
}

function fail(code, message) {
  throw new UatAuthWranglerInvocationError(code, message)
}

export function assertUatAuthWranglerAction(argumentsList) {
  if (argumentsList.length !== 1 || !['deploy', 'preview'].includes(argumentsList[0])) {
    fail(
      'UAT_WRANGLER_ARGUMENTS_FORBIDDEN',
      'UAT Auth Wrangler wrapper accepts exactly one fixed action and no forwarded options.',
    )
  }
  return argumentsList[0]
}

export function uatAuthWranglerArguments(action, configPath = defaultConfigPath) {
  if (action === 'deploy') {
    return Object.freeze(['deploy', '--env', UAT_AUTH_ENVIRONMENT, '--config', resolve(configPath)])
  }
  if (action === 'preview') {
    return Object.freeze([
      'versions',
      'upload',
      '--env',
      UAT_AUTH_ENVIRONMENT,
      '--config',
      resolve(configPath),
      '--preview-alias',
      'uat-auth',
    ])
  }
  fail('UAT_WRANGLER_ACTION_INVALID', 'Unknown UAT Auth Wrangler action.')
}

function runUatAuthWrangler(action) {
  assertUatAuthWranglerTarget(defaultConfigPath)
  assertUatAuthReleaseEnvironment(process.env)
  assertUatAuthArtifact(defaultArtifactPath, process.env)

  const wranglerPackagePath = import.meta.resolve('wrangler/package.json')
  const wranglerBinary = resolve(dirname(fileURLToPath(wranglerPackagePath)), 'bin', 'wrangler.js')
  const result = spawnSync(
    process.execPath,
    [wranglerBinary, ...uatAuthWranglerArguments(action)],
    { cwd: projectRoot, env: process.env, stdio: 'inherit' },
  )
  if (result.error) {
    fail('UAT_WRANGLER_START_FAILED', 'Unable to start the pinned local Wrangler executable.')
  }
  if (result.status !== 0) process.exitCode = result.status ?? 1
}

const invokedDirectly = process.argv[1]
  && import.meta.url === pathToFileURL(resolve(process.argv[1])).href
if (invokedDirectly) {
  runUatAuthWrangler(assertUatAuthWranglerAction(process.argv.slice(2)))
}
