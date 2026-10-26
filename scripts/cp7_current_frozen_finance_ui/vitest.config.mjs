import {defineConfig} from 'vitest/config'
export default defineConfig({cacheDir:'.cache/current-frozen-finance-ui',test:{include:['scripts/cp7_current_frozen_finance_ui/**/*.test.{ts,tsx}'],exclude:['node_modules/**'],maxWorkers:2},esbuild:{jsx:'automatic'}})
