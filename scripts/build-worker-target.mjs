import { mkdir, copyFile } from 'node:fs/promises'
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
  // Each published entry also opens on a direct link or browser refresh.
  const routes = ['migrasi','cp7-preview','produksi/buat-potongan','produksi/bagi-potongan','produksi/jahit','produksi/laundry','produksi/qc', ...['planner','stock','cutting','report','reminders','ai','whatsapp','methods'].map(page => 'analisis/' + page)]
  for (const route of routes) {
    const directory = resolve(root, 'dist', route)
    await mkdir(directory, { recursive: true })
    await copyFile(resolve(root, 'dist/index.html'), resolve(directory, 'index.html'))
  }
} else {
  await build({ root, configFile: resolve(root, 'vite.config.ts') })
}
