import {defineConfig} from 'vitest/config'
export default defineConfig({cacheDir:'.cache/current-progress-finance-ui',test:{include:['scripts/cp7_current_progress_finance_ui/**/*.test.{ts,tsx}'],exclude:['node_modules/**'],maxWorkers:2},oxc:{jsx:{runtime:'automatic'}}})
