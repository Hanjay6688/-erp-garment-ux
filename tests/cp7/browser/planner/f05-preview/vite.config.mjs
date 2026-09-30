import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { assertNoForbiddenBuildSecrets } from '../../../../../scripts/build-preflight.mjs'
import { yieldPreviewPlugin } from './yieldServer.mjs'

export default defineConfig(({ mode }) => {
  assertNoForbiddenBuildSecrets({ ...loadEnv(mode, process.cwd(), ''), ...process.env })
  return { plugins: [react(), yieldPreviewPlugin()], build: { target: 'es2020', outDir: 'f05-preview-build',
    rolldownOptions: { input: 'tests/cp7/browser/planner/f05-preview/index.html' } } }
})
