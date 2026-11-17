import {spawn} from 'node:child_process'
import {fileURLToPath} from 'node:url'

const mode = process.env.INPUT_MODE
const scratch = process.env.RUNNER_TEMP
if (!['audit', 'smoke'].includes(mode) || !scratch ||
    !process.env.ACTIONS_RUNTIME_TOKEN || !process.env.ACTIONS_RESULTS_URL) {
  console.error('P20_EVIDENCE_ACTION_CONTEXT_REQUIRED')
  process.exit(1)
}
const script = fileURLToPath(new URL('../p20_publish.py', import.meta.url))
const publisher = spawn('python3', ['-u', '-B', script, mode, scratch], {stdio: 'inherit'})
for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => publisher.kill(signal))
}
publisher.on('error', () => {
  console.error('P20_EVIDENCE_PUBLISHER_START_FAILED')
  process.exitCode = 1
})
publisher.on('exit', code => { process.exitCode = code ?? 1 })
