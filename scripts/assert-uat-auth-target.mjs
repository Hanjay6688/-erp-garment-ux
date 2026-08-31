import { existsSync, readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { pathToFileURL } from 'node:url'

export const PRODUCTION_WORKER_NAME = 'erp-garment-ux'
export const UAT_AUTH_ENVIRONMENT = 'uat-auth'
export const UAT_AUTH_WORKER_NAME = 'erp-garment-ux-uat-auth'

export class UatAuthTargetError extends Error {
  constructor(code, message) {
    super(message)
    this.name = 'UatAuthTargetError'
    this.code = code
  }
}

function fail(code, message) {
  throw new UatAuthTargetError(code, message)
}

export function assertUatAuthWranglerTarget(configPath = 'wrangler.jsonc') {
  const resolvedPath = resolve(configPath)
  if (existsSync(resolve(dirname(resolvedPath), '.wrangler/deploy/config.json'))) {
    fail(
      'UAT_WRANGLER_REDIRECT_FORBIDDEN',
      'Generated Wrangler config redirection is present; refusing an ambiguous UAT target.',
    )
  }
  let config
  try {
    config = JSON.parse(readFileSync(resolvedPath, 'utf8'))
  } catch {
    fail('UAT_WRANGLER_CONFIG_INVALID', 'Wrangler configuration must be readable strict JSONC without ambiguous comments.')
  }

  if (config.name !== PRODUCTION_WORKER_NAME) {
    fail('PRODUCTION_WORKER_NAME_DRIFT', 'Canonical Worker name drifted; refusing to infer a UAT target.')
  }

  const uat = config.env?.[UAT_AUTH_ENVIRONMENT]
  if (!uat || uat.name !== UAT_AUTH_WORKER_NAME) {
    fail('UAT_WORKER_TARGET_INVALID', 'The uat-auth environment must resolve to the dedicated UAT Auth Worker.')
  }
  if (uat.workers_dev !== true || uat.preview_urls !== true) {
    fail('UAT_WORKER_PREVIEW_INVALID', 'The dedicated UAT Auth Worker must use workers.dev with preview URLs enabled.')
  }
  if ('route' in uat || 'routes' in uat || 'custom_domain' in uat) {
    fail('UAT_WORKER_ROUTE_FORBIDDEN', 'The dedicated UAT Auth environment must not declare a production route or custom domain.')
  }
  const unexpectedUatSetting = Object.keys(uat).find((name) => ![
    'name',
    'workers_dev',
    'preview_urls',
  ].includes(name))
  if (unexpectedUatSetting) {
    fail(
      'UAT_WORKER_CONFIG_UNEXPECTED',
      `Unexpected dedicated UAT environment setting: ${unexpectedUatSetting}.`,
    )
  }
  if ('route' in config || 'routes' in config) {
    fail('UAT_INHERITED_ROUTE_FORBIDDEN', 'A top-level Worker route could leak into UAT; define an isolated config before deployment.')
  }
  if (config.assets?.directory !== './dist/'
      || config.assets?.not_found_handling !== 'single-page-application') {
    fail('UAT_ASSET_CONFIG_INVALID', 'UAT Auth must inherit the reviewed static SPA asset configuration.')
  }

  return Object.freeze({ environment: UAT_AUTH_ENVIRONMENT, workerName: UAT_AUTH_WORKER_NAME })
}

const invokedDirectly = process.argv[1]
  && import.meta.url === pathToFileURL(resolve(process.argv[1])).href
if (invokedDirectly) {
  const target = assertUatAuthWranglerTarget(process.argv[2])
  console.log(`UAT Auth Wrangler target passed: ${target.workerName} via --env ${target.environment}.`)
}
