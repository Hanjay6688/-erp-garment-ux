export const ERP_ENTENG_UAT_PROJECT_REF = 'siimvrusnzxexizpyoib' as const
export const ERP_GARMENT_PRODUCTION_PROJECT_REF = 'vlxdhpkjeevubjxexnfo' as const

export type RuntimeMode = 'DEMO_SIMULATION' | 'UAT_AUTH_SIMULATION' | 'DISPOSABLE_TEST'

export type DemoRuntimeConfig = {
  mode: 'DEMO_SIMULATION'
  authMode: 'DISABLED'
  businessDataMode: 'SIMULATION'
  businessRpcEnabled: false
  accessControlMode: 'SIMULATION'
  patternMode: 'SIMULATION'
  cuttingMode: 'SIMULATION'
  distributionMode: 'SIMULATION'
  wipStatusMode: 'SIMULATION'
  bsResolutionMode: 'SIMULATION'
  laundryMode: 'SIMULATION'
  qcFinalMode: 'SIMULATION'
  fgHandoffMode: 'SIMULATION'
}

export type UatRuntimeConfig = {
  mode: 'UAT_AUTH_SIMULATION'
  authMode: 'UAT_SUPABASE'
  businessDataMode: 'PARTIAL_CONNECTED'
  businessRpcEnabled: true
  accessControlMode: 'CONNECTED'
  patternMode: 'CONNECTED'
  cuttingMode: 'CONNECTED'
  distributionMode: 'CONNECTED'
  wipStatusMode: 'CONNECTED'
  bsResolutionMode: 'CONNECTED'
  laundryMode: 'CONNECTED'
  qcFinalMode: 'CONNECTED'
  fgHandoffMode: 'BLOCKED_UNTIL_AUTHORITATIVE'
  projectRef: typeof ERP_ENTENG_UAT_PROJECT_REF
  supabaseUrl: string
  browserKey: string
}

export type DisposableRuntimeConfig = Omit<UatRuntimeConfig, 'mode' | 'authMode' | 'projectRef'> & {
  mode: 'DISPOSABLE_TEST'
  authMode: 'LOCAL_SUPABASE'
  projectRef: 'cp6-disposable'
}
export type ConnectedRuntimeConfig = UatRuntimeConfig | DisposableRuntimeConfig
export type RuntimeConfig = DemoRuntimeConfig | ConnectedRuntimeConfig
export type RuntimeEnvironment = {
  VITE_ERP_RUNTIME_MODE?: string
  VITE_SUPABASE_URL?: string
  VITE_SUPABASE_PUBLISHABLE_KEY?: string
  VITE_SUPABASE_ANON_KEY?: string
}

export class RuntimeConfigError extends Error {
  readonly code: string

  constructor(code: string, message: string) {
    super(message)
    this.name = 'RuntimeConfigError'
    this.code = code
  }
}

const connectionEnvironmentNames = [
  'VITE_SUPABASE_URL',
  'VITE_SUPABASE_PUBLISHABLE_KEY',
  'VITE_SUPABASE_ANON_KEY',
] as const

function envString(environment: RuntimeEnvironment, name: keyof RuntimeEnvironment) {
  const value = environment[name]
  return typeof value === 'string' ? value.trim() : ''
}

function decodeJwtPayload(key: string): Record<string, unknown> | null {
  const segments = key.split('.')
  if (segments.length !== 3) return null

  try {
    const normalized = segments[1].replace(/-/g, '+').replace(/_/g, '/')
    const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, '=')
    const parsed: unknown = JSON.parse(globalThis.atob(padded))
    return parsed !== null && typeof parsed === 'object' && !Array.isArray(parsed)
      ? parsed as Record<string, unknown>
      : null
  } catch {
    return null
  }
}

function validateBrowserKey(key: string) {
  const lowered = key.toLowerCase()
  if (lowered.startsWith('sb_secret_') || lowered.includes('service_role')) {
    throw new RuntimeConfigError(
      'SECRET_KEY_FORBIDDEN',
      'Kunci secret/service-role dilarang berada di aplikasi browser.',
    )
  }

  if (/^sb_publishable_[a-z0-9._-]{16,}$/i.test(key)) return

  const jwtPayload = decodeJwtPayload(key)
  if (!jwtPayload || jwtPayload.role !== 'anon') {
    throw new RuntimeConfigError(
      'BROWSER_KEY_INVALID',
      'Gunakan Supabase publishable key atau legacy anon key khusus browser.',
    )
  }

  const keyProjectRef = typeof jwtPayload.ref === 'string' ? jwtPayload.ref : null
  if (keyProjectRef && keyProjectRef !== ERP_ENTENG_UAT_PROJECT_REF) {
    throw new RuntimeConfigError(
      'BROWSER_KEY_PROJECT_MISMATCH',
      'Legacy anon key tidak berasal dari ERP Enteng UAT.',
    )
  }
}

function validateUatUrl(rawUrl: string) {
  let url: URL
  try {
    url = new URL(rawUrl)
  } catch {
    throw new RuntimeConfigError('UAT_URL_INVALID', 'URL Supabase UAT tidak valid.')
  }

  const hasUnexpectedParts = url.protocol !== 'https:'
    || url.username !== ''
    || url.password !== ''
    || url.port !== ''
    || (url.pathname !== '' && url.pathname !== '/')
    || url.search !== ''
    || url.hash !== ''
  if (hasUnexpectedParts) {
    throw new RuntimeConfigError(
      'UAT_URL_INVALID',
      'URL UAT harus berupa endpoint HTTPS proyek Supabase tanpa path atau parameter.',
    )
  }

  const expectedHost = `${ERP_ENTENG_UAT_PROJECT_REF}.supabase.co`
  const productionHost = `${ERP_GARMENT_PRODUCTION_PROJECT_REF}.supabase.co`
  if (url.hostname === productionHost) {
    throw new RuntimeConfigError(
      'PRODUCTION_TARGET_FORBIDDEN',
      'Mode UAT tidak boleh mengarah ke proyek produksi ERP-Garment.',
    )
  }
  if (url.hostname !== expectedHost) {
    throw new RuntimeConfigError(
      'UAT_PROJECT_REF_MISMATCH',
      `Mode UAT hanya boleh mengarah ke ERP Enteng (${ERP_ENTENG_UAT_PROJECT_REF}).`,
    )
  }

  return `https://${expectedHost}`
}

export function parseRuntimeConfig(environment: RuntimeEnvironment, testBuild?: {
  mode: string
  pageOrigin: string
}): RuntimeConfig {
  const configuredMode = envString(environment, 'VITE_ERP_RUNTIME_MODE')
  const mode = configuredMode || 'DEMO_SIMULATION'

  if (mode === 'DEMO_SIMULATION') {
    const leakedConnectionEnv = connectionEnvironmentNames.find((name) => envString(environment, name) !== '')
    if (leakedConnectionEnv) {
      throw new RuntimeConfigError(
        'DEMO_SUPABASE_ENV_FORBIDDEN',
        `Mode DEMO_SIMULATION tidak menerima konfigurasi Supabase (${leakedConnectionEnv}).`,
      )
    }
    return {
      mode,
      authMode: 'DISABLED',
      businessDataMode: 'SIMULATION',
      businessRpcEnabled: false,
      accessControlMode: 'SIMULATION',
      patternMode: 'SIMULATION',
      cuttingMode: 'SIMULATION',
      distributionMode: 'SIMULATION',
      wipStatusMode: 'SIMULATION',
      bsResolutionMode: 'SIMULATION',
      laundryMode: 'SIMULATION',
      qcFinalMode: 'SIMULATION',
      fgHandoffMode: 'SIMULATION',
    }
  }

  const disposable = mode === 'DISPOSABLE_TEST'
  if (disposable && (testBuild?.mode !== 'cp6-disposable-test'
    || testBuild.pageOrigin !== 'http://127.0.0.1:4176')) {
    throw new RuntimeConfigError('DISPOSABLE_BUILD_REQUIRED', 'Target uji hanya dapat dibuka dari build khusus di loopback.')
  }
  if (mode !== 'UAT_AUTH_SIMULATION' && !disposable) {
    throw new RuntimeConfigError(
      'RUNTIME_MODE_UNSUPPORTED',
      'Mode runtime tidak didukung.',
    )
  }

  const rawUrl = envString(environment, 'VITE_SUPABASE_URL')
  if (!rawUrl) {
    throw new RuntimeConfigError('UAT_URL_REQUIRED', 'VITE_SUPABASE_URL wajib untuk mode UAT.')
  }
  if (disposable && rawUrl !== 'http://127.0.0.1:54328') {
    throw new RuntimeConfigError('DISPOSABLE_TARGET_FORBIDDEN', 'Target uji wajib memakai API disposable di loopback yang ditentukan.')
  }
  const supabaseUrl = disposable ? rawUrl : validateUatUrl(rawUrl)

  const publishableKey = envString(environment, 'VITE_SUPABASE_PUBLISHABLE_KEY')
  const anonKey = envString(environment, 'VITE_SUPABASE_ANON_KEY')
  if (!publishableKey && !anonKey) {
    throw new RuntimeConfigError(
      'UAT_BROWSER_KEY_REQUIRED',
      'Isi VITE_SUPABASE_PUBLISHABLE_KEY atau legacy VITE_SUPABASE_ANON_KEY.',
    )
  }
  if (publishableKey && anonKey && publishableKey !== anonKey) {
    throw new RuntimeConfigError(
      'UAT_BROWSER_KEY_AMBIGUOUS',
      'Tetapkan satu browser key saja agar target Auth tidak ambigu.',
    )
  }

  const browserKey = publishableKey || anonKey
  if (disposable) {
    const payload = decodeJwtPayload(browserKey)
    if (payload?.role !== 'anon' || (payload.ref !== undefined && payload.ref !== 'local')) {
      throw new RuntimeConfigError('DISPOSABLE_BROWSER_KEY_INVALID', 'Target uji memerlukan anon key lokal; kredensial hosted atau secret ditolak.')
    }
  } else {
    validateBrowserKey(browserKey)
  }

  const connected = {
    businessDataMode: 'PARTIAL_CONNECTED',
    businessRpcEnabled: true,
    accessControlMode: 'CONNECTED',
    patternMode: 'CONNECTED',
    cuttingMode: 'CONNECTED',
    distributionMode: 'CONNECTED',
    wipStatusMode: 'CONNECTED',
    bsResolutionMode: 'CONNECTED',
    laundryMode: 'CONNECTED',
    qcFinalMode: 'CONNECTED',
    fgHandoffMode: 'BLOCKED_UNTIL_AUTHORITATIVE',
    supabaseUrl,
    browserKey,
  } as const
  return disposable
    ? { ...connected, mode: 'DISPOSABLE_TEST', authMode: 'LOCAL_SUPABASE', projectRef: 'cp6-disposable' }
    : { ...connected, mode: 'UAT_AUTH_SIMULATION', authMode: 'UAT_SUPABASE', projectRef: ERP_ENTENG_UAT_PROJECT_REF }
}

export function isUatRuntime(config: RuntimeConfig): config is UatRuntimeConfig {
  return config.mode === 'UAT_AUTH_SIMULATION'
}

export function isConnectedRuntime(config: RuntimeConfig): config is ConnectedRuntimeConfig {
  return config.mode === 'UAT_AUTH_SIMULATION' || config.mode === 'DISPOSABLE_TEST'
}
