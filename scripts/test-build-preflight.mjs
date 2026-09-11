import { existsSync, mkdtempSync, readFileSync, readdirSync, rmSync, statSync, writeFileSync } from 'node:fs'
import { randomUUID } from 'node:crypto'
import { tmpdir } from 'node:os'
import { resolve } from 'node:path'
import { spawnSync } from 'node:child_process'
import { scanClientArtifacts } from './scan-client-artifacts.mjs'

const canary = 'sb_secret_CANARY_NEVER_BUNDLE_1234567890'
const outputDirectory = mkdtempSync(resolve(tmpdir(), 'erp-secret-preflight-'))
const viteEntry = resolve('node_modules/vite/bin/vite.js')
const fileMode = `preflight-canary-${process.pid}-${randomUUID().slice(0, 8)}`
const environmentCanaryFile = resolve(`.env.${fileMode}`)
let ownsEnvironmentCanaryFile = false

function filesUnder(path) {
  if (!existsSync(path)) return []
  if (statSync(path).isFile()) return [path]
  return readdirSync(path).flatMap((name) => filesUnder(resolve(path, name)))
}

try {
  for (const forbiddenEnvironment of [
    { VITE_SUPABASE_SERVICE_ROLE_KEY: canary },
    { VITE_SUPABASE_PUBLISHABLE_KEY: canary },
  ]) {
    const result = spawnSync(process.execPath, [viteEntry, 'build', '--outDir', outputDirectory], {
      cwd: resolve('.'),
      encoding: 'utf8',
      env: { ...process.env, ...forbiddenEnvironment },
    })
    const output = `${result.stdout ?? ''}\n${result.stderr ?? ''}`
    if (result.status === 0 || !output.includes('FORBIDDEN_BUILD_SECRET')) {
      throw new Error(`Build preflight did not reject the forbidden canary.\n${output}`)
    }

    const leaked = filesUnder(outputDirectory).some((file) => readFileSync(file).includes(canary))
    if (leaked) throw new Error('Forbidden canary reached a client artifact.')
  }

  // Exclusive creation is the atomic existence check.
  writeFileSync(
    environmentCanaryFile,
    `VITE_SUPABASE_PUBLISHABLE_KEY=${canary}\n`,
    { flag: 'wx' },
  )
  ownsEnvironmentCanaryFile = true
  const fileEnvironmentResult = spawnSync(
    process.execPath,
    [viteEntry, 'build', '--mode', fileMode, '--outDir', outputDirectory],
    {
      cwd: resolve('.'),
      encoding: 'utf8',
      env: { ...process.env },
    },
  )
  const fileEnvironmentOutput = `${fileEnvironmentResult.stdout ?? ''}\n${fileEnvironmentResult.stderr ?? ''}`
  if (fileEnvironmentResult.status === 0 || !fileEnvironmentOutput.includes('FORBIDDEN_BUILD_SECRET')) {
    throw new Error(`Build preflight did not reject the .env.<mode> canary.\n${fileEnvironmentOutput}`)
  }
  if (filesUnder(outputDirectory).some((file) => readFileSync(file).includes(canary))) {
    throw new Error('.env.<mode> canary reached a client artifact.')
  }

  const scannerCanaryFile = resolve(outputDirectory, 'secret-canary.js')
  writeFileSync(scannerCanaryFile, canary)
  if (scanClientArtifacts(outputDirectory).length === 0) {
    throw new Error('Client artifact scanner did not detect the secret canary.')
  }
  rmSync(scannerCanaryFile, { force: true })
  console.log('Build-secret regression passed: process env and .env.<mode> server-key canaries aborted before bundling; canary was absent.')
} finally {
  if (ownsEnvironmentCanaryFile) rmSync(environmentCanaryFile, { force: true })
  rmSync(outputDirectory, { recursive: true, force: true })
}
