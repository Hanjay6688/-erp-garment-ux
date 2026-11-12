import { defineConfig, devices } from '@playwright/test'
import shellConfig from './playwright.cp7.config'

export default defineConfig({
  ...shellConfig,
  testMatch: 'cp7-b-operator.spec.ts',
  outputDir: 'test-results/cp7-b-operator/artifacts',
  reporter: [['line'], ['json', { outputFile: 'test-results/cp7-b-operator/results.json' }]],
  use: {
    ...shellConfig.use,
    baseURL: 'http://127.0.0.1:4178',
    trace: 'off',
  },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 1000 }, timezoneId: 'Asia/Jakarta' } },
    { name: 'mobile', use: { ...devices['Pixel 7'], viewport: { width: 390, height: 844 }, timezoneId: 'America/Los_Angeles' } },
  ],
  webServer: {
    command: 'npm run preview -- --host 127.0.0.1 --port 4178 --strictPort --outDir cp6-ui-build',
    url: 'http://127.0.0.1:4178',
    reuseExistingServer: false,
    timeout: 15_000,
  },
})
