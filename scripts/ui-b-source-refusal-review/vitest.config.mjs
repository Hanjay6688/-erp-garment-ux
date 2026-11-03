import {defineConfig} from 'vitest/config'
import react from '@vitejs/plugin-react'
export default defineConfig({plugins:[react()],test:{include:['scripts/ui-b-source-refusal-review/revocation_BEFORE.case.tsx'],maxWorkers:1}})
