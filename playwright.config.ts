import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests/browser',
  testMatch: ['cp45.spec.ts', 'cutting-bridge.spec.ts'],
  fullyParallel: false,
  forbidOnly: true,
  retries: 0,
  workers: 1,
  timeout: 30_000,
  expect: { timeout: 5_000 },
  outputDir: 'cp45-browser-proof/artifacts',
  reporter: [
    ['line'],
    ['json', { outputFile: 'cp45-browser-proof/results.json' }],
    ['html', { outputFolder: 'cp45-browser-proof/html', open: 'never' }],
  ],
  use: {
    baseURL: 'http://127.0.0.1:4173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'desktop-chromium', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } } },
    { name: 'mobile-chromium', use: { ...devices['Pixel 7'], viewport: { width: 412, height: 915 } } },
  ],
  webServer: {
    command: 'npm run preview -- --host 127.0.0.1 --port 4173 --strictPort',
    url: 'http://127.0.0.1:4173',
    reuseExistingServer: false,
    timeout: 30_000,
  },
})
