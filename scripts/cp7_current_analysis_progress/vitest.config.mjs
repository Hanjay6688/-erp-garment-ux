import {defineConfig} from 'vitest/config'
export default defineConfig({cacheDir:'.cache/current-analysis-progress',test:{include:['scripts/cp7_current_analysis_progress/*.test.ts'],maxWorkers:2}})
