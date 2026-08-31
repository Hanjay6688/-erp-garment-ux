import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { assertNoForbiddenBuildSecrets } from './scripts/build-preflight.mjs'

export default defineConfig(({ mode }) => {
  // Vite loads .env* after config evaluation unless the config explicitly
  // loads it. Scan every key here so a server key hidden in .env.<mode>
  // cannot reach define/import.meta.env or the client bundle.
  const fileEnvironment = loadEnv(mode, process.cwd(), '')
  assertNoForbiddenBuildSecrets({ ...fileEnvironment, ...process.env })

  return {
    plugins: [react()],
    // The Worker serves SPA fallbacks from nested routes such as
    // /auth/accept. Root-relative assets keep those deep links bootable.
    base: '/',
    build: {
      target: 'es2020',
      cssCodeSplit: true,
    },
  }
})
