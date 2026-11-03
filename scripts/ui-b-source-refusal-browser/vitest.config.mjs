import {defineConfig} from 'vitest/config'
export default defineConfig({test:{include:['scripts/ui-b-source-refusal-browser/transport.contract.test.ts'],maxWorkers:1}})
