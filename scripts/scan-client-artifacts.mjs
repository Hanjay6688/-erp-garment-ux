import { readFileSync, readdirSync, statSync } from 'node:fs'
import { resolve } from 'node:path'
import { pathToFileURL } from 'node:url'

const publishableSecretPattern = /sb_secret_[a-z0-9._-]{16,}/gi
const jwtCandidatePattern = /eyJ[a-zA-Z0-9_-]{8,}\.[a-zA-Z0-9_-]{8,}\.[a-zA-Z0-9_-]{8,}/g

function decodeJwtPayload(candidate) {
  try {
    const payload = candidate.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
    const padded = payload.padEnd(Math.ceil(payload.length / 4) * 4, '=')
    const parsed = JSON.parse(Buffer.from(padded, 'base64').toString('utf8'))
    return parsed && typeof parsed === 'object' ? parsed : null
  } catch {
    return null
  }
}

function filesUnder(path) {
  const entry = statSync(path)
  if (entry.isFile()) return [path]
  return readdirSync(path).flatMap((name) => filesUnder(resolve(path, name)))
}

export function scanClientArtifacts(rootPath) {
  const findings = []
  for (const file of filesUnder(resolve(rootPath))) {
    const content = readFileSync(file, 'utf8')
    if (publishableSecretPattern.test(content)) findings.push(`${file}: Supabase secret key`)
    publishableSecretPattern.lastIndex = 0
    for (const candidate of content.match(jwtCandidatePattern) ?? []) {
      if (decodeJwtPayload(candidate)?.role === 'service_role') {
        findings.push(`${file}: legacy Supabase service-role JWT`)
      }
    }
  }
  return findings
}

const invokedDirectly = process.argv[1]
  && import.meta.url === pathToFileURL(resolve(process.argv[1])).href
if (invokedDirectly) {
  const rootPath = process.argv[2]
  if (!rootPath) throw new Error('Usage: node scripts/scan-client-artifacts.mjs <directory>')
  const findings = scanClientArtifacts(rootPath)
  if (findings.length > 0) {
    throw new Error(`[CLIENT_SECRET_SCAN_FAILED]\n${findings.join('\n')}`)
  }
  console.log(`Client artifact secret scan passed: ${resolve(rootPath)}`)
}
