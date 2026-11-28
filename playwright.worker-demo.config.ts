import { defineConfig } from '@playwright/test'
export default defineConfig({
  testDir: './tests/browser', testMatch: ['cp8-worker.spec.ts', 'dashboard-pixel.spec.ts'], workers: 2, timeout: 60000,
  use: { baseURL: 'http://127.0.0.1:4173', screenshot: 'only-on-failure' },
  reporter: [['list'], ['json', { outputFile: 'cp45-browser-proof/worker-results.json' }]],
  webServer: { command: 'npm run preview -- --port 4173 --strictPort --host 127.0.0.1', url: 'http://127.0.0.1:4173' }
})
