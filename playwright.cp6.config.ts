import { defineConfig, devices } from '@playwright/test'

const localMockKey = 'sb_publishable_mock_cp6_browser_contract_20260904'

export default defineConfig({
  testDir: './tests/browser',
  testMatch: 'cp6-laundry-qc.spec.ts',
  fullyParallel: false,
  forbidOnly: true,
  retries: 0,
  workers: 1,
  timeout: 45_000,
  expect: { timeout: 6_000 },
  outputDir: 'cp6-browser-contract-proof/artifacts',
  reporter: [
    ['line'],
    ['json', { outputFile: 'cp6-browser-contract-proof/results.json' }],
    ['html', { outputFolder: 'cp6-browser-contract-proof/html', open: 'never' }],
  ],
  use: {
    baseURL: 'http://127.0.0.1:4175',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'desktop-chromium', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } } },
    { name: 'mobile-chromium', use: { ...devices['Pixel 7'], viewport: { width: 412, height: 915 } } },
  ],
  webServer: {
    command: 'npm run build:uat-auth && npm run preview -- --host 127.0.0.1 --port 4175 --strictPort',
    url: 'http://127.0.0.1:4175',
    reuseExistingServer: false,
    timeout: 60_000,
    env: {
      VITE_ERP_RUNTIME_MODE: 'UAT_AUTH_SIMULATION',
      VITE_SUPABASE_URL: 'https://siimvrusnzxexizpyoib.supabase.co',
      VITE_SUPABASE_PUBLISHABLE_KEY: localMockKey,
      ERP_UAT_AUTH_ALLOW_MOCK_KEY: '1',
    },
  },
})
