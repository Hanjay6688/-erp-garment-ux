import {dirname, join} from 'node:path'
import {pathToFileURL} from 'node:url'

const [file, name, modules] = process.argv.slice(2)
try {
  const entry = pathToFileURL(join(modules, 'node_modules/@actions/artifact/lib/artifact.js'))
  const {default: artifact} = await import(entry.href)
  const result = await artifact.uploadArtifact(name, [file], dirname(file), {
    retentionDays: 14,
    compressionLevel: 0
  })
  const digest = String(result.digest ?? '').replace(/^sha256:/, '')
  if (!Number.isSafeInteger(result.id) || result.id < 1 || !/^[a-f0-9]{64}$/.test(digest)) {
    throw new Error('P20_EVIDENCE_FINALIZED_ARTIFACT_RECEIPT_REQUIRED')
  }
  console.log(`CP7_UPLOAD_OK ${result.id} ${digest}`)
} catch {
  // The supervisor captures SDK output locally and does not forward it.
  process.exitCode = 1
}
