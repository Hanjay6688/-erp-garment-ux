import { execFileSync } from 'node:child_process'
import { resolve } from 'node:path'
import { build, loadEnv } from 'vite'

const root = process.cwd()
const env = { ...loadEnv('production', root, ''), ...process.env }
const demo = !env.VITE_ERP_RUNTIME_MODE || env.VITE_ERP_RUNTIME_MODE === 'DEMO_SIMULATION'
if (demo) {
  const project = resolve(root, 'worker-demo')
  execFileSync(process.execPath, [resolve(root, 'node_modules/typescript/bin/tsc'), '-p', resolve(project, 'tsconfig.app.json')], { stdio: 'inherit' })
  await build({ root: project, envDir: root, configFile: resolve(root, 'vite.config.ts'), build: { outDir: resolve(root,'dist'), emptyOutDir: true } })
} else {
  await build({ root, configFile: resolve(root, 'vite.config.ts') })
}
