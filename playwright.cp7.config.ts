import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests/browser', testMatch: 'cp7-shell.spec.ts',
  fullyParallel: false, forbidOnly: true, retries: 0, workers: 1,
  timeout: 35_000, expect: { timeout: 7_000 },
  outputDir: 'test-results/cp7-shell-proof/artifacts',
  reporter: [['line'], ['json', { outputFile: 'test-results/cp7-shell-proof/results.json' }]],
  use: {
    baseURL: 'http://127.0.0.1:4187', trace: 'retain-on-failure', screenshot: 'only-on-failure',
    launchOptions: process.env.CP7_BROWSER_EXECUTABLE ? { executablePath: process.env.CP7_BROWSER_EXECUTABLE } : {},
  },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 1000 } } },
    { name: 'mobile', use: { ...devices['Pixel 7'], viewport: { width: 412, height: 915 } } },
  ],
  webServer: {
    command: 'npm run preview -- --host 127.0.0.1 --port 4187 --strictPort',
    url: 'http://127.0.0.1:4187', reuseExistingServer: !process.env.CI, timeout: 30_000,
  },
})
