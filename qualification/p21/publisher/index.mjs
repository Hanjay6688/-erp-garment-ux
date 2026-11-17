import { spawn } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const qualification = fileURLToPath(new URL('../../', import.meta.url))
const publisher = spawn('python3', ['-u', '-B', '-m', 'p21.checkpoints'], {
  env: { ...process.env, PYTHONPATH: qualification },
  stdio: 'inherit',
})
for (const signal of ['SIGINT', 'SIGTERM']) {
  process.once(signal, () => publisher.kill(signal))
}
publisher.on('error', () => { process.exitCode = 1 })
publisher.on('exit', code => { process.exitCode = code ?? 1 })
