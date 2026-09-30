import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: '.', testMatch: 'f05.browser.ts', fullyParallel: false, workers: 1, retries: 0, forbidOnly: true,
  timeout: 30000, expect: { timeout: 5000 },
  outputDir: '../../../../../test-results/f05-browser/artifacts',
  reporter: [['line'], ['json', { outputFile: `${process.cwd()}/test-results/f05-browser/results.json` }]],
  use: { baseURL: 'http://127.0.0.1:4195', trace: 'retain-on-failure', screenshot: 'only-on-failure',
    launchOptions: process.env.F05_BROWSER_EXECUTABLE ? { executablePath: process.env.F05_BROWSER_EXECUTABLE } : {} },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 1000 } } },
    { name: 'mobile', use: { ...devices['Pixel 7'], viewport: { width: 412, height: 915 } } },
  ],
  webServer: { command: 'node_modules/.bin/vite preview --config tests/cp7/browser/planner/f05-preview/vite.config.mjs --host 127.0.0.1 --port 4195 --strictPort',
    url: 'http://127.0.0.1:4195/tests/cp7/browser/planner/f05-preview/index.html', reuseExistingServer: !process.env.CI, timeout: 30000 },
})
